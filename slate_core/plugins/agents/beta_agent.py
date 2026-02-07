#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create BETA testing agent plugin
"""
BETA Agent — Testing
=====================
Handles test generation, validation, linting, and coverage analysis.
Routes to Ollama slate-coder model for test generation, runs pytest locally.
"""

import logging
import subprocess
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.beta")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


class BetaAgent(AgentBase):
    """Testing agent — tests, validates, verifies, checks coverage."""

    AGENT_ID = "BETA"
    AGENT_NAME = "Beta Tester"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Test generation, validation, linting, and coverage analysis"
    REQUIRES_GPU = True
    DEPENDENCIES: List[str] = []

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="testing",
                patterns=["test", "validate", "verify", "coverage", "check",
                          "lint", "format", "pytest", "unittest", "assert"],
                requires_gpu=True,
                gpu_memory_mb=2048,
                cpu_cores=2,
                priority=20,
                description="Generate and run tests, lint, validate code quality",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a testing task."""
        title = task.get("title", "")
        description = task.get("description", "")

        # Determine if this is a lint, test-run, or test-generation task
        combined = f"{title} {description}".lower()

        if any(w in combined for w in ["lint", "format", "ruff"]):
            return self._run_lint()
        elif any(w in combined for w in ["run test", "pytest", "execute test"]):
            return self._run_tests(task.get("target_files", []))
        else:
            return self._generate_tests(task)

    def _run_lint(self) -> dict:
        """Run ruff linter on the codebase."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            result = subprocess.run(
                [python, "-m", "ruff", "check", "slate/", "agents/", "slate_core/"],
                capture_output=True, text=True, timeout=60,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout[:2000],
                "error": result.stderr[:500] if result.returncode != 0 else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _run_tests(self, target_files: list) -> dict:
        """Run pytest on specified files or all tests."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            cmd = [python, "-m", "pytest", "-v", "--tb=short"]
            if target_files:
                cmd.extend(target_files)
            else:
                cmd.append("tests/")

            result = subprocess.run(
                cmd, capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout[-2000:],
                "error": result.stderr[:500] if result.returncode != 0 else None,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _generate_tests(self, task: dict) -> dict:
        """Generate tests using slate-coder model."""
        title = task.get("title", "")
        description = task.get("description", "")
        prompt = (
            f"Task: {title}\nDescription: {description}\n"
            "Generate pytest tests following Arrange-Act-Assert pattern.\n"
            "Use pytest and pytest-asyncio. Place in tests/ directory."
        )
        try:
            result = subprocess.run(
                ["ollama", "run", "slate-coder", prompt],
                capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout.strip()[:3000],
                "agent": self.AGENT_ID,
                "model": "slate-coder",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        base = super().health_check()
        python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
        try:
            result = subprocess.run(
                [python, "-m", "pytest", "--version"],
                capture_output=True, text=True, timeout=10
            )
            base["pytest_available"] = result.returncode == 0
            base["healthy"] = True
        except Exception:
            base["pytest_available"] = False
        return base
