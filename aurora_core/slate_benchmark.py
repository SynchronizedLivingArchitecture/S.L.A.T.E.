#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_benchmark [python]
# Author: COPILOT | Created: 2026-02-06T00:30:00Z | Modified: 2026-02-06T00:30:00Z
# Purpose: System benchmark for SLATE
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE Benchmark
===============
Run system benchmarks to check performance.

Usage:
    python aurora_core/slate_benchmark.py
    python aurora_core/slate_benchmark.py --json
"""

import argparse
import json
import sys
import time
from datetime import datetime


def benchmark_cpu_single():
    """Single-threaded CPU benchmark."""
    start = time.perf_counter()
    total = 0.0
    for i in range(1, 100001):
        total += i ** 0.5
    elapsed = time.perf_counter() - start
    return {"name": "cpu_single", "ops": 100000, "time_sec": round(elapsed, 4), "ops_per_sec": round(100000/elapsed, 0)}


def benchmark_memory():
    """Memory allocation benchmark."""
    start = time.perf_counter()
    data = []
    for i in range(1000):
        data.append(bytearray(10000))
    elapsed = time.perf_counter() - start
    del data
    return {"name": "memory_alloc", "ops": 1000, "time_sec": round(elapsed, 4), "mb_allocated": 10}


def benchmark_disk():
    """Disk I/O benchmark."""
    import tempfile
    from pathlib import Path
    
    start = time.perf_counter()
    with tempfile.TemporaryDirectory() as tmpdir:
        testfile = Path(tmpdir) / "benchmark.bin"
        data = b"x" * (1024 * 1024)  # 1 MB
        for _ in range(10):
            testfile.write_bytes(data)
            _ = testfile.read_bytes()
    elapsed = time.perf_counter() - start
    return {"name": "disk_io", "ops": 20, "time_sec": round(elapsed, 4), "mb_transferred": 20}


def benchmark_gpu():
    """GPU benchmark (if available)."""
    try:
        import torch
        if not torch.cuda.is_available():
            return {"name": "gpu", "available": False}
        
        device = torch.device("cuda")
        torch.cuda.synchronize()
        start = time.perf_counter()
        
        a = torch.randn(2000, 2000, device=device)
        b = torch.randn(2000, 2000, device=device)
        for _ in range(10):
            c = torch.matmul(a, b)
        
        torch.cuda.synchronize()
        elapsed = time.perf_counter() - start
        
        return {
            "name": "gpu_matmul",
            "available": True,
            "device": torch.cuda.get_device_name(0),
            "ops": 10,
            "time_sec": round(elapsed, 4),
            "gflops": round((10 * 2 * 2000**3) / elapsed / 1e9, 2)
        }
    except ImportError:
        return {"name": "gpu", "available": False, "reason": "PyTorch not installed"}
    except Exception as e:
        return {"name": "gpu", "available": False, "error": str(e)}


def run_benchmarks():
    """Run all benchmarks."""
    results = {
        "timestamp": datetime.now().isoformat(),
        "benchmarks": []
    }
    
    print("Running benchmarks...")
    
    print("  [1/4] CPU single-threaded...")
    results["benchmarks"].append(benchmark_cpu_single())
    
    print("  [2/4] Memory allocation...")
    results["benchmarks"].append(benchmark_memory())
    
    print("  [3/4] Disk I/O...")
    results["benchmarks"].append(benchmark_disk())
    
    print("  [4/4] GPU compute...")
    results["benchmarks"].append(benchmark_gpu())
    
    return results


def print_results(results: dict):
    """Print benchmark results."""
    print()
    print("=" * 50)
    print("  S.L.A.T.E. Benchmark Results")
    print("=" * 50)
    print()
    
    for b in results["benchmarks"]:
        name = b["name"]
        if name == "cpu_single":
            print(f"  CPU:    {b['ops_per_sec']:,.0f} ops/sec ({b['time_sec']}s)")
        elif name == "memory_alloc":
            print(f"  Memory: {b['mb_allocated']} MB in {b['time_sec']}s")
        elif name == "disk_io":
            print(f"  Disk:   {b['mb_transferred']} MB in {b['time_sec']}s")
        elif name == "gpu_matmul" and b.get("available"):
            print(f"  GPU:    {b['gflops']} GFLOPS on {b['device']}")
        elif name == "gpu" and not b.get("available"):
            print(f"  GPU:    Not available")
    
    print()
    print("=" * 50)
    print()


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="SLATE Benchmark")
    parser.add_argument("--json", action="store_true", help="JSON output")
    args = parser.parse_args()
    
    results = run_benchmarks()
    
    if args.json:
        print(json.dumps(results, indent=2))
    else:
        print_results(results)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
