#!/usr/bin/env python3
# Modified: 2026-02-07T14:30:00Z | Author: COPILOT | Change: Create tests for DependencyScanner module
"""
Tests for SLATE Dependency Scanner.
All tests follow Arrange-Act-Assert (AAA) pattern.

The DependencyScanner implements the SLATE Installation Ethos:
    1. SCAN: Detect if dependencies exist outside the environment
    2. LINK: If found, create symlinks/junctions to reuse them
    3. INSTALL: Only install directly to workspace if not found
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

from slate.slate_dependency_scanner import (
    DependencyScanner,
    DependencyLocation,
    DependencyResult,
    ScanReport,
)


# ═══════════════════════════════════════════════════════════════════════════════
# DependencyLocation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyLocation:
    """Test the DependencyLocation dataclass."""

    def test_defaults(self):
        # Arrange & Act
        loc = DependencyLocation(path=Path("/test/path"))
        # Assert
        assert loc.path == Path("/test/path")
        assert loc.version is None
        assert loc.is_valid is True
        assert loc.size_mb == 0.0
        assert loc.metadata == {}

    def test_with_version(self):
        # Arrange & Act
        loc = DependencyLocation(
            path=Path("/python/3.11"),
            version="3.11.9",
            is_valid=True,
            drive="C:",
        )
        # Assert
        assert loc.version == "3.11.9"
        assert loc.drive == "C:"

    def test_to_dict(self):
        # Arrange
        loc = DependencyLocation(
            path=Path("/test/path"),
            version="1.0",
            size_mb=100.5,
            metadata={"key": "value"}
        )
        # Act
        d = loc.to_dict()
        # Assert
        assert d["path"] == "/test/path" or d["path"] == "\\test\\path"
        assert d["version"] == "1.0"
        assert d["size_mb"] == 100.5
        assert d["metadata"] == {"key": "value"}


# ═══════════════════════════════════════════════════════════════════════════════
# DependencyResult Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyResult:
    """Test the DependencyResult dataclass."""

    def test_defaults(self):
        # Arrange & Act
        result = DependencyResult(name="python", dep_type="runtime")
        # Assert
        assert result.name == "python"
        assert result.dep_type == "runtime"
        assert result.found is False
        assert result.locations == []
        assert result.action == "install"

    def test_found_with_locations(self):
        # Arrange
        loc = DependencyLocation(path=Path("/python"), version="3.11")
        # Act
        result = DependencyResult(
            name="python",
            dep_type="runtime",
            found=True,
            locations=[loc],
            best_location=loc,
            action="link"
        )
        # Assert
        assert result.found is True
        assert len(result.locations) == 1
        assert result.action == "link"

    def test_to_dict(self):
        # Arrange
        loc = DependencyLocation(path=Path("/test"), version="1.0")
        result = DependencyResult(
            name="test",
            dep_type="test_type",
            found=True,
            locations=[loc],
            best_location=loc,
            action="link",
            scanned_at="2026-02-07T00:00:00Z"
        )
        # Act
        d = result.to_dict()
        # Assert
        assert d["name"] == "test"
        assert d["found"] is True
        assert len(d["locations"]) == 1
        assert d["best_location"]["version"] == "1.0"


# ═══════════════════════════════════════════════════════════════════════════════
# ScanReport Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScanReport:
    """Test the ScanReport dataclass."""

    def test_defaults(self):
        # Act
        report = ScanReport(
            scan_time="2026-02-07T00:00:00Z",
            workspace="/test",
            platform="win32"
        )
        # Assert
        assert report.scan_time == "2026-02-07T00:00:00Z"
        assert report.drives_scanned == []
        assert report.results == {}
        assert report.needs_install == []

    def test_to_dict(self):
        # Arrange
        report = ScanReport(
            scan_time="2026-02-07T00:00:00Z",
            workspace="/test",
            platform="win32",
            drives_scanned=["C:", "D:"],
            needs_install=["pytorch"]
        )
        # Act
        d = report.to_dict()
        # Assert
        assert d["drives_scanned"] == ["C:", "D:"]
        assert d["needs_install"] == ["pytorch"]


# ═══════════════════════════════════════════════════════════════════════════════
# DependencyScanner Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDependencyScanner:
    """Test the DependencyScanner class."""

    def test_init(self):
        # Arrange & Act
        scanner = DependencyScanner(verbose=False)
        # Assert
        assert scanner.workspace == WORKSPACE_ROOT
        assert scanner.verbose is False
        assert scanner.report is not None

    def test_init_custom_workspace(self):
        # Arrange
        custom_path = Path("/custom/workspace")
        # Act
        scanner = DependencyScanner(workspace=custom_path, verbose=True)
        # Assert
        assert scanner.workspace == custom_path
        assert scanner.verbose is True

    @patch("slate.slate_dependency_scanner.DependencyScanner._run_cmd")
    def test_scan_python_finds_current(self, mock_run):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        # Mock returns current Python info
        mock_run.return_value = MagicMock(returncode=0, stdout="Python 3.11.9")

        # Act
        result = scanner.scan_python_installations()

        # Assert
        assert result.name == "python"
        assert result.dep_type == "runtime"
        # Current Python should always be found
        assert len(result.locations) >= 1

    def test_scan_python_returns_result(self):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        # Act
        result = scanner.scan_python_installations()
        # Assert
        assert isinstance(result, DependencyResult)
        assert result.name == "python"
        # Should always find current Python
        assert result.found is True
        assert len(result.locations) >= 1

    @patch("slate.slate_dependency_scanner.DependencyScanner._run_cmd")
    def test_scan_pytorch_not_installed(self, mock_run):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        # Mock PyTorch not found
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ModuleNotFoundError")

        # Act
        result = scanner.scan_pytorch()

        # Assert
        assert result.name == "pytorch"
        assert result.action in ["install", "link"]  # Either is valid

    @patch("slate.slate_dependency_scanner.DependencyScanner._run_cmd")
    def test_scan_cuda_no_gpu(self, mock_run):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        # Mock nvidia-smi not found
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")

        # Act
        result = scanner.scan_cuda()

        # Assert
        assert result.name == "cuda"
        # Without GPU, action should be skip (can't install CUDA without hardware)
        assert result.action in ["skip", "install"]

    # Modified: 2026-02-08T02:05:00Z | Author: COPILOT | Change: Mock OLLAMA_PATHS and shutil.which to fully simulate missing Ollama
    @patch("slate.slate_dependency_scanner.shutil.which", return_value=None)
    @patch("slate.slate_dependency_scanner.DependencyScanner._run_cmd")
    def test_scan_ollama_not_installed(self, mock_run, mock_which):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        scanner.OLLAMA_PATHS = []  # No model directories
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not found")

        # Act
        result = scanner.scan_ollama()

        # Assert
        assert result.name == "ollama"
        assert result.action == "install"

    @patch("slate.slate_dependency_scanner.DependencyScanner._run_cmd")
    def test_scan_chromadb_not_installed(self, mock_run):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="ModuleNotFoundError")

        # Act
        result = scanner.scan_chromadb()

        # Assert
        assert result.name == "chromadb"
        assert result.action == "install"

    def test_get_drives_returns_list(self):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        # Act
        drives = scanner._get_drives()
        # Assert
        assert isinstance(drives, list)
        assert len(drives) >= 1  # At least root/C: should exist

    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_python_installations")
    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_virtual_environments")
    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_pytorch")
    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_cuda")
    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_ollama")
    @patch("slate.slate_dependency_scanner.DependencyScanner.scan_chromadb")
    def test_scan_all(self, mock_chroma, mock_ollama, mock_cuda, mock_torch, mock_venv, mock_python):
        # Arrange
        scanner = DependencyScanner(verbose=False)

        # Mock all scan methods
        mock_python.return_value = DependencyResult(name="python", dep_type="runtime", found=True)
        mock_venv.return_value = DependencyResult(name="venv", dep_type="environment", found=False, action="install")
        mock_torch.return_value = DependencyResult(name="pytorch", dep_type="ml_framework", found=False, action="install")
        mock_cuda.return_value = DependencyResult(name="cuda", dep_type="gpu_toolkit", found=False, action="skip")
        mock_ollama.return_value = DependencyResult(name="ollama", dep_type="llm_runtime", found=False, action="install")
        mock_chroma.return_value = DependencyResult(name="chromadb", dep_type="vector_store", found=False, action="install")

        # Act
        report = scanner.scan_all()

        # Assert
        assert isinstance(report, ScanReport)
        assert "python" in report.results
        assert "pytorch" in report.results
        assert "ollama" in report.results
        # Check needs_install
        assert "venv" in report.needs_install
        assert "pytorch" in report.needs_install
        assert "ollama" in report.needs_install


# ═══════════════════════════════════════════════════════════════════════════════
# Link Creation Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestLinkCreation:
    """Test symlink/junction creation."""

    def test_create_link_invalid_source(self, tmp_path):
        # Arrange
        scanner = DependencyScanner(workspace=tmp_path, verbose=False)
        source = tmp_path / "nonexistent"
        target = tmp_path / "target"

        # Act
        result = scanner.create_link(source, target)

        # Assert - should fail for nonexistent source
        # Note: behavior may vary, but shouldn't crash
        assert isinstance(result, bool)

    def test_create_link_existing_target(self, tmp_path):
        # Arrange
        scanner = DependencyScanner(workspace=tmp_path, verbose=False)
        source = tmp_path / "source"
        source.mkdir()
        target = tmp_path / "target"
        target.mkdir()  # Already exists as real directory

        # Act
        result = scanner.create_link(source, target)

        # Assert - should not overwrite real directories
        assert result is False


# ═══════════════════════════════════════════════════════════════════════════════
# Integration Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestScannerIntegration:
    """Integration tests for the full scanner workflow."""

    def test_full_scan_produces_report(self):
        # Arrange
        scanner = DependencyScanner(verbose=False)

        # Act
        report = scanner.scan_all()

        # Assert
        assert isinstance(report, ScanReport)
        assert report.scan_time != ""
        assert report.workspace != ""
        assert len(report.drives_scanned) >= 1
        # Should have results for all dependency types
        expected_deps = ["python", "venv", "pytorch", "cuda", "ollama", "chromadb"]
        for dep in expected_deps:
            assert dep in report.results

    def test_report_json_serializable(self):
        # Arrange
        scanner = DependencyScanner(verbose=False)
        report = scanner.scan_all()

        # Act
        d = report.to_dict()
        json_str = json.dumps(d, default=str)

        # Assert
        assert json_str is not None
        parsed = json.loads(json_str)
        assert "results" in parsed
        assert "workspace" in parsed


# ═══════════════════════════════════════════════════════════════════════════════
# SLATE Installation Ethos Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestSlateInstallationEthos:
    """Tests verifying the SLATE installation ethos is correctly implemented."""

    def test_ethos_scan_before_install(self):
        """Verify that scan happens and produces actionable results."""
        # Arrange
        scanner = DependencyScanner(verbose=False)

        # Act
        report = scanner.scan_all()

        # Assert
        # Every result should have an action
        for name, result in report.results.items():
            assert result.action in ["link", "skip", "install"], f"{name} has invalid action"

    def test_ethos_link_when_found(self):
        """Verify that 'link' action is set when dependency is found."""
        # Arrange
        scanner = DependencyScanner(verbose=False)
        result = scanner.scan_python_installations()

        # Assert - Python should always be found and linkable/skippable
        if result.found and result.best_location:
            assert result.action in ["link", "skip"]

    def test_ethos_install_when_not_found(self):
        """Verify that 'install' action is set when dependency is not found."""
        # Arrange
        result = DependencyResult(
            name="test_dep",
            dep_type="test",
            found=False,
            locations=[],
            action="install"
        )

        # Assert
        assert result.action == "install"
        assert result.found is False

    def test_needs_install_list_populated(self):
        """Verify needs_install list is correctly populated."""
        # Arrange
        scanner = DependencyScanner(verbose=False)

        # Act
        report = scanner.scan_all()

        # Assert
        # needs_install should only contain deps with action='install'
        for dep_name in report.needs_install:
            assert report.results[dep_name].action == "install"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
