#!/usr/bin/env python3
"""
SLATE Spec-Kit Wiki Integration
================================
# Modified: 2026-02-07T12:00:00Z | Author: Claude | Change: Initial implementation

Parses specifications and generates wiki documentation using local AI.
Integrates with Ollama for section-by-section analysis.

Features:
- Parse spec.md files into hierarchical sections (h2/h3)
- Run AI analysis on each section via Ollama
- Generate wiki pages with embedded analysis
- Update sidebar navigation automatically
- Integration with GitHub workflows

Usage:
    python slate/slate_spec_kit.py --process-all --wiki --analyze  # Full processing
    python slate/slate_spec_kit.py --wiki                          # Wiki only (no AI)
    python slate/slate_spec_kit.py --analyze                       # Analysis only
    python slate/slate_spec_kit.py --status                        # Show status
    python slate/slate_spec_kit.py --json                          # JSON output
"""

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

# Modified: 2026-02-07T12:00:00Z | Author: Claude | Change: workspace setup
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

SPECS_DIR = WORKSPACE_ROOT / "specs"
WIKI_DIR = WORKSPACE_ROOT / "docs" / "wiki"
STATE_FILE = WORKSPACE_ROOT / ".slate_spec_kit.json"
ANALYSIS_DIR_NAME = "analysis"


@dataclass
class SpecSection:
    """Represents a parsed section from a spec.md file."""

    level: int  # Heading level (2 = ##, 3 = ###)
    title: str  # Section title
    anchor: str  # URL-safe anchor (e.g., "design-principles")
    content: str  # Raw content of the section
    line_start: int  # Starting line number
    line_end: int  # Ending line number
    subsections: list["SpecSection"] = field(default_factory=list)
    analysis: Optional[dict[str, Any]] = None  # AI analysis results

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "level": self.level,
            "title": self.title,
            "anchor": self.anchor,
            "content_length": len(self.content),
            "line_range": [self.line_start, self.line_end],
            "subsections": [s.to_dict() for s in self.subsections],
            "analysis": self.analysis,
        }


@dataclass
class ParsedSpec:
    """Represents a fully parsed specification."""

    spec_id: str  # e.g., "006-natural-theme-system"
    spec_path: Path  # Full path to spec.md
    title: str  # Main title from spec
    metadata: dict[str, Any]  # Status, created, etc.
    sections: list[SpecSection]  # All top-level sections
    raw_content: str  # Original file content
    parsed_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def get_all_sections_flat(self) -> list[SpecSection]:
        """Return all sections flattened (for iteration)."""
        result = []
        for section in self.sections:
            result.append(section)
            result.extend(section.subsections)
        return result


