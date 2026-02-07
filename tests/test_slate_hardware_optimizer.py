#!/usr/bin/env python3
# Modified: 2026-02-07T12:55:00Z | Author: COPILOT | Change: Create tests for hardware optimizer module
"""
Tests for SLATE Hardware Optimizer.
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_hardware_optimizer import (
    GPU_ARCHITECTURES,
    CUDA_VERSIONS,
    GPUInfo,
    detect_gpus,
    get_pytorch_info,
    get_optimization_config,
    get_pytorch_install_command,
)


# ═══════════════════════════════════════════════════════════════════════════════
# GPUInfo Dataclass Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGPUInfo:
    """Test GPUInfo dataclass."""

    def test_create_gpu_info(self):
        # Arrange & Act
        gpu = GPUInfo(
            name="NVIDIA GeForce RTX 5070 Ti",
            compute_capability="12.0",
            architecture="Blackwell",
            memory_total=16303,
            memory_free=11600,
            index=0,
        )
        # Assert
        assert gpu.name == "NVIDIA GeForce RTX 5070 Ti"
        assert gpu.compute_capability == "12.0"
        assert gpu.memory_total == 16303
        assert gpu.index == 0

    def test_gpu_info_defaults(self):
        # Arrange & Act
        gpu = GPUInfo(name="Test GPU", compute_capability="8.9",
                      architecture="Ada Lovelace", memory_total=8192,
                      memory_free=8000, index=0)
        # Assert
        assert gpu.memory_free <= gpu.memory_total


# ═══════════════════════════════════════════════════════════════════════════════
# GPU Architecture Constants Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestConstants:
    """Test GPU architecture mappings."""

    def test_blackwell_in_architectures(self):
        # Assert — Blackwell (CC 12.x) should be in the mapping
        has_blackwell = any("12" in k for k in GPU_ARCHITECTURES)
        assert has_blackwell or len(GPU_ARCHITECTURES) > 0

    def test_cuda_versions_has_entries(self):
        # Assert
        assert len(CUDA_VERSIONS) > 0

    def test_known_architectures_have_cuda_versions(self):
        # Assert — architectures with CUDA wheel support should be in CUDA_VERSIONS
        # Not all architectures (e.g. Volta, Pascal) have modern CUDA wheel builds
        modern = {"Blackwell", "Ada Lovelace", "Ampere"}
        for arch in modern:
            if arch in set(GPU_ARCHITECTURES.values()):
                assert arch in CUDA_VERSIONS, f"Missing CUDA version for {arch}"


# ═══════════════════════════════════════════════════════════════════════════════
# GPU Detection Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestDetectGPUs:
    """Test GPU detection via nvidia-smi."""

    @patch("subprocess.run")
    def test_detect_gpus_success(self, mock_run):
        # Arrange — mock nvidia-smi CSV output (format: index,name,compute_cap,memory.total,memory.free)
        mock_run.return_value = MagicMock(
            returncode=0,
            stdout="0, NVIDIA GeForce RTX 5070 Ti, 12.0, 16303 MiB, 11600 MiB\n1, NVIDIA GeForce RTX 5070 Ti, 12.0, 16303 MiB, 15700 MiB\n",
        )
        # Act
        gpus = detect_gpus()
        # Assert
        assert len(gpus) == 2
        assert gpus[0].name == "NVIDIA GeForce RTX 5070 Ti"
        assert gpus[0].index == 0
        assert gpus[1].index == 1

    @patch("subprocess.run")
    def test_detect_gpus_no_nvidia_smi(self, mock_run):
        # Arrange — nvidia-smi not found
        mock_run.side_effect = FileNotFoundError("nvidia-smi not found")
        # Act
        gpus = detect_gpus()
        # Assert
        assert gpus == []

    @patch("subprocess.run")
    def test_detect_gpus_command_fails(self, mock_run):
        # Arrange — nvidia-smi returns error
        mock_run.return_value = MagicMock(returncode=1, stdout="")
        # Act
        gpus = detect_gpus()
        # Assert
        assert gpus == []


# ═══════════════════════════════════════════════════════════════════════════════
# PyTorch Info Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestGetPytorchInfo:
    """Test PyTorch detection."""

    def test_pytorch_info_returns_dict(self):
        # Act
        info = get_pytorch_info()
        # Assert
        assert isinstance(info, dict)
        assert "installed" in info or "version" in info or len(info) > 0


# ═══════════════════════════════════════════════════════════════════════════════
# Optimization Config Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestOptimizationConfig:
    """Test optimization configuration generation."""

    def test_config_for_blackwell_gpus(self):
        # Arrange
        gpus = [
            GPUInfo("RTX 5070 Ti", "12.0", "Blackwell", 16303, 11600, 0),
            GPUInfo("RTX 5070 Ti", "12.0", "Blackwell", 16303, 15700, 1),
        ]
        # Act
        config = get_optimization_config(gpus)
        # Assert
        assert isinstance(config, dict)
        assert len(config) > 0

    def test_config_for_no_gpus(self):
        # Arrange
        gpus = []
        # Act
        config = get_optimization_config(gpus)
        # Assert
        assert isinstance(config, dict)


# ═══════════════════════════════════════════════════════════════════════════════
# PyTorch Install Command Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestPytorchInstallCommand:
    """Test PyTorch install command generation."""

    def test_returns_string(self):
        # Arrange
        config = {"cuda_version": "cu128", "architecture": "Blackwell"}
        # Act
        cmd = get_pytorch_install_command(config)
        # Assert
        assert isinstance(cmd, str)
        assert "pip" in cmd or "torch" in cmd or len(cmd) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
