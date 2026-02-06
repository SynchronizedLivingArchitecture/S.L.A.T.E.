#!/usr/bin/env python3
"""
SLATE Workflow Push Helper

Handles pushing workflow files to GitHub with proper OAuth scope.
GitHub requires the 'workflow' scope to push changes to .github/workflows/.
This script detects when workflow files need pushing and handles authentication.

Usage:
    python slate/slate_workflow_push.py          # Auto-detect and push
    python slate/slate_workflow_push.py --check  # Check if workflow scope available
    python slate/slate_workflow_push.py --auth   # Re-authenticate with workflow scope
"""

import subprocess
import sys
import json
from pathlib import Path


def run_command(cmd: list[str], capture: bool = True) -> tuple[int, str, str]:
    """Run a shell command and return exit code, stdout, stderr."""
    try:
        result = subprocess.run(
            cmd,
            capture_output=capture,
            text=True,
            shell=True if sys.platform == "win32" else False
        )
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return 1, "", str(e)


def get_gh_path() -> str | None:
    """Find the gh CLI executable."""
    if sys.platform == "win32":
        # Common Windows paths for gh
        common_paths = [
            Path.home() / "AppData/Local/Programs/GitHub CLI/gh.exe",
            Path("C:/Program Files/GitHub CLI/gh.exe"),
            Path("C:/Program Files (x86)/GitHub CLI/gh.exe"),
        ]
        for p in common_paths:
            if p.exists():
                return str(p)

    # Try PATH
    code, out, _ = run_command(["where" if sys.platform == "win32" else "which", "gh"])
    if code == 0 and out.strip():
        return out.strip().split("\n")[0]

    return None


def check_workflow_scope() -> bool:
    """Check if current GitHub auth has workflow scope."""
    gh = get_gh_path()
    if not gh:
        print("❌ GitHub CLI (gh) not found. Install from: https://cli.github.com/")
        return False

    code, out, err = run_command([gh, "auth", "status"])
    if code != 0:
        print(f"❌ Not authenticated with GitHub CLI: {err}")
        return False

    # Check scopes
    code, out, _ = run_command([gh, "api", "user", "-H", "Accept: application/vnd.github+json"])
    if code != 0:
        # Check the X-OAuth-Scopes header
        code, out, _ = run_command([gh, "api", "-i", "user"])
        if "workflow" in out.lower():
            return True
        return False

    return True


def authenticate_with_workflow_scope() -> bool:
    """Re-authenticate with workflow scope."""
    gh = get_gh_path()
    if not gh:
        print("❌ GitHub CLI (gh) not found.")
        print("   Install from: https://cli.github.com/")
        return False

    print("🔐 Authenticating with GitHub (workflow scope required)...")
    print("   This will open a browser for authentication.")
    print()

    # Run interactive auth with workflow scope
    cmd = [gh, "auth", "login", "-s", "workflow", "-w"]
    code, _, err = run_command(cmd)

    if code != 0:
        print(f"❌ Authentication failed: {err}")
        return False

    print("✅ Authentication successful with workflow scope!")
    return True


def get_staged_workflow_files() -> list[str]:
    """Get list of staged workflow files."""
    code, out, _ = run_command(["git", "diff", "--cached", "--name-only"])
    if code != 0:
        return []

    return [f for f in out.strip().split("\n") if f.startswith(".github/workflows/")]


def get_modified_workflow_files() -> list[str]:
    """Get list of modified (unstaged) workflow files."""
    code, out, _ = run_command(["git", "status", "--porcelain"])
    if code != 0:
        return []

    files = []
    for line in out.strip().split("\n"):
        if not line:
            continue
        status = line[:2]
        filepath = line[3:]
        if filepath.startswith(".github/workflows/"):
            files.append(filepath)
    return files


def push_with_retry() -> bool:
    """Attempt to push, handling workflow scope errors."""
    print("📤 Pushing to remote...")

    code, out, err = run_command(["git", "push"])

    if code == 0:
        print("✅ Push successful!")
        return True

    if "workflow" in err.lower() and "scope" in err.lower():
        print("⚠️  Push failed - workflow scope required for workflow files")
        print()

        response = input("🔐 Re-authenticate with workflow scope? [Y/n]: ").strip().lower()
        if response in ("", "y", "yes"):
            if authenticate_with_workflow_scope():
                print()
                print("📤 Retrying push...")
                code, _, err = run_command(["git", "push"])
                if code == 0:
                    print("✅ Push successful!")
                    return True
                else:
                    print(f"❌ Push still failed: {err}")
                    return False

    print(f"❌ Push failed: {err}")
    return False


def main():
    import argparse
    parser = argparse.ArgumentParser(description="SLATE Workflow Push Helper")
    parser.add_argument("--check", action="store_true", help="Check workflow scope status")
    parser.add_argument("--auth", action="store_true", help="Re-authenticate with workflow scope")
    parser.add_argument("--push", action="store_true", help="Push changes (handles workflow scope)")
    args = parser.parse_args()

    if args.check:
        gh = get_gh_path()
        if gh:
            print(f"✅ GitHub CLI found: {gh}")
            if check_workflow_scope():
                print("✅ Workflow scope available")
            else:
                print("⚠️  Workflow scope may not be available")
                print("   Run: python slate/slate_workflow_push.py --auth")
        else:
            print("❌ GitHub CLI not found")
            print("   Install from: https://cli.github.com/")
        return

    if args.auth:
        authenticate_with_workflow_scope()
        return

    # Default: check for workflow files and push
    workflow_files = get_modified_workflow_files()
    if workflow_files:
        print(f"📁 Found {len(workflow_files)} modified workflow files:")
        for f in workflow_files[:5]:
            print(f"   - {f}")
        if len(workflow_files) > 5:
            print(f"   ... and {len(workflow_files) - 5} more")
        print()

    push_with_retry()


if __name__ == "__main__":
    main()
