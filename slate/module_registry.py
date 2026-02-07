#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: module_registry [python]
# Author: COPILOT | Created: 2026-02-07T06:00:00Z
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Initial creation - hot-reload module registry
# Purpose: Thread-safe module registry with importlib.reload for dev hot-reloading
# ═══════════════════════════════════════════════════════════════════════════════
"""
Module Registry
===============
Manages dynamic module loading and reloading for SLATE agent modules.
Used in dev mode for hot-reloading when files change on disk.

Features:
- Thread-safe module registration and reload
- Callback hooks for post-reload side-effects (WebSocket push, etc.)
- Tracks reload history with timestamps
- Guards against reload storms (debounce)

Security:
- No eval/exec — uses importlib only
- Local-only operation, no network side-effects from reload itself

Usage:
    from slate.module_registry import ModuleRegistry

    registry = ModuleRegistry()
    registry.register("agents.runner_api")
    registry.register("agents.slate_dashboard_server")

    # Reload a specific module
    result = registry.reload("agents.runner_api")

    # Reload all registered modules
    results = registry.reload_all()
"""

import importlib
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger("slate.module_registry")

WORKSPACE_ROOT = Path(__file__).parent.parent

# Ensure workspace root is in path for module imports
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


@dataclass
class ReloadRecord:
    """Record of a module reload event."""
    module_name: str
    timestamp: str
    success: bool
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class RegisteredModule:
    """A module registered for hot-reload."""
    name: str
    module: Any = None
    last_reloaded: Optional[str] = None
    reload_count: int = 0
    file_path: Optional[str] = None


