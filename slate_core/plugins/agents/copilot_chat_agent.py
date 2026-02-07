#!/usr/bin/env python3
# Modified: 2026-02-07T12:00:00Z | Author: COPILOT
# Change: Create COPILOT_CHAT agent — @slate VS Code participant as subagent
"""
COPILOT_CHAT Agent — @slate Chat Participant Bridge
=====================================================
Integrates the @slate VS Code Copilot Chat participant into the SLATE
agent registry as a first-class subagent. Tasks routed to COPILOT_CHAT
are dispatched to the chat participant via a shared task queue, enabling
the LLM-powered participant to handle tasks that benefit from:

- Large language model reasoning (GPT-4/Claude via VS Code)
- Multi-tool chains across 22 registered SLATE tools
- Interactive code generation with workspace context
- Real-time streaming responses to the developer

Architecture:
    Autonomous Loop → AgentRegistry.route_task()
                          ↓
                    COPILOT_CHAT agent
                          ↓
              copilot_agent_bridge.py (shared queue)
                          ↓
                    @slate participant (VS Code)
                          ↓
                    22 LM Tools (diagnose, fix, verify)
                          ↓
              Result written back to shared queue
                          ↓
                    Autonomous loop picks up result

The bridge uses a file-based queue (.slate_copilot_bridge.json) for
cross-process communication between Python agents and the TypeScript
VS Code extension.
"""

import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.copilot_chat")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent

# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: bridge queue paths
BRIDGE_QUEUE_FILE = WORKSPACE_ROOT / ".slate_copilot_bridge.json"
BRIDGE_RESULTS_FILE = WORKSPACE_ROOT / ".slate_copilot_bridge_results.json"


