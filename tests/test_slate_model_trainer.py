# Modified: 2026-02-07T13:54:00Z | Author: COPILOT | Change: Add test coverage for slate_model_trainer module
"""
Tests for slate/slate_model_trainer.py — SLATE_MODELS definitions,
SlateModelTrainer state management, constants.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch

from slate.slate_model_trainer import (
    SLATE_MODELS,
    SlateModelTrainer,
    STATE_FILE,
    LOG_DIR,
    OLLAMA_BASE,
    MODELS_DIR,
    WORKSPACE_ROOT,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_ollama_base_localhost(self):
        assert "127.0.0.1" in OLLAMA_BASE
        assert "11434" in OLLAMA_BASE

    def test_models_dir(self):
        assert MODELS_DIR.parts[-1] == "models"

    def test_state_file(self):
        assert STATE_FILE.name == ".slate_model_state.json"

    def test_log_dir(self):
        assert LOG_DIR.parts[-1] == "models"
        assert LOG_DIR.parts[-2] == "slate_logs"


class TestSlateModels:
    """Tests for SLATE_MODELS configuration."""

    def test_three_models_defined(self):
        assert len(SLATE_MODELS) == 3

    def test_slate_coder_exists(self):
        assert "slate-coder" in SLATE_MODELS

    def test_slate_fast_exists(self):
        assert "slate-fast" in SLATE_MODELS

    def test_slate_planner_exists(self):
        assert "slate-planner" in SLATE_MODELS

    def test_coder_has_modelfile(self):
        assert SLATE_MODELS["slate-coder"]["modelfile"] == "Modelfile.slate-coder"

    def test_coder_gpu_assignment(self):
        assert SLATE_MODELS["slate-coder"]["gpu"] == 0

    def test_fast_gpu_assignment(self):
        assert SLATE_MODELS["slate-fast"]["gpu"] == 1

    def test_models_have_test_prompts(self):
        for name, cfg in SLATE_MODELS.items():
            assert "test_prompt" in cfg, f"{name} missing test_prompt"
            assert "expected_keywords" in cfg, f"{name} missing expected_keywords"

    def test_models_have_priority(self):
        for name, cfg in SLATE_MODELS.items():
            assert "priority" in cfg, f"{name} missing priority"
            assert isinstance(cfg["priority"], int)


class TestSlateModelTrainer:
    """Tests for SlateModelTrainer class."""

    def test_default_state(self, tmp_path):
        with patch("slate.slate_model_trainer.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.slate_model_trainer.LOG_DIR", tmp_path / "logs"):
                trainer = SlateModelTrainer()
                assert trainer.state["models_built"] == {}
                assert trainer.state["last_build"] is None
                assert trainer.state["last_test"] is None
                assert isinstance(trainer.state["build_history"], list)
                assert isinstance(trainer.state["test_results"], dict)

    def test_loads_existing_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "models_built": {"slate-coder": "2026-01-01"},
            "last_build": "2026-01-01",
            "last_test": None,
            "build_history": [{"model": "slate-coder"}],
            "test_results": {},
        }), encoding="utf-8")
        with patch("slate.slate_model_trainer.STATE_FILE", state_file):
            with patch("slate.slate_model_trainer.LOG_DIR", tmp_path / "logs"):
                trainer = SlateModelTrainer()
                assert "slate-coder" in trainer.state["models_built"]

    def test_save_state(self, tmp_path):
        state_file = tmp_path / "state.json"
        with patch("slate.slate_model_trainer.STATE_FILE", state_file):
            with patch("slate.slate_model_trainer.LOG_DIR", tmp_path / "logs"):
                trainer = SlateModelTrainer()
                trainer.state["last_build"] = "2026-02-07"
                trainer._save_state()
                data = json.loads(state_file.read_text(encoding="utf-8"))
                assert data["last_build"] == "2026-02-07"

    def test_workspace_set(self, tmp_path):
        with patch("slate.slate_model_trainer.STATE_FILE", tmp_path / "missing.json"):
            with patch("slate.slate_model_trainer.LOG_DIR", tmp_path / "logs"):
                trainer = SlateModelTrainer()
                assert trainer.workspace == WORKSPACE_ROOT
