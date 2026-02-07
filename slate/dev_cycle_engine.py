#!/usr/bin/env python3
# Modified: 2026-02-07T15:00:00Z | Author: CLAUDE | Change: Create development cycle state machine
"""
SLATE Development Cycle Engine
===============================
5-stage development cycle state machine with animated visualization support.

Stages: PLAN -> CODE -> TEST -> DEPLOY -> FEEDBACK -> (loop)

Features:
- Stage transitions with validation
- Activity tracking per stage
- Progress metrics and visualization data
- WebSocket event broadcasting
- Integration status per stage
- Cycle history and analytics

Usage:
    from slate.dev_cycle_engine import get_engine

    engine = get_engine()
    state = await engine.get_current_state()
    await engine.transition_stage(DevCycleStage.CODE)
    await engine.add_activity(activity)
"""

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
import uuid

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate_core.file_lock import FileLock

logger = logging.getLogger("slate.dev_cycle_engine")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

class DevCycleStage(Enum):
    """Development cycle stages."""
    PLAN = "plan"
    CODE = "code"
    TEST = "test"
    DEPLOY = "deploy"
    FEEDBACK = "feedback"


class ActivityStatus(Enum):
    """Activity status within a stage."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETE = "complete"
    BLOCKED = "blocked"
    SKIPPED = "skipped"


# Stage metadata for UI
STAGE_METADATA = {
    DevCycleStage.PLAN: {
        "icon": "📋",
        "color": "#7EA8BE",  # Steel blue
        "description": "Planning & Design",
        "integrations": ["github_issues", "specs", "roadmap"],
    },
    DevCycleStage.CODE: {
        "icon": "💻",
        "color": "#B87333",  # Copper (primary)
        "description": "Active Development",
        "integrations": ["ollama", "claude_code", "copilot"],
    },
    DevCycleStage.TEST: {
        "icon": "🧪",
        "color": "#78B89A",  # Sage green
        "description": "Testing & Validation",
        "integrations": ["pytest", "ci", "coverage"],
    },
    DevCycleStage.DEPLOY: {
        "icon": "🚀",
        "color": "#D4A054",  # Warm amber
        "description": "Build & Deployment",
        "integrations": ["docker", "runner", "releases"],
    },
    DevCycleStage.FEEDBACK: {
        "icon": "🔄",
        "color": "#C9956B",  # Light copper
        "description": "Review & Learning",
        "integrations": ["ai_review", "metrics", "insights"],
    },
}

# Valid stage transitions (can go forward or back one stage, or loop)
VALID_TRANSITIONS = {
    DevCycleStage.PLAN: [DevCycleStage.CODE, DevCycleStage.FEEDBACK],
    DevCycleStage.CODE: [DevCycleStage.TEST, DevCycleStage.PLAN],
    DevCycleStage.TEST: [DevCycleStage.DEPLOY, DevCycleStage.CODE],
    DevCycleStage.DEPLOY: [DevCycleStage.FEEDBACK, DevCycleStage.TEST],
    DevCycleStage.FEEDBACK: [DevCycleStage.PLAN, DevCycleStage.DEPLOY],
}


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class StageActivity:
    """An activity within a development stage."""
    id: str
    stage: DevCycleStage
    title: str
    description: str = ""
    status: ActivityStatus = ActivityStatus.PENDING
    progress_percent: int = 0
    created_at: str = ""
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    linked_tasks: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)

    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now(timezone.utc).isoformat()
        if isinstance(self.stage, str):
            self.stage = DevCycleStage(self.stage)
        if isinstance(self.status, str):
            self.status = ActivityStatus(self.status)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stage": self.stage.value,
            "title": self.title,
            "description": self.description,
            "status": self.status.value,
            "progress_percent": self.progress_percent,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metrics": self.metrics,
            "linked_tasks": self.linked_tasks,
            "tags": self.tags,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "StageActivity":
        return cls(
            id=data["id"],
            stage=DevCycleStage(data["stage"]),
            title=data["title"],
            description=data.get("description", ""),
            status=ActivityStatus(data.get("status", "pending")),
            progress_percent=data.get("progress_percent", 0),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            metrics=data.get("metrics", {}),
            linked_tasks=data.get("linked_tasks", []),
            tags=data.get("tags", []),
        )


@dataclass
class StageTransition:
    """Record of a stage transition."""
    from_stage: DevCycleStage
    to_stage: DevCycleStage
    timestamp: str
    reason: str = ""
    activities_completed: int = 0
    duration_seconds: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "from_stage": self.from_stage.value,
            "to_stage": self.to_stage.value,
            "timestamp": self.timestamp,
            "reason": self.reason,
            "activities_completed": self.activities_completed,
            "duration_seconds": self.duration_seconds,
        }


@dataclass
class IntegrationStatus:
    """Status of an integration within a stage."""
    name: str
    available: bool
    last_check: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DevCycleState:
    """Complete development cycle state."""
    current_stage: DevCycleStage
    current_iteration: str
    cycle_count: int
    stage_activities: Dict[str, List[StageActivity]]
    integrations: Dict[str, Dict[str, bool]]
    stage_history: List[StageTransition]
    stage_entered_at: str
    updated_at: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "current_stage": self.current_stage.value,
            "current_iteration": self.current_iteration,
            "cycle_count": self.cycle_count,
            "stage_activities": {
                stage: [a.to_dict() for a in activities]
                for stage, activities in self.stage_activities.items()
            },
            "integrations": self.integrations,
            "stage_history": [t.to_dict() for t in self.stage_history[-20:]],  # Keep last 20
            "stage_entered_at": self.stage_entered_at,
            "updated_at": self.updated_at,
        }


# ═══════════════════════════════════════════════════════════════════════════════
# DEV CYCLE ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class DevCycleEngine:
    """
    Development cycle state machine with visualization support.

    Features:
    - 5-stage cycle: Plan -> Code -> Test -> Deploy -> Feedback
    - Real-time stage transitions with validation
    - Activity tracking per stage
    - Integration status monitoring
    - Visualization data generation for animated ring
    - WebSocket event broadcasting
    """

    STATE_FILE = ".slate_identity/dev_cycle_state.json"

    def __init__(
        self,
        workspace: Optional[Path] = None,
        broadcast_callback: Optional[Callable] = None,
    ):
        self.workspace = workspace or WORKSPACE_ROOT
        self.state_path = self.workspace / self.STATE_FILE
        self.broadcast_callback = broadcast_callback
        self._state: Optional[DevCycleState] = None
        self._lock = FileLock(str(self.state_path) + ".lock")

    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        self.state_path.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> DevCycleState:
        """Load state from file or create default."""
        self._ensure_state_dir()

        if self.state_path.exists():
            try:
                with open(self.state_path, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Parse activities
                stage_activities = {}
                for stage, activities in data.get("stage_activities", {}).items():
                    stage_activities[stage] = [
                        StageActivity.from_dict(a) for a in activities
                    ]

                # Parse history
                stage_history = [
                    StageTransition(
                        from_stage=DevCycleStage(t["from_stage"]),
                        to_stage=DevCycleStage(t["to_stage"]),
                        timestamp=t["timestamp"],
                        reason=t.get("reason", ""),
                        activities_completed=t.get("activities_completed", 0),
                        duration_seconds=t.get("duration_seconds", 0),
                    )
                    for t in data.get("stage_history", [])
                ]

                return DevCycleState(
                    current_stage=DevCycleStage(data.get("current_stage", "plan")),
                    current_iteration=data.get("current_iteration", "v0.1.0"),
                    cycle_count=data.get("cycle_count", 0),
                    stage_activities=stage_activities,
                    integrations=data.get("integrations", {}),
                    stage_history=stage_history,
                    stage_entered_at=data.get("stage_entered_at", datetime.now(timezone.utc).isoformat()),
                    updated_at=data.get("updated_at", datetime.now(timezone.utc).isoformat()),
                )
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                logger.warning(f"Error loading state, creating fresh: {e}")

        # Default state
        now = datetime.now(timezone.utc).isoformat()
        return DevCycleState(
            current_stage=DevCycleStage.PLAN,
            current_iteration="v0.1.0",
            cycle_count=0,
            stage_activities={stage.value: [] for stage in DevCycleStage},
            integrations={stage.value: {} for stage in DevCycleStage},
            stage_history=[],
            stage_entered_at=now,
            updated_at=now,
        )

    def _save_state(self) -> None:
        """Save state to file."""
        if self._state is None:
            return

        self._ensure_state_dir()
        self._state.updated_at = datetime.now(timezone.utc).isoformat()

        with self._lock:
            with open(self.state_path, "w", encoding="utf-8") as f:
                json.dump(self._state.to_dict(), f, indent=2)

    @property
    def state(self) -> DevCycleState:
        """Get current state, loading if necessary."""
        if self._state is None:
            self._state = self._load_state()
        return self._state

    async def _broadcast(self, event_type: str, payload: Dict[str, Any]) -> None:
        """Broadcast event via callback if available."""
        if self.broadcast_callback:
            try:
                await self.broadcast_callback({
                    "type": event_type,
                    "payload": payload,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
            except Exception as e:
                logger.error(f"Broadcast error: {e}")

    # ─── State Access ─────────────────────────────────────────────────────────

    async def get_current_state(self) -> DevCycleState:
        """Get the current development cycle state."""
        return self.state

    async def get_current_stage(self) -> DevCycleStage:
        """Get the current stage."""
        return self.state.current_stage

    async def get_stage_info(self, stage: Optional[DevCycleStage] = None) -> Dict[str, Any]:
        """Get metadata and status for a stage."""
        stage = stage or self.state.current_stage
        metadata = STAGE_METADATA[stage]
        activities = self.state.stage_activities.get(stage.value, [])

        # Calculate stage progress
        total = len(activities)
        completed = sum(1 for a in activities if a.status == ActivityStatus.COMPLETE)
        progress = (completed / total * 100) if total > 0 else 0

        return {
            "stage": stage.value,
            **metadata,
            "is_current": stage == self.state.current_stage,
            "activity_count": total,
            "completed_count": completed,
            "progress_percent": round(progress),
            "integrations": self.state.integrations.get(stage.value, {}),
        }

    # ─── Stage Transitions ────────────────────────────────────────────────────

    async def transition_stage(
        self,
        to_stage: DevCycleStage,
        reason: str = "",
        force: bool = False,
    ) -> Dict[str, Any]:
        """
        Transition to a new development stage.

        Args:
            to_stage: Target stage
            reason: Reason for transition
            force: Force transition even if invalid

        Returns:
            Transition result with previous and new stage info
        """
        from_stage = self.state.current_stage

        # Validate transition
        if not force and to_stage not in VALID_TRANSITIONS.get(from_stage, []):
            return {
                "success": False,
                "error": f"Invalid transition from {from_stage.value} to {to_stage.value}",
                "valid_targets": [s.value for s in VALID_TRANSITIONS.get(from_stage, [])],
            }

        # Calculate time in previous stage
        try:
            entered = datetime.fromisoformat(self.state.stage_entered_at.replace("Z", "+00:00"))
            duration = int((datetime.now(timezone.utc) - entered).total_seconds())
        except:
            duration = 0

        # Count completed activities in stage being left
        activities = self.state.stage_activities.get(from_stage.value, [])
        completed = sum(1 for a in activities if a.status == ActivityStatus.COMPLETE)

        # Record transition
        now = datetime.now(timezone.utc).isoformat()
        transition = StageTransition(
            from_stage=from_stage,
            to_stage=to_stage,
            timestamp=now,
            reason=reason,
            activities_completed=completed,
            duration_seconds=duration,
        )
        self.state.stage_history.append(transition)

        # Check for cycle completion (feedback -> plan)
        if from_stage == DevCycleStage.FEEDBACK and to_stage == DevCycleStage.PLAN:
            self.state.cycle_count += 1
            # Increment version
            try:
                parts = self.state.current_iteration.split(".")
                parts[-1] = str(int(parts[-1]) + 1)
                self.state.current_iteration = ".".join(parts)
            except:
                pass

        # Update state
        self.state.current_stage = to_stage
        self.state.stage_entered_at = now
        self._save_state()

        # Broadcast event
        await self._broadcast("stage_transition", {
            "from_stage": from_stage.value,
            "to_stage": to_stage.value,
            "reason": reason,
            "cycle_count": self.state.cycle_count,
            "iteration": self.state.current_iteration,
        })

        return {
            "success": True,
            "from_stage": await self.get_stage_info(from_stage),
            "to_stage": await self.get_stage_info(to_stage),
            "transition": transition.to_dict(),
            "cycle_count": self.state.cycle_count,
        }

    async def advance_stage(self, reason: str = "") -> Dict[str, Any]:
        """Advance to the next stage in the cycle."""
        current = self.state.current_stage
        # Get first valid forward transition
        valid = VALID_TRANSITIONS.get(current, [])
        if valid:
            return await self.transition_stage(valid[0], reason)
        return {"success": False, "error": "No valid forward transition"}

    # ─── Activity Management ──────────────────────────────────────────────────

    async def add_activity(
        self,
        title: str,
        description: str = "",
        stage: Optional[DevCycleStage] = None,
        tags: Optional[List[str]] = None,
        linked_tasks: Optional[List[str]] = None,
    ) -> StageActivity:
        """Add a new activity to a stage."""
        stage = stage or self.state.current_stage

        activity = StageActivity(
            id=f"activity-{uuid.uuid4().hex[:8]}",
            stage=stage,
            title=title,
            description=description,
            tags=tags or [],
            linked_tasks=linked_tasks or [],
        )

        if stage.value not in self.state.stage_activities:
            self.state.stage_activities[stage.value] = []

        self.state.stage_activities[stage.value].append(activity)
        self._save_state()

        await self._broadcast("activity_added", {
            "activity": activity.to_dict(),
            "stage": stage.value,
        })

        return activity

    async def update_activity(
        self,
        activity_id: str,
        status: Optional[ActivityStatus] = None,
        progress_percent: Optional[int] = None,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[StageActivity]:
        """Update an existing activity."""
        for stage_activities in self.state.stage_activities.values():
            for activity in stage_activities:
                if activity.id == activity_id:
                    now = datetime.now(timezone.utc).isoformat()

                    if status is not None:
                        if status == ActivityStatus.ACTIVE and activity.started_at is None:
                            activity.started_at = now
                        elif status == ActivityStatus.COMPLETE:
                            activity.completed_at = now
                            activity.progress_percent = 100
                        activity.status = status

                    if progress_percent is not None:
                        activity.progress_percent = min(100, max(0, progress_percent))

                    if metrics is not None:
                        activity.metrics.update(metrics)

                    self._save_state()

                    await self._broadcast("activity_updated", {
                        "activity": activity.to_dict(),
                    })

                    return activity

        return None

    async def complete_activity(
        self,
        activity_id: str,
        metrics: Optional[Dict[str, Any]] = None,
    ) -> Optional[StageActivity]:
        """Mark an activity as complete."""
        return await self.update_activity(
            activity_id,
            status=ActivityStatus.COMPLETE,
            progress_percent=100,
            metrics=metrics,
        )

    async def get_activities(
        self,
        stage: Optional[DevCycleStage] = None,
        status: Optional[ActivityStatus] = None,
    ) -> List[StageActivity]:
        """Get activities, optionally filtered by stage and status."""
        activities = []

        stages = [stage] if stage else list(DevCycleStage)
        for s in stages:
            stage_activities = self.state.stage_activities.get(s.value, [])
            for activity in stage_activities:
                if status is None or activity.status == status:
                    activities.append(activity)

        return activities

    # ─── Integration Status ───────────────────────────────────────────────────

    async def update_integration_status(
        self,
        stage: DevCycleStage,
        integration_name: str,
        available: bool,
    ) -> None:
        """Update the status of an integration."""
        if stage.value not in self.state.integrations:
            self.state.integrations[stage.value] = {}

        self.state.integrations[stage.value][integration_name] = available
        self._save_state()

    async def check_integrations(self, stage: Optional[DevCycleStage] = None) -> Dict[str, Dict[str, bool]]:
        """Check and return integration status for stage(s)."""
        stages = [stage] if stage else list(DevCycleStage)
        result = {}

        for s in stages:
            result[s.value] = {}
            expected = STAGE_METADATA[s]["integrations"]

            for integration in expected:
                # Check if integration is available (simplified checks)
                available = await self._check_integration(integration)
                result[s.value][integration] = available
                await self.update_integration_status(s, integration, available)

        return result

    async def _check_integration(self, name: str) -> bool:
        """Check if a specific integration is available."""
        import subprocess

        checks = {
            "github_issues": lambda: Path(self.workspace / ".git").exists(),
            "specs": lambda: Path(self.workspace / "specs").exists(),
            "roadmap": lambda: True,  # Always available
            "ollama": lambda: self._check_service("http://localhost:11434/api/tags"),
            "claude_code": lambda: Path(self.workspace / ".claude").exists(),
            "copilot": lambda: True,  # VSCode extension
            "pytest": lambda: Path(self.workspace / "tests").exists(),
            "ci": lambda: Path(self.workspace / ".github/workflows").exists(),
            "coverage": lambda: True,
            "docker": lambda: self._check_command("docker", ["--version"]),
            "runner": lambda: Path(self.workspace / ".runner").exists(),
            "releases": lambda: True,
            "ai_review": lambda: self._check_service("http://localhost:11434/api/tags"),
            "metrics": lambda: True,
            "insights": lambda: True,
        }

        check_fn = checks.get(name, lambda: False)
        try:
            return check_fn()
        except:
            return False

    def _check_service(self, url: str) -> bool:
        """Check if an HTTP service is available."""
        try:
            import httpx
            response = httpx.get(url, timeout=2)
            return response.status_code == 200
        except:
            return False

    def _check_command(self, cmd: str, args: List[str]) -> bool:
        """Check if a command is available."""
        import subprocess
        try:
            result = subprocess.run(
                [cmd] + args,
                capture_output=True,
                timeout=5,
            )
            return result.returncode == 0
        except:
            return False

    # ─── Visualization Data ───────────────────────────────────────────────────

    def generate_visualization_data(self) -> Dict[str, Any]:
        """
        Generate data for the animated ring visualization.

        Returns data suitable for SVG/CSS rendering of the dev cycle.
        """
        stages_data = []
        stage_order = [
            DevCycleStage.PLAN,
            DevCycleStage.CODE,
            DevCycleStage.TEST,
            DevCycleStage.DEPLOY,
            DevCycleStage.FEEDBACK,
        ]

        for i, stage in enumerate(stage_order):
            metadata = STAGE_METADATA[stage]
            activities = self.state.stage_activities.get(stage.value, [])
            total = len(activities)
            completed = sum(1 for a in activities if a.status == ActivityStatus.COMPLETE)
            active = sum(1 for a in activities if a.status == ActivityStatus.ACTIVE)

            stages_data.append({
                "stage": stage.value,
                "index": i,
                "angle_start": i * 72,  # 360 / 5 = 72 degrees per stage
                "angle_end": (i + 1) * 72,
                "icon": metadata["icon"],
                "color": metadata["color"],
                "description": metadata["description"],
                "is_current": stage == self.state.current_stage,
                "activity_count": total,
                "completed_count": completed,
                "active_count": active,
                "progress": (completed / total * 100) if total > 0 else 0,
            })

        return {
            "stages": stages_data,
            "current_stage": self.state.current_stage.value,
            "current_index": stage_order.index(self.state.current_stage),
            "cycle_count": self.state.cycle_count,
            "iteration": self.state.current_iteration,
            "animation": {
                "pulse_duration": "2s",
                "transition_duration": "0.5s",
                "glow_color": STAGE_METADATA[self.state.current_stage]["color"],
            },
        }

    # ─── Metrics & Analytics ──────────────────────────────────────────────────

    async def get_metrics(self) -> Dict[str, Any]:
        """Get development cycle metrics."""
        total_activities = 0
        completed_activities = 0
        total_time_seconds = 0

        for activities in self.state.stage_activities.values():
            total_activities += len(activities)
            completed_activities += sum(1 for a in activities if a.status == ActivityStatus.COMPLETE)

        for transition in self.state.stage_history:
            total_time_seconds += transition.duration_seconds

        return {
            "cycle_count": self.state.cycle_count,
            "current_iteration": self.state.current_iteration,
            "current_stage": self.state.current_stage.value,
            "total_activities": total_activities,
            "completed_activities": completed_activities,
            "completion_rate": (completed_activities / total_activities * 100) if total_activities > 0 else 0,
            "total_time_hours": round(total_time_seconds / 3600, 2),
            "transitions_count": len(self.state.stage_history),
            "avg_stage_time_minutes": round(total_time_seconds / max(len(self.state.stage_history), 1) / 60, 1),
        }

    # ─── Reset ────────────────────────────────────────────────────────────────

    async def reset(self, preserve_history: bool = True) -> None:
        """Reset the development cycle state."""
        history = self.state.stage_history if preserve_history else []
        cycle_count = self.state.cycle_count if preserve_history else 0

        now = datetime.now(timezone.utc).isoformat()
        self._state = DevCycleState(
            current_stage=DevCycleStage.PLAN,
            current_iteration="v0.1.0",
            cycle_count=cycle_count,
            stage_activities={stage.value: [] for stage in DevCycleStage},
            integrations={stage.value: {} for stage in DevCycleStage},
            stage_history=history,
            stage_entered_at=now,
            updated_at=now,
        )
        self._save_state()

        await self._broadcast("cycle_reset", {
            "preserve_history": preserve_history,
        })


# ═══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESS
# ═══════════════════════════════════════════════════════════════════════════════

_engine_instance: Optional[DevCycleEngine] = None


def get_engine(
    workspace: Optional[Path] = None,
    broadcast_callback: Optional[Callable] = None,
) -> DevCycleEngine:
    """Get or create the singleton engine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = DevCycleEngine(workspace, broadcast_callback)
    return _engine_instance


