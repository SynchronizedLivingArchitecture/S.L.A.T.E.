# Modified: 2026-02-07T13:35:00Z | Author: COPILOT | Change: Add test coverage for slate_unified_autonomous module
"""
Tests for slate/slate_unified_autonomous.py — agent routing patterns,
task classification, state management, stale detection.
"""

import json
import pytest
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import patch

from slate.slate_unified_autonomous import (
    AGENT_PATTERNS,
    UnifiedAutonomousLoop,
    TASK_FILE,
    STATE_FILE,
)


# ── Agent Routing Patterns ──────────────────────────────────────────────


class TestAgentPatterns:
    """Tests for agent routing pattern configuration."""

    def test_all_agents_defined(self):
        expected = ["ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "COPILOT", "COPILOT_CHAT"]
        for agent in expected:
            assert agent in AGENT_PATTERNS, f"Missing agent: {agent}"

    def test_alpha_handles_coding(self):
        assert "implement" in AGENT_PATTERNS["ALPHA"]
        assert "fix" in AGENT_PATTERNS["ALPHA"]
        assert "code" in AGENT_PATTERNS["ALPHA"]

    def test_beta_handles_testing(self):
        assert "test" in AGENT_PATTERNS["BETA"]
        assert "validate" in AGENT_PATTERNS["BETA"]

    def test_gamma_handles_analysis(self):
        assert "analyze" in AGENT_PATTERNS["GAMMA"]
        assert "plan" in AGENT_PATTERNS["GAMMA"]

    def test_copilot_chat_handles_diagnostics(self):
        assert "diagnose" in AGENT_PATTERNS["COPILOT_CHAT"]
        assert "investigate" in AGENT_PATTERNS["COPILOT_CHAT"]
        assert "troubleshoot" in AGENT_PATTERNS["COPILOT_CHAT"]


# ── UnifiedAutonomousLoop ───────────────────────────────────────────────


class TestUnifiedAutonomousLoop:
    """Tests for UnifiedAutonomousLoop class."""

    @pytest.fixture
    def loop(self, tmp_path):
        """Create a loop with temp workspace."""
        with patch("slate.slate_unified_autonomous.WORKSPACE_ROOT", tmp_path), \
             patch("slate.slate_unified_autonomous.STATE_FILE", tmp_path / ".state.json"), \
             patch("slate.slate_unified_autonomous.TASK_FILE", tmp_path / "tasks.json"), \
             patch("slate.slate_unified_autonomous.LOG_DIR", tmp_path / "logs"):
            loop = UnifiedAutonomousLoop()
            loop.workspace = tmp_path
            yield loop

    def test_initial_state(self, loop):
        assert loop.state["tasks_completed"] == 0
        assert loop.state["tasks_failed"] == 0
        assert loop.state["cycles"] == 0

    def test_classify_coding_task(self, loop):
        task = {"title": "Implement new feature", "description": "Add logging"}
        result = loop.classify_task(task)
        assert result["agent"] == "ALPHA"
        assert result["method"] == "pattern"

    def test_classify_testing_task(self, loop):
        task = {"title": "Validate integration tests", "description": "Check coverage"}
        result = loop.classify_task(task)
        assert result["agent"] == "BETA"

    def test_classify_analysis_task(self, loop):
        task = {"title": "Analyze performance bottleneck", "description": "Research approach"}
        result = loop.classify_task(task)
        assert result["agent"] == "GAMMA"

    def test_classify_diagnostic_task(self, loop):
        task = {"title": "Diagnose runner failure", "description": "Investigate CI issue"}
        result = loop.classify_task(task)
        assert result["agent"] == "COPILOT_CHAT"

    def test_classify_unknown_defaults_alpha(self, loop):
        # Prevent ML fallback — mock _get_ml to raise so routing falls through
        loop._get_ml = lambda: (_ for _ in ()).throw(RuntimeError("no ML"))
        task = {"title": "Misc task", "description": "Something generic"}
        result = loop.classify_task(task)
        assert result["agent"] == "ALPHA"
        assert result["method"] == "default"


# ── Stale Detection ────────────────────────────────────────────────────


class TestStaleDetection:
    """Tests for stale task detection."""

    @pytest.fixture
    def loop(self, tmp_path):
        with patch("slate.slate_unified_autonomous.WORKSPACE_ROOT", tmp_path), \
             patch("slate.slate_unified_autonomous.STATE_FILE", tmp_path / ".state.json"), \
             patch("slate.slate_unified_autonomous.TASK_FILE", tmp_path / "tasks.json"), \
             patch("slate.slate_unified_autonomous.LOG_DIR", tmp_path / "logs"):
            loop = UnifiedAutonomousLoop()
            loop.workspace = tmp_path
            yield loop

    def test_not_stale_if_not_in_progress(self, loop):
        task = {"status": "pending", "started_at": "2020-01-01T00:00:00Z"}
        assert loop._is_stale(task) is False

    def test_not_stale_if_recent(self, loop):
        recent = datetime.now(timezone.utc).isoformat()
        task = {"status": "in_progress", "started_at": recent}
        assert loop._is_stale(task) is False

    def test_stale_if_old(self, loop):
        old_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        task = {"status": "in_progress", "started_at": old_time}
        assert loop._is_stale(task) is True

    def test_not_stale_if_no_started_at(self, loop):
        task = {"status": "in_progress"}
        assert loop._is_stale(task) is False
