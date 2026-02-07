#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT
# Change: Create COPILOT orchestration agent plugin
"""
COPILOT Agent — Full Orchestration
====================================
Handles complex multi-step tasks, deployment, and release management.
Coordinates other agents for compound workflows.
"""

import logging
import subprocess
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.copilot")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


class CopilotAgent(AgentBase):
    """Orchestration agent — complex, multi-step, deploy, release."""

    AGENT_ID = "COPILOT"
    AGENT_NAME = "Copilot Orchestrator"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Full orchestration: complex tasks, deployment, release management"
    REQUIRES_GPU = True
    DEPENDENCIES: List[str] = []

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="orchestration",
                patterns=["complex", "multi-step", "orchestrate", "deploy",
                          "release", "pipeline", "workflow", "coordinate"],
                requires_gpu=True,
                gpu_memory_mb=8192,
                cpu_cores=4,
                priority=5,
                description="Handle compound multi-step tasks, deployments, and releases",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a complex orchestration task using slate-coder."""
        title = task.get("title", "")
        description = task.get("description", "")

        prompt = (
            f"Complex orchestration task: {title}\n"
            f"Details: {description}\n\n"
            "Break this into atomic steps and provide implementation for each."
        )

        try:
            result = subprocess.run(
                ["ollama", "run", "slate-coder", prompt],
                capture_output=True, text=True, timeout=180,
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
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True, text=True, timeout=10
            )
            base["models_available"] = all(
                m in result.stdout for m in ["slate-coder", "slate-planner", "slate-fast"]
            )
            base["healthy"] = True
        except Exception:
            base["models_available"] = False
            base["healthy"] = False
        return base
