# Modified: 2026-02-07T13:30:00Z | Author: COPILOT | Change: Add test coverage for pii_scanner module
"""
Tests for slate/pii_scanner.py — PII detection, redaction, allowlisting,
GitHub content scanning, and Kubernetes manifest scanning.
"""

import os
import pytest
from pathlib import Path


# ── Imports ─────────────────────────────────────────────────────────────

from slate.pii_scanner import (
    PIIMatch,
    PII_PATTERNS,
    ALLOWLIST_PATTERNS,
    scan_text,
    redact_text,
    is_allowlisted,
    scan_github_content,
    scan_k8s_manifest,
    scan_k8s_directory,
)


# ── PIIMatch NamedTuple ─────────────────────────────────────────────────


class TestPIIMatch:
    """Tests for the PIIMatch NamedTuple."""

    def test_pii_match_creation(self):
        # Arrange / Act
        match = PIIMatch(pii_type="email", value="a@b.com", start=0, end=7)
        # Assert
        assert match.pii_type == "email"
        assert match.value == "a@b.com"
        assert match.start == 0
        assert match.end == 7


# ── scan_text ───────────────────────────────────────────────────────────


class TestScanText:
    """Tests for the scan_text function."""

    def test_empty_text_returns_empty(self):
        assert scan_text("") == []
        assert scan_text(None) == []

    def test_clean_text_returns_empty(self):
        assert scan_text("This is a normal issue title about a bug fix") == []

    def test_detects_email(self):
        matches = scan_text("Contact user@malicious-domain.net for info")
        types = [m.pii_type for m in matches]
        assert "email" in types

    def test_detects_phone_us(self):
        matches = scan_text("Call me at 555-123-4567")
        types = [m.pii_type for m in matches]
        assert "phone_us" in types

    def test_detects_ssn(self):
        matches = scan_text("My SSN is 123-45-6789")
        types = [m.pii_type for m in matches]
        assert "ssn" in types

    def test_detects_github_token(self):
        matches = scan_text("Token: ghp_abcdefghijklmnopqrstuvwxyz1234567890")
        types = [m.pii_type for m in matches]
        assert "github_token" in types

    def test_detects_private_key(self):
        matches = scan_text("-----BEGIN RSA PRIVATE KEY-----")
        types = [m.pii_type for m in matches]
        assert "private_key" in types

    def test_detects_aws_key(self):
        matches = scan_text("Access key: AKIAIOSFODNN7EXAMPLE")
        types = [m.pii_type for m in matches]
        assert "aws_key" in types


# ── Allowlisting ────────────────────────────────────────────────────────


class TestAllowlist:
    """Tests for allowlist functionality."""

    def test_localhost_ip_allowed(self):
        # 127.0.0.1 is allowlisted and should not trigger ip_address detection
        matches = scan_text("Server at 127.0.0.1:8080")
        ip_matches = [m for m in matches if m.pii_type == "ip_address"]
        assert len(ip_matches) == 0

    def test_private_ip_allowed(self):
        matches = scan_text("Server at 192.168.1.100")
        ip_matches = [m for m in matches if m.pii_type == "ip_address"]
        assert len(ip_matches) == 0

    def test_example_email_allowed(self):
        matches = scan_text("Send to user@example.com")
        email_matches = [m for m in matches if m.pii_type == "email"]
        assert len(email_matches) == 0

    def test_test_email_allowed(self):
        matches = scan_text("Use test@test.com for testing")
        email_matches = [m for m in matches if m.pii_type == "email"]
        assert len(email_matches) == 0


# ── redact_text ─────────────────────────────────────────────────────────


class TestRedactText:
    """Tests for the redact_text function."""

    def test_redact_empty_text(self):
        text, matches = redact_text("")
        assert text == ""
        assert matches == []

    def test_redact_none_text(self):
        text, matches = redact_text(None)
        assert text is None
        assert matches == []

    def test_redact_clean_text(self):
        text, matches = redact_text("This is clean")
        assert text == "This is clean"
        assert matches == []

    def test_redact_email(self):
        text, matches = redact_text("Email: danger@evil.org please")
        assert "[REDACTED:EMAIL]" in text
        assert len(matches) > 0

    def test_redact_preserves_surrounding_text(self):
        text, matches = redact_text("Before ghp_abcdefghijklmnopqrstuvwxyz1234567890 After")
        assert text.startswith("Before ")
        assert text.endswith(" After")
        assert "[REDACTED:" in text


# ── scan_github_content ─────────────────────────────────────────────────


class TestScanGitHubContent:
    """Tests for the scan_github_content function."""

    def test_clean_content(self):
        result = scan_github_content("Fix a bug", "No PII here")
        assert result["has_pii"] is False
        assert result["blocked"] is False
        assert result["redacted_title"] == "Fix a bug"

    def test_pii_in_title(self):
        result = scan_github_content("Bug: user@evil.org reported crash")
        assert result["has_pii"] is True
        assert len(result["title_pii"]) > 0

    def test_critical_pii_blocks(self):
        # SSN is critical — should block
        result = scan_github_content("User 123-45-6789 needs help")
        assert result["has_pii"] is True
        assert result["blocked"] is True
        assert "Critical PII" in result["message"]

    def test_none_body(self):
        result = scan_github_content("Clean title", None)
        assert result["redacted_body"] is None


# ── scan_k8s_manifest ──────────────────────────────────────────────────


class TestScanK8sManifest:
    """Tests for K8s manifest scanning."""

    def test_nonexistent_file(self):
        result = scan_k8s_manifest("/nonexistent/file.yaml")
        assert len(result["violations"]) > 0  # "Cannot read file" violation

    def test_clean_manifest(self, tmp_path):
        manifest = tmp_path / "clean.yaml"
        manifest.write_text(
            "apiVersion: v1\n"
            "kind: Pod\n"
            "metadata:\n"
            "  name: slate-worker\n"
            "spec:\n"
            "  containers:\n"
            "    - name: worker\n"
            "      image: python:3.11\n",
            encoding="utf-8",
        )
        result = scan_k8s_manifest(str(manifest))
        assert result["has_secrets"] is False
        assert result["blocked"] is False

    def test_manifest_with_hardcoded_secret(self, tmp_path):
        manifest = tmp_path / "secret.yaml"
        manifest.write_text(
            "apiVersion: v1\n"
            "kind: Deployment\n"
            "spec:\n"
            "  containers:\n"
            "    - name: app\n"
            "      env:\n"
            "        - name: DB_PASSWORD\n"
            "          value: sk-supersecretapikey12345678\n",
            encoding="utf-8",
        )
        result = scan_k8s_manifest(str(manifest))
        assert result["has_secrets"] is True or result["has_pii"] is True
        assert result["blocked"] is True or len(result["violations"]) > 0


# ── scan_k8s_directory ─────────────────────────────────────────────────


class TestScanK8sDirectory:
    """Tests for K8s directory scanning."""

    def test_nonexistent_directory(self):
        results = scan_k8s_directory("/nonexistent/dir")
        assert results == []

    def test_empty_directory(self, tmp_path):
        results = scan_k8s_directory(str(tmp_path))
        assert results == []

    def test_directory_with_yaml(self, tmp_path):
        manifest = tmp_path / "test.yaml"
        manifest.write_text("apiVersion: v1\nkind: ConfigMap\n", encoding="utf-8")
        results = scan_k8s_directory(str(tmp_path))
        assert len(results) == 1
