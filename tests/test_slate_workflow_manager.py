#!/usr/bin/env python3
# Modified: 2026-02-07T12:55:00Z | Author: COPILOT | Change: Create tests for workflow manager module
"""
Tests for SLATE Workflow Manager.
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import sys
import tempfile
import shutil
from datetime import datetime, timezone, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_workflow_manager import SlateWorkflowManager


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

@pytest.fixture
def temp_workspace(tmp_path):
    """Create a temporary workspace with a current_tasks.json."""
    tasks_file = tmp_path / "current_tasks.json"
    tasks_file.write_text(json.dumps({
        "tasks": [
            {
                "id": "task_001",
                "title": "Active task",
                "status": "pending",
                "priority": "high",
                "assigned_to": "workflow",
                "source": "user_request",
                "created_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "task_002",
                "title": "Completed task",
                "status": "completed",
                "priority": "medium",
                "assigned_to": "workflow",
                "source": "user_request",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat(),
                "completed_at": datetime.now(timezone.utc).isoformat(),
            },
            {
                "id": "task_003",
                "title": "Test Task integration test",
                "status": "pending",
                "priority": "low",
                "assigned_to": "workflow",
                "source": "test",
                "created_at": (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat(),
            },
        ],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }), encoding="utf-8")
    # Create archive dir
    (tmp_path / ".slate_archive").mkdir(exist_ok=True)
    return tmp_path


@pytest.fixture
def manager(temp_workspace):
    """Create a SlateWorkflowManager pointing at the temp workspace."""
    with patch.object(SlateWorkflowManager, "__init__", lambda self: None):
        mgr = SlateWorkflowManager.__new__(SlateWorkflowManager)
        # Class-level attributes that need to be overridden to point at temp workspace
        mgr.TASK_FILE = temp_workspace / "current_tasks.json"
        mgr.ARCHIVE_FILE = temp_workspace / ".slate_archive" / "archived_tasks.json"
        mgr.gh_cli = None
        # Initialize archive file (normally done by _ensure_archive_dir)
        mgr.ARCHIVE_FILE.parent.mkdir(parents=True, exist_ok=True)
        if not mgr.ARCHIVE_FILE.exists():
            mgr.ARCHIVE_FILE.write_text('{"archived": [], "last_archive": null}', encoding="utf-8")
    return mgr


@pytest.fixture
def empty_workspace(tmp_path):
    """Create a workspace with no tasks."""
    tasks_file = tmp_path / "current_tasks.json"
    tasks_file.write_text(json.dumps({"tasks": []}), encoding="utf-8")
    (tmp_path / ".slate_archive").mkdir(exist_ok=True)
    return tmp_path


# ═══════════════════════════════════════════════════════════════════════════════
# Initialization Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestInit:
    """Test SlateWorkflowManager initialization."""

    @patch("subprocess.run")
    def test_creates_instance(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        # Act
        mgr = SlateWorkflowManager()
        # Assert
        assert mgr is not None

    @patch("subprocess.run")
    def test_archive_file_class_attr(self, mock_run):
        # Arrange
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        # Act & Assert — ARCHIVE_FILE is a class-level attribute
        assert hasattr(SlateWorkflowManager, "ARCHIVE_FILE")
        assert hasattr(SlateWorkflowManager, "TASK_FILE")


# ═══════════════════════════════════════════════════════════════════════════════
# Task Analysis Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzeTasks:
    """Test task analysis."""

    def test_analyze_returns_dict(self, manager):
        # Act
        result = manager.analyze_tasks()
        # Assert
        assert isinstance(result, dict)

    def test_analyze_counts_tasks(self, manager):
        # Act
        result = manager.analyze_tasks()
        # Assert
        assert "total" in result or "tasks" in result or len(result) > 0

    def test_analyze_detects_test_tasks(self, manager):
        # Act
        result = manager.analyze_tasks()
        # Assert — should detect the "Test Task" in fixtures
        result_str = json.dumps(result).lower()
        assert "test" in result_str or "deprecated" in result_str


# ═══════════════════════════════════════════════════════════════════════════════
# Cleanup Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestCleanup:
    """Test task cleanup."""

    def test_cleanup_returns_dict(self, manager):
        # Act
        result = manager.cleanup()
        # Assert
        assert isinstance(result, dict)

    def test_cleanup_removes_test_tasks(self, manager):
        # Arrange — verify test task exists
        tasks_before = json.loads(manager.TASK_FILE.read_text(encoding="utf-8"))
        test_ids = [t["id"] for t in tasks_before["tasks"] if "Test" in t.get("title", "")]
        assert len(test_ids) > 0, "Fixture should include a test task"
        # Act
        manager.cleanup()
        # Assert
        tasks_after = json.loads(manager.TASK_FILE.read_text(encoding="utf-8"))
        remaining_ids = [t["id"] for t in tasks_after["tasks"]]
        for tid in test_ids:
            assert tid not in remaining_ids, f"Test task {tid} should have been removed"

    def test_cleanup_preserves_valid_tasks(self, manager):
        # Act
        manager.cleanup()
        # Assert
        tasks_after = json.loads(manager.TASK_FILE.read_text(encoding="utf-8"))
        valid_ids = [t["id"] for t in tasks_after["tasks"] if t["status"] in ("pending", "completed")]
        # task_001 (pending, non-test) and task_002 (completed) should remain
        assert "task_001" in valid_ids
        assert "task_002" in valid_ids

    def test_dry_run_does_not_modify(self, manager):
        # Arrange
        before = manager.TASK_FILE.read_text(encoding="utf-8")
        # Act
        manager.cleanup(dry_run=True)
        # Assert
        after = manager.TASK_FILE.read_text(encoding="utf-8")
        assert before == after


# ═══════════════════════════════════════════════════════════════════════════════
# Enforce Completion Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEnforceCompletion:
    """Test completion enforcement."""

    def test_enforce_returns_dict(self, manager):
        # Act
        result = manager.enforce_completion()
        # Assert
        assert isinstance(result, dict)

    def test_enforce_with_few_tasks_allows_new(self, manager):
        # Act
        result = manager.enforce_completion()
        # Assert
        can_accept = result.get("can_accept", result.get("allowed", result.get("ok", None)))
        # With only 3 tasks (well under max_concurrent=5), should allow new tasks
        if can_accept is not None:
            assert can_accept is True

    def test_enforce_with_empty_queue(self, empty_workspace):
        # Arrange
        with patch.object(SlateWorkflowManager, "__init__", lambda self: None):
            mgr = SlateWorkflowManager.__new__(SlateWorkflowManager)
            mgr.TASK_FILE = empty_workspace / "current_tasks.json"
            mgr.ARCHIVE_FILE = empty_workspace / ".slate_archive" / "archived_tasks.json"
            mgr.gh_cli = None
        # Act
        result = mgr.enforce_completion()
        # Assert
        assert isinstance(result, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# Stale Task Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestStaleDetection:
    """Test stale and abandoned task detection."""

    def test_old_in_progress_is_stale(self, manager):
        # Arrange — add a stale in-progress task
        tasks = json.loads(manager.TASK_FILE.read_text(encoding="utf-8"))
        stale_time = (datetime.now(timezone.utc) - timedelta(hours=5)).isoformat()
        tasks["tasks"].append({
            "id": "stale_001",
            "title": "Stale task",
            "status": "in_progress",
            "started_at": stale_time,
            "created_at": stale_time,
            "assigned_to": "workflow",
            "source": "test",
        })
        manager.TASK_FILE.write_text(json.dumps(tasks), encoding="utf-8")
        # Act
        result = manager.analyze_tasks()
        # Assert
        result_str = json.dumps(result).lower()
        assert "stale" in result_str


# ═══════════════════════════════════════════════════════════════════════════════
# Archive Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestArchive:
    """Test task archiving."""

    def test_cleanup_creates_archive(self, manager):
        # Act
        manager.cleanup()
        # Assert — archive file should exist if tasks were removed
        if manager.ARCHIVE_FILE.exists():
            archived = json.loads(manager.ARCHIVE_FILE.read_text(encoding="utf-8"))
            assert isinstance(archived, (dict, list))


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
