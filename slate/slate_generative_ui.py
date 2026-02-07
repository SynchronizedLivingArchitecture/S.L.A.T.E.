#!/usr/bin/env python3
# Modified: 2026-02-08T03:30:00Z | Author: Claude Opus 4.5 | Change: Add schematic protocol integration
"""
SLATE Generative UI Engine
============================
AI-powered generative interface components for the SLATE onboarding experience.

Features:
- Dynamic AI narration via local Ollama
- Generative step descriptions
- Adaptive UI recommendations
- Real-time system analysis
- Personalized onboarding paths
- Schematic diagram generation (Spec 012)

Usage:
    python slate/slate_generative_ui.py --status
    python slate/slate_generative_ui.py --narrate "System Scan"
    python slate/slate_generative_ui.py --generate-step "ai-backends"
    python slate/slate_generative_ui.py --analyze-system
    python slate/slate_generative_ui.py --schematic "system"
"""

import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

logger = logging.getLogger("slate.generative_ui")

# ── Schematic SDK Import ─────────────────────────────────────────────────────

try:
    from slate.schematic_sdk import (
        SchematicEngine,
        SchematicConfig,
        ComponentStatus,
        generate_from_system_state,
        generate_from_tech_tree,
    )
    from slate.schematic_sdk.library import (
        TEMPLATES,
        build_from_template,
        slate_dashboard,
        slate_ollama,
        slate_chromadb,
        slate_dual_gpu,
        slate_runner,
    )
    SCHEMATIC_SDK_AVAILABLE = True
except ImportError:
    SCHEMATIC_SDK_AVAILABLE = False
    logger.info("Schematic SDK not available - schematic features disabled")

# ── Design Tokens (from spec 007) ────────────────────────────────────────────

DESIGN_TOKENS = {
    "colors": {
        "primary": "#B85A3C",
        "primary_light": "#D4785A",
        "primary_dark": "#8B4530",
        "blueprint_bg": "#0D1B2A",
        "blueprint_grid": "#1B3A4B",
        "blueprint_accent": "#98C1D9",
        "blueprint_node": "#E0FBFC",
        "status_active": "#22C55E",
        "status_pending": "#F59E0B",
        "status_error": "#EF4444",
        "status_inactive": "#6B7280",
    },
    "typography": {
        "font_display": "'Segoe UI', 'Inter', system-ui, sans-serif",
        "font_mono": "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace",
    },
    "spacing": {
        "xs": "4px",
        "sm": "8px",
        "md": "16px",
        "lg": "24px",
        "xl": "32px",
        "2xl": "48px",
    },
}


# ── Onboarding Steps ─────────────────────────────────────────────────────────

class OnboardingStep(Enum):
    """Guided onboarding steps."""
    WELCOME = "welcome"
    SYSTEM_SCAN = "system-scan"
    CORE_SERVICES = "core-services"
    AI_BACKENDS = "ai-backends"
    INTEGRATIONS = "integrations"
    VALIDATION = "validation"
    COMPLETE = "complete"


STEP_METADATA = {
    OnboardingStep.WELCOME: {
        "title": "Welcome to SLATE",
        "icon": "rocket",
        "description": "AI-powered local development environment",
        "duration_estimate": 5,
        "ai_focus": "greeting",
    },
    OnboardingStep.SYSTEM_SCAN: {
        "title": "System Scan",
        "icon": "search",
        "description": "Detecting installed services and capabilities",
        "duration_estimate": 15,
        "ai_focus": "detection",
    },
    OnboardingStep.CORE_SERVICES: {
        "title": "Core Services",
        "icon": "server",
        "description": "Configuring SLATE core infrastructure",
        "duration_estimate": 30,
        "ai_focus": "configuration",
    },
    OnboardingStep.AI_BACKENDS: {
        "title": "AI Backends",
        "icon": "brain",
        "description": "Setting up local AI inference",
        "duration_estimate": 20,
        "ai_focus": "ai_setup",
    },
    OnboardingStep.INTEGRATIONS: {
        "title": "Integrations",
        "icon": "link",
        "description": "Connecting external services",
        "duration_estimate": 15,
        "ai_focus": "integration",
    },
    OnboardingStep.VALIDATION: {
        "title": "Validation",
        "icon": "check-circle",
        "description": "Running comprehensive checks",
        "duration_estimate": 20,
        "ai_focus": "validation",
    },
    OnboardingStep.COMPLETE: {
        "title": "Setup Complete",
        "icon": "party",
        "description": "Your SLATE system is ready!",
        "duration_estimate": 5,
        "ai_focus": "celebration",
    },
}