class SpecParser:
    """Parses spec.md files into structured sections."""

    METADATA_PATTERN = re.compile(r"^\*\*([^*]+)\*\*:\s*(.+)$")
    HEADING_PATTERN = re.compile(r"^(#{2,6})\s+(.+)$")

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.specs_dir = SPECS_DIR

    def parse_metadata(self, content: str) -> dict[str, Any]:
        """Extract YAML-like metadata from spec header."""
        metadata = {}
        for line in content.split("\n")[:20]:  # Check first 20 lines
            match = self.METADATA_PATTERN.match(line)
            if match:
                key = match.group(1).strip().lower().replace(" ", "_")
                value = match.group(2).strip()
                metadata[key] = value
        return metadata

    def _make_anchor(self, title: str) -> str:
        """Convert title to URL-safe anchor."""
        anchor = title.lower()
        anchor = re.sub(r"[^\w\s-]", "", anchor)
        anchor = re.sub(r"\s+", "-", anchor)
        return anchor

    def parse_sections(self, content: str) -> list[SpecSection]:
        """Parse content into hierarchical sections."""
        lines = content.split("\n")
        sections: list[SpecSection] = []
        current_h2: Optional[SpecSection] = None
        current_h3: Optional[SpecSection] = None
        current_content_lines: list[str] = []

        for i, line in enumerate(lines):
            match = self.HEADING_PATTERN.match(line)
            if match:
                level = len(match.group(1))
                title = match.group(2).strip()

                # Save accumulated content to previous section
                if current_h3:
                    current_h3.content = "\n".join(current_content_lines).strip()
                    current_h3.line_end = i - 1
                elif current_h2:
                    current_h2.content = "\n".join(current_content_lines).strip()
                    current_h2.line_end = i - 1

                current_content_lines = []

                if level == 2:
                    new_section = SpecSection(
                        level=2,
                        title=title,
                        anchor=self._make_anchor(title),
                        content="",
                        line_start=i,
                        line_end=i,
                    )
                    sections.append(new_section)
                    current_h2 = new_section
                    current_h3 = None

                elif level == 3 and current_h2:
                    new_section = SpecSection(
                        level=3,
                        title=title,
                        anchor=self._make_anchor(title),
                        content="",
                        line_start=i,
                        line_end=i,
                    )
                    current_h2.subsections.append(new_section)
                    current_h3 = new_section
            else:
                current_content_lines.append(line)

        # Close final section
        if current_h3:
            current_h3.content = "\n".join(current_content_lines).strip()
            current_h3.line_end = len(lines) - 1
        elif current_h2:
            current_h2.content = "\n".join(current_content_lines).strip()
            current_h2.line_end = len(lines) - 1

        return sections

    def parse_spec(self, spec_path: Path) -> ParsedSpec:
        """Parse a complete spec.md file."""
        content = spec_path.read_text(encoding="utf-8")

        # Extract title from first H1
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        title = title_match.group(1) if title_match else spec_path.parent.name

        metadata = self.parse_metadata(content)
        sections = self.parse_sections(content)

        spec_id = metadata.get("spec_id", spec_path.parent.name)

        return ParsedSpec(
            spec_id=spec_id,
            spec_path=spec_path,
            title=title,
            metadata=metadata,
            sections=sections,
            raw_content=content,
        )

    def discover_specs(self) -> list[Path]:
        """Find all spec.md files in specs directory."""
        if not self.specs_dir.exists():
            return []
        return sorted(self.specs_dir.glob("*/spec.md"))