class CopilotChatAgent(AgentBase):
    """@slate VS Code Chat Participant as a SLATE subagent.

    Routes tasks to the @slate participant in VS Code for LLM-powered
    multi-tool execution. The participant has access to 22 SLATE tools
    and can chain diagnostics, fixes, and verifications in a single turn.
    """

    AGENT_ID = "COPILOT_CHAT"
    AGENT_NAME = "Copilot Chat Participant"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = (
        "@slate VS Code chat participant — LLM-powered multi-tool agent with "
        "22 SLATE tools for diagnostics, code generation, service management, "
        "and autonomous task execution"
    )
    REQUIRES_GPU = False  # GPU is used by Ollama, not by this agent directly
    DEPENDENCIES: List[str] = []  # No agent dependencies; depends on VS Code

    # Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: task timeout
    TASK_TIMEOUT_S = 300  # 5 min max wait for participant response
    POLL_INTERVAL_S = 2   # Check for results every 2s

    def capabilities(self) -> List[AgentCapability]:
        """Copilot Chat handles interactive, multi-tool, and complex diagnostic tasks."""
        return [
            AgentCapability(
                name="interactive_diagnosis",
                patterns=["diagnose", "debug", "investigate", "explain", "why",
                          "troubleshoot", "root cause", "deep dive"],
                requires_gpu=False,
                cpu_cores=1,
                priority=15,
                description="Deep interactive diagnostics using LLM reasoning + 22 tools",
            ),
            AgentCapability(
                name="multi_tool_chain",
                patterns=["full protocol", "run protocol", "lock-in", "end-to-end",
                          "comprehensive", "full check", "all systems"],
                requires_gpu=False,
                cpu_cores=1,
                priority=10,
                description="Multi-tool chain execution (up to 15 rounds)",
            ),
            AgentCapability(
                name="code_review_explain",
                patterns=["review", "explain code", "what does", "how does",
                          "refactor suggestion", "architecture"],
                requires_gpu=False,
                cpu_cores=1,
                priority=20,
                description="LLM-powered code review and explanation",
            ),
            AgentCapability(
                name="service_orchestration",
                patterns=["start services", "deploy", "restart", "bring up",
                          "health check all", "system status"],
                requires_gpu=False,
                cpu_cores=1,
                priority=25,
                description="Service lifecycle management via SLATE tools",
            ),
            AgentCapability(
                name="security_audit",
                patterns=["security audit", "pii scan", "action guard",
                          "vulnerability", "compliance"],
                requires_gpu=False,
                cpu_cores=1,
                priority=20,
                description="Security scanning via ActionGuard + PII + SDK guards",
            ),
        ]

    def on_load(self) -> bool:
        """Initialize the bridge queue files."""
        try:
            # Ensure bridge queue exists
            if not BRIDGE_QUEUE_FILE.exists():
                BRIDGE_QUEUE_FILE.write_text(
                    json.dumps({"tasks": [], "created_at": datetime.now(timezone.utc).isoformat()},
                               indent=2),
                    encoding="utf-8"
                )
            if not BRIDGE_RESULTS_FILE.exists():
                BRIDGE_RESULTS_FILE.write_text(
                    json.dumps({"results": [], "created_at": datetime.now(timezone.utc).isoformat()},
                               indent=2),
                    encoding="utf-8"
                )
            logger.info("COPILOT_CHAT agent bridge initialized")
            return True
        except Exception as e:
            logger.error("Failed to initialize bridge: %s", e)
            return False

    def on_unload(self) -> None:
        """Clean up bridge state on unload."""
        logger.info("COPILOT_CHAT agent unloaded")

    def execute(self, task: dict) -> dict:
        """Dispatch task to @slate chat participant via bridge queue.

        The task is written to .slate_copilot_bridge.json and we poll
        .slate_copilot_bridge_results.json for completion.
        """
        task_id = task.get("id", f"chat_{int(time.time())}")
        title = task.get("title", "untitled")
        description = task.get("description", "")

        logger.info("Dispatching to @slate participant: %s", title[:60])

        # Build the bridge task
        bridge_task = {
            "id": task_id,
            "title": title,
            "description": description,
            "priority": task.get("priority", "medium"),
            "source": "agent_registry",
            "agent": "COPILOT_CHAT",
            "status": "pending",
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "prompt": self._build_prompt(task),
            "tools_hint": self._suggest_tools(task),
        }

        # Write to bridge queue
        try:
            self._enqueue_bridge_task(bridge_task)
        except Exception as e:
            return {"success": False, "error": f"Bridge queue write failed: {e}"}

        # Poll for result (with timeout)
        start = time.time()
        while time.time() - start < self.TASK_TIMEOUT_S:
            result = self._check_bridge_result(task_id)
            if result is not None:
                elapsed = round(time.time() - start, 1)
                logger.info("@slate participant completed: %s (%.1fs)", title[:40], elapsed)
                return {
                    "success": result.get("success", False),
                    "result": result.get("result", ""),
                    "agent": "COPILOT_CHAT",
                    "model": result.get("model", "copilot-chat"),
                    "tool_calls": result.get("tool_calls", 0),
                    "duration_s": elapsed,
                }
            time.sleep(self.POLL_INTERVAL_S)

        # Timeout — task stays in queue for participant to pick up later
        logger.warning("@slate participant did not respond within %ds for: %s",
                       self.TASK_TIMEOUT_S, title[:40])
        return {
            "success": False,
            "error": f"Participant did not respond within {self.TASK_TIMEOUT_S}s. "
                     "Task remains in bridge queue for the next @slate session.",
            "agent": "COPILOT_CHAT",
            "duration_s": self.TASK_TIMEOUT_S,
        }

    def _build_prompt(self, task: dict) -> str:
        """Build a prompt for the @slate participant from task data."""
        title = task.get("title", "")
        desc = task.get("description", "")
        file_paths = task.get("file_paths", "")

        prompt = f"AUTONOMOUS TASK: {title}"
        if desc:
            prompt += f"\n\nDetails: {desc}"
        if file_paths:
            prompt += f"\n\nRelevant files: {file_paths}"
        prompt += (
            "\n\nINSTRUCTION: Execute this task using your available SLATE tools. "
            "Follow the DIAGNOSE → ACT → VERIFY pattern. "
            "Report what you DID, not what could be done."
        )
        return prompt

    def _suggest_tools(self, task: dict) -> list[str]:
        """Suggest which SLATE tools the participant should use."""
        title = (task.get("title", "") + " " + task.get("description", "")).lower()
        suggestions = []

        tool_map = {
            "slate_systemStatus": ["health", "status", "check"],
            "slate_orchestrator": ["service", "start", "stop", "deploy", "dashboard"],
            "slate_workflow": ["task", "workflow", "cleanup", "stale"],
            "slate_runnerStatus": ["runner", "ci", "dispatch"],
            "slate_hardwareInfo": ["gpu", "cuda", "hardware", "optimize"],
            "slate_securityAudit": ["security", "audit", "pii", "guard"],
            "slate_autonomous": ["autonomous", "discover", "execute"],
            "slate_benchmark": ["benchmark", "performance"],
            "slate_executeWork": ["full pipeline", "execute work"],
        }

        for tool_name, keywords in tool_map.items():
            if any(kw in title for kw in keywords):
                suggestions.append(tool_name)

        return suggestions or ["slate_systemStatus", "slate_runProtocol"]

    def _enqueue_bridge_task(self, task: dict) -> None:
        """Add a task to the bridge queue file."""
        data = {"tasks": []}
        if BRIDGE_QUEUE_FILE.exists():
            try:
                data = json.loads(BRIDGE_QUEUE_FILE.read_text(encoding="utf-8"))
            except Exception:
                data = {"tasks": []}

        data["tasks"].append(task)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        BRIDGE_QUEUE_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")

    def _check_bridge_result(self, task_id: str) -> Optional[dict]:
        """Check if the participant has completed a task."""
        if not BRIDGE_RESULTS_FILE.exists():
            return None
        try:
            data = json.loads(BRIDGE_RESULTS_FILE.read_text(encoding="utf-8"))
            for result in data.get("results", []):
                if result.get("task_id") == task_id and result.get("status") == "completed":
                    return result
        except Exception:
            pass
        return None

    def health_check(self) -> dict:
        """Check if the bridge files are accessible and VS Code is responsive."""
        base = super().health_check()
        base["bridge_queue_exists"] = BRIDGE_QUEUE_FILE.exists()
        base["bridge_results_exists"] = BRIDGE_RESULTS_FILE.exists()

        # Check if there are stale pending tasks (>10 min without response)
        stale_count = 0
        if BRIDGE_QUEUE_FILE.exists():
            try:
                data = json.loads(BRIDGE_QUEUE_FILE.read_text(encoding="utf-8"))
                now = datetime.now(timezone.utc)
                for task in data.get("tasks", []):
                    if task.get("status") == "pending":
                        dispatched = task.get("dispatched_at", "")
                        if dispatched:
                            try:
                                dt = datetime.fromisoformat(dispatched.replace("Z", "+00:00"))
                                if (now - dt).total_seconds() > 600:
                                    stale_count += 1
                            except Exception:
                                pass
            except Exception:
                pass

        base["stale_tasks"] = stale_count
        base["healthy"] = base["bridge_queue_exists"] and stale_count < 5
        return base
