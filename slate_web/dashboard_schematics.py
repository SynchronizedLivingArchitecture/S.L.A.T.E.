#!/usr/bin/env python3
# Modified: 2026-02-07T15:00:00Z | Author: COPILOT | Change: Create dashboard schematic integration
"""
SLATE Dashboard Schematic Integration

Provides pre-built, embeddable schematics for the SLATE dashboard.
Uses the schematic SDK to generate inline SVGs that can be embedded
in the dashboard HTML template.

Design principles:
  1. Generate SVGs that match dashboard theme (copper accents, dark substrate)
  2. Provide base64-encoded versions for inline embedding
  3. Support dynamic/live schematics that update with system state
  4. Reuse the same schematics used on the GitHub Pages website
"""

import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Ensure workspace root is in path
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.schematic_sdk import (
    SchematicEngine,
    SchematicConfig,
    ServiceNode,
    DatabaseNode,
    GPUNode,
    AINode,
    QueueNode,
    ExternalNode,
    FlowConnector,
    DashedConnector,
    ComponentStatus,
    Base64Exporter,
    DarkTheme,
)


class DashboardSchematicGenerator:
    """
    Generates embeddable schematics for the SLATE dashboard.

    Usage:
        generator = DashboardSchematicGenerator()
        svg = generator.system_overview()
        base64_uri = generator.system_overview_base64()
    """

    def __init__(self, theme: str = "dark"):
        """Initialize with theme settings."""
        self.theme = theme
        self._cache: Dict[str, str] = {}

    def _get_engine(self, title: str, width: int = 800, height: int = 400) -> SchematicEngine:
        """Create a configured schematic engine."""
        config = SchematicConfig(
            title=title,
            width=width,
            height=height,
            theme="dark",
            show_grid=True,
            show_legend=False,  # Compact for dashboard
            margin=20,
        )
        return SchematicEngine(config)

    def system_overview(self, compact: bool = True) -> str:
        """
        Generate the main system overview schematic.

        Shows: Dashboard -> Orchestrator -> AI Backends -> GPU

        Args:
            compact: If True, generate a smaller version for dashboard cards

        Returns:
            SVG string
        """
        cache_key = f"system_overview_{compact}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        size = (600, 300) if compact else (900, 500)
        engine = self._get_engine("System Overview", size[0], size[1])

        # Presentation layer
        engine.add_node(ServiceNode(
            id="dashboard",
            label="Dashboard",
            sublabel=":8080",
            layer=0,
            status=ComponentStatus.ACTIVE,
        ))

        engine.add_node(ServiceNode(
            id="cli",
            label="CLI Tools",
            sublabel="slate/",
            layer=0,
        ))

        # Orchestration layer
        engine.add_node(ServiceNode(
            id="orchestrator",
            label="Orchestrator",
            sublabel="Task Router",
            layer=1,
        ))

        # AI Backend layer
        engine.add_node(AINode(
            id="ollama",
            label="Ollama",
            sublabel=":11434",
            layer=2,
            status=ComponentStatus.ACTIVE,
        ))

        engine.add_node(AINode(
            id="foundry",
            label="Foundry Local",
            sublabel=":5272",
            layer=2,
        ))

        # GPU layer
        engine.add_node(GPUNode(
            id="gpu",
            label="Your GPU(s)",
            sublabel="Auto-Detected",
            layer=3,
        ))

        # Connections
        engine.add_connector(FlowConnector(from_node="dashboard", to_node="orchestrator"))
        engine.add_connector(FlowConnector(from_node="cli", to_node="orchestrator"))
        engine.add_connector(FlowConnector(from_node="orchestrator", to_node="ollama"))
        engine.add_connector(FlowConnector(from_node="orchestrator", to_node="foundry"))
        engine.add_connector(FlowConnector(from_node="ollama", to_node="gpu"))
        engine.add_connector(FlowConnector(from_node="foundry", to_node="gpu"))

        svg = engine.render_svg()
        self._cache[cache_key] = svg
        return svg

    def ai_pipeline(self, compact: bool = True) -> str:
        """
        Generate the AI inference pipeline schematic.

        Shows task routing through AI backends.

        Returns:
            SVG string
        """
        cache_key = f"ai_pipeline_{compact}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        size = (600, 280) if compact else (900, 450)
        engine = self._get_engine("AI Inference Pipeline", size[0], size[1])

        # Input
        engine.add_node(QueueNode(
            id="tasks",
            label="Task Queue",
            sublabel="current_tasks.json",
            layer=0,
        ))

        # Router
        engine.add_node(ServiceNode(
            id="router",
            label="Task Router",
            sublabel="Unified Backend",
            layer=1,
        ))

        # AI Backends
        engine.add_node(AINode(
            id="ollama",
            label="Ollama",
            sublabel="mistral-nemo",
            layer=2,
            status=ComponentStatus.ACTIVE,
        ))

        engine.add_node(AINode(
            id="foundry",
            label="Foundry",
            sublabel="ONNX Models",
            layer=2,
        ))

        # Vector store
        engine.add_node(DatabaseNode(
            id="chromadb",
            label="ChromaDB",
            sublabel="RAG Memory",
            layer=2,
        ))

        # Output
        engine.add_node(ServiceNode(
            id="output",
            label="Results",
            sublabel="Processed",
            layer=3,
        ))

        # Connections
        engine.add_connector(FlowConnector(from_node="tasks", to_node="router"))
        engine.add_connector(FlowConnector(from_node="router", to_node="ollama"))
        engine.add_connector(FlowConnector(from_node="router", to_node="foundry"))
        engine.add_connector(DashedConnector(from_node="router", to_node="chromadb"))
        engine.add_connector(FlowConnector(from_node="ollama", to_node="output"))
        engine.add_connector(FlowConnector(from_node="foundry", to_node="output"))

        svg = engine.render_svg()
        self._cache[cache_key] = svg
        return svg

    def github_integration(self, compact: bool = True) -> str:
        """
        Generate the GitHub integration schematic.

        Shows workflow execution pipeline.

        Returns:
            SVG string
        """
        cache_key = f"github_integration_{compact}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        size = (600, 280) if compact else (900, 450)
        engine = self._get_engine("GitHub Integration", size[0], size[1])

        # GitHub
        engine.add_node(ExternalNode(
            id="github",
            label="GitHub",
            sublabel="Repository",
            layer=0,
        ))

        # Workflows
        engine.add_node(ServiceNode(
            id="workflows",
            label="Actions",
            sublabel="CI/CD",
            layer=1,
        ))

        # Runner
        engine.add_node(ServiceNode(
            id="runner",
            label="Self-Hosted",
            sublabel="Runner",
            layer=2,
            status=ComponentStatus.ACTIVE,
        ))

        # Task execution
        engine.add_node(ServiceNode(
            id="executor",
            label="Task Executor",
            sublabel="GPU Labels",
            layer=3,
        ))

        # Connections
        engine.add_connector(FlowConnector(from_node="github", to_node="workflows"))
        engine.add_connector(FlowConnector(from_node="workflows", to_node="runner"))
        engine.add_connector(FlowConnector(from_node="runner", to_node="executor"))

        svg = engine.render_svg()
        self._cache[cache_key] = svg
        return svg

    def multi_runner(self, compact: bool = True) -> str:
        """
        Generate the multi-runner system schematic.

        Shows parallel execution across GPUs.

        Returns:
            SVG string
        """
        cache_key = f"multi_runner_{compact}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        size = (600, 280) if compact else (900, 450)
        engine = self._get_engine("Multi-Runner System", size[0], size[1])

        # Scheduler
        engine.add_node(ServiceNode(
            id="scheduler",
            label="GPU Scheduler",
            sublabel="Load Balancer",
            layer=0,
        ))

        # Runners
        engine.add_node(ServiceNode(
            id="gpu_runner",
            label="GPU Runners",
            sublabel="Scales to hardware",
            layer=1,
            status=ComponentStatus.ACTIVE,
        ))

        engine.add_node(ServiceNode(
            id="cpu_runner",
            label="CPU Runners",
            sublabel="Fallback",
            layer=1,
        ))

        # GPUs
        engine.add_node(GPUNode(
            id="gpu0",
            label="GPU 0",
            sublabel="Primary",
            layer=2,
        ))

        engine.add_node(GPUNode(
            id="gpuN",
            label="GPU N",
            sublabel="Multi-GPU",
            layer=2,
        ))

        # Connections
        engine.add_connector(FlowConnector(from_node="scheduler", to_node="gpu_runner"))
        engine.add_connector(FlowConnector(from_node="scheduler", to_node="cpu_runner"))
        engine.add_connector(FlowConnector(from_node="gpu_runner", to_node="gpu0"))
        engine.add_connector(FlowConnector(from_node="gpu_runner", to_node="gpuN"))

        svg = engine.render_svg()
        self._cache[cache_key] = svg
        return svg

    def get_all_schematics(self, compact: bool = True) -> Dict[str, str]:
        """
        Get all available dashboard schematics.

        Returns:
            Dict mapping schematic names to SVG strings
        """
        return {
            "system_overview": self.system_overview(compact),
            "ai_pipeline": self.ai_pipeline(compact),
            "github_integration": self.github_integration(compact),
            "multi_runner": self.multi_runner(compact),
        }

    def get_all_base64(self, compact: bool = True) -> Dict[str, str]:
        """
        Get all schematics as base64 data URIs for inline embedding.

        Returns:
            Dict mapping schematic names to base64 data URIs
        """
        schematics = self.get_all_schematics(compact)
        return {
            name: Base64Exporter.encode(svg)
            for name, svg in schematics.items()
        }


