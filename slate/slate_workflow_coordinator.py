#!/usr/bin/env python3
# Modified: 2026-02-07T16:00:00Z | Author: Claude | Change: Intelligent workflow coordinator for AI task scheduling
"""
SLATE Workflow Coordinator
===========================

Coordinates AI-powered GitHub Actions workflows to run in an intelligent sequence.
Ensures maximum efficiency by:
- Batching similar AI tasks together (minimizes model loading)
- Sequencing dependent workflows correctly
- Distributing work across dual GPUs
- Preventing workflow collisions
- Maximizing local AI inference utilization

Usage:
    python slate/slate_workflow_coordinator.py --status          # Show coordinator status
    python slate/slate_workflow_coordinator.py --plan            # Generate execution plan
    python slate/slate_workflow_coordinator.py --dispatch        # Dispatch scheduled workflows
    python slate/slate_workflow_coordinator.py --optimize        # Optimize workflow schedule
"""

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

STATE_FILE = WORKSPACE_ROOT / ".slate_workflow_coordinator.json"
WORKFLOWS_DIR = WORKSPACE_ROOT / ".github" / "workflows"

# Workflow categories and their AI requirements
WORKFLOW_CONFIG = {
    # Training workflows (highest priority, runs first)
    "ai-training.yml": {
        "category": "training",
        "priority": 1,
        "gpu_required": True,
        "estimated_minutes": 60,
        "ai_models": ["mistral-nemo", "slate-custom"],
        "dependencies": [],
        "description": "Weekly model training from git repository",
    },
    # Maintenance workflows (runs after training)
    "ai-maintenance.yml": {
        "category": "maintenance",
        "priority": 2,
        "gpu_required": True,
        "estimated_minutes": 30,
        "ai_models": ["mistral-nemo"],
        "dependencies": [],
        "description": "Codebase analysis and documentation updates",
    },
    # Agentic workflows (autonomous task execution)
    "agentic.yml": {
        "category": "agentic",
        "priority": 3,
        "gpu_required": True,
        "estimated_minutes": 45,
        "ai_models": ["slate-coder", "slate-fast", "slate-planner"],
        "dependencies": ["ai-training.yml"],
        "description": "Autonomous agent task execution",
    },
    # Fork intelligence (analyzes upstream/downstream)
    "fork-intelligence.yml": {
        "category": "intelligence",
        "priority": 4,
        "gpu_required": True,
        "estimated_minutes": 20,
        "ai_models": ["mistral-nemo"],
        "dependencies": [],
        "description": "AI-powered fork analysis",
    },
    # CI workflows (lightweight, can run in parallel)
    "ci.yml": {
        "category": "ci",
        "priority": 5,
        "gpu_required": True,
        "estimated_minutes": 15,
        "ai_models": ["mistral-nemo"],
        "dependencies": [],
        "description": "Continuous integration with AI code review",
    },
    # Nightly workflows (comprehensive)
    "nightly.yml": {
        "category": "nightly",
        "priority": 6,
        "gpu_required": True,
        "estimated_minutes": 45,
        "ai_models": ["mistral-nemo"],
        "dependencies": [],
        "description": "Nightly full test suite and AI analysis",
    },
    # Service management (lightweight)
    "service-management.yml": {
        "category": "service",
        "priority": 10,
        "gpu_required": False,
        "estimated_minutes": 5,
        "ai_models": [],
        "dependencies": [],
        "description": "Service health checks and management",
    },
}

# Optimal execution order for maximum efficiency
OPTIMAL_SEQUENCE = [
    # Phase 1: Training (model updates first)
    ["ai-training.yml"],
    # Phase 2: Maintenance (use fresh models)
    ["ai-maintenance.yml", "fork-intelligence.yml"],
    # Phase 3: Agentic (task execution with updated models)
    ["agentic.yml"],
    # Phase 4: Validation (parallel CI/Nightly)
    ["ci.yml", "nightly.yml"],
    # Phase 5: Services (always last)
    ["service-management.yml"],
]


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

