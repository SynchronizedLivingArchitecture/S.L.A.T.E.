#!/usr/bin/env python3
# Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Create dependency scanner for SLATE installation ethos
"""
SLATE Dependency Scanner
========================
Implements the SLATE installation ethos:
    1. SCAN: Detect if dependencies exist outside the environment (other folders/drives)
    2. LINK: If a dependency exists elsewhere, create a symlink/junction to reuse it
    3. INSTALL: Only install directly to workspace if not found anywhere

This prevents redundant downloads and leverages existing system installations.

Usage:
    python slate/slate_dependency_scanner.py --scan               # Full system scan
    python slate/slate_dependency_scanner.py --scan-pytorch       # Scan for PyTorch
    python slate/slate_dependency_scanner.py --scan-cuda          # Scan for CUDA
    python slate/slate_dependency_scanner.py --scan-ollama        # Scan for Ollama
    python slate/slate_dependency_scanner.py --link-all           # Create links for all found deps
    python slate/slate_dependency_scanner.py --report             # Generate dependency report
    python slate/slate_dependency_scanner.py --json               # JSON output

Architecture:
    DependencyScanner → scans drives/folders → DependencyResult
                      → creates symlinks/junctions → links to workspace
                      → reports what needs fresh install

Security:
    - All operations are local-only
    - No external network calls in scanning phase
    - Symlinks require appropriate permissions
"""

import argparse
import json
import os
import platform
import shutil
import subprocess
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Any

WORKSPACE_ROOT = Path(__file__).parent.parent

# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class DependencyLocation:
    """Represents a found dependency location."""
    path: Path
    version: Optional[str] = None
    is_valid: bool = True
    size_mb: float = 0.0
    drive: str = ""
    link_target: Optional[Path] = None  # Where to link in workspace
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["path"] = str(self.path)
        d["link_target"] = str(self.link_target) if self.link_target else None
        return d


@dataclass
class DependencyResult:
    """Result of scanning for a specific dependency."""
    name: str
    dep_type: str  # python, pytorch, cuda, ollama, chromadb, venv, etc.
    found: bool = False
    locations: List[DependencyLocation] = field(default_factory=list)
    best_location: Optional[DependencyLocation] = None
    action: str = "install"  # link, skip, install
    error: Optional[str] = None
    scanned_at: str = ""

    def to_dict(self) -> dict:
        d = asdict(self)
        d["locations"] = [loc.to_dict() if isinstance(loc, DependencyLocation) else loc for loc in self.locations]
        d["best_location"] = self.best_location.to_dict() if self.best_location else None
        return d