class ModuleRegistry:
    """Thread-safe registry for dynamically reloadable modules.

    Provides importlib.reload-based hot-swapping with debounce,
    callback hooks, and reload history tracking.
    """

    DEBOUNCE_MS: float = 500  # Minimum ms between reloads of same module

    def __init__(self, max_history: int = 100):
        self._modules: Dict[str, RegisteredModule] = {}
        self._callbacks: List[Callable[[str, bool, Optional[str]], None]] = []
        self._history: List[ReloadRecord] = []
        self._max_history = max_history
        self._lock = threading.RLock()
        self._last_reload_time: Dict[str, float] = {}

    # ─── Registration ─────────────────────────────────────────────────────

    def register(self, module_name: str) -> bool:
        """Register a module for hot-reload tracking.

        Args:
            module_name: Dotted module name (e.g. 'agents.runner_api')

        Returns:
            True if registered successfully, False on import error.
        """
        with self._lock:
            if module_name in self._modules:
                return True

            try:
                mod = importlib.import_module(module_name)
                file_path = getattr(mod, '__file__', None)
                self._modules[module_name] = RegisteredModule(
                    name=module_name,
                    module=mod,
                    file_path=file_path,
                )
                logger.info("Registered module: %s", module_name)
                return True
            except Exception as e:
                logger.error("Failed to register %s: %s", module_name, e)
                return False

    def unregister(self, module_name: str) -> bool:
        """Remove a module from the registry."""
        with self._lock:
            if module_name in self._modules:
                del self._modules[module_name]
                self._last_reload_time.pop(module_name, None)
                return True
            return False

    # ─── Reload ───────────────────────────────────────────────────────────

    def reload(self, module_name: str, force: bool = False) -> ReloadRecord:
        """Reload a registered module using importlib.reload.

        Args:
            module_name: The module to reload.
            force: If True, skip debounce check.

        Returns:
            ReloadRecord with success/failure info.
        """
        with self._lock:
            now = time.monotonic() * 1000  # ms
            last = self._last_reload_time.get(module_name, 0)

            if not force and (now - last) < self.DEBOUNCE_MS:
                return ReloadRecord(
                    module_name=module_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    success=False,
                    error="debounced",
                    duration_ms=0,
                )

            entry = self._modules.get(module_name)
            if not entry:
                return ReloadRecord(
                    module_name=module_name,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                    success=False,
                    error="not registered",
                )

            start = time.monotonic()
            ts = datetime.now(timezone.utc).isoformat()
            try:
                mod = sys.modules.get(module_name)
                if mod is None:
                    mod = importlib.import_module(module_name)
                else:
                    mod = importlib.reload(mod)

                entry.module = mod
                entry.last_reloaded = ts
                entry.reload_count += 1
                self._last_reload_time[module_name] = now

                duration = (time.monotonic() - start) * 1000
                record = ReloadRecord(
                    module_name=module_name,
                    timestamp=ts,
                    success=True,
                    duration_ms=round(duration, 2),
                )
                self._append_history(record)
                logger.info("Reloaded %s in %.1fms", module_name, duration)

                # Fire callbacks
                for cb in self._callbacks:
                    try:
                        cb(module_name, True, None)
                    except Exception as cb_err:
                        logger.warning("Callback error for %s: %s", module_name, cb_err)

                return record

            except Exception as e:
                duration = (time.monotonic() - start) * 1000
                error_msg = f"{type(e).__name__}: {e}"
                record = ReloadRecord(
                    module_name=module_name,
                    timestamp=ts,
                    success=False,
                    error=error_msg,
                    duration_ms=round(duration, 2),
                )
                self._append_history(record)
                logger.error("Failed to reload %s: %s", module_name, error_msg)

                for cb in self._callbacks:
                    try:
                        cb(module_name, False, error_msg)
                    except Exception:
                        pass

                return record

    def reload_all(self, force: bool = False) -> List[ReloadRecord]:
        """Reload all registered modules.

        Returns:
            List of ReloadRecords for each module.
        """
        with self._lock:
            names = list(self._modules.keys())

        results = []
        for name in names:
            results.append(self.reload(name, force=force))
        return results

    def reload_by_path(self, file_path: str) -> List[ReloadRecord]:
        """Reload modules whose source file matches the given path.

        Used by the file watcher to map changed files to modules.
        """
        resolved = Path(file_path).resolve()
        results = []
        with self._lock:
            for entry in self._modules.values():
                if entry.file_path:
                    if Path(entry.file_path).resolve() == resolved:
                        results.append(self.reload(entry.name, force=True))
        return results

    # ─── Callbacks ────────────────────────────────────────────────────────

    def on_reload(self, callback: Callable[[str, bool, Optional[str]], None]):
        """Register a callback fired after each reload.

        Callback signature: (module_name: str, success: bool, error: Optional[str])
        """
        with self._lock:
            self._callbacks.append(callback)

    # ─── Queries ──────────────────────────────────────────────────────────

    def get_module(self, module_name: str) -> Optional[Any]:
        """Get the current module object for a registered module."""
        with self._lock:
            entry = self._modules.get(module_name)
            return entry.module if entry else None

    @property
    def registered_modules(self) -> List[str]:
        """List all registered module names."""
        with self._lock:
            return list(self._modules.keys())

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get reload history as list of dicts."""
        with self._lock:
            return [
                {
                    "module": r.module_name,
                    "timestamp": r.timestamp,
                    "success": r.success,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                }
                for r in self._history
            ]

    def status(self) -> Dict[str, Any]:
        """Get registry status summary."""
        with self._lock:
            modules_info = {}
            for name, entry in self._modules.items():
                modules_info[name] = {
                    "last_reloaded": entry.last_reloaded,
                    "reload_count": entry.reload_count,
                    "file_path": entry.file_path,
                }

            return {
                "registered_count": len(self._modules),
                "modules": modules_info,
                "total_reloads": sum(e.reload_count for e in self._modules.values()),
                "history_length": len(self._history),
                "last_reload": self._history[-1].timestamp if self._history else None,
            }

    # ─── Internals ────────────────────────────────────────────────────────

    def _append_history(self, record: ReloadRecord):
        """Append to history with size cap."""
        self._history.append(record)
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]


# ─── Singleton ────────────────────────────────────────────────────────────────

_global_registry: Optional[ModuleRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> ModuleRegistry:
    """Get or create the global module registry singleton."""
    global _global_registry
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = ModuleRegistry()
    return _global_registry


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    """CLI for module registry operations."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Module Registry")
    parser.add_argument("--status", action="store_true", help="Show registry status")
    parser.add_argument("--register", type=str, help="Register a module")
    parser.add_argument("--reload", type=str, help="Reload a module")
    parser.add_argument("--reload-all", action="store_true", help="Reload all modules")
    parser.add_argument("--list", action="store_true", help="List registered modules")

    args = parser.parse_args()
    registry = get_registry()

    # Default modules to register
    default_modules = [
        "agents.runner_api",
        "agents.install_api",
    ]

    if args.register:
        ok = registry.register(args.register)
        print(f"{'OK' if ok else 'FAIL'}: {args.register}")
    elif args.reload:
        registry.register(args.reload)
        result = registry.reload(args.reload, force=True)
        print(f"{'OK' if result.success else 'FAIL'}: {result.module_name} ({result.duration_ms}ms)")
        if result.error:
            print(f"  Error: {result.error}")
    elif args.reload_all:
        for m in default_modules:
            registry.register(m)
        results = registry.reload_all(force=True)
        for r in results:
            status = "OK" if r.success else "FAIL"
            print(f"  {status}: {r.module_name} ({r.duration_ms}ms)")
    elif args.list or args.status:
        for m in default_modules:
            registry.register(m)
        import json
        print(json.dumps(registry.status(), indent=2))
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
