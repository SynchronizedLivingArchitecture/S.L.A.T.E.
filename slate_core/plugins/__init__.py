#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create dynamic agent plugin registry
"""
SLATE Core Plugins — Dynamic Agent Registry
=============================================
Kernel-style modular agent system with runtime registration,
hot-load/unload, health checks, and dependency tracking.

Usage:
    from slate_core.plugins import AgentRegistry, get_agent_registry

    registry = get_agent_registry()
    registry.discover_agents()          # Auto-scan slate_core/plugins/agents/
    registry.load_agent("EPSILON")      # Load specific agent
    registry.unload_agent("EPSILON")    # Unload agent (kernel rmmod style)
    agent = registry.get_agent("ALPHA") # Get loaded agent instance
"""

from .agent_registry import (
    AgentBase,
    AgentCapability,
    AgentInfo,
    AgentRegistry,
    AgentState,
    get_agent_registry,
)

__all__ = [
    "AgentBase",
    "AgentCapability",
    "AgentInfo",
    "AgentRegistry",
    "AgentState",
    "get_agent_registry",
]