def reset_engine() -> None:
    """Reset the engine instance."""
    global _engine_instance
    _engine_instance = None


# Alias for backwards compatibility
reset_dev_cycle_engine = reset_engine


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

async def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Development Cycle Engine")
    parser.add_argument("--status", action="store_true", help="Show current state")
    parser.add_argument("--advance", action="store_true", help="Advance to next stage")
    parser.add_argument("--transition", metavar="STAGE", help="Transition to specific stage")
    parser.add_argument("--reason", metavar="REASON", help="Reason for stage transition")
    parser.add_argument("--activities", metavar="STAGE", help="Show activities for a specific stage")
    parser.add_argument("--add-activity", metavar="TITLE", help="Add activity to current stage")
    parser.add_argument("--visualization", action="store_true", help="Get visualization data")
    parser.add_argument("--metrics", action="store_true", help="Show cycle metrics")
    parser.add_argument("--check-integrations", action="store_true", help="Check all integrations")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    engine = get_engine()

    if args.advance:
        result = await engine.advance_stage("CLI advance")
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result["success"]:
                print(f"Advanced: {result['from_stage']['stage']} -> {result['to_stage']['stage']}")
            else:
                print(f"Error: {result.get('error')}")
        return

    if args.transition:
        try:
            stage = DevCycleStage(args.transition.lower())
            reason = args.reason if args.reason else "CLI transition"
            result = await engine.transition_stage(stage, reason)
            if args.json:
                print(json.dumps(result, indent=2))
            else:
                if result["success"]:
                    print(f"Transitioned to: {stage.value}")
                else:
                    print(f"Error: {result.get('error')}")
        except ValueError:
            print(f"Invalid stage: {args.transition}")
            print(f"Valid stages: {[s.value for s in DevCycleStage]}")
        return

    if args.activities:
        try:
            stage = DevCycleStage(args.activities.lower())
            state = await engine.get_current_state()
            activities = state.stage_activities.get(stage.value, [])
            if args.json:
                print(json.dumps([a.to_dict() for a in activities], indent=2))
            else:
                print(f"Activities for {stage.value.upper()}:")
                if not activities:
                    print("  (none)")
                for a in activities:
                    status_icon = {"pending": "○", "active": "◐", "complete": "●", "blocked": "✗", "skipped": "−"}
                    print(f"  {status_icon.get(a.status.value, '?')} [{a.status.value}] {a.title}")
        except ValueError:
            print(f"Invalid stage: {args.activities}")
            print(f"Valid stages: {[s.value for s in DevCycleStage]}")
        return

    if args.add_activity:
        activity = await engine.add_activity(args.add_activity)
        if args.json:
            print(json.dumps(activity.to_dict(), indent=2))
        else:
            print(f"Added activity: {activity.id} - {activity.title}")
        return

    if args.visualization:
        data = engine.generate_visualization_data()
        print(json.dumps(data, indent=2))
        return

    if args.metrics:
        metrics = await engine.get_metrics()
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print("Development Cycle Metrics")
            print("-" * 40)
            for key, value in metrics.items():
                print(f"  {key}: {value}")
        return

    if args.check_integrations:
        result = await engine.check_integrations()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            for stage, integrations in result.items():
                print(f"\n{stage.upper()}")
                for name, available in integrations.items():
                    status = "OK" if available else "MISSING"
                    print(f"  {name}: {status}")
        return

    # Default: show status
    state = await engine.get_current_state()
    if args.json:
        print(json.dumps(state.to_dict(), indent=2))
    else:
        print("=" * 50)
        print("  SLATE Development Cycle Status")
        print("=" * 50)
        print(f"\n  Current Stage: {STAGE_METADATA[state.current_stage]['icon']} {state.current_stage.value.upper()}")
        print(f"  Iteration: {state.current_iteration}")
        print(f"  Cycle Count: {state.cycle_count}")

        print("\n  Stage Activities:")
        for stage in DevCycleStage:
            activities = state.stage_activities.get(stage.value, [])
            completed = sum(1 for a in activities if a.status == ActivityStatus.COMPLETE)
            marker = "→" if stage == state.current_stage else " "
            print(f"  {marker} {stage.value}: {completed}/{len(activities)} complete")

        print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
