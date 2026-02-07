#!/usr/bin/env python3
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Tests for module registry hot-reload
"""
Tests for slate.module_registry
================================
AAA (Arrange-Act-Assert) pattern throughout.
"""

import importlib
import sys
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.module_registry import ModuleRegistry, ReloadRecord, get_registry


class TestModuleRegistry:
    """Tests for the ModuleRegistry class."""

    def test_register_valid_module(self):
        """Register a standard library module successfully."""
        # Arrange
        registry = ModuleRegistry()

        # Act
        result = registry.register("json")

        # Assert
        assert result is True
        assert "json" in registry.registered_modules

    def test_register_invalid_module(self):
        """Register a nonexistent module returns False."""
        # Arrange
        registry = ModuleRegistry()

        # Act
        result = registry.register("nonexistent_module_xyz_12345")

        # Assert
        assert result is False
        assert "nonexistent_module_xyz_12345" not in registry.registered_modules

    def test_register_idempotent(self):
        """Registering the same module twice is idempotent."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")

        # Act
        result = registry.register("json")

        # Assert
        assert result is True
        assert registry.registered_modules.count("json") == 1

    def test_unregister(self):
        """Unregister removes a module from the registry."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")

        # Act
        result = registry.unregister("json")

        # Assert
        assert result is True
        assert "json" not in registry.registered_modules

    def test_unregister_nonexistent(self):
        """Unregistering a non-registered module returns False."""
        # Arrange
        registry = ModuleRegistry()

        # Act
        result = registry.unregister("nonexistent")

        # Assert
        assert result is False

    def test_reload_registered_module(self):
        """Reload a registered module successfully."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")

        # Act
        record = registry.reload("json", force=True)

        # Assert
        assert record.success is True
        assert record.module_name == "json"
        assert record.duration_ms >= 0
        assert record.error is None

    def test_reload_unregistered_module(self):
        """Reload an unregistered module returns failure."""
        # Arrange
        registry = ModuleRegistry()

        # Act
        record = registry.reload("json")

        # Assert
        assert record.success is False
        assert "not registered" in record.error

    def test_reload_debounce(self):
        """Rapid reloads are debounced."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        registry.reload("json", force=True)  # first reload

        # Act
        record = registry.reload("json", force=False)  # immediate second reload

        # Assert
        assert record.success is False
        assert record.error == "debounced"

    def test_reload_all(self):
        """Reload all registered modules."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        registry.register("os")

        # Act
        results = registry.reload_all(force=True)

        # Assert
        assert len(results) == 2
        assert all(r.success for r in results)

    def test_reload_callback(self):
        """Callbacks are fired on reload."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        callback_calls = []
        registry.on_reload(lambda name, success, error: callback_calls.append((name, success)))

        # Act
        registry.reload("json", force=True)

        # Assert
        assert len(callback_calls) == 1
        assert callback_calls[0] == ("json", True)

    def test_reload_callback_error_does_not_crash(self):
        """A failing callback does not prevent reload from completing."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        registry.on_reload(lambda name, success, error: 1 / 0)  # intentional error

        # Act
        record = registry.reload("json", force=True)

        # Assert
        assert record.success is True

    def test_history_tracking(self):
        """Reload history is tracked."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")

        # Act
        registry.reload("json", force=True)
        registry.reload("json", force=True)

        # Assert
        history = registry.history
        assert len(history) == 2
        assert all(h["success"] for h in history)

    def test_history_max_size(self):
        """History respects max_history cap."""
        # Arrange
        registry = ModuleRegistry(max_history=5)
        registry.register("json")

        # Act
        for _ in range(10):
            registry.reload("json", force=True)

        # Assert
        assert len(registry.history) == 5

    def test_status(self):
        """Status returns expected structure."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        registry.reload("json", force=True)

        # Act
        status = registry.status()

        # Assert
        assert status["registered_count"] == 1
        assert "json" in status["modules"]
        assert status["total_reloads"] == 1
        assert status["last_reload"] is not None

    def test_get_module(self):
        """get_module returns the module object."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")

        # Act
        mod = registry.get_module("json")

        # Assert
        import json
        assert mod is json

    def test_get_module_nonexistent(self):
        """get_module returns None for unregistered modules."""
        # Arrange
        registry = ModuleRegistry()

        # Act
        mod = registry.get_module("nonexistent")

        # Assert
        assert mod is None

    def test_thread_safety(self):
        """Concurrent register/reload operations are thread-safe."""
        # Arrange
        registry = ModuleRegistry()
        errors = []

        def worker(mod_name):
            try:
                registry.register(mod_name)
                registry.reload(mod_name, force=True)
            except Exception as e:
                errors.append(e)

        # Act — use safe stdlib modules that won't corrupt pytest internals
        modules = ["json", "os", "csv", "textwrap", "math"]
        threads = [
            threading.Thread(target=worker, args=(mod,))
            for mod in modules
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Assert
        assert len(errors) == 0
        assert len(registry.registered_modules) == 5

    def test_reload_by_path(self):
        """reload_by_path reloads modules matching a file path."""
        # Arrange
        registry = ModuleRegistry()
        registry.register("json")
        import json as json_mod
        json_path = json_mod.__file__

        # Act
        results = registry.reload_by_path(json_path)

        # Assert
        assert len(results) == 1
        assert results[0].success is True


class TestGetRegistry:
    """Tests for the singleton get_registry function."""

    def test_singleton(self):
        """get_registry returns the same instance."""
        # Arrange & Act
        r1 = get_registry()
        r2 = get_registry()

        # Assert
        assert r1 is r2