class WikiGenerator:
    """Generates wiki pages from parsed specifications."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.wiki_dir = WIKI_DIR
        self.wiki_dir.mkdir(parents=True, exist_ok=True)

    def _spec_id_to_wiki_filename(self, spec_id: str) -> str:
        """Convert spec ID to wiki filename."""
        # "006-natural-theme-system" -> "Spec-006-Natural-Theme-System.md"
        parts = spec_id.split("-")
        number = parts[0] if parts and parts[0].isdigit() else ""
        name = "-".join(parts[1:]) if len(parts) > 1 else spec_id
        name_titled = "-".join(word.capitalize() for word in name.split("-"))
        if number:
            return f"Spec-{number}-{name_titled}.md"
        return f"Spec-{name_titled}.md"

    def generate_spec_page(self, spec: ParsedSpec, include_analysis: bool = True) -> str:
        """Generate wiki markdown for a parsed spec."""
        lines = [
            f"# {spec.title}",
            f"<!-- Auto-generated from specs/{spec.spec_id}/spec.md -->",
            f"<!-- Generated: {datetime.now(timezone.utc).isoformat()} -->",
            "",
        ]

        # Add metadata table
        if spec.metadata:
            lines.append("| Property | Value |")
            lines.append("|----------|-------|")
            for key, value in spec.metadata.items():
                lines.append(f"| **{key.replace('_', ' ').title()}** | {value} |")
            lines.append("")

        # Add navigation
        lines.append("## Contents")
        lines.append("")
        for section in spec.sections:
            lines.append(f"- [{section.title}](#{section.anchor})")
            for sub in section.subsections:
                lines.append(f"  - [{sub.title}](#{sub.anchor})")
        lines.append("")
        lines.append("---")
        lines.append("")

        # Add sections
        for section in spec.sections:
            lines.append(f"## {section.title}")
            lines.append("")
            if section.content:
                lines.append(section.content)
                lines.append("")

            # Add analysis if available
            if include_analysis and section.analysis and not section.analysis.get("error"):
                lines.append("<details>")
                lines.append("<summary>AI Analysis</summary>")
                lines.append("")
                if section.analysis.get("requirements"):
                    reqs = section.analysis["requirements"]
                    if isinstance(reqs, list):
                        lines.append(f"> **Requirements**: {', '.join(reqs[:3])}")
                    else:
                        lines.append(f"> **Requirements**: {reqs}")
                if section.analysis.get("implementation_notes"):
                    lines.append(f"> **Implementation Notes**: {section.analysis['implementation_notes'][:200]}")
                if section.analysis.get("risks"):
                    risks = section.analysis["risks"]
                    if isinstance(risks, list):
                        lines.append(f"> **Risks**: {', '.join(risks[:3])}")
                    else:
                        lines.append(f"> **Risks**: {risks}")
                lines.append("")
                lines.append("</details>")
                lines.append("")

            # Add subsections
            for sub in section.subsections:
                lines.append(f"### {sub.title}")
                lines.append("")
                if sub.content:
                    lines.append(sub.content)
                    lines.append("")

                if include_analysis and sub.analysis and sub.analysis.get("summary"):
                    lines.append(f"> *AI Note*: {sub.analysis['summary'][:200]}")
                    lines.append("")

        # Footer
        lines.append("---")
        lines.append(f"*Source: [specs/{spec.spec_id}/spec.md](../../../specs/{spec.spec_id}/spec.md)*")
        lines.append("")

        return "\n".join(lines)

    def write_spec_page(self, spec: ParsedSpec, include_analysis: bool = True) -> Path:
        """Write wiki page for a spec."""
        filename = self._spec_id_to_wiki_filename(spec.spec_id)
        wiki_path = self.wiki_dir / filename
        content = self.generate_spec_page(spec, include_analysis)
        wiki_path.write_text(content, encoding="utf-8")
        return wiki_path

    def update_sidebar(self, specs: list[ParsedSpec]) -> Path:
        """Update _Sidebar.md with spec links."""
        sidebar_path = self.wiki_dir / "_Sidebar.md"

        # Read existing sidebar
        if sidebar_path.exists():
            existing = sidebar_path.read_text(encoding="utf-8")
        else:
            existing = "# Navigation\n\n**[Home](Home)**\n"

        # Check if specs section exists
        if "## Specifications" not in existing:
            # Add specs section before "## Advanced"
            new_section = "\n## Specifications\n"
            for spec in specs:
                filename = self._spec_id_to_wiki_filename(spec.spec_id)
                page_name = filename.replace(".md", "")
                status = spec.metadata.get("status", "unknown")
                status_icon = "+" if status == "completed" else "o"
                new_section += f"- [{status_icon}] [{spec.title.replace('Specification: ', '')}]({page_name})\n"

            # Insert before "## Advanced" or at end
            if "## Advanced" in existing:
                existing = existing.replace("## Advanced", new_section + "\n## Advanced")
            else:
                existing += new_section
        else:
            # Update existing specs section
            lines = existing.split("\n")
            new_lines = []
            in_specs_section = False

            for line in lines:
                if line.startswith("## Specifications"):
                    in_specs_section = True
                    new_lines.append(line)
                    for spec in specs:
                        filename = self._spec_id_to_wiki_filename(spec.spec_id)
                        page_name = filename.replace(".md", "")
                        status = spec.metadata.get("status", "unknown")
                        status_icon = "+" if status == "completed" else "o"
                        new_lines.append(f"- [{status_icon}] [{spec.title.replace('Specification: ', '')}]({page_name})")
                elif in_specs_section and line.startswith("## "):
                    in_specs_section = False
                    new_lines.append(line)
                elif not in_specs_section:
                    new_lines.append(line)

            existing = "\n".join(new_lines)

        sidebar_path.write_text(existing, encoding="utf-8")
        return sidebar_path


class SpecKitRunner:
    """Runs AI analysis on spec sections using Ollama."""

    SYSTEM_PROMPT = """You are a software architect analyzing a specification section.
For each section, provide a structured analysis in JSON format with these fields:
- requirements: Key requirements extracted from this section (list of strings)
- implementation_notes: Technical considerations for implementation (string)
- risks: Potential risks or challenges (list of strings)
- dependencies: External dependencies mentioned (list of strings)
- summary: One-sentence summary of this section (string)

