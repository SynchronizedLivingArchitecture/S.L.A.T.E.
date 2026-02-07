#!/usr/bin/env python3
# Modified: 2026-02-07T10:45:00Z | Author: COPILOT | Change: Agentic AI prompt engineering for SLATE controls
"""
SLATE Agentic Control Intelligence
====================================
Local ML-powered prompt engineering for SLATE control buttons.

Uses Ollama (slate-fast 3B) for:
  1. Pre-flight analysis — Recommend actions based on system state
  2. Post-action summaries — Explain results in natural language
  3. Error recovery — Suggest fixes when controls fail
  4. Usage patterns — Adaptive button ordering based on history

All inference is LOCAL ONLY (127.0.0.1:11434).
"""

import json
import urllib.request
import urllib.error
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Any


OLLAMA_URL = "http://127.0.0.1:11434"
FAST_MODEL = "slate-fast"
HISTORY_FILE = Path(__file__).parent / "slate_memory" / "control_history.json"


class SlateControlIntelligence:
    """ML-powered intelligence layer for SLATE dashboard controls."""

    # Modified: 2026-02-07T10:45:00Z | Author: COPILOT | Change: Initial implementation

    PROMPTS = {
        "pre-flight": (
            "You are SLATE, an AI system operator. Given the current system state, "
            "recommend the single most important action the user should take next. "
            "Be extremely concise (1-2 sentences). State format: {state}"
        ),
        "post-action": (
            "You are SLATE. Summarize this action result in one clear sentence. "
            "Action: {action}. Output: {output}"
        ),
        "error-recovery": (
            "You are SLATE. This action failed: {action}. Error: {error}. "
            "Suggest one fix in 1-2 sentences."
        ),
        "smart-order": (
            "You are SLATE. Given this usage history, rank these 8 controls "
            "by predicted next use: {controls}. History: {history}. "
            "Return only a JSON list of control names in order."
        ),
    }

    def __init__(self):
        self._history: List[Dict] = []
        self._load_history()

    def _load_history(self):
        """Load control usage history from disk."""
        try:
            if HISTORY_FILE.exists():
                with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                    self._history = json.load(f)
        except (json.JSONDecodeError, IOError):
            self._history = []

    def _save_history(self):
        """Persist control usage history."""
        try:
            HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
            # Keep last 200 entries
            trimmed = self._history[-200:]
            with open(HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump(trimmed, f, indent=2)
        except IOError:
            pass

    def record_action(self, action: str, success: bool, duration_ms: int = 0):
        """Record a control action for usage pattern learning."""
        self._history.append({
            "action": action,
            "success": success,
            "duration_ms": duration_ms,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._save_history()

    def _ollama_generate(self, prompt: str, model: str = FAST_MODEL, timeout: int = 10) -> Optional[str]:
        """Call Ollama generate API. Returns None if unavailable."""
        try:
            body = json.dumps({
                "model": model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "num_predict": 100,
                    "temperature": 0.3,
                }
            }).encode("utf-8")
            req = urllib.request.Request(
                f"{OLLAMA_URL}/api/generate",
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                return data.get("response", "").strip()
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError):
            return None

    def pre_flight(self, system_state: Dict[str, Any]) -> Optional[str]:
        """Analyze system state and recommend next action."""
        state_summary = json.dumps({
            "gpu_count": system_state.get("gpu_count", 0),
            "cpu_pct": system_state.get("cpu_percent", 0),
            "mem_pct": system_state.get("memory_percent", 0),
            "pending_tasks": system_state.get("pending_tasks", 0),
            "runner_online": system_state.get("runner_online", False),
            "ollama_online": system_state.get("ollama_online", False),
            "last_action": self._history[-1]["action"] if self._history else "none",
        }, indent=0)
        prompt = self.PROMPTS["pre-flight"].format(state=state_summary)
        return self._ollama_generate(prompt)

    def post_action_summary(self, action: str, output: str) -> Optional[str]:
        """Generate a natural language summary of an action result."""
        # Truncate long output
        truncated = output[:300] if len(output) > 300 else output
        prompt = self.PROMPTS["post-action"].format(action=action, output=truncated)
        return self._ollama_generate(prompt)

    def error_recovery(self, action: str, error: str) -> Optional[str]:
        """Suggest a fix for a failed action."""
        truncated = error[:300] if len(error) > 300 else error
        prompt = self.PROMPTS["error-recovery"].format(action=action, error=truncated)
        return self._ollama_generate(prompt)

    def get_usage_stats(self) -> Dict[str, Any]:
        """Return usage statistics for dashboard rendering."""
        if not self._history:
            return {"total_actions": 0, "actions": {}, "success_rate": 0.0}

        action_counts: Dict[str, int] = {}
        success_count = 0
        for entry in self._history:
            action_counts[entry["action"]] = action_counts.get(entry["action"], 0) + 1
            if entry.get("success"):
                success_count += 1

        return {
            "total_actions": len(self._history),
            "actions": action_counts,
            "success_rate": round(success_count / len(self._history) * 100, 1),
            "most_used": max(action_counts, key=action_counts.get) if action_counts else None,
            "recent": self._history[-5:],
        }

    def get_recommended_order(self) -> List[str]:
        """Return controls ordered by predicted next use (heuristic, no ML call)."""
        controls = [
            "run-protocol", "update", "debug", "benchmark",
            "deploy", "security", "agents", "gpu"
        ]
        if not self._history:
            return controls

        # Score by recency + frequency
        scores: Dict[str, float] = {c: 0.0 for c in controls}
        for i, entry in enumerate(self._history):
            action = entry["action"]
            if action in scores:
                recency_weight = (i + 1) / len(self._history)  # More recent = higher
                scores[action] += 1.0 + recency_weight

        return sorted(controls, key=lambda c: scores.get(c, 0), reverse=True)


# ─── Singleton instance for the dashboard server ──────────────────────────────
_instance: Optional[SlateControlIntelligence] = None


def get_intelligence() -> SlateControlIntelligence:
    """Get or create the singleton intelligence instance."""
    global _instance
    if _instance is None:
        _instance = SlateControlIntelligence()
    return _instance


if __name__ == "__main__":
    intel = get_intelligence()
    print("SLATE Control Intelligence")
    print(f"  History entries: {len(intel._history)}")
    print(f"  Usage stats: {json.dumps(intel.get_usage_stats(), indent=2)}")
    print(f"  Recommended order: {intel.get_recommended_order()}")

    # Test pre-flight if Ollama is available
    rec = intel.pre_flight({"gpu_count": 2, "pending_tasks": 3, "runner_online": True, "ollama_online": True})
    if rec:
        print(f"  AI recommendation: {rec}")
    else:
        print("  AI recommendation: (Ollama unavailable)")
