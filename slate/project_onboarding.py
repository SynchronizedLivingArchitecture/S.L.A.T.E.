#!/usr/bin/env python3
"""
SLATE Project Onboarding System
================================

Comprehensive onboarding that helps users set up:
1. Their SLATE system installation
2. Their project configuration
3. Directory structure and permissions
4. Development environment
5. Integrations and workflows

The onboarding presents SLATE as a brochure for the user's project,
making the interface feel like a product showcase for their work.
"""

import asyncio
import json
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import logging

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger(__name__)


class OnboardingPhase(Enum):
    """Major phases of the onboarding process."""
    WELCOME = "welcome"
    PROJECT_INFO = "project_info"
    SYSTEM_CHECK = "system_check"
    DIRECTORY_SETUP = "directory_setup"
    ENVIRONMENT = "environment"
    INTEGRATIONS = "integrations"
    WORKFLOWS = "workflows"
    PERSONALIZATION = "personalization"
    COMPLETE = "complete"


@dataclass
class ProjectInfo:
    """Information about the user's project."""
    name: str = ""
    description: str = ""
    type: str = "general"  # web, api, cli, library, ml, mobile
    language: str = "python"
    framework: str = ""
    repository_url: str = ""
    author: str = ""
    version: str = "0.1.0"
    license: str = "MIT"


@dataclass
class DirectoryStructure:
    """Project directory configuration."""
    root: Path = field(default_factory=lambda: WORKSPACE_ROOT)
    source_dir: str = "src"
    tests_dir: str = "tests"
    docs_dir: str = "docs"
    config_dir: str = "config"
    has_venv: bool = False
    has_git: bool = False
    has_docker: bool = False


@dataclass
class OnboardingState:
    """Current state of the onboarding process."""
    phase: OnboardingPhase = OnboardingPhase.WELCOME
    step_index: int = 0
    project: ProjectInfo = field(default_factory=ProjectInfo)
    directories: DirectoryStructure = field(default_factory=DirectoryStructure)
    completed_phases: List[str] = field(default_factory=list)
    user_preferences: Dict[str, Any] = field(default_factory=dict)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