Respond ONLY with valid JSON, no markdown formatting or code blocks."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.ollama = None  # Lazy-loaded

    def _get_ollama(self):
        """Lazy-load Ollama client from ml_orchestrator."""
        if self.ollama is None:
            try:
                from slate.ml_orchestrator import OllamaClient
                self.ollama = OllamaClient()
            except ImportError:
                # Fallback: minimal OllamaClient
                self.ollama = self._create_minimal_client()
        return self.ollama

    def _create_minimal_client(self):
        """Create a minimal Ollama client if ml_orchestrator unavailable."""
        import urllib.request
        import urllib.error

        class MinimalOllamaClient:
            def __init__(self):
                self.base_url = "http://127.0.0.1:11434"

            def is_running(self) -> bool:
                try:
                    req = urllib.request.Request(f"{self.base_url}/api/tags")
                    urllib.request.urlopen(req, timeout=3)
                    return True
                except Exception:
                    return False

            def generate(self, model: str, prompt: str, system: str = "",
                        temperature: float = 0.7, max_tokens: int = 2048,
                        stream: bool = False, keep_alive: str = "24h") -> dict:
                data = {
                    "model": model,
                    "prompt": prompt,
                    "stream": stream,
                    "keep_alive": keep_alive,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                }
                if system:
                    data["system"] = system
                body = json.dumps(data).encode("utf-8")
                req = urllib.request.Request(
                    f"{self.base_url}/api/generate",
                    data=body,
                    headers={"Content-Type": "application/json"}
                )
                resp = urllib.request.urlopen(req, timeout=300)
                return json.loads(resp.read().decode("utf-8"))

        return MinimalOllamaClient()

    def analyze_section(self, section: SpecSection, spec_context: str = "") -> dict[str, Any]:
        """Run AI analysis on a single section."""
        ollama = self._get_ollama()

        if not ollama.is_running():
            return {"error": "Ollama not available"}

        prompt = f"""Analyze this specification section:

Title: {section.title}
Level: {"##" if section.level == 2 else "###"}

Content:
{section.content[:3000]}

Context: {spec_context[:500]}

Provide structured analysis in JSON format."""

        try:
            result = ollama.generate(
                model="mistral-nemo:latest",
                prompt=prompt,
                system=self.SYSTEM_PROMPT,
                temperature=0.3,
                max_tokens=1024,
            )

            response = result.get("response", "")

            # Parse JSON from response
            try:
                # Clean response - remove markdown code blocks if present
                response = response.strip()
                if response.startswith("```"):
                    response = re.sub(r"```(?:json)?\n?", "", response)
                    response = response.rstrip("`")

                analysis = json.loads(response)
                return analysis
            except json.JSONDecodeError:
                return {
                    "summary": response[:200],
                    "requirements": [],
                    "implementation_notes": "Could not parse structured analysis",
                    "risks": [],
                    "dependencies": [],
                }
        except Exception as e:
            return {"error": str(e)}

    def analyze_spec(self, spec: ParsedSpec, save_results: bool = True) -> ParsedSpec:
        """Analyze all sections in a spec."""
        context = f"Spec: {spec.title}. Status: {spec.metadata.get('status', 'unknown')}."

        for section in spec.sections:
            print(f"    Analyzing: {section.title}")
            section.analysis = self.analyze_section(section, context)

            for subsection in section.subsections:
                print(f"      Analyzing: {subsection.title}")
                subsection.analysis = self.analyze_section(
                    subsection,
                    f"{context} Parent: {section.title}"
                )

        if save_results:
            self._save_analysis(spec)

        return spec

    def _save_analysis(self, spec: ParsedSpec):
        """Save analysis results to specs/*/analysis/."""
        analysis_dir = spec.spec_path.parent / ANALYSIS_DIR_NAME
        analysis_dir.mkdir(exist_ok=True)

        analysis_data = {
            "spec_id": spec.spec_id,
            "analyzed_at": datetime.now(timezone.utc).isoformat(),
            "sections": [s.to_dict() for s in spec.sections],
        }

        analysis_path = analysis_dir / "section_analysis.json"
        analysis_path.write_text(json.dumps(analysis_data, indent=2), encoding="utf-8")


