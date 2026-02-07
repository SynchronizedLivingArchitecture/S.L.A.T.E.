# Modified: 2026-02-07T13:40:00Z | Author: COPILOT | Change: Add test coverage for slate_runtime module
"""
Tests for slate/slate_runtime.py — integration checks, check_all results,
check_integration helper.
"""

import pytest
from unittest.mock import patch, MagicMock

from slate.slate_runtime import (
    check_integration,
    check_python,
    check_venv,
    check_all,
    INTEGRATIONS,
)


class TestCheckIntegration:
    """Tests for the check_integration helper."""

    def test_active_integration(self):
        result = check_integration("test", lambda: True)
        assert result["name"] == "test"
        assert result["status"] == "active"

    def test_inactive_integration(self):
        result = check_integration("test", lambda: False)
        assert result["status"] == "inactive"

    def test_error_integration(self):
        def boom():
            raise RuntimeError("fail")
        result = check_integration("test", boom)
        assert result["status"] == "error"
        assert "fail" in result["error"]

    def test_details_function(self):
        result = check_integration("python", lambda: True, lambda: "3.11.9")
        assert result["details"] == "3.11.9"

    def test_details_skipped_when_inactive(self):
        result = check_integration("python", lambda: False, lambda: "3.11.9")
        assert result["details"] is None


class TestCheckPython:
    """Tests for Python version check."""

    def test_python_version_ok(self):
        # We're running 3.11+ so this should pass
        assert check_python() is True


class TestCheckVenv:
    """Tests for venv check."""

    def test_venv_exists(self):
        # In workspace root, .venv exists
        assert check_venv() is True


class TestCheckAll:
    """Tests for check_all function."""

    def test_returns_integrations(self):
        results = check_all()
        assert "integrations" in results
        assert "summary" in results
        assert len(results["integrations"]) == len(INTEGRATIONS)

    def test_summary_counts(self):
        results = check_all()
        summary = results["summary"]
        assert summary["total"] == len(INTEGRATIONS)
        assert 0 <= summary["active"] <= summary["total"]

    def test_has_timestamp(self):
        results = check_all()
        assert "timestamp" in results


class TestIntegrationsList:
    """Tests for the INTEGRATIONS constant."""

    def test_seven_integrations(self):
        assert len(INTEGRATIONS) == 7

    def test_integration_names(self):
        names = [i[0] for i in INTEGRATIONS]
        assert "Python 3.11+" in names
        assert "Virtual Env" in names
        assert "NVIDIA GPU" in names
        assert "PyTorch" in names
        assert "Ollama" in names
        assert "ChromaDB" in names