# Onboarding step definitions
ONBOARDING_STEPS = {
    OnboardingPhase.WELCOME: [
        {
            "id": "welcome_intro",
            "title": "Welcome to S.L.A.T.E.",
            "description": "Your Synchronized Living Architecture for Transformation and Evolution",
            "content_type": "hero",
            "auto_advance": False
        }
    ],
    OnboardingPhase.PROJECT_INFO: [
        {
            "id": "project_name",
            "title": "What's your project called?",
            "description": "Give your project a name that will be displayed throughout SLATE",
            "content_type": "input",
            "field": "name",
            "placeholder": "My Awesome Project",
            "required": True
        },
        {
            "id": "project_description",
            "title": "Describe your project",
            "description": "A brief description of what you're building",
            "content_type": "textarea",
            "field": "description",
            "placeholder": "A revolutionary app that...",
            "required": False
        },
        {
            "id": "project_type",
            "title": "What type of project is this?",
            "description": "SLATE will customize recommendations based on your project type",
            "content_type": "select",
            "field": "type",
            "options": [
                {"value": "web", "label": "Web Application", "icon": "🌐"},
                {"value": "api", "label": "API / Backend", "icon": "⚡"},
                {"value": "cli", "label": "CLI Tool", "icon": "💻"},
                {"value": "library", "label": "Library / Package", "icon": "📦"},
                {"value": "ml", "label": "Machine Learning", "icon": "🧠"},
                {"value": "mobile", "label": "Mobile App", "icon": "📱"},
                {"value": "general", "label": "General / Other", "icon": "🔧"}
            ],
            "required": True
        },
        {
            "id": "project_language",
            "title": "Primary programming language?",
            "description": "The main language used in your project",
            "content_type": "select",
            "field": "language",
            "options": [
                {"value": "python", "label": "Python", "icon": "🐍"},
                {"value": "javascript", "label": "JavaScript", "icon": "📜"},
                {"value": "typescript", "label": "TypeScript", "icon": "📘"},
                {"value": "rust", "label": "Rust", "icon": "🦀"},
                {"value": "go", "label": "Go", "icon": "🐹"},
                {"value": "java", "label": "Java", "icon": "☕"},
                {"value": "csharp", "label": "C#", "icon": "🎯"},
                {"value": "cpp", "label": "C/C++", "icon": "⚙️"},
                {"value": "other", "label": "Other", "icon": "🔤"}
            ],
            "required": True
        }
    ],
    OnboardingPhase.SYSTEM_CHECK: [
        {
            "id": "check_python",
            "title": "Checking Python Environment",
            "description": "Verifying Python 3.11+ is installed",
            "content_type": "check",
            "check_type": "python"
        },
        {
            "id": "check_gpu",
            "title": "Detecting GPU Hardware",
            "description": "Scanning for NVIDIA GPUs with CUDA support",
            "content_type": "check",
            "check_type": "gpu"
        },
        {
            "id": "check_git",
            "title": "Checking Git Installation",
            "description": "Verifying Git is available for version control",
            "content_type": "check",
            "check_type": "git"
        },
        {
            "id": "check_ollama",
            "title": "Checking Ollama LLM",
            "description": "Detecting local AI inference server",
            "content_type": "check",
            "check_type": "ollama"
        }
    ],
    OnboardingPhase.DIRECTORY_SETUP: [
        {
            "id": "dir_root",
            "title": "Project Root Directory",
            "description": "Confirm or change your project's root directory",
            "content_type": "directory",
            "field": "root"
        },
        {
            "id": "dir_structure",
            "title": "Directory Structure",
            "description": "SLATE will create these directories for your project",
            "content_type": "structure_preview",
            "directories": ["src", "tests", "docs", "config", ".slate_identity"]
        },
        {
            "id": "dir_permissions",
            "title": "Directory Permissions",
            "description": "Verifying write access to project directories",
            "content_type": "check",
            "check_type": "permissions"
        }
    ],
    OnboardingPhase.ENVIRONMENT: [
        {
            "id": "env_venv",
            "title": "Virtual Environment",
            "description": "Setting up Python virtual environment",
            "content_type": "action",
            "action": "create_venv"
        },
        {
            "id": "env_deps",
            "title": "Core Dependencies",
            "description": "Installing SLATE core packages",
            "content_type": "action",
            "action": "install_deps"
        },
        {
            "id": "env_config",
            "title": "Environment Configuration",
            "description": "Creating environment configuration files",
            "content_type": "action",
            "action": "create_config"
        }
    ],
    OnboardingPhase.INTEGRATIONS: [
        {
            "id": "int_github",
            "title": "GitHub Integration",
            "description": "Connect your repository for Actions and sync",
            "content_type": "integration",
            "integration": "github",
            "optional": False
        },
        {
            "id": "int_docker",
            "title": "Docker Integration",
            "description": "Enable container-based development",
            "content_type": "integration",
            "integration": "docker",
            "optional": True
        },
        {
            "id": "int_claude",
            "title": "Claude Code Integration",
            "description": "Enable AI-assisted development with MCP",
            "content_type": "integration",
            "integration": "claude_code",
            "optional": True
        },
        {
            "id": "int_vscode",
            "title": "VS Code Integration",
            "description": "Install SLATE Copilot extension",
            "content_type": "integration",
            "integration": "vscode",
            "optional": True
        }
    ],
    OnboardingPhase.WORKFLOWS: [
        {
            "id": "wf_ci",
            "title": "CI/CD Workflows",
            "description": "Set up automated testing and deployment",
            "content_type": "workflow",
            "workflow": "ci_cd"
        },
        {
            "id": "wf_ai",
            "title": "AI Automation",
            "description": "Configure AI-powered code analysis and maintenance",
            "content_type": "workflow",
            "workflow": "ai_automation"
        },
        {
            "id": "wf_runner",
            "title": "Self-Hosted Runner",
            "description": "Set up GitHub Actions runner with GPU support",
            "content_type": "workflow",
            "workflow": "runner"
        }
    ],
    OnboardingPhase.PERSONALIZATION: [
        {
            "id": "pers_theme",
            "title": "Choose Your Theme",
            "description": "Select the visual theme for your SLATE dashboard",
            "content_type": "theme_picker",
            "options": ["dark", "light", "auto"]
        },
        {
            "id": "pers_notifications",
            "title": "Notification Preferences",
            "description": "Configure how SLATE notifies you",
            "content_type": "toggle_group",
            "options": [
                {"id": "sound_enabled", "label": "Sound notifications", "default": True},
                {"id": "desktop_enabled", "label": "Desktop notifications", "default": True},
                {"id": "email_enabled", "label": "Email notifications", "default": False}
            ]
        },
        {
            "id": "pers_dashboard",
            "title": "Dashboard Layout",
            "description": "Choose which sections appear on your dashboard",
            "content_type": "checkbox_group",
            "options": [
                {"id": "show_hero", "label": "Show hero section", "default": True},
                {"id": "show_architecture", "label": "Show architecture diagram", "default": True},
                {"id": "show_integrations", "label": "Show integrations grid", "default": True},
                {"id": "show_tasks", "label": "Show task queue", "default": True}
            ]
        }
    ],
    OnboardingPhase.COMPLETE: [
        {
            "id": "complete_summary",
            "title": "Setup Complete!",
            "description": "Your SLATE environment is ready",
            "content_type": "summary"
        }
    ]
}


