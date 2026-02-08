#!/usr/bin/env python3
# Modified: 2026-02-07T20:00:00Z | Author: COPILOT | Change: Remove hardcoded workspace path from docstring
"""
S.L.A.T.E. Dependency Resolver
================================
Scans the local system for existing Python environments, packages, and tools
BEFORE installing anything. If a dependency already exists on another drive or
folder, it creates a symlink/junction or adds it to sys.path rather than
downloading and installing a duplicate copy.

Philosophy:
    1. SCAN — find all Python venvs, site-packages dirs, and tool installations
    2. MATCH — for each required dependency, check if it's already installed anywhere
    3. LINK  — if found, symlink the package into the workspace venv's site-packages
    4. INSTALL — only if NOT found anywhere on the system, install directly to workspace

This saves disk space (PyTorch alone is ~3GB) and dramatically speeds up installs
when users have multiple SLATE or ML workspaces on the same machine.
"""

import json
import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Initial creation


# ═══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════

# Large packages worth scanning for (>10MB installed size)
HEAVY_PACKAGES = {
    "torch", "torchvision", "torchaudio",
    "transformers", "accelerate",
    "chromadb", "onnxruntime", "onnxruntime-gpu",
    "numpy", "scipy", "pandas",
    "bitsandbytes", "datasets",
    "mypy", "ruff", "black",
    "pytest", "coverage",
}

# Tools that may exist as system-level installs (not pip)
SYSTEM_TOOLS = {
    "ollama": {"check_cmd": ["ollama", "--version"], "type": "binary"},
    "docker": {"check_cmd": ["docker", "--version"], "type": "binary"},
    "git":    {"check_cmd": ["git", "--version"], "type": "binary"},
    "node":   {"check_cmd": ["node", "--version"], "type": "binary"},
    "npm":    {"check_cmd": ["npm", "--version"], "type": "binary"},
    "code":   {"check_cmd": ["code", "--version"], "type": "binary"},
}

# Modified: 2026-02-07T15:30:00Z | Author: COPILOT | Change: Add GPU compute capability detection for Blackwell sm_120 compatibility

# Minimum CUDA toolkit version needed per GPU compute capability (sm_XX)
# Mapping: compute_capability_float -> minimum CUDA toolkit version string
GPU_CC_MIN_CUDA = {
    12.0: "12.8",   # Blackwell (RTX 50xx) — requires CUDA 12.8+
    9.0:  "12.0",   # Hopper (H100) — requires CUDA 12.0+
    8.9:  "11.8",   # Ada Lovelace (RTX 40xx) — requires CUDA 11.8+
    8.6:  "11.1",   # Ampere GA10x (RTX 30xx) — CUDA 11.1+
    8.0:  "11.0",   # Ampere GA100 (A100) — CUDA 11.0+
    7.5:  "10.0",   # Turing (RTX 20xx) — CUDA 10.0+
    7.0:  "9.0",    # Volta (V100)
    6.1:  "8.0",    # Pascal (GTX 10xx)
}

# Directories to scan for Python environments (Windows-centric + cross-platform)
SCAN_ROOTS = []