# Singleton instance for dashboard use
_generator: Optional[DashboardSchematicGenerator] = None


def get_generator() -> DashboardSchematicGenerator:
    """Get the singleton schematic generator instance."""
    global _generator
    if _generator is None:
        _generator = DashboardSchematicGenerator()
    return _generator


def system_overview_svg(compact: bool = True) -> str:
    """Get the system overview schematic SVG."""
    return get_generator().system_overview(compact)


def system_overview_base64(compact: bool = True) -> str:
    """Get the system overview schematic as base64 data URI."""
    return Base64Exporter.encode(system_overview_svg(compact))


def ai_pipeline_svg(compact: bool = True) -> str:
    """Get the AI pipeline schematic SVG."""
    return get_generator().ai_pipeline(compact)


def ai_pipeline_base64(compact: bool = True) -> str:
    """Get the AI pipeline schematic as base64 data URI."""
    return Base64Exporter.encode(ai_pipeline_svg(compact))


def github_integration_svg(compact: bool = True) -> str:
    """Get the GitHub integration schematic SVG."""
    return get_generator().github_integration(compact)


def github_integration_base64(compact: bool = True) -> str:
    """Get the GitHub integration schematic as base64 data URI."""
    return Base64Exporter.encode(github_integration_svg(compact))


def multi_runner_svg(compact: bool = True) -> str:
    """Get the multi-runner schematic SVG."""
    return get_generator().multi_runner(compact)


def multi_runner_base64(compact: bool = True) -> str:
    """Get the multi-runner schematic as base64 data URI."""
    return Base64Exporter.encode(multi_runner_svg(compact))


def all_schematics_base64(compact: bool = True) -> Dict[str, str]:
    """Get all schematics as base64 data URIs."""
    return get_generator().get_all_base64(compact)


# CLI interface
if __name__ == "__main__":
    import json

    print("SLATE Dashboard Schematic Generator")
    print("=" * 40)

    generator = DashboardSchematicGenerator()
    schematics = generator.get_all_schematics(compact=True)

    for name, svg in schematics.items():
        print(f"\n{name}:")
        print(f"  SVG size: {len(svg):,} bytes")

    print("\n\nBase64 data URIs available for inline embedding.")
    print("Import from slate_web.dashboard_schematics to use.")
