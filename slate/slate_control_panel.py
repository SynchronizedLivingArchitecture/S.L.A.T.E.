#!/usr/bin/env python3
"""
SLATE Control Panel
====================

A practical, button-driven interface that guides users through
real operations with clear feedback and hand-holding.

Design: Mission control style - organized panels, real buttons,
actual commands, immediate feedback.
"""

import asyncio
import json
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional
import logging

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger(__name__)


class ActionState(Enum):
    """State of an action button."""
    READY = "ready"
    RUNNING = "running"
    SUCCESS = "success"
    ERROR = "error"


@dataclass
class ControlAction:
    """A single executable action."""
    id: str
    label: str
    description: str
    command: str  # The actual command to run
    args: str = ""
    category: str = "general"
    icon: str = "play"
    timeout: int = 120
    state: ActionState = ActionState.READY
    last_result: Optional[Dict[str, Any]] = None
    last_run: Optional[datetime] = None


# Real, executable actions organized by category
CONTROL_ACTIONS: Dict[str, List[ControlAction]] = {
    "health": [
        ControlAction(
            id="quick_status",
            label="Quick Status",
            description="Check all services in 5 seconds",
            command="slate/slate_status.py",
            args="--quick",
            category="health",
            icon="pulse",
            timeout=30
        ),
        ControlAction(
            id="full_diagnostics",
            label="Full Diagnostics",
            description="Complete system health check",
            command="slate/slate_status.py",
            args="--json",
            category="health",
            icon="scan",
            timeout=60
        ),
        ControlAction(
            id="runtime_check",
            label="Runtime Check",
            description="Verify all integrations work",
            command="slate/slate_runtime.py",
            args="--check-all",
            category="health",
            icon="check",
            timeout=60
        ),
    ],
    "testing": [
        ControlAction(
            id="run_tests",
            label="Run Tests",
            description="Execute pytest test suite",
            command="-m",
            args="pytest tests/ -v --tb=short",
            category="testing",
            icon="flask",
            timeout=300
        ),
        ControlAction(
            id="run_lint",
            label="Lint Check",
            description="Check code quality with ruff",
            command="SHELL",
            args="ruff check .",
            category="testing",
            icon="sparkle",
            timeout=120
        ),
        ControlAction(
            id="security_scan",
            label="Security Scan",
            description="Check for vulnerabilities",
            command="slate/action_guard.py",
            args="",
            category="testing",
            icon="shield",
            timeout=60
        ),
    ],
    "ai": [
        ControlAction(
            id="ai_review",
            label="AI Code Review",
            description="Analyze recent changes with AI",
            command="slate/slate_ai_orchestrator.py",
            args="--analyze-recent",
            category="ai",
            icon="brain",
            timeout=600
        ),
        ControlAction(
            id="ai_docs",
            label="Update Docs",
            description="AI-generate documentation",
            command="slate/slate_ai_orchestrator.py",
            args="--update-docs",
            category="ai",
            icon="document",
            timeout=900
        ),
        ControlAction(
            id="ollama_status",
            label="Ollama Status",
            description="Check local AI models",
            command="slate/foundry_local.py",
            args="--models",
            category="ai",
            icon="cpu",
            timeout=30
        ),
    ],
    "workflow": [
        ControlAction(
            id="workflow_status",
            label="Workflow Status",
            description="Check task queue health",
            command="slate/slate_workflow_manager.py",
            args="--status",
            category="workflow",
            icon="list",
            timeout=30
        ),
        ControlAction(
            id="workflow_cleanup",
            label="Cleanup Tasks",
            description="Remove stale/duplicate tasks",
            command="slate/slate_workflow_manager.py",
            args="--cleanup",
            category="workflow",
            icon="trash",
            timeout=60
        ),
        ControlAction(
            id="dispatch_ci",
            label="Run CI Pipeline",
            description="Trigger GitHub CI workflow",
            command="SHELL",
            args="gh workflow run ci.yml",
            category="workflow",
            icon="rocket",
            timeout=30
        ),
    ],
    "services": [
        ControlAction(
            id="start_services",
            label="Start All",
            description="Start SLATE services",
            command="slate/slate_orchestrator.py",
            args="start",
            category="services",
            icon="play",
            timeout=60
        ),
        ControlAction(
            id="stop_services",
            label="Stop All",
            description="Stop SLATE services",
            command="slate/slate_orchestrator.py",
            args="stop",
            category="services",
            icon="stop",
            timeout=30
        ),
        ControlAction(
            id="restart_services",
            label="Restart All",
            description="Restart SLATE services",
            command="slate/slate_orchestrator.py",
            args="restart",
            category="services",
            icon="refresh",
            timeout=90
        ),
    ],
    "github": [
        ControlAction(
            id="gh_prs",
            label="View PRs",
            description="List open pull requests",
            command="SHELL",
            args="gh pr list --limit 10",
            category="github",
            icon="merge",
            timeout=30
        ),
        ControlAction(
            id="gh_issues",
            label="View Issues",
            description="List open issues",
            command="SHELL",
            args="gh issue list --limit 10",
            category="github",
            icon="bug",
            timeout=30
        ),
        ControlAction(
            id="gh_workflows",
            label="View Workflows",
            description="Recent workflow runs",
            command="SHELL",
            args="gh run list --limit 5",
            category="github",
            icon="workflow",
            timeout=30
        ),
        ControlAction(
            id="sync_forks",
            label="Sync Forks",
            description="Sync fork dependencies",
            command="slate/slate_fork_manager.py",
            args="--sync",
            category="github",
            icon="sync",
            timeout=120
        ),
    ],
}

