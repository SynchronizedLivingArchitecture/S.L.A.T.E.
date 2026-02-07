#!/usr/bin/env python3
# Modified: 2026-02-07T15:30:00Z | Author: Claude | Change: Intelligent AI task scheduler for sequenced execution
"""
SLATE AI Task Scheduler
========================

Intelligently schedules and sequences AI tasks across the local GPU infrastructure
to maximize throughput and minimize context switching overhead.

Features:
- Task queue with priority-based scheduling
- GPU-aware task placement (dual RTX 5070 Ti)
- Model warmup optimization (keeps hot models loaded)
- Batch processing for similar task types
- Dependency-aware sequencing
- Rate limiting to prevent GPU memory exhaustion

Usage:
    python slate/slate_ai_scheduler.py --status          # Show scheduler status
    python slate/slate_ai_scheduler.py --queue           # View task queue
    python slate/slate_ai_scheduler.py --run             # Run scheduled tasks
    python slate/slate_ai_scheduler.py --schedule        # Generate optimal schedule
    python slate/slate_ai_scheduler.py --add "task"      # Add task to queue
"""

import argparse
import json
import subprocess
import sys
import time
import threading
import urllib.request
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Optional
from queue import PriorityQueue
import heapq

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

# ═══════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════

OLLAMA_URL = "http://127.0.0.1:11434"
STATE_FILE = WORKSPACE_ROOT / ".slate_scheduler_state.json"
QUEUE_FILE = WORKSPACE_ROOT / ".slate_task_queue.json"

# GPU configuration for dual RTX 5070 Ti
GPU_CONFIG = {
    0: {
        "name": "RTX 5070 Ti (Primary)",
        "vram_mb": 16384,
        "max_concurrent": 2,
        "preferred_tasks": ["code_generation", "code_review", "analysis"],
    },
    1: {
        "name": "RTX 5070 Ti (Secondary)",
        "vram_mb": 16384,
        "max_concurrent": 2,
        "preferred_tasks": ["embedding", "classification", "summarization", "quick"],
    },
}

# Model VRAM requirements (approximate MB)
MODEL_VRAM = {
    "mistral-nemo": 8000,
    "mistral-nemo:latest": 8000,
    "llama3.2:3b": 3000,
    "llama3.2": 3000,
    "phi:latest": 2000,
    "phi": 2000,
    "codellama:13b": 10000,
    "nomic-embed-text:latest": 500,
    "slate-custom:latest": 8000,
    "slate-coder:latest": 10000,
    "slate-fast:latest": 3000,
    "slate-planner:latest": 6000,
}

# Task type to model mapping
TASK_MODELS = {
    "code_generation": ["slate-coder:latest", "mistral-nemo"],
    "code_review": ["slate-coder:latest", "mistral-nemo"],
    "analysis": ["slate-planner:latest", "mistral-nemo"],
    "documentation": ["mistral-nemo", "llama3.2"],
    "embedding": ["nomic-embed-text:latest"],
    "classification": ["slate-fast:latest", "llama3.2:3b"],
    "summarization": ["slate-fast:latest", "llama3.2:3b"],
    "planning": ["slate-planner:latest", "mistral-nemo"],
    "quick": ["slate-fast:latest", "phi:latest"],
    "training": ["mistral-nemo"],  # Training uses base models
    "general": ["slate-custom:latest", "mistral-nemo"],
}

# Task priorities (lower = higher priority)
TASK_PRIORITY = {
    "training": 1,       # Training runs first
    "embedding": 2,      # Index updates
    "code_review": 3,    # PR reviews
    "code_generation": 4,
    "analysis": 5,
    "planning": 6,
    "documentation": 7,
    "classification": 8,
    "summarization": 9,
    "quick": 10,
    "general": 11,
}


# ═══════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════

