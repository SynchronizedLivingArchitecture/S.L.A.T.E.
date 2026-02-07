#!/usr/bin/env python3
"""
SLATE Multi-Runner Coordinator - Manage multiple parallel runners.

Coordinates multiple GitHub Actions runners working as a team,
distributing tasks based on resource requirements and availability.

Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Scale to 50-runner capacity
"""

import json
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any
import threading

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_runner_benchmark import RunnerBenchmark  # noqa: E402


@dataclass
class RunnerInstance:
    """Individual runner instance."""
    id: str
    name: str
    profile: str
    gpu_id: int | None
    status: str = "idle"  # idle, running, error
    current_task: str | None = None
    started_at: datetime | None = None
    tasks_completed: int = 0


@dataclass
class MultiRunnerConfig:
    """Configuration for multi-runner setup."""
    runners: list[RunnerInstance] = field(default_factory=list)
    max_parallel_workflows: int = 8
    task_timeout_minutes: int = 30
    gpu_reservation: dict[int, list[str]] = field(default_factory=dict)


class MultiRunnerCoordinator:
    """Coordinates multiple runners for parallel task execution."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.config_path = self.workspace / ".slate_runners.json"
        self.config: MultiRunnerConfig | None = None
        self.benchmark = RunnerBenchmark()
        self._lock = threading.Lock()

    def initialize(self, use_optimal: bool = True) -> MultiRunnerConfig:
        """Initialize multi-runner configuration."""
        self.benchmark.benchmark_all()

        if use_optimal:
            optimal = self.benchmark.results["optimal"]
            config = self._create_from_optimal(optimal)
        else:
            config = self._create_minimal()

        self.config = config
        self._save_config()
        return config

    def _create_from_optimal(self, optimal: dict) -> MultiRunnerConfig:
        """Create runner config from optimal benchmark results."""
        runners = []
        runner_id = 0

        for cfg in optimal["configuration"]:
            gpu_id = cfg["gpu"] if isinstance(cfg["gpu"], int) else None
            profile = cfg["profile"]
            count = cfg["count"]

            for i in range(count):
                runner_id += 1
                name = f"slate-{profile.replace('_', '-')}-{runner_id:02d}"
                runners.append(RunnerInstance(
                    id=f"runner-{runner_id:03d}",
                    name=name,
                    profile=profile,
                    gpu_id=gpu_id,
                ))

        # Build GPU reservation map
        gpu_reservation: dict[int, list[str]] = {}
        for runner in runners:
            if runner.gpu_id is not None:
                if runner.gpu_id not in gpu_reservation:
                    gpu_reservation[runner.gpu_id] = []
                gpu_reservation[runner.gpu_id].append(runner.id)

        return MultiRunnerConfig(
            runners=runners,
            max_parallel_workflows=optimal["parallel_workflows"],
            gpu_reservation=gpu_reservation,
        )

    def _create_minimal(self) -> MultiRunnerConfig:
        """Create minimal 2-runner configuration."""
        return MultiRunnerConfig(
            runners=[
                RunnerInstance(id="runner-001", name="slate-primary", profile="standard", gpu_id=0),
                RunnerInstance(id="runner-002", name="slate-secondary", profile="light", gpu_id=1),
            ],
            max_parallel_workflows=2,
        )

    def _save_config(self) -> None:
        """Save configuration to disk."""
        if not self.config:
            return

        data = {
            "runners": [
                {
                    "id": r.id,
                    "name": r.name,
                    "profile": r.profile,
                    "gpu_id": r.gpu_id,
                    "status": r.status,
                    "current_task": r.current_task,
                    "tasks_completed": r.tasks_completed,
                }
                for r in self.config.runners
            ],
            "max_parallel_workflows": self.config.max_parallel_workflows,
            "gpu_reservation": {str(k): v for k, v in self.config.gpu_reservation.items()},
            "updated_at": datetime.now().isoformat(),
        }

        with open(self.config_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

    def _load_config(self) -> MultiRunnerConfig | None:
        """Load configuration from disk."""
        if not self.config_path.exists():
            return None

        with open(self.config_path, encoding="utf-8") as f:
            data = json.load(f)

        runners = [
            RunnerInstance(
                id=r["id"],
                name=r["name"],
                profile=r["profile"],
                gpu_id=r.get("gpu_id"),
                status=r.get("status", "idle"),
                current_task=r.get("current_task"),
                tasks_completed=r.get("tasks_completed", 0),
            )
            for r in data["runners"]
        ]

        gpu_reservation = {int(k): v for k, v in data.get("gpu_reservation", {}).items()}

        self.config = MultiRunnerConfig(
            runners=runners,
            max_parallel_workflows=data.get("max_parallel_workflows", 4),
            gpu_reservation=gpu_reservation,
        )
        return self.config

    def get_available_runners(self, profile: str | None = None) -> list[RunnerInstance]:
        """Get list of idle runners, optionally filtered by profile."""
        if not self.config:
            self._load_config() or self.initialize()

        available = [r for r in self.config.runners if r.status == "idle"]

        if profile:
            available = [r for r in available if r.profile == profile]

        return available

    def assign_task(self, task_id: str, profile: str | None = None) -> RunnerInstance | None:
        """Assign a task to an available runner."""
        with self._lock:
            available = self.get_available_runners(profile)
            if not available:
                return None

            # Pick best runner (prefer GPU if available for GPU tasks)
            runner = available[0]
            runner.status = "running"
            runner.current_task = task_id
            runner.started_at = datetime.now()

            self._save_config()
            return runner

    def complete_task(self, runner_id: str, success: bool = True) -> None:
        """Mark a task as complete and free the runner."""
        with self._lock:
            if not self.config:
                return

            for runner in self.config.runners:
                if runner.id == runner_id:
                    runner.status = "idle" if success else "error"
                    runner.current_task = None
                    runner.started_at = None
                    if success:
                        runner.tasks_completed += 1
                    break

            self._save_config()

    def get_status(self) -> dict[str, Any]:
        """Get current multi-runner status."""
        if not self.config:
            self._load_config() or self.initialize()

        running = [r for r in self.config.runners if r.status == "running"]
        idle = [r for r in self.config.runners if r.status == "idle"]
        error = [r for r in self.config.runners if r.status == "error"]

        return {
            "total_runners": len(self.config.runners),
            "running": len(running),
            "idle": len(idle),
            "error": len(error),
            "max_parallel": self.config.max_parallel_workflows,
            "gpu_distribution": {
                f"GPU {k}": len(v) for k, v in self.config.gpu_reservation.items()
            },
            "runners": [
                {
                    "id": r.id,
                    "name": r.name,
                    "profile": r.profile,
                    "gpu": r.gpu_id,
                    "status": r.status,
                    "task": r.current_task,
                    "completed": r.tasks_completed,
                }
                for r in self.config.runners
            ],
        }

    def print_status(self) -> None:
        """Print human-readable status."""
        status = self.get_status()

        print("=" * 60)
        print("  SLATE Multi-Runner Status")
        print("=" * 60)
        print()
        print(f"Total Runners: {status['total_runners']}")
        print(f"  Running: {status['running']}")
        print(f"  Idle:    {status['idle']}")
        print(f"  Error:   {status['error']}")
        print(f"Max Parallel: {status['max_parallel']}")
        print()

        if status["gpu_distribution"]:
            print("GPU Distribution:")
            for gpu, count in status["gpu_distribution"].items():
                print(f"  {gpu}: {count} runners")
            print()

        print("Runners:")
        print("-" * 60)
        print(f"  {'ID':<12} {'Name':<25} {'Profile':<12} {'GPU':<5} {'Status':<8}")
        print(f"  {'-'*12} {'-'*25} {'-'*12} {'-'*5} {'-'*8}")
        for r in status["runners"]:
            gpu_str = str(r["gpu"]) if r["gpu"] is not None else "-"
            print(f"  {r['id']:<12} {r['name']:<25} {r['profile']:<12} {gpu_str:<5} {r['status']:<8}")
        print()
        print("=" * 60)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Multi-Runner Coordinator")
    parser.add_argument("--init", action="store_true", help="Initialize runner configuration")
    parser.add_argument("--status", action="store_true", help="Show runner status")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--assign", type=str, help="Assign task to runner")
    parser.add_argument("--complete", type=str, help="Mark runner task complete")
    parser.add_argument("--minimal", action="store_true", help="Use minimal 2-runner config")
    parser.add_argument("--scale", type=int, help="Scale to target runner count (max 50)")
    args = parser.parse_args()

    coordinator = MultiRunnerCoordinator()

    if args.scale:
        target = min(args.scale, 50)  # Cap at 50 per capacity spec
        config = coordinator.initialize(use_optimal=True)
        # Adjust runner count to target
        if len(config.runners) < target:
            print(f"Scaling from {len(config.runners)} to {target} runners...")
            # Add light runners to fill gap
            for i in range(len(config.runners), target):
                config.runners.append(RunnerInstance(
                    id=f"runner-{i+1}",
                    name=f"slate-runner-{i+1}",
                    labels=["self-hosted", "slate", "light"],
                    profile="light",
                    gpu=None,
                ))
            coordinator._save_config(config)
        print(f"Scaled to {len(config.runners)} runners")
        coordinator.print_status()
    elif args.init:
        config = coordinator.initialize(use_optimal=not args.minimal)
        print(f"Initialized {len(config.runners)} runners")
        coordinator.print_status()
    elif args.assign:
        runner = coordinator.assign_task(args.assign)
        if runner:
            print(f"Assigned task '{args.assign}' to {runner.name}")
        else:
            print("No available runners")
    elif args.complete:
        coordinator.complete_task(args.complete)
        print(f"Completed task for runner {args.complete}")
    elif args.json:
        status = coordinator.get_status()
        print(json.dumps(status, indent=2, default=str))
    else:
        coordinator.print_status()


if __name__ == "__main__":
    main()