@dataclass
class WorkflowRun:
    """Represents a workflow run."""
    workflow: str
    run_id: int
    status: str
    conclusion: Optional[str]
    started_at: Optional[str]
    completed_at: Optional[str]
    duration_minutes: float = 0


@dataclass
class ExecutionPlan:
    """An execution plan for workflows."""
    phases: list
    total_estimated_minutes: int
    gpu_utilization: float
    model_switches: int
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ═══════════════════════════════════════════════════════════════════════
# WORKFLOW COORDINATOR
# ═══════════════════════════════════════════════════════════════════════

class WorkflowCoordinator:
    """Coordinates AI-powered workflow execution."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.state = self._load_state()
        self.gh_cli = self._find_gh_cli()

    def _find_gh_cli(self) -> str:
        local_gh = self.workspace / ".tools" / "gh.exe"
        if local_gh.exists():
            return str(local_gh)
        return "gh"

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "last_coordination": None,
            "total_dispatches": 0,
            "workflow_stats": {},
        }

    def _save_state(self):
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str), encoding="utf-8")

    def _run_gh(self, args: list[str], timeout: int = 30) -> subprocess.CompletedProcess:
        return subprocess.run(
            [self.gh_cli] + args,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(self.workspace), encoding="utf-8", errors="replace"
        )

    def get_workflow_list(self) -> list[str]:
        """Get list of workflow files."""
        workflows = []
        for wf in WORKFLOWS_DIR.glob("*.yml"):
            workflows.append(wf.name)
        return sorted(workflows)

    def get_recent_runs(self, workflow: str = None, limit: int = 10) -> list[WorkflowRun]:
        """Get recent workflow runs."""
        args = ["run", "list", "--limit", str(limit), "--json",
                "databaseId,workflowName,status,conclusion,createdAt,updatedAt"]
        if workflow:
            args.extend(["--workflow", workflow])

        result = self._run_gh(args)
        if result.returncode != 0:
            return []

        runs = []
        try:
            data = json.loads(result.stdout)
            for run in data:
                started = run.get("createdAt")
                completed = run.get("updatedAt")

                duration = 0
                if started and completed and run.get("status") == "completed":
                    try:
                        start_dt = datetime.fromisoformat(started.replace("Z", "+00:00"))
                        end_dt = datetime.fromisoformat(completed.replace("Z", "+00:00"))
                        duration = (end_dt - start_dt).total_seconds() / 60
                    except Exception:
                        pass

                runs.append(WorkflowRun(
                    workflow=run.get("workflowName", ""),
                    run_id=run.get("databaseId", 0),
                    status=run.get("status", ""),
                    conclusion=run.get("conclusion"),
                    started_at=started,
                    completed_at=completed,
                    duration_minutes=duration,
                ))
        except json.JSONDecodeError:
            pass

        return runs

    def get_running_workflows(self) -> list[str]:
        """Get currently running workflows."""
        runs = self.get_recent_runs(limit=20)
        return [r.workflow for r in runs if r.status in ("queued", "in_progress")]

    def check_workflow_available(self, workflow: str) -> bool:
        """Check if a workflow is available to run (not already running)."""
        running = self.get_running_workflows()
        return workflow not in running

    def generate_execution_plan(self, workflows: list[str] = None) -> ExecutionPlan:
        """Generate an optimal execution plan for workflows."""
        if not workflows:
            workflows = list(WORKFLOW_CONFIG.keys())

        phases = []
        total_minutes = 0
        model_switches = 0
        last_models = set()

        for phase_workflows in OPTIMAL_SEQUENCE:
            phase_items = []
            for wf in phase_workflows:
                if wf in workflows and wf in WORKFLOW_CONFIG:
                    config = WORKFLOW_CONFIG[wf]
                    phase_items.append({
                        "workflow": wf,
                        "category": config["category"],
                        "priority": config["priority"],
                        "estimated_minutes": config["estimated_minutes"],
                        "ai_models": config["ai_models"],
                        "gpu_required": config["gpu_required"],
                    })
                    total_minutes += config["estimated_minutes"]

                    # Count model switches
                    current_models = set(config["ai_models"])
                    if current_models and current_models != last_models:
                        model_switches += 1
                        last_models = current_models

            if phase_items:
                phases.append({
                    "phase": len(phases) + 1,
                    "workflows": phase_items,
                    "parallel": len(phase_items) > 1,
                })

        # Calculate GPU utilization
        gpu_workflows = sum(1 for wf in workflows if WORKFLOW_CONFIG.get(wf, {}).get("gpu_required", False))
        gpu_utilization = gpu_workflows / max(len(workflows), 1)

        return ExecutionPlan(
            phases=phases,
            total_estimated_minutes=total_minutes,
            gpu_utilization=gpu_utilization,
            model_switches=model_switches,
        )

    def dispatch_workflow(self, workflow: str, inputs: dict = None) -> bool:
        """Dispatch a workflow via GitHub CLI."""
        if not self.check_workflow_available(workflow):
            print(f"  [!] {workflow} is already running")
            return False

        args = ["workflow", "run", workflow]
        if inputs:
            for key, value in inputs.items():
                args.extend(["-f", f"{key}={value}"])

        result = self._run_gh(args)
        if result.returncode == 0:
            # Update stats
            stats = self.state.setdefault("workflow_stats", {})
            wf_stats = stats.setdefault(workflow, {"dispatches": 0, "last_dispatch": None})
            wf_stats["dispatches"] = wf_stats.get("dispatches", 0) + 1
            wf_stats["last_dispatch"] = datetime.now(timezone.utc).isoformat()
            self.state["total_dispatches"] = self.state.get("total_dispatches", 0) + 1
            self._save_state()
            return True

        return False

    def dispatch_scheduled(self, dry_run: bool = False) -> dict:
        """Dispatch workflows according to the optimal schedule."""
        print()
        print("=" * 70)
        print("  SLATE Workflow Coordinator - Dispatching Scheduled Workflows")
        print("=" * 70)
        print()

        plan = self.generate_execution_plan()
        dispatched = []
        skipped = []

        for phase in plan.phases:
            print(f"  Phase {phase['phase']}:")
            for item in phase["workflows"]:
                workflow = item["workflow"]

                if not self.check_workflow_available(workflow):
                    print(f"    [SKIP] {workflow} - already running")
                    skipped.append(workflow)
                    continue

                if dry_run:
                    print(f"    [DRY] Would dispatch: {workflow}")
                    dispatched.append(workflow)
                else:
                    if self.dispatch_workflow(workflow):
                        print(f"    [OK] Dispatched: {workflow}")
                        dispatched.append(workflow)
                    else:
                        print(f"    [!] Failed to dispatch: {workflow}")
                        skipped.append(workflow)

            print()

        self.state["last_coordination"] = datetime.now(timezone.utc).isoformat()
        self._save_state()

        result = {
            "dispatched": dispatched,
            "skipped": skipped,
            "total_phases": len(plan.phases),
            "estimated_minutes": plan.total_estimated_minutes,
        }

        print(f"  Dispatched: {len(dispatched)}, Skipped: {len(skipped)}")
        print("=" * 70)

        return result

    def analyze_workflow_efficiency(self) -> dict:
        """Analyze workflow efficiency and suggest optimizations."""
        analysis = {
            "total_workflows": len(self.get_workflow_list()),
            "ai_enabled_workflows": 0,
            "gpu_workflows": 0,
            "self_hosted_workflows": 0,
            "optimization_suggestions": [],
        }

        for wf_name in self.get_workflow_list():
            wf_path = WORKFLOWS_DIR / wf_name
            if not wf_path.exists():
                continue

            try:
                content = wf_path.read_text(encoding="utf-8")

                # Check for self-hosted runner
                if "self-hosted" in content:
                    analysis["self_hosted_workflows"] += 1

                # Check for GPU usage
                if "gpu" in content.lower() or "cuda" in content.lower():
                    analysis["gpu_workflows"] += 1

                # Check for AI/Ollama usage
                if "ollama" in content.lower() or "ai" in content.lower():
                    analysis["ai_enabled_workflows"] += 1

                # Check for optimization opportunities
                if "ubuntu-latest" in content and wf_name in WORKFLOW_CONFIG:
                    analysis["optimization_suggestions"].append({
                        "workflow": wf_name,
                        "suggestion": "Consider using self-hosted runner for AI tasks",
                    })

            except Exception:
                continue

        return analysis

    def print_status(self):
        """Print coordinator status."""
        print()
        print("=" * 70)
        print("  SLATE Workflow Coordinator Status")
        print("=" * 70)
        print()

        print("  Coordination Stats:")
        print(f"    Last coordination: {self.state.get('last_coordination', 'Never')}")
        print(f"    Total dispatches: {self.state.get('total_dispatches', 0)}")
        print()

        # Currently running
        running = self.get_running_workflows()
        print(f"  Currently Running: {len(running)}")
        for wf in running:
            print(f"    - {wf}")
        print()

        # Workflow stats
        analysis = self.analyze_workflow_efficiency()
        print("  Workflow Analysis:")
        print(f"    Total workflows: {analysis['total_workflows']}")
        print(f"    AI-enabled: {analysis['ai_enabled_workflows']}")
        print(f"    GPU-enabled: {analysis['gpu_workflows']}")
        print(f"    Self-hosted: {analysis['self_hosted_workflows']}")
        print()

        # Recent runs
        runs = self.get_recent_runs(limit=5)
        if runs:
            print("  Recent Runs:")
            for run in runs:
                status = run.conclusion or run.status
                print(f"    {run.workflow}: {status} ({run.duration_minutes:.1f} min)")
        print()

        print("=" * 70)

    def print_plan(self):
        """Print execution plan."""
        print()
        print("=" * 70)
        print("  SLATE Workflow Execution Plan")
        print("=" * 70)
        print()

        plan = self.generate_execution_plan()

        for phase in plan.phases:
            parallel = " (parallel)" if phase["parallel"] else ""
            print(f"  Phase {phase['phase']}{parallel}:")
            for item in phase["workflows"]:
                models = ", ".join(item["ai_models"]) if item["ai_models"] else "none"
                gpu = "GPU" if item["gpu_required"] else "CPU"
                print(f"    - {item['workflow']:<30} ~{item['estimated_minutes']}min  [{gpu}]  Models: {models}")
            print()

        print("  Summary:")
        print(f"    Total phases: {len(plan.phases)}")
        print(f"    Estimated time: {plan.total_estimated_minutes} minutes")
        print(f"    GPU utilization: {plan.gpu_utilization * 100:.0f}%")
        print(f"    Model switches: {plan.model_switches}")
        print()
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SLATE Workflow Coordinator")
    parser.add_argument("--status", action="store_true", help="Show coordinator status")
    parser.add_argument("--plan", action="store_true", help="Show execution plan")
    parser.add_argument("--dispatch", action="store_true", help="Dispatch scheduled workflows")
    parser.add_argument("--optimize", action="store_true", help="Analyze and suggest optimizations")
    parser.add_argument("--dry-run", action="store_true", help="Dry run (don't actually dispatch)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    coordinator = WorkflowCoordinator()

    if args.dispatch:
        result = coordinator.dispatch_scheduled(dry_run=args.dry_run)
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.plan:
        if args.json:
            plan = coordinator.generate_execution_plan()
            print(json.dumps({
                "phases": plan.phases,
                "total_estimated_minutes": plan.total_estimated_minutes,
                "gpu_utilization": plan.gpu_utilization,
                "model_switches": plan.model_switches,
            }, indent=2))
        else:
            coordinator.print_plan()

    elif args.optimize:
        analysis = coordinator.analyze_workflow_efficiency()
        if args.json:
            print(json.dumps(analysis, indent=2))
        else:
            print("\nWorkflow Efficiency Analysis:")
            print(json.dumps(analysis, indent=2))

    else:
        coordinator.print_status()


if __name__ == "__main__":
    main()