class TaskStatus(Enum):
    PENDING = "pending"
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass(order=True)
class AITask:
    """An AI task to be scheduled."""
    priority: int
    task_id: str = field(compare=False)
    task_type: str = field(compare=False)
    description: str = field(compare=False)
    payload: dict = field(default_factory=dict, compare=False)
    status: TaskStatus = field(default=TaskStatus.PENDING, compare=False)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat(), compare=False)
    started_at: Optional[str] = field(default=None, compare=False)
    completed_at: Optional[str] = field(default=None, compare=False)
    assigned_gpu: Optional[int] = field(default=None, compare=False)
    assigned_model: Optional[str] = field(default=None, compare=False)
    result: Optional[str] = field(default=None, compare=False)
    error: Optional[str] = field(default=None, compare=False)
    dependencies: list = field(default_factory=list, compare=False)

    def to_dict(self) -> dict:
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "description": self.description,
            "payload": self.payload,
            "status": self.status.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "assigned_gpu": self.assigned_gpu,
            "assigned_model": self.assigned_model,
            "result": self.result,
            "error": self.error,
            "dependencies": self.dependencies,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "AITask":
        return cls(
            priority=data.get("priority", 10),
            task_id=data.get("task_id", ""),
            task_type=data.get("task_type", "general"),
            description=data.get("description", ""),
            payload=data.get("payload", {}),
            status=TaskStatus(data.get("status", "pending")),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            assigned_gpu=data.get("assigned_gpu"),
            assigned_model=data.get("assigned_model"),
            result=data.get("result"),
            error=data.get("error"),
            dependencies=data.get("dependencies", []),
        )


@dataclass
class GPUState:
    """Current state of a GPU."""
    gpu_id: int
    name: str
    vram_total_mb: int
    vram_used_mb: int = 0
    active_tasks: int = 0
    loaded_models: list = field(default_factory=list)
    available: bool = True


# ═══════════════════════════════════════════════════════════════════════
# OLLAMA CLIENT
# ═══════════════════════════════════════════════════════════════════════

class OllamaClient:
    """Client for Ollama API."""

    def __init__(self):
        self.base_url = OLLAMA_URL

    def _request(self, path: str, data: dict | None = None, timeout: int = 120) -> dict:
        url = f"{self.base_url}{path}"
        if data:
            body = json.dumps(data).encode("utf-8")
            req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
        else:
            req = urllib.request.Request(url)
        resp = urllib.request.urlopen(req, timeout=timeout)
        return json.loads(resp.read().decode("utf-8"))

    def is_running(self) -> bool:
        try:
            self._request("/api/tags", timeout=3)
            return True
        except Exception:
            return False

    def list_models(self) -> list[str]:
        try:
            data = self._request("/api/tags", timeout=5)
            return [m.get("name", "") for m in data.get("models", [])]
        except Exception:
            return []

    def running_models(self) -> list[dict]:
        try:
            data = self._request("/api/ps", timeout=5)
            return data.get("models", [])
        except Exception:
            return []

    def generate(self, model: str, prompt: str, system: str = "",
                 temperature: float = 0.7, max_tokens: int = 2048) -> dict:
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": "24h",
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        if system:
            data["system"] = system
        return self._request("/api/generate", data, timeout=300)


# ═══════════════════════════════════════════════════════════════════════
# AI SCHEDULER
# ═══════════════════════════════════════════════════════════════════════