class SpecKitOrchestrator:
    """Main orchestrator for Spec-Kit Wiki Integration."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.parser = SpecParser()
        self.wiki = WikiGenerator()
        self.runner = SpecKitRunner()
        self.state = self._load_state()

    def _load_state(self) -> dict[str, Any]:
        """Load persistent state."""
        if STATE_FILE.exists():
            try:
                return json.loads(STATE_FILE.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {
            "last_run": None,
            "specs_processed": 0,
            "wiki_pages_generated": 0,
            "sections_analyzed": 0,
        }

    def _save_state(self):
        """Save persistent state."""
        self.state["last_run"] = datetime.now(timezone.utc).isoformat()
        STATE_FILE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    def process_all(self, analyze: bool = True, wiki: bool = True) -> dict[str, Any]:
        """Process all specs: parse, analyze, generate wiki."""
        print()
        print("=" * 70)
        print("  SLATE Spec-Kit Wiki Integration")
        print("=" * 70)
        print()

        spec_paths = self.parser.discover_specs()
        if not spec_paths:
            print("  No specs found in specs/*/spec.md")
            return {"success": False, "error": "No specs found"}

        print(f"  Found {len(spec_paths)} specifications")
        print()

        results: dict[str, Any] = {
            "success": True,
            "specs_processed": 0,
            "sections_analyzed": 0,
            "wiki_pages_generated": 0,
            "specs": [],
        }

        parsed_specs = []

        for spec_path in spec_paths:
            spec_id = spec_path.parent.name
            print(f"  Processing: {spec_id}")

            # Parse
            spec = self.parser.parse_spec(spec_path)
            print(f"    Parsed {len(spec.sections)} sections")
            results["specs_processed"] += 1

            # Analyze
            if analyze:
                print("    Running AI analysis...")
                spec = self.runner.analyze_spec(spec, save_results=True)
                section_count = len(spec.get_all_sections_flat())
                results["sections_analyzed"] += section_count
                print(f"    Analyzed {section_count} sections")

            parsed_specs.append(spec)

            # Generate wiki page
            if wiki:
                wiki_path = self.wiki.write_spec_page(spec, include_analysis=analyze)
                print(f"    Wiki page: {wiki_path.relative_to(self.workspace)}")
                results["wiki_pages_generated"] += 1

            results["specs"].append({
                "spec_id": spec.spec_id,
                "title": spec.title,
                "status": spec.metadata.get("status"),
                "sections": len(spec.sections),
            })
            print()

        # Update sidebar
        if wiki and parsed_specs:
            sidebar_path = self.wiki.update_sidebar(parsed_specs)
            print(f"  Updated sidebar: {sidebar_path.relative_to(self.workspace)}")

        self.state["specs_processed"] += results["specs_processed"]
        self.state["sections_analyzed"] += results["sections_analyzed"]
        self.state["wiki_pages_generated"] += results["wiki_pages_generated"]
        self._save_state()

        print()
        print("=" * 70)
        print(f"  Processed: {results['specs_processed']} specs")
        print(f"  Analyzed: {results['sections_analyzed']} sections")
        print(f"  Generated: {results['wiki_pages_generated']} wiki pages")
        print("=" * 70)

        return results

    def print_status(self):
        """Print spec-kit status."""
        print()
        print("=" * 70)
        print("  SLATE Spec-Kit Status")
        print("=" * 70)
        print()
        print(f"  Last Run: {self.state.get('last_run', 'Never')}")
        print(f"  Specs Processed: {self.state.get('specs_processed', 0)}")
        print(f"  Sections Analyzed: {self.state.get('sections_analyzed', 0)}")
        print(f"  Wiki Pages Generated: {self.state.get('wiki_pages_generated', 0)}")
        print()

        # List current specs
        spec_paths = self.parser.discover_specs()
        print(f"  Current Specs ({len(spec_paths)}):")
        for spec_path in spec_paths:
            spec = self.parser.parse_spec(spec_path)
            status = spec.metadata.get("status", "unknown")
            title = spec.title[:40]
            print(f"    [{status:>12}] {spec.spec_id}: {title}")

        print()
        print("=" * 70)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="SLATE Spec-Kit Wiki Integration",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
    python slate/slate_spec_kit.py --process-all --wiki --analyze
    python slate/slate_spec_kit.py --wiki
    python slate/slate_spec_kit.py --status
    python slate/slate_spec_kit.py --json
        """
    )
    parser.add_argument("--process-all", action="store_true", help="Process all specs")
    parser.add_argument("--wiki", action="store_true", help="Generate wiki pages")
    parser.add_argument("--analyze", action="store_true", help="Run AI analysis on sections")
    parser.add_argument("--status", action="store_true", help="Show spec-kit status")
    parser.add_argument("--list", action="store_true", help="List all specifications")
    parser.add_argument("--roadmap", action="store_true", help="Show development roadmap from specs")
    parser.add_argument("--brief", action="store_true", help="Brief output (spec names only)")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    parser.add_argument("--spec", type=str, help="Process a specific spec ID")

    args = parser.parse_args()
    orchestrator = SpecKitOrchestrator()

    if args.list:
        # List all specifications
        specs = orchestrator.get_all_specs() if hasattr(orchestrator, 'get_all_specs') else []
        # Fallback: scan specs directory
        if not specs:
            specs_dir = orchestrator.workspace / "specs"
            specs = []
            if specs_dir.exists():
                for spec_dir in sorted(specs_dir.iterdir()):
                    if spec_dir.is_dir() and not spec_dir.name.startswith('.'):
                        spec_md = spec_dir / "spec.md"
                        name = spec_dir.name
                        if spec_md.exists():
                            try:
                                content = spec_md.read_text(encoding="utf-8")[:500]
                                title_match = content.split('\n')[0].strip('#').strip()
                                name = title_match or spec_dir.name
                            except Exception:
                                pass
                        specs.append({"id": spec_dir.name, "name": name})

        if args.json:
            print(json.dumps(specs, indent=2))
        elif args.brief:
            # Brief output: just names on one line
            names = [s.get("name", s.get("id", "?")) for s in specs]
            print(", ".join(names) if names else "none")
        else:
            print("Specifications:")
            print("-" * 50)
            for s in specs:
                print(f"  [{s.get('id', '?')}] {s.get('name', 'Untitled')}")

    elif args.roadmap:
        # Extract roadmap from specs
        specs_dir = orchestrator.workspace / "specs"
        roadmap = []
        if specs_dir.exists():
            for spec_dir in sorted(specs_dir.iterdir()):
                if spec_dir.is_dir() and not spec_dir.name.startswith('.'):
                    spec_md = spec_dir / "spec.md"
                    tasks_md = spec_dir / "tasks.md"
                    if spec_md.exists():
                        try:
                            content = spec_md.read_text(encoding="utf-8")[:1000]
                            title_match = content.split('\n')[0].strip('#').strip()
                            # Count tasks if available
                            task_count = 0
                            if tasks_md.exists():
                                tasks_content = tasks_md.read_text(encoding="utf-8")
                                task_count = tasks_content.count("- [")
                            roadmap.append({
                                "spec_id": spec_dir.name,
                                "title": title_match or spec_dir.name,
                                "task_count": task_count,
                            })
                        except Exception:
                            pass

        if args.json:
            print(json.dumps(roadmap, indent=2))
        else:
            print("Development Roadmap:")
            print("-" * 50)
            for r in roadmap:
                tasks_str = f"({r['task_count']} tasks)" if r.get('task_count') else ""
                print(f"  {r['spec_id']}: {r['title']} {tasks_str}")

    elif args.process_all:
        results = orchestrator.process_all(
            analyze=args.analyze,
            wiki=args.wiki,
        )
        if args.json:
            print(json.dumps(results, indent=2, default=str))
    elif args.status:
        if args.json:
            print(json.dumps(orchestrator.state, indent=2, default=str))
        else:
            orchestrator.print_status()
    else:
        orchestrator.print_status()


if __name__ == "__main__":
    main()
