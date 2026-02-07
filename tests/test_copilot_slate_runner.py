# Modified: 2026-02-07T13:42:00Z | Author: COPILOT | Change: Add test coverage for copilot_slate_runner module
"""
Tests for slate/copilot_slate_runner.py — CopilotSlateRunner state management,
queue operations, constants.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from slate.copilot_slate_runner import (
    CopilotSlateRunner,
    STATE_FILE,
    QUEUE_FILE,
    TASK_FILE,
    LOG_DIR,
    PID_FILE,
    WORKSPACE_ROOT,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_state_file_path(self):
        assert STATE_FILE.name == ".slate_copilot_runner.json"

    def test_queue_file_path(self):
        assert QUEUE_FILE.name == ".slate_copilot_queue.json"

    def test_task_file_path(self):
        assert TASK_FILE.name == "current_tasks.json"

    def test_log_dir(self):
        assert LOG_DIR.parts[-1] == "copilot_runner"
        assert LOG_DIR.parts[-2] == "slate_logs"

    def test_pid_file(self):
        assert PID_FILE.name == ".slate_copilot_runner.pid"


class TestLoadState:
    """Tests for CopilotSlateRunner._load_state default values."""

    def test_default_state_structure(self, tmp_path):
        with patch("slate.copilot_slate_runner.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner.state["status"] == "stopped"
                assert runner.state["started_at"] is None
                assert runner.state["pid"] is None
                assert runner.state["tasks_processed"] == 0
                assert runner.state["tasks_queued"] == 0
                assert runner.state["last_task"] is None
                assert isinstance(runner.state["copilot_requests"], list)

    def test_loads_existing_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "status": "running",
            "started_at": "2026-01-01T00:00:00Z",
            "pid": 1234,
            "tasks_processed": 10,
            "tasks_queued": 2,
            "last_task": "test task",
            "copilot_requests": [],
        }), encoding="utf-8")
        with patch("slate.copilot_slate_runner.STATE_FILE", state_file):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner.state["status"] == "running"
                assert runner.state["pid"] == 1234
                assert runner.state["tasks_processed"] == 10

    def test_corrupted_state_returns_default(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text("not valid json!!!", encoding="utf-8")
        with patch("slate.copilot_slate_runner.STATE_FILE", state_file):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner.state["status"] == "stopped"


class TestSaveState:
    """Tests for CopilotSlateRunner._save_state."""

    def test_save_creates_file(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("slate.copilot_slate_runner.STATE_FILE", state_file):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                runner.state["status"] = "running"
                runner._save_state()
                assert state_file.exists()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["status"] == "running"


class TestLazyLoading:
    """Tests for lazy-loaded components."""

    def test_autonomous_initially_none(self, tmp_path):
        with patch("slate.copilot_slate_runner.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner.autonomous is None

    def test_bridge_initially_none(self, tmp_path):
        with patch("slate.copilot_slate_runner.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner.bridge is None

    def test_running_flag_initially_true(self, tmp_path):
        with patch("slate.copilot_slate_runner.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.copilot_slate_runner.LOG_DIR", tmp_path / "logs"):
                runner = CopilotSlateRunner()
                assert runner._running is True
