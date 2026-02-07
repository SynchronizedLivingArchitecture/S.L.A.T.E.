#!/usr/bin/env python3
# Modified: 2026-02-07T12:00:00Z | Author: Claude | Change: Tests for spec-kit wiki integration
"""
Tests for slate.slate_spec_kit
==============================
AAA (Arrange-Act-Assert) pattern throughout.
"""

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.slate_spec_kit import (
    ParsedSpec,
    SpecKitOrchestrator,
    SpecKitRunner,
    SpecParser,
    SpecSection,
    WikiGenerator,
)


class TestSpecSection:
    """Tests for the SpecSection dataclass."""

    def test_section_to_dict(self):
        """Section converts to dictionary correctly."""
        # Arrange
        section = SpecSection(
            level=2,
            title="Test Section",
            anchor="test-section",
            content="Some content here",
            line_start=10,
            line_end=20,
        )

        # Act
        result = section.to_dict()

        # Assert
        assert result["level"] == 2
        assert result["title"] == "Test Section"
        assert result["anchor"] == "test-section"
        assert result["content_length"] == len("Some content here")
        assert result["line_range"] == [10, 20]

    def test_section_with_subsections(self):
        """Section with subsections includes them in dict."""
        # Arrange
        subsection = SpecSection(
            level=3,
            title="Subsection",
            anchor="subsection",
            content="Sub content",
            line_start=15,
            line_end=18,
        )
        section = SpecSection(
            level=2,
            title="Parent",
            anchor="parent",
            content="Parent content",
            line_start=10,
            line_end=20,
            subsections=[subsection],
        )

        # Act
        result = section.to_dict()

        # Assert
        assert len(result["subsections"]) == 1
        assert result["subsections"][0]["title"] == "Subsection"


class TestSpecParser:
    """Tests for the SpecParser class."""

    def test_make_anchor(self):
        """Anchor generation from title works correctly."""
        # Arrange
        parser = SpecParser()

        # Act & Assert
        assert parser._make_anchor("Design Principles") == "design-principles"
        assert parser._make_anchor("API Reference") == "api-reference"
        assert parser._make_anchor("Test Case #1") == "test-case-1"

    def test_parse_metadata(self):
        """Metadata extraction from spec header works."""
        # Arrange
        parser = SpecParser()
        content = """# Test Spec

**Spec ID**: 001-test-spec
**Status**: implementing
**Created**: 2026-02-07

## Overview
Some content here.
"""

        # Act
        metadata = parser.parse_metadata(content)

        # Assert
        assert metadata["spec_id"] == "001-test-spec"
        assert metadata["status"] == "implementing"
        assert metadata["created"] == "2026-02-07"

    def test_parse_sections_h2_only(self):
        """Parsing content with only h2 headings works."""
        # Arrange
        parser = SpecParser()
        content = """# Main Title

## First Section
Content for first section.

## Second Section
Content for second section.
"""

        # Act
        sections = parser.parse_sections(content)

        # Assert
        assert len(sections) == 2
        assert sections[0].title == "First Section"
        assert sections[0].level == 2
        assert sections[1].title == "Second Section"

    def test_parse_sections_with_subsections(self):
        """Parsing content with h2 and h3 headings works."""
        # Arrange
        parser = SpecParser()
        content = """# Main Title

## Overview
Overview content.

### Details
Detail content.

### More Details
More detail content.

## Another Section
Another section content.
"""

        # Act
        sections = parser.parse_sections(content)

        # Assert
        assert len(sections) == 2
        assert sections[0].title == "Overview"
        assert len(sections[0].subsections) == 2
        assert sections[0].subsections[0].title == "Details"
        assert sections[0].subsections[1].title == "More Details"
        assert sections[1].title == "Another Section"
        assert len(sections[1].subsections) == 0


class TestParsedSpec:
    """Tests for the ParsedSpec dataclass."""

    def test_get_all_sections_flat(self):
        """Flattening sections includes all levels."""
        # Arrange
        subsection = SpecSection(
            level=3,
            title="Sub",
            anchor="sub",
            content="",
            line_start=5,
            line_end=10,
        )
        section = SpecSection(
            level=2,
            title="Parent",
            anchor="parent",
            content="",
            line_start=0,
            line_end=15,
            subsections=[subsection],
        )
        spec = ParsedSpec(
            spec_id="test",
            spec_path=Path("test.md"),
            title="Test",
            metadata={},
            sections=[section],
            raw_content="",
        )

        # Act
        flat = spec.get_all_sections_flat()

        # Assert
        assert len(flat) == 2
        assert flat[0].title == "Parent"
        assert flat[1].title == "Sub"


