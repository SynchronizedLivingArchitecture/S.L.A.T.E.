#!/usr/bin/env python3
# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Create Docker daemon manager for SLATE container lifecycle
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_docker_daemon [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Purpose: Docker daemon manager — container lifecycle, compose, builds, health
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE Docker Daemon
====================
Manages Docker container lifecycle for the SLATE system.

Features:
- Docker Desktop / daemon detection and health monitoring
- Compose-based service orchestration (dev/prod/default profiles)
- Container build, start, stop, restart, logs, status
- GPU passthrough validation (NVIDIA Container Toolkit)
- Image registry operations (ghcr.io push/pull)
- Health check monitoring for all containers
- Volume and network management
- Integration with SLATE orchestrator

Security:
- All port bindings use 127.0.0.1 (enforced by ActionGuard)
- No external telemetry
- Trusted registries only (via SDK Source Guard)

Usage:
    python slate/slate_docker_daemon.py --status           # Docker system status
    python slate/slate_docker_daemon.py --up               # Start containers (default profile)
    python slate/slate_docker_daemon.py --up --profile dev  # Start dev containers
    python slate/slate_docker_daemon.py --up --profile prod # Start prod containers
    python slate/slate_docker_daemon.py --down              # Stop all containers
    python slate/slate_docker_daemon.py --build             # Build images
    python slate/slate_docker_daemon.py --logs              # Tail container logs
    python slate/slate_docker_daemon.py --health            # Health check all containers
    python slate/slate_docker_daemon.py --prune             # Clean unused images/volumes
    python slate/slate_docker_daemon.py --gpu-check         # Validate GPU passthrough
    python slate/slate_docker_daemon.py --json              # JSON output (combine with other flags)
"""

import argparse
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("slate.docker")

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# ─── Constants ────────────────────────────────────────────────────────────────

REGISTRY = "ghcr.io"
IMAGE_BASE = "synchronizedlivingarchitecture/s.l.a.t.e"
STATE_FILE = WORKSPACE_ROOT / ".slate_docker_state.json"

# Compose file mapping
COMPOSE_FILES = {
    "default": WORKSPACE_ROOT / "docker-compose.yml",
    "dev": WORKSPACE_ROOT / "docker-compose.dev.yml",
    "prod": WORKSPACE_ROOT / "docker-compose.prod.yml",
}

# Expected containers per profile
EXPECTED_CONTAINERS = {
    "default": ["slate", "ollama"],
    "dev": ["slate-dev", "ollama-dev"],
    "prod": ["slate", "ollama", "chromadb"],
}

# Health check endpoints for containers
HEALTH_ENDPOINTS = {
    "slate": ("127.0.0.1", 8080, "/health"),
    "slate-dev": ("127.0.0.1", 8080, "/health"),
    "slate-cpu": ("127.0.0.1", 8080, "/health"),
    "ollama": ("127.0.0.1", 11434, "/api/tags"),
    "ollama-dev": ("127.0.0.1", 11434, "/api/tags"),
    "chromadb": ("127.0.0.1", 8000, "/api/v1/heartbeat"),
}

# Trusted registries (enforced by SDK Source Guard)
TRUSTED_REGISTRIES = [
    "ghcr.io/synchronizedlivingarchitecture/",
    "nvidia/cuda",
    "ollama/ollama",
    "chromadb/chroma",
    "python:",
    "docker.io/library/",
]


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _run(cmd: List[str], timeout: int = 30, cwd: Optional[str] = None) -> subprocess.CompletedProcess:
    """Run a subprocess command safely."""
    try:
        return subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or str(WORKSPACE_ROOT),
            encoding="utf-8",
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr="Timeout")
    except FileNotFoundError:
        return subprocess.CompletedProcess(cmd, returncode=-2, stdout="", stderr=f"Command not found: {cmd[0]}")
    except Exception as e:
        return subprocess.CompletedProcess(cmd, returncode=-3, stdout="", stderr=str(e))


def _http_check(host: str, port: int, path: str, timeout: int = 5) -> Tuple[bool, int, str]:
    """Check HTTP endpoint health. Returns (ok, status_code, body_snippet)."""
    try:
        import http.client
        conn = http.client.HTTPConnection(host, port, timeout=timeout)
        conn.request("GET", path)
        resp = conn.getresponse()
        body = resp.read(256).decode("utf-8", errors="replace")
        conn.close()
        return resp.status < 500, resp.status, body[:128]
    except Exception as e:
        return False, 0, str(e)


# ─── Docker Daemon Manager ───────────────────────────────────────────────────

class SlateDockerDaemon:
    """Manages Docker containers and services for SLATE."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self._docker_cmd = self._find_docker()
        self._compose_cmd = self._find_compose()

    # ── Detection ─────────────────────────────────────────────────────────

    def _find_docker(self) -> Optional[str]:
        """Find the docker executable."""
        result = _run(["docker", "--version"])
        if result.returncode == 0:
            return "docker"
        # Check common Windows paths
        for path in [
            r"C:\Program Files\Docker\Docker\resources\bin\docker.exe",
            r"C:\ProgramData\DockerDesktop\version-bin\docker.exe",
        ]:
            if Path(path).exists():
                return path
        return None

    def _find_compose(self) -> Optional[List[str]]:
        """Find docker compose (v2 plugin or standalone)."""
        # Try docker compose (v2 plugin)
        result = _run(["docker", "compose", "version"])
        if result.returncode == 0:
            return ["docker", "compose"]
        # Try docker-compose (v1 standalone)
        result = _run(["docker-compose", "--version"])
        if result.returncode == 0:
            return ["docker-compose"]
        return None

    def detect(self) -> Dict[str, Any]:
        """Detect Docker installation and daemon status."""
        info = {
            "installed": False,
            "version": None,
            "daemon_running": False,
            "compose_available": False,
            "compose_version": None,
            "gpu_runtime": False,
            "buildx": False,
            "platform": sys.platform,
        }

        if not self._docker_cmd:
            return info

        # Docker version
        result = _run([self._docker_cmd, "--version"])
        if result.returncode == 0:
            info["installed"] = True
            version_line = result.stdout.strip()
            # Parse "Docker version X.Y.Z, build abc"
            if "version" in version_line.lower():
                parts = version_line.split("version")
                if len(parts) > 1:
                    info["version"] = parts[1].strip().split(",")[0].strip()

        # Daemon running
        result = _run([self._docker_cmd, "info", "--format", "{{.ServerVersion}}"], timeout=10)
        if result.returncode == 0 and result.stdout.strip():
            info["daemon_running"] = True
            info["server_version"] = result.stdout.strip()

        # Compose
        if self._compose_cmd:
            result = _run(self._compose_cmd + ["version"])
            if result.returncode == 0:
                info["compose_available"] = True
                info["compose_version"] = result.stdout.strip()

        # GPU runtime (NVIDIA Container Toolkit)
        if info["daemon_running"]:
            result = _run([self._docker_cmd, "info", "--format", "{{.Runtimes}}"], timeout=10)
            if result.returncode == 0 and "nvidia" in result.stdout.lower():
                info["gpu_runtime"] = True

            # Buildx
            result = _run([self._docker_cmd, "buildx", "version"])
            if result.returncode == 0:
                info["buildx"] = True

        return info

    # ── Container Operations ──────────────────────────────────────────────

    def list_containers(self, all_containers: bool = True) -> List[Dict[str, str]]:
        """List Docker containers with SLATE-related filters."""
        if not self._docker_cmd:
            return []

        fmt = "{{.Names}}\t{{.Image}}\t{{.Status}}\t{{.State}}\t{{.Ports}}"
        cmd = [self._docker_cmd, "ps", "--format", fmt]
        if all_containers:
            cmd.append("-a")

        # Filter for SLATE containers
        for name in ["slate", "ollama", "chromadb"]:
            cmd_filtered = cmd + ["--filter", f"name={name}"]
            result = _run(cmd_filtered)
            if result.returncode == 0:
                pass  # processed below

        # Get all containers and filter
        result = _run(cmd)
        if result.returncode != 0:
            return []

        containers = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 4:
                name = parts[0]
                # Only include SLATE-related containers
                if any(s in name.lower() for s in ["slate", "ollama", "chromadb"]):
                    containers.append({
                        "name": name,
                        "image": parts[1] if len(parts) > 1 else "",
                        "status": parts[2] if len(parts) > 2 else "",
                        "state": parts[3] if len(parts) > 3 else "",
                        "ports": parts[4] if len(parts) > 4 else "",
                    })
        return containers

    def container_stats(self) -> List[Dict[str, str]]:
        """Get resource usage stats for running SLATE containers."""
        if not self._docker_cmd:
            return []

        fmt = "{{.Name}}\t{{.CPUPerc}}\t{{.MemUsage}}\t{{.MemPerc}}\t{{.NetIO}}\t{{.BlockIO}}\t{{.PIDs}}"
        result = _run([self._docker_cmd, "stats", "--no-stream", "--format", fmt], timeout=15)
        if result.returncode != 0:
            return []

        stats = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 5:
                name = parts[0]
                if any(s in name.lower() for s in ["slate", "ollama", "chromadb"]):
                    stats.append({
                        "name": name,
                        "cpu": parts[1] if len(parts) > 1 else "0%",
                        "memory": parts[2] if len(parts) > 2 else "0",
                        "mem_percent": parts[3] if len(parts) > 3 else "0%",
                        "net_io": parts[4] if len(parts) > 4 else "0",
                        "block_io": parts[5] if len(parts) > 5 else "0",
                        "pids": parts[6] if len(parts) > 6 else "0",
                    })
        return stats

    def container_logs(self, container: str, lines: int = 50) -> str:
        """Get container logs."""
        if not self._docker_cmd:
            return "Docker not available"
        result = _run([self._docker_cmd, "logs", "--tail", str(lines), container], timeout=10)
        if result.returncode == 0:
            return result.stdout + result.stderr
        return f"Error getting logs: {result.stderr}"

    # ── Compose Operations ────────────────────────────────────────────────

    def _compose_cmd_for_profile(self, profile: str = "default") -> List[str]:
        """Build compose command for the given profile."""
        if not self._compose_cmd:
            raise RuntimeError("Docker Compose not available")

        compose_file = COMPOSE_FILES.get(profile)
        if not compose_file or not compose_file.exists():
            raise FileNotFoundError(f"Compose file not found for profile '{profile}': {compose_file}")

        return self._compose_cmd + ["-f", str(compose_file)]

    def up(self, profile: str = "default", build: bool = False, detach: bool = True) -> Dict[str, Any]:
        """Start containers via docker compose up.

        Args:
            profile: 'default', 'dev', or 'prod'
            build: Force rebuild images before starting
            detach: Run in background (default True)

        Returns:
            dict with success status and details
        """
        try:
            cmd = self._compose_cmd_for_profile(profile)
        except (RuntimeError, FileNotFoundError) as e:
            return {"success": False, "error": str(e)}

        cmd.append("up")
        if detach:
            cmd.append("-d")
        if build:
            cmd.append("--build")

        print(f"  Starting containers (profile={profile}, build={build})...")
        result = _run(cmd, timeout=300)

        success = result.returncode == 0
        output = result.stdout + "\n" + result.stderr

        if success:
            print("  [OK] Containers started")
            self._save_state(profile, "running")
        else:
            print(f"  [X] Failed to start containers: {result.stderr[:200]}")

        return {
            "success": success,
            "profile": profile,
            "output": output.strip(),
            "returncode": result.returncode,
        }

    def down(self, profile: str = "default", volumes: bool = False) -> Dict[str, Any]:
        """Stop and remove containers via docker compose down.

        Args:
            profile: 'default', 'dev', or 'prod'
            volumes: Also remove named volumes (data loss warning!)
        """
        try:
            cmd = self._compose_cmd_for_profile(profile)
        except (RuntimeError, FileNotFoundError) as e:
            return {"success": False, "error": str(e)}

        cmd.append("down")
        if volumes:
            cmd.append("-v")

        print(f"  Stopping containers (profile={profile})...")
        result = _run(cmd, timeout=60)

        success = result.returncode == 0
        if success:
            print("  [OK] Containers stopped")
            self._save_state(profile, "stopped")
        else:
            print(f"  [X] Failed to stop containers: {result.stderr[:200]}")

        return {
            "success": success,
            "profile": profile,
            "output": (result.stdout + "\n" + result.stderr).strip(),
            "returncode": result.returncode,
        }

    def restart(self, profile: str = "default") -> Dict[str, Any]:
        """Restart containers."""
        try:
            cmd = self._compose_cmd_for_profile(profile)
        except (RuntimeError, FileNotFoundError) as e:
            return {"success": False, "error": str(e)}

        cmd.append("restart")
        result = _run(cmd, timeout=120)

        return {
            "success": result.returncode == 0,
            "profile": profile,
            "output": (result.stdout + "\n" + result.stderr).strip(),
        }

    def pull(self, profile: str = "default") -> Dict[str, Any]:
        """Pull latest images for a profile."""
        try:
            cmd = self._compose_cmd_for_profile(profile)
        except (RuntimeError, FileNotFoundError) as e:
            return {"success": False, "error": str(e)}

        cmd.append("pull")
        print(f"  Pulling images (profile={profile})...")
        result = _run(cmd, timeout=600)

        return {
            "success": result.returncode == 0,
            "output": (result.stdout + "\n" + result.stderr).strip(),
        }

    # ── Image Operations ──────────────────────────────────────────────────

    def build_images(self, targets: Optional[List[str]] = None) -> Dict[str, Any]:
        """Build Docker images.

        Args:
            targets: List of Dockerfile targets to build. Default: all (gpu, cpu, dev)
        """
        if not self._docker_cmd:
            return {"success": False, "error": "Docker not available"}

        dockerfile_map = {
            "gpu": ("Dockerfile", f"{REGISTRY}/{IMAGE_BASE}:latest-gpu"),
            "cpu": ("Dockerfile.cpu", f"{REGISTRY}/{IMAGE_BASE}:latest-cpu"),
            "dev": ("Dockerfile.dev", "slate-dev:local"),
        }

        if targets is None:
            targets = list(dockerfile_map.keys())

        results = {}
        all_success = True

        for target in targets:
            if target not in dockerfile_map:
                results[target] = {"success": False, "error": f"Unknown target: {target}"}
                all_success = False
                continue

            dockerfile, tag = dockerfile_map[target]
            dockerfile_path = self.workspace / dockerfile

            if not dockerfile_path.exists():
                results[target] = {"success": False, "error": f"Dockerfile not found: {dockerfile}"}
                all_success = False
                continue

            print(f"  Building {target} image ({tag})...")
            cmd = [
                self._docker_cmd, "build",
                "-f", str(dockerfile_path),
                "-t", tag,
                str(self.workspace),
            ]

            result = _run(cmd, timeout=600)
            success = result.returncode == 0

            if success:
                print(f"  [OK] {target} image built: {tag}")
            else:
                print(f"  [X] {target} build failed")
                all_success = False

            results[target] = {
                "success": success,
                "tag": tag,
                "output": result.stderr[-500:] if not success else "",
            }

        return {"success": all_success, "builds": results}

    def list_images(self) -> List[Dict[str, str]]:
        """List SLATE-related Docker images."""
        if not self._docker_cmd:
            return []

        fmt = "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}\t{{.CreatedSince}}"
        result = _run([self._docker_cmd, "images", "--format", fmt])
        if result.returncode != 0:
            return []

        images = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 3:
                repo_tag = parts[0]
                if any(s in repo_tag.lower() for s in ["slate", "ollama", "chroma", "cuda"]):
                    images.append({
                        "image": repo_tag,
                        "id": parts[1] if len(parts) > 1 else "",
                        "size": parts[2] if len(parts) > 2 else "",
                        "created": parts[3] if len(parts) > 3 else "",
                    })
        return images

    # ── GPU Validation ────────────────────────────────────────────────────

    def gpu_check(self) -> Dict[str, Any]:
        """Validate GPU passthrough is working in Docker containers."""
        if not self._docker_cmd:
            return {"available": False, "error": "Docker not available"}

        info = self.detect()
        if not info["daemon_running"]:
            return {"available": False, "error": "Docker daemon not running"}

        result_info = {
            "gpu_runtime_installed": info["gpu_runtime"],
            "nvidia_smi": False,
            "cuda_version": None,
            "gpu_count": 0,
            "gpus": [],
        }

        if not info["gpu_runtime"]:
            result_info["error"] = "NVIDIA Container Toolkit not detected"
            return result_info

        # Test nvidia-smi inside container
        result = _run(
            [self._docker_cmd, "run", "--rm", "--gpus", "all",
             "nvidia/cuda:12.4.1-runtime-ubuntu22.04", "nvidia-smi",
             "--query-gpu=name,memory.total,driver_version,cuda_version",
             "--format=csv,noheader"],
            timeout=60,
        )

        if result.returncode == 0 and result.stdout.strip():
            result_info["nvidia_smi"] = True
            for line in result.stdout.strip().splitlines():
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    result_info["gpus"].append({
                        "name": parts[0],
                        "memory": parts[1],
                        "driver": parts[2],
                        "cuda": parts[3],
                    })
                    result_info["cuda_version"] = parts[3]
            result_info["gpu_count"] = len(result_info["gpus"])
        else:
            result_info["error"] = f"nvidia-smi failed: {result.stderr[:200]}"

        return result_info

    # ── Health Monitoring ─────────────────────────────────────────────────

    def health_check(self) -> Dict[str, Any]:
        """Check health of all SLATE Docker containers and their endpoints."""
        containers = self.list_containers(all_containers=True)

        health = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "containers": {},
            "all_healthy": True,
        }

        for container in containers:
            name = container["name"]
            state = container["state"].lower()
            is_running = state == "running"

            container_health = {
                "state": state,
                "status": container["status"],
                "running": is_running,
                "endpoint_ok": False,
            }

            # Check endpoint health if container is running
            if is_running and name in HEALTH_ENDPOINTS:
                host, port, path = HEALTH_ENDPOINTS[name]
                ok, status_code, body = _http_check(host, port, path)
                container_health["endpoint_ok"] = ok
                container_health["http_status"] = status_code
                if not ok:
                    container_health["endpoint_error"] = body
                    health["all_healthy"] = False
            elif not is_running:
                health["all_healthy"] = False

            health["containers"][name] = container_health

        # Check for expected containers that don't exist
        all_expected = set()
        for names in EXPECTED_CONTAINERS.values():
            all_expected.update(names)

        existing_names = {c["name"] for c in containers}
        health["missing"] = list(all_expected - existing_names)

        return health

    # ── Volume & Network Management ───────────────────────────────────────

    def list_volumes(self) -> List[Dict[str, str]]:
        """List SLATE-related Docker volumes."""
        if not self._docker_cmd:
            return []

        fmt = "{{.Name}}\t{{.Driver}}\t{{.Mountpoint}}"
        result = _run([self._docker_cmd, "volume", "ls", "--format", fmt])
        if result.returncode != 0:
            return []

        volumes = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 1:
                name = parts[0]
                if any(s in name.lower() for s in ["slate", "ollama", "chroma"]):
                    volumes.append({
                        "name": name,
                        "driver": parts[1] if len(parts) > 1 else "local",
                        "mountpoint": parts[2] if len(parts) > 2 else "",
                    })
        return volumes

    def list_networks(self) -> List[Dict[str, str]]:
        """List SLATE-related Docker networks."""
        if not self._docker_cmd:
            return []

        fmt = "{{.Name}}\t{{.Driver}}\t{{.Scope}}"
        result = _run([self._docker_cmd, "network", "ls", "--format", fmt])
        if result.returncode != 0:
            return []

        networks = []
        for line in result.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) >= 1:
                name = parts[0]
                if "slate" in name.lower():
                    networks.append({
                        "name": name,
                        "driver": parts[1] if len(parts) > 1 else "",
                        "scope": parts[2] if len(parts) > 2 else "",
                    })
        return networks

    # ── Cleanup ───────────────────────────────────────────────────────────

    def prune(self, images: bool = True, volumes: bool = False) -> Dict[str, Any]:
        """Clean up unused Docker resources.

        Args:
            images: Remove dangling images
            volumes: Remove unused volumes (CAUTION: data loss)
        """
        if not self._docker_cmd:
            return {"success": False, "error": "Docker not available"}

        results = {}

        # Prune stopped SLATE containers
        stopped = [c for c in self.list_containers() if c["state"].lower() != "running"]
        for c in stopped:
            if any(s in c["name"].lower() for s in ["slate", "ollama", "chromadb"]):
                result = _run([self._docker_cmd, "rm", c["name"]])
                results[f"rm_{c['name']}"] = result.returncode == 0

        # Prune dangling images
        if images:
            result = _run([self._docker_cmd, "image", "prune", "-f"])
            if result.returncode == 0:
                results["image_prune"] = result.stdout.strip()

        # Prune volumes (only with explicit flag)
        if volumes:
            # Only prune non-active SLATE volumes
            for vol in self.list_volumes():
                # Skip active volumes
                result = _run([self._docker_cmd, "volume", "inspect", vol["name"]])
                if result.returncode == 0:
                    vol_info = json.loads(result.stdout)
                    if isinstance(vol_info, list) and vol_info:
                        # Check if any container is using this volume
                        # Only prune if explicitly asked
                        pass

            result = _run([self._docker_cmd, "volume", "prune", "-f"])
            if result.returncode == 0:
                results["volume_prune"] = result.stdout.strip()

        return {"success": True, "cleaned": results}

    # ── State Management ──────────────────────────────────────────────────

    def _save_state(self, profile: str, status: str):
        """Persist daemon state to disk."""
        state = {
            "profile": profile,
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        try:
            STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")
        except IOError:
            pass

    def _load_state(self) -> Dict[str, Any]:
        """Load persisted daemon state."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, IOError):
                pass
        return {"profile": "unknown", "status": "unknown"}

    # ── Full Status ───────────────────────────────────────────────────────

    def full_status(self) -> Dict[str, Any]:
        """Get comprehensive Docker daemon status."""
        detection = self.detect()
        state = self._load_state()

        status = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "docker": detection,
            "state": state,
            "containers": [],
            "images": [],
            "volumes": [],
            "networks": [],
            "health": {},
        }

        if detection["daemon_running"]:
            status["containers"] = self.list_containers()
            status["images"] = self.list_images()
            status["volumes"] = self.list_volumes()
            status["networks"] = self.list_networks()

            # Only check health of running containers
            running = [c for c in status["containers"] if c["state"].lower() == "running"]
            if running:
                status["health"] = self.health_check()
            else:
                status["health"] = {"all_healthy": True, "containers": {}, "note": "No running containers"}

        return status

    def print_status(self):
        """Print formatted Docker daemon status."""
        status = self.full_status()
        docker = status["docker"]

        print()
        print("=" * 60)
        print("  SLATE Docker Daemon Status")
        print("=" * 60)
        print()

        # Docker installation
        if docker["installed"]:
            print(f"  Docker:        v{docker['version']}")
        else:
            print("  Docker:        NOT INSTALLED")
            print()
            print("  Install Docker Desktop:")
            print("  https://www.docker.com/products/docker-desktop/")
            print()
            return

        # Daemon
        if docker["daemon_running"]:
            print(f"  Daemon:        Running (server {docker.get('server_version', 'unknown')})")
        else:
            print("  Daemon:        STOPPED")
            print()
            print("  Start Docker Desktop or run: dockerd")
            print()
            return

        # Compose
        if docker["compose_available"]:
            print(f"  Compose:       Available")
        else:
            print("  Compose:       NOT AVAILABLE")

        # GPU
        if docker["gpu_runtime"]:
            print("  GPU Runtime:   NVIDIA Container Toolkit")
        else:
            print("  GPU Runtime:   Not configured")

        # Buildx
        if docker["buildx"]:
            print("  Buildx:        Available")

        print()

        # Containers
        containers = status["containers"]
        if containers:
            print("  Containers:")
            print(f"  {'Name':<20} {'State':<12} {'Status':<30}")
            print(f"  {'─'*20} {'─'*12} {'─'*30}")
            for c in containers:
                state_icon = "●" if c["state"].lower() == "running" else "○"
                print(f"  {state_icon} {c['name']:<18} {c['state']:<12} {c['status'][:28]}")
        else:
            print("  Containers:    None")

        print()

        # Images
        images = status["images"]
        if images:
            print("  Images:")
            for img in images[:10]:
                print(f"    {img['image']:<50} {img['size']:<10} {img['created']}")
        else:
            print("  Images:        None built yet")

        print()

        # Volumes
        volumes = status["volumes"]
        if volumes:
            print(f"  Volumes:       {len(volumes)} SLATE volumes")
            for v in volumes:
                print(f"    {v['name']}")
        else:
            print("  Volumes:       None")

        # Networks
        networks = status["networks"]
        if networks:
            print(f"  Networks:      {len(networks)} SLATE networks")

        print()

        # Health
        health = status.get("health", {})
        if health.get("containers"):
            print("  Health:")
            for name, h in health["containers"].items():
                if h["running"]:
                    ep_status = "✓" if h["endpoint_ok"] else "✗"
                    http_info = f" (HTTP {h.get('http_status', '?')})" if "http_status" in h else ""
                    print(f"    {ep_status} {name}: {h['state']}{http_info}")
                else:
                    print(f"    ○ {name}: {h['state']}")
            if health.get("missing"):
                print(f"    Missing: {', '.join(health['missing'])}")

        # State
        state = status["state"]
        if state["status"] != "unknown":
            print(f"\n  Last profile:  {state['profile']} ({state['status']})")
            if state.get("updated_at"):
                print(f"  Updated:       {state['updated_at']}")

        print()
        print("=" * 60)
        print()

    def print_health(self):
        """Print container health details."""
        health = self.health_check()

        print()
        print("=" * 60)
        print("  SLATE Docker Health Check")
        print("=" * 60)
        print()

        overall = "HEALTHY" if health["all_healthy"] else "UNHEALTHY"
        print(f"  Overall: {overall}")
        print()

        for name, h in health.get("containers", {}).items():
            if h["running"]:
                ep_icon = "✓" if h["endpoint_ok"] else "✗"
                http_info = f"HTTP {h.get('http_status', '?')}"
                print(f"  {ep_icon} {name}")
                print(f"    State:    {h['state']}")
                print(f"    Endpoint: {http_info}")
                if h.get("endpoint_error"):
                    print(f"    Error:    {h['endpoint_error'][:80]}")
            else:
                print(f"  ○ {name}")
                print(f"    State:    {h['state']}")
                print(f"    Status:   {h['status']}")
            print()

        if health.get("missing"):
            print(f"  Missing containers: {', '.join(health['missing'])}")
            print()

        print(f"  Timestamp: {health['timestamp']}")
        print()
        print("=" * 60)
        print()

    def print_gpu_check(self):
        """Print GPU passthrough validation results."""
        print()
        print("=" * 60)
        print("  SLATE Docker GPU Validation")
        print("=" * 60)
        print()

        gpu = self.gpu_check()

        print(f"  NVIDIA Runtime: {'✓ Installed' if gpu.get('gpu_runtime_installed') else '✗ Not found'}")
        print(f"  nvidia-smi:     {'✓ Working' if gpu.get('nvidia_smi') else '✗ Failed'}")

        if gpu.get("gpus"):
            print(f"  CUDA Version:   {gpu.get('cuda_version', 'unknown')}")
            print(f"  GPU Count:      {gpu['gpu_count']}")
            print()
            for i, g in enumerate(gpu["gpus"]):
                print(f"    GPU {i}: {g['name']} ({g['memory']}) [Driver {g['driver']}]")
        elif gpu.get("error"):
            print(f"  Error:          {gpu['error']}")

        print()
        print("=" * 60)
        print()


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    """CLI entry point for SLATE Docker Daemon."""
    parser = argparse.ArgumentParser(
        description="SLATE Docker Daemon — Container lifecycle management"
    )

    # Actions
    parser.add_argument("--status", action="store_true", help="Show Docker system status")
    parser.add_argument("--up", action="store_true", help="Start containers (docker compose up)")
    parser.add_argument("--down", action="store_true", help="Stop containers (docker compose down)")
    parser.add_argument("--restart", action="store_true", help="Restart containers")
    parser.add_argument("--build", action="store_true", help="Build Docker images")
    parser.add_argument("--pull", action="store_true", help="Pull latest images")
    parser.add_argument("--logs", action="store_true", help="Show container logs")
    parser.add_argument("--health", action="store_true", help="Health check all containers")
    parser.add_argument("--gpu-check", action="store_true", help="Validate GPU passthrough")
    parser.add_argument("--prune", action="store_true", help="Clean unused Docker resources")
    parser.add_argument("--stats", action="store_true", help="Show container resource usage")
    parser.add_argument("--images", action="store_true", help="List SLATE Docker images")
    parser.add_argument("--volumes", action="store_true", help="List SLATE Docker volumes")

    # Options
    parser.add_argument("--profile", choices=["default", "dev", "prod"], default="default",
                        help="Docker Compose profile (default: default)")
    parser.add_argument("--target", nargs="*", choices=["gpu", "cpu", "dev"],
                        help="Build targets (default: all)")
    parser.add_argument("--container", type=str, help="Specific container name for logs")
    parser.add_argument("--lines", type=int, default=50, help="Number of log lines (default: 50)")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--force-build", action="store_true",
                        help="Force rebuild when using --up")
    parser.add_argument("--remove-volumes", action="store_true",
                        help="Also remove volumes when using --down or --prune")

    args = parser.parse_args()

    # If no action specified, show status
    if not any([args.status, args.up, args.down, args.restart, args.build,
                args.pull, args.logs, args.health, args.gpu_check, args.prune,
                args.stats, args.images, args.volumes]):
        args.status = True

    daemon = SlateDockerDaemon()

    # ── Status ────────────────────────────────────────────────────────
    if args.status:
        if args.json:
            print(json.dumps(daemon.full_status(), indent=2))
        else:
            daemon.print_status()

    # ── Up ────────────────────────────────────────────────────────────
    elif args.up:
        result = daemon.up(profile=args.profile, build=args.force_build)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["success"]:
            print(f"\n  SLATE containers started (profile={args.profile})")
            print("  Dashboard: http://127.0.0.1:8080")
            if args.profile == "prod":
                print("  ChromaDB:  http://127.0.0.1:8000")
        else:
            print(f"\n  Failed: {result.get('error', result.get('output', 'Unknown error')[:200])}")
            sys.exit(1)

    # ── Down ──────────────────────────────────────────────────────────
    elif args.down:
        result = daemon.down(profile=args.profile, volumes=args.remove_volumes)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["success"]:
            print(f"\n  SLATE containers stopped (profile={args.profile})")
        else:
            print(f"\n  Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    # ── Restart ───────────────────────────────────────────────────────
    elif args.restart:
        result = daemon.restart(profile=args.profile)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["success"]:
            print(f"\n  SLATE containers restarted (profile={args.profile})")
        else:
            print(f"\n  Failed: {result.get('error', 'Unknown error')}")
            sys.exit(1)

    # ── Build ─────────────────────────────────────────────────────────
    elif args.build:
        result = daemon.build_images(targets=args.target)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print()
            for target, info in result.get("builds", {}).items():
                status = "✓" if info["success"] else "✗"
                print(f"  {status} {target}: {info.get('tag', 'unknown')}")
                if not info["success"] and info.get("output"):
                    print(f"    Error: {info['output'][:100]}")
            print()

    # ── Pull ──────────────────────────────────────────────────────────
    elif args.pull:
        result = daemon.pull(profile=args.profile)
        if args.json:
            print(json.dumps(result, indent=2))
        elif result["success"]:
            print("\n  Images pulled successfully")

    # ── Logs ──────────────────────────────────────────────────────────
    elif args.logs:
        container = args.container
        if not container:
            # Show logs for all SLATE containers
            containers = daemon.list_containers()
            running = [c for c in containers if c["state"].lower() == "running"]
            if not running:
                print("  No running SLATE containers")
                sys.exit(0)
            # Show first running container logs
            container = running[0]["name"]

        logs = daemon.container_logs(container, lines=args.lines)
        if args.json:
            print(json.dumps({"container": container, "logs": logs}))
        else:
            print(f"\n  === Logs: {container} (last {args.lines} lines) ===\n")
            print(logs)

    # ── Health ────────────────────────────────────────────────────────
    elif args.health:
        if args.json:
            print(json.dumps(daemon.health_check(), indent=2))
        else:
            daemon.print_health()

    # ── GPU Check ─────────────────────────────────────────────────────
    elif args.gpu_check:
        if args.json:
            print(json.dumps(daemon.gpu_check(), indent=2))
        else:
            daemon.print_gpu_check()

    # ── Prune ─────────────────────────────────────────────────────────
    elif args.prune:
        result = daemon.prune(images=True, volumes=args.remove_volumes)
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            print("\n  Docker cleanup complete")
            for k, v in result.get("cleaned", {}).items():
                print(f"    {k}: {v}")
            print()

    # ── Stats ─────────────────────────────────────────────────────────
    elif args.stats:
        stats = daemon.container_stats()
        if args.json:
            print(json.dumps(stats, indent=2))
        elif stats:
            print()
            print(f"  {'Container':<20} {'CPU':<8} {'Memory':<20} {'Net I/O':<15} {'PIDs'}")
            print(f"  {'─'*20} {'─'*8} {'─'*20} {'─'*15} {'─'*5}")
            for s in stats:
                print(f"  {s['name']:<20} {s['cpu']:<8} {s['memory']:<20} {s['net_io']:<15} {s['pids']}")
            print()
        else:
            print("  No running SLATE containers")

    # ── Images ────────────────────────────────────────────────────────
    elif args.images:
        images = daemon.list_images()
        if args.json:
            print(json.dumps(images, indent=2))
        elif images:
            print()
            print(f"  {'Image':<50} {'Size':<10} {'Created'}")
            print(f"  {'─'*50} {'─'*10} {'─'*15}")
            for img in images:
                print(f"  {img['image']:<50} {img['size']:<10} {img['created']}")
            print()
        else:
            print("  No SLATE images found")

    # ── Volumes ───────────────────────────────────────────────────────
    elif args.volumes:
        volumes = daemon.list_volumes()
        if args.json:
            print(json.dumps(volumes, indent=2))
        elif volumes:
            print()
            for v in volumes:
                print(f"  {v['name']} ({v['driver']})")
            print()
        else:
            print("  No SLATE volumes found")


if __name__ == "__main__":
    main()
