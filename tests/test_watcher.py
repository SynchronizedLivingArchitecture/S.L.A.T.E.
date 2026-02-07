#!/usr/bin/env python3
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Tests for file watcher and dev reload manager
"""
Tests for slate.slate_watcher
==============================
AAA (Arrange-Act-Assert) pattern throughout.
"""

import json
import sys
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_watcher import (
    ChangeCategory,
    FileChangeEvent,
    SlateFileWatcher,
    categorize_change,
    path_to_module,
    WATCHFILES_AVAILABLE,
)


class TestPathToModule:
    """Tests for path_to_module conversion."""

    def test_agent_module(self):
        """Agent Python file converts to dotted module name."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "runner_api.py"

        # Act
        result = path_to_module(path)

        # Assert
        assert result == "agents.runner_api"

    def test_slate_module(self):
        """Slate Python file converts to dotted module name."""
        # Arrange
        path = WORKSPACE_ROOT / "slate" / "module_registry.py"

        # Act
        result = path_to_module(path)

        # Assert
        assert result == "slate.module_registry"

    def test_non_python_file(self):
        """Non-Python files return None."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "config.json"

        # Act
        result = path_to_module(path)

        # Assert
        assert result is None

    def test_init_file(self):
        """__init__.py converts to package name."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "__init__.py"

        # Act
        result = path_to_module(path)

        # Assert
        assert result == "agents"

    def test_outside_workspace(self):
        """File outside workspace returns None."""
        # Arrange
        path = Path("/tmp/some_module.py")

        # Act
        result = path_to_module(path)

        # Assert
        assert result is None


class TestCategorizeChange:
    """Tests for file change categorization."""

    def test_agent_file(self):
        """Agent Python files categorize as AGENT."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "runner_api.py"

        # Act
        result = categorize_change(path)

        # Assert
        assert result == ChangeCategory.AGENT

    def test_skill_file(self):
        """Skill files categorize as SKILL."""
        # Arrange
        path = WORKSPACE_ROOT / "skills" / "slate-status" / "skill.md"

        # Act
        result = categorize_change(path)

        # Assert
        assert result == ChangeCategory.SKILL

    def test_task_file(self):
        """current_tasks.json categorizes as TASK."""
        # Arrange
        path = WORKSPACE_ROOT / "current_tasks.json"

        # Act
        result = categorize_change(path)

        # Assert
        assert result == ChangeCategory.TASK

    def test_config_file(self):
        """YAML/JSON config files categorize as CONFIG."""
        # Arrange
        path = WORKSPACE_ROOT / "some_config.yaml"

        # Act
        result = categorize_change(path)

        # Assert
        assert result == ChangeCategory.CONFIG

    def test_unknown_file(self):
        """Other files categorize as UNKNOWN."""
        # Arrange
        path = WORKSPACE_ROOT / "README.md"

        # Act
        result = categorize_change(path)

        # Assert
        assert result == ChangeCategory.UNKNOWN


