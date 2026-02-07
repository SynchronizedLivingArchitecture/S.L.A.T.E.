#!/usr/bin/env python3
"""
SLATE Interactive Experience Engine
====================================

A choose-your-own-adventure style interface for software development.
Based on human psychology and AI inference to create an engaging,
game-like experience for controlling the development lifecycle.

Design Principles:
1. Exploration before commitment - users can learn without acting
2. Branching dialogue trees - multiple paths, not linear steps
3. AI companion guidance - contextual recommendations and explanations
4. Consequence previews - see what happens before you choose
5. Progress visualization - visual maps of development state
6. Psychological engagement - reward loops, discovery, agency

Inspired by:
- RPG dialogue systems (Mass Effect, Baldur's Gate)
- Skill trees (Path of Exile, Civilization tech trees)
- Interactive fiction (Twine, Choice of Games)
- Roguelike progression (Hades, Slay the Spire)
"""

import asyncio
import json
import random
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Set
import logging

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger(__name__)


class NodeType(Enum):
    """Types of nodes in the interaction tree."""
    HUB = "hub"                    # Central navigation point
    DIALOGUE = "dialogue"          # AI presents info, user responds
    CHOICE = "choice"              # Multiple options branch
    ACTION = "action"              # Executable action
    EXPLORATION = "exploration"    # Browse/learn mode
    REVEAL = "reveal"              # Unlock new information
    CHECKPOINT = "checkpoint"      # Save progress point
    CONSEQUENCE = "consequence"    # Show outcome of action


class EmotionalTone(Enum):
    """Emotional context for AI responses (psychological engagement)."""
    WELCOMING = "welcoming"        # Warm, inviting
    CURIOUS = "curious"            # Encouraging exploration
    SUPPORTIVE = "supportive"      # Reassuring during uncertainty
    EXCITED = "excited"            # Building momentum
    THOUGHTFUL = "thoughtful"      # Considering options
    CELEBRATORY = "celebratory"    # Acknowledging success
    CAUTIONARY = "cautionary"      # Gentle warnings
    MYSTERIOUS = "mysterious"      # Intrigue about what's ahead


@dataclass
class InteractionOption:
    """A single option the user can choose."""
    id: str
    label: str                     # Short display text
    description: str               # Longer explanation
    icon: str                      # Visual identifier
    tone: EmotionalTone = EmotionalTone.CURIOUS
    leads_to: Optional[str] = None  # Next node ID
    action: Optional[str] = None    # Action to execute
    requires: List[str] = field(default_factory=list)  # Prerequisites
    reveals: List[str] = field(default_factory=list)   # Information unlocked
    preview: Optional[str] = None   # What happens if chosen
    learn_more: Optional[str] = None  # Expandable detail
    ai_hint: Optional[str] = None   # AI recommendation context
    risk_level: int = 0             # 0=safe, 1=low, 2=medium, 3=high
    reversible: bool = True         # Can this be undone?
    estimated_time: Optional[str] = None


@dataclass
class InteractionNode:
    """A node in the interaction tree."""
    id: str
    node_type: NodeType
    title: str
    narrative: str                  # The story/context text
    tone: EmotionalTone = EmotionalTone.WELCOMING
    options: List[InteractionOption] = field(default_factory=list)
    context_data: Dict[str, Any] = field(default_factory=dict)
    visited: bool = False
    unlocked: bool = True
    parent_id: Optional[str] = None
    ai_prompt: Optional[str] = None  # Prompt for AI to generate dynamic content


class DevelopmentMap:
    """Visual representation of the development landscape."""

    # Development zones - areas of the "map" the user can explore
    ZONES = {
        "control_center": {
            "name": "Control Center",
            "description": "System operations, health checks, and diagnostics",
            "icon": "command",
            "color": "#B87333",  # Copper
            "unlocked": True
        },
        "code_forge": {
            "name": "Code Forge",
            "description": "Where code is crafted, tested, and refined",
            "icon": "anvil",
            "color": "#4A7C59",  # Sage green
            "unlocked": True
        },
        "ai_nexus": {
            "name": "AI Nexus",
            "description": "Local AI analysis, code review, and generation",
            "icon": "brain",
            "color": "#7C3AED",  # Purple
            "unlocked": True
        },
        "deployment_dock": {
            "name": "Deployment Dock",
            "description": "Build, containerize, and ship your project",
            "icon": "rocket",
            "color": "#DC2626",  # Red
            "unlocked": True
        },
        "knowledge_archive": {
            "name": "Knowledge Archive",
            "description": "Documentation, specs, and project memory",
            "icon": "book",
            "color": "#0891B2",  # Cyan
            "unlocked": True
        },
        "collaboration_hub": {
            "name": "Collaboration Hub",
            "description": "GitHub integration, PRs, issues, and discussions",
            "icon": "people",
            "color": "#F59E0B",  # Amber
            "unlocked": True
        }
    }

    @classmethod
    def get_zone_status(cls, zone_id: str) -> Dict[str, Any]:
        """Get current status of a development zone."""
        zone = cls.ZONES.get(zone_id, {})
        # This would be enhanced with real status checks
        return {
            **zone,
            "id": zone_id,
            "active_tasks": 0,
            "health": "good",
            "last_activity": None
        }