class TestWikiGenerator:
    """Tests for the WikiGenerator class."""

    def test_spec_id_to_wiki_filename(self):
        """Filename generation from spec ID works."""
        # Arrange
        wiki = WikiGenerator()

        # Act & Assert
        assert wiki._spec_id_to_wiki_filename("005-monochrome-theme") == "Spec-005-Monochrome-Theme.md"
        assert wiki._spec_id_to_wiki_filename("006-natural-theme-system") == "Spec-006-Natural-Theme-System.md"
        # Non-numeric prefix results in just the name part being used
        assert wiki._spec_id_to_wiki_filename("test-spec") == "Spec-Spec.md"

    def test_generate_spec_page_basic(self):
        """Basic wiki page generation works."""
        # Arrange
        wiki = WikiGenerator()
        section = SpecSection(
            level=2,
            title="Overview",
            anchor="overview",
            content="This is the overview.",
            line_start=5,
            line_end=10,
        )
        spec = ParsedSpec(
            spec_id="test-spec",
            spec_path=Path("specs/test-spec/spec.md"),
            title="Test Specification",
            metadata={"status": "implementing"},
            sections=[section],
            raw_content="",
        )

        # Act
        content = wiki.generate_spec_page(spec, include_analysis=False)

        # Assert
        assert "# Test Specification" in content
        assert "## Overview" in content
        assert "This is the overview." in content
        assert "| **Status** | implementing |" in content


class TestSpecKitRunner:
    """Tests for the SpecKitRunner class."""

    def test_analyze_section_ollama_not_running(self):
        """Returns error when Ollama is not available."""
        # Arrange
        runner = SpecKitRunner()
        section = SpecSection(
            level=2,
            title="Test",
            anchor="test",
            content="Test content",
            line_start=0,
            line_end=5,
        )

        # Mock Ollama as not running
        with patch.object(runner, "_get_ollama") as mock_get:
            mock_ollama = MagicMock()
            mock_ollama.is_running.return_value = False
            mock_get.return_value = mock_ollama

            # Act
            result = runner.analyze_section(section)

        # Assert
        assert "error" in result
        assert result["error"] == "Ollama not available"

    def test_analyze_section_success(self):
        """Successfully analyzes section when Ollama is available."""
        # Arrange
        runner = SpecKitRunner()
        section = SpecSection(
            level=2,
            title="Test",
            anchor="test",
            content="Test content for analysis",
            line_start=0,
            line_end=5,
        )

        # Mock Ollama response
        mock_response = {
            "response": json.dumps({
                "requirements": ["req1", "req2"],
                "implementation_notes": "Some notes",
                "risks": ["risk1"],
                "dependencies": [],
                "summary": "Test summary",
            })
        }

        with patch.object(runner, "_get_ollama") as mock_get:
            mock_ollama = MagicMock()
            mock_ollama.is_running.return_value = True
            mock_ollama.generate.return_value = mock_response
            mock_get.return_value = mock_ollama

            # Act
            result = runner.analyze_section(section)

        # Assert
        assert "error" not in result
        assert result["requirements"] == ["req1", "req2"]
        assert result["summary"] == "Test summary"


class TestSpecKitOrchestrator:
    """Tests for the SpecKitOrchestrator class."""

    def test_load_state_missing_file(self, tmp_path):
        """Returns default state when file doesn't exist."""
        # Arrange
        with patch("slate.slate_spec_kit.STATE_FILE", tmp_path / "nonexistent.json"):
            # Act
            orchestrator = SpecKitOrchestrator()

        # Assert
        assert orchestrator.state["last_run"] is None
        assert orchestrator.state["specs_processed"] == 0

    def test_load_state_existing_file(self, tmp_path):
        """Loads state from existing file."""
        # Arrange
        state_file = tmp_path / "state.json"
        state_file.write_text(json.dumps({
            "last_run": "2026-02-07T00:00:00Z",
            "specs_processed": 5,
            "wiki_pages_generated": 3,
            "sections_analyzed": 20,
        }))

        with patch("slate.slate_spec_kit.STATE_FILE", state_file):
            # Act
            orchestrator = SpecKitOrchestrator()

        # Assert
        assert orchestrator.state["specs_processed"] == 5
        assert orchestrator.state["sections_analyzed"] == 20


class TestIntegration:
    """Integration tests for the full spec-kit workflow."""

    def test_parse_real_spec_structure(self, tmp_path):
        """Parse a realistic spec structure."""
        # Arrange
        spec_content = """# Specification: Test Feature

**Spec ID**: 001-test-feature
**Status**: draft
**Created**: 2026-02-07

## Overview

This is a test specification for a new feature.

## Design Principles

### Simplicity

Keep it simple.

### Performance

Make it fast.

## Implementation

Details here.
"""
        spec_dir = tmp_path / "specs" / "001-test-feature"
        spec_dir.mkdir(parents=True)
        spec_file = spec_dir / "spec.md"
        spec_file.write_text(spec_content)

        parser = SpecParser()
        # Override specs_dir for this test
        parser.specs_dir = tmp_path / "specs"

        # Act
        specs = parser.discover_specs()
        assert len(specs) == 1
        parsed = parser.parse_spec(specs[0])

        # Assert
        assert parsed.spec_id == "001-test-feature"
        assert parsed.metadata["status"] == "draft"
        assert len(parsed.sections) == 3
        assert parsed.sections[0].title == "Overview"
        assert parsed.sections[1].title == "Design Principles"
        assert len(parsed.sections[1].subsections) == 2
        assert parsed.sections[2].title == "Implementation"