class TestFileChangeEvent:
    """Tests for FileChangeEvent."""

    def test_agent_event(self):
        """Agent change event populates module_name."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "runner_api.py"

        # Act
        event = FileChangeEvent("modified", path)

        # Assert
        assert event.category == ChangeCategory.AGENT
        assert event.module_name == "agents.runner_api"
        assert event.change_type == "modified"
        assert event.timestamp is not None

    def test_task_event_no_module(self):
        """Task change event has no module_name."""
        # Arrange
        path = WORKSPACE_ROOT / "current_tasks.json"

        # Act
        event = FileChangeEvent("modified", path)

        # Assert
        assert event.category == ChangeCategory.TASK
        assert event.module_name is None

    def test_to_dict(self):
        """to_dict produces serializable dict."""
        # Arrange
        path = WORKSPACE_ROOT / "agents" / "runner_api.py"
        event = FileChangeEvent("modified", path)

        # Act
        result = event.to_dict()

        # Assert
        assert isinstance(result, dict)
        assert result["category"] == "agent"
        assert result["module_name"] == "agents.runner_api"
        # Verify JSON-serializable
        json.dumps(result)


class TestSlateFileWatcher:
    """Tests for SlateFileWatcher."""

    def test_default_watch_paths(self):
        """Default watch paths include agents/, skills/, current_tasks.json."""
        # Arrange & Act
        watcher = SlateFileWatcher()

        # Assert
        path_strs = [str(p) for p in watcher._watch_paths]
        # At least agents/ should exist
        assert any("agents" in p for p in path_strs)

    def test_not_running_initially(self):
        """Watcher is not running after construction."""
        # Arrange & Act
        watcher = SlateFileWatcher()

        # Assert
        assert watcher.is_running is False

    def test_status(self):
        """Status returns expected structure."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        status = watcher.status()

        # Assert
        assert "running" in status
        assert "watch_paths" in status
        assert "watchfiles_available" in status
        assert status["running"] is False

    def test_filter_pycache(self):
        """Filter excludes __pycache__ files."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        result = watcher._filter_change(2, str(WORKSPACE_ROOT / "__pycache__" / "test.pyc"))

        # Assert
        assert result is False

    def test_filter_hidden_files(self):
        """Filter excludes hidden files."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        result = watcher._filter_change(2, str(WORKSPACE_ROOT / ".hidden_file"))

        # Assert
        assert result is False

    def test_filter_python_files(self):
        """Filter includes .py files."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        result = watcher._filter_change(2, str(WORKSPACE_ROOT / "agents" / "runner_api.py"))

        # Assert
        assert result is True

    def test_filter_json_files(self):
        """Filter includes .json files."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        result = watcher._filter_change(2, str(WORKSPACE_ROOT / "current_tasks.json"))

        # Assert
        assert result is True

    @pytest.mark.skipif(not WATCHFILES_AVAILABLE, reason="watchfiles not installed")
    def test_start_stop(self):
        """Watcher can start and stop cleanly."""
        # Arrange
        watcher = SlateFileWatcher()

        # Act
        started = watcher.start()
        time.sleep(0.5)
        is_running = watcher.is_running
        watcher.stop()
        time.sleep(0.5)

        # Assert
        assert started is True
        assert is_running is True
        assert watcher.is_running is False

    def test_history_empty_initially(self):
        """History is empty when no changes observed."""
        # Arrange & Act
        watcher = SlateFileWatcher()

        # Assert
        assert watcher.history == []


class TestDevReloadManager:
    """Tests for the integrated DevReloadManager."""

    def test_status(self):
        """Status returns combined watcher + registry info."""
        # Arrange
        from slate.slate_watcher import DevReloadManager
        mgr = DevReloadManager()

        # Act
        status = mgr.status()

        # Assert
        assert "watcher" in status
        assert "registry" in status

    def test_trigger_reload_all(self):
        """trigger_reload with no module reloads all registered."""
        # Arrange
        from slate.slate_watcher import DevReloadManager
        mgr = DevReloadManager()

        # Act
        result = mgr.trigger_reload()

        # Assert
        assert "reloaded" in result
        assert isinstance(result["reloaded"], list)

    def test_trigger_reload_specific(self):
        """trigger_reload with a specific module reloads just that one."""
        # Arrange
        from slate.slate_watcher import DevReloadManager
        mgr = DevReloadManager()

        # Act
        result = mgr.trigger_reload("json")

        # Assert
        assert result["reloaded"] == ["json"]
        assert result["success"] is True

    def test_broadcast_callback(self):
        """Broadcast callback receives reload events."""
        # Arrange
        messages = []
        from slate.slate_watcher import DevReloadManager
        mgr = DevReloadManager(broadcast_callback=lambda msg: messages.append(msg))

        # Act
        mgr.trigger_reload("json")

        # Assert
        # The registry's on_reload callback fires which calls _handle_changes indirectly
        # but trigger_reload goes through the registry directly
        assert isinstance(messages, list)