class AICompanion:
    """
    The AI companion that guides the user through the experience.

    Provides contextual dialogue, recommendations, and explanations
    based on the current state and user history.
    """

    PERSONALITY_TRAITS = {
        "helpful": 0.9,
        "curious": 0.8,
        "encouraging": 0.85,
        "technical": 0.7,
        "playful": 0.4
    }

    # Dialogue templates by emotional tone
    DIALOGUE_TEMPLATES = {
        EmotionalTone.WELCOMING: [
            "Welcome back to SLATE. What would you like to explore today?",
            "Good to see you. The system is ready for your direction.",
            "Your development environment awaits. Where shall we begin?"
        ],
        EmotionalTone.CURIOUS: [
            "Interesting choice. Would you like to know more about {topic}?",
            "There's quite a bit we could explore here. What catches your attention?",
            "I notice you're drawn to {topic}. Shall I explain what's possible?"
        ],
        EmotionalTone.SUPPORTIVE: [
            "This is a solid approach. Here's what will happen...",
            "Don't worry, this is reversible if you change your mind.",
            "I'm here to help. Take your time exploring the options."
        ],
        EmotionalTone.EXCITED: [
            "Excellent! This will be interesting to see unfold.",
            "Now we're getting somewhere! Ready to proceed?",
            "This is going to make a real difference. Let's do it."
        ],
        EmotionalTone.THOUGHTFUL: [
            "Let me consider the implications...",
            "There are a few paths we could take here. Each has trade-offs.",
            "Based on the current state, I'd suggest considering..."
        ],
        EmotionalTone.CAUTIONARY: [
            "Before we proceed, you should know...",
            "This action has some implications worth considering.",
            "Just a heads up - this will affect {affected_areas}."
        ],
        EmotionalTone.CELEBRATORY: [
            "Well done! That completed successfully.",
            "Excellent work. The system is in better shape now.",
            "Achievement unlocked: {achievement}. Nice job!"
        ],
        EmotionalTone.MYSTERIOUS: [
            "There's something interesting over here...",
            "I've discovered something you might want to see.",
            "The data suggests an opportunity we haven't explored yet."
        ]
    }

    def __init__(self):
        self.ollama_available = False
        self.conversation_history: List[Dict[str, str]] = []
        self.user_preferences: Dict[str, Any] = {}
        self._check_ollama()

    def _check_ollama(self) -> None:
        """Check if Ollama is available for dynamic responses."""
        try:
            import httpx
            response = httpx.get("http://localhost:11434/api/tags", timeout=2)
            self.ollama_available = response.status_code == 200
        except Exception:
            self.ollama_available = False

    def get_dialogue(self, tone: EmotionalTone, context: Dict[str, Any] = None) -> str:
        """Get appropriate dialogue based on tone and context."""
        templates = self.DIALOGUE_TEMPLATES.get(tone, self.DIALOGUE_TEMPLATES[EmotionalTone.WELCOMING])
        template = random.choice(templates)

        if context:
            try:
                return template.format(**context)
            except KeyError:
                pass
        return template

    async def generate_contextual_response(
        self,
        situation: str,
        user_query: Optional[str] = None,
        tone: EmotionalTone = EmotionalTone.SUPPORTIVE
    ) -> str:
        """Generate a contextual AI response using Ollama if available."""
        if not self.ollama_available:
            return self.get_dialogue(tone)

        try:
            import httpx

            personality = ", ".join([f"{k} ({int(v*100)}%)" for k, v in self.PERSONALITY_TRAITS.items()])

            prompt = f"""You are SLATE's AI companion, guiding a developer through their project.
Your personality: {personality}
Current emotional tone: {tone.value}
Situation: {situation}
{f'User asked: {user_query}' if user_query else ''}

Provide a brief, engaging response (2-3 sentences max) that:
1. Acknowledges the current situation
2. Offers helpful guidance or information
3. Maintains the emotional tone
4. Feels like a video game companion, not a chatbot

Response:"""

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 150}
                    },
                    timeout=10
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("response", "").strip()
        except Exception as e:
            logger.warning(f"AI response generation failed: {e}")

        return self.get_dialogue(tone)

    async def recommend_action(self, available_options: List[InteractionOption], context: Dict[str, Any]) -> Optional[str]:
        """AI recommends which option the user should consider."""
        if not available_options:
            return None

        # Simple heuristics for now, could be enhanced with ML
        # Prioritize: low risk, reversible, good for current state
        scored = []
        for opt in available_options:
            score = 10
            score -= opt.risk_level * 2  # Lower risk = higher score
            if opt.reversible:
                score += 2
            if opt.preview:
                score += 1  # Options with previews are more transparent
            scored.append((score, opt))

        scored.sort(reverse=True, key=lambda x: x[0])
        recommended = scored[0][1] if scored else None

        if recommended:
            return f"I'd suggest exploring **{recommended.label}**. {recommended.description}"
        return None


