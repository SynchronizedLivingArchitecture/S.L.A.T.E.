#!/usr/bin/env python3
"""
SLATE Multi-Runner Benchmark - Determine optimal runner count per GPU.

Benchmarks system resources to calculate how many concurrent runners
can be supported based on GPU memory, CPU cores, and RAM.

Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Scale capacity cap from 20 to 50 runners
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# Resource requirements per runner type
RUNNER_PROFILES = {
    "light": {
        "name": "Light Runner",
        "description": "Linting, formatting, simple tests",
        "gpu_memory_mb": 0,
        "cpu_cores": 1,
        "ram_mb": 512,
        "examples": ["ruff check", "black --check", "mypy"],
    },
    "standard": {
        "name": "Standard Runner",
        "description": "Unit tests, SDK validation, security scans",
        "gpu_memory_mb": 0,
        "cpu_cores": 2,
        "ram_mb": 1024,
        "examples": ["pytest", "bandit", "sdk-validation"],
    },
    "gpu_light": {
        "name": "GPU Light Runner",
        "description": "Small model inference, embeddings",
        "gpu_memory_mb": 2048,
        "cpu_cores": 2,
        "ram_mb": 2048,
        "examples": ["embeddings", "small-llm", "classification"],
    },
    "gpu_heavy": {
        "name": "GPU Heavy Runner",
        "description": "Large model inference, training, benchmarks",
        "gpu_memory_mb": 8192,
        "cpu_cores": 4,
        "ram_mb": 8192,
        "examples": ["mistral-nemo", "fine-tuning", "full-benchmark"],
    },
    "gpu_max": {
        "name": "GPU Max Runner",
        "description": "Maximum GPU allocation for single large task",
        "gpu_memory_mb": 14000,
        "cpu_cores": 4,
        "ram_mb": 16384,
        "examples": ["large-model", "multi-gpu-training"],
    },
}


@dataclass
class SystemResources:
    """Current system resource availability."""
    gpu_count: int
    gpu_memory_total_mb: list[int]
    gpu_memory_free_mb: list[int]
    gpu_utilization: list[int]
    cpu_cores: int
    ram_total_mb: int
    ram_free_mb: int


@dataclass
class RunnerCapacity:
    """Calculated runner capacity."""
    profile: str
    max_total: int
    max_per_gpu: list[int]
    max_cpu_bound: int
    max_ram_bound: int
    limiting_factor: str


class RunnerBenchmark:
    """Benchmark system to determine optimal runner configuration."""

    def __init__(self):
        self.resources: SystemResources | None = None
        self.results: dict[str, Any] = {}

    def detect_resources(self) -> SystemResources:
        """Detect current system resources."""
        # GPU detection
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=memory.total,memory.free,utilization.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            gpu_lines = result.stdout.strip().split("\n")
            gpu_count = len(gpu_lines)
            gpu_memory_total = []
            gpu_memory_free = []
            gpu_utilization = []

            for line in gpu_lines:
                parts = [p.strip() for p in line.split(",")]
                gpu_memory_total.append(int(parts[0]))
                gpu_memory_free.append(int(parts[1]))
                gpu_utilization.append(int(parts[2]))
        except Exception:
            gpu_count = 0
            gpu_memory_total = []
            gpu_memory_free = []
            gpu_utilization = []

        # CPU detection
        import os
        cpu_cores = os.cpu_count() or 4

        # RAM detection
        try:
            import psutil
            mem = psutil.virtual_memory()
            ram_total_mb = mem.total // (1024 * 1024)
            ram_free_mb = mem.available // (1024 * 1024)
        except ImportError:
            # Fallback
            ram_total_mb = 32768
            ram_free_mb = 16384

        self.resources = SystemResources(
            gpu_count=gpu_count,
            gpu_memory_total_mb=gpu_memory_total,
            gpu_memory_free_mb=gpu_memory_free,
            gpu_utilization=gpu_utilization,
            cpu_cores=cpu_cores,
            ram_total_mb=ram_total_mb,
            ram_free_mb=ram_free_mb,
        )
        return self.resources

    def calculate_capacity(self, profile_id: str) -> RunnerCapacity:
        """Calculate runner capacity for a given profile."""
        if not self.resources:
            self.detect_resources()

        profile = RUNNER_PROFILES[profile_id]
        res = self.resources

        # GPU-based capacity (per GPU)
        max_per_gpu = []
        if profile["gpu_memory_mb"] > 0 and res.gpu_count > 0:
            for free_mb in res.gpu_memory_free_mb:
                count = free_mb // profile["gpu_memory_mb"]
                max_per_gpu.append(count)
            max_gpu_total = sum(max_per_gpu)
        else:
            max_per_gpu = [999] * max(res.gpu_count, 1)  # Unlimited if no GPU needed
            max_gpu_total = 999

        # CPU-based capacity
        max_cpu = res.cpu_cores // profile["cpu_cores"]

        # RAM-based capacity
        max_ram = res.ram_free_mb // profile["ram_mb"]

        # Determine limiting factor
        limits = [
            ("gpu", max_gpu_total),
            ("cpu", max_cpu),
            ("ram", max_ram),
        ]
        limiting = min(limits, key=lambda x: x[1])
        max_total = limiting[1]

        return RunnerCapacity(
            profile=profile_id,
            max_total=min(max_total, 50),  # Cap at 50 runners
            max_per_gpu=max_per_gpu,
            max_cpu_bound=max_cpu,
            max_ram_bound=max_ram,
            limiting_factor=limiting[0],
        )

    def benchmark_all(self) -> dict[str, Any]:
        """Run full benchmark across all profiles."""
        self.detect_resources()

        capacities = {}
        for profile_id in RUNNER_PROFILES:
            cap = self.calculate_capacity(profile_id)
            capacities[profile_id] = {
                "name": RUNNER_PROFILES[profile_id]["name"],
                "max_runners": cap.max_total,
                "per_gpu": cap.max_per_gpu,
                "cpu_limit": cap.max_cpu_bound,
                "ram_limit": cap.max_ram_bound,
                "limiting_factor": cap.limiting_factor,
            }

        # Optimal configuration recommendation
        optimal = self._recommend_optimal()

        self.results = {
            "system": {
                "gpu_count": self.resources.gpu_count,
                "gpu_memory_total_mb": self.resources.gpu_memory_total_mb,
                "gpu_memory_free_mb": self.resources.gpu_memory_free_mb,
                "gpu_utilization_percent": self.resources.gpu_utilization,
                "cpu_cores": self.resources.cpu_cores,
                "ram_total_mb": self.resources.ram_total_mb,
                "ram_free_mb": self.resources.ram_free_mb,
            },
            "capacities": capacities,
            "optimal": optimal,
        }
        return self.results

    def _recommend_optimal(self) -> dict[str, Any]:
        """Recommend optimal runner configuration."""
        res = self.resources

        # Strategy: Mix of runner types for maximum parallelism
        # Reserve 1 GPU for heavy tasks, use rest for light/standard

        if res.gpu_count >= 2:
            # Dual GPU: scaled to 50 runners with mixed profiles
            # GPU 0: heavy inference (1) + light (4)
            # GPU 1: light inference (6) + standard (4)
            # CPU-only: standard (10) + light (25)
            return {
                "strategy": "dual_gpu_scaled",
                "description": "50-runner config: GPU 0/1 for inference, CPU pool for parallelism",
                "configuration": [
                    {"gpu": 0, "profile": "gpu_heavy", "count": 1},
                    {"gpu": 0, "profile": "gpu_light", "count": 4},
                    {"gpu": 1, "profile": "gpu_light", "count": 6},
                    {"gpu": 1, "profile": "standard", "count": 4},
                    {"gpu": "cpu", "profile": "standard", "count": 10},
                    {"gpu": "cpu", "profile": "light", "count": 25},
                ],
                "total_runners": 50,
                "parallel_workflows": 8,
            }
        elif res.gpu_count == 1:
            return {
                "strategy": "single_gpu_balanced",
                "description": "Time-slice GPU between tasks",
                "configuration": [
                    {"gpu": 0, "profile": "gpu_light", "count": 4},
                    {"gpu": "cpu", "profile": "standard", "count": 4},
                    {"gpu": "cpu", "profile": "light", "count": 8},
                ],
                "total_runners": 16,
                "parallel_workflows": 3,
            }
        else:
            return {
                "strategy": "cpu_only",
                "description": "CPU-based runners only",
                "configuration": [
                    {"gpu": "cpu", "profile": "standard", "count": res.cpu_cores // 2},
                    {"gpu": "cpu", "profile": "light", "count": res.cpu_cores},
                ],
                "total_runners": res.cpu_cores + res.cpu_cores // 2,
                "parallel_workflows": 2,
            }

    def print_report(self) -> None:
        """Print human-readable benchmark report."""
        if not self.results:
            self.benchmark_all()

        print("=" * 60)
        print("  SLATE Multi-Runner Benchmark Report")
        print("=" * 60)
        print()

        # System resources
        sys_info = self.results["system"]
        print("System Resources:")
        print("-" * 40)
        print(f"  GPUs: {sys_info['gpu_count']}")
        for i, (total, free, util) in enumerate(zip(
            sys_info["gpu_memory_total_mb"],
            sys_info["gpu_memory_free_mb"],
            sys_info["gpu_utilization_percent"]
        )):
            print(f"    GPU {i}: {free:,} / {total:,} MB free ({util}% utilized)")
        print(f"  CPU Cores: {sys_info['cpu_cores']}")
        print(f"  RAM: {sys_info['ram_free_mb']:,} / {sys_info['ram_total_mb']:,} MB free")
        print()

        # Capacity by profile
        print("Runner Capacity by Profile:")
        print("-" * 40)
        print(f"  {'Profile':<20} {'Max':<6} {'Limit':<8} {'Per GPU'}")
        print(f"  {'-'*20} {'-'*6} {'-'*8} {'-'*15}")
        for profile_id, cap in self.results["capacities"].items():
            per_gpu_str = ", ".join(str(x) for x in cap["per_gpu"]) if cap["per_gpu"] else "N/A"
            print(f"  {cap['name']:<20} {cap['max_runners']:<6} {cap['limiting_factor']:<8} [{per_gpu_str}]")
        print()

        # Optimal recommendation
        opt = self.results["optimal"]
        print("Optimal Configuration:")
        print("-" * 40)
        print(f"  Strategy: {opt['strategy']}")
        print(f"  {opt['description']}")
        print(f"  Total Runners: {opt['total_runners']}")
        print(f"  Parallel Workflows: {opt['parallel_workflows']}")
        print()
        print("  Configuration:")
        for cfg in opt["configuration"]:
            print(f"    {cfg['gpu']}: {cfg['count']}x {cfg['profile']}")
        print()
        print("=" * 60)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Multi-Runner Benchmark")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--profile", type=str, help="Check specific profile capacity")
    args = parser.parse_args()

    benchmark = RunnerBenchmark()

    if args.profile:
        if args.profile not in RUNNER_PROFILES:
            print(f"Unknown profile: {args.profile}")
            print(f"Available: {', '.join(RUNNER_PROFILES.keys())}")
            sys.exit(1)
        benchmark.detect_resources()
        cap = benchmark.calculate_capacity(args.profile)
        if args.json:
            print(json.dumps({
                "profile": args.profile,
                "max_runners": cap.max_total,
                "per_gpu": cap.max_per_gpu,
                "limiting_factor": cap.limiting_factor,
            }, indent=2))
        else:
            print(f"{RUNNER_PROFILES[args.profile]['name']}: {cap.max_total} runners (limited by {cap.limiting_factor})")
    else:
        results = benchmark.benchmark_all()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            benchmark.print_report()


if __name__ == "__main__":
    main()
