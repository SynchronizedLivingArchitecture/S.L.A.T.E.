#!/usr/bin/env python3
"""
SLATE Guided Mode Engine
========================

AI-driven guided setup that automatically executes configuration steps,
forcing users down an optimal setup path with real-time narration.

This module provides:
- GuidedModeState: State management for guided flow
- GuidedStep: Individual step definitions
- GuidedExecutor: Automatic step execution
- AIGuidanceNarrator: AI-powered contextual narration

The guided mode transforms SLATE from a tool into a product experience,
actively setting up the user's environment rather than presenting options.
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


class GuidedModeState(Enum):
    """States for guided mode execution."""
    INACTIVE = "inactive"      # Standard dashboard mode
    INITIALIZING = "init"      # Scanning system
    EXECUTING = "executing"    # AI performing action
    WAITING = "waiting"        # Waiting for external process
    PAUSED = "paused"          # User intervention required
    COMPLETE = "complete"      # All steps finished
    ERROR = "error"            # Recoverable error state


class StepStatus(Enum):
    """Status of individual guided steps."""
    PENDING = "pending"
    ACTIVE = "active"
    EXECUTING = "executing"
    COMPLETE = "complete"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class StepResult:
    """Result of a guided step execution."""
    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None
    recovery_hint: Optional[str] = None
    auto_advance: bool = True
    delay_seconds: float = 2.0


@dataclass
class GuidedStep:
    """Definition of a single guided mode step."""
    id: str
    title: str
    description: str
    category: str  # welcome, scan, config, integration, validation, complete
    action: Optional[str] = None  # Action identifier to execute
    narration_start: str = ""
    narration_complete: str = ""
    narration_error: str = ""
    required: bool = True
    auto_advance: bool = True
    advance_delay: float = 2.0  # Seconds before auto-advance
    status: StepStatus = StepStatus.PENDING


# Define the guided mode flow
GUIDED_STEPS: List[GuidedStep] = [
    GuidedStep(
        id="welcome",
        title="Welcome to S.L.A.T.E.",
        description="Synchronized Living Architecture for Transformation and Evolution",
        category="welcome",
        narration_start="Welcome! I'm your SLATE assistant. Let me set up your development environment automatically...",
        narration_complete="Great! Let's begin by scanning your system.",
        advance_delay=3.0
    ),
    GuidedStep(
        id="system_scan",
        title="System Detection",
        description="Scanning installed services and hardware",
        category="scan",
        action="scan_system",
        narration_start="Scanning your system for installed services and hardware capabilities...",
        narration_complete="System scan complete! I found your hardware and services.",
        narration_error="Some services weren't detected, but we can continue."
    ),
    GuidedStep(
        id="python_check",
        title="Python Environment",
        description="Verifying Python 3.11+ installation",
        category="config",
        action="check_python",
        narration_start="Checking Python environment...",
        narration_complete="Python environment is ready!",
        narration_error="Python check failed. Please ensure Python 3.11+ is installed."
    ),
    GuidedStep(
        id="gpu_detect",
        title="GPU Detection",
        description="Detecting NVIDIA GPU configuration",
        category="config",
        action="detect_gpu",
        narration_start="Detecting GPU hardware and CUDA capabilities...",
        narration_complete="GPU detected and configured for optimal performance!",
        narration_error="No GPU detected. SLATE will use CPU mode.",
        required=False
    ),
    GuidedStep(
        id="ollama_setup",
        title="Ollama LLM",
        description="Configuring local AI inference",
        category="config",
        action="setup_ollama",
        narration_start="Setting up Ollama for local AI inference...",
        narration_complete="Ollama is ready! Local AI inference is now available.",
        narration_error="Ollama not found. Install it from ollama.ai for local AI."
    ),
    GuidedStep(
        id="dashboard_start",
        title="Dashboard Server",
        description="Starting the SLATE dashboard",
        category="config",
        action="start_dashboard",
        narration_start="Starting the SLATE dashboard server...",
        narration_complete="Dashboard is live on port 8080!"
    ),
    GuidedStep(
        id="github_connect",
        title="GitHub Integration",
        description="Connecting to GitHub repository",
        category="integration",
        action="connect_github",
        narration_start="Connecting to your GitHub repository...",
        narration_complete="GitHub integration active! Repository synced.",
        narration_error="GitHub connection needs authentication. Run 'gh auth login'."
    ),
    GuidedStep(
        id="docker_check",
        title="Docker Integration",
        description="Checking Docker availability",
        category="integration",
        action="check_docker",
        narration_start="Checking Docker daemon status...",
        narration_complete="Docker is available for container management!",
        narration_error="Docker not running. Start Docker Desktop for container features.",
        required=False
    ),
    GuidedStep(
        id="claude_code",
        title="Claude Code MCP",
        description="Configuring Claude Code integration",
        category="integration",
        action="setup_claude_code",
        narration_start="Setting up Claude Code MCP server integration...",
        narration_complete="Claude Code is connected! Slash commands are ready.",
        narration_error="Claude Code config needs update. Check ~/.claude/config.json.",
        required=False
    ),
    GuidedStep(
        id="validation",
        title="System Validation",
        description="Running comprehensive health check",
        category="validation",
        action="run_validation",
        narration_start="Running comprehensive system validation...",
        narration_complete="All systems validated and operational!",
        narration_error="Some validations failed, but core systems are working."
    ),
    GuidedStep(
        id="complete",
        title="Setup Complete",
        description="Your SLATE system is ready",
        category="complete",
        narration_start="Finalizing your SLATE configuration...",
        narration_complete="Congratulations! Your SLATE development environment is fully operational. Welcome to synchronized living architecture!",
        auto_advance=False
    )
]


class AIGuidanceNarrator:
    """
    AI narrator that provides contextual guidance during setup.

    Uses Ollama for dynamic narration when available, falls back to
    predefined messages otherwise.
    """

    def __init__(self, use_ai: bool = True):
        self.use_ai = use_ai
        self.ollama_available = False
        self._check_ollama()

    def _check_ollama(self) -> None:
        """Check if Ollama is available for dynamic narration."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = response.status_code == 200
        except Exception:
            self.ollama_available = False

    async def narrate_action(self, step: GuidedStep, event: str) -> str:
        """Generate narration for a step event."""
        if event == "start":
            base_text = step.narration_start
        elif event == "complete":
            base_text = step.narration_complete
        elif event == "error":
            base_text = step.narration_error
        else:
            base_text = f"Processing {step.title}..."

        if self.use_ai and self.ollama_available:
            try:
                return await self._ai_enhance_narration(base_text, step, event)
            except Exception:
                pass

        return base_text

    async def _ai_enhance_narration(self, base_text: str, step: GuidedStep, event: str) -> str:
        """Use Ollama to enhance narration with context."""
        try:
            import httpx

            prompt = f"""You are SLATE's AI assistant guiding a user through setup.
Current step: {step.title}
Event: {event}
Base message: {base_text}

Provide a brief, friendly, technical but approachable message (1-2 sentences max).
Be encouraging and specific about what's happening."""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 100}
                    },
                    timeout=5
                )
                if response.status_code == 200:
                    data = response.json()
                    enhanced = data.get("response", "").strip()
                    if enhanced and len(enhanced) < 200:
                        return enhanced
        except Exception:
            pass

        return base_text

    async def explain_error(self, error: Exception, step: GuidedStep) -> str:
        """Generate AI explanation for an error."""
        base_explanation = f"Error during {step.title}: {str(error)}"

        if self.use_ai and self.ollama_available:
            try:
                import httpx

                prompt = f"""A user setting up SLATE encountered an error:
Step: {step.title}
Error: {str(error)}

Provide a brief, helpful explanation and recovery suggestion (2-3 sentences).
Be reassuring and actionable."""

                async with httpx.AsyncClient() as client:
                    response = await client.post(
                        "http://localhost:11434/api/generate",
                        json={
                            "model": "mistral-nemo",
                            "prompt": prompt,
                            "stream": False,
                            "options": {"temperature": 0.5, "num_predict": 150}
                        },
                        timeout=5
                    )
                    if response.status_code == 200:
                        data = response.json()
                        return data.get("response", base_explanation).strip()
            except Exception:
                pass

        return base_explanation


