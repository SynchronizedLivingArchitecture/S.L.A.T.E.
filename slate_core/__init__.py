#!/usr/bin/env python3
# Modified: 2025-07-09T12:10:00Z | Author: COPILOT
# Change: Add plugins subpackage export for agent registry
"""
SLATE Core Infrastructure
=========================
Shared infrastructure modules for SLATE system.

Modules:
- file_lock: Thread-safe file locking for current_tasks.json
- gpu_scheduler: GPU resource management for dual-GPU setup
- memory: Constitution and memory storage
- plugins: Dynamic agent registry with kernel-style load/unload
"""

from .file_lock import FileLock, file_lock
from .gpu_scheduler import GPUScheduler, get_available_gpu
from .memory import ConstitutionMemory, get_constitution

__all__ = [
    "FileLock",
    "file_lock",
    "GPUScheduler",
    "get_available_gpu",
    "ConstitutionMemory",
    "get_constitution",
    "plugins",
]

__version__ = "1.0.0"
