#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_runtime [python]
# Author: COPILOT | Created: 2026-02-06T00:30:00Z
# Purpose: Runtime integration checker
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE Runtime Checker - Check all integrations and dependencies.

Usage:
    python aurora_core/slate_runtime.py --check-all
    python aurora_core/slate_runtime.py --json
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

def check_integration(name, check_fn, details_fn=None):
    try:
        status = check_fn()
        details = details_fn() if details_fn and status else None
        return {"name": name, "status": "active" if status else "inactive", "details": details}
    except Exception as e:
        return {"name": name, "status": "error", "error": str(e)}

def check_python(): return sys.version_info >= (3, 11)
def python_details(): return f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
def check_pytorch():
    try: import torch; return True
    except: return False
def pytorch_details():
    import torch
    cuda = f", CUDA {torch.version.cuda}" if torch.cuda.is_available() else ", CPU"
    return f"{torch.__version__}{cuda}"
def check_ollama():
    try: return subprocess.run(["ollama", "--version"], capture_output=True, timeout=5).returncode == 0
    except: return False
def check_gpu():
    try:
        r = subprocess.run(["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], capture_output=True, text=True, timeout=5)
        return r.returncode == 0 and r.stdout.strip()
    except: return False
def check_transformers():
    try: import transformers; return True
    except: return False
def check_venv(): return (Path.cwd() / ".venv").exists()

INTEGRATIONS = [
    ("Python 3.11+", check_python, python_details),
    ("Virtual Env", check_venv, None),
    ("NVIDIA GPU", check_gpu, None),
    ("PyTorch", check_pytorch, pytorch_details),
    ("Transformers", check_transformers, None),
    ("Ollama", check_ollama, None),
]

def check_all():
    results = {"timestamp": datetime.now().isoformat(), "integrations": []}
    for name, check_fn, details_fn in INTEGRATIONS:
        results["integrations"].append(check_integration(name, check_fn, details_fn))
    active = sum(1 for i in results["integrations"] if i["status"] == "active")
    results["summary"] = {"active": active, "total": len(results["integrations"])}
    return results

def print_results(results):
    print("\n" + "=" * 60)
    print("  S.L.A.T.E. Runtime Check")
    print("=" * 60 + "\n")
    for item in results["integrations"]:
        icon = "\u2713" if item["status"] == "active" else "\u25cb" if item["status"] == "inactive" else "\u2717"
        details = f" ({item['details']})" if item.get("details") else ""
        print(f"  {icon} {item['name']}{details}")
    s = results["summary"]
    print(f"\n  Summary: {s['active']}/{s['total']} integrations active")
    print("\n" + "=" * 60 + "\n")

def main():
    parser = argparse.ArgumentParser(description="SLATE Runtime Checker")
    parser.add_argument("--check-all", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    results = check_all()
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)
    return 0

if __name__ == "__main__":
    sys.exit(main())
