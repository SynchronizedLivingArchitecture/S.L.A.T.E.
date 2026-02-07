#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create ALPHA coding agent plugin
"""
ALPHA Agent — Coding
=====================
Handles code generation, implementation, refactoring, and bug fixes.
Routes to Ollama slate-coder model for GPU-accelerated inference.
"""

import logging
import subprocess
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.alpha")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


class AlphaAgent(AgentBase):
    """Coding agent — implements, builds, fixes, refactors code."""

    AGENT_ID = "ALPHA"
    AGENT_NAME = "Alpha Coder"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Code generation, implementation, refactoring, and bug fixes"
    REQUIRES_GPU = True
    DEPENDENCIES: List[str] = []

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="code_generation",
                patterns=["implement", "code", "build", "fix", "create", "add",
                          "refactor", "write", "function", "class", "method"],
                requires_gpu=True,
                gpu_memory_mb=4096,
                cpu_cores=2,
                priority=10,
                description="Generate, refactor, or fix Python/TypeScript code",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a coding task using slate-coder model."""
        title = task.get("title", "")
        description = task.get("description", "")
        target_files = task.get("target_files", [])

        prompt = f"Task: {title}\nDescription: {description}\n"
        if target_files:
            prompt += f"Target files: {', '.join(target_files)}\n"
        prompt += "\nProvide the implementation."

        try:
            result = self._run_ollama("slate-coder", prompt)
            return {
                "success": True,
                "result": result,
                "agent": self.AGENT_ID,
                "model": "slate-coder",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        """Check that slate-coder model is available."""
        base = super().health_check()
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            base["model_available"] = "slate-coder" in result.stdout
            base["healthy"] = base["model_available"]
        except Exception:
            base["model_available"] = False
            base["healthy"] = False
        return base

    def _run_ollama(self, model: str, prompt: str) -> str:
        """Run inference via Ollama CLI."""
        result = subprocess.run(
            ["ollama", "run", model, prompt],
            capture_output=True, text=True, timeout=120,
            cwd=str(WORKSPACE_ROOT),
        )
        if result.returncode != 0:
            raise RuntimeError(f"Ollama error: {result.stderr[:200]}")
        return result.stdout.strip()
