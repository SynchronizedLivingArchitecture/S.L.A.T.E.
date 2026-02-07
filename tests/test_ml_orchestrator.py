# Modified: 2026-02-07T13:35:00Z | Author: COPILOT | Change: Add test coverage for ml_orchestrator module
"""
Tests for slate/ml_orchestrator.py — model routing, GPU strategy,
OllamaClient basics, constants.
"""

import pytest
from unittest.mock import patch, MagicMock

from slate.ml_orchestrator import (
    MODEL_ROUTING,
    FALLBACK_ROUTING,
    GPU_STRATEGY,
    OLLAMA_BASE,
    OllamaClient,
)


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    """Tests for ML orchestrator constants."""

    def test_ollama_base_is_localhost(self):
        assert "127.0.0.1" in OLLAMA_BASE

    def test_model_routing_tasks_defined(self):
        expected = ["code_generation", "summarization", "embedding", "general"]
        for task in expected:
            assert task in MODEL_ROUTING, f"Missing routing for {task}"

    def test_fallback_routing_covers_slate_models(self):
        # Each SLATE model should have a fallback
        assert "slate-coder:latest" in FALLBACK_ROUTING
        assert "slate-fast:latest" in FALLBACK_ROUTING
        assert "slate-planner:latest" in FALLBACK_ROUTING

    def test_gpu_strategy_dual_gpu(self):
        assert 0 in GPU_STRATEGY
        assert 1 in GPU_STRATEGY
        assert GPU_STRATEGY[0]["role"] == "primary_inference"
        assert GPU_STRATEGY[1]["role"] == "secondary_inference"

    def test_gpu_vram_limits(self):
        assert GPU_STRATEGY[0]["max_vram_mb"] == 14000
        assert GPU_STRATEGY[1]["max_vram_mb"] == 14000


# ── OllamaClient ───────────────────────────────────────────────────────


class TestOllamaClient:
    """Tests for OllamaClient class."""

    def test_default_base_url(self):
        client = OllamaClient()
        assert client.base_url == OLLAMA_BASE

    def test_custom_base_url(self):
        client = OllamaClient(base_url="http://127.0.0.1:9999")
        assert client.base_url == "http://127.0.0.1:9999"

    def test_is_running_returns_false_when_offline(self):
        client = OllamaClient(base_url="http://127.0.0.1:19999")
        # Should return False when Ollama is not reachable
        assert client.is_running() is False


# ── Model Routing ───────────────────────────────────────────────────────


class TestModelRouting:
    """Tests for model routing configuration."""

    def test_code_tasks_use_coder_model(self):
        assert "coder" in MODEL_ROUTING["code_generation"].lower()
        assert "coder" in MODEL_ROUTING["code_review"].lower()

    def test_fast_tasks_use_fast_model(self):
        assert "fast" in MODEL_ROUTING["summarization"].lower()
        assert "fast" in MODEL_ROUTING["classification"].lower()

    def test_embedding_uses_nomic(self):
        assert "nomic" in MODEL_ROUTING["embedding"].lower()

    def test_planning_uses_planner(self):
        assert "planner" in MODEL_ROUTING["planning"].lower()
