# Modified: 2026-02-07T13:40:00Z | Author: COPILOT | Change: Add test coverage for runner_fallback module
"""
Tests for slate/runner_fallback.py — config persistence, fallback logic,
mode switching.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from slate.runner_fallback import (
    DEFAULT_CONFIG,
    load_config,
    save_config,
)


class TestDefaultConfig:
    """Tests for default configuration."""

    def test_default_mode_self_hosted(self):
        assert DEFAULT_CONFIG["mode"] == "self-hosted-only"

    def test_default_labels(self):
        assert "self-hosted" in DEFAULT_CONFIG["self_hosted_labels"]
        assert "slate" in DEFAULT_CONFIG["self_hosted_labels"]

    def test_default_fallback_runner(self):
        assert DEFAULT_CONFIG["fallback_runner"] == "ubuntu-latest"

    def test_cost_tracking_defaults(self):
        ct = DEFAULT_CONFIG["cost_tracking"]
        assert ct["enabled"] is True
        assert ct["monthly_budget_usd"] == 0


class TestConfigPersistence:
    """Tests for load/save config."""

    def test_load_missing_returns_default(self, tmp_path):
        with patch("slate.runner_fallback.CONFIG_FILE", tmp_path / "missing.json"):
            config = load_config()
            assert config["mode"] == "self-hosted-only"

    def test_save_and_load_roundtrip(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("slate.runner_fallback.CONFIG_FILE", config_file):
            config = DEFAULT_CONFIG.copy()
            config["mode"] = "fallback-enabled"
            save_config(config)

            loaded = load_config()
            assert loaded["mode"] == "fallback-enabled"
            assert loaded["last_updated"] is not None

    def test_save_sets_timestamp(self, tmp_path):
        config_file = tmp_path / "config.json"
        with patch("slate.runner_fallback.CONFIG_FILE", config_file):
            config = DEFAULT_CONFIG.copy()
            save_config(config)
            assert config["last_updated"] is not None

    def test_load_fills_missing_keys(self, tmp_path):
        config_file = tmp_path / "config.json"
        # Write a partial config
        config_file.write_text(json.dumps({"mode": "fallback-enabled"}), encoding="utf-8")
        with patch("slate.runner_fallback.CONFIG_FILE", config_file):
            loaded = load_config()
            assert loaded["mode"] == "fallback-enabled"
            # Missing keys filled from defaults
            assert "self_hosted_labels" in loaded
            assert "fallback_runner" in loaded