# Guided sequences - step-by-step workflows
GUIDED_SEQUENCES = {
    "first_time_setup": {
        "name": "First Time Setup",
        "description": "Set up your SLATE environment step by step",
        "steps": [
            {"action": "quick_status", "instruction": "First, let's check your system status"},
            {"action": "runtime_check", "instruction": "Now verifying all integrations..."},
            {"action": "ollama_status", "instruction": "Checking local AI models..."},
            {"action": "workflow_status", "instruction": "Finally, checking the task queue..."},
        ]
    },
    "pre_commit_check": {
        "name": "Pre-Commit Check",
        "description": "Run all checks before committing code",
        "steps": [
            {"action": "run_lint", "instruction": "Step 1: Checking code style..."},
            {"action": "run_tests", "instruction": "Step 2: Running tests..."},
            {"action": "security_scan", "instruction": "Step 3: Security scan..."},
        ]
    },
    "ai_analysis": {
        "name": "AI Analysis Suite",
        "description": "Full AI-powered code analysis",
        "steps": [
            {"action": "ollama_status", "instruction": "Checking AI is ready..."},
            {"action": "ai_review", "instruction": "Running AI code review..."},
            {"action": "ai_docs", "instruction": "Updating documentation..."},
        ]
    },
    "deploy_prep": {
        "name": "Deployment Preparation",
        "description": "Prepare for deployment",
        "steps": [
            {"action": "run_tests", "instruction": "Step 1: Running full test suite..."},
            {"action": "security_scan", "instruction": "Step 2: Security audit..."},
            {"action": "workflow_cleanup", "instruction": "Step 3: Cleaning up tasks..."},
            {"action": "dispatch_ci", "instruction": "Step 4: Triggering CI pipeline..."},
        ]
    },
}


