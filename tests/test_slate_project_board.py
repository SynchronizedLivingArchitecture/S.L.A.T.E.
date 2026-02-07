# Modified: 2026-02-07T13:52:00Z | Author: COPILOT | Change: Add test coverage for slate_project_board module
"""
Tests for slate/slate_project_board.py — constants, PROJECTS mapping,
run_gh, list_projects structure.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from slate.slate_project_board import (
    PROJECTS,
    PROJECT_OWNER,
    TASKS_FILE,
    WORKSPACE_ROOT,
    run_gh,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_project_owner(self):
        assert PROJECT_OWNER == "SynchronizedLivingArchitecture"

    def test_tasks_file_path(self):
        assert TASKS_FILE.name == "current_tasks.json"

    def test_projects_mapping_kanban(self):
        assert PROJECTS["kanban"] == 5

    def test_projects_mapping_bugs(self):
        assert PROJECTS["bugs"] == 7

    def test_projects_mapping_iterative(self):
        assert PROJECTS["iterative"] == 8

    def test_projects_mapping_roadmap(self):
        assert PROJECTS["roadmap"] == 10

    def test_all_project_ids_are_ints(self):
        for name, pid in PROJECTS.items():
            assert isinstance(pid, int), f"Project '{name}' id should be int"

    def test_project_count(self):
        # kanban, bugs, iterative, roadmap, planning, future, launch, introspection
        assert len(PROJECTS) == 8


class TestRunGh:
    """Tests for run_gh helper."""

    def test_returns_tuple(self):
        with patch("slate.slate_project_board.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="ok")
            code, output = run_gh("version")
            assert isinstance(code, int)
            assert isinstance(output, str)

    def test_success_code(self):
        with patch("slate.slate_project_board.subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="2.0.0")
            code, output = run_gh("version")
            assert code == 0
            assert output == "2.0.0"

    def test_timeout_returns_error(self):
        import subprocess as sp
        with patch("slate.slate_project_board.subprocess.run", side_effect=sp.TimeoutExpired("gh", 30)):
            code, output = run_gh("project", "list")
            assert code == 1
            assert "timed out" in output.lower()

    def test_file_not_found_returns_error(self):
        with patch("slate.slate_project_board.subprocess.run", side_effect=FileNotFoundError()):
            code, output = run_gh("version")
            assert code == 1
            assert "not found" in output.lower()
