# Modified: 2026-02-07T13:56:00Z | Author: COPILOT | Change: Add test coverage for slate_gpu_manager module
"""
Tests for slate/slate_gpu_manager.py — GPU_MODEL_MAP configuration,
GPUManager initialization, nvidia-smi parsing.
"""

import json
import pytest
from unittest.mock import patch, MagicMock

from slate.slate_gpu_manager import (
    GPU_MODEL_MAP,
    GPUManager,
    OLLAMA_BASE,
    WORKSPACE_ROOT,
)


class TestConstants:
    """Tests for module-level constants."""

    def test_ollama_base_localhost(self):
        assert "127.0.0.1" in OLLAMA_BASE
        assert "11434" in OLLAMA_BASE


class TestGPUModelMap:
    """Tests for GPU_MODEL_MAP configuration."""

    def test_two_gpus(self):
        assert 0 in GPU_MODEL_MAP
        assert 1 in GPU_MODEL_MAP

    def test_gpu0_role(self):
        assert GPU_MODEL_MAP[0]["role"] == "heavy_inference"

    def test_gpu1_role(self):
        assert GPU_MODEL_MAP[1]["role"] == "quick_tasks"

    def test_gpu0_has_models(self):
        models = GPU_MODEL_MAP[0]["models"]
        assert len(models) > 0
        assert any("slate-coder" in m for m in models)

    def test_gpu1_has_models(self):
        models = GPU_MODEL_MAP[1]["models"]
        assert len(models) > 0
        assert any("slate-fast" in m for m in models)

    def test_max_loaded_mb(self):
        assert GPU_MODEL_MAP[0]["max_loaded_mb"] == 14000
        assert GPU_MODEL_MAP[1]["max_loaded_mb"] == 14000


class TestGPUManager:
    """Tests for GPUManager class."""

    def test_init_sets_workspace(self):
        mgr = GPUManager()
        assert mgr.workspace == WORKSPACE_ROOT

    def test_get_gpu_status_no_nvidia_smi(self):
        with patch("slate.slate_gpu_manager.subprocess.run", side_effect=FileNotFoundError()):
            mgr = GPUManager()
            result = mgr.get_gpu_status()
            assert result == []

    def test_get_gpu_status_parses_csv(self):
        mock_result = MagicMock()
        mock_result.stdout = "0, NVIDIA GeForce RTX 5070 Ti, 2000, 14000, 16384, 15, 45\n1, NVIDIA GeForce RTX 5070 Ti, 1000, 15000, 16384, 5, 40"
        with patch("slate.slate_gpu_manager.subprocess.run", return_value=mock_result):
            mgr = GPUManager()
            gpus = mgr.get_gpu_status()
            assert len(gpus) == 2
            assert gpus[0]["index"] == 0
            assert gpus[0]["name"] == "NVIDIA GeForce RTX 5070 Ti"
            assert gpus[0]["memory_used_mb"] == 2000
            assert gpus[0]["memory_free_mb"] == 14000
            assert gpus[0]["role"] == "heavy_inference"
            assert gpus[1]["index"] == 1
            assert gpus[1]["role"] == "quick_tasks"

    def test_get_loaded_models_offline(self):
        with patch.object(GPUManager, "_ollama_request", side_effect=Exception("offline")):
            mgr = GPUManager()
            result = mgr.get_loaded_models()
            assert result == []
