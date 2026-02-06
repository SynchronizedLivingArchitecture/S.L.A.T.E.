#!/usr/bin/env python3
# Modified: 2026-02-06T01:10:00Z | Author: COPILOT | Change: Centralize shared logic
"""
SLATE Utilities
===============
Shared logic for hardware detection, software status, and environment validation.
"""

import subprocess
import sys

def get_gpu_info():
    """Detect NVIDIA GPUs."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,compute_cap,memory.total,memory.free", "--format=csv,noheader"],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            gpus = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    gpus.append({
                        "name": parts[0],
                        "compute_capability": parts[1],
                        "memory_total": parts[2],
                        "memory_free": parts[3]
                    })
            return {"available": True, "count": len(gpus), "gpus": gpus}
        return {"available": False, "count": 0, "gpus": []}
    except Exception:
        return {"available": False, "count": 0, "gpus": []}

def check_gpu():
    """Simple boolean check for GPU availability."""
    info = get_gpu_info()
    return info["available"]

def get_pytorch_info():
    """Check PyTorch installation."""
    try:
        import torch
        cuda_available = torch.cuda.is_available()
        return {
            "installed": True,
            "version": torch.__version__,
            "cuda_available": cuda_available,
            "cuda_version": torch.version.cuda if cuda_available else None,
            "device_count": torch.cuda.device_count() if cuda_available else 0
        }
    except ImportError:
        return {"installed": False}

def check_pytorch():
    """Simple boolean check for PyTorch installation."""
    return get_pytorch_info()["installed"]

def get_pytorch_details():
    """Get formatted PyTorch details."""
    info = get_pytorch_info()
    if not info["installed"]:
        return "Not installed"
    cuda = f", CUDA {info['cuda_version']}" if info['cuda_available'] else ", CPU"
    return f"{info['version']}{cuda}"

def get_ollama_info():
    """Check Ollama status."""
    try:
        # Try 'ollama list' first as it's more comprehensive
        result = subprocess.run(
            ["ollama", "list"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")
            models = [l.split()[0] for l in lines[1:] if l.strip()]
            return {"available": True, "model_count": len(models), "models": models[:10]}

        # Fallback to --version
        result = subprocess.run(["ollama", "--version"], capture_output=True, timeout=5)
        return {"available": result.returncode == 0, "model_count": 0}
    except Exception:
        return {"available": False, "model_count": 0}

def check_ollama():
    """Simple boolean check for Ollama availability."""
    return get_ollama_info()["available"]

def get_python_info():
    """Get Python version info."""
    version = sys.version_info
    return {
        "version": f"{version.major}.{version.minor}.{version.micro}",
        "executable": sys.executable,
        "ok": version.major >= 3 and version.minor >= 11
    }
