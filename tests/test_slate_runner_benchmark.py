# Modified: 2026-02-07T13:35:00Z | Author: COPILOT | Change: Add test coverage for slate_runner_benchmark module
"""
Tests for slate/slate_runner_benchmark.py — runner profiles, system resources,
capacity calculations.
"""

import pytest
from unittest.mock import patch, MagicMock

from slate.slate_runner_benchmark import (
    RUNNER_PROFILES,
    SystemResources,
    RunnerCapacity,
    RunnerBenchmark,
)


# ── Constants ───────────────────────────────────────────────────────────


class TestRunnerProfiles:
    """Tests for runner profile definitions."""

    def test_light_profile_no_gpu(self):
        assert RUNNER_PROFILES["light"]["gpu_memory_mb"] == 0

    def test_gpu_heavy_requires_gpu(self):
        assert RUNNER_PROFILES["gpu_heavy"]["gpu_memory_mb"] > 0

    def test_all_profiles_have_required_fields(self):
        for pid, profile in RUNNER_PROFILES.items():
            assert "name" in profile, f"{pid} missing name"
            assert "gpu_memory_mb" in profile, f"{pid} missing gpu_memory_mb"
            assert "cpu_cores" in profile, f"{pid} missing cpu_cores"
            assert "ram_mb" in profile, f"{pid} missing ram_mb"
            assert "examples" in profile, f"{pid} missing examples"

    def test_profile_hierarchy_gpu_memory(self):
        # gpu_max > gpu_heavy > gpu_light > light
        assert RUNNER_PROFILES["gpu_max"]["gpu_memory_mb"] > RUNNER_PROFILES["gpu_heavy"]["gpu_memory_mb"]
        assert RUNNER_PROFILES["gpu_heavy"]["gpu_memory_mb"] > RUNNER_PROFILES["gpu_light"]["gpu_memory_mb"]
        assert RUNNER_PROFILES["gpu_light"]["gpu_memory_mb"] > RUNNER_PROFILES["light"]["gpu_memory_mb"]


# ── SystemResources ─────────────────────────────────────────────────────


class TestSystemResources:
    """Tests for SystemResources dataclass."""

    def test_creation(self):
        res = SystemResources(
            gpu_count=2,
            gpu_memory_total_mb=[16384, 16384],
            gpu_memory_free_mb=[14000, 14000],
            gpu_utilization=[10, 5],
            cpu_cores=16,
            ram_total_mb=32768,
            ram_free_mb=24576,
        )
        assert res.gpu_count == 2
        assert len(res.gpu_memory_total_mb) == 2
        assert res.cpu_cores == 16


# ── RunnerBenchmark ─────────────────────────────────────────────────────


class TestRunnerBenchmark:
    """Tests for RunnerBenchmark capacity calculations."""

    @pytest.fixture
    def benchmark(self):
        bm = RunnerBenchmark()
        # Inject mock resources matching dual RTX 5070 Ti
        bm.resources = SystemResources(
            gpu_count=2,
            gpu_memory_total_mb=[16384, 16384],
            gpu_memory_free_mb=[14000, 14000],
            gpu_utilization=[10, 5],
            cpu_cores=16,
            ram_total_mb=32768,
            ram_free_mb=24576,
        )
        return bm

    def test_light_runner_high_capacity(self, benchmark):
        cap = benchmark.calculate_capacity("light")
        assert cap.max_total > 10  # Lots of light runners possible

    def test_gpu_max_limited_capacity(self, benchmark):
        cap = benchmark.calculate_capacity("gpu_max")
        assert cap.max_total <= 4  # Very few max-GPU runners

    def test_capacity_has_limiting_factor(self, benchmark):
        cap = benchmark.calculate_capacity("standard")
        assert cap.limiting_factor in ("gpu", "cpu", "ram")

    def test_no_gpu_runners_with_light_profile(self, benchmark):
        cap = benchmark.calculate_capacity("light")
        # light profile needs 0 GPU memory — should not be GPU limited
        assert cap.limiting_factor != "gpu"

    def test_detect_resources_with_mock(self):
        bm = RunnerBenchmark()
        mock_result = MagicMock()
        mock_result.stdout = "16384, 14000, 10\n16384, 14000, 5"
        mock_result.returncode = 0

        with patch("subprocess.run", return_value=mock_result):
            res = bm.detect_resources()
            assert res.gpu_count == 2
            assert res.cpu_cores > 0
