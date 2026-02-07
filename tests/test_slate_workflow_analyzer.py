# Modified: 2026-02-07T13:30:00Z | Author: COPILOT | Change: Add test coverage for slate_workflow_analyzer module
"""
Tests for slate/slate_workflow_analyzer.py — workflow categorization,
deprecation detection, redundancy checking, health analysis.
"""

import json
import pytest
from pathlib import Path

from slate.slate_workflow_analyzer import (
    WorkflowAnalyzer,
    WORKFLOW_CATEGORIES,
    DEPRECATED_PATTERNS,
)


# ── Constants ───────────────────────────────────────────────────────────


class TestConstants:
    """Tests for workflow analyzer constants."""

    def test_workflow_categories_defined(self):
        assert "core" in WORKFLOW_CATEGORIES
        assert "security" in WORKFLOW_CATEGORIES
        assert "docker" in WORKFLOW_CATEGORIES
        assert "release" in WORKFLOW_CATEGORIES

    def test_each_category_has_required_fields(self):
        for cat_id, cat_info in WORKFLOW_CATEGORIES.items():
            assert "name" in cat_info, f"{cat_id} missing name"
            assert "description" in cat_info, f"{cat_id} missing description"
            assert "paths" in cat_info, f"{cat_id} missing paths"
            assert "workflows" in cat_info, f"{cat_id} missing workflows"

    def test_deprecated_patterns_defined(self):
        assert "old_shell_syntax" in DEPRECATED_PATTERNS
        assert "external_action" in DEPRECATED_PATTERNS


# ── WorkflowAnalyzer with temp workspace ────────────────────────────────


@pytest.fixture
def workspace(tmp_path):
    """Create a minimal workspace with workflows for testing."""
    # Create workflow directory
    wf_dir = tmp_path / ".github" / "workflows"
    wf_dir.mkdir(parents=True)

    # Create ci.yml
    (wf_dir / "ci.yml").write_text(
        "name: CI\non:\n  push:\n  pull_request:\n  workflow_dispatch:\n"
        "jobs:\n  test:\n    runs-on: [self-hosted, slate]\n"
        "    steps:\n      - run: echo 'test'\n",
        encoding="utf-8",
    )

    # Create cd.yml
    (wf_dir / "cd.yml").write_text(
        "name: CD\non:\n  push:\n    branches: [main]\n"
        "jobs:\n  deploy:\n    runs-on: [self-hosted, slate]\n",
        encoding="utf-8",
    )

    # Create codeql.yml
    (wf_dir / "codeql.yml").write_text(
        "name: CodeQL\non:\n  push:\n  schedule:\n"
        "jobs:\n  analyze:\n    runs-on: [self-hosted, slate]\n",
        encoding="utf-8",
    )

    # Create docker.yml
    (wf_dir / "docker.yml").write_text(
        "name: Docker\non:\n  push:\n  workflow_dispatch:\n"
        "jobs:\n  build:\n    runs-on: [self-hosted, slate]\n",
        encoding="utf-8",
    )

    # Create slate/ directory for category detection
    (tmp_path / "slate").mkdir()
    (tmp_path / "slate" / "slate_status.py").write_text("# test", encoding="utf-8")

    # Create pyproject.toml for release category
    (tmp_path / "pyproject.toml").write_text("[project]\nname='slate'\n", encoding="utf-8")

    return tmp_path


class TestWorkflowAnalyzer:
    """Tests for WorkflowAnalyzer class."""

    def test_analyze_all_returns_results(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        assert "categories" in results
        assert "workflows" in results
        assert "deprecated" in results
        assert "redundant" in results
        assert "health" in results
        assert "timestamp" in results

    def test_workflows_detected(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        names = [w["name"] for w in results["workflows"]]
        assert "ci.yml" in names
        assert "cd.yml" in names

    def test_workflow_metadata(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        ci = next(w for w in results["workflows"] if w["name"] == "ci.yml")
        assert ci["has_self_hosted"] is True
        assert ci["line_count"] > 0
        assert "push" in ci["triggers"]
        assert "pull_request" in ci["triggers"]

    def test_health_metrics(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        health = results["health"]
        assert health["total_workflows"] == 4
        assert health["has_ci"] is True
        assert health["has_cd"] is True
        assert health["has_security"] is True
        assert health["has_docker"] is True

    def test_category_coverage(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        # core category: slate/ dir exists + ci.yml exists
        core = results["categories"]["core"]
        assert core["has_files"] is True

    def test_empty_workspace(self, tmp_path):
        (tmp_path / ".github" / "workflows").mkdir(parents=True)
        analyzer = WorkflowAnalyzer(tmp_path)
        results = analyzer.analyze_all()
        assert results["health"]["total_workflows"] == 0


# ── Trigger Extraction ──────────────────────────────────────────────────


class TestTriggerExtraction:
    """Tests for trigger extraction from workflow content."""

    def test_extract_push_trigger(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        content = "on:\n  push:\n  pull_request:\n"
        triggers = analyzer._extract_triggers(content)
        assert "push" in triggers
        assert "pull_request" in triggers

    def test_extract_schedule_trigger(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        content = "on:\n  schedule:\n    - cron: '0 0 * * *'\n"
        triggers = analyzer._extract_triggers(content)
        assert "schedule" in triggers

    def test_extract_workflow_dispatch(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        content = "on:\n  workflow_dispatch:\n"
        triggers = analyzer._extract_triggers(content)
        assert "workflow_dispatch" in triggers


# ── Categorization ──────────────────────────────────────────────────────


class TestCategorization:
    """Tests for workflow categorization."""

    def test_ci_categorized_correctly(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        cats = analyzer._categorize_workflow("ci.yml")
        assert "core" in cats

    def test_unknown_workflow_uncategorized(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        cats = analyzer._categorize_workflow("mystery.yml")
        assert cats == ["uncategorized"]

    def test_docker_categorized(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        cats = analyzer._categorize_workflow("docker.yml")
        assert "docker" in cats


# ── Deprecated Detection ───────────────────────────────────────────────


class TestDeprecatedDetection:
    """Tests for deprecated pattern/file detection."""

    def test_deprecated_pattern_detected(self, tmp_path):
        wf_dir = tmp_path / ".github" / "workflows"
        wf_dir.mkdir(parents=True)
        # Create workflow with deprecated pattern
        (wf_dir / "bad.yml").write_text(
            "name: Bad\njobs:\n  test:\n    shell: bash\n"
            "    runs-on: ubuntu-latest\n",
            encoding="utf-8",
        )
        analyzer = WorkflowAnalyzer(tmp_path)
        results = analyzer.analyze_all()
        deprecated = results["deprecated"]
        patterns = [d.get("pattern") for d in deprecated]
        assert "shell: bash" in patterns

    def test_no_deprecated_in_clean_workspace(self, workspace):
        analyzer = WorkflowAnalyzer(workspace)
        results = analyzer.analyze_all()
        # Clean workspace shouldn't have file-based deprecations
        file_deps = [d for d in results["deprecated"] if d["type"] == "file"]
        assert len(file_deps) == 0
