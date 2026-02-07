# Modified: 2026-02-07T13:30:00Z | Author: COPILOT | Change: Add test coverage for runner_cost_tracker module
"""
Tests for slate/runner_cost_tracker.py — cost calculation, data persistence,
runner type detection, and savings analysis.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from slate.runner_cost_tracker import (
    RUNNER_COSTS,
    DEFAULT_DATA,
    load_cost_data,
    save_cost_data,
    calculate_job_cost,
)


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    """Tests for runner cost constants."""

    def test_self_hosted_is_free(self):
        assert RUNNER_COSTS["self-hosted"] == 0.0

    def test_ubuntu_cost(self):
        assert RUNNER_COSTS["ubuntu-latest"] == 0.008

    def test_windows_cost(self):
        assert RUNNER_COSTS["windows-latest"] == 0.016

    def test_macos_cost(self):
        assert RUNNER_COSTS["macos-latest"] == 0.08

    def test_default_data_structure(self):
        data = DEFAULT_DATA.copy()
        assert data["last_updated"] is None
        assert data["runs"] == []
        assert data["total_saved_usd"] == 0


# ── load_cost_data / save_cost_data ─────────────────────────────────────


class TestDataPersistence:
    """Tests for cost data file operations."""

    def test_load_missing_file_returns_default(self, tmp_path):
        with patch("slate.runner_cost_tracker.COST_DATA_FILE", tmp_path / "missing.json"):
            data = load_cost_data()
            assert data["last_updated"] is None
            assert data["runs"] == []

    def test_save_and_load_roundtrip(self, tmp_path):
        cost_file = tmp_path / "costs.json"
        with patch("slate.runner_cost_tracker.COST_DATA_FILE", cost_file):
            data = DEFAULT_DATA.copy()
            data["total_saved_usd"] = 42.50
            save_cost_data(data)

            loaded = load_cost_data()
            assert loaded["total_saved_usd"] == 42.50
            assert loaded["last_updated"] is not None

    def test_save_sets_timestamp(self, tmp_path):
        cost_file = tmp_path / "costs.json"
        with patch("slate.runner_cost_tracker.COST_DATA_FILE", cost_file):
            data = DEFAULT_DATA.copy()
            assert data["last_updated"] is None
            save_cost_data(data)
            assert data["last_updated"] is not None


# ── calculate_job_cost ──────────────────────────────────────────────────


class TestCalculateJobCost:
    """Tests for the calculate_job_cost function."""

    def test_self_hosted_job_free(self):
        job = {
            "name": "test-job",
            "labels": ["self-hosted", "slate", "gpu"],
            "started_at": "2026-02-07T10:00:00Z",
            "completed_at": "2026-02-07T10:05:00Z",
        }
        result = calculate_job_cost(job)
        assert result["is_self_hosted"] is True
        assert result["actual_cost"] == 0
        assert result["duration_minutes"] == pytest.approx(5.0, abs=0.1)
        assert result["saved"] > 0  # Would have cost money on hosted

    def test_hosted_job_has_cost(self):
        job = {
            "name": "lint",
            "labels": ["ubuntu-latest"],
            "started_at": "2026-02-07T10:00:00Z",
            "completed_at": "2026-02-07T10:10:00Z",
        }
        result = calculate_job_cost(job)
        assert result["is_self_hosted"] is False
        assert result["runner_type"] == "ubuntu-latest"
        assert result["duration_minutes"] == pytest.approx(10.0, abs=0.1)
        assert result["actual_cost"] == pytest.approx(0.08, abs=0.01)
        assert result["saved"] == 0

    def test_missing_timestamps_zero_duration(self):
        job = {
            "name": "incomplete",
            "labels": ["ubuntu-latest"],
        }
        result = calculate_job_cost(job)
        assert result["duration_minutes"] == 0
        assert result["actual_cost"] == 0

    def test_windows_runner_cost(self):
        job = {
            "name": "windows-tests",
            "labels": ["windows-latest"],
            "started_at": "2026-02-07T10:00:00Z",
            "completed_at": "2026-02-07T10:10:00Z",
        }
        result = calculate_job_cost(job)
        assert result["runner_type"] == "windows-latest"
        assert result["cost_rate"] == 0.016

    def test_slate_label_detected_as_self_hosted(self):
        job = {
            "name": "gpu-inference",
            "labels": ["slate", "gpu", "cuda"],
            "started_at": "2026-02-07T10:00:00Z",
            "completed_at": "2026-02-07T10:30:00Z",
        }
        result = calculate_job_cost(job)
        assert result["is_self_hosted"] is True
        assert result["actual_cost"] == 0
