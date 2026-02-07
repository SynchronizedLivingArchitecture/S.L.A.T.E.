#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create GAMMA planning agent plugin
"""
GAMMA Agent — Planning & Analysis
===================================
Handles analysis, planning, research, documentation, and design tasks.
Uses slate-planner model for reasoning and structured output.
"""

import logging
import subprocess
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.gamma")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


class GammaAgent(AgentBase):
    """Planning agent — analyzes, plans, researches, documents."""

    AGENT_ID = "GAMMA"
    AGENT_NAME = "Gamma Planner"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Analysis, planning, research, documentation, and architecture design"
    REQUIRES_GPU = False
    DEPENDENCIES: List[str] = []

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="planning",
                patterns=["analyze", "plan", "research", "document", "review",
                          "design", "architecture", "spec", "strategy", "roadmap"],
                requires_gpu=False,
                cpu_cores=1,
                priority=30,
                description="Analyze codebases, create plans, write documentation",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a planning/analysis task using slate-planner."""
        title = task.get("title", "")
        description = task.get("description", "")

        prompt = (
            f"Task: {title}\n"
            f"Description: {description}\n\n"
            "Provide a structured analysis with:\n"
            "1. Current state assessment\n"
            "2. Recommended approach\n"
            "3. Implementation steps\n"
            "4. Risk factors\n"
        )

        try:
            result = subprocess.run(
                ["ollama", "run", "slate-planner", prompt],
                capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout.strip()[:3000],
                "agent": self.AGENT_ID,
                "model": "slate-planner",
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
            base["model_available"] = "slate-planner" in result.stdout
            base["healthy"] = True  # Gamma can work without GPU
        except Exception:
            base["model_available"] = False
            base["healthy"] = True  # Can still do basic analysis
        return base
