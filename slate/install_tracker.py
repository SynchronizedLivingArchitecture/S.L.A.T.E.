#!/usr/bin/env python3
# Modified: 2026-02-06T19:00:00Z | Author: COPILOT | Change: New install tracking system
"""
SLATE Install Tracker
=====================
Tracks installation progress, persists state to JSON, and broadcasts
events to the SLATE Dashboard via SSE/polling. The dashboard is the
FIRST system installed so all subsequent steps are visible in real-time.

Architecture:
    install_slate.py → InstallTracker → install_state.json ← Dashboard reads
                                      → SSE broadcast    ← Dashboard listens

Usage:
    from slate.install_tracker import InstallTracker
    tracker = InstallTracker()
    tracker.start_step("python_check", "Checking Python Version")
    tracker.complete_step("python_check", success=True, details="Python 3.11.9")
"""

import json
import sys
import time
import threading
from dataclasses import dataclass, field, asdict
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Callable, Optional

WORKSPACE_ROOT = Path(__file__).parent.parent


def _scrub_path(value: str) -> str:
    # Modified: 2026-02-06T00:00:00Z | Author: COPILOT | Change: Scrub local paths for install metadata
    try:
        text = str(value)
    except Exception:
        return value

    workspace = str(WORKSPACE_ROOT)
    home = str(Path.home())
    text_lower = text.lower()
    workspace_lower = workspace.lower()
    home_lower = home.lower()

    if text_lower.startswith(workspace_lower):
        return "<workspace>" + text[len(workspace):]
    if text_lower.startswith(home_lower):
        return "<home>" + text[len(home):]
    return text


class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"
    WARNING = "warning"


@dataclass
class InstallStep:
    id: str
    name: str
    description: str
    status: str = StepStatus.PENDING
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_ms: Optional[int] = None
    details: Optional[str] = None
    error: Optional[str] = None
    progress_pct: int = 0
    substeps: list = field(default_factory=list)
    order: int = 0

    def to_dict(self):
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class InstallState:
    version: str = "1.0.0"
    slate_version: str = ""
    install_id: str = ""
    status: str = "not_started"  # not_started, in_progress, completed, failed
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_step: Optional[str] = None
    steps: list = field(default_factory=list)
    system_info: dict = field(default_factory=dict)
    git_info: dict = field(default_factory=dict)
    errors: list = field(default_factory=list)
    log: list = field(default_factory=list)

    def to_dict(self):
        d = asdict(self)
        d["steps"] = [s if isinstance(s, dict) else asdict(s) for s in self.steps]
        return d


# ─── SSE Event Queue ──────────────────────────────────────────────────────────
_sse_listeners: list = []
_sse_lock = threading.Lock()


def register_sse_listener(callback: Callable):
    """Register a callback for SSE events. Dashboard server calls this."""
    with _sse_lock:
        _sse_listeners.append(callback)


def unregister_sse_listener(callback: Callable):
    with _sse_lock:
        _sse_listeners[:] = [cb for cb in _sse_listeners if cb is not callback]


def _broadcast_sse(event_type: str, data: dict):
    """Broadcast an SSE event to all listeners."""
    with _sse_lock:
        for cb in _sse_listeners:
            try:
                cb(event_type, data)
            except Exception:
                pass


# ─── Install Tracker ──────────────────────────────────────────────────────────

