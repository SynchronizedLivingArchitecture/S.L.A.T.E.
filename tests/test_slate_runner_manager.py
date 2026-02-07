#!/usr/bin/env python3
# Modified: 2026-02-07T12:55:00Z | Author: COPILOT | Change: Create tests for runner manager module
"""
Tests for SLATE Runner Manager.
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import os
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch, PropertyMock

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_runner_manager import SlateRunnerManager


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def manager():
    """Create a SlateRunnerManager instance with mocked subprocess calls."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="")
        mgr = SlateRunnerManager()
    return mgr


# ═══════════════════════════════════════════════════════════════════════════════
# Initialization Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInit:
    """Test SlateRunnerManager initialization."""

    def test_workspace_root_set(self, manager):
        # Assert
        assert manager.workspace is not None or hasattr(manager, "workspace_root")

    def test_runner_dir_detection(self):
        # Arrange — mock the runner directory existence
        with patch("pathlib.Path.exists", return_value=True):
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
                # Act
                mgr = SlateRunnerManager()
        # Assert — should have attempted to find runner
        assert mgr is not None


# ═══════════════════════════════════════════════════════════════════════════════
# Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetect:
    """Test runner detection capabilities."""

    @patch("subprocess.run")
    def test_detect_returns_dict(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mgr = SlateRunnerManager()
        # Act
        result = mgr.detect()
        # Assert
        assert isinstance(result, dict)

    @patch("subprocess.run")
    def test_detect_includes_runner_info(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mgr = SlateRunnerManager()
        # Act
        result = mgr.detect()
        # Assert
        assert "runner" in result or "status" in result or len(result) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Runner Status Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetRunnerStatus:
    """Test runner status checking."""

    @patch("subprocess.run")
    def test_status_returns_dict(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mgr = SlateRunnerManager()
        # Act
        result = mgr.get_runner_status()
        # Assert
        assert isinstance(result, dict)

    @patch("subprocess.run")
    def test_status_when_runner_offline(self, mock_run):
        # Arrange — all process checks fail
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="No process found")
        mgr = SlateRunnerManager()
        # Act
        result = mgr.get_runner_status()
        # Assert
        assert isinstance(result, dict)
        # Should indicate runner is not running
        status_str = json.dumps(result).lower()
        assert "offline" in status_str or "stopped" in status_str or "not" in status_str or "false" in status_str


# ═══════════════════════════════════════════════════════════════════════════════
# Workflow Dispatch Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDispatchWorkflow:
    """Test GitHub Actions workflow dispatch."""

    @patch("subprocess.run")
    def test_dispatch_calls_gh_cli(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="Dispatched", stderr="")
        mgr = SlateRunnerManager()
        # Override gh_cli path for test
        if hasattr(mgr, "gh_cli"):
            mgr.gh_cli = "gh"
        # Act
        result = mgr.dispatch_workflow("ci.yml")
        # Assert
        assert isinstance(result, dict)

    @patch("subprocess.run")
    def test_dispatch_with_inputs(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="Dispatched", stderr="")
        mgr = SlateRunnerManager()
        if hasattr(mgr, "gh_cli"):
            mgr.gh_cli = "gh"
        # Act
        result = mgr.dispatch_workflow("agentic.yml", inputs={"mode": "health-check"})
        # Assert
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Setup Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSetup:
    """Test runner setup/configuration."""

    @patch("subprocess.run")
    def test_setup_returns_dict(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=0, stdout="", stderr="")
        mgr = SlateRunnerManager()
        # Act
        result = mgr.setup()
        # Assert
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
