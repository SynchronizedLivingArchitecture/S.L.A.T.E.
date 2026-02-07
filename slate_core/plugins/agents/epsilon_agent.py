#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create EPSILON spec-weaver agent plugin
"""
EPSILON Agent — Spec Weaver
=============================
Generates structured specifications, architecture docs, and capacity
planning documents. Analyzes codebase to produce machine-readable specs
that feed back into task generation and roadmap planning.

Spec Types:
- Architecture specs (system component maps)
- Capacity specs (agents, runners, GPU allocation)
- API specs (endpoint documentation)
- Security specs (threat models, compliance checklists)

Uses slate-planner model for structured reasoning and file I/O
for persisting specs to docs/specs/.
"""

import json
import logging
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from slate_core.plugins.agent_registry import AgentBase, AgentCapability

logger = logging.getLogger("slate.agent.epsilon")
WORKSPACE_ROOT = Path(__file__).parent.parent.parent.parent
SPECS_DIR = WORKSPACE_ROOT / "docs" / "specs"


class EpsilonAgent(AgentBase):
    """Spec-weaver agent — generates structured specifications and architecture docs."""

    AGENT_ID = "EPSILON"
    AGENT_NAME = "Epsilon Spec-Weaver"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Generate structured specs, architecture docs, and capacity plans"
    REQUIRES_GPU = False
    DEPENDENCIES: List[str] = []

    def on_load(self) -> bool:
        """Ensure specs directory exists."""
        SPECS_DIR.mkdir(parents=True, exist_ok=True)
        return True

    def capabilities(self) -> List[AgentCapability]:
        return [
            AgentCapability(
                name="spec_generation",
                patterns=["spec", "specification", "architecture", "capacity",
                          "blueprint", "schema", "diagram", "rfc"],
                requires_gpu=False,
                cpu_cores=1,
                priority=35,
                description="Generate structured specifications and architecture documents",
            ),
            AgentCapability(
                name="documentation",
                patterns=["doc", "documentation", "api-doc", "wiki", "readme",
                          "changelog", "guide"],
                requires_gpu=False,
                cpu_cores=1,
                priority=45,
                description="Create and update project documentation",
            ),
        ]

    def execute(self, task: dict) -> dict:
        """Execute a spec generation or documentation task."""
        title = task.get("title", "")
        description = task.get("description", "")
        combined = f"{title} {description}".lower()

        if any(w in combined for w in ["capacity", "agent", "runner", "scale"]):
            return self._generate_capacity_spec(task)
        elif any(w in combined for w in ["architecture", "system", "component"]):
            return self._generate_architecture_spec(task)
        elif any(w in combined for w in ["api", "endpoint", "rest"]):
            return self._generate_api_spec(task)
        elif any(w in combined for w in ["security", "threat", "compliance"]):
            return self._generate_security_spec(task)
        else:
            return self._generate_generic_spec(task)

    def _generate_capacity_spec(self, task: dict) -> dict:
        """Generate agent/runner capacity specification."""
        # Gather system data
        sys_info = self._gather_system_info()

        spec = {
            "spec_type": "capacity",
            "title": task.get("title", "Agent & Runner Capacity Specification"),
            "version": "1.0.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generator": "EPSILON/spec-weaver",
            "system": sys_info,
            "agents": {
                "ALPHA": {
                    "role": "Coding", "gpu": True,
                    "gpu_mb": 4096, "cpu": 2, "model": "slate-coder",
                },
                "BETA": {
                    "role": "Testing", "gpu": True,
                    "gpu_mb": 2048, "cpu": 2, "model": "slate-coder",
                },
                "GAMMA": {
                    "role": "Planning", "gpu": False,
                    "cpu": 1, "model": "slate-planner",
                },
                "DELTA": {
                    "role": "Integration", "gpu": False,
                    "cpu": 1, "model": "slate-planner",
                },
                "EPSILON": {
                    "role": "Spec-Weaver", "gpu": False,
                    "cpu": 1, "model": "slate-planner",
                },
                "ZETA": {
                    "role": "Benchmark Oracle", "gpu": True,
                    "gpu_mb": 1024, "cpu": 2, "model": "slate-fast",
                },
                "COPILOT": {
                    "role": "Orchestration", "gpu": True,
                    "gpu_mb": 8192, "cpu": 4, "model": "slate-coder",
                },
            },
            "runner_profiles": {
                "light": {"gpu_mb": 0, "cpu": 1, "ram_mb": 512},
                "standard": {"gpu_mb": 0, "cpu": 2, "ram_mb": 1024},
                "gpu_light": {"gpu_mb": 2048, "cpu": 2, "ram_mb": 2048},
                "gpu_heavy": {"gpu_mb": 8192, "cpu": 4, "ram_mb": 8192},
                "gpu_max": {"gpu_mb": 14000, "cpu": 4, "ram_mb": 16384},
            },
            "scaling": {
                "max_runners": 50,
                "max_parallel_workflows": 8,
                "gpu_partitioning": "time-slice + memory-partition",
            },
        }

        # Write spec to disk
        spec_path = SPECS_DIR / "agents-capacity.json"
        spec_path.parent.mkdir(parents=True, exist_ok=True)
        with open(spec_path, "w", encoding="utf-8") as f:
            json.dump(spec, f, indent=2)

        # Also write markdown version
        md_path = SPECS_DIR / "agents-capacity.md"
        md_content = self._spec_to_markdown(spec)
        with open(md_path, "w", encoding="utf-8") as f:
            f.write(md_content)

        return {
            "success": True,
            "result": f"Capacity spec written to {spec_path} and {md_path}",
            "agent": self.AGENT_ID,
            "artifacts": [str(spec_path), str(md_path)],
        }

    def _generate_architecture_spec(self, task: dict) -> dict:
        """Generate architecture specification."""
        prompt = (
            f"Generate an architecture specification for: {task.get('title', '')}\n"
            f"Context: {task.get('description', '')}\n"
            "Include: components, data flow, dependencies, deployment topology."
        )
        return self._generate_with_model(task, prompt, "architecture")

    def _generate_api_spec(self, task: dict) -> dict:
        """Generate API specification."""
        prompt = (
            f"Generate an API specification for: {task.get('title', '')}\n"
            f"Context: {task.get('description', '')}\n"
            "Include: endpoints, request/response schemas, authentication, error codes."
        )
        return self._generate_with_model(task, prompt, "api")

    def _generate_security_spec(self, task: dict) -> dict:
        """Generate security specification."""
        prompt = (
            f"Generate a security specification for: {task.get('title', '')}\n"
            f"Context: {task.get('description', '')}\n"
            "Include: threat model, attack vectors, mitigations, compliance checklist."
        )
        return self._generate_with_model(task, prompt, "security")

    def _generate_generic_spec(self, task: dict) -> dict:
        """Generate a generic specification document."""
        prompt = (
            f"Generate a specification document for: {task.get('title', '')}\n"
            f"Details: {task.get('description', '')}\n"
            "Include: overview, requirements, design, implementation plan, acceptance criteria."
        )
        return self._generate_with_model(task, prompt, "spec")

    def _generate_with_model(self, task: dict, prompt: str, spec_type: str) -> dict:
        """Generate spec content using slate-planner model."""
        try:
            result = subprocess.run(
                ["ollama", "run", "slate-planner", prompt],
                capture_output=True, text=True, timeout=120,
                cwd=str(WORKSPACE_ROOT),
            )

            if result.returncode != 0:
                return {"success": False, "error": f"Model error: {result.stderr[:300]}"}

            content = result.stdout.strip()
            # Write to file
            slug = task.get("title", "spec").lower().replace(" ", "-")[:40]
            spec_path = SPECS_DIR / f"{spec_type}-{slug}.md"
            with open(spec_path, "w", encoding="utf-8") as f:
                f.write(f"# {task.get('title', 'Specification')}\n\n")
                f.write(f"Generated: {datetime.now(timezone.utc).isoformat()}\n")
                f.write("Agent: EPSILON/spec-weaver\n\n---\n\n")
                f.write(content)

            return {
                "success": True,
                "result": content[:2000],
                "agent": self.AGENT_ID,
                "artifacts": [str(spec_path)],
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _gather_system_info(self) -> dict:
        """Gather current system information for capacity specs."""
        import os
        info: dict = {
            "cpu_cores": os.cpu_count() or 0,
            "gpus": [],
        }
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total,memory.free",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=10
            )
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 3:
                    info["gpus"].append({
                        "name": parts[0],
                        "memory_total_mb": int(parts[1]),
                        "memory_free_mb": int(parts[2]),
                    })
        except Exception:
            pass

        try:
            import psutil
            mem = psutil.virtual_memory()
            info["ram_total_mb"] = mem.total // (1024 * 1024)
            info["ram_free_mb"] = mem.available // (1024 * 1024)
        except ImportError:
            info["ram_total_mb"] = 0
            info["ram_free_mb"] = 0

        return info

    def _spec_to_markdown(self, spec: dict) -> str:
        """Convert a capacity spec dict to markdown."""
        lines = [
            f"# {spec['title']}",
            "",
            f"**Version:** {spec['version']}",
            f"**Generated:** {spec['generated_at']}",
            f"**Generator:** {spec['generator']}",
            "",
            "---",
            "",
            "## System Resources",
            "",
            f"- **CPU Cores:** {spec['system'].get('cpu_cores', 'N/A')}",
            f"- **RAM Total:** {spec['system'].get('ram_total_mb', 'N/A')} MB",
            f"- **RAM Free:** {spec['system'].get('ram_free_mb', 'N/A')} MB",
            "",
        ]

        gpus = spec["system"].get("gpus", [])
        if gpus:
            lines.append("### GPUs")
            lines.append("")
            lines.append("| GPU | Name | Total (MB) | Free (MB) |")
            lines.append("|-----|------|-----------|----------|")
            for i, gpu in enumerate(gpus):
                total = gpu['memory_total_mb']
                free = gpu['memory_free_mb']
                lines.append(
                    f"| {i} | {gpu['name']} | {total:,}"
                    f" | {free:,} |"
                )
            lines.append("")

        lines.append("## Agent Roster")
        lines.append("")
        lines.append("| Agent | Role | GPU | GPU (MB) | CPU | Model |")
        lines.append("|-------|------|-----|---------|-----|-------|")
        for agent_id, info in spec["agents"].items():
            gpu_str = "Yes" if info.get("gpu") else "No"
            gpu_mb = info.get("gpu_mb", 0)
            cpu = info.get("cpu", 1)
            model = info.get("model", "N/A")
            role = info['role']
            lines.append(
                f"| {agent_id} | {role} | {gpu_str}"
                f" | {gpu_mb} | {cpu} | {model} |"
            )
        lines.append("")

        lines.append("## Runner Profiles")
        lines.append("")
        lines.append("| Profile | GPU (MB) | CPU | RAM (MB) |")
        lines.append("|---------|---------|-----|---------|")
        for profile, info in spec["runner_profiles"].items():
            lines.append(f"| {profile} | {info['gpu_mb']} | {info['cpu']} | {info['ram_mb']} |")
        lines.append("")

        lines.append("## Scaling Configuration")
        lines.append("")
        scaling = spec["scaling"]
        lines.append(f"- **Max Runners:** {scaling['max_runners']}")
        lines.append(f"- **Max Parallel Workflows:** {scaling['max_parallel_workflows']}")
        lines.append(f"- **GPU Strategy:** {scaling['gpu_partitioning']}")
        lines.append("")

        return "\n".join(lines)

    def health_check(self) -> dict:
        base = super().health_check()
        base["specs_dir_exists"] = SPECS_DIR.exists()
        base["specs_count"] = len(list(SPECS_DIR.glob("*.md"))) if SPECS_DIR.exists() else 0
        base["healthy"] = True
        return base