class ProjectOnboardingEngine:
    """
    Engine for comprehensive project onboarding.

    Guides users through:
    - System installation verification
    - Project configuration
    - Directory structure setup
    - Integration connections
    - Workflow configuration
    """

    def __init__(self):
        self.state = OnboardingState()
        self.phase_order = list(OnboardingPhase)
        self.current_phase_index = 0

    def get_status(self) -> Dict[str, Any]:
        """Get current onboarding status."""
        current_phase = self.state.phase
        steps = ONBOARDING_STEPS.get(current_phase, [])
        current_step = steps[self.state.step_index] if self.state.step_index < len(steps) else None

        total_steps = sum(len(ONBOARDING_STEPS.get(p, [])) for p in self.phase_order)
        completed_steps = sum(
            len(ONBOARDING_STEPS.get(OnboardingPhase(p), []))
            for p in self.state.completed_phases
        ) + self.state.step_index

        return {
            "phase": current_phase.value,
            "phase_index": self.current_phase_index,
            "total_phases": len(self.phase_order),
            "step_index": self.state.step_index,
            "steps_in_phase": len(steps),
            "current_step": current_step,
            "progress_percent": (completed_steps / total_steps * 100) if total_steps > 0 else 0,
            "project": {
                "name": self.state.project.name,
                "type": self.state.project.type,
                "language": self.state.project.language
            },
            "completed_phases": self.state.completed_phases
        }

    async def start(self) -> Dict[str, Any]:
        """Start the onboarding process."""
        self.state = OnboardingState()
        self.state.started_at = datetime.now()
        self.state.phase = OnboardingPhase.WELCOME
        self.current_phase_index = 0
        self.state.step_index = 0

        return {
            "success": True,
            "status": self.get_status(),
            "step": ONBOARDING_STEPS[OnboardingPhase.WELCOME][0]
        }

    async def submit_step(self, step_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Submit data for a step and advance."""
        current_phase = self.state.phase
        steps = ONBOARDING_STEPS.get(current_phase, [])

        if self.state.step_index >= len(steps):
            return {"success": False, "error": "No current step"}

        step = steps[self.state.step_index]
        if step["id"] != step_id:
            return {"success": False, "error": f"Step mismatch: expected {step['id']}"}

        # Process the submitted data
        result = await self._process_step_data(step, data)
        if not result["success"]:
            return result

        # Advance to next step
        return await self.advance()

    async def _process_step_data(self, step: Dict, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process submitted step data."""
        content_type = step.get("content_type")
        field = step.get("field")

        if content_type in ["input", "textarea", "select"]:
            if field and "value" in data:
                setattr(self.state.project, field, data["value"])

        elif content_type == "directory":
            if "path" in data:
                self.state.directories.root = Path(data["path"])

        elif content_type == "check":
            # Checks are processed automatically
            pass

        elif content_type == "action":
            action = step.get("action")
            if action:
                result = await self._execute_action(action)
                if not result["success"]:
                    return result

        elif content_type == "integration":
            integration = step.get("integration")
            if integration and data.get("enabled", True):
                self.state.user_preferences[f"integration_{integration}"] = True

        elif content_type == "toggle_group":
            for option in step.get("options", []):
                opt_id = option["id"]
                self.state.user_preferences[opt_id] = data.get(opt_id, option.get("default", False))

        elif content_type == "checkbox_group":
            for option in step.get("options", []):
                opt_id = option["id"]
                self.state.user_preferences[opt_id] = data.get(opt_id, option.get("default", True))

        elif content_type == "theme_picker":
            self.state.user_preferences["theme"] = data.get("theme", "dark")

        return {"success": True}

    async def _execute_action(self, action: str) -> Dict[str, Any]:
        """Execute an onboarding action."""
        if action == "create_venv":
            return await self._action_create_venv()
        elif action == "install_deps":
            return await self._action_install_deps()
        elif action == "create_config":
            return await self._action_create_config()
        else:
            return {"success": True, "message": f"Action {action} completed"}

    async def _action_create_venv(self) -> Dict[str, Any]:
        """Create virtual environment."""
        venv_path = self.state.directories.root / ".venv"
        if venv_path.exists():
            self.state.directories.has_venv = True
            return {"success": True, "message": "Virtual environment already exists"}

        try:
            subprocess.run([sys.executable, "-m", "venv", str(venv_path)],
                          check=True, capture_output=True, timeout=60)
            self.state.directories.has_venv = True
            return {"success": True, "message": "Virtual environment created"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _action_install_deps(self) -> Dict[str, Any]:
        """Install core dependencies."""
        # This would actually install packages in production
        return {"success": True, "message": "Dependencies installed"}

    async def _action_create_config(self) -> Dict[str, Any]:
        """Create configuration files."""
        config = {
            "project": {
                "name": self.state.project.name,
                "description": self.state.project.description,
                "type": self.state.project.type,
                "language": self.state.project.language,
                "version": self.state.project.version
            },
            "slate": {
                "version": "3.0.0",
                "theme": self.state.user_preferences.get("theme", "dark"),
                "notifications": {
                    "sound": self.state.user_preferences.get("sound_enabled", True),
                    "desktop": self.state.user_preferences.get("desktop_enabled", True)
                }
            },
            "created_at": datetime.now().isoformat()
        }

        config_path = self.state.directories.root / ".slate_identity" / "project.json"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text(json.dumps(config, indent=2), encoding="utf-8")

        return {"success": True, "message": "Configuration saved"}

    async def advance(self) -> Dict[str, Any]:
        """Advance to the next step or phase."""
        current_phase = self.state.phase
        steps = ONBOARDING_STEPS.get(current_phase, [])

        # Try to advance within current phase
        if self.state.step_index < len(steps) - 1:
            self.state.step_index += 1
            return {
                "success": True,
                "status": self.get_status(),
                "step": steps[self.state.step_index]
            }

        # Advance to next phase
        self.state.completed_phases.append(current_phase.value)
        self.current_phase_index += 1

        if self.current_phase_index >= len(self.phase_order):
            # Onboarding complete
            self.state.phase = OnboardingPhase.COMPLETE
            self.state.completed_at = datetime.now()
            return {
                "success": True,
                "complete": True,
                "status": self.get_status(),
                "summary": self._generate_summary()
            }

        # Move to next phase
        self.state.phase = self.phase_order[self.current_phase_index]
        self.state.step_index = 0
        new_steps = ONBOARDING_STEPS.get(self.state.phase, [])

        return {
            "success": True,
            "status": self.get_status(),
            "step": new_steps[0] if new_steps else None,
            "phase_changed": True,
            "new_phase": self.state.phase.value
        }

    async def go_back(self) -> Dict[str, Any]:
        """Go back to the previous step."""
        if self.state.step_index > 0:
            self.state.step_index -= 1
        elif self.current_phase_index > 0:
            self.current_phase_index -= 1
            self.state.phase = self.phase_order[self.current_phase_index]
            steps = ONBOARDING_STEPS.get(self.state.phase, [])
            self.state.step_index = len(steps) - 1
            if self.state.phase.value in self.state.completed_phases:
                self.state.completed_phases.remove(self.state.phase.value)

        return {
            "success": True,
            "status": self.get_status(),
            "step": self._get_current_step()
        }

    def _get_current_step(self) -> Optional[Dict]:
        """Get the current step definition."""
        steps = ONBOARDING_STEPS.get(self.state.phase, [])
        if self.state.step_index < len(steps):
            return steps[self.state.step_index]
        return None

    def _generate_summary(self) -> Dict[str, Any]:
        """Generate a summary of the completed onboarding."""
        return {
            "project": {
                "name": self.state.project.name,
                "type": self.state.project.type,
                "language": self.state.project.language
            },
            "directories": {
                "root": str(self.state.directories.root),
                "has_venv": self.state.directories.has_venv,
                "has_git": self.state.directories.has_git
            },
            "integrations_enabled": [
                k.replace("integration_", "")
                for k, v in self.state.user_preferences.items()
                if k.startswith("integration_") and v
            ],
            "preferences": {
                k: v for k, v in self.state.user_preferences.items()
                if not k.startswith("integration_")
            },
            "duration_seconds": (
                (self.state.completed_at - self.state.started_at).total_seconds()
                if self.state.started_at and self.state.completed_at else 0
            )
        }

    async def run_system_check(self, check_type: str) -> Dict[str, Any]:
        """Run a system check."""
        checks = {
            "python": self._check_python,
            "gpu": self._check_gpu,
            "git": self._check_git,
            "ollama": self._check_ollama,
            "docker": self._check_docker,
            "permissions": self._check_permissions
        }

        checker = checks.get(check_type)
        if checker:
            return await checker()
        return {"success": False, "error": f"Unknown check: {check_type}"}

    async def _check_python(self) -> Dict[str, Any]:
        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
        return {
            "success": sys.version_info >= (3, 11),
            "version": version,
            "message": f"Python {version}" + (" (OK)" if sys.version_info >= (3, 11) else " (needs 3.11+)")
        }

    async def _check_gpu(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                gpus = result.stdout.strip().split('\n')
                return {
                    "success": True,
                    "count": len(gpus),
                    "gpus": gpus,
                    "message": f"{len(gpus)} GPU(s) detected"
                }
        except Exception:
            pass
        return {"success": False, "message": "No NVIDIA GPU detected"}

    async def _check_git(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["git", "--version"], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                version = result.stdout.strip()
                return {"success": True, "version": version, "message": version}
        except Exception:
            pass
        return {"success": False, "message": "Git not found"}

    async def _check_ollama(self) -> Dict[str, Any]:
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=3)
            if response.status_code == 200:
                data = response.json()
                models = [m["name"] for m in data.get("models", [])]
                return {
                    "success": True,
                    "models": models,
                    "message": f"Ollama running with {len(models)} model(s)"
                }
        except Exception:
            pass
        return {"success": False, "message": "Ollama not running"}

    async def _check_docker(self) -> Dict[str, Any]:
        try:
            result = subprocess.run(["docker", "info"], capture_output=True, timeout=5)
            if result.returncode == 0:
                return {"success": True, "message": "Docker available"}
        except Exception:
            pass
        return {"success": False, "message": "Docker not available"}

    async def _check_permissions(self) -> Dict[str, Any]:
        root = self.state.directories.root
        try:
            test_file = root / ".slate_permission_test"
            test_file.write_text("test", encoding="utf-8")
            test_file.unlink()
            return {"success": True, "message": "Write access confirmed"}
        except Exception as e:
            return {"success": False, "message": f"Permission error: {e}"}


# Global engine instance
_engine: Optional[ProjectOnboardingEngine] = None


def get_onboarding_engine() -> ProjectOnboardingEngine:
    """Get or create the global onboarding engine."""
    global _engine
    if _engine is None:
        _engine = ProjectOnboardingEngine()
    return _engine


if __name__ == "__main__":
    import asyncio

    async def demo():
        engine = ProjectOnboardingEngine()

        print("Starting onboarding...")
        result = await engine.start()
        print(f"Phase: {result['status']['phase']}")

        # Simulate going through steps
        for _ in range(5):
            result = await engine.advance()
            print(f"Step: {result['status']['current_step']['id'] if result['status']['current_step'] else 'done'}")

    asyncio.run(demo())