@dataclass
class ScanReport:
    """Complete scan report for all dependencies."""
    scan_time: str
    workspace: str
    platform: str
    drives_scanned: List[str] = field(default_factory=list)
    results: Dict[str, DependencyResult] = field(default_factory=dict)
    links_created: List[Dict] = field(default_factory=list)
    needs_install: List[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["results"] = {k: v.to_dict() if isinstance(v, DependencyResult) else v
                       for k, v in self.results.items()}
        return d


# ═══════════════════════════════════════════════════════════════════════════════
# Dependency Scanner
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyScanner:
    """
    Scans the system for existing dependencies to reuse.

    SLATE Installation Ethos:
        1. Detect what already exists on the system
        2. Link to existing dependencies instead of downloading
        3. Only install fresh when absolutely necessary
    """

    # Common locations to scan for Python environments
    PYTHON_SEARCH_PATHS = [
        # Windows standard locations
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Python",
        Path(os.environ.get("PROGRAMFILES", "")) / "Python",
        Path(os.environ.get("PROGRAMFILES(X86)", "")) / "Python",
        Path.home() / "AppData" / "Local" / "Programs" / "Python",
        Path.home() / ".pyenv",
        Path.home() / "miniconda3",
        Path.home() / "anaconda3",
        # Linux/Mac locations
        Path("/usr/local/bin"),
        Path("/opt/homebrew/bin"),
        Path.home() / ".local" / "bin",
    ]

    # Common locations for virtual environments
    VENV_SEARCH_PATHS = [
        Path.home() / ".virtualenvs",
        Path.home() / "envs",
        Path.home() / "venvs",
        Path.home() / ".local" / "share" / "virtualenvs",
    ]

    # Common locations for PyTorch/CUDA
    PYTORCH_CACHE_PATHS = [
        Path.home() / ".cache" / "torch",
        Path.home() / ".cache" / "huggingface",
        Path(os.environ.get("TORCH_HOME", "")) if os.environ.get("TORCH_HOME") else None,
    ]

    # CUDA installation locations
    CUDA_PATHS = [
        Path("C:/Program Files/NVIDIA GPU Computing Toolkit/CUDA"),
        Path("C:/CUDA"),
        Path("/usr/local/cuda"),
        Path("/opt/cuda"),
    ]

    # Ollama locations
    OLLAMA_PATHS = [
        Path.home() / ".ollama",
        Path(os.environ.get("OLLAMA_MODELS", "")) if os.environ.get("OLLAMA_MODELS") else None,
        Path("C:/Users") / os.environ.get("USERNAME", "") / ".ollama" if os.name == "nt" else None,
    ]

    # ChromaDB locations
    CHROMADB_PATHS = [
        Path.home() / ".chroma",
        Path.home() / ".cache" / "chroma",
    ]

    def __init__(self, workspace: Path = None, verbose: bool = False):
        self.workspace = workspace or WORKSPACE_ROOT
        self.verbose = verbose
        self.report = ScanReport(
            scan_time=datetime.now().isoformat(),
            workspace=str(self.workspace),
            platform=platform.system(),
        )

    def _log(self, msg: str, level: str = "INFO"):
        """Log a message if verbose mode is enabled."""
        if self.verbose:
            icon = {"INFO": "i", "OK": "+", "WARN": "!", "ERROR": "x", "SCAN": ">"}.get(level, ".")
            print(f"  [{icon}] {msg}")

    def _get_drives(self) -> List[str]:
        """Get all available drives on the system."""
        drives = []
        if os.name == "nt":
            # Windows: check all possible drive letters
            for letter in "CDEFGHIJKLMNOPQRSTUVWXYZ":
                drive = f"{letter}:\\"
                if Path(drive).exists():
                    drives.append(drive)
        else:
            # Unix: root and common mount points
            drives = ["/"]
            for mount in ["/mnt", "/media", "/home"]:
                if Path(mount).exists():
                    drives.append(mount)
        self.report.drives_scanned = drives
        return drives

    def _get_folder_size_mb(self, path: Path) -> float:
        """Get folder size in MB."""
        try:
            total = 0
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
            return round(total / (1024 * 1024), 2)
        except Exception:
            return 0.0

    def _run_cmd(self, cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
        """Run a command with timeout."""
        try:
            return subprocess.run(
                cmd, capture_output=True, text=True, timeout=timeout,
                cwd=str(self.workspace)
            )
        except Exception as e:
            return subprocess.CompletedProcess(cmd, 1, "", str(e))

    # ═══════════════════════════════════════════════════════════════════════════
    # Python/Venv Scanning
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_python_installations(self) -> DependencyResult:
        """Scan for existing Python installations."""
        self._log("Scanning for Python installations...", "SCAN")
        result = DependencyResult(name="python", dep_type="runtime", scanned_at=datetime.now().isoformat())

        locations = []

        # Check current Python
        current_py = Path(sys.executable)
        if current_py.exists():
            version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
            loc = DependencyLocation(
                path=current_py,
                version=version,
                is_valid=sys.version_info >= (3, 11),
                drive=str(current_py.drive) if hasattr(current_py, 'drive') else "/",
                metadata={"current": True, "meets_requirement": sys.version_info >= (3, 11)}
            )
            locations.append(loc)
            self._log(f"Current Python: {version} at {current_py}", "OK")

        # Scan known locations
        for search_path in self.PYTHON_SEARCH_PATHS:
            if search_path and search_path.exists():
                self._log(f"Checking {search_path}", "SCAN")
                try:
                    for item in search_path.iterdir():
                        if item.is_dir():
                            # Look for python executable
                            if os.name == "nt":
                                py_exe = item / "python.exe"
                            else:
                                py_exe = item / "bin" / "python"

                            if py_exe.exists():
                                # Get version
                                ver_result = self._run_cmd([str(py_exe), "--version"], timeout=10)
                                version = ver_result.stdout.strip().replace("Python ", "") if ver_result.returncode == 0 else "unknown"

                                try:
                                    major, minor = map(int, version.split(".")[:2])
                                    is_valid = major >= 3 and minor >= 11
                                except (ValueError, IndexError):
                                    is_valid = False

                                loc = DependencyLocation(
                                    path=py_exe,
                                    version=version,
                                    is_valid=is_valid,
                                    drive=str(item.drive) if hasattr(item, 'drive') else "/",
                                    metadata={"meets_requirement": is_valid}
                                )
                                locations.append(loc)
                                self._log(f"Found Python {version} at {py_exe} (valid={is_valid})", "OK" if is_valid else "WARN")
                except PermissionError:
                    pass

        result.locations = locations
        result.found = len(locations) > 0

        # Select best location (prefer 3.11+, then current)
        valid_locs = [l for l in locations if l.is_valid]
        if valid_locs:
            result.best_location = valid_locs[0]
            result.action = "link"
        else:
            result.action = "install"

        return result

    def scan_virtual_environments(self) -> DependencyResult:
        """Scan for existing virtual environments with SLATE-compatible packages."""
        self._log("Scanning for virtual environments...", "SCAN")
        result = DependencyResult(name="venv", dep_type="environment", scanned_at=datetime.now().isoformat())

        locations = []

        # Check workspace venv first
        workspace_venv = self.workspace / ".venv"
        if workspace_venv.exists():
            py_exe = workspace_venv / ("Scripts" if os.name == "nt" else "bin") / ("python.exe" if os.name == "nt" else "python")
            if py_exe.exists():
                loc = DependencyLocation(
                    path=workspace_venv,
                    is_valid=True,
                    drive=str(workspace_venv.drive) if hasattr(workspace_venv, 'drive') else "/",
                    size_mb=self._get_folder_size_mb(workspace_venv),
                    metadata={"is_workspace_venv": True}
                )
                locations.append(loc)
                self._log(f"Workspace venv exists: {workspace_venv}", "OK")

        # Scan for other venvs with compatible packages
        for search_path in self.VENV_SEARCH_PATHS:
            if search_path and search_path.exists():
                self._log(f"Checking {search_path} for venvs", "SCAN")
                try:
                    for item in search_path.iterdir():
                        if item.is_dir():
                            # Check for venv structure
                            if os.name == "nt":
                                py_exe = item / "Scripts" / "python.exe"
                                pip_exe = item / "Scripts" / "pip.exe"
                            else:
                                py_exe = item / "bin" / "python"
                                pip_exe = item / "bin" / "pip"

                            if py_exe.exists() and pip_exe.exists():
                                # Check if it has key SLATE dependencies
                                freeze_result = self._run_cmd([str(pip_exe), "list", "--format=json"], timeout=30)
                                has_fastapi = has_torch = has_chromadb = False

                                if freeze_result.returncode == 0:
                                    try:
                                        packages = json.loads(freeze_result.stdout)
                                        pkg_names = [p.get("name", "").lower() for p in packages]
                                        has_fastapi = "fastapi" in pkg_names
                                        has_torch = "torch" in pkg_names
                                        has_chromadb = "chromadb" in pkg_names
                                    except json.JSONDecodeError:
                                        pass

                                loc = DependencyLocation(
                                    path=item,
                                    is_valid=True,
                                    drive=str(item.drive) if hasattr(item, 'drive') else "/",
                                    size_mb=self._get_folder_size_mb(item),
                                    metadata={
                                        "has_fastapi": has_fastapi,
                                        "has_torch": has_torch,
                                        "has_chromadb": has_chromadb,
                                        "compatible_score": sum([has_fastapi, has_torch, has_chromadb])
                                    }
                                )
                                locations.append(loc)
                                self._log(f"Found venv at {item} (fastapi={has_fastapi}, torch={has_torch})", "OK")
                except PermissionError:
                    pass

        result.locations = locations
        result.found = len(locations) > 0

        # Select best - prefer workspace venv, then highest compatibility score
        workspace_locs = [l for l in locations if l.metadata.get("is_workspace_venv")]
        if workspace_locs:
            result.best_location = workspace_locs[0]
            result.action = "skip"  # Already in workspace
        else:
            compatible_locs = sorted(locations, key=lambda l: l.metadata.get("compatible_score", 0), reverse=True)
            if compatible_locs and compatible_locs[0].metadata.get("compatible_score", 0) >= 2:
                result.best_location = compatible_locs[0]
                result.action = "link"
            else:
                result.action = "install"

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # PyTorch Scanning
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_pytorch(self) -> DependencyResult:
        """Scan for existing PyTorch installations."""
        self._log("Scanning for PyTorch installations...", "SCAN")
        result = DependencyResult(name="pytorch", dep_type="ml_framework", scanned_at=datetime.now().isoformat())

        locations = []

        # Check if PyTorch is importable from current Python
        check_result = self._run_cmd([
            sys.executable, "-c",
            "import torch; print(torch.__version__); print(torch.cuda.is_available()); "
            "print(torch.version.cuda or 'none'); import torch; print(torch.__file__)"
        ], timeout=30)

        if check_result.returncode == 0:
            lines = check_result.stdout.strip().splitlines()
            if len(lines) >= 4:
                version = lines[0]
                cuda_available = lines[1].lower() == "true"
                cuda_version = lines[2] if lines[2] != "none" else None
                torch_path = Path(lines[3]).parent.parent  # Go up from __file__

                loc = DependencyLocation(
                    path=torch_path,
                    version=version,
                    is_valid=True,
                    drive=str(torch_path.drive) if hasattr(torch_path, 'drive') else "/",
                    size_mb=self._get_folder_size_mb(torch_path),
                    metadata={
                        "cuda_available": cuda_available,
                        "cuda_version": cuda_version,
                        "current_env": True
                    }
                )
                locations.append(loc)
                self._log(f"Found PyTorch {version} (CUDA={cuda_available}) at {torch_path}", "OK")

        # Scan torch cache directories
        for cache_path in self.PYTORCH_CACHE_PATHS:
            if cache_path and cache_path.exists():
                self._log(f"Checking PyTorch cache: {cache_path}", "SCAN")
                hub_path = cache_path / "hub"
                if hub_path.exists():
                    loc = DependencyLocation(
                        path=cache_path,
                        is_valid=True,
                        drive=str(cache_path.drive) if hasattr(cache_path, 'drive') else "/",
                        size_mb=self._get_folder_size_mb(cache_path),
                        metadata={"is_cache": True}
                    )
                    locations.append(loc)
                    self._log(f"Found PyTorch cache at {cache_path} ({loc.size_mb}MB)", "OK")

        # Scan all drives for site-packages with torch
        for drive in self._get_drives()[:3]:  # Limit to first 3 drives for speed
            search_paths = [
                Path(drive) / "Python*" / "Lib" / "site-packages" / "torch",
                Path(drive) / "Users" / "*" / "AppData" / "Local" / "Programs" / "Python" / "Python*" / "Lib" / "site-packages" / "torch",
                Path(drive) / "Program Files" / "Python*" / "Lib" / "site-packages" / "torch",
            ]
            for pattern in search_paths:
                try:
                    import glob
                    for match in glob.glob(str(pattern)):
                        match_path = Path(match)
                        if match_path.exists() and match_path not in [l.path for l in locations]:
                            version_file = match_path / "version.py"
                            version = "unknown"
                            if version_file.exists():
                                content = version_file.read_text()
                                for line in content.splitlines():
                                    if "__version__" in line:
                                        version = line.split("=")[1].strip().strip("'\"")
                                        break

                            loc = DependencyLocation(
                                path=match_path,
                                version=version,
                                is_valid=True,
                                drive=drive,
                                size_mb=self._get_folder_size_mb(match_path),
                                metadata={"found_via_scan": True}
                            )
                            locations.append(loc)
                            self._log(f"Found PyTorch at {match_path}", "OK")
                except Exception:
                    pass

        result.locations = locations
        result.found = len(locations) > 0

        # Select best - prefer CUDA-enabled, then largest cache
        cuda_locs = [l for l in locations if l.metadata.get("cuda_available")]
        if cuda_locs:
            result.best_location = cuda_locs[0]
            result.action = "link"
        elif locations:
            # Sort by size (larger = more models cached)
            sorted_locs = sorted(locations, key=lambda l: l.size_mb, reverse=True)
            result.best_location = sorted_locs[0]
            result.action = "link"
        else:
            result.action = "install"

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # CUDA Scanning
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_cuda(self) -> DependencyResult:
        """Scan for CUDA installations."""
        self._log("Scanning for CUDA installations...", "SCAN")
        result = DependencyResult(name="cuda", dep_type="gpu_toolkit", scanned_at=datetime.now().isoformat())

        locations = []

        # Check nvidia-smi
        nvidia_result = self._run_cmd(["nvidia-smi", "--query-gpu=driver_version", "--format=csv,noheader"], timeout=15)
        if nvidia_result.returncode == 0:
            driver_version = nvidia_result.stdout.strip().splitlines()[0] if nvidia_result.stdout else "unknown"
            self._log(f"NVIDIA driver: {driver_version}", "OK")

        # Check nvcc
        nvcc_result = self._run_cmd(["nvcc", "--version"], timeout=10)
        if nvcc_result.returncode == 0:
            for line in nvcc_result.stdout.splitlines():
                if "release" in line.lower():
                    cuda_version = line.split("release")[1].strip().split(",")[0].strip()

                    # Find nvcc path
                    nvcc_path = shutil.which("nvcc")
                    if nvcc_path:
                        cuda_root = Path(nvcc_path).parent.parent
                        loc = DependencyLocation(
                            path=cuda_root,
                            version=cuda_version,
                            is_valid=True,
                            drive=str(cuda_root.drive) if hasattr(cuda_root, 'drive') else "/",
                            size_mb=self._get_folder_size_mb(cuda_root),
                            metadata={"has_nvcc": True}
                        )
                        locations.append(loc)
                        self._log(f"Found CUDA {cuda_version} at {cuda_root}", "OK")
                    break

        # Scan known CUDA paths
        for cuda_path in self.CUDA_PATHS:
            if cuda_path and cuda_path.exists():
                self._log(f"Checking {cuda_path}", "SCAN")
                try:
                    for item in cuda_path.iterdir():
                        if item.is_dir() and item.name.startswith("v"):
                            version = item.name.lstrip("v")
                            loc = DependencyLocation(
                                path=item,
                                version=version,
                                is_valid=True,
                                drive=str(item.drive) if hasattr(item, 'drive') else "/",
                                size_mb=self._get_folder_size_mb(item),
                                metadata={"installation_type": "standalone"}
                            )
                            locations.append(loc)
                            self._log(f"Found CUDA {version} at {item}", "OK")
                except PermissionError:
                    pass

        result.locations = locations
        result.found = len(locations) > 0

        if locations:
            # Prefer newest version
            sorted_locs = sorted(locations, key=lambda l: l.version or "0", reverse=True)
            result.best_location = sorted_locs[0]
            result.action = "link"
        else:
            result.action = "skip"  # CUDA needs hardware, can't just install

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Ollama Scanning
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_ollama(self) -> DependencyResult:
        """Scan for Ollama installations and models."""
        self._log("Scanning for Ollama installations...", "SCAN")
        result = DependencyResult(name="ollama", dep_type="llm_runtime", scanned_at=datetime.now().isoformat())

        locations = []

        # Check if ollama is in PATH
        ollama_result = self._run_cmd(["ollama", "--version"], timeout=10)
        if ollama_result.returncode == 0:
            version = ollama_result.stdout.strip()
            ollama_exe = shutil.which("ollama")

            if ollama_exe:
                loc = DependencyLocation(
                    path=Path(ollama_exe),
                    version=version,
                    is_valid=True,
                    drive=str(Path(ollama_exe).drive) if hasattr(Path(ollama_exe), 'drive') else "/",
                    metadata={"in_path": True}
                )
                locations.append(loc)
                self._log(f"Found Ollama {version} in PATH", "OK")

        # Check for model storage
        for ollama_path in self.OLLAMA_PATHS:
            if ollama_path and ollama_path.exists():
                models_dir = ollama_path / "models"
                if models_dir.exists():
                    # List models
                    try:
                        manifests = list((models_dir / "manifests").rglob("*"))
                        model_count = len([m for m in manifests if m.is_file()])
                    except Exception:
                        model_count = 0

                    loc = DependencyLocation(
                        path=ollama_path,
                        is_valid=True,
                        drive=str(ollama_path.drive) if hasattr(ollama_path, 'drive') else "/",
                        size_mb=self._get_folder_size_mb(ollama_path),
                        metadata={
                            "is_model_storage": True,
                            "model_count": model_count
                        }
                    )
                    locations.append(loc)
                    self._log(f"Found Ollama models at {ollama_path} ({model_count} models, {loc.size_mb}MB)", "OK")

        result.locations = locations
        result.found = len(locations) > 0

        if locations:
            # Prefer the one with most models
            sorted_locs = sorted(locations, key=lambda l: l.metadata.get("model_count", 0), reverse=True)
            result.best_location = sorted_locs[0]
            result.action = "link"
        else:
            result.action = "install"

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # ChromaDB Scanning
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_chromadb(self) -> DependencyResult:
        """Scan for ChromaDB data and installations."""
        self._log("Scanning for ChromaDB installations...", "SCAN")
        result = DependencyResult(name="chromadb", dep_type="vector_store", scanned_at=datetime.now().isoformat())

        locations = []

        # Check if chromadb is importable
        check_result = self._run_cmd([
            sys.executable, "-c",
            "import chromadb; print(chromadb.__version__); import chromadb; print(chromadb.__file__)"
        ], timeout=15)

        if check_result.returncode == 0:
            lines = check_result.stdout.strip().splitlines()
            if len(lines) >= 2:
                version = lines[0]
                chroma_path = Path(lines[1]).parent.parent

                loc = DependencyLocation(
                    path=chroma_path,
                    version=version,
                    is_valid=True,
                    drive=str(chroma_path.drive) if hasattr(chroma_path, 'drive') else "/",
                    metadata={"current_env": True}
                )
                locations.append(loc)
                self._log(f"Found ChromaDB {version} at {chroma_path}", "OK")

        # Scan for existing ChromaDB data directories
        for chroma_path in self.CHROMADB_PATHS:
            if chroma_path and chroma_path.exists():
                # Look for chroma.sqlite3 or collection directories
                has_data = any(chroma_path.glob("*.sqlite3")) or any(chroma_path.glob("**/chroma.sqlite3"))

                if has_data:
                    loc = DependencyLocation(
                        path=chroma_path,
                        is_valid=True,
                        drive=str(chroma_path.drive) if hasattr(chroma_path, 'drive') else "/",
                        size_mb=self._get_folder_size_mb(chroma_path),
                        metadata={"has_data": True}
                    )
                    locations.append(loc)
                    self._log(f"Found ChromaDB data at {chroma_path} ({loc.size_mb}MB)", "OK")

        # Check workspace .slate_index
        slate_index = self.workspace / ".slate_index"
        if slate_index.exists():
            loc = DependencyLocation(
                path=slate_index,
                is_valid=True,
                drive=str(slate_index.drive) if hasattr(slate_index, 'drive') else "/",
                size_mb=self._get_folder_size_mb(slate_index),
                metadata={"is_workspace_index": True}
            )
            locations.append(loc)
            self._log(f"Found SLATE index at {slate_index}", "OK")

        result.locations = locations
        result.found = len(locations) > 0

        if locations:
            result.best_location = locations[0]
            result.action = "link" if not locations[0].metadata.get("is_workspace_index") else "skip"
        else:
            result.action = "install"

        return result

    # ═══════════════════════════════════════════════════════════════════════════
    # Full Scan
    # ═══════════════════════════════════════════════════════════════════════════

    def scan_all(self) -> ScanReport:
        """Perform a full system scan for all dependencies."""
        self._log("Starting full dependency scan...", "SCAN")

        # Get available drives
        drives = self._get_drives()
        self._log(f"Drives to scan: {drives}", "INFO")

        # Scan each dependency type
        self.report.results["python"] = self.scan_python_installations()
        self.report.results["venv"] = self.scan_virtual_environments()
        self.report.results["pytorch"] = self.scan_pytorch()
        self.report.results["cuda"] = self.scan_cuda()
        self.report.results["ollama"] = self.scan_ollama()
        self.report.results["chromadb"] = self.scan_chromadb()

        # Determine what needs installation
        for name, dep_result in self.report.results.items():
            if dep_result.action == "install":
                self.report.needs_install.append(name)

        return self.report

    # ═══════════════════════════════════════════════════════════════════════════
    # Link Creation
    # ═══════════════════════════════════════════════════════════════════════════

    def create_link(self, source: Path, target: Path, is_directory: bool = True) -> bool:
        """
        Create a symlink or junction to reuse an existing dependency.

        Args:
            source: The existing dependency path
            target: Where to create the link in workspace

        Returns:
            True if link created successfully
        """
        self._log(f"Creating link: {target} -> {source}", "INFO")

        try:
            # Remove existing target if it exists
            if target.exists():
                if target.is_symlink():
                    target.unlink()
                elif target.is_dir():
                    # Don't remove real directories, only links
                    self._log(f"Target exists and is not a link: {target}", "WARN")
                    return False

            # Create parent directories
            target.parent.mkdir(parents=True, exist_ok=True)

            if os.name == "nt":
                # Windows: use junction for directories (no admin required), symlink for files
                if is_directory:
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(target), str(source)],
                        capture_output=True, text=True, timeout=10
                    )
                    success = result.returncode == 0
                else:
                    target.symlink_to(source)
                    success = True
            else:
                # Unix: use symlinks
                target.symlink_to(source)
                success = True

            if success:
                self._log(f"Link created: {target}", "OK")
                self.report.links_created.append({
                    "source": str(source),
                    "target": str(target),
                    "created_at": datetime.now().isoformat()
                })
            return success

        except Exception as e:
            self._log(f"Failed to create link: {e}", "ERROR")
            return False

    def create_all_links(self) -> int:
        """Create links for all dependencies that have 'link' action."""
        links_created = 0

        for name, dep_result in self.report.results.items():
            if dep_result.action == "link" and dep_result.best_location:
                source = dep_result.best_location.path

                # Determine target path based on dependency type
                if name == "pytorch":
                    # Link torch cache
                    target = self.workspace / ".cache" / "torch"
                    if self.create_link(source, target):
                        links_created += 1

                elif name == "ollama":
                    # Link ollama models
                    if dep_result.best_location.metadata.get("is_model_storage"):
                        target = Path.home() / ".ollama"
                        if not target.exists():
                            if self.create_link(source, target):
                                links_created += 1

                elif name == "chromadb":
                    # Link chroma data
                    if dep_result.best_location.metadata.get("has_data"):
                        target = self.workspace / ".slate_index"
                        if not target.exists():
                            if self.create_link(source, target):
                                links_created += 1

        return links_created

    # ═══════════════════════════════════════════════════════════════════════════
    # Reporting
    # ═══════════════════════════════════════════════════════════════════════════

    def print_report(self):
        """Print a human-readable scan report."""
        print()
        print("=" * 70)
        print("  SLATE Dependency Scanner Report")
        print("=" * 70)
        print()
        print(f"  Workspace: {self.workspace}")
        print(f"  Platform:  {platform.system()}")
        print(f"  Drives:    {', '.join(self.report.drives_scanned)}")
        print()

        for name, result in self.report.results.items():
            icon = "+" if result.found else "x"
            action_icon = {"link": "->", "skip": "=", "install": "!"}.get(result.action, "?")
            print(f"  [{icon}] {name.upper()}")
            print(f"      Found: {result.found} | Action: {result.action} {action_icon}")

            if result.locations:
                print(f"      Locations ({len(result.locations)}):")
                for loc in result.locations[:3]:  # Show first 3
                    valid_str = "valid" if loc.is_valid else "invalid"
                    version_str = f"v{loc.version}" if loc.version else ""
                    size_str = f"({loc.size_mb}MB)" if loc.size_mb else ""
                    print(f"        - {loc.path} {version_str} {size_str} [{valid_str}]")

            if result.best_location:
                print(f"      Best: {result.best_location.path}")
            print()

        if self.report.needs_install:
            print(f"  Needs fresh install: {', '.join(self.report.needs_install)}")
        else:
            print("  All dependencies found - no fresh install needed!")

        if self.report.links_created:
            print(f"  Links created: {len(self.report.links_created)}")

        print()
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(
        description="SLATE Dependency Scanner - Scan, Link, Install",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
SLATE Installation Ethos:
    1. SCAN:    Detect existing dependencies on system
    2. LINK:    Create symlinks to reuse what exists
    3. INSTALL: Only install fresh when not found

Examples:
    %(prog)s --scan                 Full system scan
    %(prog)s --scan-pytorch         Scan for PyTorch only
    %(prog)s --link-all             Create links for all found deps
    %(prog)s --report               Generate detailed report
    %(prog)s --json                 JSON output
""",
    )
    parser.add_argument("--scan", action="store_true", help="Full system scan")
    parser.add_argument("--scan-python", action="store_true", help="Scan for Python")
    parser.add_argument("--scan-pytorch", action="store_true", help="Scan for PyTorch")
    parser.add_argument("--scan-cuda", action="store_true", help="Scan for CUDA")
    parser.add_argument("--scan-ollama", action="store_true", help="Scan for Ollama")
    parser.add_argument("--scan-chromadb", action="store_true", help="Scan for ChromaDB")
    parser.add_argument("--link-all", action="store_true", help="Create links for found deps")
    parser.add_argument("--report", action="store_true", help="Generate detailed report")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")

    args = parser.parse_args()

    scanner = DependencyScanner(verbose=args.verbose or not args.json)

    if args.scan_python:
        result = scanner.scan_python_installations()
        scanner.report.results["python"] = result
    elif args.scan_pytorch:
        result = scanner.scan_pytorch()
        scanner.report.results["pytorch"] = result
    elif args.scan_cuda:
        result = scanner.scan_cuda()
        scanner.report.results["cuda"] = result
    elif args.scan_ollama:
        result = scanner.scan_ollama()
        scanner.report.results["ollama"] = result
    elif args.scan_chromadb:
        result = scanner.scan_chromadb()
        scanner.report.results["chromadb"] = result
    else:
        # Default: full scan
        scanner.scan_all()

    if args.link_all:
        links = scanner.create_all_links()
        if not args.json:
            print(f"  Created {links} links")

    if args.json:
        print(json.dumps(scanner.report.to_dict(), indent=2, default=str))
    elif args.report or args.scan:
        scanner.print_report()

    # Return exit code based on whether install is needed
    return 0 if not scanner.report.needs_install else 1


if __name__ == "__main__":
    sys.exit(main())