class ControlPanel:
    """
    Main control panel that executes real commands.
    """

    def __init__(self):
        self.actions = {
            action.id: action
            for category in CONTROL_ACTIONS.values()
            for action in category
        }
        self.current_sequence: Optional[str] = None
        self.sequence_step: int = 0
        self.execution_log: List[Dict[str, Any]] = []

    def get_panel_state(self) -> Dict[str, Any]:
        """Get complete panel state for UI rendering."""
        # Get real system status
        system_status = self._get_quick_status()

        return {
            "categories": {
                cat: [self._action_to_dict(a) for a in actions]
                for cat, actions in CONTROL_ACTIONS.items()
            },
            "sequences": {
                seq_id: {
                    "id": seq_id,
                    "name": seq["name"],
                    "description": seq["description"],
                    "step_count": len(seq["steps"])
                }
                for seq_id, seq in GUIDED_SEQUENCES.items()
            },
            "system_status": system_status,
            "current_sequence": self.current_sequence,
            "sequence_step": self.sequence_step,
            "recent_log": self.execution_log[-10:] if self.execution_log else []
        }

    def _get_quick_status(self) -> Dict[str, Any]:
        """Get quick system status without running commands."""
        status = {
            "dashboard": "unknown",
            "runner": "unknown",
            "ollama": "unknown",
            "tasks_pending": 0,
            "gpu_available": False
        }

        # Check dashboard
        try:
            import httpx
            r = httpx.get("http://127.0.0.1:8080/health", timeout=2)
            status["dashboard"] = "online" if r.status_code == 200 else "offline"
        except Exception:
            status["dashboard"] = "offline"

        # Check ollama
        try:
            import httpx
            r = httpx.get("http://localhost:11434/api/tags", timeout=2)
            status["ollama"] = "online" if r.status_code == 200 else "offline"
        except Exception:
            status["ollama"] = "offline"

        # Check GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                capture_output=True, timeout=5
            )
            status["gpu_available"] = result.returncode == 0
        except Exception:
            pass

        # Check tasks
        try:
            tasks_file = WORKSPACE_ROOT / "current_tasks.json"
            if tasks_file.exists():
                tasks = json.loads(tasks_file.read_text())
                status["tasks_pending"] = len([t for t in tasks if t.get("status") == "pending"])
        except Exception:
            pass

        # Check runner
        try:
            runner_file = WORKSPACE_ROOT / ".runner"
            status["runner"] = "online" if runner_file.exists() else "offline"
        except Exception:
            pass

        return status

    def _action_to_dict(self, action: ControlAction) -> Dict[str, Any]:
        """Convert action to dictionary."""
        return {
            "id": action.id,
            "label": action.label,
            "description": action.description,
            "category": action.category,
            "icon": action.icon,
            "state": action.state.value,
            "last_run": action.last_run.isoformat() if action.last_run else None,
            "last_success": action.last_result.get("success") if action.last_result else None
        }

    async def execute_action(self, action_id: str) -> Dict[str, Any]:
        """Execute a single action."""
        action = self.actions.get(action_id)
        if not action:
            return {"success": False, "error": f"Unknown action: {action_id}"}

        action.state = ActionState.RUNNING
        action.last_run = datetime.now()

        try:
            if action.command == "SHELL":
                result = await self._run_shell(action.args, action.timeout)
            elif action.command == "-m":
                result = await self._run_python_module(action.args, action.timeout)
            else:
                result = await self._run_slate_script(action.command, action.args, action.timeout)

            action.state = ActionState.SUCCESS if result.get("success") else ActionState.ERROR
            action.last_result = result

            # Log execution
            self.execution_log.append({
                "action": action_id,
                "label": action.label,
                "success": result.get("success"),
                "timestamp": datetime.now().isoformat(),
                "output_preview": (result.get("output") or "")[:200]
            })

            return {
                "success": result.get("success", False),
                "action_id": action_id,
                "label": action.label,
                "output": result.get("output", ""),
                "error": result.get("error", ""),
                "duration_ms": result.get("duration_ms", 0)
            }

        except Exception as e:
            action.state = ActionState.ERROR
            action.last_result = {"success": False, "error": str(e)}
            return {"success": False, "action_id": action_id, "error": str(e)}

    async def _run_slate_script(self, script: str, args: str, timeout: int) -> Dict[str, Any]:
        """Run a SLATE Python script."""
        python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
        cmd = [python, str(WORKSPACE_ROOT / script)]
        if args:
            cmd.extend(args.split())

        start = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(WORKSPACE_ROOT),
                env={
                    **dict(__import__('os').environ),
                    "PYTHONPATH": str(WORKSPACE_ROOT),
                    "PYTHONIOENCODING": "utf-8"
                }
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:3000] if result.stdout else "",
                "error": result.stderr[:500] if result.returncode != 0 else "",
                "duration_ms": duration
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_python_module(self, args: str, timeout: int) -> Dict[str, Any]:
        """Run a Python module."""
        python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
        cmd = [python, "-m"] + args.split()

        start = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(WORKSPACE_ROOT)
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:3000] if result.stdout else "",
                "error": result.stderr[:500] if result.returncode != 0 else "",
                "duration_ms": duration
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_shell(self, cmd: str, timeout: int) -> Dict[str, Any]:
        """Run a shell command."""
        start = datetime.now()
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(WORKSPACE_ROOT)
            )
            duration = int((datetime.now() - start).total_seconds() * 1000)
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:3000] if result.stdout else "",
                "error": result.stderr[:500] if result.returncode != 0 else "",
                "duration_ms": duration
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def start_sequence(self, sequence_id: str) -> Dict[str, Any]:
        """Start a guided sequence."""
        if sequence_id not in GUIDED_SEQUENCES:
            return {"success": False, "error": f"Unknown sequence: {sequence_id}"}

        self.current_sequence = sequence_id
        self.sequence_step = 0

        seq = GUIDED_SEQUENCES[sequence_id]
        step = seq["steps"][0]

        return {
            "success": True,
            "sequence_id": sequence_id,
            "sequence_name": seq["name"],
            "total_steps": len(seq["steps"]),
            "current_step": 0,
            "instruction": step["instruction"],
            "action": self._action_to_dict(self.actions[step["action"]])
        }

    async def execute_sequence_step(self) -> Dict[str, Any]:
        """Execute the current step in the sequence."""
        if not self.current_sequence:
            return {"success": False, "error": "No sequence active"}

        seq = GUIDED_SEQUENCES[self.current_sequence]
        if self.sequence_step >= len(seq["steps"]):
            return {"success": True, "complete": True, "message": "Sequence complete!"}

        step = seq["steps"][self.sequence_step]
        result = await self.execute_action(step["action"])

        return {
            "success": result.get("success"),
            "step_result": result,
            "current_step": self.sequence_step,
            "total_steps": len(seq["steps"]),
            "instruction": step["instruction"]
        }

    def advance_sequence(self) -> Dict[str, Any]:
        """Move to next step in sequence."""
        if not self.current_sequence:
            return {"success": False, "error": "No sequence active"}

        seq = GUIDED_SEQUENCES[self.current_sequence]
        self.sequence_step += 1

        if self.sequence_step >= len(seq["steps"]):
            self.current_sequence = None
            self.sequence_step = 0
            return {
                "success": True,
                "complete": True,
                "message": f"'{seq['name']}' complete! All steps finished."
            }

        step = seq["steps"][self.sequence_step]
        return {
            "success": True,
            "complete": False,
            "current_step": self.sequence_step,
            "total_steps": len(seq["steps"]),
            "instruction": step["instruction"],
            "action": self._action_to_dict(self.actions[step["action"]])
        }

    def cancel_sequence(self) -> Dict[str, Any]:
        """Cancel the current sequence."""
        self.current_sequence = None
        self.sequence_step = 0
        return {"success": True, "message": "Sequence cancelled"}


