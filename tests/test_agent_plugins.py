#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create tests for agent plugins
"""
Tests for SLATE Agent Plugins (ALPHA through COPILOT).
All tests follow Arrange-Act-Assert (AAA) pattern.
"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

# Ensure workspace root is on path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate_core.plugins.agent_registry import AgentBase, AgentCapability, AgentState


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Import Tests (verify all agents can be loaded)
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentImports:
    def test_import_alpha(self):
        # Arrange & Act
        from slate_core.plugins.agents.alpha_agent import AlphaAgent

        # Assert
        assert AlphaAgent.AGENT_ID == "ALPHA"

    def test_import_beta(self):
        from slate_core.plugins.agents.beta_agent import BetaAgent
        assert BetaAgent.AGENT_ID == "BETA"

    def test_import_gamma(self):
        from slate_core.plugins.agents.gamma_agent import GammaAgent
        assert GammaAgent.AGENT_ID == "GAMMA"

    def test_import_delta(self):
        from slate_core.plugins.agents.delta_agent import DeltaAgent
        assert DeltaAgent.AGENT_ID == "DELTA"

    def test_import_epsilon(self):
        from slate_core.plugins.agents.epsilon_agent import EpsilonAgent
        assert EpsilonAgent.AGENT_ID == "EPSILON"

    def test_import_zeta(self):
        from slate_core.plugins.agents.zeta_agent import ZetaAgent
        assert ZetaAgent.AGENT_ID == "ZETA"

    def test_import_copilot(self):
        from slate_core.plugins.agents.copilot_agent import CopilotAgent
        assert CopilotAgent.AGENT_ID == "COPILOT"


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Base Contract Tests (verify all agents implement interface)
# ═══════════════════════════════════════════════════════════════════════════════

def _get_all_agents():
    """Import and instantiate all agent classes."""
    from slate_core.plugins.agents.alpha_agent import AlphaAgent
    from slate_core.plugins.agents.beta_agent import BetaAgent
    from slate_core.plugins.agents.gamma_agent import GammaAgent
    from slate_core.plugins.agents.delta_agent import DeltaAgent
    from slate_core.plugins.agents.epsilon_agent import EpsilonAgent
    from slate_core.plugins.agents.zeta_agent import ZetaAgent
    from slate_core.plugins.agents.copilot_agent import CopilotAgent

    return [
        AlphaAgent(),
        BetaAgent(),
        GammaAgent(),
        DeltaAgent(),
        EpsilonAgent(),
        ZetaAgent(),
        CopilotAgent(),
    ]


class TestAgentContract:
    """Verify all agents implement the AgentBase interface correctly."""

    @pytest.fixture(params=[
        "ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "COPILOT"
    ])
    def agent(self, request):
        agents = {a.AGENT_ID: a for a in _get_all_agents()}
        return agents[request.param]

    def test_is_agent_base_subclass(self, agent):
        # Assert
        assert isinstance(agent, AgentBase)

    def test_has_agent_id(self, agent):
        # Assert
        assert agent.AGENT_ID != ""
        assert isinstance(agent.AGENT_ID, str)

    def test_has_agent_name(self, agent):
        assert agent.AGENT_NAME != ""

    def test_has_version(self, agent):
        assert agent.AGENT_VERSION != ""

    def test_capabilities_returns_list(self, agent):
        # Act
        caps = agent.capabilities()

        # Assert
        assert isinstance(caps, list)
        for cap in caps:
            assert isinstance(cap, AgentCapability)
            assert cap.name != ""

    def test_info_returns_dict(self, agent):
        # Act
        info = agent.info()

        # Assert
        assert isinstance(info, dict)
        assert "id" in info
        assert "name" in info
        assert "version" in info
        assert "capabilities" in info

    def test_health_check_returns_dict(self, agent):
        # Act
        health = agent.health_check()

        # Assert
        assert isinstance(health, dict)
        assert "healthy" in health

    def test_default_state_is_unloaded(self, agent):
        # Assert
        assert agent.state == AgentState.UNLOADED

    def test_on_load_returns_bool(self, agent):
        # Act
        result = agent.on_load()

        # Assert
        assert isinstance(result, bool)


# ═══════════════════════════════════════════════════════════════════════════════
# EPSILON (Spec-Weaver) Specific Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestEpsilonAgent:
    def test_spec_to_markdown(self):
        # Arrange
        from slate_core.plugins.agents.epsilon_agent import EpsilonAgent
        agent = EpsilonAgent()

        spec = {
            "title": "Test Spec",
            "version": "1.0.0",
            "generated_at": "2026-01-01T00:00:00Z",
            "generator": "EPSILON/test",
            "system": {"cpu_cores": 4, "ram_total_mb": 8192, "ram_free_mb": 4096, "gpus": []},
            "agents": {"ALPHA": {"role": "Coding", "gpu": True, "gpu_mb": 4096, "cpu": 2, "model": "test"}},
            "runner_profiles": {"light": {"gpu_mb": 0, "cpu": 1, "ram_mb": 512}},
            "scaling": {"max_runners": 50, "max_parallel_workflows": 8, "gpu_partitioning": "test"},
        }

        # Act
        md = agent._spec_to_markdown(spec)

        # Assert
        assert "# Test Spec" in md
        assert "ALPHA" in md
        assert "50" in md

    def test_capacity_patterns(self):
        # Arrange
        from slate_core.plugins.agents.epsilon_agent import EpsilonAgent
        agent = EpsilonAgent()

        # Act
        caps = agent.capabilities()

        # Assert
        assert any("spec" in cap.patterns for cap in caps)
        assert any("architecture" in cap.patterns for cap in caps)

    def test_generate_capacity_spec(self, tmp_path):
        # Arrange
        from slate_core.plugins.agents.epsilon_agent import EpsilonAgent
        import slate_core.plugins.agents.epsilon_agent as eps_mod
        original = eps_mod.SPECS_DIR
        eps_mod.SPECS_DIR = tmp_path

        agent = EpsilonAgent()
        task = {"title": "Generate capacity spec", "description": "agent and runner capacity"}

        # Act
        result = agent._generate_capacity_spec(task)

        # Assert
        assert result["success"] is True
        assert (tmp_path / "agents-capacity.json").exists()
        assert (tmp_path / "agents-capacity.md").exists()

        # Cleanup
        eps_mod.SPECS_DIR = original


# ═══════════════════════════════════════════════════════════════════════════════
# ZETA (Benchmark Oracle) Specific Tests
# ═══════════════════════════════════════════════════════════════════════════════

class TestZetaAgent:
    def test_benchmark_patterns(self):
        # Arrange
        from slate_core.plugins.agents.zeta_agent import ZetaAgent
        agent = ZetaAgent()

        # Act
        caps = agent.capabilities()

        # Assert
        pattern_names = [c.name for c in caps]
        assert "benchmarking" in pattern_names
        assert "hardware_analysis" in pattern_names

    def test_save_benchmark(self, tmp_path):
        # Arrange
        from slate_core.plugins.agents.zeta_agent import ZetaAgent
        import slate_core.plugins.agents.zeta_agent as zeta_mod
        original = zeta_mod.BENCH_DIR
        zeta_mod.BENCH_DIR = tmp_path

        agent = ZetaAgent()
        data = {"test": True, "value": 42}

        # Act
        agent._save_benchmark("test_bench", data)

        # Assert
        bench_files = list(tmp_path.glob("test_bench_*.json"))
        assert len(bench_files) == 1

        # Cleanup
        zeta_mod.BENCH_DIR = original

    def test_disk_io_benchmark(self, tmp_path):
        # Arrange
        from slate_core.plugins.agents.zeta_agent import ZetaAgent
        import slate_core.plugins.agents.zeta_agent as zeta_mod
        original = zeta_mod.BENCH_DIR
        zeta_mod.BENCH_DIR = tmp_path

        agent = ZetaAgent()

        # Act
        result = agent._benchmark_disk_io()

        # Assert
        assert result["success"] is True
        assert "disk_io" in result["data"]
        assert result["data"]["disk_io"]["write_mb_s"] > 0
        assert result["data"]["disk_io"]["read_mb_s"] > 0

        # Cleanup
        zeta_mod.BENCH_DIR = original


# ═══════════════════════════════════════════════════════════════════════════════
# Unique Agent IDs Test
# ═══════════════════════════════════════════════════════════════════════════════

class TestAgentUniqueness:
    def test_all_agent_ids_unique(self):
        # Arrange
        agents = _get_all_agents()

        # Act
        ids = [a.AGENT_ID for a in agents]

        # Assert
        assert len(ids) == len(set(ids)), f"Duplicate IDs: {ids}"

    def test_seven_agents_exist(self):
        # Arrange & Act
        agents = _get_all_agents()

        # Assert
        assert len(agents) == 7

    def test_expected_ids(self):
        # Arrange
        expected = {"ALPHA", "BETA", "GAMMA", "DELTA", "EPSILON", "ZETA", "COPILOT"}

        # Act
        agents = _get_all_agents()
        actual = {a.AGENT_ID for a in agents}

        # Assert
        assert actual == expected
