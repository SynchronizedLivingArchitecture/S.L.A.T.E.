#!/usr/bin/env python3
# Modified: 2026-02-06T01:00:00Z | Author: COPILOT | Change: Create security check script
"""
SLATE Security Checker
======================
Performs security audits on the SLATE codebase.
"""

import os
import re
import sys
from pathlib import Path

# Security requirements from memory/documentation
REQUIRED_BLOCKED = [
    "curl.exe", "Start-Sleep", "wget", "curl", "nc", "netcat", "rm", "sh", "bash"
]

TELEMETRY_PACKAGES = [
    "opentelemetry-api", "opentelemetry-sdk", "opentelemetry-exporter-otlp"
]

def check_shell_injection():
    """Check for shell=True in subprocess calls."""
    print("[1/4] Checking for shell injection vulnerabilities...")
    issues = []
    for root, _, files in os.walk("."):
        for file in files:
            if file.endswith(".py") and file != "slate_security.py":
                path = Path(root) / file
                try:
                    content = path.read_text()
                    if "shell=True" in content:
                        issues.append(f"{path}: Contains 'shell=True'")
                except Exception as e:
                    print(f"  Error reading {path}: {e}")

    if issues:
        for issue in issues:
            print(f"  ✗ {issue}")
        return False
    print("  ✓ No 'shell=True' found in Python files")
    return True

def check_blocked_commands():
    """Check if slate_terminal_monitor.py blocks required commands."""
    print("[2/4] Checking blocked commands in terminal monitor...")
    monitor_path = Path("aurora_core/slate_terminal_monitor.py")
    if not monitor_path.exists():
        print(f"  ✗ {monitor_path} not found")
        return False

    try:
        content = monitor_path.read_text()
        missing = []
        for cmd in REQUIRED_BLOCKED:
            if f'"{cmd}"' not in content and f"'{cmd}'" not in content:
                missing.append(cmd)

        if missing:
            print(f"  ✗ Missing blocked commands: {missing}")
            return False
        print("  ✓ All required commands are blocked")
        return True
    except Exception as e:
        print(f"  Error reading {monitor_path}: {e}")
        return False

def check_network_bindings():
    """Check for 0.0.0.0 bindings."""
    print("[3/4] Checking for non-local network bindings...")
    issues = []
    # Simple regex for 0.0.0.0
    pattern = re.compile(r"0\.0\.0\.0")

    for root, _, files in os.walk("."):
        if ".git" in root or "__pycache__" in root:
            continue
        for file in files:
            if file.endswith((".py", ".yaml", ".slate", ".md")) and file != "slate_security.py":
                path = Path(root) / file
                try:
                    content = path.read_text()
                    if pattern.search(content):
                        # Skip README and instructions if they mention it as a rule
                        if "README" in file or "instructions" in file:
                            if "dont" in content.lower() or "avoid" in content.lower():
                                continue
                        issues.append(f"{path}: Contains '0.0.0.0'")
                except Exception as e:
                    pass

    if issues:
        for issue in issues:
            print(f"  ✗ {issue}")
        return False
    print("  ✓ No '0.0.0.0' bindings found")
    return True

def check_telemetry():
    """Check for telemetry packages in requirements.txt."""
    print("[4/4] Checking for telemetry packages...")
    req_path = Path("requirements.txt")
    if not req_path.exists():
        print("  ○ requirements.txt not found")
        return True

    try:
        content = req_path.read_text()
        found = []
        for pkg in TELEMETRY_PACKAGES:
            if pkg in content:
                found.append(pkg)

        if found:
            print(f"  ! Found telemetry packages: {found} (Should be removed if not used)")
            return False
        print("  ✓ No telemetry packages found")
        return True
    except Exception as e:
        print(f"  Error reading {req_path}: {e}")
        return False

def main():
    print("\n" + "="*50)
    print("  S.L.A.T.E. Security Audit")
    print("="*50 + "\n")

    results = [
        check_shell_injection(),
        check_blocked_commands(),
        check_network_bindings(),
        check_telemetry()
    ]

    print("\n" + "="*50)
    if all(results):
        print("  PASSED: All security checks passed")
        return 0
    else:
        print("  FAILED: Security issues detected")
        return 1

if __name__ == "__main__":
    sys.exit(main())