class InteractiveExperience:
    """
    Main engine for the choose-your-own-adventure experience.

    Manages the interaction tree, state, and user journey through
    the development landscape.
    """

    def __init__(self):
        self.companion = AICompanion()
        self.current_node_id: str = "main_hub"
        self.visited_nodes: Set[str] = set()
        self.unlocked_info: Set[str] = set()
        self.action_history: List[Dict[str, Any]] = []
        self.session_start = datetime.now()
        self.nodes: Dict[str, InteractionNode] = {}
        self._build_interaction_tree()

    def _build_interaction_tree(self):
        """Build the complete interaction tree."""

        # ═══════════════════════════════════════════════════════════════
        # MAIN HUB - The central starting point
        # ═══════════════════════════════════════════════════════════════
        self.nodes["main_hub"] = InteractionNode(
            id="main_hub",
            node_type=NodeType.HUB,
            title="SLATE Command Center",
            narrative="You stand at the heart of your development environment. The system hums with potential, awaiting your direction. Multiple paths branch out before you, each leading to different aspects of your project.",
            tone=EmotionalTone.WELCOMING,
            options=[
                InteractionOption(
                    id="explore_status",
                    label="Survey the System",
                    description="Get a comprehensive view of your project's current state",
                    icon="radar",
                    tone=EmotionalTone.CURIOUS,
                    leads_to="system_overview",
                    preview="You'll see: service health, GPU status, task queue, recent activity",
                    learn_more="The system overview shows everything at a glance - like a captain's bridge display. No actions are taken, just observation.",
                    risk_level=0,
                    estimated_time="instant"
                ),
                InteractionOption(
                    id="enter_code_forge",
                    label="Enter the Code Forge",
                    description="Where code is tested, analyzed, and refined",
                    icon="anvil",
                    tone=EmotionalTone.EXCITED,
                    leads_to="code_forge_hub",
                    preview="Access: tests, linting, security audits, code quality tools",
                    learn_more="The Code Forge contains all your quality assurance tools. Run tests, check code style, and ensure your code meets standards.",
                    risk_level=0,
                    estimated_time=None
                ),
                InteractionOption(
                    id="consult_ai",
                    label="Consult the AI Nexus",
                    description="Engage local AI for analysis and guidance",
                    icon="brain",
                    tone=EmotionalTone.MYSTERIOUS,
                    leads_to="ai_nexus_hub",
                    preview="Access: AI code review, documentation generation, codebase analysis",
                    learn_more="The AI Nexus uses your local Ollama models to analyze code, generate documentation, and provide intelligent recommendations. All processing happens locally.",
                    risk_level=0,
                    estimated_time=None
                ),
                InteractionOption(
                    id="visit_deployment",
                    label="Visit Deployment Dock",
                    description="Prepare your project for the world",
                    icon="rocket",
                    tone=EmotionalTone.THOUGHTFUL,
                    leads_to="deployment_hub",
                    preview="Access: Docker builds, CI/CD pipelines, release management",
                    learn_more="The Deployment Dock handles containerization, builds, and shipping your code. Actions here can trigger real deployments.",
                    risk_level=1,
                    estimated_time=None
                ),
                InteractionOption(
                    id="browse_archive",
                    label="Browse Knowledge Archive",
                    description="Explore documentation, specs, and project memory",
                    icon="book",
                    tone=EmotionalTone.CURIOUS,
                    leads_to="archive_hub",
                    preview="Access: specs, wiki, tech tree, project history",
                    learn_more="The Archive contains all project knowledge - specifications, documentation, and the tech tree that guides development priorities.",
                    risk_level=0,
                    estimated_time=None
                ),
                InteractionOption(
                    id="open_collaboration",
                    label="Open Collaboration Hub",
                    description="Connect with GitHub - PRs, issues, discussions",
                    icon="people",
                    tone=EmotionalTone.SUPPORTIVE,
                    leads_to="collaboration_hub",
                    preview="Access: pull requests, issues, commits, GitHub integration",
                    learn_more="The Collaboration Hub connects to your GitHub repository. View PRs, manage issues, and coordinate with your team.",
                    risk_level=0,
                    estimated_time=None
                ),
                InteractionOption(
                    id="quick_action",
                    label="Execute Quick Action",
                    description="Jump straight to a common operation",
                    icon="lightning",
                    tone=EmotionalTone.EXCITED,
                    leads_to="quick_actions",
                    preview="Fast access to: health check, run tests, AI review, deploy",
                    learn_more="Quick Actions let you bypass exploration and execute common tasks immediately. Best for when you know exactly what you want.",
                    risk_level=1,
                    estimated_time="varies"
                )
            ]
        )

        # ═══════════════════════════════════════════════════════════════
        # SYSTEM OVERVIEW - Survey the current state
        # ═══════════════════════════════════════════════════════════════
        self.nodes["system_overview"] = InteractionNode(
            id="system_overview",
            node_type=NodeType.EXPLORATION,
            title="System Overview",
            narrative="The holographic display springs to life, showing the vital signs of your development environment. Data streams flow across the visualization.",
            tone=EmotionalTone.CURIOUS,
            parent_id="main_hub",
            ai_prompt="Describe the current system state as if narrating a sci-fi game",
            options=[
                InteractionOption(
                    id="view_services",
                    label="Inspect Services",
                    description="Check the status of all running services",
                    icon="server",
                    leads_to="services_detail",
                    learn_more="Services include: Dashboard (8080), Ollama (11434), Docker, GitHub Runner. Each can be individually managed.",
                    risk_level=0
                ),
                InteractionOption(
                    id="view_resources",
                    label="Examine Resources",
                    description="CPU, memory, GPU utilization",
                    icon="gauge",
                    leads_to="resources_detail",
                    learn_more="See real-time utilization of your dual RTX 5070 Ti GPUs, system memory, and CPU. SLATE automatically balances AI workloads.",
                    risk_level=0
                ),
                InteractionOption(
                    id="view_tasks",
                    label="Review Task Queue",
                    description="See pending, active, and completed tasks",
                    icon="list",
                    leads_to="task_queue_detail",
                    learn_more="The task queue shows all work items. Tasks flow through: pending → in_progress → completed. You can prioritize or cancel from here.",
                    risk_level=0
                ),
                InteractionOption(
                    id="run_diagnostics",
                    label="Run Full Diagnostics",
                    description="Comprehensive health check of all systems",
                    icon="scan",
                    action="run_diagnostics",
                    preview="Executes: status check, runtime validation, workflow health, security scan. Takes ~30 seconds.",
                    learn_more="Diagnostics verify every component is working correctly. Any issues found will be reported with suggested fixes.",
                    risk_level=0,
                    estimated_time="~30 sec"
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

        # ═══════════════════════════════════════════════════════════════
        # CODE FORGE - Testing and Quality
        # ═══════════════════════════════════════════════════════════════
        self.nodes["code_forge_hub"] = InteractionNode(
            id="code_forge_hub",
            node_type=NodeType.HUB,
            title="The Code Forge",
            narrative="Heat shimmers from the forges where code is tempered and tested. Quality is not negotiable here - only refined code passes through.",
            tone=EmotionalTone.THOUGHTFUL,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="run_tests",
                    label="Ignite Test Suite",
                    description="Execute the full pytest test suite",
                    icon="flame",
                    action="run_tests",
                    preview="Runs all tests in tests/ directory with coverage reporting. Results show pass/fail counts.",
                    learn_more="Tests verify your code works as expected. Coverage shows how much of your code is tested. Higher is better.",
                    risk_level=0,
                    reversible=True,
                    estimated_time="~3 min"
                ),
                InteractionOption(
                    id="run_lint",
                    label="Polish with Linter",
                    description="Check code style and quality with ruff",
                    icon="sparkle",
                    action="run_lint",
                    preview="Analyzes all Python files for style issues, unused imports, and potential bugs.",
                    learn_more="Linting catches common mistakes and enforces consistent style. Issues found can often be auto-fixed.",
                    risk_level=0,
                    reversible=True,
                    estimated_time="~1 min"
                ),
                InteractionOption(
                    id="security_scan",
                    label="Security Audit",
                    description="Scan for vulnerabilities and secrets",
                    icon="shield",
                    action="security_audit",
                    preview="Checks: SDK source guard, PII scanner, ActionGuard rules, credential detection.",
                    learn_more="Security audits look for leaked secrets, vulnerable dependencies, and dangerous code patterns. Critical for safe development.",
                    risk_level=0,
                    reversible=True,
                    estimated_time="~2 min"
                ),
                InteractionOption(
                    id="explore_tests",
                    label="Explore Test Results",
                    description="Review previous test runs and coverage",
                    icon="magnify",
                    leads_to="test_history",
                    learn_more="See trends in test results over time, identify flaky tests, and find areas needing more coverage.",
                    risk_level=0
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

        # ═══════════════════════════════════════════════════════════════
        # AI NEXUS - Local AI Integration
        # ═══════════════════════════════════════════════════════════════
        self.nodes["ai_nexus_hub"] = InteractionNode(
            id="ai_nexus_hub",
            node_type=NodeType.HUB,
            title="The AI Nexus",
            narrative="Neural pathways illuminate as you enter the AI Nexus. Your local models stand ready - mistral-nemo hums with potential, waiting to analyze and assist.",
            tone=EmotionalTone.MYSTERIOUS,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="ai_code_review",
                    label="Request Code Review",
                    description="AI analyzes recent code changes",
                    icon="eye",
                    action="ai_code_review",
                    preview="AI examines your recent commits, identifies issues, suggests improvements. Results in ~5 minutes.",
                    learn_more="The AI reviewer looks at code structure, potential bugs, performance issues, and style. It's like having a senior developer review your code.",
                    ai_hint="Good for: after making changes, before creating a PR",
                    risk_level=0,
                    reversible=True,
                    estimated_time="~5 min"
                ),
                InteractionOption(
                    id="ai_documentation",
                    label="Generate Documentation",
                    description="AI creates docs for changed files",
                    icon="document",
                    action="ai_documentation",
                    preview="AI generates docstrings, README updates, and API documentation for recent changes.",
                    learn_more="Documentation is automatically generated based on your code. It understands function signatures, class structures, and module purposes.",
                    ai_hint="Good for: maintaining docs, onboarding, API references",
                    risk_level=1,
                    reversible=True,
                    estimated_time="~10 min"
                ),
                InteractionOption(
                    id="ai_full_analysis",
                    label="Deep Codebase Analysis",
                    description="Comprehensive AI analysis of entire project",
                    icon="brain",
                    action="ai_full_analysis",
                    preview="AI analyzes the complete codebase: architecture, patterns, tech debt, opportunities.",
                    learn_more="A thorough analysis that maps your codebase structure, identifies patterns, and suggests architectural improvements. Takes longer but provides deep insights.",
                    ai_hint="Good for: periodic reviews, planning refactors, understanding legacy code",
                    risk_level=0,
                    reversible=True,
                    estimated_time="~30 min"
                ),
                InteractionOption(
                    id="talk_to_ai",
                    label="Converse with AI",
                    description="Ask questions about your codebase",
                    icon="chat",
                    leads_to="ai_conversation",
                    learn_more="Have a dialogue with the AI about your code. Ask questions, get explanations, explore possibilities.",
                    ai_hint="Good for: understanding code, exploring options, getting recommendations",
                    risk_level=0
                ),
                InteractionOption(
                    id="ai_model_status",
                    label="Check AI Model Status",
                    description="View available models and their status",
                    icon="cpu",
                    leads_to="ai_models_detail",
                    learn_more="See which AI models are loaded, their memory usage, and capabilities. Manage model loading.",
                    risk_level=0
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

        # ═══════════════════════════════════════════════════════════════
        # QUICK ACTIONS - Fast execution paths
        # ═══════════════════════════════════════════════════════════════
        self.nodes["quick_actions"] = InteractionNode(
            id="quick_actions",
            node_type=NodeType.CHOICE,
            title="Quick Actions",
            narrative="The express lanes of development. Choose your action and it executes immediately. For when you know exactly what you want.",
            tone=EmotionalTone.EXCITED,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="quick_health",
                    label="Health Check",
                    description="Fast system status verification",
                    icon="heart",
                    action="quick_health_check",
                    preview="Verifies: services running, GPU available, tasks healthy",
                    risk_level=0,
                    estimated_time="~5 sec"
                ),
                InteractionOption(
                    id="quick_tests",
                    label="Run Tests",
                    description="Execute test suite immediately",
                    icon="play",
                    action="run_tests",
                    preview="Starts pytest with coverage, shows results when complete",
                    risk_level=0,
                    estimated_time="~3 min"
                ),
                InteractionOption(
                    id="quick_ai_review",
                    label="AI Review",
                    description="Quick AI analysis of recent changes",
                    icon="brain",
                    action="ai_code_review",
                    preview="AI reviews recent commits, returns findings",
                    risk_level=0,
                    estimated_time="~5 min"
                ),
                InteractionOption(
                    id="quick_lint",
                    label="Lint Check",
                    description="Run code quality checks",
                    icon="check",
                    action="run_lint",
                    preview="Runs ruff linter, reports issues",
                    risk_level=0,
                    estimated_time="~1 min"
                ),
                InteractionOption(
                    id="quick_security",
                    label="Security Scan",
                    description="Quick security audit",
                    icon="shield",
                    action="security_audit",
                    preview="Runs security checks, reports vulnerabilities",
                    risk_level=0,
                    estimated_time="~2 min"
                ),
                InteractionOption(
                    id="return_hub",
                    label="Back to Exploration",
                    description="Return to detailed navigation",
                    icon="map",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

        # Additional hubs can be added similarly...
        self._add_deployment_hub()
        self._add_archive_hub()
        self._add_collaboration_hub()

    def _add_deployment_hub(self):
        """Add deployment-related nodes."""
        self.nodes["deployment_hub"] = InteractionNode(
            id="deployment_hub",
            node_type=NodeType.HUB,
            title="Deployment Dock",
            narrative="The launch bays stretch before you, ready to send your code into the world. Container orchestration systems await your command.",
            tone=EmotionalTone.CAUTIONARY,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="build_docker",
                    label="Build Containers",
                    description="Build Docker images for the project",
                    icon="container",
                    action="docker_build",
                    preview="Builds: Dockerfile, Dockerfile.cpu, Dockerfile.dev. Does not push to registry.",
                    learn_more="Docker images package your application with all dependencies. Building locally lets you test before pushing.",
                    risk_level=1,
                    reversible=True,
                    estimated_time="~10 min"
                ),
                InteractionOption(
                    id="view_containers",
                    label="View Running Containers",
                    description="See active Docker containers",
                    icon="eye",
                    leads_to="containers_detail",
                    learn_more="Monitor containers running on your system, their resource usage, and logs.",
                    risk_level=0
                ),
                InteractionOption(
                    id="trigger_ci",
                    label="Trigger CI Pipeline",
                    description="Manually dispatch CI workflow",
                    icon="gear",
                    action="trigger_ci",
                    preview="Dispatches ci.yml workflow on GitHub Actions",
                    learn_more="CI runs tests, linting, and security checks in a clean environment. Results visible on GitHub.",
                    risk_level=1,
                    reversible=False,
                    estimated_time="~5 min"
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

    def _add_archive_hub(self):
        """Add knowledge archive nodes."""
        self.nodes["archive_hub"] = InteractionNode(
            id="archive_hub",
            node_type=NodeType.HUB,
            title="Knowledge Archive",
            narrative="Ancient scrolls (markdown files) and glowing crystals (JSON specs) line the shelves. The project's memory lives here.",
            tone=EmotionalTone.CURIOUS,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="view_tech_tree",
                    label="Examine Tech Tree",
                    description="View the development roadmap",
                    icon="tree",
                    leads_to="tech_tree_view",
                    learn_more="The tech tree shows what features are available, in development, and planned. It guides prioritization.",
                    risk_level=0
                ),
                InteractionOption(
                    id="browse_specs",
                    label="Browse Specifications",
                    description="View project specifications",
                    icon="document",
                    leads_to="specs_browser",
                    learn_more="Specifications define features before implementation. They go through: draft → specified → planned → implementing → complete.",
                    risk_level=0
                ),
                InteractionOption(
                    id="search_docs",
                    label="Search Documentation",
                    description="Find information in project docs",
                    icon="search",
                    leads_to="doc_search",
                    learn_more="Full-text search across all project documentation, README files, and comments.",
                    risk_level=0
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

    def _add_collaboration_hub(self):
        """Add GitHub collaboration nodes."""
        self.nodes["collaboration_hub"] = InteractionNode(
            id="collaboration_hub",
            node_type=NodeType.HUB,
            title="Collaboration Hub",
            narrative="Signals from the wider development community flow through here. GitHub's pulse is visible in real-time.",
            tone=EmotionalTone.SUPPORTIVE,
            parent_id="main_hub",
            options=[
                InteractionOption(
                    id="view_prs",
                    label="Review Pull Requests",
                    description="See open PRs and their status",
                    icon="merge",
                    leads_to="pr_browser",
                    learn_more="Pull requests are how code changes get reviewed and merged. See status, reviews, and CI results.",
                    risk_level=0
                ),
                InteractionOption(
                    id="view_issues",
                    label="Browse Issues",
                    description="View open issues and bugs",
                    icon="bug",
                    leads_to="issues_browser",
                    learn_more="Issues track bugs, features, and tasks. They can be linked to PRs and project boards.",
                    risk_level=0
                ),
                InteractionOption(
                    id="view_workflows",
                    label="Monitor Workflows",
                    description="Check GitHub Actions status",
                    icon="workflow",
                    leads_to="workflows_browser",
                    learn_more="GitHub Actions workflows automate testing, building, and deployment. See run history and logs.",
                    risk_level=0
                ),
                InteractionOption(
                    id="sync_forks",
                    label="Sync Fork Repositories",
                    description="Update fork dependencies",
                    icon="sync",
                    action="sync_forks",
                    preview="Syncs: github/spec-kit, anthropics/anthropic-sdk-python with upstream",
                    learn_more="SLATE depends on forked repositories. Syncing keeps them up to date with upstream changes.",
                    risk_level=1,
                    reversible=True,
                    estimated_time="~2 min"
                ),
                InteractionOption(
                    id="return_hub",
                    label="Return to Command Center",
                    description="Go back to the main hub",
                    icon="home",
                    leads_to="main_hub",
                    risk_level=0
                )
            ]
        )

    def get_current_node(self) -> InteractionNode:
        """Get the current interaction node."""
        return self.nodes.get(self.current_node_id, self.nodes["main_hub"])

    def navigate_to(self, node_id: str) -> Dict[str, Any]:
        """Navigate to a specific node."""
        if node_id not in self.nodes:
            return {"success": False, "error": f"Unknown location: {node_id}"}

        node = self.nodes[node_id]
        if not node.unlocked:
            return {"success": False, "error": "This area is not yet accessible"}

        self.current_node_id = node_id
        self.visited_nodes.add(node_id)
        node.visited = True

        return {
            "success": True,
            "node": self._node_to_dict(node),
            "breadcrumb": self._get_breadcrumb(),
            "companion_dialogue": self.companion.get_dialogue(node.tone)
        }

    def select_option(self, option_id: str) -> Dict[str, Any]:
        """Select an option from the current node."""
        node = self.get_current_node()
        option = next((o for o in node.options if o.id == option_id), None)

        if not option:
            return {"success": False, "error": f"Option not found: {option_id}"}

        # Check prerequisites
        for req in option.requires:
            if req not in self.unlocked_info:
                return {
                    "success": False,
                    "error": f"Requires: {req}",
                    "hint": "Explore more to unlock this option"
                }

        # Reveal new information
        for reveal in option.reveals:
            self.unlocked_info.add(reveal)

        # If it leads to another node, navigate
        if option.leads_to:
            return self.navigate_to(option.leads_to)

        # If it's an action, execute it
        if option.action:
            return self._prepare_action(option)

        return {"success": True, "option": self._option_to_dict(option)}

    def _prepare_action(self, option: InteractionOption) -> Dict[str, Any]:
        """Prepare an action for execution (shows confirmation)."""
        return {
            "success": True,
            "type": "action_confirmation",
            "action": {
                "id": option.action,
                "label": option.label,
                "description": option.description,
                "preview": option.preview,
                "risk_level": option.risk_level,
                "reversible": option.reversible,
                "estimated_time": option.estimated_time,
                "learn_more": option.learn_more
            },
            "companion_dialogue": self.companion.get_dialogue(
                EmotionalTone.THOUGHTFUL if option.risk_level > 0 else EmotionalTone.EXCITED
            ),
            "confirm_prompt": "Ready to proceed?" if option.risk_level == 0 else "This action has some impact. Are you sure?"
        }

    async def execute_action(self, action_id: str) -> Dict[str, Any]:
        """Execute a confirmed action."""
        action_map = {
            "run_diagnostics": self._action_run_diagnostics,
            "run_tests": self._action_run_tests,
            "run_lint": self._action_run_lint,
            "security_audit": self._action_security_audit,
            "ai_code_review": self._action_ai_code_review,
            "ai_documentation": self._action_ai_documentation,
            "ai_full_analysis": self._action_ai_full_analysis,
            "docker_build": self._action_docker_build,
            "trigger_ci": self._action_trigger_ci,
            "sync_forks": self._action_sync_forks,
            "quick_health_check": self._action_quick_health,
        }

        handler = action_map.get(action_id)
        if not handler:
            return {"success": False, "error": f"Unknown action: {action_id}"}

        # Record action
        self.action_history.append({
            "action": action_id,
            "timestamp": datetime.now().isoformat(),
            "status": "started"
        })

        try:
            result = await handler()
            self.action_history[-1]["status"] = "completed" if result.get("success") else "failed"
            self.action_history[-1]["result"] = result

            # Generate companion response
            tone = EmotionalTone.CELEBRATORY if result.get("success") else EmotionalTone.SUPPORTIVE
            result["companion_dialogue"] = await self.companion.generate_contextual_response(
                f"Action {action_id} {'completed successfully' if result.get('success') else 'encountered an issue'}",
                tone=tone
            )

            return result
        except Exception as e:
            self.action_history[-1]["status"] = "error"
            self.action_history[-1]["error"] = str(e)
            return {
                "success": False,
                "error": str(e),
                "companion_dialogue": self.companion.get_dialogue(EmotionalTone.SUPPORTIVE)
            }

    async def _action_quick_health(self) -> Dict[str, Any]:
        """Quick health check."""
        return await self._run_slate_command("slate/slate_status.py", "--quick")

    async def _action_run_diagnostics(self) -> Dict[str, Any]:
        """Run full diagnostics."""
        results = []
        for label, script, args in [
            ("System Health", "slate/slate_status.py", "--quick"),
            ("Runtime Check", "slate/slate_runtime.py", "--check-all"),
            ("Workflow Health", "slate/slate_workflow_manager.py", "--status"),
        ]:
            result = await self._run_slate_command(script, args)
            results.append({"step": label, **result})

        return {
            "success": all(r.get("success") for r in results),
            "steps": results
        }

    async def _action_run_tests(self) -> Dict[str, Any]:
        """Run test suite."""
        return await self._run_slate_command(
            "-m", "pytest tests/ -v --tb=short",
            timeout=300
        )

    async def _action_run_lint(self) -> Dict[str, Any]:
        """Run linter."""
        return await self._run_shell_command("ruff check .", timeout=120)

    async def _action_security_audit(self) -> Dict[str, Any]:
        """Run security audit."""
        return await self._run_slate_command("slate/action_guard.py", "")

    async def _action_ai_code_review(self) -> Dict[str, Any]:
        """Run AI code review."""
        return await self._run_slate_command(
            "slate/slate_ai_orchestrator.py", "--analyze-recent",
            timeout=600
        )

    async def _action_ai_documentation(self) -> Dict[str, Any]:
        """Generate AI documentation."""
        return await self._run_slate_command(
            "slate/slate_ai_orchestrator.py", "--update-docs",
            timeout=900
        )

    async def _action_ai_full_analysis(self) -> Dict[str, Any]:
        """Full AI codebase analysis."""
        return await self._run_slate_command(
            "slate/slate_ai_orchestrator.py", "--analyze-codebase",
            timeout=3600
        )

    async def _action_docker_build(self) -> Dict[str, Any]:
        """Build Docker images."""
        return await self._run_shell_command(
            "docker build -t slate:latest .",
            timeout=600
        )

    async def _action_trigger_ci(self) -> Dict[str, Any]:
        """Trigger CI workflow."""
        return await self._run_shell_command("gh workflow run ci.yml", timeout=30)

    async def _action_sync_forks(self) -> Dict[str, Any]:
        """Sync fork repositories."""
        return await self._run_slate_command("slate/slate_fork_manager.py", "--sync")

    async def _run_slate_command(self, script: str, args: str, timeout: int = 120) -> Dict[str, Any]:
        """Run a SLATE Python script."""
        python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
        cmd = [python, str(WORKSPACE_ROOT / script)]
        if args:
            cmd.extend(args.split())

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(WORKSPACE_ROOT)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000] if result.stdout else "",
                "error": result.stderr[:500] if result.returncode != 0 else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _run_shell_command(self, cmd: str, timeout: int = 120) -> Dict[str, Any]:
        """Run a shell command."""
        try:
            result = subprocess.run(
                cmd,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=str(WORKSPACE_ROOT)
            )
            return {
                "success": result.returncode == 0,
                "output": result.stdout[:2000] if result.stdout else "",
                "error": result.stderr[:500] if result.returncode != 0 else ""
            }
        except subprocess.TimeoutExpired:
            return {"success": False, "error": f"Timeout after {timeout}s"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def get_learn_more(self, option_id: str) -> Dict[str, Any]:
        """Get expanded information about an option."""
        node = self.get_current_node()
        option = next((o for o in node.options if o.id == option_id), None)

        if not option:
            return {"success": False, "error": "Option not found"}

        return {
            "success": True,
            "option_id": option_id,
            "label": option.label,
            "description": option.description,
            "learn_more": option.learn_more,
            "preview": option.preview,
            "ai_hint": option.ai_hint,
            "risk_level": option.risk_level,
            "reversible": option.reversible,
            "estimated_time": option.estimated_time,
            "companion_dialogue": self.companion.get_dialogue(EmotionalTone.CURIOUS, {"topic": option.label})
        }

    async def ask_companion(self, question: str) -> Dict[str, Any]:
        """Ask the AI companion a question."""
        node = self.get_current_node()
        context = f"User is at: {node.title}. Available options: {[o.label for o in node.options]}"

        response = await self.companion.generate_contextual_response(
            context,
            user_query=question,
            tone=EmotionalTone.SUPPORTIVE
        )

        # Get recommendation if asking for advice
        recommendation = None
        if any(word in question.lower() for word in ["recommend", "suggest", "should", "best", "advice"]):
            recommendation = await self.companion.recommend_action(node.options, {})

        return {
            "success": True,
            "response": response,
            "recommendation": recommendation
        }

    def _node_to_dict(self, node: InteractionNode) -> Dict[str, Any]:
        """Convert node to dictionary for API response."""
        return {
            "id": node.id,
            "type": node.node_type.value,
            "title": node.title,
            "narrative": node.narrative,
            "tone": node.tone.value,
            "options": [self._option_to_dict(o) for o in node.options],
            "visited": node.visited,
            "parent_id": node.parent_id
        }

    def _option_to_dict(self, option: InteractionOption) -> Dict[str, Any]:
        """Convert option to dictionary for API response."""
        return {
            "id": option.id,
            "label": option.label,
            "description": option.description,
            "icon": option.icon,
            "tone": option.tone.value,
            "has_action": option.action is not None,
            "has_destination": option.leads_to is not None,
            "has_learn_more": option.learn_more is not None,
            "risk_level": option.risk_level,
            "reversible": option.reversible,
            "estimated_time": option.estimated_time,
            "preview": option.preview
        }

    def _get_breadcrumb(self) -> List[Dict[str, str]]:
        """Get navigation breadcrumb trail."""
        trail = []
        node_id = self.current_node_id

        while node_id:
            node = self.nodes.get(node_id)
            if node:
                trail.insert(0, {"id": node.id, "title": node.title})
                node_id = node.parent_id
            else:
                break

        return trail

    def get_status(self) -> Dict[str, Any]:
        """Get current experience status."""
        node = self.get_current_node()
        return {
            "current_node": self._node_to_dict(node),
            "breadcrumb": self._get_breadcrumb(),
            "visited_count": len(self.visited_nodes),
            "total_nodes": len(self.nodes),
            "action_count": len(self.action_history),
            "session_duration_seconds": (datetime.now() - self.session_start).total_seconds(),
            "unlocked_info": list(self.unlocked_info),
            "zones": {k: DevelopmentMap.get_zone_status(k) for k in DevelopmentMap.ZONES}
        }


# Global experience instance
_experience: Optional[InteractiveExperience] = None


def get_experience() -> InteractiveExperience:
    """Get or create the global interactive experience."""
    global _experience
    if _experience is None:
        _experience = InteractiveExperience()
    return _experience


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Interactive Experience")
    parser.add_argument("--status", action="store_true", help="Show current status")
    parser.add_argument("--interactive", action="store_true", help="Run interactive CLI mode")
    args = parser.parse_args()

    if args.status:
        exp = get_experience()
        print(json.dumps(exp.get_status(), indent=2, default=str))

    elif args.interactive:
        async def run_interactive():
            exp = InteractiveExperience()

            print("\n" + "=" * 70)
            print("  S.L.A.T.E. Interactive Experience")
            print("  Your development adventure begins...")
            print("=" * 70)

            while True:
                node = exp.get_current_node()
                print(f"\n{'─' * 70}")
                print(f"  [{node.title}]")
                print(f"{'─' * 70}")
                print(f"\n  {node.narrative}\n")

                # Show companion dialogue
                print(f"  SLATE: \"{exp.companion.get_dialogue(node.tone)}\"\n")

                # Show options
                print("  Options:")
                for i, opt in enumerate(node.options, 1):
                    risk = "!" * opt.risk_level if opt.risk_level > 0 else ""
                    time_hint = f" ({opt.estimated_time})" if opt.estimated_time else ""
                    print(f"    {i}. {opt.label}{risk}{time_hint}")
                    print(f"       {opt.description}")

                print(f"\n    ?. Learn more about an option")
                print(f"    q. Quit")

                choice = input("\n  Your choice: ").strip().lower()

                if choice == 'q':
                    print("\n  Until next time, developer.\n")
                    break

                if choice == '?':
                    opt_num = input("  Which option number? ").strip()
                    if opt_num.isdigit():
                        idx = int(opt_num) - 1
                        if 0 <= idx < len(node.options):
                            info = exp.get_learn_more(node.options[idx].id)
                            print(f"\n  📖 {info.get('label')}")
                            print(f"  {info.get('learn_more', 'No additional information.')}")
                            if info.get('preview'):
                                print(f"  Preview: {info['preview']}")
                    continue

                if choice.isdigit():
                    idx = int(choice) - 1
                    if 0 <= idx < len(node.options):
                        opt = node.options[idx]
                        result = exp.select_option(opt.id)

                        if result.get("type") == "action_confirmation":
                            print(f"\n  ⚡ Action: {result['action']['label']}")
                            print(f"  {result['action']['preview']}")
                            confirm = input("  Proceed? (y/n): ").strip().lower()
                            if confirm == 'y':
                                print("  Executing...")
                                action_result = asyncio.get_event_loop().run_until_complete(
                                    exp.execute_action(result['action']['id'])
                                )
                                if action_result.get("success"):
                                    print(f"  ✓ Success!")
                                    if action_result.get("output"):
                                        print(f"  {action_result['output'][:500]}")
                                else:
                                    print(f"  ✗ {action_result.get('error', 'Failed')}")

        asyncio.run(run_interactive())

    else:
        parser.print_help()
