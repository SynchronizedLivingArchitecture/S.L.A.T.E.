#!/usr/bin/env python3
# Modified: 2026-02-07T15:30:00Z | Author: CLAUDE | Change: Create AI-driven interactive learning engine
"""
SLATE Interactive Tutor Engine
===============================
AI-driven interactive learning engine with achievements, XP system, and personalized paths.

Features:
- Multiple learning paths (fundamentals, AI integration, workflows, GPU optimization)
- Achievement system with unlockable badges
- XP and streak tracking
- AI-generated explanations via Ollama
- Progressive disclosure of content
- Personalized recommendations based on tech stack

Usage:
    from slate.interactive_tutor import get_tutor

    tutor = get_tutor()
    await tutor.start_learning_session("slate-fundamentals")
    step = await tutor.get_current_step()
    explanation = await tutor.get_ai_explanation("GPU load balancing")
    result = await tutor.complete_step(step.id, {"success": True})
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate_core.file_lock import FileLock

logger = logging.getLogger("slate.interactive_tutor")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class StepCategory(Enum):
    """Type of learning step."""
    CONCEPT = "concept"       # Understanding a concept
    HANDS_ON = "hands_on"     # Practical exercise
    QUIZ = "quiz"             # Knowledge check
    PROJECT = "project"       # Mini-project
    EXPLORE = "explore"       # Self-guided exploration


class AchievementCategory(Enum):
    """Achievement tier."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    MASTERY = "mastery"


class SessionStatus(Enum):
    """Learning session status."""
    INACTIVE = "inactive"
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LearningStep:
    """A single step in a learning path."""
    id: str
    title: str
    description: str
    category: StepCategory
    path_id: str
    order: int
    prerequisites: List[str] = field(default_factory=list)
    ai_explanation_prompt: str = ""
    success_criteria: Dict[str, Any] = field(default_factory=dict)
    hints: List[str] = field(default_factory=list)
    estimated_minutes: int = 5
    xp_reward: int = 50
    achievement_trigger: Optional[str] = None
    action_command: Optional[str] = None  # Optional Python command to run
    resources: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category.value,
            "path_id": self.path_id,
            "order": self.order,
            "prerequisites": self.prerequisites,
            "ai_explanation_prompt": self.ai_explanation_prompt,
            "success_criteria": self.success_criteria,
            "hints": self.hints,
            "estimated_minutes": self.estimated_minutes,
            "xp_reward": self.xp_reward,
            "achievement_trigger": self.achievement_trigger,
            "action_command": self.action_command,
            "resources": self.resources,
        }


@dataclass
class Achievement:
    """An unlockable achievement."""
    id: str
    name: str
    description: str
    icon: str  # Emoji or SVG reference
    category: AchievementCategory
    trigger_condition: str  # e.g., "complete_5_steps", "finish_path:slate-fundamentals"
    xp_reward: int
    unlocked_at: Optional[str] = None
    hidden: bool = False  # Secret achievements

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "category": self.category.value,
            "trigger_condition": self.trigger_condition,
            "xp_reward": self.xp_reward,
            "unlocked_at": self.unlocked_at,
            "hidden": self.hidden,
            "unlocked": self.unlocked_at is not None,
        }


@dataclass
class LearningPath:
    """A complete learning path."""
    id: str
    name: str
    description: str
    icon: str
    difficulty: str  # "beginner", "intermediate", "advanced"
    steps: List[LearningStep]
    estimated_hours: float
    prerequisites: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "icon": self.icon,
            "difficulty": self.difficulty,
            "step_count": len(self.steps),
            "estimated_hours": self.estimated_hours,
            "prerequisites": self.prerequisites,
            "tags": self.tags,
        }


@dataclass
class LearningProgress:
    """User's learning progress."""
    user_id: str = "local-user"
    current_path: Optional[str] = None
    current_step_index: int = 0
    session_status: SessionStatus = SessionStatus.INACTIVE
    completed_steps: List[str] = field(default_factory=list)
    completed_paths: List[str] = field(default_factory=list)
    achievements: List[str] = field(default_factory=list)
    total_xp: int = 0
    streak_days: int = 0
    last_session_date: Optional[str] = None
    tech_stack: List[str] = field(default_factory=list)
    skill_levels: Dict[str, int] = field(default_factory=dict)
    preferences: Dict[str, Any] = field(default_factory=dict)
    session_started_at: Optional[str] = None
    hints_used: int = 0
    total_time_minutes: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "user_id": self.user_id,
            "current_path": self.current_path,
            "current_step_index": self.current_step_index,
            "session_status": self.session_status.value,
            "completed_steps": self.completed_steps,
            "completed_paths": self.completed_paths,
            "achievements": self.achievements,
            "total_xp": self.total_xp,
            "streak_days": self.streak_days,
            "last_session_date": self.last_session_date,
            "tech_stack": self.tech_stack,
            "skill_levels": self.skill_levels,
            "preferences": self.preferences,
            "session_started_at": self.session_started_at,
            "hints_used": self.hints_used,
            "total_time_minutes": self.total_time_minutes,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# LEARNING PATHS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

