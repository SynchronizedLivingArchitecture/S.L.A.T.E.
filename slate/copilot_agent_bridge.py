#!/usr/bin/env python3
# Modified: 2026-02-07T12:00:00Z | Author: COPILOT
# Change: Create copilot agent bridge — shared queue between Python agents and @slate participant
"""
SLATE Copilot Agent Bridge
============================
Manages the shared task queue between the Python-side SLATE agent system
and the TypeScript-side @slate VS Code chat participant.

Architecture:
    ┌─────────────────────────────────────────────────────────┐
    │  Python Side (Agent Registry / Autonomous Loop)         │
    │                                                         │
    │  copilot_chat_agent.py → copilot_agent_bridge.py        │
    │         enqueue_task()      dequeue_result()             │
    └──────────────┬────────────────────┬─────────────────────┘
                   │                    │
          .slate_copilot_bridge.json    .slate_copilot_bridge_results.json
                   │                    │
    ┌──────────────┴────────────────────┴─────────────────────┐
    │  TypeScript Side (@slate Chat Participant)               │
    │                                                         │
    │  tools.ts → CopilotAgentBridgeTool                      │
    │        poll_tasks()       write_result()                 │
    └─────────────────────────────────────────────────────────┘

Usage:
    python slate/copilot_agent_bridge.py --status     # Bridge status
    python slate/copilot_agent_bridge.py --pending     # Show pending tasks
    python slate/copilot_agent_bridge.py --results     # Show completed results
    python slate/copilot_agent_bridge.py --cleanup     # Remove stale tasks
    python slate/copilot_agent_bridge.py --enqueue "task description"
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: workspace setup
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

BRIDGE_QUEUE_FILE = WORKSPACE_ROOT / ".slate_copilot_bridge.json"
BRIDGE_RESULTS_FILE = WORKSPACE_ROOT / ".slate_copilot_bridge_results.json"

# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: stale task threshold
STALE_THRESHOLD_S = 600  # 10 minutes


class CopilotAgentBridge:
    """Manages the shared task queue for @slate participant integration."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self._ensure_files()

    def _ensure_files(self):
        """Ensure bridge files exist."""
        now = datetime.now(timezone.utc).isoformat()
        if not BRIDGE_QUEUE_FILE.exists():
            BRIDGE_QUEUE_FILE.write_text(
                json.dumps({"tasks": [], "created_at": now}, indent=2),
                encoding="utf-8"
            )
        if not BRIDGE_RESULTS_FILE.exists():
            BRIDGE_RESULTS_FILE.write_text(
                json.dumps({"results": [], "created_at": now}, indent=2),
                encoding="utf-8"
            )

    # ─── Queue Operations (Python → TypeScript) ──────────────────────────

    def enqueue_task(self, title: str, description: str = "",
                     priority: str = "medium", source: str = "bridge",
                     tools_hint: list[str] | None = None) -> dict:
        """Add a task for the @slate participant to process."""
        task = {
            "id": f"bridge_{int(time.time())}_{id(self) % 10000}",
            "title": title[:200],
            "description": description[:2000],
            "priority": priority,
            "source": source,
            "agent": "COPILOT_CHAT",
            "status": "pending",
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
            "prompt": (
                f"AUTONOMOUS TASK: {title}\n\n"
                f"Details: {description}\n\n"
                "INSTRUCTION: Execute this task using your available SLATE tools. "
                "Follow the DIAGNOSE → ACT → VERIFY pattern."
            ),
            "tools_hint": tools_hint or [],
        }

        data = self._read_queue()
        data["tasks"].append(task)
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._write_queue(data)
        return task

    def get_pending_tasks(self) -> list[dict]:
        """Get all pending tasks waiting for participant."""
        data = self._read_queue()
        return [t for t in data.get("tasks", []) if t.get("status") == "pending"]

    def mark_task_processing(self, task_id: str) -> bool:
        """Mark a task as being processed by the participant."""
        data = self._read_queue()
        for task in data.get("tasks", []):
            if task.get("id") == task_id and task.get("status") == "pending":
                task["status"] = "processing"
                task["started_at"] = datetime.now(timezone.utc).isoformat()
                self._write_queue(data)
                return True
        return False

    def complete_task(self, task_id: str, success: bool, result: str = "",
                      tool_calls: int = 0, model: str = "copilot-chat") -> bool:
        """Write a task result and remove from pending queue."""
        # Write result
        results_data = self._read_results()
        results_data["results"].append({
            "task_id": task_id,
            "success": success,
            "result": result[:5000],
            "status": "completed",
            "tool_calls": tool_calls,
            "model": model,
            "completed_at": datetime.now(timezone.utc).isoformat(),
        })
        # Keep results trimmed
        if len(results_data["results"]) > 100:
            results_data["results"] = results_data["results"][-100:]
        results_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._write_results(results_data)

        # Remove from queue
        queue_data = self._read_queue()
        queue_data["tasks"] = [
            t for t in queue_data.get("tasks", []) if t.get("id") != task_id
        ]
        queue_data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._write_queue(queue_data)
        return True

    # ─── Status & Cleanup ────────────────────────────────────────────────

    def get_status(self) -> dict:
        """Get bridge status summary."""
        queue = self._read_queue()
        results = self._read_results()

        tasks = queue.get("tasks", [])
        pending = [t for t in tasks if t.get("status") == "pending"]
        processing = [t for t in tasks if t.get("status") == "processing"]

        all_results = results.get("results", [])
        succeeded = [r for r in all_results if r.get("success")]
        failed = [r for r in all_results if not r.get("success")]

        # Check for stale tasks
        now = datetime.now(timezone.utc)
        stale = 0
        for t in pending + processing:
            dispatched = t.get("dispatched_at", "")
            if dispatched:
                try:
                    dt = datetime.fromisoformat(dispatched.replace("Z", "+00:00"))
                    if (now - dt).total_seconds() > STALE_THRESHOLD_S:
                        stale += 1
                except Exception:
                    pass

        return {
            "queue_file": str(BRIDGE_QUEUE_FILE),
            "results_file": str(BRIDGE_RESULTS_FILE),
            "pending": len(pending),
            "processing": len(processing),
            "stale": stale,
            "total_results": len(all_results),
            "succeeded": len(succeeded),
            "failed": len(failed),
            "last_updated": queue.get("last_updated"),
        }

    def cleanup_stale(self) -> int:
        """Remove stale tasks (pending/processing > threshold)."""
        data = self._read_queue()
        now = datetime.now(timezone.utc)
        cleaned = 0
        remaining = []

        for task in data.get("tasks", []):
            dispatched = task.get("dispatched_at", "")
            if dispatched:
                try:
                    dt = datetime.fromisoformat(dispatched.replace("Z", "+00:00"))
                    if (now - dt).total_seconds() > STALE_THRESHOLD_S:
                        cleaned += 1
                        continue
                except Exception:
                    pass
            remaining.append(task)

        data["tasks"] = remaining
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._write_queue(data)
        return cleaned

    # ─── File I/O ────────────────────────────────────────────────────────

    def _read_queue(self) -> dict:
        try:
            return json.loads(BRIDGE_QUEUE_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"tasks": []}

    def _write_queue(self, data: dict):
        BRIDGE_QUEUE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _read_results(self) -> dict:
        try:
            return json.loads(BRIDGE_RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            return {"results": []}

    def _write_results(self, data: dict):
        BRIDGE_RESULTS_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    # ─── Display ─────────────────────────────────────────────────────────

    def print_status(self):
        """Print human-readable status."""
        s = self.get_status()
        print("=" * 60)
        print("  SLATE Copilot Agent Bridge")
        print("=" * 60)
        print(f"\n  Pending Tasks:   {s['pending']}")
        print(f"  Processing:      {s['processing']}")
        print(f"  Stale:           {s['stale']}")
        print(f"\n  Completed:       {s['succeeded']}")
        print(f"  Failed:          {s['failed']}")
        print(f"  Total Results:   {s['total_results']}")
        print(f"\n  Queue File:      {s['queue_file']}")
        print(f"  Last Updated:    {s.get('last_updated', 'N/A')}")
        print("\n" + "=" * 60)

    def print_pending(self):
        """Print pending tasks."""
        pending = self.get_pending_tasks()
        if not pending:
            print("No pending tasks in bridge queue.")
            return
        print(f"Pending tasks ({len(pending)}):")
        for t in pending:
            print(f"  [{t.get('priority', '?'):>8}] {t.get('title', '?')[:60]}")
            print(f"           ID: {t.get('id', '?')} | Source: {t.get('source', '?')}")
            print(f"           Dispatched: {t.get('dispatched_at', '?')}")
            print()

    def print_results(self):
        """Print recent results."""
        data = self._read_results()
        results = data.get("results", [])[-10:]
        if not results:
            print("No results in bridge.")
            return
        print(f"Recent results ({len(results)}):")
        for r in results:
            icon = "✓" if r.get("success") else "✗"
            print(f"  [{icon}] Task {r.get('task_id', '?')[:30]}")
            print(f"       Tools: {r.get('tool_calls', 0)} | Model: {r.get('model', '?')}")
            print(f"       Completed: {r.get('completed_at', '?')}")
            if r.get("result"):
                print(f"       Result: {r['result'][:80]}...")
            print()


def main():
    """CLI entry point."""
    # Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: add --complete for TypeScript bridge tool
    parser = argparse.ArgumentParser(description="SLATE Copilot Agent Bridge")
    parser.add_argument("--status", action="store_true", help="Show bridge status")
    parser.add_argument("--pending", action="store_true", help="Show pending tasks")
    parser.add_argument("--results", action="store_true", help="Show recent results")
    parser.add_argument("--cleanup", action="store_true", help="Remove stale tasks")
    parser.add_argument("--enqueue", type=str, help="Enqueue a task for @slate participant")
    parser.add_argument("--complete", type=str, metavar="TASK_ID", help="Complete a task by ID")
    parser.add_argument("--success", type=str, default="true", help="Task success (true/false)")
    parser.add_argument("--result", type=str, default="completed", help="Task result text")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()

    bridge = CopilotAgentBridge()

    if args.complete:
        success = args.success.lower() in ("true", "1", "yes")
        bridge.complete_task(
            task_id=args.complete,
            success=success,
            result=args.result,
        )
        print(f"Completed: {args.complete} (success={success})")
    elif args.enqueue:
        task = bridge.enqueue_task(args.enqueue)
        print(f"Enqueued: {task['id']}")
    elif args.pending:
        if args.json:
            tasks = bridge.get_pending_tasks()
            print(json.dumps({"pending": len(tasks), "tasks": tasks}, indent=2, default=str))
        else:
            bridge.print_pending()
    elif args.results:
        bridge.print_results()
    elif args.cleanup:
        cleaned = bridge.cleanup_stale()
        print(f"Cleaned {cleaned} stale tasks")
    elif args.json:
        print(json.dumps(bridge.get_status(), indent=2, default=str))
    else:
        bridge.print_status()


if __name__ == "__main__":
    main()
