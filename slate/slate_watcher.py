#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_watcher [python]
# Author: COPILOT | Created: 2026-02-07T06:00:00Z
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Initial creation - watchfiles-based hot-reload daemon
# Purpose: File system watcher for dev hot-reloading of agents, skills, and task config
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE File Watcher
==================
Watches filesystem paths for changes and triggers module reloads + WebSocket
broadcasts in dev mode. Uses the ``watchfiles`` library for efficient,
cross-platform file change detection.

Watched Paths:
- agents/*.py          → importlib.reload via ModuleRegistry
- skills/**            → push notification to dashboard
- current_tasks.json   → push notification to dashboard

Security:
- No eval/exec — delegates to ModuleRegistry (importlib only)
- Local-only — no outbound network calls
- Read-only FS observation — never modifies watched files

Usage:
    # As a thread inside the orchestrator:
    from slate.slate_watcher import SlateFileWatcher
    watcher = SlateFileWatcher(on_change=my_callback)
    watcher.start()   # starts background thread
    watcher.stop()

    # Standalone CLI:
    python slate/slate_watcher.py --watch
    python slate/slate_watcher.py --status
"""

import asyncio
import json
import logging
import os
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("slate.watcher")

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# ─── Watchfiles import guard ─────────────────────────────────────────────────

try:
    from watchfiles import watch, Change
    WATCHFILES_AVAILABLE = True
except ImportError:
    WATCHFILES_AVAILABLE = False
    logger.warning("watchfiles not installed — file watcher disabled")


# ─── Path-to-Module mapping ──────────────────────────────────────────────────

def path_to_module(file_path: Path) -> Optional[str]:
    """Convert a file path to a Python module name relative to workspace root.

    Examples:
        agents/runner_api.py → agents.runner_api
        slate/module_registry.py → slate.module_registry
    """
    try:
        rel = file_path.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        return None

    if rel.suffix != '.py':
        return None

    parts = list(rel.parts)
    # Remove .py extension from last part
    parts[-1] = parts[-1][:-3]
    # Skip __init__
    if parts[-1] == '__init__':
        parts = parts[:-1]
    if not parts:
        return None
    return '.'.join(parts)


# ─── Change Categories ───────────────────────────────────────────────────────

class ChangeCategory:
    """Categorize file changes for routing."""
    AGENT = "agent"
    SKILL = "skill"
    TASK = "task"
    CONFIG = "config"
    UNKNOWN = "unknown"


def categorize_change(file_path: Path) -> str:
    """Categorize a changed file into a change type."""
    try:
        rel = file_path.resolve().relative_to(WORKSPACE_ROOT.resolve())
    except ValueError:
        return ChangeCategory.UNKNOWN

    rel_str = str(rel).replace('\\', '/')

    if rel_str.startswith('agents/') and rel_str.endswith('.py'):
        return ChangeCategory.AGENT
    elif rel_str.startswith('skills/'):
        return ChangeCategory.SKILL
    elif rel_str == 'current_tasks.json':
        return ChangeCategory.TASK
    elif rel_str.endswith('.json') or rel_str.endswith('.yaml') or rel_str.endswith('.yml'):
        return ChangeCategory.CONFIG
    else:
        return ChangeCategory.UNKNOWN


# ─── Change Event ─────────────────────────────────────────────────────────────

class FileChangeEvent:
    """Represents a file change event with metadata."""

    def __init__(self, change_type: str, file_path: Path):
        self.change_type = change_type  # 'added', 'modified', 'deleted'
        self.file_path = file_path
        self.category = categorize_change(file_path)
        self.module_name = path_to_module(file_path) if self.category == ChangeCategory.AGENT else None
        self.timestamp = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "change_type": self.change_type,
            "file_path": str(self.file_path),
            "category": self.category,
            "module_name": self.module_name,
            "timestamp": self.timestamp,
        }


# ─── File Watcher ─────────────────────────────────────────────────────────────

# Map watchfiles Change enum to human-readable strings
CHANGE_NAMES = {1: "added", 2: "modified", 3: "deleted"}


class SlateFileWatcher:
    """Watches SLATE workspace paths for changes and triggers reloads.

    Designed to run as a background thread inside the orchestrator daemon.
    In prod mode, this class is a no-op (never starts).
    """

    def __init__(
        self,
        on_change: Optional[Callable[[List[FileChangeEvent]], None]] = None,
        watch_paths: Optional[List[Path]] = None,
        debounce_ms: int = 300,
    ):
        """
        Args:
            on_change: Callback invoked with batched change events.
            watch_paths: Paths to watch. Defaults to agents/, skills/, current_tasks.json.
            debounce_ms: Debounce interval for watchfiles (ms).
        """
        self._on_change = on_change
        self._debounce_ms = debounce_ms
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._change_history: List[Dict[str, Any]] = []
        self._max_history = 200
        self._lock = threading.Lock()

        # Default watch paths
        if watch_paths is None:
            self._watch_paths = [
                WORKSPACE_ROOT / "agents",
                WORKSPACE_ROOT / "skills",
                WORKSPACE_ROOT / "current_tasks.json",
            ]
        else:
            self._watch_paths = watch_paths

        # Filter to existing paths
        self._watch_paths = [p for p in self._watch_paths if p.exists()]

    @property
    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> bool:
        """Start the file watcher in a background thread.

        Returns:
            True if started, False if watchfiles unavailable or already running.
        """
        if not WATCHFILES_AVAILABLE:
            logger.warning("Cannot start watcher: watchfiles not installed")
            return False

        if self.is_running:
            logger.info("Watcher already running")
            return True

        if not self._watch_paths:
            logger.warning("No valid watch paths found")
            return False

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._watch_loop,
            daemon=True,
            name="slate-file-watcher",
        )
        self._thread.start()
        logger.info(
            "File watcher started — watching %d paths",
            len(self._watch_paths),
        )
        return True

    def stop(self):
        """Stop the file watcher."""
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5)
        self._thread = None
        logger.info("File watcher stopped")

    def _watch_loop(self):
        """Main watch loop — runs in background thread."""
        try:
            # watchfiles.watch is a blocking generator
            for changes in watch(
                *self._watch_paths,
                debounce=self._debounce_ms,
                stop_event=self._stop_event,
                watch_filter=self._filter_change,
            ):
                if self._stop_event.is_set():
                    break

                events = []
                for change_type, path_str in changes:
                    change_name = CHANGE_NAMES.get(change_type, "unknown")
                    event = FileChangeEvent(change_name, Path(path_str))
                    events.append(event)

                if events:
                    self._record_events(events)
                    if self._on_change:
                        try:
                            self._on_change(events)
                        except Exception as e:
                            logger.error("on_change callback error: %s", e)

        except Exception as e:
            if not self._stop_event.is_set():
                logger.error("Watcher loop error: %s", e)

    def _filter_change(self, change: int, path: str) -> bool:
        """Filter which file changes to process."""
        p = Path(path)
        # Skip __pycache__, .pyc, hidden files, temp files
        name = p.name
        if name.startswith('.') or name.startswith('__pycache__'):
            return False
        if p.suffix in ('.pyc', '.pyo', '.tmp', '.swp', '.swo'):
            return False
        # Only watch relevant extensions
        if p.suffix in ('.py', '.json', '.yaml', '.yml', '.md'):
            return True
        return False

    def _record_events(self, events: List[FileChangeEvent]):
        """Record events to history."""
        with self._lock:
            for ev in events:
                self._change_history.append(ev.to_dict())
            # Trim
            if len(self._change_history) > self._max_history:
                self._change_history = self._change_history[-self._max_history:]

    @property
    def history(self) -> List[Dict[str, Any]]:
        """Get change history."""
        with self._lock:
            return list(self._change_history)

    def status(self) -> Dict[str, Any]:
        """Get watcher status."""
        with self._lock:
            return {
                "running": self.is_running,
                "watch_paths": [str(p) for p in self._watch_paths],
                "watchfiles_available": WATCHFILES_AVAILABLE,
                "debounce_ms": self._debounce_ms,
                "history_length": len(self._change_history),
                "last_change": self._change_history[-1] if self._change_history else None,
            }


# ─── Integrated Watcher + Registry ───────────────────────────────────────────

class DevReloadManager:
    """Orchestrates the file watcher + module registry for dev hot-reload.

    Combines SlateFileWatcher with ModuleRegistry to provide:
    1. Watch agents/*.py → importlib.reload via registry
    2. Watch skills/** → broadcast notification
    3. Watch current_tasks.json → broadcast notification
    4. WebSocket broadcast callback for dashboard push
    """

    def __init__(self, broadcast_callback: Optional[Callable[[dict], None]] = None):
        """
        Args:
            broadcast_callback: Async or sync function to push events to
                                WebSocket clients. Signature: (message: dict) -> None
        """
        from slate.module_registry import get_registry

        self._registry = get_registry()
        self._broadcast = broadcast_callback
        self._watcher = SlateFileWatcher(on_change=self._handle_changes)

        # Pre-register known agent modules
        agent_modules = [
            "agents.runner_api",
            "agents.install_api",
        ]
        for mod in agent_modules:
            self._registry.register(mod)

    def start(self) -> bool:
        """Start the dev reload manager."""
        return self._watcher.start()

    def stop(self):
        """Stop the dev reload manager."""
        self._watcher.stop()

    @property
    def is_running(self) -> bool:
        return self._watcher.is_running

    def _handle_changes(self, events: List[FileChangeEvent]):
        """Handle batched file change events."""
        reload_results = []
        notifications = []

        for event in events:
            logger.info(
                "File %s: %s [%s]",
                event.change_type,
                event.file_path,
                event.category,
            )

            if event.category == ChangeCategory.AGENT and event.module_name:
                # Reload Python agent module
                results = self._registry.reload_by_path(str(event.file_path))
                if not results:
                    # Module exists on disk but wasn't registered — register and reload
                    if self._registry.register(event.module_name):
                        result = self._registry.reload(event.module_name, force=True)
                        results = [result]
                reload_results.extend(results)

            elif event.category == ChangeCategory.TASK:
                notifications.append({
                    "type": "tasks_changed",
                    "timestamp": event.timestamp,
                })

            elif event.category == ChangeCategory.SKILL:
                notifications.append({
                    "type": "skills_changed",
                    "file": str(event.file_path),
                    "timestamp": event.timestamp,
                })

        # Broadcast reload results
        if reload_results and self._broadcast:
            for r in reload_results:
                msg = {
                    "type": "module_reloaded",
                    "module": r.module_name,
                    "success": r.success,
                    "error": r.error,
                    "duration_ms": r.duration_ms,
                    "timestamp": r.timestamp,
                }
                try:
                    self._broadcast(msg)
                except Exception as e:
                    logger.error("Broadcast error: %s", e)

        # Broadcast notifications
        if notifications and self._broadcast:
            for note in notifications:
                try:
                    self._broadcast(note)
                except Exception as e:
                    logger.error("Broadcast error: %s", e)

    def status(self) -> Dict[str, Any]:
        """Get combined status."""
        return {
            "watcher": self._watcher.status(),
            "registry": self._registry.status(),
        }

    def trigger_reload(self, module_name: Optional[str] = None) -> Dict[str, Any]:
        """Manually trigger a reload (for /reload endpoint).

        Args:
            module_name: Specific module to reload, or None for all.

        Returns:
            Dict with reload results.
        """
        if module_name:
            self._registry.register(module_name)
            result = self._registry.reload(module_name, force=True)
            return {
                "reloaded": [result.module_name],
                "success": result.success,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        else:
            results = self._registry.reload_all(force=True)
            return {
                "reloaded": [r.module_name for r in results],
                "all_success": all(r.success for r in results),
                "details": [
                    {
                        "module": r.module_name,
                        "success": r.success,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in results
                ],
            }


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point for standalone watcher."""
    import argparse

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    )

    parser = argparse.ArgumentParser(description="SLATE File Watcher")
    parser.add_argument("--watch", action="store_true", help="Start watching for changes")
    parser.add_argument("--status", action="store_true", help="Show watcher status")
    parser.add_argument("--paths", nargs="*", help="Custom paths to watch")

    args = parser.parse_args()

    if args.watch:
        if not WATCHFILES_AVAILABLE:
            print("[!] watchfiles not installed. Run: pip install watchfiles")
            sys.exit(1)

        dev_mgr = DevReloadManager(
            broadcast_callback=lambda msg: print(f"  [WS] {json.dumps(msg)}"),
        )

        print()
        print("=" * 60)
        print("  SLATE File Watcher (Dev Mode)")
        print("=" * 60)
        print()
        for p in dev_mgr._watcher._watch_paths:
            print(f"  Watching: {p}")
        print()
        print("  Press Ctrl+C to stop")
        print()

        dev_mgr.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            dev_mgr.stop()
            print("\n  [OK] Watcher stopped")

    elif args.status:
        watcher = SlateFileWatcher()
        print(json.dumps(watcher.status(), indent=2))

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