class InstallTracker:
    """
    Tracks installation progress and persists state to disk.

    The state file (.slate_install/install_state.json) is read by the
    dashboard to show real-time install progress. The tracker also
    broadcasts SSE events for live dashboard updates.
    """

    STATE_DIR = WORKSPACE_ROOT / ".slate_install"
    STATE_FILE = STATE_DIR / "install_state.json"
    LOG_FILE = STATE_DIR / "install.log"

    # ── Canonical install steps ──
    INSTALL_STEPS = [
        InstallStep("dashboard_boot", "Dashboard Bootstrap",
                    "Starting SLATE Dashboard (first system online)", order=0),
        InstallStep("python_check", "Python Version",
                    "Verifying Python 3.11+ is available", order=1),
        InstallStep("venv_setup", "Virtual Environment",
                    "Creating .venv virtual environment", order=2),
        InstallStep("deps_install", "Core Dependencies",
                    "Installing requirements.txt packages", order=3),
        InstallStep("gpu_detect", "Hardware Detection",
                    "Detecting NVIDIA GPUs and compute capability", order=4),
        InstallStep("sdk_validate", "SDK Validation",
                    "Validating SLATE SDK imports and version", order=5),
        InstallStep("dirs_create", "Directory Structure",
                    "Creating workspace directories and init files", order=6),
        InstallStep("git_sync", "Git Synchronization",
                    "Syncing with GitHub repository state", order=7),
        InstallStep("benchmark", "System Benchmark",
                    "Running CPU, memory, disk, and GPU benchmarks", order=8),
        InstallStep("runtime_check", "Runtime Verification",
                    "Final verification of all integrations", order=9),
    ]

    def __init__(self):
        self.state = InstallState()
        self.state.install_id = f"install_{int(time.time())}"
        self.state.steps = [InstallStep(
            id=s.id, name=s.name, description=s.description, order=s.order
        ) for s in self.INSTALL_STEPS]
        self._ensure_dirs()
        self._collect_system_info()
        self._collect_git_info()

    def _ensure_dirs(self):
        self.STATE_DIR.mkdir(parents=True, exist_ok=True)

    def _collect_system_info(self):
        """Collect system info for the install state."""
        self.state.system_info = {
            "platform": sys.platform,
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "python_executable": _scrub_path(sys.executable),
            "cwd": _scrub_path(Path.cwd()),
            "workspace_root": _scrub_path(WORKSPACE_ROOT),
        }
        try:
            import psutil
            self.state.system_info["cpu_count"] = psutil.cpu_count()
            mem = psutil.virtual_memory()
            self.state.system_info["ram_total_gb"] = round(mem.total / (1024**3), 1)
            self.state.system_info["ram_available_gb"] = round(mem.available / (1024**3), 1)
        except ImportError:
            pass

    def _collect_git_info(self):
        """Collect git repository info."""
        import subprocess
        try:
            branch = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True, text=True, timeout=5, cwd=str(WORKSPACE_ROOT)
            )
            commit = subprocess.run(
                ["git", "rev-parse", "--short", "HEAD"],
                capture_output=True, text=True, timeout=5, cwd=str(WORKSPACE_ROOT)
            )
            remote = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                capture_output=True, text=True, timeout=5, cwd=str(WORKSPACE_ROOT)
            )
            self.state.git_info = {
                "branch": branch.stdout.strip() if branch.returncode == 0 else "unknown",
                "commit": commit.stdout.strip() if commit.returncode == 0 else "unknown",
                "remote": remote.stdout.strip() if remote.returncode == 0 else "unknown",
            }
        except Exception:
            self.state.git_info = {"branch": "unknown", "commit": "unknown", "remote": "unknown"}

    def _get_step(self, step_id: str) -> Optional[InstallStep]:
        for s in self.state.steps:
            if s.id == step_id:
                return s
        return None

    def _save_state(self):
        """Persist state to JSON for dashboard polling."""
        try:
            with open(self.STATE_FILE, "w") as f:
                json.dump(self.state.to_dict(), f, indent=2, default=str)
        except Exception:
            pass

    def _log(self, message: str, level: str = "INFO"):
        """Append to install log."""
        ts = datetime.now().strftime("%H:%M:%S")
        entry = f"[{ts}] [{level}] {message}"
        self.state.log.append(entry)
        try:
            with open(self.LOG_FILE, "a") as f:
                f.write(entry + "\n")
        except Exception:
            pass
        # Also print to console
        icon = {"INFO": "ℹ", "OK": "✓", "WARN": "⚠", "ERROR": "✗", "STEP": "→"}.get(level, "·")
        print(f"  {icon} {message}")

    def begin_install(self):
        """Mark installation as started."""
        self.state.status = "in_progress"
        self.state.started_at = datetime.now().isoformat()
        try:
            from slate import __version__
            self.state.slate_version = __version__
        except Exception:
            self.state.slate_version = "unknown"
        self._log("S.L.A.T.E. installation started", "STEP")
        self._save_state()
        _broadcast_sse("install_started", {
            "install_id": self.state.install_id,
            "slate_version": self.state.slate_version,
            "system_info": self.state.system_info,
        })

    def start_step(self, step_id: str, substep: str = None):
        """Mark a step as running."""
        step = self._get_step(step_id)
        if not step:
            return
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now().isoformat()
        step.progress_pct = 10
        self.state.current_step = step_id
        if substep:
            step.substeps.append({"name": substep, "started": datetime.now().isoformat()})
        self._log(f"[{step.order + 1}/{len(self.state.steps)}] {step.name}...", "STEP")
        self._save_state()
        _broadcast_sse("step_started", {
            "step_id": step_id,
            "step_name": step.name,
            "order": step.order,
            "total_steps": len(self.state.steps),
        })

    def update_progress(self, step_id: str, progress_pct: int, detail: str = None):
        """Update progress within a step."""
        step = self._get_step(step_id)
        if not step:
            return
        step.progress_pct = min(progress_pct, 99)
        if detail:
            step.details = detail
        self._save_state()
        _broadcast_sse("step_progress", {
            "step_id": step_id,
            "progress_pct": progress_pct,
            "detail": detail,
        })

    def complete_step(self, step_id: str, success: bool = True,
                      details: str = None, error: str = None, warning: bool = False):
        """Mark a step as completed."""
        step = self._get_step(step_id)
        if not step:
            return
        if warning:
            step.status = StepStatus.WARNING
        elif success:
            step.status = StepStatus.SUCCESS
        else:
            step.status = StepStatus.FAILED
            if error:
                step.error = error
                self.state.errors.append({"step": step_id, "error": error,
                                          "time": datetime.now().isoformat()})
        step.completed_at = datetime.now().isoformat()
        step.progress_pct = 100 if success else step.progress_pct
        if step.started_at:
            start = datetime.fromisoformat(step.started_at)
            step.duration_ms = int((datetime.now() - start).total_seconds() * 1000)
        if details:
            step.details = details

        level = "OK" if success else ("WARN" if warning else "ERROR")
        msg = f"{step.name}: {details or ('Done' if success else error or 'Failed')}"
        self._log(msg, level)
        self._save_state()
        _broadcast_sse("step_completed", {
            "step_id": step_id,
            "status": step.status,
            "details": details,
            "error": error,
            "duration_ms": step.duration_ms,
        })

    def skip_step(self, step_id: str, reason: str = "Skipped"):
        """Mark a step as skipped."""
        step = self._get_step(step_id)
        if not step:
            return
        step.status = StepStatus.SKIPPED
        step.details = reason
        step.progress_pct = 100
        self._log(f"{step.name}: {reason}", "INFO")
        self._save_state()
        _broadcast_sse("step_skipped", {"step_id": step_id, "reason": reason})

    def finish_install(self, success: bool = True):
        """Mark installation as complete."""
        self.state.status = "completed" if success else "failed"
        self.state.completed_at = datetime.now().isoformat()
        self.state.current_step = None

        completed = sum(1 for s in self.state.steps
                        if s.status in (StepStatus.SUCCESS, StepStatus.WARNING, StepStatus.SKIPPED))
        failed = sum(1 for s in self.state.steps if s.status == StepStatus.FAILED)

        self._log(
            f"Installation {'completed' if success else 'FAILED'}: "
            f"{completed} passed, {failed} failed",
            "OK" if success else "ERROR"
        )
        self._save_state()
        _broadcast_sse("install_finished", {
            "success": success,
            "completed": completed,
            "failed": failed,
            "total": len(self.state.steps),
        })

    def get_state(self) -> dict:
        """Return current install state as dict (for API)."""
        return self.state.to_dict()

    @classmethod
    def load_state(cls) -> Optional[dict]:
        """Load install state from disk (for dashboard polling)."""
        try:
            if cls.STATE_FILE.exists():
                with open(cls.STATE_FILE) as f:
                    return json.load(f)
        except Exception:
            pass
        return None

    @classmethod
    def get_install_log(cls) -> list:
        """Read install log lines."""
        try:
            if cls.LOG_FILE.exists():
                return cls.LOG_FILE.read_text().strip().split("\n")
        except Exception:
            pass
        return []
