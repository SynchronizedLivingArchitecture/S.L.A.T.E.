#!/usr/bin/env python3
"""
SLATE Workflow Analyzer - Meta-workflow management for SLATE development.

This module enables SLATE to manage its own development workflows by:
1. Identifying deprecated/redundant workflows
2. Categorizing workflows by development area
3. Self-documenting workflow purposes and dependencies
4. Detecting workflow health issues

Modified: 2026-02-06T22:30:00Z | Author: COPILOT | Change: Initial implementation
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from typing import Any

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# Development workflow categories
WORKFLOW_CATEGORIES = {
    "core": {
        "name": "Core SLATE",
        "description": "Core SDK, orchestrator, and system health",
        "paths": ["slate/", "slate_core/"],
        "workflows": ["ci.yml", "slate.yml", "nightly.yml"],
    },
    "ui": {
        "name": "UI Development",
        "description": "Dashboard, tech tree visualization, frontend",
        "paths": ["agents/slate_dashboard_server.py", "src/frontend/"],
        "workflows": ["slate.yml"],
    },
    "copilot": {
        "name": "Copilot Instructions",
        "description": "GitHub Copilot integration, prompts, skills",
        "paths": [".github/copilot-instructions.md", ".github/prompts/", "skills/"],
        "workflows": ["ci.yml"],
    },
    "claude": {
        "name": "Claude Integration",
        "description": "Claude Code commands, plugins, MCP",
        "paths": [".claude/", "slate/mcp_server.py", "CLAUDE.md"],
        "workflows": ["ci.yml"],
    },
    "docker": {
        "name": "Docker Infrastructure",
        "description": "Container images, compose, registry",
        "paths": ["Dockerfile*", "docker-compose.yml", ".dockerignore"],
        "workflows": ["docker.yml"],
    },
    "runner": {
        "name": "GitHub Runner",
        "description": "Self-hosted runner, GPU, CI/CD",
        "paths": ["actions-runner/", "slate/slate_runner_manager.py"],
        "workflows": ["runner-check.yml", "ci.yml"],
    },
    "security": {
        "name": "Security",
        "description": "Security scanning, fork validation, SDK guard",
        "paths": ["slate/action_guard.py", "slate/sdk_source_guard.py"],
        "workflows": ["codeql.yml", "fork-validation.yml"],
    },
    "release": {
        "name": "Release & CD",
        "description": "Releases, deployment, versioning",
        "paths": ["pyproject.toml", "CHANGELOG.md"],
        "workflows": ["cd.yml", "release.yml"],
    },
}

# Known redundant/deprecated patterns
DEPRECATED_PATTERNS = {
    "agent_legacy": {
        "files": ["agents/alpha_agent.py", "agents/beta_agent.py", "agents/gamma_agent.py", "agents/delta_agent.py"],
        "reason": "Legacy agent system replaced by workflow-based execution",
        "replacement": "Use GitHub Actions workflows via slate_runner_manager.py",
    },
    "old_shell_syntax": {
        "patterns": ["shell: pwsh", "shell: bash"],
        "reason": "SLATE uses PowerShell 5.1 on Windows",
        "replacement": "shell: powershell",
    },
    "external_action": {
        "patterns": ["actions/setup-python@"],
        "reason": "SLATE uses local venv, not actions/setup-python",
        "replacement": "Add venv path to GITHUB_PATH directly",
    },
}


class WorkflowAnalyzer:
    """Analyzes SLATE workflows for redundancy, deprecation, and health."""

    def __init__(self, workspace: Path | None = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.workflows_dir = self.workspace / ".github" / "workflows"
        self.results: dict[str, Any] = {}

    def analyze_all(self) -> dict[str, Any]:
        """Run complete workflow analysis."""
        self.results = {
            "timestamp": datetime.now().isoformat(),
            "workspace": str(self.workspace),
            "categories": self._analyze_categories(),
            "workflows": self._analyze_workflows(),
            "deprecated": self._find_deprecated(),
            "redundant": self._find_redundant(),
            "health": self._check_health(),
            "recommendations": [],
        }
        self._generate_recommendations()
        return self.results

    def _analyze_categories(self) -> dict[str, Any]:
        """Analyze which development categories have proper workflow coverage."""
        coverage = {}
        for cat_id, cat_info in WORKFLOW_CATEGORIES.items():
            has_files = any(
                (self.workspace / p).exists() or list(self.workspace.glob(p))
                for p in cat_info["paths"]
            )
            has_workflows = all(
                (self.workflows_dir / w).exists() for w in cat_info["workflows"]
            )
            coverage[cat_id] = {
                "name": cat_info["name"],
                "description": cat_info["description"],
                "has_files": has_files,
                "has_workflows": has_workflows,
                "coverage": "complete" if has_files and has_workflows else "partial" if has_files else "none",
            }
        return coverage

    def _analyze_workflows(self) -> list[dict[str, Any]]:
        """Analyze each workflow file."""
        workflows = []
        if not self.workflows_dir.exists():
            return workflows

        for wf_file in sorted(self.workflows_dir.glob("*.yml")):
            content = wf_file.read_text(encoding="utf-8")
            workflows.append({
                "name": wf_file.name,
                "size_bytes": wf_file.stat().st_size,
                "line_count": len(content.splitlines()),
                "has_self_hosted": "self-hosted" in content,
                "has_gpu": "gpu" in content.lower(),
                "triggers": self._extract_triggers(content),
                "categories": self._categorize_workflow(wf_file.name),
            })
        return workflows

    def _extract_triggers(self, content: str) -> list[str]:
        """Extract workflow triggers from content."""
        triggers = []
        if "push:" in content:
            triggers.append("push")
        if "pull_request:" in content:
            triggers.append("pull_request")
        if "workflow_dispatch:" in content:
            triggers.append("workflow_dispatch")
        if "schedule:" in content:
            triggers.append("schedule")
        return triggers

    def _categorize_workflow(self, workflow_name: str) -> list[str]:
        """Find which categories a workflow belongs to."""
        categories = []
        for cat_id, cat_info in WORKFLOW_CATEGORIES.items():
            if workflow_name in cat_info["workflows"]:
                categories.append(cat_id)
        return categories if categories else ["uncategorized"]

    def _find_deprecated(self) -> list[dict[str, Any]]:
        """Find deprecated files and patterns."""
        deprecated = []
        for dep_id, dep_info in DEPRECATED_PATTERNS.items():
            if "files" in dep_info:
                for file_path in dep_info["files"]:
                    if (self.workspace / file_path).exists():
                        deprecated.append({
                            "type": "file",
                            "id": dep_id,
                            "path": file_path,
                            "reason": dep_info["reason"],
                            "replacement": dep_info["replacement"],
                        })
            if "patterns" in dep_info:
                for wf_file in self.workflows_dir.glob("*.yml"):
                    content = wf_file.read_text(encoding="utf-8")
                    for pattern in dep_info["patterns"]:
                        if pattern in content:
                            deprecated.append({
                                "type": "pattern",
                                "id": dep_id,
                                "file": wf_file.name,
                                "pattern": pattern,
                                "reason": dep_info["reason"],
                                "replacement": dep_info["replacement"],
                            })
        return deprecated

    def _find_redundant(self) -> list[dict[str, Any]]:
        """Find redundant workflows (similar triggers/paths)."""
        redundant = []
        workflows = list(self.workflows_dir.glob("*.yml"))

        # Check for workflows with overlapping triggers on same paths
        workflow_triggers: dict[str, set[str]] = {}
        for wf_file in workflows:
            content = wf_file.read_text(encoding="utf-8")
            triggers = set(self._extract_triggers(content))
            workflow_triggers[wf_file.name] = triggers

        # Find overlaps
        checked = set()
        for wf1, triggers1 in workflow_triggers.items():
            for wf2, triggers2 in workflow_triggers.items():
                if wf1 >= wf2 or (wf1, wf2) in checked:
                    continue
                checked.add((wf1, wf2))
                overlap = triggers1 & triggers2
                if overlap and len(overlap) > 1:
                    # Check if they cover similar paths
                    content1 = (self.workflows_dir / wf1).read_text(encoding="utf-8")
                    content2 = (self.workflows_dir / wf2).read_text(encoding="utf-8")
                    if "slate/" in content1 and "slate/" in content2:
                        redundant.append({
                            "workflows": [wf1, wf2],
                            "overlapping_triggers": list(overlap),
                            "suggestion": f"Consider consolidating {wf1} and {wf2}",
                        })

        return redundant

    def _check_health(self) -> dict[str, Any]:
        """Check overall workflow health."""
        total = len(list(self.workflows_dir.glob("*.yml")))
        categorized = sum(
            1 for wf in self.workflows_dir.glob("*.yml")
            if self._categorize_workflow(wf.name) != ["uncategorized"]
        )
        return {
            "total_workflows": total,
            "categorized": categorized,
            "uncategorized": total - categorized,
            "coverage_percent": round(categorized / total * 100, 1) if total > 0 else 0,
            "has_ci": (self.workflows_dir / "ci.yml").exists(),
            "has_cd": (self.workflows_dir / "cd.yml").exists(),
            "has_security": (self.workflows_dir / "codeql.yml").exists(),
            "has_docker": (self.workflows_dir / "docker.yml").exists(),
        }

    def _generate_recommendations(self) -> None:
        """Generate actionable recommendations."""
        recs = []

        # Check for missing coverage
        for cat_id, cat_data in self.results["categories"].items():
            if cat_data["coverage"] == "partial":
                recs.append({
                    "priority": "medium",
                    "category": cat_id,
                    "action": f"Add workflows for {cat_data['name']}",
                    "reason": "Files exist but no dedicated workflow",
                })

        # Check for deprecated items
        if self.results["deprecated"]:
            recs.append({
                "priority": "high",
                "action": "Remove deprecated files/patterns",
                "count": len(self.results["deprecated"]),
                "reason": "Deprecated items should be cleaned up",
            })

        # Check for redundant workflows
        if self.results["redundant"]:
            recs.append({
                "priority": "low",
                "action": "Consider consolidating redundant workflows",
                "count": len(self.results["redundant"]),
                "reason": "Reduce maintenance overhead",
            })

        self.results["recommendations"] = recs

    def print_report(self) -> None:
        """Print human-readable analysis report."""
        if not self.results:
            self.analyze_all()

        print("=" * 60)
        print("  SLATE Workflow Analysis Report")
        print("=" * 60)
        print()

        # Health summary
        health = self.results["health"]
        print(f"Workflows: {health['total_workflows']} total, {health['categorized']} categorized")
        print(f"Coverage:  {health['coverage_percent']}%")
        print()

        # Category coverage
        print("Development Categories:")
        print("-" * 40)
        for cat_id, cat_data in self.results["categories"].items():
            status = "[OK]" if cat_data["coverage"] == "complete" else "[--]" if cat_data["coverage"] == "partial" else "[  ]"
            print(f"  {status} {cat_data['name']}: {cat_data['coverage']}")
        print()

        # Deprecated items
        if self.results["deprecated"]:
            print(f"Deprecated Items: {len(self.results['deprecated'])}")
            print("-" * 40)
            for dep in self.results["deprecated"][:5]:
                print(f"  [X] {dep.get('path', dep.get('file', 'unknown'))}: {dep['reason']}")
            if len(self.results["deprecated"]) > 5:
                print(f"  ... and {len(self.results['deprecated']) - 5} more")
            print()

        # Recommendations
        if self.results["recommendations"]:
            print("Recommendations:")
            print("-" * 40)
            for rec in self.results["recommendations"]:
                print(f"  [{rec['priority'].upper()}] {rec['action']}")
        print()
        print("=" * 60)


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Workflow Analyzer")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--categories", action="store_true", help="Show category details")
    parser.add_argument("--deprecated", action="store_true", help="Show deprecated items only")
    args = parser.parse_args()

    analyzer = WorkflowAnalyzer()
    results = analyzer.analyze_all()

    if args.json:
        print(json.dumps(results, indent=2, default=str))
    elif args.deprecated:
        for dep in results["deprecated"]:
            print(f"{dep.get('path', dep.get('file'))}: {dep['reason']}")
    elif args.categories:
        for cat_id, cat_data in results["categories"].items():
            print(f"{cat_id}: {cat_data['name']} [{cat_data['coverage']}]")
    else:
        analyzer.print_report()


if __name__ == "__main__":
    main()