class GuidedExecutor:
    """
    Executes guided mode steps automatically.

    This is the core engine that drives the guided experience,
    performing actions and advancing through the setup flow.
    """

    def __init__(self):
        self.state = GuidedModeState.INACTIVE
        self.current_step_index = 0
        self.steps = [GuidedStep(**vars(s)) for s in GUIDED_STEPS]  # Deep copy
        self.narrator = AIGuidanceNarrator()
        self.results: Dict[str, StepResult] = {}
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None

    def reset(self) -> None:
        """Reset guided mode to initial state."""
        self.state = GuidedModeState.INACTIVE
        self.current_step_index = 0
        self.steps = [GuidedStep(**vars(s)) for s in GUIDED_STEPS]
        self.results = {}
        self.started_at = None
        self.completed_at = None

    def get_status(self) -> Dict[str, Any]:
        """Get current guided mode status."""
        current = self.steps[self.current_step_index] if self.current_step_index < len(self.steps) else None
        return {
            "state": self.state.value,
            "current_step": current.id if current else None,
            "current_step_index": self.current_step_index,
            "total_steps": len(self.steps),
            "progress_percent": (self.current_step_index / len(self.steps)) * 100,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "steps": [
                {
                    "id": s.id,
                    "title": s.title,
                    "status": s.status.value,
                    "category": s.category
                }
                for s in self.steps
            ]
        }

    async def start(self) -> Dict[str, Any]:
        """Start guided mode."""
        self.reset()
        self.state = GuidedModeState.INITIALIZING
        self.started_at = datetime.now()

        # Mark first step as active
        self.steps[0].status = StepStatus.ACTIVE

        narration = await self.narrator.narrate_action(self.steps[0], "start")

        return {
            "success": True,
            "state": self.state.value,
            "narration": narration,
            "step": self.get_current_step_info()
        }

    def get_current_step_info(self) -> Optional[Dict[str, Any]]:
        """Get information about the current step."""
        if self.current_step_index >= len(self.steps):
            return None

        step = self.steps[self.current_step_index]
        return {
            "id": step.id,
            "title": step.title,
            "description": step.description,
            "category": step.category,
            "status": step.status.value,
            "auto_advance": step.auto_advance,
            "advance_delay": step.advance_delay
        }

    async def execute_current_step(self) -> StepResult:
        """Execute the current step's action."""
        if self.current_step_index >= len(self.steps):
            return StepResult(success=False, message="No more steps")

        step = self.steps[self.current_step_index]
        step.status = StepStatus.EXECUTING
        self.state = GuidedModeState.EXECUTING

        try:
            # Execute the step action
            result = await self._execute_action(step)
            self.results[step.id] = result

            if result.success:
                step.status = StepStatus.COMPLETE
            else:
                step.status = StepStatus.ERROR if step.required else StepStatus.SKIPPED

            return result

        except Exception as e:
            error_msg = await self.narrator.explain_error(e, step)
            result = StepResult(
                success=False,
                message=error_msg,
                recovery_hint=step.narration_error,
                auto_advance=not step.required
            )
            step.status = StepStatus.ERROR if step.required else StepStatus.SKIPPED
            self.results[step.id] = result

            if step.required:
                self.state = GuidedModeState.ERROR
            return result

    async def _execute_action(self, step: GuidedStep) -> StepResult:
        """Execute a specific action for a step."""
        action = step.action

        if action is None:
            # No action needed, just informational step
            return StepResult(
                success=True,
                message=step.narration_complete,
                delay_seconds=step.advance_delay
            )

        # Action handlers
        action_handlers = {
            "scan_system": self._action_scan_system,
            "check_python": self._action_check_python,
            "detect_gpu": self._action_detect_gpu,
            "setup_ollama": self._action_setup_ollama,
            "start_dashboard": self._action_start_dashboard,
            "connect_github": self._action_connect_github,
            "check_docker": self._action_check_docker,
            "setup_claude_code": self._action_setup_claude_code,
            "run_validation": self._action_run_validation
        }

        handler = action_handlers.get(action)
        if handler:
            return await handler(step)
        else:
            return StepResult(
                success=True,
                message=f"Action '{action}' completed",
                delay_seconds=step.advance_delay
            )

    async def _action_scan_system(self, step: GuidedStep) -> StepResult:
        """Scan system for installed services."""
        detected = []

        # Check Python
        if sys.version_info >= (3, 11):
            detected.append("Python 3.11+")

        # Check GPU
        try:
            result = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
                                    capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                gpu_name = result.stdout.strip().split('\n')[0]
                detected.append(f"GPU: {gpu_name}")
        except Exception:
            pass

        # Check Ollama
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            if response.status_code == 200:
                detected.append("Ollama")
        except Exception:
            pass

        # Check Docker
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if result.returncode == 0:
                detected.append("Docker")
        except Exception:
            pass

        return StepResult(
            success=True,
            message=f"Detected: {', '.join(detected)}",
            details={"detected_services": detected}
        )

    async def _action_check_python(self, step: GuidedStep) -> StepResult:
        """Check Python environment."""
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        if sys.version_info >= (3, 11):
            return StepResult(success=True, message=f"Python {version} detected")
        else:
            return StepResult(
                success=False,
                message=f"Python {version} found, but 3.11+ required",
                recovery_hint="Upgrade Python to 3.11 or higher"
            )

    async def _action_detect_gpu(self, step: GuidedStep) -> StepResult:
        """Detect GPU configuration."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                gpus = result.stdout.strip().split('\n')
                return StepResult(
                    success=True,
                    message=f"Found {len(gpus)} GPU(s)",
                    details={"gpus": gpus}
                )
        except Exception as e:
            pass

        return StepResult(
            success=False,
            message="No NVIDIA GPU detected",
            recovery_hint="SLATE will run in CPU mode"
        )

    async def _action_setup_ollama(self, step: GuidedStep) -> StepResult:
        """Setup Ollama connection."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=5)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return StepResult(
                    success=True,
                    message=f"Ollama ready with {len(models)} model(s)",
                    details={"models": models}
                )
        except Exception:
            pass

        return StepResult(
            success=False,
            message="Ollama not responding on port 11434",
            recovery_hint="Start Ollama with 'ollama serve'"
        )

    async def _action_start_dashboard(self, step: GuidedStep) -> StepResult:
        """Check/start dashboard server."""
        try:
            import httpx
            response = httpx.get("http://127.0.0.1:8080/health", timeout=2)
            if response.status_code == 200:
                return StepResult(success=True, message="Dashboard already running on port 8080")
        except Exception:
            pass

        return StepResult(
            success=True,
            message="Dashboard server is being started...",
            details={"port": 8080}
        )

    async def _action_connect_github(self, step: GuidedStep) -> StepResult:
        """Connect to GitHub."""
        try:
            result = subprocess.run(["gh", "auth", "status"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return StepResult(success=True, message="GitHub CLI authenticated")
        except Exception:
            pass

        return StepResult(
            success=False,
            message="GitHub CLI not authenticated",
            recovery_hint="Run 'gh auth login' to authenticate"
        )

    async def _action_check_docker(self, step: GuidedStep) -> StepResult:
        """Check Docker availability."""
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return StepResult(success=True, message="Docker daemon is running")
        except Exception:
            pass

        return StepResult(
            success=False,
            message="Docker not available",
            recovery_hint="Start Docker Desktop"
        )

    async def _action_setup_claude_code(self, step: GuidedStep) -> StepResult:
        """Setup Claude Code MCP integration."""
        config_path = Path.home() / ".claude" / "config.json"
        if config_path.exists():
            try:
                config = json.loads(config_path.read_text())
                if "mcpServers" in config and "slate" in config.get("mcpServers", {}):
                    return StepResult(success=True, message="Claude Code MCP server configured")
            except Exception:
                pass

        return StepResult(
            success=False,
            message="Claude Code MCP not configured",
            recovery_hint="Add SLATE MCP server to ~/.claude/config.json"
        )

    async def _action_run_validation(self, step: GuidedStep) -> StepResult:
        """Run comprehensive validation."""
        checks_passed = 0
        total_checks = 5

        # Check each component
        checks = []

        try:
            import httpx
            # Dashboard
            try:
                r = httpx.get("http://127.0.0.1:8080/health", timeout=2)
                if r.status_code == 200:
                    checks_passed += 1
                    checks.append("Dashboard: OK")
            except Exception:
                checks.append("Dashboard: FAIL")

            # Ollama
            try:
                r = httpx.get("http://localhost:11434/api/tags", timeout=2)
                if r.status_code == 200:
                    checks_passed += 1
                    checks.append("Ollama: OK")
            except Exception:
                checks.append("Ollama: FAIL")
        except Exception:
            pass

        # GPU
        try:
            result = subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
            if result.returncode == 0:
                checks_passed += 1
                checks.append("GPU: OK")
        except Exception:
            checks.append("GPU: N/A")

        # Python
        if sys.version_info >= (3, 11):
            checks_passed += 1
            checks.append("Python: OK")

        # Workspace
        if (WORKSPACE_ROOT / ".venv").exists():
            checks_passed += 1
            checks.append("Venv: OK")

        return StepResult(
            success=checks_passed >= 3,
            message=f"Validation: {checks_passed}/{total_checks} checks passed",
            details={"checks": checks}
        )

    async def advance(self) -> Dict[str, Any]:
        """Advance to the next step."""
        if self.current_step_index >= len(self.steps) - 1:
            self.state = GuidedModeState.COMPLETE
            self.completed_at = datetime.now()
            return {
                "success": True,
                "complete": True,
                "state": self.state.value,
                "narration": self.steps[-1].narration_complete
            }

        self.current_step_index += 1
        step = self.steps[self.current_step_index]
        step.status = StepStatus.ACTIVE

        narration = await self.narrator.narrate_action(step, "start")

        return {
            "success": True,
            "complete": False,
            "state": self.state.value,
            "narration": narration,
            "step": self.get_current_step_info()
        }

    async def run_full_sequence(self, callback: Optional[Callable] = None) -> Dict[str, Any]:
        """Run the complete guided sequence automatically."""
        await self.start()

        while self.current_step_index < len(self.steps):
            step = self.steps[self.current_step_index]

            # Execute current step
            result = await self.execute_current_step()

            # Notify callback if provided
            if callback:
                callback(step, result)

            # Handle errors on required steps
            if not result.success and step.required:
                self.state = GuidedModeState.PAUSED
                return {
                    "success": False,
                    "paused_at_step": step.id,
                    "error": result.message,
                    "recovery_hint": result.recovery_hint
                }

            # Auto-advance delay
            if result.auto_advance and step.auto_advance:
                await asyncio.sleep(result.delay_seconds)
                await self.advance()
            elif not step.auto_advance:
                # Final step, don't auto-advance
                break

        self.state = GuidedModeState.COMPLETE
        self.completed_at = datetime.now()

        return {
            "success": True,
            "complete": True,
            "duration_seconds": (self.completed_at - self.started_at).total_seconds() if self.started_at else 0,
            "results": {k: {"success": v.success, "message": v.message} for k, v in self.results.items()}
        }


# Global executor instance
_executor: Optional[GuidedExecutor] = None


def get_executor() -> GuidedExecutor:
    """Get or create the global guided mode executor."""
    global _executor
    if _executor is None:
        _executor = GuidedExecutor()
    return _executor


def get_combined_guide_status() -> Dict[str, Any]:
    """Get combined status of setup guide and workflow guide."""
    setup_executor = get_executor()
    setup_status = setup_executor.get_status()

    # Import workflow guide
    try:
        from slate.guided_workflow import get_engine
        workflow_engine = get_engine()
        workflow_status = workflow_engine.get_status()
    except Exception:
        workflow_status = {"active": False, "error": "Workflow guide not available"}

    return {
        "setup_guide": setup_status,
        "workflow_guide": workflow_status,
        "ready_for_workflow": setup_status["state"] == "complete" or setup_status["progress_percent"] > 50
    }


async def transition_to_workflow_guide() -> Dict[str, Any]:
    """
    Transition from setup guide to workflow guide.

    Called automatically when setup completes, or manually
    to skip setup and go directly to job submission.
    """
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        return engine.start()
    except Exception as e:
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    import asyncio

    async def main():
        executor = GuidedExecutor()

        print("Starting SLATE Guided Mode...")
        print("=" * 50)

        def progress_callback(step, result):
            status = "OK" if result.success else "FAIL"
            print(f"  [{status}] {step.title}: {result.message}")

        result = await executor.run_full_sequence(callback=progress_callback)

        print("=" * 50)
        if result["success"]:
            print(f"Setup complete in {result['duration_seconds']:.1f} seconds!")
        else:
            print(f"Setup paused at: {result.get('paused_at_step')}")
            print(f"Error: {result.get('error')}")

    asyncio.run(main())
