#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_orchestrator [python]
# Author: Claude | Created: 2026-02-06T23:30:00Z
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Persistent daemon with dev hot-reload via watchfiles
# Purpose: Unified SLATE system orchestrator - persistent daemon with dev/prod modes
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE Orchestrator
==================
Persistent daemon managing the complete SLATE system lifecycle.

Modes:
- **dev**:  Hot-reload via watchfiles (agents/, skills/, tasks.json).
            Modules reloaded via importlib; WebSocket push to dashboard.
- **prod**: Static process supervision, no reload. Docker/systemd-bound.

Services managed:
- Dashboard server (FastAPI on port 8080)
- GitHub Actions runner (self-hosted)
- Workflow manager (task lifecycle)
- System health monitoring
- File watcher (dev mode only)

Usage:
    python slate/slate_orchestrator.py start              # Start (auto-detect mode)
    python slate/slate_orchestrator.py start --mode dev   # Force dev mode
    python slate/slate_orchestrator.py start --mode prod  # Force prod mode
    python slate/slate_orchestrator.py stop               # Stop all services
    python slate/slate_orchestrator.py status              # Show service status
    python slate/slate_orchestrator.py restart             # Restart all services

Environment:
    SLATE_MODE=dev|prod  — Override mode detection
"""

import argparse
import atexit
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("slate.orchestrator")

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# PID file for tracking running orchestrator
PID_FILE = WORKSPACE_ROOT / ".slate_orchestrator.pid"
STATE_FILE = WORKSPACE_ROOT / ".slate_orchestrator_state.json"


# ─── Mode detection ──────────────────────────────────────────────────────────

def detect_mode() -> str:
    """Detect dev vs prod mode.

    Order of precedence:
    1. SLATE_MODE env var
    2. Running inside Docker -> prod
    3. .venv exists -> dev
    4. Default -> prod
    """
    env_mode = os.environ.get("SLATE_MODE", "").lower().strip()
    if env_mode in ("dev", "development"):
        return "dev"
    if env_mode in ("prod", "production"):
        return "prod"

    # Docker detection
    if Path("/.dockerenv").exists() or os.environ.get("SLATE_DOCKER"):
        return "prod"

    # venv implies local dev
    if (WORKSPACE_ROOT / ".venv").exists():
        return "dev"

    return "prod"


class SlateOrchestrator:
    """Manages all SLATE system services."""

    def __init__(self, mode: Optional[str] = None):
        self.workspace = WORKSPACE_ROOT
        self.runner_dir = self.workspace / "actions-runner"
        self.processes: Dict[str, subprocess.Popen] = {}
        self.running = False
        self._shutdown_event = threading.Event()
        self.mode = mode or detect_mode()
        self._dev_reload_manager = None
        self._restart_counts: Dict[str, int] = {}
        self._last_restart: Dict[str, float] = {}

    def _get_python(self) -> str:
        """Get venv Python path."""
        if os.name == "nt":
            return str(self.workspace / ".venv" / "Scripts" / "python.exe")
        return str(self.workspace / ".venv" / "bin" / "python")

    def _save_state(self, state: Dict[str, Any]):
        """Save orchestrator state to file."""
        state["updated_at"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")

    def _load_state(self) -> Dict[str, Any]:
        """Load orchestrator state from file."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"services": {}, "started_at": None}

    def _write_pid(self):
        """Write current PID to file."""
        PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    def _clear_pid(self):
        """Remove PID file."""
        if PID_FILE.exists():
            PID_FILE.unlink()

    def _check_existing(self) -> Optional[int]:
        """Check if orchestrator is already running."""
        if not PID_FILE.exists():
            return None
        try:
            pid = int(PID_FILE.read_text().strip())
            # Check if process exists
            if os.name == "nt":
                result = subprocess.run(
                    ["tasklist", "/FI", f"PID eq {pid}"],
                    capture_output=True, text=True
                )
                if str(pid) in result.stdout:
                    return pid
            else:
                os.kill(pid, 0)  # Signal 0 = check if exists
                return pid
        except (ValueError, OSError, ProcessLookupError):
            self._clear_pid()
        return None

    def start_runner(self) -> bool:
        """Start the GitHub Actions runner."""
        run_cmd = self.runner_dir / "run.cmd"
        if not run_cmd.exists():
            print("  [!] Runner not installed at", self.runner_dir)
            return False

        # FIRST: Check if runner process is already running locally
        try:
            proc_check = subprocess.run(
                ["powershell", "-Command",
                 "Get-Process -Name 'Runner.Listener' -ErrorAction SilentlyContinue | Select-Object Id"],
                capture_output=True, text=True, timeout=5
            )
            if proc_check.returncode == 0 and proc_check.stdout.strip() and "Id" in proc_check.stdout:
                print("  [OK] Runner process already running")
                return True
        except Exception:
            pass

        # SECOND: Check GitHub API for runner status
        try:
            from slate.slate_runner_manager import SlateRunnerManager
            manager = SlateRunnerManager()
            detection = manager.detect()

            gh = detection.get("github", {})
            if gh.get("authenticated"):
                gh_cli = manager.gh_cli
                result = subprocess.run(
                    [gh_cli, "api", "repos/SynchronizedLivingArchitecture/S.L.A.T.E/actions/runners",
                     "--jq", ".runners[] | select(.name==\"slate-DESKTOP-R3UD82D\") | .status"],
                    capture_output=True, text=True, timeout=10, cwd=str(self.workspace)
                )
                if result.returncode == 0 and "online" in result.stdout:
                    print("  [OK] Runner already online (GitHub)")
                    return True
        except Exception:
            pass

        # Start runner process (only if not already running)
        try:
            if os.name == "nt":
                # Windows: start in background
                process = subprocess.Popen(
                    ["cmd", "/c", str(run_cmd)],
                    cwd=str(self.runner_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS
                )
            else:
                process = subprocess.Popen(
                    [str(run_cmd)],
                    cwd=str(self.runner_dir),
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True
                )

            self.processes["runner"] = process
            print(f"  [OK] Runner started (PID {process.pid})")
            return True
        except Exception as e:
            print(f"  [X] Runner failed: {e}")
            return False

    def start_dashboard(self) -> bool:
        """Start the SLATE dashboard server.

        Handles port conflicts by killing stale processes before starting.
        """
        # Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Handle port 8080 conflicts before starting dashboard
        dashboard_script = self.workspace / "agents" / "slate_dashboard_server.py"

        if not dashboard_script.exists():
            print("  [!] Dashboard server not found")
            return False

        # Kill stale processes on port 8080 before starting
        try:
            if os.name == "nt":
                check = subprocess.run(
                    ["powershell", "-Command",
                     "Get-NetTCPConnection -LocalPort 8080 -ErrorAction SilentlyContinue | Select-Object -ExpandProperty OwningProcess -Unique"],
                    capture_output=True, text=True, timeout=5
                )
                if check.returncode == 0 and check.stdout.strip():
                    for pid_str in check.stdout.strip().splitlines():
                        pid_str = pid_str.strip()
                        if pid_str.isdigit() and int(pid_str) != os.getpid():
                            try:
                                subprocess.run(
                                    ["taskkill", "/F", "/PID", pid_str],
                                    capture_output=True, timeout=5
                                )
                                print(f"  [*] Killed stale process on port 8080 (PID {pid_str})")
                                time.sleep(1)
                            except Exception:
                                pass
        except Exception:
            pass

        try:
            python = self._get_python()
            process = subprocess.Popen(
                [python, str(dashboard_script)],
                cwd=str(self.workspace),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
            self.processes["dashboard"] = process
            print(f"  [OK] Dashboard started (PID {process.pid}) > http://127.0.0.1:8080")
            return True
        except Exception as e:
            print(f"  [X] Dashboard failed: {e}")
            return False

    def start_workflow_monitor(self) -> bool:
        """Start the workflow monitor for task lifecycle management."""
        # This runs as a background thread, not a separate process
        try:
            from slate.slate_workflow_manager import SlateWorkflowManager

            def monitor_loop():
                manager = SlateWorkflowManager()
                while not self._shutdown_event.is_set():
                    try:
                        # Check and cleanup every 5 minutes
                        analysis = manager.analyze_tasks()
                        if analysis.get("needs_attention"):
                            manager.cleanup(dry_run=False)
                    except Exception:
                        pass
                    self._shutdown_event.wait(300)  # 5 minute interval

            thread = threading.Thread(target=monitor_loop, daemon=True, name="workflow-monitor")
            thread.start()
            print("  [OK] Workflow monitor started")
            return True
        except Exception as e:
            print(f"  [!] Workflow monitor skipped: {e}")
            return True  # Non-fatal

    def start_file_watcher(self) -> bool:
        """Start the dev-mode file watcher for hot-reloading.

        Only active in dev mode. Watches agents/, skills/, current_tasks.json
        and reloads modules via importlib + pushes WebSocket notifications.
        """
        if self.mode != "dev":
            print("  [~] File watcher skipped (prod mode)")
            return True  # Not an error in prod

        try:
            from slate.slate_watcher import DevReloadManager

            # Create broadcast function that pushes to dashboard WebSocket
            def _broadcast_sync(message: dict):
                """Synchronous wrapper for WebSocket broadcast."""
                try:
                    import urllib.request
                    data = json.dumps(message).encode('utf-8')
                    req = urllib.request.Request(
                        'http://127.0.0.1:8080/api/watcher-event',
                        data=data,
                        headers={'Content-Type': 'application/json'},
                        method='POST',
                    )
                    urllib.request.urlopen(req, timeout=2)
                except Exception:
                    pass  # Dashboard may not be up yet

            self._dev_reload_manager = DevReloadManager(
                broadcast_callback=_broadcast_sync,
            )
            success = self._dev_reload_manager.start()
            if success:
                print("  [OK] File watcher started (dev hot-reload active)")
            else:
                print("  [!] File watcher failed to start")
            return success

        except ImportError as e:
            print(f"  [!] File watcher unavailable: {e}")
            return True  # Non-fatal
        except Exception as e:
            print(f"  [!] File watcher error: {e}")
            return True  # Non-fatal

    def _auto_restart_service(self, service_name: str) -> bool:
        """Auto-restart a crashed service with exponential backoff."""
        MAX_RESTARTS = 5
        BACKOFF_BASE = 2  # seconds

        now = time.time()
        count = self._restart_counts.get(service_name, 0)
        last = self._last_restart.get(service_name, 0)

        # Reset counter if 5+ minutes since last restart
        if now - last > 300:
            count = 0

        if count >= MAX_RESTARTS:
            print(f"  [!] {service_name}: Max restart attempts ({MAX_RESTARTS}) reached")
            # Reset after 10 minutes
            if now - last > 600:
                self._restart_counts[service_name] = 0
            return False

        # Exponential backoff
        backoff = BACKOFF_BASE * (2 ** count)
        if now - last < backoff:
            return False

        print(f"  [*] Auto-restarting {service_name} (attempt {count + 1}/{MAX_RESTARTS})")

        success = False
        if service_name == "dashboard":
            success = self.start_dashboard()
        elif service_name == "runner":
            success = self.start_runner()

        self._restart_counts[service_name] = count + 1
        self._last_restart[service_name] = now

        if success:
            print(f"  [OK] {service_name} restarted successfully")
        else:
            print(f"  [!] {service_name} restart failed")

        return success

    def start(self) -> bool:
        """Start all SLATE services."""
        existing_pid = self._check_existing()
        if existing_pid:
            print(f"[!] SLATE orchestrator already running (PID {existing_pid})")
            return False

        print()
        print("=" * 60)
        print("  Starting SLATE Orchestrator")
        print("=" * 60)
        print()

        self._write_pid()
        atexit.register(self._clear_pid)

        # Register signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

        services_started = 0
        services_total = 4 if self.mode == "dev" else 3

        # 1. Start GitHub Runner
        print(f"  [1/{services_total}] GitHub Runner...")
        if self.start_runner():
            services_started += 1
        time.sleep(1)

        # 2. Start Dashboard
        print(f"  [2/{services_total}] Dashboard Server...")
        if self.start_dashboard():
            services_started += 1
        time.sleep(0.5)

        # 3. Start Workflow Monitor
        print(f"  [3/{services_total}] Workflow Monitor...")
        if self.start_workflow_monitor():
            services_started += 1

        # 4. Start File Watcher (dev only)
        if self.mode == "dev":
            print(f"  [4/{services_total}] File Watcher...")
            if self.start_file_watcher():
                services_started += 1

        # Verify dashboard is actually responding
        time.sleep(2)
        dashboard_ok = False
        try:
            import urllib.request
            resp = urllib.request.urlopen("http://127.0.0.1:8080/health", timeout=5)
            dashboard_ok = resp.status == 200
        except Exception:
            pass

        if not dashboard_ok and "dashboard" in self.processes:
            # Dashboard process may have crashed silently on port conflict
            proc = self.processes["dashboard"]
            if proc.poll() is not None:
                print(f"  [!] Dashboard exited (code {proc.returncode}), retrying...")
                del self.processes["dashboard"]
                if self.start_dashboard():
                    time.sleep(2)

        print()
        print("=" * 60)
        print(f"  SLATE Started: {services_started}/{services_total} services")
        print(f"  Mode: {self.mode.upper()}")
        print("=" * 60)
        print()
        print("  Dashboard:  http://127.0.0.1:8080")
        print("  Runner:     slate-DESKTOP-R3UD82D")
        if self.mode == "dev":
            print("  Hot-Reload: Active (agents/, skills/, tasks.json)")
            print("  Reload API: POST http://127.0.0.1:8080/api/reload")
        print()
        print("  Press Ctrl+C to stop")
        print()

        # Save state
        self._save_state({
            "status": "running",
            "started_at": datetime.now(timezone.utc).isoformat(),
            "services": {
                "runner": "runner" in self.processes,
                "dashboard": "dashboard" in self.processes,
                "workflow_monitor": True
            },
            "pid": os.getpid()
        })

        self.running = True

        # Keep running until shutdown with auto-restart
        try:
            while self.running and not self._shutdown_event.is_set():
                # Check if child processes are still running and restart if needed
                for name, proc in list(self.processes.items()):
                    if proc.poll() is not None:
                        exit_code = proc.returncode
                        del self.processes[name]
                        print(f"  [!] {name} exited with code {exit_code}")

                        # Auto-restart with backoff
                        self._auto_restart_service(name)

                time.sleep(5)
        except KeyboardInterrupt:
            pass

        self.stop()
        return True

    def _signal_handler(self, signum, frame):
        """Handle shutdown signals."""
        print("\n  [!] Shutdown signal received...")
        self.running = False
        self._shutdown_event.set()

    def stop(self):
        """Stop all SLATE services."""
        print()
        print("  Stopping SLATE services...")

        self._shutdown_event.set()

        # Stop file watcher
        if self._dev_reload_manager:
            try:
                self._dev_reload_manager.stop()
                print("  [OK] File watcher stopped")
            except Exception as e:
                print(f"  [!] File watcher stop error: {e}")

        # Stop managed processes
        for name, proc in self.processes.items():
            try:
                proc.terminate()
                proc.wait(timeout=5)
                print(f"  [OK] {name} stopped")
            except subprocess.TimeoutExpired:
                proc.kill()
                print(f"  [!] {name} killed")
            except Exception as e:
                print(f"  [!] {name} stop error: {e}")

        # Stop any orphaned runner processes
        try:
            if os.name == "nt":
                subprocess.run(
                    ["taskkill", "/F", "/IM", "Runner.Listener.exe"],
                    capture_output=True
                )
        except Exception:
            pass

        self._save_state({
            "status": "stopped",
            "stopped_at": datetime.now(timezone.utc).isoformat(),
            "services": {}
        })

        self._clear_pid()
        print("  [OK] SLATE stopped")
        print()

    def status(self, skip_dashboard_check: bool = False) -> Dict[str, Any]:
        """Get status of all SLATE services.

        Args:
            skip_dashboard_check: If True, skip the HTTP health check of the dashboard.
                Used when called FROM the dashboard itself to avoid recursive self-connection.
        """
        # Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Add Docker daemon status to orchestrator status
        result = {
            "orchestrator": {"running": False, "pid": None, "mode": self.mode},
            "runner": {"running": False, "status": "unknown"},
            "dashboard": {"running": False, "port": 8080},
            "workflow": {"task_count": 0, "healthy": False},
            "file_watcher": {"running": False, "mode": self.mode},
            "docker": {"available": False, "daemon_running": False, "containers": 0},
        }

        # Check orchestrator
        existing_pid = self._check_existing()
        if existing_pid:
            result["orchestrator"]["running"] = True
            result["orchestrator"]["pid"] = existing_pid

        # Check runner via GitHub API
        try:
            from slate.slate_runner_manager import SlateRunnerManager
            manager = SlateRunnerManager()
            gh_cli = manager.gh_cli

            check = subprocess.run(
                [gh_cli, "api", "repos/SynchronizedLivingArchitecture/S.L.A.T.E/actions/runners",
                 "--jq", ".runners[0] | {status, busy}"],
                capture_output=True, text=True, timeout=10, cwd=str(self.workspace)
            )
            if check.returncode == 0:
                data = json.loads(check.stdout)
                result["runner"]["running"] = data.get("status") == "online"
                result["runner"]["status"] = data.get("status", "unknown")
                result["runner"]["busy"] = data.get("busy", False)
        except Exception:
            pass

        # Check dashboard
        # Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Use http.client for robust health check
        if skip_dashboard_check:
            # When called from the dashboard itself, assume it's running
            result["dashboard"]["running"] = True
        else:
            try:
                import http.client
                conn = http.client.HTTPConnection("127.0.0.1", 8080, timeout=3)
                conn.request("GET", "/health")
                resp = conn.getresponse()
                result["dashboard"]["running"] = resp.status == 200
                conn.close()
            except Exception:
                pass

        # Check workflow
        try:
            from slate.slate_workflow_manager import SlateWorkflowManager
            manager = SlateWorkflowManager()
            analysis = manager.analyze_tasks()
            result["workflow"]["task_count"] = analysis.get("total", 0)
            result["workflow"]["healthy"] = not analysis.get("needs_attention", True)
            result["workflow"]["in_progress"] = analysis.get("by_status", {}).get("in-progress", 0)
        except Exception:
            pass

        # Check file watcher (dev mode)
        if self._dev_reload_manager:
            try:
                watcher_status = self._dev_reload_manager.status()
                result["file_watcher"]["running"] = watcher_status.get("watcher", {}).get("running", False)
                result["file_watcher"]["registry"] = watcher_status.get("registry", {})
            except Exception:
                pass

        # Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Add Docker daemon status integration
        # Check Docker daemon
        try:
            from slate.slate_docker_daemon import SlateDockerDaemon
            docker_daemon = SlateDockerDaemon()
            detection = docker_daemon.detect()
            result["docker"]["available"] = detection.get("installed", False)
            result["docker"]["daemon_running"] = detection.get("daemon_running", False)
            result["docker"]["version"] = detection.get("version")
            result["docker"]["gpu_runtime"] = detection.get("gpu_runtime", False)
            if detection["daemon_running"]:
                containers = docker_daemon.list_containers()
                running = [c for c in containers if c["state"].lower() == "running"]
                result["docker"]["containers"] = len(containers)
                result["docker"]["running"] = len(running)
        except Exception:
            pass

        return result

    def print_status(self):
        """Print formatted status."""
        status = self.status()

        print()
        print("=" * 60)
        print("  SLATE System Status")
        print("=" * 60)
        print()

        # Orchestrator
        orch = status["orchestrator"]
        if orch["running"]:
            print(f"  Orchestrator:  Running (PID {orch['pid']})")
        else:
            print("  Orchestrator:  Stopped")

        # Runner
        runner = status["runner"]
        if runner["running"]:
            busy = " (busy)" if runner.get("busy") else ""
            print(f"  Runner:        Online{busy}")
        else:
            print(f"  Runner:        {runner['status']}")

        # Dashboard
        dash = status["dashboard"]
        if dash["running"]:
            print(f"  Dashboard:     Running > http://127.0.0.1:{dash['port']}")
        else:
            print("  Dashboard:     Stopped")

        # Workflow
        wf = status["workflow"]
        health = "Healthy" if wf["healthy"] else "Needs attention"
        print(f"  Workflow:      {wf['task_count']} tasks ({health})")
        if wf.get("in_progress", 0) > 0:
            print(f"                 {wf['in_progress']} in progress")

        # File Watcher
        fw = status.get("file_watcher", {})
        mode = fw.get("mode", self.mode)
        if mode == "dev":
            fw_status = "Running" if fw.get("running") else "Stopped"
            registry_info = fw.get("registry", {})
            mod_count = registry_info.get("registered_count", 0)
            print(f"  File Watcher:  {fw_status} ({mod_count} modules registered)")
        else:
            print("  File Watcher:  Disabled (prod mode)")

        # Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Display Docker daemon status in orchestrator output
        # Docker
        docker = status.get("docker", {})
        if docker.get("available"):
            if docker.get("daemon_running"):
                running = docker.get("running", 0)
                total = docker.get("containers", 0)
                gpu_tag = " [GPU]" if docker.get("gpu_runtime") else ""
                print(f"  Docker:        v{docker.get('version', '?')}{gpu_tag} ({running}/{total} containers)")
            else:
                print(f"  Docker:        Installed v{docker.get('version', '?')} (daemon stopped)")
        else:
            print("  Docker:        Not installed")

        print(f"  Mode:          {mode.upper()}")
        print()
        print("=" * 60)
        print()


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SLATE Orchestrator - Manages all SLATE services"
    )
    parser.add_argument("command", nargs="?", default="status",
                       choices=["start", "stop", "status", "restart"],
                       help="Command to run")
    parser.add_argument("--json", action="store_true", help="JSON output for status")
    parser.add_argument("--mode", choices=["dev", "prod"],
                       help="Force dev or prod mode (overrides auto-detection)")

    args = parser.parse_args()

    # Configure logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
    )

    orchestrator = SlateOrchestrator(mode=args.mode)

    if args.command == "start":
        orchestrator.start()

    elif args.command == "stop":
        existing = orchestrator._check_existing()
        if existing:
            try:
                os.kill(existing, signal.SIGTERM)
                print(f"[OK] Sent stop signal to PID {existing}")
                time.sleep(2)
            except Exception as e:
                print(f"[!] Failed to stop: {e}")
        else:
            print("[!] Orchestrator not running")
        orchestrator.stop()

    elif args.command == "restart":
        existing = orchestrator._check_existing()
        if existing:
            try:
                os.kill(existing, signal.SIGTERM)
                time.sleep(3)
            except Exception:
                pass
        orchestrator.start()

    elif args.command == "status":
        if args.json:
            print(json.dumps(orchestrator.status(), indent=2))
        else:
            orchestrator.print_status()


if __name__ == "__main__":
    main()