# ── Data Classes ─────────────────────────────────────────────────────────────

@dataclass
class SystemAnalysis:
    """Results from system analysis."""
    python_version: Optional[str] = None
    gpu_count: int = 0
    gpu_models: List[str] = field(default_factory=list)
    total_vram_gb: float = 0.0
    ollama_available: bool = False
    ollama_models: List[str] = field(default_factory=list)
    docker_available: bool = False
    github_authenticated: bool = False
    venv_exists: bool = False
    slate_installed: bool = False
    recommendations: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GeneratedContent:
    """AI-generated UI content."""
    narration: str = ""
    step_description: str = ""
    recommendations: List[str] = field(default_factory=list)
    css_overrides: Dict[str, str] = field(default_factory=dict)
    animation_hints: List[str] = field(default_factory=list)
    schematic_svg: str = ""  # Optional schematic for the step
    generated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ── Schematic Protocol (Spec 012) ─────────────────────────────────────────────

@dataclass
class SchematicProtocol:
    """
    Schematic generation protocol for Generative UI.

    Provides step-specific schematic diagrams that visually represent
    system state during onboarding and dashboard visualization.
    """
    template: str = "system"
    title: str = "SLATE Architecture"
    width: int = 900
    height: int = 500
    highlight_components: List[str] = field(default_factory=list)
    status_overrides: Dict[str, str] = field(default_factory=dict)

    def generate_svg(self) -> str:
        """Generate SVG for this schematic configuration."""
        if not SCHEMATIC_SDK_AVAILABLE:
            return self._fallback_svg()

        try:
            if self.template in TEMPLATES:
                return build_from_template(self.template)
            elif self.template == "system-state":
                return generate_from_system_state()
            elif self.template == "tech-tree":
                return generate_from_tech_tree()
            else:
                return self._generate_custom()
        except Exception as e:
            logger.warning(f"Schematic generation failed: {e}")
            return self._fallback_svg()

    def _generate_custom(self) -> str:
        """Generate a custom schematic with status overrides."""
        if not SCHEMATIC_SDK_AVAILABLE:
            return self._fallback_svg()

        config = SchematicConfig(
            title=self.title,
            width=self.width,
            height=self.height,
            theme="blueprint",
            layout="hierarchical",
        )
        engine = SchematicEngine(config)

        # Map status strings to ComponentStatus
        status_map = {
            "active": ComponentStatus.ACTIVE,
            "pending": ComponentStatus.PENDING,
            "error": ComponentStatus.ERROR,
            "inactive": ComponentStatus.INACTIVE,
        }

        # Add SLATE components with status overrides
        overrides = self.status_overrides
        engine.add_node(slate_dashboard(status_map.get(overrides.get("dashboard", "active"), ComponentStatus.ACTIVE)))
        engine.add_node(slate_ollama(status_map.get(overrides.get("ollama", "active"), ComponentStatus.ACTIVE)))
        engine.add_node(slate_chromadb(status_map.get(overrides.get("chromadb", "inactive"), ComponentStatus.INACTIVE)))
        engine.add_node(slate_dual_gpu(status_map.get(overrides.get("gpu", "active"), ComponentStatus.ACTIVE)))
        engine.add_node(slate_runner(status_map.get(overrides.get("runner", "active"), ComponentStatus.ACTIVE)))

        return engine.render_svg()

    def _fallback_svg(self) -> str:
        """Return a simple placeholder SVG when SDK is unavailable."""
        return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {self.width} {self.height}">
            <rect width="100%" height="100%" fill="#0D1B2A"/>
            <text x="50%" y="50%" text-anchor="middle" fill="#E8E2DE" font-family="Segoe UI" font-size="16">
                {self.title}
            </text>
            <text x="50%" y="60%" text-anchor="middle" fill="#6B7280" font-family="Consolas" font-size="12">
                Schematic SDK Loading...
            </text>
        </svg>'''


# Step-specific schematic configurations
STEP_SCHEMATICS: Dict[OnboardingStep, SchematicProtocol] = {
    OnboardingStep.WELCOME: SchematicProtocol(
        template="system",
        title="SLATE Overview",
        highlight_components=["dashboard"],
    ),
    OnboardingStep.SYSTEM_SCAN: SchematicProtocol(
        template="system-state",
        title="System Scan",
        status_overrides={"dashboard": "active", "ollama": "pending", "gpu": "pending"},
    ),
    OnboardingStep.CORE_SERVICES: SchematicProtocol(
        template="system",
        title="Core Services",
        highlight_components=["dashboard", "runner", "task-router"],
    ),
    OnboardingStep.AI_BACKENDS: SchematicProtocol(
        template="inference",
        title="AI Backends",
        highlight_components=["ollama", "gpu-cluster"],
    ),
    OnboardingStep.INTEGRATIONS: SchematicProtocol(
        template="cicd",
        title="Integrations",
        highlight_components=["github", "runner"],
    ),
    OnboardingStep.VALIDATION: SchematicProtocol(
        template="system-state",
        title="Validation Complete",
        status_overrides={"dashboard": "active", "ollama": "active", "gpu": "active", "runner": "active"},
    ),
    OnboardingStep.COMPLETE: SchematicProtocol(
        template="system",
        title="SLATE Ready",
    ),
}


def get_step_schematic(step: OnboardingStep) -> str:
    """Get the schematic SVG for a specific onboarding step."""
    protocol = STEP_SCHEMATICS.get(step)
    if protocol:
        return protocol.generate_svg()
    return SchematicProtocol().generate_svg()


# ── Generative UI Engine ─────────────────────────────────────────────────────

class GenerativeUIEngine:
    """AI-powered generative UI engine for SLATE onboarding."""

    def __init__(self):
        self.workspace = WORKSPACE_ROOT
        self.ollama_url = "http://127.0.0.1:11434"
        self.model = "mistral-nemo"
        self._system_analysis: Optional[SystemAnalysis] = None

    # ── AI Narration ─────────────────────────────────────────────────────

    async def generate_narration(self, step: OnboardingStep, context: Optional[Dict] = None) -> str:
        """Generate AI narration for a step."""
        meta = STEP_METADATA.get(step, {})
        focus = meta.get("ai_focus", "general")

        prompts = {
            "greeting": (
                "You are SLATE AI, a friendly local AI assistant. Generate a warm, "
                "encouraging welcome message (max 40 words) for a developer setting up "
                "their local AI development environment. Mention zero cloud costs and "
                "dual GPU power. Be concise and enthusiastic."
            ),
            "detection": (
                "You are SLATE AI scanning a developer's system. Generate a brief message "
                "(max 30 words) explaining you're detecting installed services like Python, "
                "GPU, Ollama, and Docker. Be technical but friendly."
            ),
            "configuration": (
                "You are SLATE AI configuring core services. Generate a brief message "
                "(max 30 words) about setting up the dashboard, orchestrator, and essential "
                "SLATE infrastructure. Sound knowledgeable and reassuring."
            ),
            "ai_setup": (
                "You are SLATE AI setting up local inference. Generate a brief message "
                "(max 30 words) about configuring Ollama with models like mistral-nemo "
                "for local AI without API costs. Be excited about the capabilities."
            ),
            "integration": (
                "You are SLATE AI connecting services. Generate a brief message "
                "(max 30 words) about linking GitHub, Docker, and other integrations "
                "for full automation. Sound professional and capable."
            ),
            "validation": (
                "You are SLATE AI validating the setup. Generate a brief message "
                "(max 30 words) about running comprehensive checks to ensure everything "
                "works together. Sound thorough and confident."
            ),
            "celebration": (
                "You are SLATE AI celebrating a successful setup. Generate an enthusiastic "
                "message (max 40 words) congratulating the developer. Mention what they "
                "can do next like '@slate /run' or opening the dashboard."
            ),
        }

        prompt = prompts.get(focus, prompts["general"] if "general" in prompts else prompts["greeting"])

        # Add context if provided
        if context:
            prompt += f"\n\nContext: {json.dumps(context)}"

        try:
            response = await self._query_ollama(prompt)
            return response if response else self._get_fallback_narration(step)
        except Exception as e:
            logger.warning(f"Ollama narration failed: {e}")
            return self._get_fallback_narration(step)

    def _get_fallback_narration(self, step: OnboardingStep) -> str:
        """Get fallback narration when AI is unavailable."""
        fallbacks = {
            OnboardingStep.WELCOME: (
                "Welcome to SLATE! I'm your AI guide. Let me set up your local "
                "development environment with zero cloud costs."
            ),
            OnboardingStep.SYSTEM_SCAN: (
                "Now scanning your system to detect installed services. "
                "This helps me understand what's already available."
            ),
            OnboardingStep.CORE_SERVICES: (
                "Configuring SLATE's core infrastructure. This includes the "
                "dashboard, orchestrator, and essential services."
            ),
            OnboardingStep.AI_BACKENDS: (
                "Setting up your local AI inference with Ollama. This powers "
                "all AI features without any API costs."
            ),
            OnboardingStep.INTEGRATIONS: (
                "Connecting external services like GitHub and Docker. These "
                "enable full CI/CD automation."
            ),
            OnboardingStep.VALIDATION: (
                "Running comprehensive validation to ensure everything works "
                "together seamlessly."
            ),
            OnboardingStep.COMPLETE: (
                "Congratulations! Your SLATE system is fully operational. "
                "Try '@slate /run' in VS Code to get started!"
            ),
        }
        return fallbacks.get(step, f"Processing {step.value}...")

    # ── Step Generation ──────────────────────────────────────────────────

    async def generate_step_content(self, step: OnboardingStep, include_schematic: bool = True) -> GeneratedContent:
        """Generate dynamic content for a step.

        Args:
            step: The onboarding step to generate content for
            include_schematic: Whether to include schematic SVG (default True)

        Returns:
            GeneratedContent with narration, description, recommendations, and schematic
        """
        meta = STEP_METADATA.get(step, {})

        # Generate narration
        narration = await self.generate_narration(step)

        # Generate step description
        description = await self._generate_description(step)

        # Generate recommendations based on system state
        recommendations = await self._generate_recommendations(step)

        # Generate animation hints
        animations = self._get_animation_hints(step)

        # Generate schematic for step (Spec 012)
        schematic_svg = ""
        if include_schematic:
            schematic_svg = get_step_schematic(step)

        return GeneratedContent(
            narration=narration,
            step_description=description,
            recommendations=recommendations,
            animation_hints=animations,
            schematic_svg=schematic_svg,
        )

    async def _generate_description(self, step: OnboardingStep) -> str:
        """Generate a dynamic step description."""
        meta = STEP_METADATA.get(step, {})
        base = meta.get("description", "")

        # Add context based on system state
        if self._system_analysis:
            if step == OnboardingStep.AI_BACKENDS:
                models = len(self._system_analysis.ollama_models)
                if models > 0:
                    base += f" ({models} models detected)"
            elif step == OnboardingStep.SYSTEM_SCAN:
                gpus = self._system_analysis.gpu_count
                if gpus > 0:
                    base += f" ({gpus} GPU{'s' if gpus > 1 else ''} detected)"

        return base

    async def _generate_recommendations(self, step: OnboardingStep) -> List[str]:
        """Generate personalized recommendations for a step."""
        recs = []

        if not self._system_analysis:
            await self.analyze_system()

        analysis = self._system_analysis

        if step == OnboardingStep.AI_BACKENDS:
            if not analysis.ollama_available:
                recs.append("Install Ollama from https://ollama.ai for local AI")
            if "mistral-nemo" not in analysis.ollama_models:
                recs.append("Run 'ollama pull mistral-nemo' for best results")

        elif step == OnboardingStep.INTEGRATIONS:
            if not analysis.github_authenticated:
                recs.append("Run 'gh auth login' to enable GitHub integration")
            if not analysis.docker_available:
                recs.append("Install Docker Desktop for container support")

        elif step == OnboardingStep.COMPLETE:
            recs.append("Try '@slate /run' in VS Code chat")
            recs.append("Open the dashboard at http://127.0.0.1:8080")
            if analysis.gpu_count >= 2:
                recs.append("Your dual GPU setup enables parallel AI workloads")

        return recs

    def _get_animation_hints(self, step: OnboardingStep) -> List[str]:
        """Get animation hints for UI rendering."""
        hints = {
            OnboardingStep.WELCOME: ["pulse-logo", "fade-in-title", "slide-up-cta"],
            OnboardingStep.SYSTEM_SCAN: ["scan-wave", "detect-pulse", "check-appear"],
            OnboardingStep.CORE_SERVICES: ["config-spin", "service-stack", "connect-lines"],
            OnboardingStep.AI_BACKENDS: ["brain-pulse", "model-load", "inference-flow"],
            OnboardingStep.INTEGRATIONS: ["link-connect", "sync-arrows", "api-pulse"],
            OnboardingStep.VALIDATION: ["check-cascade", "green-wave", "success-burst"],
            OnboardingStep.COMPLETE: ["celebration-burst", "confetti", "glow-pulse"],
        }
        return hints.get(step, [])

    # ── System Analysis ──────────────────────────────────────────────────

    async def analyze_system(self) -> SystemAnalysis:
        """Analyze the current system for onboarding."""
        import subprocess

        analysis = SystemAnalysis()

        # Check Python
        try:
            result = subprocess.run(
                ["python", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                analysis.python_version = result.stdout.strip()
        except Exception:
            pass

        # Check GPU
        try:
            result = subprocess.run(
                ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")
                analysis.gpu_count = len(lines)
                for line in lines:
                    parts = line.split(",")
                    if len(parts) >= 1:
                        analysis.gpu_models.append(parts[0].strip())
                    if len(parts) >= 2:
                        mem = parts[1].strip().replace("MiB", "").strip()
                        try:
                            analysis.total_vram_gb += float(mem) / 1024
                        except ValueError:
                            pass
        except Exception:
            pass

        # Check Ollama
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self.ollama_url}/api/tags", timeout=5)
                if resp.status_code == 200:
                    analysis.ollama_available = True
                    data = resp.json()
                    analysis.ollama_models = [m["name"] for m in data.get("models", [])]
        except Exception:
            pass

        # Check Docker
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            analysis.docker_available = result.returncode == 0
        except Exception:
            pass

        # Check GitHub auth
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            analysis.github_authenticated = result.returncode == 0
        except Exception:
            pass

        # Check venv
        venv_path = self.workspace / ".venv"
        analysis.venv_exists = venv_path.exists()

        # Check SLATE installed
        slate_path = self.workspace / "slate"
        analysis.slate_installed = slate_path.exists()

        # Generate recommendations
        if not analysis.ollama_available:
            analysis.recommendations.append("Install Ollama for local AI inference")
        if analysis.gpu_count == 0:
            analysis.recommendations.append("GPU not detected - some features may be slower")
        if not analysis.docker_available:
            analysis.recommendations.append("Install Docker for container support")
        if not analysis.github_authenticated:
            analysis.recommendations.append("Run 'gh auth login' for GitHub integration")

        self._system_analysis = analysis
        return analysis

    # ── Ollama Integration ───────────────────────────────────────────────

    async def _query_ollama(self, prompt: str) -> str:
        """Query Ollama for AI-generated content."""
        try:
            import httpx
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 100},
                    },
                    timeout=30,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    return data.get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama query failed: {e}")
        return ""

    # ── Status ───────────────────────────────────────────────────────────

    def get_status(self) -> Dict[str, Any]:
        """Get generative UI engine status."""
        return {
            "engine": "GenerativeUIEngine",
            "version": "2.0.0",  # Updated for schematic protocol support
            "ollama_url": self.ollama_url,
            "model": self.model,
            "design_tokens": DESIGN_TOKENS,
            "steps": [s.value for s in OnboardingStep],
            "system_analyzed": self._system_analysis is not None,
            "schematic_sdk_available": SCHEMATIC_SDK_AVAILABLE,
            "schematic_templates": list(TEMPLATES.keys()) if SCHEMATIC_SDK_AVAILABLE else [],
            "step_schematics": list(STEP_SCHEMATICS.keys()) if SCHEMATIC_SDK_AVAILABLE else [],
        }


# ── Singleton ────────────────────────────────────────────────────────────────

_engine_instance: Optional[GenerativeUIEngine] = None


def get_engine() -> GenerativeUIEngine:
    """Get the singleton GenerativeUIEngine instance."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = GenerativeUIEngine()
    return _engine_instance


def reset_engine() -> None:
    """Reset the engine instance."""
    global _engine_instance
    _engine_instance = None


# ── CLI ──────────────────────────────────────────────────────────────────────

async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="SLATE Generative UI Engine")
    parser.add_argument("--status", action="store_true", help="Show engine status")
    parser.add_argument("--analyze-system", action="store_true", help="Analyze system")
    parser.add_argument("--narrate", metavar="STEP", help="Generate narration for step")
    parser.add_argument("--generate-step", metavar="STEP", help="Generate full step content")
    parser.add_argument("--tokens", action="store_true", help="Show design tokens")
    parser.add_argument("--schematic", metavar="TEMPLATE", help="Generate schematic (system, inference, cicd, or step name)")
    parser.add_argument("--output", metavar="FILE", help="Output file for schematic SVG")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    engine = get_engine()

    if args.analyze_system:
        analysis = await engine.analyze_system()
        if args.json:
            print(json.dumps(analysis.to_dict(), indent=2))
        else:
            print("System Analysis")
            print("-" * 40)
            print(f"Python: {analysis.python_version or 'Not found'}")
            print(f"GPUs: {analysis.gpu_count} ({', '.join(analysis.gpu_models) or 'None'})")
            print(f"VRAM: {analysis.total_vram_gb:.1f} GB")
            print(f"Ollama: {'Available' if analysis.ollama_available else 'Not found'}")
            if analysis.ollama_models:
                print(f"Models: {', '.join(analysis.ollama_models[:5])}")
            print(f"Docker: {'Available' if analysis.docker_available else 'Not found'}")
            print(f"GitHub: {'Authenticated' if analysis.github_authenticated else 'Not authenticated'}")
            if analysis.recommendations:
                print("\nRecommendations:")
                for rec in analysis.recommendations:
                    print(f"  - {rec}")

    elif args.narrate:
        try:
            step = OnboardingStep(args.narrate)
        except ValueError:
            print(f"Invalid step: {args.narrate}")
            print(f"Valid steps: {[s.value for s in OnboardingStep]}")
            return
        narration = await engine.generate_narration(step)
        if args.json:
            print(json.dumps({"step": step.value, "narration": narration}))
        else:
            print(f"[{step.value}] {narration}")

    elif args.generate_step:
        try:
            step = OnboardingStep(args.generate_step)
        except ValueError:
            print(f"Invalid step: {args.generate_step}")
            print(f"Valid steps: {[s.value for s in OnboardingStep]}")
            return
        content = await engine.generate_step_content(step)
        if args.json:
            print(json.dumps(content.to_dict(), indent=2))
        else:
            print(f"Step: {step.value}")
            print("-" * 40)
            print(f"Narration: {content.narration}")
            print(f"Description: {content.step_description}")
            if content.recommendations:
                print("Recommendations:")
                for rec in content.recommendations:
                    print(f"  - {rec}")
            if content.animation_hints:
                print(f"Animations: {', '.join(content.animation_hints)}")

    elif args.schematic:
        template = args.schematic.lower()

        # Check if it's a step name
        try:
            step = OnboardingStep(template)
            svg = get_step_schematic(step)
            title = f"Schematic for {step.value}"
        except ValueError:
            # It's a template name
            protocol = SchematicProtocol(template=template, title=f"SLATE {template.title()}")
            svg = protocol.generate_svg()
            title = protocol.title

        if args.output:
            output_path = Path(args.output)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            output_path.write_text(svg, encoding="utf-8")
            print(f"[+] Schematic saved to {output_path}")
        elif args.json:
            print(json.dumps({"template": template, "title": title, "svg": svg}))
        else:
            print(f"Generated: {title}")
            print(f"SVG length: {len(svg)} bytes")
            if not args.output:
                print("\nTip: Use --output FILE to save the SVG")

    elif args.tokens:
        if args.json:
            print(json.dumps(DESIGN_TOKENS, indent=2))
        else:
            print("Design Tokens")
            print("-" * 40)
            for category, values in DESIGN_TOKENS.items():
                print(f"\n{category}:")
                for key, val in values.items():
                    print(f"  {key}: {val}")

    elif args.json:
        print(json.dumps(engine.get_status(), indent=2))

    else:
        status = engine.get_status()
        print("=" * 50)
        print("  SLATE Generative UI Engine")
        print("=" * 50)
        print(f"\n  Version: {status['version']}")
        print(f"  Ollama: {status['ollama_url']}")
        print(f"  Model: {status['model']}")
        print(f"\n  Steps: {len(status['steps'])}")
        for step in status["steps"]:
            print(f"    - {step}")
        print("\n" + "=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
