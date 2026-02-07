#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create tests for agent registry
"""
Tests for SLATE Agent Registry (kernel-style module system).
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import json
import sys
import threading
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate_core.plugins.agent_registry import (
    AgentBase,
    AgentCapability,
    AgentInfo,
    AgentRegistry,
    AgentState,
)


# ═══════════════════════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════════════════════

class MockAgent(AgentBase):
    """Test agent for unit testing."""
    AGENT_ID = "MOCK"
    AGENT_NAME = "Mock Agent"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Unit test mock agent"
    REQUIRES_GPU = False
    DEPENDENCIES = []

    def capabilities(self):
        return [
            AgentCapability(
                name="mock_capability",
                patterns=["mock", "test", "fake"],
                priority=50,
                description="Mock capability for testing",
            ),
        ]

    def execute(self, task):
        return {"success": True, "result": f"mocked: {task.get('title', '')}"}


class FailingAgent(AgentBase):
    """Agent that fails on_load."""
    AGENT_ID = "FAILLOAD"
    AGENT_NAME = "Failing Agent"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Fails on load"
    REQUIRES_GPU = False

    def capabilities(self):
        return []

    def execute(self, task):
        return {"success": False, "error": "should not reach here"}

    def on_load(self):
        return False


class DependentAgent(AgentBase):
    """Agent that depends on MOCK."""
    AGENT_ID = "DEPENDENT"
    AGENT_NAME = "Dependent Agent"
    AGENT_VERSION = "1.0.0"
    AGENT_DESCRIPTION = "Depends on MOCK"
    REQUIRES_GPU = False
    DEPENDENCIES = ["MOCK"]

    def capabilities(self):
        return []

    def execute(self, task):
        return {"success": True, "result": "dependent ok"}


@pytest.fixture
def registry(tmp_path):
    """Create a fresh registry with tmp_path as agents dir."""
    return AgentRegistry(agents_dir=tmp_path / "agents")


@pytest.fixture
def populated_registry(registry):
    """Registry with MOCK agent registered manually."""
    info = AgentInfo(
        agent_id="MOCK",
        name="Mock Agent",
        version="1.0.0",
        description="Test",
        module_path=__file__,
        class_name="MockAgent",
    )
    registry._agents["MOCK"] = info
    return registry


# ═══════════════════════════════════════════════════════════════════════════════
# AgentState Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentState:
    def test_all_states_exist(self):
        # Arrange
        expected = {"unloaded", "loading", "loaded", "active", "degraded", "unloading", "error"}

        # Act
        actual = {s.value for s in AgentState}

        # Assert
        assert actual == expected

    def test_default_state(self):
        # Arrange & Act
        agent = MockAgent()

        # Assert
        assert agent.state == AgentState.UNLOADED


# ═══════════════════════════════════════════════════════════════════════════════
# AgentBase Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentBase:
    def test_info_returns_metadata(self):
        # Arrange
        agent = MockAgent()

        # Act
        info = agent.info()

        # Assert
        assert info["id"] == "MOCK"
        assert info["name"] == "Mock Agent"
        assert info["version"] == "1.0.0"
        assert "mock_capability" in info["capabilities"]

    def test_health_check_default(self):
        # Arrange
        agent = MockAgent()

        # Act
        health = agent.health_check()

        # Assert
        assert health["healthy"] is True
        assert health["agent_id"] == "MOCK"

    def test_execute_returns_result(self):
        # Arrange
        agent = MockAgent()
        task = {"title": "do something"}

        # Act
        result = agent.execute(task)

        # Assert
        assert result["success"] is True
        assert "mocked" in result["result"]

    def test_on_load_default_returns_true(self):
        # Arrange
        agent = MockAgent()

        # Act
        ok = agent.on_load()

        # Assert
        assert ok is True

    def test_capabilities_returns_list(self):
        # Arrange
        agent = MockAgent()

        # Act
        caps = agent.capabilities()

        # Assert
        assert len(caps) == 1
        assert caps[0].name == "mock_capability"
        assert "mock" in caps[0].patterns


# ═══════════════════════════════════════════════════════════════════════════════
# AgentCapability Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentCapability:
    def test_defaults(self):
        # Arrange & Act
        cap = AgentCapability(name="test")

        # Assert
        assert cap.patterns == []
        assert cap.requires_gpu is False
        assert cap.priority == 50
        assert cap.cpu_cores == 1

    def test_custom_values(self):
        # Arrange & Act
        cap = AgentCapability(
            name="gpu_task",
            patterns=["gpu", "cuda"],
            requires_gpu=True,
            gpu_memory_mb=4096,
            priority=10,
        )

        # Assert
        assert cap.requires_gpu is True
        assert cap.gpu_memory_mb == 4096
        assert len(cap.patterns) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# AgentRegistry Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentRegistryDiscovery:
    def test_discover_creates_agents_dir(self, registry, tmp_path):
        # Arrange — agents dir doesn't exist yet

        # Act
        registry.discover_agents()

        # Assert
        assert (tmp_path / "agents").exists()

    def test_discover_skips_init_file(self, registry):
        # Arrange
        registry._agents_dir.mkdir(parents=True, exist_ok=True)
        (registry._agents_dir / "__init__.py").write_text("# init", encoding="utf-8")

        # Act
        discovered = registry.discover_agents()

        # Assert
        assert len(discovered) == 0

    def test_discover_empty_dir(self, registry):
        # Arrange
        registry._agents_dir.mkdir(parents=True, exist_ok=True)

        # Act
        discovered = registry.discover_agents()

        # Assert
        assert discovered == []


class TestAgentRegistryLoadUnload:
    def test_load_unknown_agent_returns_false(self, registry):
        # Arrange — no agents registered

        # Act
        result = registry.load_agent("NONEXISTENT")

        # Assert
        assert result is False

    def test_load_already_loaded_returns_true(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE

        # Act
        result = populated_registry.load_agent("MOCK")

        # Assert
        assert result is True

    def test_unload_unknown_returns_false(self, registry):
        # Arrange — empty registry

        # Act
        result = registry.unload_agent("NONEXISTENT")

        # Assert
        assert result is False

    def test_unload_already_unloaded_returns_true(self, populated_registry):
        # Arrange
        populated_registry._agents["MOCK"].state = AgentState.UNLOADED

        # Act
        result = populated_registry.unload_agent("MOCK")

        # Assert
        assert result is True


class TestAgentRegistryRouting:
    def test_route_no_agents_returns_none(self, registry):
        # Arrange
        task = {"title": "implement something"}

        # Act
        result = registry.route_task(task)

        # Assert
        assert result is None

    def test_route_matches_capability_patterns(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        info.instance = MockAgent()
        info.instance.state = AgentState.ACTIVE
        task = {"title": "run a mock test", "description": ""}

        # Act
        result = populated_registry.route_task(task)

        # Assert
        assert result == "MOCK"

    def test_route_no_match_returns_none(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        info.instance = MockAgent()
        task = {"title": "deploy to production", "description": ""}

        # Act
        result = populated_registry.route_task(task)

        # Assert
        assert result is None

    def test_execute_task_success(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        info.instance = MockAgent()
        task = {"title": "mock this task", "description": "testing"}

        # Act
        result = populated_registry.execute_task(task)

        # Assert
        assert result["success"] is True
        assert result["agent"] == "MOCK"
        assert "duration_ms" in result

    def test_execute_task_no_agent_available(self, registry):
        # Arrange
        task = {"title": "impossible task"}

        # Act
        result = registry.execute_task(task)

        # Assert
        assert result["success"] is False
        assert "No agent" in result["error"]


class TestAgentRegistryHealthChecks:
    def test_health_check_all_empty(self, registry):
        # Arrange — no agents

        # Act
        results = registry.health_check_all()

        # Assert
        assert results == {}

    def test_health_check_active_agent(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        info.instance = MockAgent()

        # Act
        results = populated_registry.health_check_all()

        # Assert
        assert "MOCK" in results
        assert results["MOCK"]["healthy"] is True

    def test_health_check_sets_degraded(self, populated_registry):
        # Arrange
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        agent = MockAgent()
        agent.health_check = lambda: {"healthy": False, "reason": "test failure"}
        info.instance = agent

        # Act
        populated_registry.health_check_all()

        # Assert
        assert info.state == AgentState.DEGRADED


class TestAgentRegistryFallback:
    def test_set_fallback(self, registry):
        # Arrange & Act
        registry.set_fallback("ALPHA", "COPILOT")

        # Assert
        assert registry._fallback_routes["ALPHA"] == "COPILOT"


class TestAgentRegistryLifecycle:
    def test_lifecycle_callback_fires(self, populated_registry):
        # Arrange
        events = []
        populated_registry.on_lifecycle(lambda aid, old, new: events.append((aid, old.value, new.value)))
        populated_registry._agents["MOCK"].state = AgentState.ACTIVE

        # Act
        populated_registry.unload_agent("MOCK")

        # Assert
        assert len(events) >= 1
        # Should contain an unloading and unloaded event
        states = [e[2] for e in events]
        assert "unloading" in states
        assert "unloaded" in states


class TestAgentRegistryStatus:
    def test_status_returns_structure(self, populated_registry):
        # Arrange — one agent registered

        # Act
        status = populated_registry.status()

        # Assert
        assert status["total_agents"] == 1
        assert "agents" in status
        assert "agents_by_state" in status
        assert "agents_dir" in status

    def test_list_agents(self, populated_registry):
        # Arrange — MOCK registered

        # Act
        agents = populated_registry.list_agents()

        # Assert
        assert len(agents) == 1
        assert agents[0]["id"] == "MOCK"
        assert agents[0]["state"] == "unloaded"


class TestAgentRegistryPersistence:
    def test_save_and_load_state(self, populated_registry, tmp_path):
        # Arrange
        populated_registry._state_file = tmp_path / "state.json"
        populated_registry.set_fallback("MOCK", "OTHER")

        # Act
        populated_registry.save_state()
        new_registry = AgentRegistry(agents_dir=tmp_path / "agents")
        new_registry._state_file = tmp_path / "state.json"
        loaded = new_registry.load_state()

        # Assert
        assert loaded is True
        assert new_registry._fallback_routes.get("MOCK") == "OTHER"

    def test_load_missing_state_returns_false(self, registry, tmp_path):
        # Arrange
        registry._state_file = tmp_path / "nonexistent.json"

        # Act
        loaded = registry.load_state()

        # Assert
        assert loaded is False


class TestAgentRegistryThreadSafety:
    def test_concurrent_access(self, populated_registry):
        # Arrange
        errors = []
        info = populated_registry._agents["MOCK"]
        info.state = AgentState.ACTIVE
        info.instance = MockAgent()

        def run_health_checks():
            try:
                for _ in range(20):
                    populated_registry.health_check_all()
            except Exception as e:
                errors.append(str(e))

        def run_status_checks():
            try:
                for _ in range(20):
                    populated_registry.status()
            except Exception as e:
                errors.append(str(e))

        # Act
        threads = [
            threading.Thread(target=run_health_checks),
            threading.Thread(target=run_status_checks),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=10)

        # Assert
        assert len(errors) == 0
