# Modified: 2026-02-07T13:44:00Z | Author: COPILOT | Change: Add test coverage for slate_real_multi_runner module
"""
Tests for slate/slate_real_multi_runner.py — RealRunner dataclass,
RealMultiRunnerManager constants, runner discovery logic.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from dataclasses import fields

from slate.slate_real_multi_runner import (
    RealRunner,
    RealMultiRunnerManager,
    WORKSPACE_ROOT,
)


class TestRealRunnerDataclass:
    """Tests for the RealRunner dataclass."""

    def test_required_fields(self):
        runner = RealRunner(name="test-runner", directory=Path("/tmp"))
        assert runner.name == "test-runner"
        assert runner.directory == Path("/tmp")

    def test_default_values(self):
        runner = RealRunner(name="r", directory=Path("."))
        assert runner.agent_id is None
        assert runner.labels is None
        assert runner.status == "unknown"
        assert runner.busy is False
        assert runner.pid is None
        assert runner.gpu_id is None

    def test_all_fields_settable(self):
        runner = RealRunner(
            name="slate-runner",
            directory=Path("/runners/1"),
            agent_id=42,
            labels=["self-hosted", "slate"],
            status="online",
            busy=True,
            pid=9999,
            gpu_id=0,
        )
        assert runner.agent_id == 42
        assert runner.status == "online"
        assert runner.busy is True
        assert runner.gpu_id == 0

    def test_field_count(self):
        assert len(fields(RealRunner)) == 8


class TestRealMultiRunnerManager:
    """Tests for RealMultiRunnerManager initialization and constants."""

    def test_repo_constant(self):
        assert RealMultiRunnerManager.REPO == "SynchronizedLivingArchitecture/S.L.A.T.E"

    def test_api_base_contains_repo(self):
        assert RealMultiRunnerManager.REPO in RealMultiRunnerManager.API_BASE

    def test_init_default_workspace(self):
        mgr = RealMultiRunnerManager()
        assert mgr.workspace == WORKSPACE_ROOT

    def test_init_custom_workspace(self, tmp_path):
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        assert mgr.workspace == tmp_path

    def test_init_empty_runners(self):
        mgr = RealMultiRunnerManager()
        assert mgr.runners == []

    def test_init_token_none(self):
        mgr = RealMultiRunnerManager()
        assert mgr._token is None


class TestDiscoverLocalRunners:
    """Tests for discover_local_runners."""

    def test_discover_empty_workspace(self, tmp_path):
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        runners = mgr.discover_local_runners()
        assert runners == []

    def test_discover_runner_without_config(self, tmp_path):
        runner_dir = tmp_path / "actions-runner"
        runner_dir.mkdir()
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        runners = mgr.discover_local_runners()
        assert len(runners) == 1
        assert runners[0].name == "actions-runner"
        assert runners[0].agent_id is None

    def test_discover_runner_with_config(self, tmp_path):
        runner_dir = tmp_path / "actions-runner"
        runner_dir.mkdir()
        runner_file = runner_dir / ".runner"
        runner_file.write_text(json.dumps({
            "agentName": "slate-runner",
            "agentId": 42,
        }), encoding="utf-8")
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        runners = mgr.discover_local_runners()
        assert len(runners) == 1
        assert runners[0].name == "slate-runner"
        assert runners[0].agent_id == 42

    def test_discover_multiple_runners(self, tmp_path):
        for i in range(1, 4):
            d = tmp_path / f"actions-runner-{i}"
            d.mkdir()
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        runners = mgr.discover_local_runners()
        assert len(runners) == 3

    def test_ignores_non_runner_dirs(self, tmp_path):
        (tmp_path / "some-other-dir").mkdir()
        (tmp_path / "actions-runner").mkdir()
        mgr = RealMultiRunnerManager(workspace=tmp_path)
        runners = mgr.discover_local_runners()
        assert len(runners) == 1
