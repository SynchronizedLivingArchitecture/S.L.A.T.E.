# Modified: 2026-02-07T13:46:00Z | Author: COPILOT | Change: Add test coverage for integrated_autonomous_loop module
"""
Tests for slate/integrated_autonomous_loop.py — IntegratedAutonomousLoop
state management, health checks, component initialization.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from slate.integrated_autonomous_loop import (
    IntegratedAutonomousLoop,
    STATE_FILE,
    LOG_DIR,
    WORKSPACE_ROOT,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_state_file_path(self):
        assert STATE_FILE.name == ".slate_integrated_state.json"

    def test_log_dir(self):
        assert LOG_DIR.parts[-1] == "integrated"
        assert LOG_DIR.parts[-2] == "slate_logs"


class TestLoadState:
    """Tests for IntegratedAutonomousLoop state management."""

    def test_default_state(self, tmp_path):
        with patch("slate.integrated_autonomous_loop.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                assert loop.state["cycles"] == 0
                assert loop.state["started_at"] is None
                assert loop.state["components_healthy"] == 0
                assert loop.state["components_total"] == 7
                assert loop.state["tasks_completed"] == 0
                assert loop.state["tasks_failed"] == 0
                assert loop.state["self_heals"] == 0
                assert isinstance(loop.state["adaptations"], list)
                assert isinstance(loop.state["health_history"], list)

    def test_loads_existing_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "started_at": "2026-01-01T00:00:00Z",
            "cycles": 42,
            "last_cycle": "2026-01-01T01:00:00Z",
            "components_healthy": 6,
            "components_total": 7,
            "tasks_completed": 100,
            "tasks_failed": 5,
            "self_heals": 3,
            "adaptations": ["adapted-1"],
            "health_history": [],
        }), encoding="utf-8")
        with patch("slate.integrated_autonomous_loop.STATE_FILE", state_file):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                assert loop.state["cycles"] == 42
                assert loop.state["tasks_completed"] == 100
                assert loop.state["self_heals"] == 3

    def test_corrupted_state_returns_default(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("corrupted!!!", encoding="utf-8")
        with patch("slate.integrated_autonomous_loop.STATE_FILE", state_file):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                assert loop.state["cycles"] == 0


class TestSaveState:
    """Tests for _save_state."""

    def test_save_creates_file(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("slate.integrated_autonomous_loop.STATE_FILE", state_file):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                loop.state["cycles"] = 10
                loop._save_state()
                assert state_file.exists()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["cycles"] == 10


class TestLog:
    """Tests for _log method."""

    def test_log_creates_file(self, tmp_path):
        log_dir = tmp_path / "logs"
        with patch("slate.integrated_autonomous_loop.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", log_dir):
                loop = IntegratedAutonomousLoop()
                loop._log("test message")
                log_files = list(log_dir.glob("integrated_*.log"))
                assert len(log_files) == 1
                content = log_files[0].read_text(encoding="utf-8")
                assert "test message" in content
                assert "[INTEGRATED]" in content

    def test_log_includes_level(self, tmp_path):
        log_dir = tmp_path / "logs"
        with patch("slate.integrated_autonomous_loop.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", log_dir):
                loop = IntegratedAutonomousLoop()
                loop._log("error occurred", level="ERROR")
                content = list(log_dir.glob("*.log"))[0].read_text(encoding="utf-8")
                assert "[ERROR]" in content


class TestInitialization:
    """Tests for IntegratedAutonomousLoop init."""

    def test_components_empty_on_init(self, tmp_path):
        with patch("slate.integrated_autonomous_loop.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                assert loop._components == {}

    def test_workspace_set(self, tmp_path):
        with patch("slate.integrated_autonomous_loop.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.integrated_autonomous_loop.LOG_DIR", tmp_path / "logs"):
                loop = IntegratedAutonomousLoop()
                assert loop.workspace == WORKSPACE_ROOT
