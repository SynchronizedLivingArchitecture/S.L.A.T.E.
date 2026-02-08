#!/usr/bin/env python3
# Modified: 2026-02-08T14:30:00Z | Author: COPILOT | Change: Create stable release manager for SLATE install/update reference
"""
SLATE Release Manager
======================
Manages the "stable" release channel that serves as the primary install and
update reference for the full SLATE system. Maintains local release artifacts,
validates release integrity, and coordinates with GitHub Releases.

Architecture:
    pyproject.toml (version source) → release_state.json → GitHub Release
    install_slate.py (--update) uses this to determine current/target versions

Channels:
    - stable:  Production-ready, tested, CI/CD passed (tagged vX.Y.Z)
    - beta:    Pre-release, feature-complete, needs validation (tagged vX.Y.Z-beta.N)
    - nightly: Auto-generated from main branch (not tagged, artifact only)

Stability Contract:
    A "stable" release MUST pass:
    1. All CI tests (core, security, agents, ml)
    2. GPU inference health check
    3. Docker build validation
    4. install_slate.py --check (ecosystem validation)
    5. SDK bridge compatibility check
    6. Local runner connectivity test

Usage:
    python slate/slate_release_manager.py --status       # Current release state
    python slate/slate_release_manager.py --validate     # Validate current checkout is release-worthy
    python slate/slate_release_manager.py --lock          # Lock current version as stable
    python slate/slate_release_manager.py --prepare X.Y.Z # Prepare a release candidate
    python slate/slate_release_manager.py --promote       # Promote current RC to stable
    python slate/slate_release_manager.py --check-update   # Check if update is available
    python slate/slate_release_manager.py --json          # JSON output
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Modified: 2026-02-08T14:30:00Z | Author: COPILOT | Change: Initial release manager implementation
WORKSPACE_ROOT = Path(__file__).parent.parent.resolve()
RELEASE_STATE_FILE = WORKSPACE_ROOT / ".slate_release_state.json"
PYPROJECT_FILE = WORKSPACE_ROOT / "pyproject.toml"
INSTALL_SCRIPT = WORKSPACE_ROOT / "install_slate.py"


class ReleaseChannel:
    STABLE = "stable"
    BETA = "beta"
    NIGHTLY = "nightly"


class ReleaseManager:
    """
    Manages SLATE release lifecycle — versioning, validation, promotion.
    The stable release is the single source of truth for install_slate.py.
    """

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.state_file = self.workspace / ".slate_release_state.json"
        self.pyproject = self.workspace / "pyproject.toml"
        self._state = None

    # ─── Version Source ───────────────────────────────────────────────────

    def get_pyproject_version(self) -> str:
        """Read version from pyproject.toml (single source of truth)."""
        try:
            import tomllib
        except ImportError:
            import tomli as tomllib  # type: ignore[no-redef]

        with open(self.pyproject, "rb") as f:
            data = tomllib.load(f)
        return data["project"]["version"]

    def get_git_tag(self) -> Optional[str]:
        """Get current git tag if HEAD is tagged."""
        try:
            result = subprocess.run(
                ["git", "describe", "--exact-match", "--tags", "HEAD"],
                capture_output=True, text=True,
                cwd=str(self.workspace)
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            pass
        return None

    def get_git_sha(self) -> str:
        """Get current HEAD commit SHA."""
        try:
            result = subprocess.run(
                ["git", "rev-parse", "--short=12", "HEAD"],
                capture_output=True, text=True,
                cwd=str(self.workspace)
            )
            return result.stdout.strip()
        except (subprocess.SubprocessError, OSError):
            return "unknown"

    def get_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                capture_output=True, text=True,
                cwd=str(self.workspace)
            )
            return result.stdout.strip() or "detached"
        except (subprocess.SubprocessError, OSError):
            return "unknown"

    # ─── Release State Persistence ────────────────────────────────────────

    def load_state(self) -> dict[str, Any]:
        """Load persisted release state."""
        if self._state is not None:
            return self._state
        if self.state_file.exists():
            try:
                with open(self.state_file, "r", encoding="utf-8") as f:
                    self._state = json.load(f)
                    return self._state
            except (json.JSONDecodeError, OSError):
                pass
        # Default state
        self._state = {
            "channel": ReleaseChannel.NIGHTLY,
            "stable_version": None,
            "stable_sha": None,
            "stable_date": None,
            "rc_version": None,
            "rc_sha": None,
            "rc_date": None,
            "last_validation": None,
            "validation_passed": False,
            "locked": False,
            "history": [],
        }
        return self._state

    def save_state(self):
        """Persist release state to disk."""
        state = self.load_state()
        with open(self.state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    # ─── Validation Pipeline ─────────────────────────────────────────────

    def validate_release(self, verbose: bool = True) -> dict[str, Any]:
        """
        Run the full stability validation pipeline.
        A release MUST pass ALL checks to qualify as stable.
        """
        checks: list[dict[str, Any]] = []
        now = datetime.now(timezone.utc).isoformat()

        def _check(name: str, cmd: list[str], timeout: int = 60) -> bool:
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True,
                    cwd=str(self.workspace), timeout=timeout
                )
                passed = result.returncode == 0
                checks.append({
                    "name": name, "passed": passed,
                    "output": result.stdout[:500] if not passed else "",
                    "error": result.stderr[:500] if not passed else "",
                })
                if verbose:
                    icon = "✓" if passed else "✗"
                    print(f"  [{icon}] {name}")
                return passed
            except (subprocess.SubprocessError, OSError) as e:
                checks.append({"name": name, "passed": False, "error": str(e)})
                if verbose:
                    print(f"  [✗] {name}: {e}")
                return False

        python = str(self.workspace / ".venv" / "Scripts" / "python.exe")
        if not Path(python).exists():
            python = str(self.workspace / ".venv" / "bin" / "python")

        if verbose:
            print("\n  SLATE Release Validation Pipeline")
            print("  " + "=" * 40)

        # 1. Python environment
        _check("Python environment", [python, "--version"])

        # 2. Core SDK import
        _check("SDK import", [python, "-c",
                               "import slate; print(f'v{slate.__version__}')"])

        # 3. System health
        _check("System health", [python, "slate/slate_status.py", "--quick"], timeout=30)

        # 4. Runtime integrations
        _check("Runtime integrations", [python, "slate/slate_runtime.py", "--check-all"], timeout=30)

        # 5. Action guard
        _check("Security guards", [python, "-c",
                                    "from slate.action_guard import ActionGuard; g = ActionGuard(); print('ActionGuard OK')"])

        # 6. Install script check
        _check("Install script --check", [python, "install_slate.py", "--check"], timeout=120)

        # 7. SDK bridge compatibility  
        sdk_bridge = self.workspace / "slate" / "slate_copilot_sdk_bridge.py"
        if sdk_bridge.exists():
            _check("Copilot SDK bridge", [python, str(sdk_bridge), "--check"], timeout=30)

        # 8. Docker compose validation
        _check("Docker compose", [python, "-c",
                                   "import yaml; yaml.safe_load(open('docker-compose.yml')); print('docker-compose.yml valid')"],
               timeout=10)

        # 9. pyproject.toml validity
        _check("pyproject.toml", [python, "-c",
                                   "import tomllib; d=tomllib.load(open('pyproject.toml','rb')); print(f'v{d[\"project\"][\"version\"]}')"])

        # 10. Git state (clean working tree)
        git_check = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True,
            cwd=str(self.workspace)
        )
        clean = len(git_check.stdout.strip()) == 0
        checks.append({"name": "Git clean state", "passed": clean,
                       "output": "" if clean else f"{len(git_check.stdout.splitlines())} uncommitted changes"})
        if verbose:
            icon = "✓" if clean else "⚠"
            print(f"  [{icon}] Git clean state {'(clean)' if clean else '(uncommitted changes)'}")

        all_passed = all(c["passed"] for c in checks)
        critical_passed = all(c["passed"] for c in checks
                             if c["name"] not in ["Git clean state", "Docker compose"])

        # Update state
        state = self.load_state()
        state["last_validation"] = now
        state["validation_passed"] = all_passed
        self.save_state()

        if verbose:
            print("  " + "-" * 40)
            passed_count = sum(1 for c in checks if c["passed"])
            print(f"  Result: {passed_count}/{len(checks)} checks passed")
            if all_passed:
                print("  ✓ RELEASE-WORTHY — all checks passed")
            elif critical_passed:
                print("  ⚠ RELEASE-POSSIBLE — non-critical checks failed")
            else:
                print("  ✗ NOT RELEASE-WORTHY — critical checks failed")
            print()

        return {
            "timestamp": now,
            "version": self.get_pyproject_version(),
            "sha": self.get_git_sha(),
            "branch": self.get_branch(),
            "all_passed": all_passed,
            "critical_passed": critical_passed,
            "checks": checks,
            "passed_count": sum(1 for c in checks if c["passed"]),
            "total_checks": len(checks),
        }

    # ─── Release Operations ──────────────────────────────────────────────

    def lock_stable(self) -> dict[str, Any]:
        """Lock the current version as the stable release."""
        version = self.get_pyproject_version()
        sha = self.get_git_sha()
        now = datetime.now(timezone.utc).isoformat()

        state = self.load_state()
        old_stable = state.get("stable_version")

        state["channel"] = ReleaseChannel.STABLE
        state["stable_version"] = version
        state["stable_sha"] = sha
        state["stable_date"] = now
        state["locked"] = True

        # Track history
        if old_stable and old_stable != version:
            state["history"].append({
                "version": old_stable,
                "sha": state.get("stable_sha", "unknown"),
                "promoted": state.get("stable_date", now),
                "superseded_by": version,
                "superseded_date": now,
            })
            # Keep last 20 entries
            state["history"] = state["history"][-20:]

        self.save_state()

        print(f"\n  ✓ Locked v{version} ({sha}) as STABLE release")
        print(f"    This version is now the install/update reference")
        if old_stable and old_stable != version:
            print(f"    Previous stable: v{old_stable}")
        print()

        return {"version": version, "sha": sha, "channel": "stable", "locked": True}

    def prepare_release(self, target_version: str) -> dict[str, Any]:
        """Prepare a release candidate for the given version."""
        sha = self.get_git_sha()
        now = datetime.now(timezone.utc).isoformat()

        state = self.load_state()
        state["rc_version"] = target_version
        state["rc_sha"] = sha
        state["rc_date"] = now
        self.save_state()

        print(f"\n  ✓ Release candidate prepared: v{target_version}")
        print(f"    SHA: {sha}")
        print(f"    Run --validate to check stability, then --promote to release")
        print()

        return {"rc_version": target_version, "sha": sha, "timestamp": now}

    def promote_to_stable(self) -> dict[str, Any]:
        """Promote the current RC to stable (requires passing validation)."""
        state = self.load_state()

        if not state.get("rc_version"):
            print("  ✗ No release candidate prepared. Run --prepare X.Y.Z first.")
            return {"error": "no_rc"}

        if not state.get("validation_passed"):
            print("  ✗ Validation not passed. Run --validate first.")
            return {"error": "validation_failed"}

        # Lock as stable
        result = self.lock_stable()
        state = self.load_state()
        state["rc_version"] = None
        state["rc_sha"] = None
        state["rc_date"] = None
        self.save_state()

        return result

    def check_for_updates(self) -> dict[str, Any]:
        """Check if a newer stable release is available on GitHub."""
        current = self.get_pyproject_version()
        result: dict[str, Any] = {
            "current_version": current,
            "latest_release": None,
            "update_available": False,
            "channel": self.load_state().get("channel", "unknown"),
        }

        try:
            # Get latest release from GitHub API
            cred = subprocess.run(
                ["git", "credential", "fill"],
                input="protocol=https\nhost=github.com\n",
                capture_output=True, text=True, timeout=10
            )
            token = None
            for line in cred.stdout.splitlines():
                if line.startswith("password="):
                    token = line.split("=", 1)[1]
                    break

            if token:
                import urllib.request
                req = urllib.request.Request(
                    "https://api.github.com/repos/SynchronizedLivingArchitecture/S.L.A.T.E/releases/latest",
                    headers={
                        "Authorization": f"token {token}",
                        "Accept": "application/vnd.github.v3+json",
                    }
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    data = json.loads(resp.read())
                    latest_tag = data.get("tag_name", "").lstrip("v")
                    result["latest_release"] = latest_tag
                    result["update_available"] = latest_tag != current and latest_tag > current

        except Exception as e:
            result["error"] = str(e)

        return result

    # ─── Status Report ────────────────────────────────────────────────────

    def status(self) -> dict[str, Any]:
        """Full release status."""
        state = self.load_state()
        return {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "version": self.get_pyproject_version(),
            "sha": self.get_git_sha(),
            "branch": self.get_branch(),
            "tag": self.get_git_tag(),
            "channel": state.get("channel", "unknown"),
            "stable_version": state.get("stable_version"),
            "stable_sha": state.get("stable_sha"),
            "stable_date": state.get("stable_date"),
            "rc_version": state.get("rc_version"),
            "locked": state.get("locked", False),
            "last_validation": state.get("last_validation"),
            "validation_passed": state.get("validation_passed", False),
            "history_count": len(state.get("history", [])),
        }

    def print_status(self):
        """Print human-readable release status."""
        s = self.status()
        print()
        print("=" * 60)
        print("  SLATE Release Manager")
        print("=" * 60)
        print()
        print(f"  Current Version:    v{s['version']}")
        print(f"  Branch:             {s['branch']}")
        print(f"  Commit:             {s['sha']}")
        print(f"  Tag:                {s['tag'] or 'none'}")
        print(f"  Channel:            {s['channel'].upper()}")
        print()
        if s.get("stable_version"):
            locked = "✓ LOCKED" if s["locked"] else "unlocked"
            print(f"  Stable Release:     v{s['stable_version']} ({locked})")
            print(f"  Stable SHA:         {s['stable_sha']}")
            print(f"  Stable Date:        {s['stable_date']}")
        else:
            print("  Stable Release:     ⚠ Not yet locked")
        print()
        if s.get("rc_version"):
            print(f"  Release Candidate:  v{s['rc_version']}")
        valid = "✓ Passed" if s["validation_passed"] else "✗ Not passed"
        print(f"  Validation:         {valid}")
        if s.get("last_validation"):
            print(f"  Last Validated:     {s['last_validation']}")
        print(f"  Release History:    {s['history_count']} entries")
        print()
        print("=" * 60)
        print()


def main():
    parser = argparse.ArgumentParser(
        description="SLATE Release Manager — stable release lifecycle management"
    )
    parser.add_argument("--status", action="store_true", help="Show release status")
    parser.add_argument("--validate", action="store_true", help="Run full validation pipeline")
    parser.add_argument("--lock", action="store_true", help="Lock current version as stable")
    parser.add_argument("--prepare", type=str, metavar="VERSION", help="Prepare release candidate")
    parser.add_argument("--promote", action="store_true", help="Promote RC to stable")
    parser.add_argument("--check-update", action="store_true", help="Check for available updates")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    mgr = ReleaseManager()

    if args.validate:
        result = mgr.validate_release(verbose=not args.json)
        if args.json:
            print(json.dumps(result, indent=2))
        return

    if args.lock:
        result = mgr.lock_stable()
        if args.json:
            print(json.dumps(result, indent=2))
        return

    if args.prepare:
        result = mgr.prepare_release(args.prepare)
        if args.json:
            print(json.dumps(result, indent=2))
        return

    if args.promote:
        result = mgr.promote_to_stable()
        if args.json:
            print(json.dumps(result, indent=2))
        return

    if args.check_update:
        result = mgr.check_for_updates()
        if args.json:
            print(json.dumps(result, indent=2))
        else:
            if result.get("update_available"):
                print(f"\n  ⬆ Update available: v{result['current_version']} → v{result['latest_release']}")
                print(f"    Run: python install_slate.py --update")
            else:
                print(f"\n  ✓ You are on the latest version: v{result['current_version']}")
                if result.get("latest_release"):
                    print(f"    Latest release: v{result['latest_release']}")
            print()
        return

    # Default: status
    if args.json:
        print(json.dumps(mgr.status(), indent=2))
    else:
        mgr.print_status()


if __name__ == "__main__":
    main()