def _create_fundamentals_path() -> LearningPath:
    """Create the SLATE Fundamentals learning path."""
    steps = [
        LearningStep(
            id="fund-01-welcome",
            title="Welcome to SLATE",
            description="Understand what SLATE is and how it transforms your development workflow.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=1,
            ai_explanation_prompt="Explain SLATE (Synchronized Living Architecture for Transformation and Evolution) in simple terms. Focus on how it combines AI, GPU acceleration, and automation.",
            hints=["SLATE stands for Synchronized Living Architecture for Transformation and Evolution"],
            estimated_minutes=3,
            xp_reward=25,
        ),
        LearningStep(
            id="fund-02-dashboard",
            title="The SLATE Dashboard",
            description="Learn to navigate the SLATE dashboard and understand its key sections.",
            category=StepCategory.EXPLORE,
            path_id="slate-fundamentals",
            order=2,
            prerequisites=["fund-01-welcome"],
            ai_explanation_prompt="Explain the main sections of the SLATE dashboard: system status, workflow pipeline, service controls, and activity feed.",
            action_command="slate/slate_status.py --quick",
            hints=["The dashboard shows real-time status of all SLATE services"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-03-services",
            title="Understanding Services",
            description="Learn about the core services: Dashboard, Ollama, Runner, GPU Manager.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=3,
            prerequisites=["fund-02-dashboard"],
            ai_explanation_prompt="Explain each SLATE service: Dashboard server (FastAPI on 8080), Ollama (local LLM on 11434), GitHub Runner, and GPU Manager. What does each do?",
            hints=["Each service has a specific port and purpose"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-04-start-services",
            title="Starting Services",
            description="Practice starting and stopping SLATE services using the orchestrator.",
            category=StepCategory.HANDS_ON,
            path_id="slate-fundamentals",
            order=4,
            prerequisites=["fund-03-services"],
            action_command="slate/slate_orchestrator.py status",
            success_criteria={"command_ran": True},
            hints=["Use 'start' to launch services, 'status' to check them"],
            estimated_minutes=5,
            xp_reward=75,
            achievement_trigger="first_command",
        ),
        LearningStep(
            id="fund-05-task-queue",
            title="The Task Queue",
            description="Understand how tasks flow through SLATE's workflow system.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=5,
            prerequisites=["fund-04-start-services"],
            ai_explanation_prompt="Explain the SLATE task queue system. How do tasks move from pending to in-progress to complete? What is current_tasks.json?",
            hints=["Tasks are stored in current_tasks.json with FileLock for safety"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-06-workflow-pipeline",
            title="Workflow Pipeline",
            description="Learn how tasks connect to GitHub Actions workflows.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=6,
            prerequisites=["fund-05-task-queue"],
            ai_explanation_prompt="Explain how SLATE connects to GitHub Actions: task queue -> runner pickup -> workflow execution -> validation -> completion.",
            hints=["The self-hosted runner executes workflows locally"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-07-check-workflow",
            title="Checking Workflow Status",
            description="Practice checking the workflow pipeline status.",
            category=StepCategory.HANDS_ON,
            path_id="slate-fundamentals",
            order=7,
            prerequisites=["fund-06-workflow-pipeline"],
            action_command="slate/slate_workflow_manager.py --status",
            hints=["The workflow manager shows pending, in-progress, and completed tasks"],
            estimated_minutes=5,
            xp_reward=75,
        ),
        LearningStep(
            id="fund-08-security",
            title="Security Architecture",
            description="Understand SLATE's security layers: ActionGuard, PII Scanner, SDK Guard.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=8,
            prerequisites=["fund-07-check-workflow"],
            ai_explanation_prompt="Explain SLATE's security architecture: ActionGuard blocks dangerous commands, PII Scanner detects credentials, SDK Source Guard ensures trusted packages.",
            hints=["All servers bind to 127.0.0.1 only - localhost security"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-09-security-scan",
            title="Running a Security Scan",
            description="Practice running a security audit on the codebase.",
            category=StepCategory.HANDS_ON,
            path_id="slate-fundamentals",
            order=9,
            prerequisites=["fund-08-security"],
            action_command="slate/action_guard.py --scan",
            hints=["Security scans help identify potential vulnerabilities"],
            estimated_minutes=5,
            xp_reward=75,
            achievement_trigger="security_scan",
        ),
        LearningStep(
            id="fund-10-development-cycle",
            title="The Development Cycle",
            description="Learn about SLATE's 5-stage development cycle: Plan -> Code -> Test -> Deploy -> Feedback.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=10,
            prerequisites=["fund-09-security-scan"],
            ai_explanation_prompt="Explain the 5 stages of SLATE's development cycle and how they connect to form a continuous improvement loop.",
            hints=["Each stage has associated integrations and activities"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="fund-11-quiz",
            title="Fundamentals Quiz",
            description="Test your understanding of SLATE fundamentals.",
            category=StepCategory.QUIZ,
            path_id="slate-fundamentals",
            order=11,
            prerequisites=["fund-10-development-cycle"],
            success_criteria={"quiz_passed": True},
            hints=["Review the previous steps if you're unsure"],
            estimated_minutes=5,
            xp_reward=100,
        ),
        LearningStep(
            id="fund-12-complete",
            title="Fundamentals Complete!",
            description="Congratulations! You've completed the SLATE Fundamentals path.",
            category=StepCategory.CONCEPT,
            path_id="slate-fundamentals",
            order=12,
            prerequisites=["fund-11-quiz"],
            ai_explanation_prompt="Congratulate the user on completing SLATE Fundamentals. Suggest next learning paths based on their interests.",
            estimated_minutes=2,
            xp_reward=200,
            achievement_trigger="complete_path:slate-fundamentals",
        ),
    ]

    return LearningPath(
        id="slate-fundamentals",
        name="SLATE Fundamentals",
        description="Master the core concepts of SLATE: services, workflows, security, and the development cycle.",
        icon="📚",
        difficulty="beginner",
        steps=steps,
        estimated_hours=1.0,
        tags=["core", "beginner", "essential"],
    )


def _create_ai_integration_path() -> LearningPath:
    """Create the AI Integration learning path."""
    steps = [
        LearningStep(
            id="ai-01-overview",
            title="AI in SLATE",
            description="Understand how SLATE integrates AI at every level.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=1,
            ai_explanation_prompt="Explain the AI capabilities in SLATE: Ollama for local inference, Claude Code integration, AI-powered code review, and autonomous task execution.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="ai-02-ollama",
            title="Ollama: Local LLMs",
            description="Learn about Ollama and running AI models locally.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=2,
            prerequisites=["ai-01-overview"],
            ai_explanation_prompt="Explain Ollama: what it is, why local AI matters (privacy, cost, speed), and the models SLATE uses (mistral-nemo, phi).",
            hints=["Ollama runs on port 11434 by default"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="ai-03-check-ollama",
            title="Checking Ollama Status",
            description="Practice checking if Ollama is running and what models are available.",
            category=StepCategory.HANDS_ON,
            path_id="ai-integration",
            order=3,
            prerequisites=["ai-02-ollama"],
            action_command="slate/foundry_local.py --check",
            hints=["Ollama should show 'running' with available models"],
            estimated_minutes=5,
            xp_reward=75,
        ),
        LearningStep(
            id="ai-04-claude-code",
            title="Claude Code Integration",
            description="Learn how SLATE integrates with Claude Code via MCP.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=4,
            prerequisites=["ai-03-check-ollama"],
            ai_explanation_prompt="Explain Claude Code integration in SLATE: MCP server, slash commands, hooks system, and the @slate chat participant in VSCode.",
            hints=["MCP = Model Context Protocol"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="ai-05-validate-claude",
            title="Validating Claude Code",
            description="Practice validating your Claude Code configuration.",
            category=StepCategory.HANDS_ON,
            path_id="ai-integration",
            order=5,
            prerequisites=["ai-04-claude-code"],
            action_command="slate/claude_code_manager.py --validate",
            hints=["Validation checks settings, MCP servers, and security integration"],
            estimated_minutes=5,
            xp_reward=75,
            achievement_trigger="claude_validated",
        ),
        LearningStep(
            id="ai-06-autonomous",
            title="Autonomous Task Execution",
            description="Learn how SLATE can autonomously execute tasks using AI.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=6,
            prerequisites=["ai-05-validate-claude"],
            ai_explanation_prompt="Explain SLATE's autonomous task execution: task discovery, agent routing (ALPHA/BETA/COPILOT_CHAT), and the unified autonomous loop.",
            hints=["The autonomous loop can discover and execute tasks without human intervention"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="ai-07-discover-tasks",
            title="Discovering Tasks",
            description="Practice using the autonomous system to discover available tasks.",
            category=StepCategory.HANDS_ON,
            path_id="ai-integration",
            order=7,
            prerequisites=["ai-06-autonomous"],
            action_command="slate/slate_unified_autonomous.py --discover",
            hints=["Tasks can come from the queue, GitHub issues, or codebase analysis"],
            estimated_minutes=5,
            xp_reward=75,
        ),
        LearningStep(
            id="ai-08-feedback-loop",
            title="The AI Feedback Loop",
            description="Learn how SLATE learns from AI operations to improve over time.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=8,
            prerequisites=["ai-07-discover-tasks"],
            ai_explanation_prompt="Explain the feedback loop: tool event recording, pattern recognition, insight generation, and how SLATE adapts based on successful operations.",
            hints=["The feedback layer tracks tool usage patterns"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="ai-09-complete",
            title="AI Integration Complete!",
            description="You've mastered SLATE's AI integration capabilities.",
            category=StepCategory.CONCEPT,
            path_id="ai-integration",
            order=9,
            prerequisites=["ai-08-feedback-loop"],
            estimated_minutes=2,
            xp_reward=200,
            achievement_trigger="complete_path:ai-integration",
        ),
    ]

    return LearningPath(
        id="ai-integration",
        name="AI Integration",
        description="Master SLATE's AI capabilities: Ollama, Claude Code, autonomous execution, and the feedback loop.",
        icon="🧠",
        difficulty="intermediate",
        steps=steps,
        estimated_hours=0.75,
        prerequisites=["slate-fundamentals"],
        tags=["ai", "ollama", "claude", "autonomous"],
    )


def _create_workflow_mastery_path() -> LearningPath:
    """Create the Workflow Mastery learning path."""
    steps = [
        LearningStep(
            id="wf-01-github-actions",
            title="GitHub Actions in SLATE",
            description="Understand how SLATE uses GitHub Actions for task execution.",
            category=StepCategory.CONCEPT,
            path_id="workflow-mastery",
            order=1,
            ai_explanation_prompt="Explain GitHub Actions integration in SLATE: self-hosted runner, workflow files, and how they connect to the task queue.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="wf-02-runner",
            title="The Self-Hosted Runner",
            description="Learn about the slate-runner and its capabilities.",
            category=StepCategory.CONCEPT,
            path_id="workflow-mastery",
            order=2,
            prerequisites=["wf-01-github-actions"],
            ai_explanation_prompt="Explain the SLATE self-hosted runner: labels (gpu, cuda, blackwell), pre-job hooks, GPU access, and security considerations.",
            hints=["The runner has labels like 'self-hosted', 'slate', 'gpu', 'cuda'"],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="wf-03-check-runner",
            title="Checking Runner Status",
            description="Practice checking the GitHub Actions runner status.",
            category=StepCategory.HANDS_ON,
            path_id="workflow-mastery",
            order=3,
            prerequisites=["wf-02-runner"],
            action_command="slate/slate_runner_manager.py --status",
            hints=["The runner should show 'online' or 'idle' when ready"],
            estimated_minutes=5,
            xp_reward=75,
        ),
        LearningStep(
            id="wf-04-workflows",
            title="SLATE Workflow Files",
            description="Explore the key workflow files in .github/workflows/",
            category=StepCategory.EXPLORE,
            path_id="workflow-mastery",
            order=4,
            prerequisites=["wf-03-check-runner"],
            ai_explanation_prompt="Explain the main SLATE workflows: ci.yml, nightly.yml, ai-maintenance.yml, agentic.yml, and their purposes.",
            hints=["Workflow files define what happens when triggers fire"],
            estimated_minutes=10,
            xp_reward=75,
        ),
        LearningStep(
            id="wf-05-dispatch",
            title="Dispatching Workflows",
            description="Learn how to manually dispatch workflows.",
            category=StepCategory.HANDS_ON,
            path_id="workflow-mastery",
            order=5,
            prerequisites=["wf-04-workflows"],
            action_command="slate/slate_runner_manager.py --status",
            hints=["Use --dispatch to trigger a workflow"],
            estimated_minutes=5,
            xp_reward=75,
        ),
        LearningStep(
            id="wf-06-cicd",
            title="CI/CD Best Practices",
            description="Learn CI/CD best practices with SLATE.",
            category=StepCategory.CONCEPT,
            path_id="workflow-mastery",
            order=6,
            prerequisites=["wf-05-dispatch"],
            ai_explanation_prompt="Explain CI/CD best practices in SLATE: test before merge, security scanning, multi-stage deployment, and monitoring.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="wf-07-complete",
            title="Workflow Mastery Complete!",
            description="You've mastered SLATE's workflow system.",
            category=StepCategory.CONCEPT,
            path_id="workflow-mastery",
            order=7,
            prerequisites=["wf-06-cicd"],
            estimated_minutes=2,
            xp_reward=200,
            achievement_trigger="complete_path:workflow-mastery",
        ),
    ]

    return LearningPath(
        id="workflow-mastery",
        name="Workflow Mastery",
        description="Master GitHub Actions, CI/CD, and the SLATE workflow system.",
        icon="🔄",
        difficulty="intermediate",
        steps=steps,
        estimated_hours=0.75,
        prerequisites=["slate-fundamentals"],
        tags=["github", "cicd", "workflows", "runner"],
    )


def _create_gpu_optimization_path() -> LearningPath:
    """Create the GPU Optimization learning path."""
    steps = [
        LearningStep(
            id="gpu-01-overview",
            title="Dual-GPU Architecture",
            description="Understand SLATE's dual-GPU setup and capabilities.",
            category=StepCategory.CONCEPT,
            path_id="gpu-optimization",
            order=1,
            ai_explanation_prompt="Explain SLATE's dual RTX 5070 Ti setup: Blackwell architecture, compute capability 12.0, 16GB VRAM each, and why this matters for AI inference.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="gpu-02-check-gpu",
            title="Checking GPU Status",
            description="Learn to check GPU utilization and health.",
            category=StepCategory.HANDS_ON,
            path_id="gpu-optimization",
            order=2,
            prerequisites=["gpu-01-overview"],
            action_command="slate/slate_gpu_manager.py --status",
            hints=["GPU status shows utilization, memory, and temperature"],
            estimated_minutes=5,
            xp_reward=75,
            achievement_trigger="gpu_check",
        ),
        LearningStep(
            id="gpu-03-load-balancing",
            title="GPU Load Balancing",
            description="Learn how SLATE balances work across multiple GPUs.",
            category=StepCategory.CONCEPT,
            path_id="gpu-optimization",
            order=3,
            prerequisites=["gpu-02-check-gpu"],
            ai_explanation_prompt="Explain GPU load balancing in SLATE: how models are distributed, memory management, and optimal task placement.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="gpu-04-benchmarks",
            title="Running Benchmarks",
            description="Practice running GPU benchmarks to measure performance.",
            category=StepCategory.HANDS_ON,
            path_id="gpu-optimization",
            order=4,
            prerequisites=["gpu-03-load-balancing"],
            action_command="slate/slate_benchmark.py",
            hints=["Benchmarks measure inference speed, memory bandwidth, and efficiency"],
            estimated_minutes=10,
            xp_reward=100,
            achievement_trigger="benchmark_run",
        ),
        LearningStep(
            id="gpu-05-optimization",
            title="Optimization Techniques",
            description="Learn techniques to optimize GPU utilization.",
            category=StepCategory.CONCEPT,
            path_id="gpu-optimization",
            order=5,
            prerequisites=["gpu-04-benchmarks"],
            ai_explanation_prompt="Explain GPU optimization techniques: batch sizing, model quantization, memory pooling, and keeping models warm.",
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="gpu-06-complete",
            title="GPU Optimization Complete!",
            description="You've mastered SLATE's GPU optimization.",
            category=StepCategory.CONCEPT,
            path_id="gpu-optimization",
            order=6,
            prerequisites=["gpu-05-optimization"],
            estimated_minutes=2,
            xp_reward=200,
            achievement_trigger="complete_path:gpu-optimization",
        ),
    ]

    return LearningPath(
        id="gpu-optimization",
        name="GPU Optimization",
        description="Master dual-GPU utilization, benchmarking, and performance optimization.",
        icon="⚡",
        difficulty="advanced",
        steps=steps,
        estimated_hours=0.5,
        prerequisites=["slate-fundamentals"],
        tags=["gpu", "cuda", "performance", "optimization"],
    )


def _create_github_mastery_path() -> LearningPath:
    """Create the GitHub Mastery learning path for earning GitHub achievements."""
    steps = [
        LearningStep(
            id="gh-01-achievements",
            title="GitHub Achievement System",
            description="Learn about GitHub's achievement system and how to earn badges.",
            category=StepCategory.CONCEPT,
            path_id="github-mastery",
            order=1,
            ai_explanation_prompt="Explain GitHub achievements: Pull Shark, YOLO, Quickdraw, Galaxy Brain, Pair Extraordinaire, Starstruck. How are they earned and what tiers exist?",
            hints=[
                "GitHub awards achievements for various contributions",
                "Achievements have tiers: Bronze, Silver, Gold, Platinum",
                "Check your profile to see earned achievements",
            ],
            estimated_minutes=5,
            xp_reward=50,
        ),
        LearningStep(
            id="gh-02-first-pr",
            title="Create Your First Pull Request",
            description="Open a PR and start your journey to Pull Shark.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=2,
            prerequisites=["gh-01-achievements"],
            action_command="gh pr create --fill",
            hints=[
                "Use 'gh pr create' or the GitHub web interface",
                "Write a clear title and description",
                "Reference any related issues with 'Closes #123'",
            ],
            estimated_minutes=10,
            xp_reward=75,
            achievement_trigger="first_pr",
        ),
        LearningStep(
            id="gh-03-co-author",
            title="Co-Author Commits",
            description="Learn to co-author commits for Pair Extraordinaire.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=3,
            prerequisites=["gh-02-first-pr"],
            hints=[
                "Add 'Co-authored-by: Name <email>' to commit messages",
                "SLATE uses: Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>",
                "Both authors get credit for the commit",
            ],
            estimated_minutes=5,
            xp_reward=75,
            achievement_trigger="pair_extraordinaire",
        ),
        LearningStep(
            id="gh-04-review-pr",
            title="Review Pull Requests",
            description="Start earning Code Reviewer by reviewing others' work.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=4,
            prerequisites=["gh-03-co-author"],
            action_command="gh pr list --state open",
            hints=[
                "Look for PRs needing review",
                "Check code quality and tests",
                "Leave constructive feedback",
                "Approve or request changes",
            ],
            estimated_minutes=10,
            xp_reward=75,
            achievement_trigger="code_reviewer",
        ),
        LearningStep(
            id="gh-05-close-issue",
            title="Close Issues with PRs",
            description="Reference and close issues automatically for Issue Closer.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=5,
            prerequisites=["gh-04-review-pr"],
            hints=[
                "Use 'Closes #123' or 'Fixes #123' in PR description",
                "The issue closes automatically when PR is merged",
                "Multiple issues can be closed in one PR",
            ],
            estimated_minutes=10,
            xp_reward=100,
            achievement_trigger="issue_closer",
        ),
        LearningStep(
            id="gh-06-release",
            title="Create GitHub Releases",
            description="Package and release your work for Release Maker.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=6,
            prerequisites=["gh-05-close-issue"],
            action_command="gh release list",
            hints=[
                "Tag your code with semantic versioning (v1.0.0)",
                "Write comprehensive release notes",
                "Attach build artifacts if applicable",
            ],
            estimated_minutes=10,
            xp_reward=100,
            achievement_trigger="release_maker",
        ),
        LearningStep(
            id="gh-07-ci-success",
            title="Master CI/CD Workflows",
            description="Achieve successful CI runs for CI Master.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=7,
            prerequisites=["gh-06-release"],
            action_command="gh run list --status success",
            hints=[
                "Create .github/workflows/*.yml files",
                "Set up automated testing",
                "Fix failing tests to get green builds",
            ],
            estimated_minutes=15,
            xp_reward=125,
            achievement_trigger="ci_master",
        ),
        LearningStep(
            id="gh-08-discussions",
            title="Engage in Discussions",
            description="Answer questions to earn Galaxy Brain.",
            category=StepCategory.HANDS_ON,
            path_id="github-mastery",
            order=8,
            prerequisites=["gh-07-ci-success"],
            hints=[
                "Find discussions in repositories you know well",
                "Provide detailed, helpful answers",
                "Follow up to ensure the solution works",
            ],
            estimated_minutes=15,
            xp_reward=100,
            achievement_trigger="galaxy_brain",
        ),
        LearningStep(
            id="gh-09-sponsor",
            title="Support Open Source",
            description="Become a Public Sponsor of open source.",
            category=StepCategory.EXPLORE,
            path_id="github-mastery",
            order=9,
            prerequisites=["gh-08-discussions"],
            hints=[
                "Find a project you use and appreciate",
                "Check if they have GitHub Sponsors enabled",
                "Choose a tier that works for you",
            ],
            estimated_minutes=10,
            xp_reward=100,
            achievement_trigger="public_sponsor",
        ),
        LearningStep(
            id="gh-10-complete",
            title="GitHub Mastery Complete!",
            description="You've mastered GitHub contributions and achievements.",
            category=StepCategory.CONCEPT,
            path_id="github-mastery",
            order=10,
            prerequisites=["gh-09-sponsor"],
            estimated_minutes=2,
            xp_reward=300,
            achievement_trigger="complete_path:github-mastery",
        ),
    ]

    return LearningPath(
        id="github-mastery",
        name="GitHub Mastery",
        description="Master GitHub contributions and earn achievement badges like Pull Shark, Galaxy Brain, and more.",
        icon="🐙",
        difficulty="intermediate",
        steps=steps,
        estimated_hours=1.5,
        prerequisites=["slate-fundamentals"],
        tags=["github", "achievements", "contributions", "community"],
    )


# Create all paths
LEARNING_PATHS: Dict[str, LearningPath] = {
    "slate-fundamentals": _create_fundamentals_path(),
    "ai-integration": _create_ai_integration_path(),
    "workflow-mastery": _create_workflow_mastery_path(),
    "gpu-optimization": _create_gpu_optimization_path(),
    "github-mastery": _create_github_mastery_path(),
}


# ═══════════════════════════════════════════════════════════════════════════════
# ACHIEVEMENTS DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

ACHIEVEMENTS: Dict[str, Achievement] = {
    # Beginner
    "first_step": Achievement(
        id="first_step",
        name="First Steps",
        description="Complete your first learning step",
        icon="👣",
        category=AchievementCategory.BEGINNER,
        trigger_condition="complete_1_step",
        xp_reward=50,
    ),
    "first_command": Achievement(
        id="first_command",
        name="Command Line Hero",
        description="Run your first SLATE command",
        icon="⌨️",
        category=AchievementCategory.BEGINNER,
        trigger_condition="first_command",
        xp_reward=75,
    ),
    "streak_3": Achievement(
        id="streak_3",
        name="Consistent Learner",
        description="Maintain a 3-day learning streak",
        icon="🔥",
        category=AchievementCategory.BEGINNER,
        trigger_condition="streak_3",
        xp_reward=100,
    ),

    # Intermediate
    "complete_path:slate-fundamentals": Achievement(
        id="complete_path:slate-fundamentals",
        name="SLATE Graduate",
        description="Complete the SLATE Fundamentals path",
        icon="🎓",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="complete_path:slate-fundamentals",
        xp_reward=250,
    ),
    "security_scan": Achievement(
        id="security_scan",
        name="Security Guardian",
        description="Run your first security scan",
        icon="🛡️",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="security_scan",
        xp_reward=100,
    ),
    "claude_validated": Achievement(
        id="claude_validated",
        name="AI Connected",
        description="Successfully validate Claude Code integration",
        icon="🤖",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="claude_validated",
        xp_reward=100,
    ),
    "streak_7": Achievement(
        id="streak_7",
        name="Week Warrior",
        description="Maintain a 7-day learning streak",
        icon="🗓️",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="streak_7",
        xp_reward=200,
    ),

    # Advanced
    "complete_path:ai-integration": Achievement(
        id="complete_path:ai-integration",
        name="AI Master",
        description="Complete the AI Integration path",
        icon="🧠",
        category=AchievementCategory.ADVANCED,
        trigger_condition="complete_path:ai-integration",
        xp_reward=300,
    ),
    "complete_path:workflow-mastery": Achievement(
        id="complete_path:workflow-mastery",
        name="Workflow Wizard",
        description="Complete the Workflow Mastery path",
        icon="🔄",
        category=AchievementCategory.ADVANCED,
        trigger_condition="complete_path:workflow-mastery",
        xp_reward=300,
    ),
    "gpu_check": Achievement(
        id="gpu_check",
        name="GPU Discoverer",
        description="Check your GPU status for the first time",
        icon="💻",
        category=AchievementCategory.ADVANCED,
        trigger_condition="gpu_check",
        xp_reward=100,
    ),
    "benchmark_run": Achievement(
        id="benchmark_run",
        name="Benchmark Champion",
        description="Run a full GPU benchmark",
        icon="📊",
        category=AchievementCategory.ADVANCED,
        trigger_condition="benchmark_run",
        xp_reward=150,
    ),

    # Mastery
    "complete_path:gpu-optimization": Achievement(
        id="complete_path:gpu-optimization",
        name="Performance Guru",
        description="Complete the GPU Optimization path",
        icon="⚡",
        category=AchievementCategory.MASTERY,
        trigger_condition="complete_path:gpu-optimization",
        xp_reward=400,
    ),
    "all_paths": Achievement(
        id="all_paths",
        name="SLATE Master",
        description="Complete all learning paths",
        icon="🏆",
        category=AchievementCategory.MASTERY,
        trigger_condition="all_paths",
        xp_reward=1000,
    ),
    "streak_30": Achievement(
        id="streak_30",
        name="Monthly Dedication",
        description="Maintain a 30-day learning streak",
        icon="💎",
        category=AchievementCategory.MASTERY,
        trigger_condition="streak_30",
        xp_reward=500,
    ),

    # GitHub Achievements (maps to real GitHub badges)
    "first_pr": Achievement(
        id="first_pr",
        name="First Pull Request",
        description="Create your first pull request",
        icon="🦈",
        category=AchievementCategory.BEGINNER,
        trigger_condition="first_pr",
        xp_reward=100,
    ),
    "pair_extraordinaire": Achievement(
        id="pair_extraordinaire",
        name="Pair Extraordinaire",
        description="Create a co-authored commit",
        icon="👥",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="pair_extraordinaire",
        xp_reward=100,
    ),
    "code_reviewer": Achievement(
        id="code_reviewer",
        name="Code Reviewer",
        description="Review a pull request",
        icon="👀",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="code_reviewer",
        xp_reward=100,
    ),
    "issue_closer": Achievement(
        id="issue_closer",
        name="Issue Closer",
        description="Close an issue via PR reference",
        icon="🎯",
        category=AchievementCategory.INTERMEDIATE,
        trigger_condition="issue_closer",
        xp_reward=100,
    ),
    "release_maker": Achievement(
        id="release_maker",
        name="Release Maker",
        description="Create a GitHub release",
        icon="📦",
        category=AchievementCategory.ADVANCED,
        trigger_condition="release_maker",
        xp_reward=150,
    ),
    "ci_master": Achievement(
        id="ci_master",
        name="CI Master",
        description="Achieve successful CI workflow runs",
        icon="✅",
        category=AchievementCategory.ADVANCED,
        trigger_condition="ci_master",
        xp_reward=150,
    ),
    "galaxy_brain": Achievement(
        id="galaxy_brain",
        name="Galaxy Brain",
        description="Get a discussion answer marked as accepted",
        icon="🧠",
        category=AchievementCategory.ADVANCED,
        trigger_condition="galaxy_brain",
        xp_reward=150,
    ),
    "public_sponsor": Achievement(
        id="public_sponsor",
        name="Public Sponsor",
        description="Sponsor an open source project",
        icon="💖",
        category=AchievementCategory.MASTERY,
        trigger_condition="public_sponsor",
        xp_reward=200,
    ),
    "complete_path:github-mastery": Achievement(
        id="complete_path:github-mastery",
        name="GitHub Champion",
        description="Complete the GitHub Mastery path",
        icon="🐙",
        category=AchievementCategory.MASTERY,
        trigger_condition="complete_path:github-mastery",
        xp_reward=400,
    ),
}


# ═══════════════════════════════════════════════════════════════════════════════
# INTERACTIVE TUTOR ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class InteractiveTutor:
    """
    AI-driven interactive learning engine.

    Features:
    - Multiple learning paths with progressive steps
    - Achievement system with unlockable badges
    - XP and streak tracking
    - AI-generated explanations via Ollama
    - Personalized recommendations
    """

    PROGRESS_FILE = ".slate_identity/learning_progress.json"
    OLLAMA_URL = "http://localhost:11434/api/generate"

    def __init__(
        self,
        workspace: Optional[Path] = None,
        broadcast_callback: Optional[Callable] = None,
    ):
        self.workspace = workspace or WORKSPACE_ROOT
        self.progress_path = self.workspace / self.PROGRESS_FILE
        self.broadcast_callback = broadcast_callback
        self._progress: Optional[LearningProgress] = None
        self._lock = FileLock(str(self.progress_path) + ".lock")

    def _ensure_dir(self) -> None:
        """Ensure progress directory exists."""
        self.progress_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_progress(self) -> LearningProgress:
        """Load progress from file."""
        self._ensure_dir()

        if self.progress_path.exists():
            try:
                with open(self.progress_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return LearningProgress(
                    user_id=data.get("user_id", "local-user"),
                    current_path=data.get("current_path"),
                    current_step_index=data.get("current_step_index", 0),
                    session_status=SessionStatus(data.get("session_status", "inactive")),
                    completed_steps=data.get("completed_steps", []),
                    completed_paths=data.get("completed_paths", []),
                    achievements=data.get("achievements", []),
                    total_xp=data.get("total_xp", 0),
                    streak_days=data.get("streak_days", 0),
                    last_session_date=data.get("last_session_date"),
                    tech_stack=data.get("tech_stack", []),
                    skill_levels=data.get("skill_levels", {}),
                    preferences=data.get("preferences", {}),
                    session_started_at=data.get("session_started_at"),
                    hints_used=data.get("hints_used", 0),
                    total_time_minutes=data.get("total_time_minutes", 0),
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Error loading progress, creating fresh: {e}")

        return LearningProgress()

    def _save_progress(self) -> None:
        """Save progress to file."""
        if self._progress is None:
            return

        self._ensure_dir()
        with self._lock:
            with open(self.progress_path, "w", encoding="utf-8") as f:
                json.dump(self._progress.to_dict(), f, indent=2)

    @property
    def progress(self) -> LearningProgress:
        """Get current progress."""
        if self._progress is None:
            self._progress = self._load_progress()
        return self._progress

    async def _broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcast event."""
        if self.broadcast_callback:
            try:
                await self.broadcast_callback({
                    "type": event_type,
                    "payload": payload,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    # ─── Learning Paths ───────────────────────────────────────────────────────

    def get_available_paths(self) -> List[Dict[str, Any]]:
        """Get all available learning paths with progress info."""
        paths = []
        for path in LEARNING_PATHS.values():
            completed_steps = sum(
                1 for step in path.steps
                if step.id in self.progress.completed_steps
            )
            paths.append({
                **path.to_dict(),
                "completed_steps": completed_steps,
                "progress_percent": round(completed_steps / len(path.steps) * 100),
                "is_completed": path.id in self.progress.completed_paths,
                "is_current": path.id == self.progress.current_path,
                "unlocked": all(
                    prereq in self.progress.completed_paths
                    for prereq in path.prerequisites
                ),
            })
        return paths

    def get_learning_paths(self) -> List[Dict[str, Any]]:
        """Alias for get_available_paths for backwards compatibility."""
        return self.get_available_paths()

    def get_path(self, path_id: str) -> Optional[LearningPath]:
        """Get a learning path by ID."""
        return LEARNING_PATHS.get(path_id)

    # ─── Session Management ───────────────────────────────────────────────────

    async def start_learning_session(self, path_id: str) -> Dict[str, Any]:
        """Start a new learning session."""
        path = LEARNING_PATHS.get(path_id)
        if not path:
            return {"success": False, "error": f"Path not found: {path_id}"}

        # Check prerequisites
        for prereq in path.prerequisites:
            if prereq not in self.progress.completed_paths:
                return {
                    "success": False,
                    "error": f"Prerequisite not met: {prereq}",
                    "missing_prerequisite": prereq,
                }

        # Update streak
        today = datetime.now(timezone.utc).date().isoformat()
        if self.progress.last_session_date:
            last = datetime.fromisoformat(self.progress.last_session_date).date()
            diff = (datetime.now(timezone.utc).date() - last).days
            if diff == 1:
                self.progress.streak_days += 1
            elif diff > 1:
                self.progress.streak_days = 1
        else:
            self.progress.streak_days = 1

        # Find starting step
        start_index = 0
        for i, step in enumerate(path.steps):
            if step.id not in self.progress.completed_steps:
                start_index = i
                break

        self.progress.current_path = path_id
        self.progress.current_step_index = start_index
        self.progress.session_status = SessionStatus.ACTIVE
        self.progress.session_started_at = datetime.now(timezone.utc).isoformat()
        self.progress.last_session_date = today
        self._save_progress()

        # Check for streak achievements
        await self._check_streak_achievements()

        current_step = path.steps[start_index]

        await self._broadcast("learning_session_started", {
            "path_id": path_id,
            "path_name": path.name,
            "step_id": current_step.id,
            "step_title": current_step.title,
        })

        return {
            "success": True,
            "path": path.to_dict(),
            "current_step": current_step.to_dict(),
            "progress": self.progress.to_dict(),
        }

    async def pause_session(self) -> Dict[str, Any]:
        """Pause the current session."""
        if self.progress.session_status != SessionStatus.ACTIVE:
            return {"success": False, "error": "No active session"}

        self.progress.session_status = SessionStatus.PAUSED
        self._save_progress()

        return {"success": True, "status": "paused"}

    async def resume_session(self) -> Dict[str, Any]:
        """Resume a paused session."""
        if self.progress.session_status != SessionStatus.PAUSED:
            return {"success": False, "error": "No paused session"}

        self.progress.session_status = SessionStatus.ACTIVE
        self._save_progress()

        path = LEARNING_PATHS.get(self.progress.current_path)
        if path:
            current_step = path.steps[self.progress.current_step_index]
            return {
                "success": True,
                "current_step": current_step.to_dict(),
            }

        return {"success": True, "status": "resumed"}

    # ─── Steps ────────────────────────────────────────────────────────────────

    async def get_current_step(self) -> Optional[LearningStep]:
        """Get the current step in the active session."""
        if not self.progress.current_path:
            return None

        path = LEARNING_PATHS.get(self.progress.current_path)
        if not path:
            return None

        if self.progress.current_step_index >= len(path.steps):
            return None

        return path.steps[self.progress.current_step_index]

    async def get_next_step(self) -> Optional[LearningStep]:
        """Alias for get_current_step for backwards compatibility."""
        return await self.get_current_step()

    async def complete_step(
        self,
        step_id: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Complete a learning step."""
        if self.progress.session_status != SessionStatus.ACTIVE:
            return {"success": False, "error": "No active session"}

        path = LEARNING_PATHS.get(self.progress.current_path)
        if not path:
            return {"success": False, "error": "Path not found"}

        current_step = path.steps[self.progress.current_step_index]
        if current_step.id != step_id:
            return {"success": False, "error": "Step mismatch"}

        # Mark step complete
        if step_id not in self.progress.completed_steps:
            self.progress.completed_steps.append(step_id)

        # Award XP
        xp_earned = current_step.xp_reward
        self.progress.total_xp += xp_earned

        # Check for achievements
        unlocked = []
        if current_step.achievement_trigger:
            achievement = await self._unlock_achievement(current_step.achievement_trigger)
            if achievement:
                unlocked.append(achievement)

        # Check step count achievements
        step_count = len(self.progress.completed_steps)
        if step_count == 1:
            achievement = await self._unlock_achievement("complete_1_step")
            if achievement:
                unlocked.append(achievement)

        # Move to next step or complete path
        next_step = None
        path_completed = False

        if self.progress.current_step_index + 1 < len(path.steps):
            self.progress.current_step_index += 1
            next_step = path.steps[self.progress.current_step_index]
        else:
            # Path completed
            if path.id not in self.progress.completed_paths:
                self.progress.completed_paths.append(path.id)
            path_completed = True
            self.progress.session_status = SessionStatus.COMPLETED

            # Check all paths achievement
            if len(self.progress.completed_paths) == len(LEARNING_PATHS):
                achievement = await self._unlock_achievement("all_paths")
                if achievement:
                    unlocked.append(achievement)

        self._save_progress()

        await self._broadcast("learning_step_complete", {
            "step_id": step_id,
            "xp_earned": xp_earned,
            "total_xp": self.progress.total_xp,
            "achievements_unlocked": [a.to_dict() for a in unlocked],
            "path_completed": path_completed,
        })

        return {
            "success": True,
            "xp_earned": xp_earned,
            "total_xp": self.progress.total_xp,
            "achievements_unlocked": [a.to_dict() for a in unlocked],
            "next_step": next_step.to_dict() if next_step else None,
            "path_completed": path_completed,
        }

    async def get_hint(self, hint_index: int = 0) -> Optional[str]:
        """Get a hint for the current step."""
        step = await self.get_current_step()
        if not step or not step.hints:
            return None

        if hint_index >= len(step.hints):
            return None

        self.progress.hints_used += 1
        self._save_progress()

        return step.hints[hint_index]

    async def skip_step(self) -> Dict[str, Any]:
        """Skip the current step (no XP awarded)."""
        if self.progress.session_status != SessionStatus.ACTIVE:
            return {"success": False, "error": "No active session"}

        path = LEARNING_PATHS.get(self.progress.current_path)
        if not path:
            return {"success": False, "error": "Path not found"}

        current_step = path.steps[self.progress.current_step_index]

        # Mark as skipped (still counts as completed for progression)
        if current_step.id not in self.progress.completed_steps:
            self.progress.completed_steps.append(current_step.id)

        # Move to next step
        if self.progress.current_step_index + 1 < len(path.steps):
            self.progress.current_step_index += 1
            next_step = path.steps[self.progress.current_step_index]
            self._save_progress()
            return {
                "success": True,
                "skipped": current_step.id,
                "next_step": next_step.to_dict(),
            }
        else:
            self._save_progress()
            return {"success": True, "skipped": current_step.id, "path_completed": True}

    # ─── AI Explanations ──────────────────────────────────────────────────────

    async def get_ai_explanation(
        self,
        topic: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Get an AI-generated explanation for a topic."""
        step = await self.get_current_step()

        prompt = f"""You are SLATE's AI tutor. Explain the following topic in a friendly, educational way.

Topic: {topic}

Context:
- User is learning about SLATE (Synchronized Living Architecture for Transformation and Evolution)
- Current learning path: {self.progress.current_path or 'general'}
- Current step: {step.title if step else 'None'}
- User's XP level: {self.progress.total_xp}

{step.ai_explanation_prompt if step and step.ai_explanation_prompt else ''}

Provide a clear, concise explanation (2-3 paragraphs max). Use examples where helpful.
Be encouraging and reference what they've already learned when relevant."""

        try:
            import httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    self.OLLAMA_URL,
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {
                            "temperature": 0.7,
                            "num_predict": 300,
                        },
                    },
                    timeout=30,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "Unable to generate explanation.")
        except Exception as e:
            logger.error(f"AI explanation error: {e}")

        # Fallback
        if step and step.ai_explanation_prompt:
            return f"Learn about {topic}: {step.description}"
        return f"Topic: {topic}\n\nPlease refer to the SLATE documentation for more information."

    # ─── Achievements ─────────────────────────────────────────────────────────

    async def _unlock_achievement(self, trigger: str) -> Optional[Achievement]:
        """Attempt to unlock an achievement."""
        if trigger in self.progress.achievements:
            return None  # Already unlocked

        achievement = ACHIEVEMENTS.get(trigger)
        if not achievement:
            return None

        achievement.unlocked_at = datetime.now(timezone.utc).isoformat()
        self.progress.achievements.append(trigger)
        self.progress.total_xp += achievement.xp_reward
        self._save_progress()

        await self._broadcast("achievement_unlocked", {
            "achievement": achievement.to_dict(),
            "xp_reward": achievement.xp_reward,
        })

        return achievement

    async def _check_streak_achievements(self) -> List[Achievement]:
        """Check and unlock streak-based achievements."""
        unlocked = []
        streak = self.progress.streak_days

        if streak >= 3 and "streak_3" not in self.progress.achievements:
            achievement = await self._unlock_achievement("streak_3")
            if achievement:
                unlocked.append(achievement)

        if streak >= 7 and "streak_7" not in self.progress.achievements:
            achievement = await self._unlock_achievement("streak_7")
            if achievement:
                unlocked.append(achievement)

        if streak >= 30 and "streak_30" not in self.progress.achievements:
            achievement = await self._unlock_achievement("streak_30")
            if achievement:
                unlocked.append(achievement)

        return unlocked

    def get_achievements(self) -> List[Dict[str, Any]]:
        """Get all achievements with unlock status."""
        return [
            {
                **achievement.to_dict(),
                "unlocked": achievement.id in self.progress.achievements,
            }
            for achievement in ACHIEVEMENTS.values()
            if not achievement.hidden or achievement.id in self.progress.achievements
        ]

    def get_all_achievements(self) -> List[Dict[str, Any]]:
        """Alias for get_achievements for backwards compatibility."""
        return self.get_achievements()

    def get_progress(self) -> LearningProgress:
        """Get the current learning progress."""
        return self.progress

    # ─── Progress Summary ─────────────────────────────────────────────────────

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get a summary of learning progress."""
        total_steps = sum(len(p.steps) for p in LEARNING_PATHS.values())
        completed_steps = len(self.progress.completed_steps)

        return {
            **self.progress.to_dict(),
            "total_paths": len(LEARNING_PATHS),
            "completed_paths_count": len(self.progress.completed_paths),
            "total_steps": total_steps,
            "completed_steps_count": completed_steps,
            "overall_progress_percent": round(completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "total_achievements": len(ACHIEVEMENTS),
            "unlocked_achievements_count": len(self.progress.achievements),
            "level": self._calculate_level(),
        }

    def _calculate_level(self) -> Dict[str, Any]:
        """Calculate user level from XP."""
        xp = self.progress.total_xp
        level = 1
        xp_for_next = 100

        while xp >= xp_for_next:
            xp -= xp_for_next
            level += 1
            xp_for_next = int(xp_for_next * 1.5)

        return {
            "level": level,
            "xp_current": xp,
            "xp_for_next": xp_for_next,
            "progress_percent": round(xp / xp_for_next * 100),
        }

    def calculate_level(self, xp: Optional[int] = None) -> int:
        """Calculate level from XP. Public method for backwards compatibility."""
        if xp is None:
            return self._calculate_level()["level"]
        # Calculate level from given XP
        level = 1
        xp_for_next = 100
        remaining = xp
        while remaining >= xp_for_next:
            remaining -= xp_for_next
            level += 1
            xp_for_next = int(xp_for_next * 1.5)
        return level

    # ─── Tech Stack Detection ─────────────────────────────────────────────────

    async def detect_tech_stack(self) -> List[str]:
        """Detect the user's tech stack from the project."""
        tech_stack = []

        # Check for Python
        if (self.workspace / "requirements.txt").exists():
            tech_stack.append("python")

        # Check for TypeScript/JavaScript
        if (self.workspace / "package.json").exists():
            tech_stack.append("typescript")

        # Check for Docker
        if (self.workspace / "Dockerfile").exists():
            tech_stack.append("docker")

        # Check for FastAPI
        requirements = self.workspace / "requirements.txt"
        if requirements.exists():
            content = requirements.read_text()
            if "fastapi" in content.lower():
                tech_stack.append("fastapi")
            if "torch" in content.lower():
                tech_stack.append("pytorch")

        # Check for GitHub Actions
        if (self.workspace / ".github/workflows").exists():
            tech_stack.append("github-actions")

        self.progress.tech_stack = tech_stack
        self._save_progress()

        return tech_stack


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_tutor_instance: Optional[InteractiveTutor] = None


def get_tutor(
    workspace: Optional[Path] = None,
    broadcast_callback: Optional[Callable] = None,
) -> InteractiveTutor:
    """Get or create the singleton tutor instance."""
    global _tutor_instance
    if _tutor_instance is None:
        _tutor_instance = InteractiveTutor(workspace, broadcast_callback)
    return _tutor_instance


def reset_tutor() -> None:
    """Reset the tutor instance."""
    global _tutor_instance
    _tutor_instance = None


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Interactive Tutor")
    parser.add_argument("--paths", action="store_true", help="List learning paths")
    parser.add_argument("--start", metavar="PATH_ID", help="Start learning path")
    parser.add_argument("--status", action="store_true", help="Show current progress")
    parser.add_argument("--next", action="store_true", help="Get next learning step")
    parser.add_argument("--achievements", action="store_true", help="List achievements")
    parser.add_argument("--explain", metavar="TOPIC", help="Get AI explanation")
    parser.add_argument("--complete", metavar="STEP_ID", help="Complete current step")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    tutor = get_tutor()

    if args.paths:
        paths = tutor.get_available_paths()
        if args.json:
            print(json.dumps(paths, indent=2))
        else:
            print("Available Learning Paths:")
            print("-" * 50)
            for p in paths:
                status = "COMPLETED" if p["is_completed"] else (
                    f"{p['progress_percent']}%" if p["unlocked"] else "LOCKED"
                )
                print(f"  {p['icon']} {p['name']} [{status}]")
                print(f"     {p['description']}")
                print(f"     {p['step_count']} steps, ~{p['estimated_hours']}h")
                print()
        return

    if args.start:
        result = await tutor.start_learning_session(args.start)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Started: {result['path']['name']}")
                print(f"Current step: {result['current_step']['title']}")
            else:
                print(f"Error: {result.get('error')}")
        return

    if args.achievements:
        achievements = tutor.get_achievements()
        if args.json:
            print(json.dumps(achievements, indent=2))
        else:
            print("Achievements:")
            print("-" * 50)
            for a in achievements:
                status = "UNLOCKED" if a["unlocked"] else "locked"
                print(f"  {a['icon']} {a['name']} [{status}]")
                print(f"     {a['description']}")
                print(f"     +{a['xp_reward']} XP")
                print()
        return

    if args.next:
        step = await tutor.get_current_step()
        if step:
            if args.json:
                print(json.dumps(step.to_dict(), indent=2))
            else:
                print("Next Learning Step:")
                print("-" * 50)
                print(f"  {step.title}")
                print(f"  Category: {step.category}")
                print(f"  {step.description}")
                if step.hints:
                    print(f"\n  Hints: {len(step.hints)} available")
        else:
            if args.json:
                print(json.dumps({"step": None, "message": "No active learning session"}, indent=2))
            else:
                print("No active learning session. Start one with --start <path_id>")
        return

    if args.explain:
        explanation = await tutor.get_ai_explanation(args.explain)
        print(explanation)
        return

    if args.complete:
        result = await tutor.complete_step(args.complete, {"success": True})
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Step completed! +{result['xp_earned']} XP")
                if result.get("achievements_unlocked"):
                    for a in result["achievements_unlocked"]:
                        print(f"  Achievement unlocked: {a['name']}!")
            else:
                print(f"Error: {result.get('error')}")
        return

    # Default: show status
    summary = tutor.get_progress_summary()
    if args.json:
        print(json.dumps(summary, indent=2))
    else:
        print("=" * 50)
        print("  SLATE Learning Progress")
        print("=" * 50)
        print(f"\n  Level {summary['level']['level']} ({summary['total_xp']} XP)")
        print(f"  Streak: {summary['streak_days']} days 🔥")
        print(f"\n  Paths: {summary['completed_paths_count']}/{summary['total_paths']}")
        print(f"  Steps: {summary['completed_steps_count']}/{summary['total_steps']}")
        print(f"  Achievements: {summary['unlocked_achievements_count']}/{summary['total_achievements']}")

        if summary["current_path"]:
            print(f"\n  Current path: {summary['current_path']}")

        print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
