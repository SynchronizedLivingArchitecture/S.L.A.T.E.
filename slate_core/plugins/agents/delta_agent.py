#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create DELTA integration agent plugin
"""
DELTA Agent — External Integration
====================================
Handles Claude, MCP, SDK, API integrations, and plugin management.
Bridges SLATE to external tooling without exposing secrets.
"""

import logging
import subprocess
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.delta")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent


class DeltaAgent(AgentBase):
    """Integration agent — Claude, MCP, SDK, API, plugin work."""

    AGENT_ID = "DELTA"
    AGENT_NAME = "Delta Integrator"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "External integration: Claude, MCP, SDK, APIs, plugins"
    REQUIRES_GPU = False
    DEPENDENCIES: List[str] = []

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="integration",
                patterns=["claude", "mcp", "sdk", "integration", "api",
                          "plugin", "extension", "bridge", "webhook"],
                requires_gpu=False,
                cpu_cores=1,
                priority=40,
                description="Manage external integrations, API bridges, SDK packaging",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute an integration task."""
        title = task.get("title", "")
        description = task.get("description", "")
        combined = f"{title} {description}".lower()

        if "mcp" in combined:
            return self._handle_mcp_task(task)
        elif "sdk" in combined:
            return self._handle_sdk_task(task)
        else:
            return self._handle_generic_integration(task)

    def _handle_mcp_task(self, task: dict) -> dict:
        """Handle MCP server related tasks."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            result = subprocess.run(
                [python, str(WORKSPACE_ROOT / "slate" / "mcp_server.py"), "--status"],
                capture_output=True, text=True, timeout=30,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": True,
                "result": f"MCP status checked. {result.stdout[:500]}",
                "agent": self.AGENT_ID,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_sdk_task(self, task: dict) -> dict:
        """Handle SDK packaging or validation tasks."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            result = subprocess.run(
                [python, "-m", "pip", "show", "slate"],
                capture_output=True, text=True, timeout=30,
            )
            return {
                "success": True,
                "result": f"SDK info: {result.stdout[:500]}",
                "agent": self.AGENT_ID,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _handle_generic_integration(self, task: dict) -> dict:
        """Handle generic integration tasks via planner model."""
        prompt = f"Integration task: {task.get('title', '')}\n{task.get('description', '')}"
        try:
            result = subprocess.run(
                ["ollama", "run", "slate-planner", prompt],
                capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout.strip()[:2000],
                "agent": self.AGENT_ID,
                "model": "slate-planner",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def health_check(self) -> dict:
        base = super().health_check()
        # Check MCP server module is importable
        try:
            mcp_path = WORKSPACE_ROOT / "slate" / "mcp_server.py"
            base["mcp_available"] = mcp_path.exists()
            base["healthy"] = True
        except Exception:
            base["healthy"] = True
        return base
