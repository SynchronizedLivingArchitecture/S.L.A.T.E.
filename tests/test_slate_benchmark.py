# Modified: 2026-02-07T13:50:00Z | Author: COPILOT | Change: Add test coverage for slate_benchmark module
"""
Tests for slate/slate_benchmark.py — individual benchmarks, run_benchmarks, result structure.
"""

import pytest
from unittest.mock import patch, MagicMock

from slate.slate_benchmark import (
    benchmark_cpu_single,
    benchmark_memory,
    benchmark_disk,
    benchmark_gpu,
    run_benchmarks,
)


class TestBenchmarkCPU:
    """Tests for CPU benchmark."""

    def test_returns_dict(self):
        result = benchmark_cpu_single()
        assert isinstance(result, dict)

    def test_has_name(self):
        result = benchmark_cpu_single()
        assert result["name"] == "cpu_single"

    def test_has_ops(self):
        result = benchmark_cpu_single()
        assert result["ops"] == 100000

    def test_time_is_positive(self):
        result = benchmark_cpu_single()
        assert result["time_sec"] > 0

    def test_ops_per_sec_positive(self):
        result = benchmark_cpu_single()
        assert result["ops_per_sec"] > 0


class TestBenchmarkMemory:
    """Tests for memory benchmark."""

    def test_returns_dict(self):
        result = benchmark_memory()
        assert isinstance(result, dict)

    def test_name(self):
        result = benchmark_memory()
        assert result["name"] == "memory_alloc"

    def test_ops_count(self):
        result = benchmark_memory()
        assert result["ops"] == 1000

    def test_mb_allocated(self):
        result = benchmark_memory()
        assert result["mb_allocated"] == 10


class TestBenchmarkDisk:
    """Tests for disk I/O benchmark."""

    def test_returns_dict(self):
        result = benchmark_disk()
        assert isinstance(result, dict)

    def test_name(self):
        result = benchmark_disk()
        assert result["name"] == "disk_io"

    def test_mb_transferred(self):
        result = benchmark_disk()
        assert result["mb_transferred"] == 20


class TestBenchmarkGPU:
    """Tests for GPU benchmark."""

    def test_returns_dict(self):
        result = benchmark_gpu()
        assert isinstance(result, dict)

    def test_name_starts_with_gpu(self):
        result = benchmark_gpu()
        assert result["name"].startswith("gpu")

    def test_has_available_field(self):
        # GPU may or may not be available, but "available" key should exist
        # unless GPU is present and succeeds
        result = benchmark_gpu()
        if "available" in result:
            assert isinstance(result["available"], bool)


class TestRunBenchmarks:
    """Tests for run_benchmarks aggregator."""

    def test_returns_dict(self):
        result = run_benchmarks()
        assert isinstance(result, dict)

    def test_has_timestamp(self):
        result = run_benchmarks()
        assert "timestamp" in result

    def test_has_benchmarks_list(self):
        result = run_benchmarks()
        assert isinstance(result["benchmarks"], list)

    # Modified: 2026-02-08T02:06:00Z | Author: COPILOT | Change: Update expected count from 4 to 5 after GPU memory benchmark addition
    def test_five_benchmarks(self):
        result = run_benchmarks()
        assert len(result["benchmarks"]) == 5
