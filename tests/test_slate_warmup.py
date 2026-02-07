# Modified: 2026-02-07T13:58:00Z | Author: COPILOT | Change: Add test coverage for slate_warmup module
"""
Tests for slate/slate_warmup.py — SlateWarmup state management,
PRELOAD_MODELS config, OLLAMA_ENV_CONFIG constants.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from slate.slate_warmup import (
    SlateWarmup,
    PRELOAD_MODELS,
    OLLAMA_ENV_CONFIG,
    STATE_FILE,
    LOG_DIR,
    OLLAMA_BASE,
    INDEX_REFRESH_INTERVAL,
    WORKSPACE_ROOT,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_ollama_base_localhost(self):
        assert "127.0.0.1" in OLLAMA_BASE

    def test_index_refresh_interval(self):
        # Should be 6 hours in seconds
        assert INDEX_REFRESH_INTERVAL == 6 * 3600

    def test_state_file_path(self):
        assert STATE_FILE.name == ".slate_warmup_state.json"

    def test_log_dir(self):
        assert LOG_DIR.parts[-1] == "warmup"
        assert LOG_DIR.parts[-2] == "slate_logs"


class TestPreloadModels:
    """Tests for PRELOAD_MODELS configuration."""

    def test_has_models(self):
        assert len(PRELOAD_MODELS) >= 3

    def test_all_have_name(self):
        for m in PRELOAD_MODELS:
            assert "name" in m

    def test_all_have_gpu(self):
        for m in PRELOAD_MODELS:
            assert "gpu" in m
            assert m["gpu"] in (0, 1)

    def test_all_have_keep_alive(self):
        for m in PRELOAD_MODELS:
            assert "keep_alive" in m

    def test_all_have_priority(self):
        for m in PRELOAD_MODELS:
            assert "priority" in m
            assert isinstance(m["priority"], int)

    def test_slate_coder_in_preload(self):
        names = [m["name"] for m in PRELOAD_MODELS]
        assert any("slate-coder" in n for n in names)

    def test_slate_fast_in_preload(self):
        names = [m["name"] for m in PRELOAD_MODELS]
        assert any("slate-fast" in n for n in names)


class TestOllamaEnvConfig:
    """Tests for OLLAMA_ENV_CONFIG."""

    def test_cuda_visible_devices(self):
        assert OLLAMA_ENV_CONFIG["CUDA_VISIBLE_DEVICES"] == "0,1"

    def test_host_localhost(self):
        assert "127.0.0.1" in OLLAMA_ENV_CONFIG["OLLAMA_HOST"]

    def test_flash_attention_enabled(self):
        assert OLLAMA_ENV_CONFIG["OLLAMA_FLASH_ATTENTION"] == "1"

    def test_keep_alive_set(self):
        assert OLLAMA_ENV_CONFIG["OLLAMA_KEEP_ALIVE"] == "24h"


class TestSlateWarmup:
    """Tests for SlateWarmup class."""

    def test_default_state(self, tmp_path):
        with patch("slate.slate_warmup.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.slate_warmup.LOG_DIR", tmp_path / "logs"):
                warmup = SlateWarmup()
                assert warmup.state["last_warmup"] is None
                assert warmup.state["last_preload"] is None
                assert warmup.state["last_index"] is None
                assert warmup.state["warmup_count"] == 0
                assert isinstance(warmup.state["models_loaded"], list)
                assert isinstance(warmup.state["preload_failures"], list)

    def test_loads_existing_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "last_warmup": "2026-01-01",
            "last_preload": "2026-01-01",
            "last_index": None,
            "models_loaded": ["slate-coder"],
            "warmup_count": 5,
            "preload_failures": [],
            "index_stats": {},
        }), encoding="utf-8")
        with patch("slate.slate_warmup.STATE_FILE", state_file):
            with patch("slate.slate_warmup.LOG_DIR", tmp_path / "logs"):
                warmup = SlateWarmup()
                assert warmup.state["warmup_count"] == 5
                assert warmup.state["models_loaded"] == ["slate-coder"]

    def test_save_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("slate.slate_warmup.STATE_FILE", state_file):
            with patch("slate.slate_warmup.LOG_DIR", tmp_path / "logs"):
                warmup = SlateWarmup()
                warmup.state["warmup_count"] = 10
                warmup._save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["warmup_count"] == 10

    def test_log_creates_file(self, tmp_path):
        log_dir = tmp_path / "logs"
        with patch("slate.slate_warmup.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.slate_warmup.LOG_DIR", log_dir):
                warmup = SlateWarmup()
                warmup._log("warmup started")
                log_files = list(log_dir.glob("warmup_*.log"))
                assert len(log_files) == 1
                content = log_files[0].read_text(encoding="utf-8")
                assert "[WARMUP]" in content
                assert "warmup started" in content
