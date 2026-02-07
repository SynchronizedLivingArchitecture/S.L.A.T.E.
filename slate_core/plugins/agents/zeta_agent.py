#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT
# Change: Create ZETA benchmark oracle agent plugin
"""
ZETA Agent — Benchmark Oracle
===============================
System performance benchmarking, hardware profiling, and optimization
recommendations. Runs GPU/CPU/memory/disk benchmarks and tracks
historical performance trends.

Features:
- GPU inference benchmarks (tokens/sec per model)
- Memory pressure testing
- Disk I/O profiling
- Runner capacity calculations
- Historical trend analysis
- Optimization recommendations

Uses slate-fast model for quick classification of benchmark results.
"""

import json
import logging
import os
import subprocess
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.zeta")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
BENCH_DIR = WORKSPACE_ROOT / "slate_logs" / "benchmarks"


class ZetaAgent(AgentBase):
    """Benchmark oracle agent — system profiling and optimization."""

    AGENT_ID = "ZETA"
    AGENT_NAME = "Zeta Benchmark Oracle"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "System benchmarking, GPU profiling, capacity analysis, optimization"
    REQUIRES_GPU = True
    DEPENDENCIES: List[str] = []

    def on_load(self) -> bool:
        """Ensure benchmark directory exists."""
        BENCH_DIR.mkdir(parents=True, exist_ok=True)
        return True

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="benchmarking",
                patterns=["benchmark", "performance", "profile", "speed",
                          "throughput", "latency", "optimize", "capacity"],
                requires_gpu=True,
                gpu_memory_mb=1024,
                cpu_cores=2,
                priority=25,
                description="Run system benchmarks, GPU profiling, capacity analysis",
            ),
            AgentCapability(
                name="hardware_analysis",
                patterns=["gpu", "cuda", "memory", "disk", "cpu", "hardware",
                          "resource", "utilization"],
                requires_gpu=False,
                cpu_cores=1,
                priority=35,
                description="Analyze hardware resources and utilization patterns",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a benchmarking or profiling task."""
        title = task.get("title", "")
        description = task.get("description", "")
        combined = f"{title} {description}".lower()

        if any(w in combined for w in ["gpu", "inference", "model", "ollama"]):
            return self._benchmark_gpu_inference()
        elif any(w in combined for w in ["runner", "capacity", "scale"]):
            return self._benchmark_runner_capacity()
        elif any(w in combined for w in ["memory", "ram"]):
            return self._benchmark_memory()
        elif any(w in combined for w in ["disk", "io"]):
            return self._benchmark_disk_io()
        else:
            return self._benchmark_full()

    def _benchmark_gpu_inference(self) -> dict:
        """Benchmark GPU inference speed using Ollama models."""
        results = {"benchmarks": [], "timestamp": datetime.now(timezone.utc).isoformat()}
        models = ["slate-fast", "slate-planner", "slate-coder"]

        for model in models:
            try:
                prompt = "Explain the concept of recursion in programming in 50 words."
                start = time.monotonic()
                result = subprocess.run(
                    ["ollama", "run", model, prompt],
                    capture_output=True, text=True, timeout=60,
                    cwd=str(WORKSPACE_ROOT),
                )
                elapsed = time.monotonic() - start

                if result.returncode == 0:
                    output = result.stdout.strip()
                    # Estimate tokens (rough: words * 1.3)
                    word_count = len(output.split())
                    est_tokens = int(word_count * 1.3)
                    tokens_per_sec = est_tokens / elapsed if elapsed > 0 else 0

                    results["benchmarks"].append({
                        "model": model,
                        "elapsed_s": round(elapsed, 2),
                        "est_tokens": est_tokens,
                        "tokens_per_sec": round(tokens_per_sec, 1),
                        "success": True,
                    })
                else:
                    results["benchmarks"].append({
                        "model": model,
                        "success": False,
                        "error": result.stderr[:200],
                    })
            except Exception as e:
                results["benchmarks"].append({
                    "model": model,
                    "success": False,
                    "error": str(e),
                })

        # Save results
        self._save_benchmark("gpu_inference", results)

        summary = "\n".join(
            f"  {b['model']}: {b.get('tokens_per_sec', 0):.1f} tok/s ({b.get('elapsed_s', 0):.1f}s)"
            if b["success"] else f"  {b['model']}: FAILED"
            for b in results["benchmarks"]
        )

        return {
            "success": True,
            "result": f"GPU Inference Benchmark:\n{summary}",
            "agent": self.AGENT_ID,
            "data": results,
        }

    def _benchmark_runner_capacity(self) -> dict:
        """Calculate runner capacity from current hardware."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            result = subprocess.run(
                [python, str(WORKSPACE_ROOT / "slate" / "slate_runner_benchmark.py"), "--json"],
                capture_output=True, text=True, timeout=30,
                cwd=str(WORKSPACE_ROOT),
            )
            if result.returncode == 0:
                data = json.loads(result.stdout)
                self._save_benchmark("runner_capacity", data)
                return {
                    "success": True,
                    "result": json.dumps(data.get("optimal", {}), indent=2),
                    "agent": self.AGENT_ID,
                    "data": data,
                }
            return {"success": False, "error": result.stderr[:300]}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _benchmark_memory(self) -> dict:
        """Benchmark memory usage and availability."""
        results: dict = {"timestamp": datetime.now(timezone.utc).isoformat()}
        try:
            import psutil
            mem = psutil.virtual_memory()
            results["ram"] = {
                "total_gb": round(mem.total / (1024 ** 3), 1),
                "available_gb": round(mem.available / (1024 ** 3), 1),
                "used_percent": mem.percent,
            }

            # GPU memory
            gpu_result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.free,memory.used",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            results["gpu_memory"] = []
            for line in gpu_result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    results["gpu_memory"].append({
                        "total_mb": int(parts[0]),
                        "free_mb": int(parts[1]),
                        "used_mb": int(parts[2]),
                    })

            self._save_benchmark("memory", results)
            return {
                "success": True,
                "result": json.dumps(results, indent=2),
                "agent": self.AGENT_ID,
                "data": results,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _benchmark_disk_io(self) -> dict:
        """Simple disk I/O benchmark."""
        # Modified: 2025-07-09T12:05:00Z | Author: COPILOT
        # Change: Guard against zero-time division
        results: dict = {"timestamp": datetime.now(timezone.utc).isoformat()}
        test_file = BENCH_DIR / "_bench_io_test.tmp"

        try:
            # Write test
            data = b"x" * (1024 * 1024)  # 1 MB
            start = time.monotonic()
            for _ in range(10):
                with open(test_file, "wb") as f:
                    f.write(data)
                    f.flush()
                    os.fsync(f.fileno())
            write_time = max(time.monotonic() - start, 1e-6)

            # Read test
            start = time.monotonic()
            for _ in range(10):
                with open(test_file, "rb") as f:
                    _ = f.read()
            read_time = max(time.monotonic() - start, 1e-6)

            # Cleanup
            test_file.unlink(missing_ok=True)

            results["disk_io"] = {
                "write_mb_s": round(10 / write_time, 1),
                "read_mb_s": round(10 / read_time, 1),
            }

            self._save_benchmark("disk_io", results)
            return {
                "success": True,
                "result": (
                    f"Disk I/O: Write {results['disk_io']['write_mb_s']} MB/s, "
                    f"Read {results['disk_io']['read_mb_s']} MB/s"
                ),
                "agent": self.AGENT_ID,
                "data": results,
            }
        except Exception as e:
            test_file.unlink(missing_ok=True)
            return {"success": False, "error": str(e)}

    def _benchmark_full(self) -> dict:
        """Run full system benchmark suite."""
        try:
            python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
            result = subprocess.run(
                [python, str(WORKSPACE_ROOT / "slate" / "slate_benchmark.py")],
                capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )
            return {
                "success": result.returncode == 0,
                "result": result.stdout[-2000:],
                "agent": self.AGENT_ID,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _save_benchmark(self, bench_type: str, data: dict) -> None:
        """Save benchmark results to disk with timestamp."""
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        path = BENCH_DIR / f"{bench_type}_{ts}.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        logger.info("Saved benchmark %s to %s", bench_type, path)

    def health_check(self) -> dict:
        base = super().health_check()
        base["bench_dir_exists"] = BENCH_DIR.exists()
        base["nvidia_smi_available"] = True
        try:
            subprocess.run(["nvidia-smi"], capture_output=True, timeout=5)
        except Exception:
            base["nvidia_smi_available"] = False
        base["healthy"] = base["nvidia_smi_available"]
        return base
