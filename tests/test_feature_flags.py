# Modified: 2026-02-07T13:35:00Z | Author: COPILOT | Change: Add test coverage for feature_flags module
"""
Tests for slate/feature_flags.py — FeatureFlags lifecycle, overrides,
file persistence, default flags, module-level helpers.
"""

import json
import pytest
from pathlib import Path

from slate.feature_flags import (
    FeatureFlags,
    FeatureFlag,
    DEFAULT_FLAGS,
    FLAGS_FILE,
)


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    """Tests for feature flag constants."""

    def test_default_flags_has_gpu(self):
        assert "gpu_acceleration" in DEFAULT_FLAGS
        assert DEFAULT_FLAGS["gpu_acceleration"] is True

    def test_default_flags_has_security(self):
        assert "action_guard" in DEFAULT_FLAGS
        assert "pii_scanner" in DEFAULT_FLAGS

    def test_default_flags_has_experimental_disabled(self):
        assert DEFAULT_FLAGS["cuda_graphs"] is False
        assert DEFAULT_FLAGS["flash_attention"] is False

    def test_flags_file_constant(self):
        assert FLAGS_FILE == ".slate_flags.json"


# ── FeatureFlag dataclass ───────────────────────────────────────────────


class TestFeatureFlagDataclass:
    """Tests for FeatureFlag dataclass."""

    def test_creation(self):
        flag = FeatureFlag(name="test", enabled=True, description="A test flag")
        assert flag.name == "test"
        assert flag.enabled is True
        assert flag.source == "default"


# ── FeatureFlags class ──────────────────────────────────────────────────


class TestFeatureFlags:
    """Tests for FeatureFlags class."""

    def test_default_flags_loaded(self):
        flags = FeatureFlags()
        assert flags.is_enabled("gpu_acceleration") is True

    def test_disabled_flag(self):
        flags = FeatureFlags()
        assert flags.is_enabled("cuda_graphs") is False

    def test_unknown_flag_defaults_false(self):
        flags = FeatureFlags()
        assert flags.is_enabled("nonexistent_flag") is False

    def test_set_override(self):
        flags = FeatureFlags()
        assert flags.is_enabled("cuda_graphs") is False
        flags.set("cuda_graphs", True)
        assert flags.is_enabled("cuda_graphs") is True

    def test_reset_override(self):
        flags = FeatureFlags()
        flags.set("cuda_graphs", True)
        assert flags.is_enabled("cuda_graphs") is True
        flags.reset("cuda_graphs")
        assert flags.is_enabled("cuda_graphs") is False  # back to default

    def test_get_all_includes_overrides(self):
        flags = FeatureFlags()
        flags.set("new_flag", True)
        all_flags = flags.get_all()
        assert "new_flag" in all_flags
        assert all_flags["new_flag"] is True

    def test_get_enabled_returns_sorted(self):
        flags = FeatureFlags()
        enabled = flags.get_enabled()
        assert isinstance(enabled, list)
        assert enabled == sorted(enabled)
        assert "gpu_acceleration" in enabled

    def test_get_disabled_returns_sorted(self):
        flags = FeatureFlags()
        disabled = flags.get_disabled()
        assert isinstance(disabled, list)
        assert "cuda_graphs" in disabled


# ── File persistence ────────────────────────────────────────────────────


class TestFilePersistence:
    """Tests for flag file load/save."""

    def test_save_creates_file(self, tmp_path):
        flags = FeatureFlags(workspace=str(tmp_path))
        flags.save()
        flags_file = tmp_path / FLAGS_FILE
        assert flags_file.exists()

    def test_save_valid_json(self, tmp_path):
        flags = FeatureFlags(workspace=str(tmp_path))
        flags.save()
        data = json.loads((tmp_path / FLAGS_FILE).read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert "gpu_acceleration" in data

    def test_load_from_file(self, tmp_path):
        # Write custom flags
        flags_file = tmp_path / FLAGS_FILE
        flags_file.write_text(
            json.dumps({"cuda_graphs": True, "flash_attention": True}),
            encoding="utf-8",
        )
        flags = FeatureFlags(workspace=str(tmp_path))
        assert flags.is_enabled("cuda_graphs") is True
        assert flags.is_enabled("flash_attention") is True

    def test_load_ignores_malformed_json(self, tmp_path):
        flags_file = tmp_path / FLAGS_FILE
        flags_file.write_text("not valid json {{{", encoding="utf-8")
        # Should not raise, fall back to defaults
        flags = FeatureFlags(workspace=str(tmp_path))
        assert flags.is_enabled("gpu_acceleration") is True

    def test_override_survives_save_load(self, tmp_path):
        flags = FeatureFlags(workspace=str(tmp_path))
        flags.set("cuda_graphs", True)
        flags.save()

        flags2 = FeatureFlags(workspace=str(tmp_path))
        assert flags2.is_enabled("cuda_graphs") is True
