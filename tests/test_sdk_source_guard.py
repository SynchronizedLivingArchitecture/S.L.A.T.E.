# Modified: 2026-02-07T13:30:00Z | Author: COPILOT | Change: Add test coverage for sdk_source_guard module
"""
Tests for slate/sdk_source_guard.py — SDKSourceGuard package validation,
typosquat detection, container image validation, Helm chart validation.
"""

import os
import pytest
from pathlib import Path

from slate.sdk_source_guard import (
    SDKSourceGuard,
    SourceValidation,
    TRUSTED_PUBLISHERS,
    TRUSTED_INDICES,
    TYPOSQUAT_PATTERNS,
    BLOCKED_PACKAGES,
    TRUSTED_CONTAINER_REGISTRIES,
    TRUSTED_HELM_REPOS,
    get_guard,
    validate_package,
    validate_index,
)


# ── SourceValidation ────────────────────────────────────────────────────


class TestSourceValidation:
    """Tests for SourceValidation dataclass."""

    def test_valid_str(self):
        v = SourceValidation(valid=True, package="torch", reason="OK")
        assert "[VALID]" in str(v)

    def test_blocked_str(self):
        v = SourceValidation(valid=False, package="bad", reason="Blocked")
        assert "[BLOCKED]" in str(v)


# ── Package Validation ──────────────────────────────────────────────────


class TestPackageValidation:
    """Tests for SDKSourceGuard.validate_package."""

    @pytest.fixture
    def guard(self):
        return SDKSourceGuard()

    def test_legitimate_package_allowed(self, guard):
        result = guard.validate_package("torch")
        assert result.valid is True

    def test_numpy_allowed(self, guard):
        result = guard.validate_package("numpy")
        assert result.valid is True

    def test_fastapi_allowed(self, guard):
        result = guard.validate_package("fastapi")
        assert result.valid is True

    def test_transformers_allowed(self, guard):
        result = guard.validate_package("transformers")
        assert result.valid is True

    def test_blocked_typosquat_colourama(self, guard):
        result = guard.validate_package("colourama")
        assert result.valid is False
        assert "malicious" in result.reason.lower()

    def test_blocked_python3_dateutil(self, guard):
        result = guard.validate_package("python3-dateutil")
        assert result.valid is False

    def test_typosquat_reqeusts(self, guard):
        result = guard.validate_package("reqeusts")
        assert result.valid is False
        assert "typosquat" in result.reason.lower()

    def test_typosquat_numppy(self, guard):
        result = guard.validate_package("numppy")
        assert result.valid is False

    def test_case_insensitive(self, guard):
        result = guard.validate_package("Colourama")
        assert result.valid is False


# ── Index Validation ────────────────────────────────────────────────────


class TestIndexValidation:
    """Tests for SDKSourceGuard.validate_index."""

    @pytest.fixture
    def guard(self):
        return SDKSourceGuard()

    def test_pypi_trusted(self, guard):
        result = guard.validate_index("https://pypi.org/simple/")
        assert result.valid is True

    def test_pytorch_index_trusted(self, guard):
        result = guard.validate_index("https://download.pytorch.org/whl/cu128")
        assert result.valid is True

    def test_untrusted_index(self, guard):
        result = guard.validate_index("https://evil-pypi.example.com/simple/")
        assert result.valid is False
        assert "Untrusted" in result.reason


# ── Container Image Validation ──────────────────────────────────────────


class TestContainerImageValidation:
    """Tests for SDKSourceGuard.validate_container_image."""

    @pytest.fixture
    def guard(self):
        return SDKSourceGuard()

    def test_ghcr_slate_allowed(self, guard):
        result = guard.validate_container_image("ghcr.io/synchronizedlivingarchitecture/slate:latest")
        assert result.valid is True

    def test_ollama_allowed(self, guard):
        result = guard.validate_container_image("ollama/ollama:latest")
        assert result.valid is True

    def test_nvidia_cuda_allowed(self, guard):
        result = guard.validate_container_image("nvidia/cuda:12.4.1-runtime-ubuntu22.04")
        assert result.valid is True

    def test_mcr_microsoft_allowed(self, guard):
        result = guard.validate_container_image("mcr.microsoft.com/dotnet/runtime:8.0")
        assert result.valid is True

    def test_k8s_registry_allowed(self, guard):
        result = guard.validate_container_image("registry.k8s.io/pause:3.9")
        assert result.valid is True

    def test_untrusted_registry_blocked(self, guard):
        result = guard.validate_container_image("evil-registry.io/malware:latest")
        assert result.valid is False


# ── Helm Repo Validation ───────────────────────────────────────────────


class TestHelmRepoValidation:
    """Tests for SDKSourceGuard.validate_helm_repo."""

    @pytest.fixture
    def guard(self):
        return SDKSourceGuard()

    def test_bitnami_trusted(self, guard):
        result = guard.validate_helm_repo("https://charts.bitnami.com/bitnami")
        assert result.valid is True

    def test_prometheus_trusted(self, guard):
        result = guard.validate_helm_repo("https://prometheus-community.github.io/helm-charts")
        assert result.valid is True

    def test_untrusted_helm_repo(self, guard):
        result = guard.validate_helm_repo("https://evil-charts.example.com")
        assert result.valid is False


# ── Requirements Validation ─────────────────────────────────────────────


class TestRequirementsValidation:
    """Tests for SDKSourceGuard.validate_requirements."""

    def test_validate_requirements_file(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("torch>=2.0\nnumpy\nfastapi\n", encoding="utf-8")

        guard = SDKSourceGuard()
        results = guard.validate_requirements(str(req))
        assert len(results) == 3
        assert all(r.valid for r in results)

    def test_requirements_with_blocked(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("torch\ncolourama\nnumpy\n", encoding="utf-8")

        guard = SDKSourceGuard()
        results = guard.validate_requirements(str(req))
        blocked = [r for r in results if not r.valid]
        assert len(blocked) == 1
        assert blocked[0].package == "colourama"

    def test_requirements_nonexistent(self):
        guard = SDKSourceGuard()
        results = guard.validate_requirements("/nonexistent/requirements.txt")
        assert results == []

    def test_requirements_skips_comments(self, tmp_path):
        req = tmp_path / "requirements.txt"
        req.write_text("# comment\ntorch\n-r other.txt\nnumpy\n", encoding="utf-8")

        guard = SDKSourceGuard()
        results = guard.validate_requirements(str(req))
        assert len(results) == 2  # only torch and numpy


# ── Module-level functions ──────────────────────────────────────────────


class TestModuleFunctions:
    """Tests for module-level convenience functions."""

    def test_validate_package_function(self):
        result = validate_package("torch")
        assert result.valid is True

    def test_validate_index_function(self):
        result = validate_index("https://pypi.org/simple/")
        assert result.valid is True