# Global instance
_panel: Optional[ControlPanel] = None


def get_panel() -> ControlPanel:
    """Get or create the global control panel."""
    global _panel
    if _panel is None:
        _panel = ControlPanel()
    return _panel


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Control Panel")
    parser.add_argument("--status", action="store_true", help="Show panel status")
    parser.add_argument("--execute", type=str, help="Execute an action by ID")
    parser.add_argument("--list", action="store_true", help="List all actions")
    parser.add_argument("--sequence", type=str, help="Run a guided sequence")
    args = parser.parse_args()

    panel = get_panel()

    if args.status:
        state = panel.get_panel_state()
        print(json.dumps(state, indent=2, default=str))

    elif args.list:
        print("\nAvailable Actions:")
        print("=" * 60)
        for cat, actions in CONTROL_ACTIONS.items():
            print(f"\n[{cat.upper()}]")
            for action in actions:
                print(f"  {action.id}: {action.label}")
                print(f"      {action.description}")

        print("\n\nGuided Sequences:")
        print("=" * 60)
        for seq_id, seq in GUIDED_SEQUENCES.items():
            print(f"\n  {seq_id}: {seq['name']}")
            print(f"      {seq['description']}")
            print(f"      Steps: {len(seq['steps'])}")

    elif args.execute:
        async def run():
            result = await panel.execute_action(args.execute)
            if result.get("success"):
                print(f"SUCCESS: {result.get('label')}")
                if result.get("output"):
                    print(result["output"])
            else:
                print(f"ERROR: {result.get('error')}")

        asyncio.run(run())

    elif args.sequence:
        async def run_sequence():
            result = panel.start_sequence(args.sequence)
            if not result.get("success"):
                print(f"ERROR: {result.get('error')}")
                return

            print(f"\n{'=' * 60}")
            print(f"  {result['sequence_name']}")
            print(f"  {result['total_steps']} steps")
            print(f"{'=' * 60}\n")

            while True:
                step = panel.sequence_step
                seq = GUIDED_SEQUENCES[panel.current_sequence]
                instruction = seq["steps"][step]["instruction"]

                print(f"\n[Step {step + 1}/{result['total_steps']}] {instruction}")

                step_result = await panel.execute_sequence_step()
                if step_result.get("success"):
                    print(f"  OK: {step_result['step_result'].get('output', '')[:100]}")
                else:
                    print(f"  ERROR: {step_result['step_result'].get('error')}")

                advance = panel.advance_sequence()
                if advance.get("complete"):
                    print(f"\n{advance['message']}")
                    break

        asyncio.run(run_sequence())

    else:
        parser.print_help()