def _detect_gpu_compute_capability() -> Optional[float]:
    """Detect the highest GPU compute capability on the system via nvidia-smi."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=compute_cap", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            ccs = result.stdout.strip().splitlines()
            return max(float(cc.strip()) for cc in ccs if cc.strip())
    except Exception:
        pass
    return None


def _min_cuda_for_gpu(compute_cap: float) -> Optional[str]:
    """Return the minimum CUDA toolkit version needed for a given GPU compute capability."""
    for cc_threshold in sorted(GPU_CC_MIN_CUDA.keys(), reverse=True):
        if compute_cap >= cc_threshold:
            return GPU_CC_MIN_CUDA[cc_threshold]
    return None


def _pytorch_cuda_version(version_str: str) -> Optional[str]:
    """Extract CUDA toolkit version from a PyTorch version string like '2.10.0+cu128' -> '12.8'."""
    match = re.search(r'\+cu(\d+)', version_str)
    if match:
        cu_num = match.group(1)
        if len(cu_num) >= 3:
            return f"{cu_num[:-1]}.{cu_num[-1]}"  # "128" -> "12.8"
        elif len(cu_num) == 2:
            return f"{cu_num[0]}.{cu_num[1]}"      # "92" -> "9.2"
    return None


def _cuda_version_gte(a: str, b: str) -> bool:
    """Check if CUDA version a >= b (e.g., '12.8' >= '12.4')."""
    try:
        a_parts = [int(x) for x in a.split(".")]
        b_parts = [int(x) for x in b.split(".")]
        return a_parts >= b_parts
    except (ValueError, IndexError):
        return False


def _get_scan_roots() -> list[Path]:
    """Build the list of root directories to scan for existing Python environments."""
    roots = []

    # All drive letters on Windows
    if os.name == "nt":
        import string
        for letter in string.ascii_uppercase:
            drive = Path(f"{letter}:\\")
            if drive.exists():
                roots.append(drive)
    else:
        roots.append(Path.home())
        roots.append(Path("/opt"))
        roots.append(Path("/usr/local"))

    # Also check common Python install locations
    if os.name == "nt":
        localappdata = os.environ.get("LOCALAPPDATA", "")
        if localappdata:
            roots.append(Path(localappdata) / "Programs" / "Python")
        appdata = os.environ.get("APPDATA", "")
        if appdata:
            roots.append(Path(appdata) / "Python")

    return [r for r in roots if r.exists()]


def _find_site_packages(venv_path: Path) -> Optional[Path]:
    """Given a venv root, find its site-packages directory."""
    if os.name == "nt":
        sp = venv_path / "Lib" / "site-packages"
    else:
        # Linux/macOS: lib/pythonX.Y/site-packages
        lib_dir = venv_path / "lib"
        if lib_dir.exists():
            for child in lib_dir.iterdir():
                if child.name.startswith("python"):
                    sp = child / "site-packages"
                    if sp.exists():
                        return sp
        sp = venv_path / "Lib" / "site-packages"

    return sp if sp.exists() else None


# ═══════════════════════════════════════════════════════════════════════════════
#  ENVIRONMENT SCANNER
# ═══════════════════════════════════════════════════════════════════════════════

class EnvironmentScanner:
    """
    Scans the local filesystem for existing Python virtual environments
    and catalogs what packages each one has installed.
    """

    def __init__(self, workspace: Path, max_depth: int = 4, scan_timeout: float = 30.0):
        self.workspace = workspace
        self.max_depth = max_depth
        self.scan_timeout = scan_timeout
        self.discovered_venvs: list[dict] = []
        self.package_index: dict[str, list[dict]] = {}  # pkg_name -> [{path, version, venv}]
        self._scan_start = 0.0
        self._seen_paths: set[str] = set()  # Deduplication tracker

    def scan(self, progress_callback=None) -> dict:
        """
        Scan all drives/roots for Python venvs and build a package index.

        Returns:
            {
                "venvs_found": int,
                "packages_indexed": int,
                "scan_time_ms": int,
                "heavy_packages_found": {pkg: [{path, version, venv_root}]}
            }
        """
        self._scan_start = time.time()
        roots = _get_scan_roots()

        if progress_callback:
            progress_callback(5, f"Scanning {len(roots)} root(s) for Python environments...")

        for root in roots:
            if time.time() - self._scan_start > self.scan_timeout:
                break
            self._scan_dir(root, depth=0, progress_callback=progress_callback)

        # Now index packages from discovered venvs (excluding our own workspace)
        if progress_callback:
            progress_callback(60, f"Found {len(self.discovered_venvs)} venv(s), indexing packages...")

        for i, venv_info in enumerate(self.discovered_venvs):
            if time.time() - self._scan_start > self.scan_timeout * 2:
                break

            venv_root = Path(venv_info["path"])

            # Skip ourselves
            if venv_root == self.workspace / ".venv":
                continue

            self._index_venv_packages(venv_root, progress_callback)

            if progress_callback:
                pct = 60 + int(30 * (i + 1) / max(len(self.discovered_venvs), 1))
                progress_callback(pct, f"Indexed {i + 1}/{len(self.discovered_venvs)} venvs")

        elapsed = int((time.time() - self._scan_start) * 1000)

        # Filter to just the heavy packages we care about
        heavy_found = {
            pkg: entries for pkg, entries in self.package_index.items()
            if pkg in HEAVY_PACKAGES and entries
        }

        return {
            "venvs_found": len(self.discovered_venvs),
            "packages_indexed": len(self.package_index),
            "scan_time_ms": elapsed,
            "heavy_packages_found": heavy_found,
        }

    def _scan_dir(self, root: Path, depth: int, progress_callback=None):
        # Modified: 2026-02-07T12:30:00Z | Author: COPILOT | Change: Fix dedup, skip already-seen paths
        """Recursively scan for .venv directories or pyvenv.cfg files."""
        if depth > self.max_depth:
            return
        if time.time() - self._scan_start > self.scan_timeout:
            return

        try:
            entries = list(root.iterdir())
        except (PermissionError, OSError):
            return

        for entry in entries:
            if time.time() - self._scan_start > self.scan_timeout:
                return

            try:
                if not entry.is_dir():
                    continue

                # Skip known non-productive directories
                name_lower = entry.name.lower()
                if name_lower in {
                    "$recycle.bin", "system volume information", "windows",
                    "program files", "program files (x86)", "programdata",
                    ".git", "node_modules", "__pycache__", "actions-runner",
                    "slate_work", "appdata", "recovery", "users",
                }:
                    continue

                entry_str = str(entry)
                if entry_str in self._seen_paths:
                    continue
                self._seen_paths.add(entry_str)

                # Is this a venv? (has pyvenv.cfg at this level)
                pyvenv_cfg = entry / "pyvenv.cfg"
                if pyvenv_cfg.exists():
                    sp = _find_site_packages(entry)
                    if sp:
                        self.discovered_venvs.append({
                            "path": entry_str,
                            "site_packages": str(sp),
                            "python_version": self._read_pyvenv_version(pyvenv_cfg),
                        })
                        if progress_callback:
                            progress_callback(None, f"Found venv: {entry}")
                    continue  # Don't recurse into venvs

                # Check for .venv subdirectory (project folder pattern)
                venv_subdir = entry / ".venv"
                venv_str = str(venv_subdir)
                if (venv_subdir.exists() and venv_str not in self._seen_paths
                        and (venv_subdir / "pyvenv.cfg").exists()):
                    self._seen_paths.add(venv_str)
                    sp = _find_site_packages(venv_subdir)
                    if sp:
                        self.discovered_venvs.append({
                            "path": venv_str,
                            "site_packages": str(sp),
                            "python_version": self._read_pyvenv_version(
                                venv_subdir / "pyvenv.cfg"),
                        })
                        if progress_callback:
                            progress_callback(None, f"Found venv: {venv_subdir}")

                # Recurse deeper (but not into the .venv we just found)
                self._scan_dir(entry, depth + 1, progress_callback)

            except (PermissionError, OSError):
                continue

    def _read_pyvenv_version(self, cfg_path: Path) -> str:
        """Extract Python version from pyvenv.cfg."""
        try:
            text = cfg_path.read_text(encoding='utf-8', errors='ignore')
            for line in text.splitlines():
                if line.startswith("version"):
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        return parts[1].strip()
        except Exception:
            pass
        return "unknown"

    def _index_venv_packages(self, venv_root: Path, progress_callback=None):
        """
        Index all packages in a venv's site-packages by reading dist-info.
        This is faster than running `pip list` (no subprocess).
        """
        sp = _find_site_packages(venv_root)
        if not sp:
            return

        try:
            for item in sp.iterdir():
                # dist-info directories: package_name-version.dist-info
                if item.name.endswith(".dist-info") and item.is_dir():
                    # Parse name and version from directory name
                    # Format: name-version.dist-info
                    parts = item.name[:-len(".dist-info")]
                    # PEP-427: name may contain hyphens, version after last hyphen
                    # But dist-info uses the normalized form
                    match = re.match(r'^(.+?)-(\d+.*)$', parts)
                    if match:
                        pkg_name = match.group(1).lower().replace("-", "_").replace(".", "_")
                        pkg_version = match.group(2)

                        # Find the actual package directory/files
                        pkg_dir = self._find_package_dir(sp, pkg_name, item)

                        entry = {
                            "version": pkg_version,
                            "venv_root": str(venv_root),
                            "site_packages": str(sp),
                            "dist_info": str(item),
                            "package_dir": str(pkg_dir) if pkg_dir else None,
                        }

                        if pkg_name not in self.package_index:
                            self.package_index[pkg_name] = []
                        self.package_index[pkg_name].append(entry)

        except (PermissionError, OSError):
            pass

    def _find_package_dir(self, site_packages: Path, pkg_name: str,
                          dist_info_dir: Path) -> Optional[Path]:
        """Find the actual installed package directory in site-packages."""
        # Try RECORD file for the list of installed files
        record_file = dist_info_dir / "RECORD"
        if record_file.exists():
            try:
                text = record_file.read_text(encoding='utf-8', errors='ignore')
                first_line = text.splitlines()[0] if text.strip() else ""
                top_dir = first_line.split("/")[0] if "/" in first_line else ""
                if top_dir:
                    candidate = site_packages / top_dir
                    if candidate.exists():
                        return candidate
            except Exception:
                pass

        # Try top_level.txt
        top_level = dist_info_dir / "top_level.txt"
        if top_level.exists():
            try:
                names = top_level.read_text(encoding='utf-8', errors='ignore').strip().splitlines()
                if names:
                    candidate = site_packages / names[0].strip()
                    if candidate.exists():
                        return candidate
            except Exception:
                pass

        # Try direct name match
        for name_variant in [pkg_name, pkg_name.replace("_", "-")]:
            candidate = site_packages / name_variant
            if candidate.exists():
                return candidate

        return None

    def find_package(self, package_name: str) -> Optional[dict]:
        """
        Find the best existing installation of a package.
        Prefers: same Python version > newest version > any.
        """
        normalized = package_name.lower().replace("-", "_").replace(".", "_")
        entries = self.package_index.get(normalized, [])

        if not entries:
            return None

        # Prefer installations from the same Python minor version
        our_version = f"{sys.version_info.major}.{sys.version_info.minor}"
        same_ver = [e for e in entries if our_version in e.get("version", "")]

        # Sort by version (highest first)
        def _version_key(entry):
            v = entry.get("version", "0")
            parts = re.findall(r'\d+', v)
            return tuple(int(p) for p in parts[:4]) if parts else (0,)

        candidates = same_ver or entries
        candidates.sort(key=_version_key, reverse=True)
        return candidates[0]


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPENDENCY LINKER
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyLinker:
    """
    Creates symlinks/junctions from an existing package installation
    into the workspace venv's site-packages, avoiding a full reinstall.
    """

    def __init__(self, workspace: Path):
        self.workspace = workspace
        self.venv_sp = _find_site_packages(workspace / ".venv")
        self.linked: list[dict] = []
        self.failed: list[dict] = []

    def link_package(self, package_name: str, source_info: dict) -> bool:
        """
        Link a package from source_info into our venv's site-packages.

        Creates:
            1. A junction/symlink for the package directory
            2. A copy of the .dist-info directory (metadata)

        Returns True if successful.
        """
        if not self.venv_sp:
            self.failed.append({"package": package_name, "reason": "no site-packages"})
            return False

        source_sp = Path(source_info["site_packages"])
        pkg_dir = source_info.get("package_dir")
        dist_info = source_info.get("dist_info")

        if not pkg_dir or not Path(pkg_dir).exists():
            self.failed.append({"package": package_name, "reason": "source package dir not found"})
            return False

        source_pkg = Path(pkg_dir)
        target_pkg = self.venv_sp / source_pkg.name

        # Check if already exists
        if target_pkg.exists():
            self.linked.append({
                "package": package_name,
                "source": str(source_pkg),
                "target": str(target_pkg),
                "action": "already_exists",
            })
            return True

        try:
            # Create junction (Windows) or symlink (Unix) for the package dir
            if source_pkg.is_dir():
                if os.name == "nt":
                    # Use junction for directories on Windows (no admin required)
                    result = subprocess.run(
                        ["cmd", "/c", "mklink", "/J", str(target_pkg), str(source_pkg)],
                        capture_output=True, text=True, timeout=10,
                    )
                    if result.returncode != 0:
                        # Fall back to directory symlink
                        try:
                            target_pkg.symlink_to(source_pkg, target_is_directory=True)
                        except OSError:
                            # Last resort: copy (for packages on different filesystems)
                            shutil.copytree(str(source_pkg), str(target_pkg))
                else:
                    target_pkg.symlink_to(source_pkg, target_is_directory=True)
            else:
                # Single file module
                target_file = self.venv_sp / source_pkg.name
                if os.name == "nt":
                    subprocess.run(
                        ["cmd", "/c", "mklink", str(target_file), str(source_pkg)],
                        capture_output=True, text=True, timeout=10,
                    )
                else:
                    target_file.symlink_to(source_pkg)

            # Also link/copy dist-info for pip to recognize the package
            if dist_info and Path(dist_info).exists():
                source_dist = Path(dist_info)
                target_dist = self.venv_sp / source_dist.name
                if not target_dist.exists():
                    if os.name == "nt":
                        subprocess.run(
                            ["cmd", "/c", "mklink", "/J", str(target_dist), str(source_dist)],
                            capture_output=True, text=True, timeout=10,
                        )
                    else:
                        target_dist.symlink_to(source_dist, target_is_directory=True)

            self.linked.append({
                "package": package_name,
                "source": str(source_pkg),
                "target": str(target_pkg),
                "action": "linked",
                "version": source_info.get("version", "unknown"),
            })
            return True

        except Exception as e:
            self.failed.append({"package": package_name, "reason": str(e)})
            return False

    def get_summary(self) -> dict:
        """Get a summary of linking operations."""
        return {
            "linked": len(self.linked),
            "failed": len(self.failed),
            "details": {
                "linked": self.linked,
                "failed": self.failed,
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════
#  DEPENDENCY RESOLVER (Main Orchestrator)
# ═══════════════════════════════════════════════════════════════════════════════

class DependencyResolver:
    """
    Orchestrates the scan → match → link → install pipeline.

    Usage:
        resolver = DependencyResolver(workspace=Path("."))
        result = resolver.resolve_all(requirements_file=Path("requirements.txt"))
        print(result["summary"])
    """

    def __init__(self, workspace: Path, scan_timeout: float = 30.0):
        self.workspace = workspace
        self.scanner = EnvironmentScanner(workspace, scan_timeout=scan_timeout)
        self.linker = DependencyLinker(workspace)
        self.scan_result: Optional[dict] = None
        self._log: list[str] = []

    def log(self, msg: str):
        """Internal log."""
        self._log.append(f"[{time.strftime('%H:%M:%S')}] {msg}")

    def scan_system(self, progress_callback=None) -> dict:
        """Phase 1: Scan the system for existing environments and packages."""
        self.log("Starting system scan for existing Python environments...")
        self.scan_result = self.scanner.scan(progress_callback)
        self.log(f"Scan complete: {self.scan_result['venvs_found']} venvs, "
                 f"{self.scan_result['packages_indexed']} packages indexed in "
                 f"{self.scan_result['scan_time_ms']}ms")
        return self.scan_result

    def resolve_requirements(self, requirements_file: Path,
                             progress_callback=None) -> dict:
        """
        Phase 2+3: For each requirement, try to link from existing install,
        otherwise mark for fresh install.

        Returns:
            {
                "linked": [list of packages linked from other envs],
                "to_install": [list of packages that need fresh install],
                "already_present": [list already in workspace venv],
                "skipped": [list of packages skipped (comments, etc)],
            }
        """
        if self.scan_result is None:
            self.scan_system(progress_callback)

        linked = []
        to_install = []
        already_present = []
        skipped = []

        # Parse requirements file
        requirements = self._parse_requirements(requirements_file)

        if progress_callback:
            progress_callback(0, f"Resolving {len(requirements)} dependencies...")

        workspace_sp = _find_site_packages(self.workspace / ".venv")

        for i, req in enumerate(requirements):
            pkg_name = req["name"]
            normalized = pkg_name.lower().replace("-", "_").replace(".", "_")

            if progress_callback:
                pct = int(100 * (i + 1) / max(len(requirements), 1))
                progress_callback(pct, f"Resolving {pkg_name}...")

            # Check if already in our workspace venv
            if workspace_sp and self._package_in_site_packages(workspace_sp, normalized):
                already_present.append(pkg_name)
                self.log(f"  ✓ {pkg_name}: already in workspace venv")
                continue

            # Check if it's a heavy package worth linking
            if normalized in HEAVY_PACKAGES:
                existing = self.scanner.find_package(pkg_name)
                if existing:
                    # Try to link it
                    version_ok = self._version_compatible(
                        existing.get("version", ""), req.get("version_spec", ""))
                    if version_ok:
                        success = self.linker.link_package(pkg_name, existing)
                        if success:
                            linked.append({
                                "name": pkg_name,
                                "version": existing.get("version", "?"),
                                "source": existing.get("venv_root", "?"),
                            })
                            self.log(f"  → {pkg_name}: LINKED from {existing['venv_root']} "
                                     f"(v{existing.get('version', '?')})")
                            continue
                        else:
                            self.log(f"  ✗ {pkg_name}: link failed, will install fresh")

            # Not found or not linkable — mark for install
            to_install.append(req["raw_line"])
            self.log(f"  ↓ {pkg_name}: will install fresh")

        return {
            "linked": linked,
            "to_install": to_install,
            "already_present": already_present,
            "skipped": skipped,
            "link_summary": self.linker.get_summary(),
        }

    def install_remaining(self, to_install: list[str], pip_exe: Path,
                          progress_callback=None) -> dict:
        """
        Phase 4: Install only the packages that weren't found anywhere.
        Writes a temp requirements file with only the missing packages.
        """
        if not to_install:
            return {"installed": 0, "success": True, "details": "Nothing to install — all resolved"}

        # Write a temporary requirements file with only missing packages
        temp_req = self.workspace / ".slate_install" / "remaining_requirements.txt"
        temp_req.parent.mkdir(parents=True, exist_ok=True)
        temp_req.write_text("\n".join(to_install) + "\n", encoding='utf-8')

        self.log(f"Installing {len(to_install)} remaining packages...")
        if progress_callback:
            progress_callback(10, f"Installing {len(to_install)} packages (others were linked)...")

        try:
            result = subprocess.run(
                [str(pip_exe), "install", "-r", str(temp_req), "--quiet"],
                capture_output=True, text=True, timeout=600,
                cwd=str(self.workspace),
            )
            if result.returncode == 0:
                self.log(f"Successfully installed {len(to_install)} packages")
                return {
                    "installed": len(to_install),
                    "success": True,
                    "details": f"{len(to_install)} packages installed fresh",
                }
            else:
                error = result.stderr.strip().splitlines()[-1] if result.stderr else "unknown error"
                self.log(f"pip install failed: {error}")
                return {
                    "installed": 0,
                    "success": False,
                    "details": f"pip install failed: {error}",
                    "stderr": result.stderr,
                }
        except subprocess.TimeoutExpired:
            return {"installed": 0, "success": False, "details": "pip install timed out"}
        except Exception as e:
            return {"installed": 0, "success": False, "details": str(e)}

    def resolve_all(self, requirements_file: Path, pip_exe: Path,
                    progress_callback=None) -> dict:
        """
        Full pipeline: scan → match → link → install.

        Returns a comprehensive result dict.
        """
        # Phase 1: Scan
        if progress_callback:
            progress_callback(5, "Phase 1/4: Scanning system for existing dependencies...")
        scan = self.scan_system(
            lambda pct, msg: progress_callback(5 + int(pct * 0.25), msg) if progress_callback and pct else None
        )

        # Phase 2+3: Resolve & Link
        if progress_callback:
            progress_callback(35, "Phase 2/4: Matching & linking existing packages...")
        resolution = self.resolve_requirements(
            requirements_file,
            lambda pct, msg: progress_callback(35 + int(pct * 0.25), msg) if progress_callback and pct else None
        )

        # Phase 4: Install remaining
        if progress_callback:
            progress_callback(65, "Phase 3/4: Installing missing dependencies...")
        install_result = self.install_remaining(
            resolution["to_install"], pip_exe,
            lambda pct, msg: progress_callback(65 + int(pct * 0.30), msg) if progress_callback and pct else None
        )

        if progress_callback:
            progress_callback(95, "Phase 4/4: Finalizing...")

        summary = {
            "scan": scan,
            "linked": resolution["linked"],
            "installed_fresh": install_result.get("installed", 0),
            "already_present": resolution["already_present"],
            "link_summary": resolution["link_summary"],
            "install_result": install_result,
            "packages_saved": len(resolution["linked"]),
            "total_requirements": (len(resolution["linked"]) +
                                   len(resolution["to_install"]) +
                                   len(resolution["already_present"])),
            "log": self._log,
        }

        self.log(f"\nResolution complete: "
                 f"{len(resolution['already_present'])} present, "
                 f"{len(resolution['linked'])} linked, "
                 f"{install_result.get('installed', 0)} installed fresh")

        return summary

    def check_system_tools(self, progress_callback=None) -> dict:
        """Check which system-level tools (Ollama, Docker, etc.) are available."""
        results = {}
        for tool_name, tool_info in SYSTEM_TOOLS.items():
            try:
                result = subprocess.run(
                    tool_info["check_cmd"],
                    capture_output=True, text=True, timeout=10,
                )
                if result.returncode == 0:
                    version = result.stdout.strip().split("\n")[0]
                    results[tool_name] = {
                        "installed": True,
                        "version": version,
                        "path": shutil.which(tool_info["check_cmd"][0]),
                    }
                else:
                    results[tool_name] = {"installed": False}
            except (FileNotFoundError, subprocess.TimeoutExpired):
                results[tool_name] = {"installed": False}

        return results

    def find_pytorch(self) -> Optional[dict]:
        # Modified: 2026-02-07T15:30:00Z | Author: COPILOT | Change: Add GPU compute capability filtering for Blackwell sm_120
        """
        Special handler for PyTorch — it's huge (~3GB) and worth scanning for.
        Checks all known venvs for a CUDA-enabled PyTorch installation.
        Prefers: GPU-compatible > CUDA-enabled > highest version > stable over dev builds.

        GPU compatibility: If an NVIDIA GPU is detected, only CUDA-enabled PyTorch
        builds whose CUDA toolkit version meets the GPU's minimum requirement are
        considered compatible. E.g., Blackwell (sm_120) requires CUDA 12.8+, so
        PyTorch+cu124 will be rejected in favor of PyTorch+cu128.
        """
        torch_entries = self.scanner.package_index.get("torch", [])
        if not torch_entries:
            return None

        # Detect GPU compute capability for compatibility filtering
        gpu_cc = _detect_gpu_compute_capability()
        min_cuda = _min_cuda_for_gpu(gpu_cc) if gpu_cc else None

        # Enrich entries with CUDA info and compatibility
        for entry in torch_entries:
            venv_root = Path(entry.get("venv_root", ""))
            sp = Path(entry.get("site_packages", ""))
            torch_dir = sp / "torch"

            if torch_dir.exists():
                # Check if this torch has CUDA
                cuda_dir = torch_dir / "lib"  # Windows: torch/lib has CUDA DLLs
                has_cuda = False
                if cuda_dir.exists():
                    cuda_files = list(cuda_dir.glob("*cuda*")) + list(cuda_dir.glob("*cublas*"))
                    has_cuda = len(cuda_files) > 0

                entry["has_cuda"] = has_cuda
                entry["torch_dir"] = str(torch_dir)

                # Check GPU compatibility: does this PyTorch's CUDA version support the GPU?
                version_str = entry.get("version", "")
                cuda_ver = _pytorch_cuda_version(version_str)
                entry["cuda_toolkit_version"] = cuda_ver
                if min_cuda and cuda_ver:
                    entry["gpu_compatible"] = _cuda_version_gte(cuda_ver, min_cuda)
                elif min_cuda and has_cuda and not cuda_ver:
                    # Has CUDA but can't determine version — mark uncertain
                    entry["gpu_compatible"] = None
                else:
                    entry["gpu_compatible"] = True  # No GPU detected or no min requirement

        # Sort: GPU-compatible first, then CUDA, then stable, then by version
        def _torch_sort_key(e):
            # GPU compatibility: True=2, None/unknown=1, False=0
            gpu_compat = e.get("gpu_compatible")
            if gpu_compat is True:
                compat_score = 2
            elif gpu_compat is None:
                compat_score = 1
            else:
                compat_score = 0

            has_cuda = 1 if e.get("has_cuda", False) else 0
            v = e.get("version", "0")
            is_stable = 0 if "dev" in v else 1  # Stable builds preferred
            numeric = self._parse_version(v)
            return (compat_score, has_cuda, is_stable, numeric)

        torch_entries.sort(key=_torch_sort_key, reverse=True)

        best = torch_entries[0] if torch_entries else None

        # If the best candidate is explicitly GPU-incompatible, log a warning
        if best and best.get("gpu_compatible") is False and gpu_cc:
            best["_warning"] = (
                f"PyTorch {best.get('version')} (CUDA {best.get('cuda_toolkit_version')}) "
                f"does NOT support GPU compute {gpu_cc} (needs CUDA {min_cuda}+). "
                f"Will install a compatible version instead."
            )

        return best

    # ─── Internal helpers ─────────────────────────────────────────────────────

    def _parse_requirements(self, req_file: Path) -> list[dict]:
        """Parse a requirements.txt into structured entries."""
        requirements = []
        try:
            lines = req_file.read_text(encoding='utf-8').splitlines()
        except Exception:
            return requirements

        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or stripped.startswith("-"):
                continue

            # Handle version specifiers: pkg>=1.0,<2
            match = re.match(r'^([a-zA-Z0-9_\-\.]+(?:\[[^\]]+\])?)\s*(.*)$', stripped)
            if match:
                name = match.group(1).split("[")[0]  # Remove extras like [standard]
                version_spec = match.group(2)
                requirements.append({
                    "name": name,
                    "version_spec": version_spec,
                    "raw_line": stripped,
                })

        return requirements

    def _package_in_site_packages(self, site_packages: Path, pkg_name: str) -> bool:
        """Check if a package is already installed in a site-packages dir."""
        # Check for directory
        if (site_packages / pkg_name).exists():
            return True
        # Check for dist-info
        for item in site_packages.iterdir():
            if (item.name.startswith(f"{pkg_name}-") and
                    item.name.endswith(".dist-info")):
                return True
        return False

    def _version_compatible(self, installed_version: str, version_spec: str) -> bool:
        """Check if an installed version meets the version specification."""
        if not version_spec:
            return True  # No spec = any version OK

        # Simple check for common patterns
        # For robust checking, we'd use packaging.version, but we keep it minimal
        try:
            specs = version_spec.split(",")
            for spec in specs:
                spec = spec.strip()
                if spec.startswith(">="):
                    min_ver = spec[2:]
                    if not self._version_gte(installed_version, min_ver):
                        return False
                elif spec.startswith("<="):
                    max_ver = spec[2:]
                    if not self._version_lte(installed_version, max_ver):
                        return False
                elif spec.startswith("<"):
                    max_ver = spec[1:]
                    if not self._version_lt(installed_version, max_ver):
                        return False
                elif spec.startswith(">"):
                    min_ver = spec[1:]
                    if not self._version_gt(installed_version, min_ver):
                        return False
                elif spec.startswith("=="):
                    eq_ver = spec[2:]
                    if installed_version != eq_ver:
                        return False
                elif spec.startswith("!="):
                    ne_ver = spec[2:]
                    if installed_version == ne_ver:
                        return False
            return True
        except Exception:
            return True  # On parse error, assume compatible

    @staticmethod
    def _parse_version(v: str) -> tuple:
        """Parse version string to comparable tuple."""
        parts = re.findall(r'\d+', v)
        return tuple(int(p) for p in parts[:4]) if parts else (0,)

    @classmethod
    def _version_gte(cls, a: str, b: str) -> bool:
        return cls._parse_version(a) >= cls._parse_version(b)

    @classmethod
    def _version_lte(cls, a: str, b: str) -> bool:
        return cls._parse_version(a) <= cls._parse_version(b)

    @classmethod
    def _version_lt(cls, a: str, b: str) -> bool:
        return cls._parse_version(a) < cls._parse_version(b)

    @classmethod
    def _version_gt(cls, a: str, b: str) -> bool:
        return cls._parse_version(a) > cls._parse_version(b)


# ═══════════════════════════════════════════════════════════════════════════════
#  CLI ENTRY POINT
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI: scan system and report what can be linked vs installed."""
    import argparse
    parser = argparse.ArgumentParser(description="SLATE Dependency Resolver")
    parser.add_argument("--scan", action="store_true", help="Scan system for existing environments")
    parser.add_argument("--resolve", action="store_true", help="Resolve requirements.txt with linking")
    parser.add_argument("--json", action="store_true", help="JSON output")
    parser.add_argument("--timeout", type=float, default=30.0, help="Scan timeout in seconds")
    args = parser.parse_args()

    workspace = Path(__file__).parent.parent
    resolver = DependencyResolver(workspace, scan_timeout=args.timeout)

    if args.scan:
        result = resolver.scan_system(
            lambda pct, msg: print(f"  [{pct or '?'}%] {msg}") if msg else None
        )
        if args.json:
            # Convert heavy_packages_found for JSON serialization
            output = {**result}
            print(json.dumps(output, indent=2, default=str))
        else:
            print(f"\n  Venvs found: {result['venvs_found']}")
            print(f"  Packages indexed: {result['packages_indexed']}")
            print(f"  Scan time: {result['scan_time_ms']}ms")
            if result['heavy_packages_found']:
                print(f"\n  Heavy packages available for linking:")
                for pkg, entries in result['heavy_packages_found'].items():
                    for e in entries:
                        print(f"    • {pkg} v{e['version']} @ {e['venv_root']}")
            else:
                print("  No heavy packages found in other environments")

    elif args.resolve:
        req_file = workspace / "requirements.txt"
        pip_exe = workspace / ".venv" / ("Scripts" if os.name == "nt" else "bin") / "pip.exe"
        result = resolver.resolve_all(
            req_file, pip_exe,
            lambda pct, msg: print(f"  [{pct}%] {msg}") if msg else None
        )
        if args.json:
            print(json.dumps(result, indent=2, default=str))
        else:
            print(f"\n  Resolution Summary:")
            print(f"    Already present: {len(result['already_present'])}")
            print(f"    Linked from other envs: {result['packages_saved']}")
            print(f"    Installed fresh: {result['installed_fresh']}")
            if result['linked']:
                print(f"\n  Linked packages:")
                for pkg in result['linked']:
                    print(f"    → {pkg['name']} v{pkg['version']} from {pkg['source']}")
    else:
        # Default: just scan and report
        print("  SLATE Dependency Resolver")
        print("  Use --scan to scan system, --resolve to resolve + link\n")
        tools = resolver.check_system_tools()
        print("  System Tools:")
        for name, info in tools.items():
            status = f"✓ {info.get('version', '')}" if info.get("installed") else "✗ not found"
            print(f"    {name:10s} {status}")


if __name__ == "__main__":
    main()
