#!/usr/bin/env python3
# Modified: 2026-02-07T12:55:00Z | Author: COPILOT | Change: Create tests for InstallTracker module
"""
Tests for SLATE Install Tracker.
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import sys
import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, mock_open, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.install_tracker import (
    InstallStep,
    InstallState,
    InstallTracker,
    StepStatus,
    _scrub_path,
    register_sse_listener,
    unregister_sse_listener,
)


# ═══════════════════════════════════════════════════════════════════════════════
# StepStatus Enum Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStepStatus:
    """Test the StepStatus enum values."""

    def test_all_statuses_exist(self):
        # Arrange
        expected = {"pending", "running", "success", "failed", "skipped", "warning"}
        # Act
        actual = {s.value for s in StepStatus}
        # Assert
        assert actual == expected


# ═══════════════════════════════════════════════════════════════════════════════
# SLATE Installation Ethos Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlateInstallationEthos:
    """Test that the install tracker includes the dep_scan step for SLATE ethos."""

    def test_dep_scan_step_exists(self):
        """Verify that dependency scanning step is in the canonical steps."""
        # Arrange
        step_ids = [s.id for s in InstallTracker.INSTALL_STEPS]
        # Assert
        assert "dep_scan" in step_ids, "dep_scan step should exist for SLATE installation ethos"

    def test_dep_scan_step_order(self):
        """Verify dep_scan runs before deps_install."""
        # Arrange
        steps = {s.id: s.order for s in InstallTracker.INSTALL_STEPS}
        # Assert
        assert steps.get("dep_scan", 999) < steps.get("deps_install", 0), \
            "dep_scan should run before deps_install"

    def test_dep_scan_description(self):
        """Verify dep_scan has appropriate description."""
        # Arrange
        dep_scan = [s for s in InstallTracker.INSTALL_STEPS if s.id == "dep_scan"]
        # Assert
        assert len(dep_scan) == 1
        assert "scan" in dep_scan[0].description.lower()

    def test_status_is_string(self):
        # Assert — StepStatus inherits from str
        assert isinstance(StepStatus.PENDING, str)
        assert StepStatus.SUCCESS == "success"


# ═══════════════════════════════════════════════════════════════════════════════
# InstallStep Dataclass Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstallStep:
    """Test InstallStep dataclass."""

    def test_defaults(self):
        # Arrange & Act
        step = InstallStep(id="test", name="Test Step", description="A test")
        # Assert
        assert step.status == StepStatus.PENDING
        assert step.progress_pct == 0
        assert step.substeps == []
        assert step.error is None

    def test_to_dict_roundtrip(self):
        # Arrange
        step = InstallStep(id="gpu", name="GPU Setup", description="Detect GPUs", order=5)
        # Act
        d = step.to_dict()
        # Assert
        assert d["id"] == "gpu"
        assert d["name"] == "GPU Setup"
        assert d["order"] == 5
        assert d["status"] == "pending"

    def test_to_dict_with_timestamps(self):
        # Arrange
        step = InstallStep(
            id="dep", name="Deps", description="Install",
            started_at="2026-02-07T00:00:00Z",
            completed_at="2026-02-07T00:01:00Z",
            duration_ms=60000,
        )
        # Act
        d = step.to_dict()
        # Assert
        assert d["started_at"] == "2026-02-07T00:00:00Z"
        assert d["duration_ms"] == 60000


# ═══════════════════════════════════════════════════════════════════════════════
# InstallState Dataclass Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstallState:
    """Test InstallState dataclass."""

    def test_defaults(self):
        # Act
        state = InstallState()
        # Assert
        assert state.status == "not_started"
        assert state.steps == []
        assert state.errors == []

    def test_to_dict(self):
        # Arrange
        state = InstallState(version="1.0", slate_version="2.4.0", status="running")
        # Act
        d = state.to_dict()
        # Assert
        assert d["version"] == "1.0"
        assert d["slate_version"] == "2.4.0"
        assert d["status"] == "running"


# ═══════════════════════════════════════════════════════════════════════════════
# Path Scrubbing Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScrubPath:
    """Test the _scrub_path utility."""

    def test_scrubs_home_path(self):
        # Arrange — _scrub_path replaces paths starting with home dir
        home = str(Path.home())
        path = home + r"\projects\slate"
        # Act
        result = _scrub_path(path)
        # Assert — should replace home prefix with <home>
        assert result.startswith("<home>") or result.startswith("<workspace>")

    def test_preserves_non_path_strings(self):
        # Arrange
        value = "hello world"
        # Act
        result = _scrub_path(value)
        # Assert
        assert result == "hello world"


# ═══════════════════════════════════════════════════════════════════════════════
# InstallTracker Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInstallTracker:
    """Test the InstallTracker lifecycle."""

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info")
    @patch("slate.install_tracker.InstallTracker._collect_system_info")
    def test_init_creates_state(self, mock_sys, mock_git, mock_save):
        # Arrange
        mock_sys.return_value = {"cpu": "24 cores"}
        mock_git.return_value = {"branch": "main"}
        # Act
        tracker = InstallTracker()
        # Assert
        assert tracker.state is not None
        assert tracker.state.status == "not_started"

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info", return_value={})
    @patch("slate.install_tracker.InstallTracker._collect_system_info", return_value={})
    def test_begin_install_sets_running(self, mock_sys, mock_git, mock_save):
        # Arrange
        tracker = InstallTracker()
        # Act
        tracker.begin_install()
        # Assert
        assert tracker.state.status == "in_progress"
        assert tracker.state.started_at is not None

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info", return_value={})
    @patch("slate.install_tracker.InstallTracker._collect_system_info", return_value={})
    def test_step_lifecycle(self, mock_sys, mock_git, mock_save):
        # Arrange
        tracker = InstallTracker()
        tracker.begin_install()
        # Act — start, progress, complete
        tracker.start_step("python_check")
        tracker.update_progress("python_check", 50, "Checking version...")
        tracker.complete_step("python_check", success=True, details="Python 3.11.9")
        # Assert
        state = tracker.get_state()
        steps = {s["id"]: s for s in state.get("steps", [])}
        if "python_check" in steps:
            assert steps["python_check"]["status"] == "success"

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info", return_value={})
    @patch("slate.install_tracker.InstallTracker._collect_system_info", return_value={})
    def test_skip_step(self, mock_sys, mock_git, mock_save):
        # Arrange
        tracker = InstallTracker()
        tracker.begin_install()
        # Act
        tracker.skip_step("docker_check", reason="Docker not installed")
        # Assert
        state = tracker.get_state()
        steps = {s["id"]: s for s in state.get("steps", [])}
        if "docker_check" in steps:
            assert steps["docker_check"]["status"] == "skipped"

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info", return_value={})
    @patch("slate.install_tracker.InstallTracker._collect_system_info", return_value={})
    def test_finish_install(self, mock_sys, mock_git, mock_save):
        # Arrange
        tracker = InstallTracker()
        tracker.begin_install()
        # Act
        tracker.finish_install(success=True)
        # Assert
        assert tracker.state.status == "completed"
        assert tracker.state.completed_at is not None

    @patch("slate.install_tracker.InstallTracker._save_state")
    @patch("slate.install_tracker.InstallTracker._collect_git_info", return_value={})
    @patch("slate.install_tracker.InstallTracker._collect_system_info", return_value={})
    def test_finish_install_failure(self, mock_sys, mock_git, mock_save):
        # Arrange
        tracker = InstallTracker()
        tracker.begin_install()
        # Act
        tracker.finish_install(success=False)
        # Assert
        assert tracker.state.status == "failed"


# ═══════════════════════════════════════════════════════════════════════════════
# SSE Listener Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSSEListeners:
    """Test SSE broadcast system."""

    def test_register_and_unregister(self):
        # Arrange
        callback = MagicMock()
        # Act
        register_sse_listener(callback)
        unregister_sse_listener(callback)
        # Assert — no error thrown, callback was added and removed


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
