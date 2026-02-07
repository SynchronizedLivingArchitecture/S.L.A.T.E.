#!/usr/bin/env python3
"""
SLATE Guided Workflow Engine
============================

Interactive guided experience for submitting jobs and controlling
the project through the dashboard workflow pipeline.

This module provides:
- WorkflowGuide: Step-by-step workflow submission guidance
- JobTemplates: Pre-configured job templates for common tasks
- WorkflowNarrator: AI-powered contextual help
- PipelineVisualizer: Visual representation of workflow stages

The guided workflow transforms the dashboard from a monitoring tool
into an interactive command center for project control.
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple
import logging

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger(__name__)


class WorkflowStage(Enum):
    """Stages in the workflow pipeline."""
    TASK_QUEUE = "task_queue"      # Task created in queue
    RUNNER_PICKUP = "runner"        # Runner picks up task
    WORKFLOW_EXEC = "workflow"      # GitHub workflow executing
    VALIDATION = "validation"       # Tests/checks running
    COMPLETION = "completion"       # PR/merge/complete


class JobCategory(Enum):
    """Categories of jobs that can be submitted."""
    CODE_CHANGE = "code_change"        # Edit/refactor code
    BUG_FIX = "bug_fix"                # Fix a bug
    NEW_FEATURE = "new_feature"        # Add functionality
    DOCUMENTATION = "documentation"    # Update docs
    TESTING = "testing"                # Run tests
    AI_ANALYSIS = "ai_analysis"        # AI code analysis
    MAINTENANCE = "maintenance"        # Cleanup/maintenance
    DEPLOYMENT = "deployment"          # Deploy/release


@dataclass
class JobTemplate:
    """Template for a submittable job."""
    id: str
    name: str
    description: str
    category: JobCategory
    workflow: str  # GitHub workflow to trigger
    ai_capable: bool = False  # Can be processed by local AI
    parameters: Dict[str, Any] = field(default_factory=dict)
    estimated_duration: str = "~5 min"
    priority: int = 5  # 1-10, 10 is highest


# Pre-configured job templates
JOB_TEMPLATES: List[JobTemplate] = [
    JobTemplate(
        id="run_tests",
        name="Run Test Suite",
        description="Execute full pytest test suite with coverage",
        category=JobCategory.TESTING,
        workflow="ci.yml",
        parameters={"test_args": "-v --cov=slate"},
        estimated_duration="~3 min"
    ),
    JobTemplate(
        id="lint_check",
        name="Code Lint Check",
        description="Run ruff linter and check code quality",
        category=JobCategory.MAINTENANCE,
        workflow="ci.yml",
        parameters={"lint_only": True},
        estimated_duration="~1 min"
    ),
    JobTemplate(
        id="security_audit",
        name="Security Audit",
        description="Run security checks (SDK guard, PII scan, ActionGuard)",
        category=JobCategory.MAINTENANCE,
        workflow="ci.yml",
        parameters={"security_check": True},
        estimated_duration="~2 min"
    ),
    JobTemplate(
        id="ai_code_review",
        name="AI Code Review",
        description="Local AI analysis of recent code changes",
        category=JobCategory.AI_ANALYSIS,
        workflow="ai-maintenance.yml",
        ai_capable=True,
        parameters={"analyze_recent": True},
        estimated_duration="~5 min",
        priority=7
    ),
    JobTemplate(
        id="ai_documentation",
        name="AI Documentation Update",
        description="AI-generated documentation for changed files",
        category=JobCategory.DOCUMENTATION,
        workflow="ai-maintenance.yml",
        ai_capable=True,
        parameters={"update_docs": True},
        estimated_duration="~10 min"
    ),
    JobTemplate(
        id="full_analysis",
        name="Full Codebase Analysis",
        description="Comprehensive AI analysis of entire codebase",
        category=JobCategory.AI_ANALYSIS,
        workflow="ai-maintenance.yml",
        ai_capable=True,
        parameters={"full_analysis": True},
        estimated_duration="~30 min",
        priority=3
    ),
    JobTemplate(
        id="nightly_suite",
        name="Nightly Test Suite",
        description="Complete nightly tests with dependency audit",
        category=JobCategory.TESTING,
        workflow="nightly.yml",
        estimated_duration="~15 min"
    ),
    JobTemplate(
        id="docker_build",
        name="Docker Build",
        description="Build and validate Docker images",
        category=JobCategory.DEPLOYMENT,
        workflow="docker.yml",
        parameters={"push": False},
        estimated_duration="~10 min"
    ),
    JobTemplate(
        id="fork_sync",
        name="Fork Sync",
        description="Sync fork repositories with upstream",
        category=JobCategory.MAINTENANCE,
        workflow="fork-sync.yml",
        estimated_duration="~2 min"
    ),
    JobTemplate(
        id="custom_task",
        name="Custom Task",
        description="Create a custom task for the workflow queue",
        category=JobCategory.CODE_CHANGE,
        workflow="agentic.yml",
        ai_capable=True,
        parameters={"custom": True},
        estimated_duration="varies",
        priority=5
    )
]


@dataclass
class GuidedWorkflowStep:
    """A step in the guided workflow submission process."""
    id: str
    title: str
    description: str
    instruction: str
    action_type: str  # "select", "input", "confirm", "execute", "observe"
    options: List[Dict[str, Any]] = field(default_factory=list)
    requires_input: bool = False
    input_placeholder: str = ""
    validation_fn: Optional[str] = None
    auto_advance: bool = False
    advance_delay: float = 1.5


# Guided workflow submission steps
WORKFLOW_GUIDE_STEPS: List[GuidedWorkflowStep] = [
    GuidedWorkflowStep(
        id="welcome",
        title="Workflow Submission Guide",
        description="Learn to control your project through the workflow pipeline",
        instruction="This guide will walk you through submitting jobs to SLATE. Jobs flow through: Task Queue -> Runner -> GitHub Workflows -> Results",
        action_type="confirm",
        auto_advance=True,
        advance_delay=3.0
    ),
    GuidedWorkflowStep(
        id="select_category",
        title="Select Job Category",
        description="What type of work do you want to perform?",
        instruction="Choose the category that best matches your task:",
        action_type="select",
        options=[
            {"id": "testing", "label": "Testing", "icon": "flask", "desc": "Run tests and validations"},
            {"id": "ai_analysis", "label": "AI Analysis", "icon": "brain", "desc": "Local AI code review"},
            {"id": "maintenance", "label": "Maintenance", "icon": "wrench", "desc": "Cleanup and checks"},
            {"id": "deployment", "label": "Deployment", "icon": "rocket", "desc": "Build and deploy"},
            {"id": "custom", "label": "Custom Task", "icon": "edit", "desc": "Create custom job"}
        ]
    ),
    GuidedWorkflowStep(
        id="select_template",
        title="Select Job Template",
        description="Choose a pre-configured job or create custom",
        instruction="These templates are optimized for common tasks:",
        action_type="select",
        options=[]  # Populated dynamically based on category
    ),
    GuidedWorkflowStep(
        id="configure_job",
        title="Configure Job Parameters",
        description="Customize job settings before submission",
        instruction="Adjust parameters or accept defaults:",
        action_type="input",
        requires_input=True,
        input_placeholder="Additional parameters (optional)"
    ),
    GuidedWorkflowStep(
        id="review_job",
        title="Review Job Details",
        description="Confirm your job configuration",
        instruction="Review the job details before submission:",
        action_type="confirm"
    ),
    GuidedWorkflowStep(
        id="submit_job",
        title="Submit to Workflow",
        description="Adding job to the task queue",
        instruction="Your job is being submitted to the workflow pipeline...",
        action_type="execute",
        auto_advance=True,
        advance_delay=2.0
    ),
    GuidedWorkflowStep(
        id="observe_pipeline",
        title="Monitor Pipeline Progress",
        description="Watch your job flow through the pipeline",
        instruction="Track your job as it progresses through each stage:",
        action_type="observe"
    ),
    GuidedWorkflowStep(
        id="complete",
        title="Job Submitted Successfully",
        description="Your job is now in the workflow pipeline",
        instruction="You can monitor progress in the Workflow Pipeline panel or the Workflows page.",
        action_type="confirm"
    )
]


class WorkflowNarrator:
    """
    AI narrator for workflow guidance.

    Provides contextual help and explanations during the
    guided workflow submission process.
    """

    def __init__(self):
        self.ollama_available = False
        self._check_ollama()

    def _check_ollama(self) -> None:
        """Check if Ollama is available."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = response.status_code == 200
        except Exception:
            self.ollama_available = False

    async def explain_stage(self, stage: WorkflowStage) -> str:
        """Explain what happens at each workflow stage."""
        explanations = {
            WorkflowStage.TASK_QUEUE: (
                "Your job enters the Task Queue where it's stored in current_tasks.json. "
                "The queue manages priority, prevents duplicates, and tracks status."
            ),
            WorkflowStage.RUNNER_PICKUP: (
                "The GitHub Actions Runner picks up queued tasks. SLATE uses a self-hosted "
                "runner with dual RTX 5070 Ti GPUs for AI-accelerated processing."
            ),
            WorkflowStage.WORKFLOW_EXEC: (
                "GitHub Workflows execute your job. Workflows can run tests, perform AI analysis, "
                "build artifacts, or trigger deployments based on your job template."
            ),
            WorkflowStage.VALIDATION: (
                "Validation checks run automatically: tests must pass, security audits complete, "
                "and code quality gates are verified before marking the job complete."
            ),
            WorkflowStage.COMPLETION: (
                "Job complete! Results are available in the dashboard. AI-analyzed results "
                "include recommendations and the workflow may create PRs for code changes."
            )
        }
        return explanations.get(stage, "Processing...")

    async def suggest_job(self, context: Dict[str, Any]) -> str:
        """AI-powered job suggestion based on context."""
        if not self.ollama_available:
            return "Consider running an AI Code Review to analyze recent changes."

        try:
            import httpx

            # Get recent git activity for context
            git_info = ""
            try:
                result = subprocess.run(
                    ["git", "log", "--oneline", "-5"],
                    capture_output=True, text=True, timeout=5,
                    cwd=str(WORKSPACE_ROOT)
                )
                if result.returncode == 0:
                    git_info = f"Recent commits:\n{result.stdout}"
            except Exception:
                pass

            prompt = f"""You are SLATE's workflow advisor. Based on the current project state,
suggest the most valuable job to run next.

{git_info}

Context: {json.dumps(context, default=str)}

Provide a brief (1-2 sentence) recommendation for what job to submit.
Focus on: testing, AI analysis, security, or maintenance."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.5, "num_predict": 100}
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
        except Exception as e:
            logger.warning(f"AI suggestion failed: {e}")

        return "Consider running an AI Code Review to analyze recent changes."


class GuidedWorkflowEngine:
    """
    Main engine for guided workflow submission.

    Manages the step-by-step process of submitting jobs
    to the SLATE workflow pipeline.
    """

    def __init__(self):
        self.current_step_index = 0
        self.steps = list(WORKFLOW_GUIDE_STEPS)
        self.narrator = WorkflowNarrator()
        self.job_config: Dict[str, Any] = {}
        self.selected_category: Optional[str] = None
        self.selected_template: Optional[JobTemplate] = None
        self.active = False
        self.started_at: Optional[datetime] = None
        self.job_id: Optional[str] = None

    def reset(self) -> None:
        """Reset to initial state."""
        self.current_step_index = 0
        self.job_config = {}
        self.selected_category = None
        self.selected_template = None
        self.active = False
        self.started_at = None
        self.job_id = None

    def get_status(self) -> Dict[str, Any]:
        """Get current guided workflow status."""
        current = self.steps[self.current_step_index] if self.current_step_index < len(self.steps) else None
        return {
            "active": self.active,
            "current_step": current.id if current else None,
            "current_step_index": self.current_step_index,
            "total_steps": len(self.steps),
            "progress_percent": (self.current_step_index / len(self.steps)) * 100,
            "selected_category": self.selected_category,
            "selected_template": self.selected_template.id if self.selected_template else None,
            "job_config": self.job_config,
            "job_id": self.job_id
        }

    def start(self) -> Dict[str, Any]:
        """Start the guided workflow."""
        self.reset()
        self.active = True
        self.started_at = datetime.now()

        step = self.steps[0]
        return {
            "success": True,
            "active": True,
            "step": self._step_to_dict(step),
            "templates": self._get_templates_summary()
        }

    def _step_to_dict(self, step: GuidedWorkflowStep) -> Dict[str, Any]:
        """Convert step to dictionary for API response."""
        return {
            "id": step.id,
            "title": step.title,
            "description": step.description,
            "instruction": step.instruction,
            "action_type": step.action_type,
            "options": step.options,
            "requires_input": step.requires_input,
            "input_placeholder": step.input_placeholder,
            "auto_advance": step.auto_advance,
            "advance_delay": step.advance_delay
        }

    def _get_templates_summary(self) -> List[Dict[str, Any]]:
        """Get summary of all job templates."""
        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "workflow": t.workflow,
                "ai_capable": t.ai_capable,
                "estimated_duration": t.estimated_duration,
                "priority": t.priority
            }
            for t in JOB_TEMPLATES
        ]

    def _get_templates_for_category(self, category: str) -> List[Dict[str, Any]]:
        """Get templates filtered by category."""
        category_map = {
            "testing": JobCategory.TESTING,
            "ai_analysis": JobCategory.AI_ANALYSIS,
            "maintenance": JobCategory.MAINTENANCE,
            "deployment": JobCategory.DEPLOYMENT,
            "documentation": JobCategory.DOCUMENTATION,
            "custom": JobCategory.CODE_CHANGE
        }

        target_category = category_map.get(category)
        if not target_category:
            return self._get_templates_summary()

        return [
            {
                "id": t.id,
                "name": t.name,
                "description": t.description,
                "category": t.category.value,
                "workflow": t.workflow,
                "ai_capable": t.ai_capable,
                "estimated_duration": t.estimated_duration,
                "priority": t.priority
            }
            for t in JOB_TEMPLATES
            if t.category == target_category or t.id == "custom_task"
        ]

    def select_category(self, category: str) -> Dict[str, Any]:
        """Handle category selection."""
        self.selected_category = category

        # Move to template selection step
        self.current_step_index = 2  # select_template
        step = self.steps[self.current_step_index]

        # Populate options with templates for this category
        templates = self._get_templates_for_category(category)
        step.options = [
            {
                "id": t["id"],
                "label": t["name"],
                "desc": t["description"],
                "duration": t["estimated_duration"],
                "ai": t["ai_capable"]
            }
            for t in templates
        ]

        return {
            "success": True,
            "step": self._step_to_dict(step),
            "templates": templates
        }

    def select_template(self, template_id: str) -> Dict[str, Any]:
        """Handle template selection."""
        template = next((t for t in JOB_TEMPLATES if t.id == template_id), None)
        if not template:
            return {"success": False, "error": f"Template '{template_id}' not found"}

        self.selected_template = template
        self.job_config = dict(template.parameters)

        # Move to configure step
        self.current_step_index = 3  # configure_job
        step = self.steps[self.current_step_index]

        return {
            "success": True,
            "step": self._step_to_dict(step),
            "template": {
                "id": template.id,
                "name": template.name,
                "description": template.description,
                "workflow": template.workflow,
                "parameters": template.parameters,
                "estimated_duration": template.estimated_duration
            }
        }

    def configure_job(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Configure job parameters."""
        self.job_config.update(parameters)

        # Move to review step
        self.current_step_index = 4  # review_job
        step = self.steps[self.current_step_index]

        return {
            "success": True,
            "step": self._step_to_dict(step),
            "job_summary": self._get_job_summary()
        }

    def _get_job_summary(self) -> Dict[str, Any]:
        """Get summary of configured job."""
        if not self.selected_template:
            return {}

        return {
            "template_name": self.selected_template.name,
            "category": self.selected_template.category.value,
            "workflow": self.selected_template.workflow,
            "ai_capable": self.selected_template.ai_capable,
            "estimated_duration": self.selected_template.estimated_duration,
            "priority": self.selected_template.priority,
            "parameters": self.job_config
        }

    async def submit_job(self) -> Dict[str, Any]:
        """Submit the configured job to the workflow."""
        if not self.selected_template:
            return {"success": False, "error": "No template selected"}

        # Move to submit step
        self.current_step_index = 5  # submit_job

        # Create task in current_tasks.json
        import uuid
        self.job_id = str(uuid.uuid4())[:8]

        task = {
            "id": self.job_id,
            "title": self.selected_template.name,
            "description": self.selected_template.description,
            "status": "pending",
            "priority": self.selected_template.priority,
            "assigned_to": "workflow",
            "created_at": datetime.now().isoformat(),
            "created_by": "guided_workflow",
            "workflow": self.selected_template.workflow,
            "parameters": self.job_config,
            "ai_capable": self.selected_template.ai_capable
        }

        # Add to task queue
        tasks_file = WORKSPACE_ROOT / "current_tasks.json"
        try:
            from slate_core.file_lock import FileLock

            with FileLock(str(tasks_file)):
                if tasks_file.exists():
                    tasks = json.loads(tasks_file.read_text())
                else:
                    tasks = []

                tasks.append(task)
                tasks_file.write_text(json.dumps(tasks, indent=2))

            # Attempt to dispatch workflow
            dispatch_result = await self._dispatch_workflow()

            # Move to observe step
            self.current_step_index = 6  # observe_pipeline
            step = self.steps[self.current_step_index]

            return {
                "success": True,
                "step": self._step_to_dict(step),
                "job_id": self.job_id,
                "task": task,
                "dispatch": dispatch_result,
                "pipeline_status": {
                    "task_queue": "complete",
                    "runner": "pending",
                    "workflow": "pending",
                    "validation": "pending",
                    "completion": "pending"
                }
            }

        except Exception as e:
            logger.error(f"Failed to submit job: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    async def _dispatch_workflow(self) -> Dict[str, Any]:
        """Dispatch the GitHub workflow."""
        if not self.selected_template:
            return {"dispatched": False, "reason": "No template"}

        workflow = self.selected_template.workflow

        try:
            # Use gh CLI to dispatch workflow
            gh_path = WORKSPACE_ROOT / ".tools" / "gh.exe"
            gh_cmd = str(gh_path) if gh_path.exists() else "gh"

            result = subprocess.run(
                [gh_cmd, "workflow", "run", workflow],
                capture_output=True,
                text=True,
                timeout=30,
                cwd=str(WORKSPACE_ROOT)
            )

            if result.returncode == 0:
                return {
                    "dispatched": True,
                    "workflow": workflow,
                    "message": f"Workflow {workflow} dispatched"
                }
            else:
                return {
                    "dispatched": False,
                    "workflow": workflow,
                    "reason": result.stderr or "Dispatch failed"
                }

        except Exception as e:
            return {
                "dispatched": False,
                "reason": str(e)
            }

    async def get_pipeline_status(self) -> Dict[str, Any]:
        """Get current pipeline status for the submitted job."""
        if not self.job_id:
            return {"error": "No job submitted"}

        # Check task queue status
        tasks_file = WORKSPACE_ROOT / "current_tasks.json"
        task_status = "unknown"

        if tasks_file.exists():
            tasks = json.loads(tasks_file.read_text())
            task = next((t for t in tasks if t.get("id") == self.job_id), None)
            if task:
                task_status = task.get("status", "unknown")

        # Check workflow runs
        workflow_status = "unknown"
        try:
            gh_path = WORKSPACE_ROOT / ".tools" / "gh.exe"
            gh_cmd = str(gh_path) if gh_path.exists() else "gh"

            result = subprocess.run(
                [gh_cmd, "run", "list", "--limit", "5", "--json", "status,conclusion,name,createdAt"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(WORKSPACE_ROOT)
            )

            if result.returncode == 0:
                runs = json.loads(result.stdout)
                if runs:
                    latest = runs[0]
                    workflow_status = latest.get("status", "unknown")
        except Exception:
            pass

        # Map to pipeline stages
        pipeline = {
            "task_queue": "complete" if task_status != "unknown" else "pending",
            "runner": "active" if task_status == "in_progress" else ("complete" if task_status == "completed" else "pending"),
            "workflow": workflow_status if workflow_status != "unknown" else "pending",
            "validation": "pending",
            "completion": "complete" if task_status == "completed" else "pending"
        }

        return {
            "job_id": self.job_id,
            "task_status": task_status,
            "workflow_status": workflow_status,
            "pipeline": pipeline,
            "stage_explanations": {
                stage.value: await self.narrator.explain_stage(stage)
                for stage in WorkflowStage
            }
        }

    def complete(self) -> Dict[str, Any]:
        """Complete the guided workflow."""
        self.current_step_index = 7  # complete
        step = self.steps[self.current_step_index]
        self.active = False

        duration = (datetime.now() - self.started_at).total_seconds() if self.started_at else 0

        return {
            "success": True,
            "complete": True,
            "step": self._step_to_dict(step),
            "job_id": self.job_id,
            "duration_seconds": duration,
            "summary": self._get_job_summary()
        }

    def skip_to_observe(self) -> Dict[str, Any]:
        """Skip directly to the observe pipeline step."""
        self.current_step_index = 6  # observe_pipeline
        step = self.steps[self.current_step_index]

        return {
            "success": True,
            "step": self._step_to_dict(step)
        }


# Quick job submission functions (bypass guided mode)

async def quick_submit_job(template_id: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """
    Quick job submission bypassing guided mode.

    Use this for programmatic job submission from CLI or other tools.
    """
    engine = GuidedWorkflowEngine()

    template = next((t for t in JOB_TEMPLATES if t.id == template_id), None)
    if not template:
        return {"success": False, "error": f"Template '{template_id}' not found"}

    engine.selected_template = template
    engine.job_config = dict(template.parameters)
    if parameters:
        engine.job_config.update(parameters)

    return await engine.submit_job()


def get_available_templates() -> List[Dict[str, Any]]:
    """Get list of all available job templates."""
    return [
        {
            "id": t.id,
            "name": t.name,
            "description": t.description,
            "category": t.category.value,
            "workflow": t.workflow,
            "ai_capable": t.ai_capable,
            "estimated_duration": t.estimated_duration,
            "command": f"python slate/guided_workflow.py --submit {t.id}"
        }
        for t in JOB_TEMPLATES
    ]


# Global engine instance
_engine: Optional[GuidedWorkflowEngine] = None


def get_engine() -> GuidedWorkflowEngine:
    """Get or create the global guided workflow engine."""
    global _engine
    if _engine is None:
        _engine = GuidedWorkflowEngine()
    return _engine


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Guided Workflow")
    parser.add_argument("--list", action="store_true", help="List available templates")
    parser.add_argument("--submit", type=str, help="Submit job by template ID")
    parser.add_argument("--status", action="store_true", help="Check workflow status")
    parser.add_argument("--interactive", action="store_true", help="Run interactive guided mode")
    args = parser.parse_args()

    if args.list:
        print("\nAvailable Job Templates:")
        print("=" * 60)
        for t in get_available_templates():
            ai_badge = " [AI]" if t["ai_capable"] else ""
            print(f"\n  {t['id']}{ai_badge}")
            print(f"    {t['name']}")
            print(f"    {t['description']}")
            print(f"    Workflow: {t['workflow']} | Duration: {t['estimated_duration']}")

    elif args.submit:
        async def do_submit():
            result = await quick_submit_job(args.submit)
            if result["success"]:
                print(f"\nJob submitted successfully!")
                print(f"  Job ID: {result.get('job_id')}")
                print(f"  Workflow: {result.get('task', {}).get('workflow')}")
            else:
                print(f"\nFailed to submit job: {result.get('error')}")

        asyncio.run(do_submit())

    elif args.status:
        engine = get_engine()
        print("\nGuided Workflow Status:")
        print(json.dumps(engine.get_status(), indent=2))

    elif args.interactive:
        async def interactive():
            engine = GuidedWorkflowEngine()

            print("\n" + "=" * 60)
            print("  SLATE Guided Workflow Submission")
            print("=" * 60)

            # Start
            result = engine.start()
            step = result["step"]
            print(f"\n{step['title']}")
            print(f"  {step['instruction']}")
            input("\nPress Enter to continue...")

            # Select category
            print("\nCategories:")
            for i, opt in enumerate(WORKFLOW_GUIDE_STEPS[1].options, 1):
                print(f"  {i}. {opt['label']} - {opt['desc']}")

            choice = input("\nSelect category (1-5): ")
            categories = ["testing", "ai_analysis", "maintenance", "deployment", "custom"]
            category = categories[int(choice) - 1] if choice.isdigit() and 1 <= int(choice) <= 5 else "testing"

            result = engine.select_category(category)

            # Select template
            print(f"\nTemplates for {category}:")
            templates = result["templates"]
            for i, t in enumerate(templates, 1):
                ai = " [AI]" if t["ai_capable"] else ""
                print(f"  {i}. {t['name']}{ai} ({t['estimated_duration']})")

            choice = input("\nSelect template: ")
            idx = int(choice) - 1 if choice.isdigit() else 0
            template_id = templates[idx]["id"] if 0 <= idx < len(templates) else templates[0]["id"]

            result = engine.select_template(template_id)

            # Configure (skip for simplicity)
            result = engine.configure_job({})

            # Review
            summary = result["job_summary"]
            print(f"\nJob Summary:")
            print(f"  Template: {summary['template_name']}")
            print(f"  Workflow: {summary['workflow']}")
            print(f"  Duration: {summary['estimated_duration']}")

            confirm = input("\nSubmit this job? (y/n): ")
            if confirm.lower() != 'y':
                print("Cancelled.")
                return

            # Submit
            result = await engine.submit_job()
            if result["success"]:
                print(f"\nJob submitted!")
                print(f"  Job ID: {result['job_id']}")

                dispatch = result.get("dispatch", {})
                if dispatch.get("dispatched"):
                    print(f"  Workflow dispatched: {dispatch['workflow']}")
                else:
                    print(f"  Dispatch note: {dispatch.get('reason', 'Queued for runner')}")
            else:
                print(f"\nFailed: {result.get('error')}")

        asyncio.run(interactive())

    else:
        parser.print_help()