class AIScheduler:
    """Intelligent scheduler for AI tasks."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.ollama = OllamaClient()
        self.task_queue: list[AITask] = []
        self.completed_tasks: list[AITask] = []
        self.gpu_states: dict[int, GPUState] = {}
        self.state = self._load_state()
        self._load_queue()
        self._init_gpu_states()
        self._task_counter = self.state.get("task_counter", 0)

    def _load_state(self) -> dict:
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "task_counter": 0,
            "total_executed": 0,
            "total_failed": 0,
            "last_run": None,
            "model_usage": {},
        }

    def _save_state(self):
        self.state["task_counter"] = self._task_counter
        STATE_FILE.write_text(json.dumps(self.state, indent=2, default=str), encoding="utf-8")

    def _load_queue(self):
        if QUEUE_FILE.exists():
            try:
                data = json.loads(QUEUE_FILE.read_text(encoding="utf-8"))
                self.task_queue = [AITask.from_dict(t) for t in data.get("pending", [])]
                self.completed_tasks = [AITask.from_dict(t) for t in data.get("completed", [])]
            except Exception:
                pass

    def _save_queue(self):
        data = {
            "pending": [t.to_dict() for t in self.task_queue],
            "completed": [t.to_dict() for t in self.completed_tasks[-100:]],  # Keep last 100
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        QUEUE_FILE.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")

    def _init_gpu_states(self):
        """Initialize GPU state tracking."""
        for gpu_id, config in GPU_CONFIG.items():
            self.gpu_states[gpu_id] = GPUState(
                gpu_id=gpu_id,
                name=config["name"],
                vram_total_mb=config["vram_mb"],
            )
        self._update_gpu_states()

    def _update_gpu_states(self):
        """Update GPU states from nvidia-smi."""
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=index,memory.used,memory.total", "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode == 0:
                for line in result.stdout.strip().split('\n'):
                    parts = [p.strip() for p in line.split(',')]
                    if len(parts) >= 3:
                        gpu_id = int(parts[0])
                        if gpu_id in self.gpu_states:
                            self.gpu_states[gpu_id].vram_used_mb = int(float(parts[1]))
                            self.gpu_states[gpu_id].vram_total_mb = int(float(parts[2]))
        except Exception:
            pass

        # Update loaded models
        running_models = self.ollama.running_models()
        for gpu_state in self.gpu_states.values():
            gpu_state.loaded_models = [m.get("name") for m in running_models]

    def add_task(self, task_type: str, description: str, payload: dict = None,
                 dependencies: list = None) -> AITask:
        """Add a new task to the queue."""
        self._task_counter += 1
        priority = TASK_PRIORITY.get(task_type, 10)

        task = AITask(
            priority=priority,
            task_id=f"task_{self._task_counter:05d}",
            task_type=task_type,
            description=description,
            payload=payload or {},
            dependencies=dependencies or [],
        )

        heapq.heappush(self.task_queue, task)
        self._save_queue()
        self._save_state()

        return task

    def get_best_gpu(self, task_type: str, required_vram: int = 0) -> Optional[int]:
        """Find the best GPU for a task."""
        self._update_gpu_states()

        candidates = []
        for gpu_id, state in self.gpu_states.items():
            config = GPU_CONFIG[gpu_id]

            # Check if task type is preferred on this GPU
            is_preferred = task_type in config.get("preferred_tasks", [])

            # Check VRAM availability
            available_vram = state.vram_total_mb - state.vram_used_mb
            if available_vram < required_vram:
                continue

            # Check concurrent task limit
            if state.active_tasks >= config.get("max_concurrent", 2):
                continue

            # Score: prefer preferred GPUs, then by available VRAM
            score = (0 if is_preferred else 100) + (1000 - available_vram // 100)
            candidates.append((score, gpu_id))

        if candidates:
            candidates.sort()
            return candidates[0][1]
        return None

    def get_best_model(self, task_type: str, available_models: list[str]) -> Optional[str]:
        """Find the best model for a task type."""
        preferred = TASK_MODELS.get(task_type, ["mistral-nemo"])

        for model in preferred:
            if model in available_models:
                return model

        # Fall back to any available model
        if available_models:
            return available_models[0]
        return None

    def generate_schedule(self) -> list[dict]:
        """Generate an optimal execution schedule."""
        schedule = []
        available_models = self.ollama.list_models()

        # Group tasks by type for batch processing
        task_groups: dict[str, list[AITask]] = {}
        for task in self.task_queue:
            if task.status == TaskStatus.PENDING:
                task_groups.setdefault(task.task_type, []).append(task)

        # Sort groups by priority
        sorted_types = sorted(task_groups.keys(), key=lambda t: TASK_PRIORITY.get(t, 10))

        for task_type in sorted_types:
            tasks = task_groups[task_type]
            model = self.get_best_model(task_type, available_models)
            gpu = self.get_best_gpu(task_type, MODEL_VRAM.get(model, 5000))

            schedule.append({
                "task_type": task_type,
                "task_count": len(tasks),
                "model": model,
                "gpu": gpu,
                "estimated_vram_mb": MODEL_VRAM.get(model, 5000),
                "task_ids": [t.task_id for t in tasks],
            })

        return schedule

    def run_task(self, task: AITask) -> bool:
        """Execute a single task."""
        task.status = TaskStatus.RUNNING
        task.started_at = datetime.now(timezone.utc).isoformat()
        self._save_queue()

        try:
            available_models = self.ollama.list_models()
            model = self.get_best_model(task.task_type, available_models)

            if not model:
                task.status = TaskStatus.FAILED
                task.error = "No suitable model available"
                return False

            task.assigned_model = model
            gpu = self.get_best_gpu(task.task_type, MODEL_VRAM.get(model, 5000))
            task.assigned_gpu = gpu

            # Build prompt
            system_prompt = f"You are SLATE AI assistant. Task type: {task.task_type}"
            prompt = task.description
            if task.payload:
                prompt += f"\n\nContext:\n{json.dumps(task.payload, indent=2)}"

            # Execute
            result = self.ollama.generate(model, prompt, system=system_prompt)

            task.result = result.get("response", "")
            task.status = TaskStatus.COMPLETED
            task.completed_at = datetime.now(timezone.utc).isoformat()

            # Update stats
            self.state["total_executed"] = self.state.get("total_executed", 0) + 1
            model_usage = self.state.setdefault("model_usage", {})
            model_usage[model] = model_usage.get(model, 0) + 1

            return True

        except Exception as e:
            task.status = TaskStatus.FAILED
            task.error = str(e)
            task.completed_at = datetime.now(timezone.utc).isoformat()
            self.state["total_failed"] = self.state.get("total_failed", 0) + 1
            return False

        finally:
            self._save_queue()
            self._save_state()

    def run_scheduled(self, max_tasks: int = 10) -> dict:
        """Run scheduled tasks in optimal order."""
        print()
        print("=" * 70)
        print("  SLATE AI Scheduler - Running Tasks")
        print("=" * 70)
        print()

        if not self.ollama.is_running():
            return {"success": False, "error": "Ollama not running"}

        executed = 0
        failed = 0

        # Sort queue by priority
        heapq.heapify(self.task_queue)

        while self.task_queue and executed < max_tasks:
            task = heapq.heappop(self.task_queue)

            if task.status != TaskStatus.PENDING:
                continue

            # Check dependencies
            if task.dependencies:
                deps_complete = all(
                    any(c.task_id == dep_id and c.status == TaskStatus.COMPLETED
                        for c in self.completed_tasks)
                    for dep_id in task.dependencies
                )
                if not deps_complete:
                    heapq.heappush(self.task_queue, task)  # Re-queue
                    continue

            print(f"  [{executed + 1}] Running: {task.task_type} - {task.description[:50]}...")

            success = self.run_task(task)
            self.completed_tasks.append(task)

            if success:
                executed += 1
                print(f"       [OK] Completed with {task.assigned_model} on GPU {task.assigned_gpu}")
            else:
                failed += 1
                print(f"       [!] Failed: {task.error}")

        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        self._save_state()
        self._save_queue()

        print()
        print(f"  Executed: {executed}, Failed: {failed}, Remaining: {len(self.task_queue)}")
        print("=" * 70)

        return {
            "success": True,
            "executed": executed,
            "failed": failed,
            "remaining": len(self.task_queue),
        }

    def print_status(self):
        """Print scheduler status."""
        print()
        print("=" * 70)
        print("  SLATE AI Scheduler Status")
        print("=" * 70)
        print()

        # Ollama status
        if self.ollama.is_running():
            models = self.ollama.list_models()
            print(f"  Ollama: Running ({len(models)} models)")
        else:
            print("  Ollama: NOT RUNNING")
            return

        # GPU status
        self._update_gpu_states()
        print()
        print("  GPU Status:")
        for gpu_id, state in self.gpu_states.items():
            used_pct = (state.vram_used_mb / state.vram_total_mb * 100) if state.vram_total_mb else 0
            print(f"    GPU {gpu_id}: {state.vram_used_mb}MB / {state.vram_total_mb}MB ({used_pct:.1f}% used)")

        # Queue status
        print()
        print("  Task Queue:")
        pending = len([t for t in self.task_queue if t.status == TaskStatus.PENDING])
        print(f"    Pending: {pending}")
        print(f"    Completed: {len(self.completed_tasks)}")
        print(f"    Total executed: {self.state.get('total_executed', 0)}")
        print(f"    Total failed: {self.state.get('total_failed', 0)}")
        print(f"    Last run: {self.state.get('last_run', 'Never')}")

        # Model usage
        if self.state.get("model_usage"):
            print()
            print("  Model Usage:")
            for model, count in sorted(self.state["model_usage"].items(), key=lambda x: -x[1]):
                print(f"    {model}: {count} tasks")

        print()
        print("=" * 70)

    def print_queue(self):
        """Print current task queue."""
        print()
        print("=" * 70)
        print("  SLATE AI Task Queue")
        print("=" * 70)
        print()

        if not self.task_queue:
            print("  Queue is empty")
        else:
            print(f"  {'ID':<15} {'Type':<18} {'Priority':<10} {'Status':<12} Description")
            print(f"  {'-'*15} {'-'*18} {'-'*10} {'-'*12} {'-'*30}")
            for task in sorted(self.task_queue, key=lambda t: t.priority):
                desc = task.description[:30] + "..." if len(task.description) > 30 else task.description
                print(f"  {task.task_id:<15} {task.task_type:<18} {task.priority:<10} {task.status.value:<12} {desc}")

        print()
        print("=" * 70)


# ═══════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="SLATE AI Task Scheduler")
    parser.add_argument("--status", action="store_true", help="Show scheduler status")
    parser.add_argument("--queue", action="store_true", help="View task queue")
    parser.add_argument("--run", action="store_true", help="Run scheduled tasks")
    parser.add_argument("--schedule", action="store_true", help="Generate optimal schedule")
    parser.add_argument("--add", type=str, help="Add task to queue (format: type:description)")
    parser.add_argument("--max-tasks", type=int, default=10, help="Max tasks to run")
    parser.add_argument("--json", action="store_true", help="Output as JSON")

    args = parser.parse_args()
    scheduler = AIScheduler()

    if args.add:
        # Parse task: type:description
        if ":" in args.add:
            task_type, description = args.add.split(":", 1)
        else:
            task_type = "general"
            description = args.add

        task = scheduler.add_task(task_type.strip(), description.strip())
        if args.json:
            print(json.dumps(task.to_dict(), indent=2))
        else:
            print(f"Added task: {task.task_id}")

    elif args.run:
        result = scheduler.run_scheduled(max_tasks=args.max_tasks)
        if args.json:
            print(json.dumps(result, indent=2))

    elif args.schedule:
        schedule = scheduler.generate_schedule()
        if args.json:
            print(json.dumps(schedule, indent=2))
        else:
            print("\nOptimal Schedule:")
            for item in schedule:
                print(f"  {item['task_type']}: {item['task_count']} tasks -> {item['model']} on GPU {item['gpu']}")

    elif args.queue:
        if args.json:
            print(json.dumps([t.to_dict() for t in scheduler.task_queue], indent=2))
        else:
            scheduler.print_queue()

    else:
        scheduler.print_status()


if __name__ == "__main__":
    main()
