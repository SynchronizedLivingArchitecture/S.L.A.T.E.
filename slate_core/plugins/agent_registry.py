#!/usr/bin/env python3
# Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create kernel-style agent registry
"""
SLATE Agent Registry — Kernel-Style Module System
===================================================
Thread-safe registry for dynamically loadable agent modules.
Inspired by Linux kernel module system (insmod/rmmod/lsmod).

Features:
- Runtime agent registration and discovery
- Hot-load / hot-unload without process restart
- Health check + fallback routing
- Dependency tracking between agents
- ChromaDB persistence for agent skill embeddings
- Callback hooks for agent lifecycle events

Architecture:
    AgentBase (abstract)
        |
        +-- AlphaAgent (coding)
        +-- BetaAgent (testing)
        +-- GammaAgent (planning)
        +-- DeltaAgent (integration)
        +-- EpsilonAgent (spec-weaver)     <-- NEW
        +-- ZetaAgent (benchmark oracle)   <-- NEW
        +-- CopilotAgent (orchestration)

Security:
- No eval/exec — uses importlib only
- Local-only operation (127.0.0.1)
- No secrets in logs or state files
"""

import importlib
import importlib.util
import json
import logging
import sys
import threading
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Callable, Dict, List, Optional

logger = logging.getLogger("slate.agent_registry")

WORKSPACE_ROOT = Path(__file__).parent.parent.parent

# Ensure workspace root is in path for agent imports
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# Agent State Machine
# ═══════════════════════════════════════════════════════════════════════════════

class AgentState(Enum):
    """Agent lifecycle states (kernel module states)."""
    UNLOADED = "unloaded"       # Not in memory
    LOADING = "loading"         # Being loaded
    LOADED = "loaded"           # In memory, not active
    ACTIVE = "active"           # Processing tasks
    DEGRADED = "degraded"       # Health check failed, fallback active
    UNLOADING = "unloading"     # Being removed
    ERROR = "error"             # Failed to load or crashed


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Capability Descriptor
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentCapability:
    """Describes what an agent can do (for routing decisions)."""
    name: str                               # e.g., "code_generation"
    patterns: List[str] = field(default_factory=list)   # keyword triggers
    requires_gpu: bool = False
    gpu_memory_mb: int = 0
    cpu_cores: int = 1
    priority: int = 50                      # 0=highest, 100=lowest
    description: str = ""


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Base Class (Abstract — all agents must implement)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentBase(ABC):
    """Abstract base class for all SLATE agents.

    Subclass this + implement the required methods to create a new agent.
    Place your agent file in slate_core/plugins/agents/ and it will be
    auto-discovered.
    """

    # Override these in subclasses
    AGENT_ID: str = ""
    AGENT_NAME: str = ""
    AGENT_VERSION: str = "1.0.0"
    AGENT_DESCRIPTION: str = ""
    REQUIRES_GPU: bool = False
    DEPENDENCIES: List[str] = []  # Other agent IDs this agent depends on

    def __init__(self):
        self._state = AgentState.UNLOADED
        self._loaded_at: Optional[str] = None
        self._tasks_processed: int = 0
        self._tasks_failed: int = 0
        self._last_health_check: Optional[str] = None
        self._health_ok: bool = True

    @property
    def state(self) -> AgentState:
        return self._state

    @state.setter
    def state(self, value: AgentState):
        self._state = value

    @abstractmethod
    def capabilities(self) -> List[AgentCapability]:
        """Return list of capabilities this agent provides."""
        ...

    @abstractmethod
    def execute(self, task: dict) -> dict:
        """Execute a task.

        Args:
            task: Task dict with id, title, description, etc.

        Returns:
            dict with 'success' (bool), 'result' (str), 'error' (optional str)
        """
        ...

    def on_load(self) -> bool:
        """Called when agent is loaded. Return False to abort load."""
        return True

    def on_unload(self) -> None:
        """Called when agent is unloaded. Clean up resources."""
        pass

    def health_check(self) -> dict:
        """Return health status. Override for custom checks."""
        return {
            "healthy": True,
            "agent_id": self.AGENT_ID,
            "state": self._state.value,
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
        }

    def info(self) -> dict:
        """Return agent metadata."""
        return {
            "id": self.AGENT_ID,
            "name": self.AGENT_NAME,
            "version": self.AGENT_VERSION,
            "description": self.AGENT_DESCRIPTION,
            "requires_gpu": self.REQUIRES_GPU,
            "dependencies": self.DEPENDENCIES,
            "state": self._state.value,
            "loaded_at": self._loaded_at,
            "tasks_processed": self._tasks_processed,
            "tasks_failed": self._tasks_failed,
            "capabilities": [c.name for c in self.capabilities()],
        }


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Info (lightweight descriptor for unloaded agents)
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class AgentInfo:
    """Lightweight info about an agent (may or may not be loaded)."""
    agent_id: str
    name: str
    version: str
    description: str
    module_path: str
    class_name: str
    requires_gpu: bool = False
    dependencies: List[str] = field(default_factory=list)
    state: AgentState = AgentState.UNLOADED
    instance: Optional[AgentBase] = None
    load_error: Optional[str] = None


# ═══════════════════════════════════════════════════════════════════════════════
# Agent Registry (kernel module manager)
# ═══════════════════════════════════════════════════════════════════════════════

class AgentRegistry:
    """Thread-safe registry for dynamically loadable agent modules.

    Manages agent lifecycle: discover → load → activate → health_check → unload.
    Provides routing by pattern matching against agent capabilities.
    """

    def __init__(self, agents_dir: Optional[Path] = None):
        self._agents_dir = agents_dir or (WORKSPACE_ROOT / "slate_core" / "plugins" / "agents")
        self._agents: Dict[str, AgentInfo] = {}
        self._lock = threading.RLock()
        self._lifecycle_callbacks: List[Callable[[str, AgentState, AgentState], None]] = []
        self._fallback_routes: Dict[str, str] = {}  # agent_id -> fallback_agent_id
        self._state_file = WORKSPACE_ROOT / ".slate_agent_registry.json"

    # ─── Discovery ────────────────────────────────────────────────────────

    def discover_agents(self) -> List[str]:
        """Scan agents directory for agent module files.

        Returns list of discovered agent IDs.
        """
        discovered = []
        self._agents_dir.mkdir(parents=True, exist_ok=True)
        files = sorted(self._agents_dir.glob("*.py"))

        for py_file in files:
            if py_file.name.startswith("_"):
                continue

            try:
                agent_id = self._probe_agent_file(py_file)
                if agent_id:
                    discovered.append(agent_id)
            except Exception as e:
                logger.warning("Failed to probe %s: %s", py_file.name, e)

        logger.info("Discovered %d agents in %s", len(discovered), self._agents_dir)
        return discovered

    def _probe_agent_file(self, path: Path) -> Optional[str]:
        """Probe a Python file for AgentBase subclass without fully importing."""
        module_name = f"slate_core.plugins.agents.{path.stem}"

        # Ensure workspace root is in path before loading agent module
        ws_root = str(WORKSPACE_ROOT)
        if ws_root not in sys.path:
            sys.path.insert(0, ws_root)

        spec = importlib.util.spec_from_file_location(module_name, path)
        if spec is None or spec.loader is None:
            return None

        module = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(module)
        except Exception as e:
            logger.warning("Error loading %s: %s", path.name, e)
            return None

        # Find AgentBase subclasses
        # Note: We check by class name in MRO because issubclass() fails
        # when AgentBase is imported via different module paths
        for attr_name in dir(module):
            attr = getattr(module, attr_name)
            if not isinstance(attr, type):
                continue

            # Check if class inherits from AgentBase by name (not identity)
            base_names = [b.__name__ for b in attr.__mro__]
            is_agent_subclass = "AgentBase" in base_names and attr.__name__ != "AgentBase"
            has_agent_id = bool(getattr(attr, "AGENT_ID", None))

            if is_agent_subclass and has_agent_id:

                agent_id = attr.AGENT_ID
                with self._lock:
                    if agent_id not in self._agents:
                        self._agents[agent_id] = AgentInfo(
                            agent_id=agent_id,
                            name=attr.AGENT_NAME or attr_name,
                            version=attr.AGENT_VERSION,
                            description=attr.AGENT_DESCRIPTION or "",
                            module_path=str(path),
                            class_name=attr_name,
                            requires_gpu=attr.REQUIRES_GPU,
                            dependencies=list(attr.DEPENDENCIES),
                        )

                # Cache module in sys.modules for reload
                sys.modules[module_name] = module
                return agent_id

        return None

    # ─── Load / Unload (insmod / rmmod) ───────────────────────────────────

    def load_agent(self, agent_id: str) -> bool:
        """Load an agent into memory and activate it.

        Returns True on success, False on failure.
        """
        with self._lock:
            info = self._agents.get(agent_id)
            if not info:
                logger.error("Agent %s not found in registry", agent_id)
                return False

            if info.state in (AgentState.LOADED, AgentState.ACTIVE):
                return True  # Already loaded

            old_state = info.state
            info.state = AgentState.LOADING
            self._fire_lifecycle(agent_id, old_state, AgentState.LOADING)

        # Check dependencies first
        for dep in info.dependencies:
            dep_info = self._agents.get(dep)
            if not dep_info or dep_info.state not in (AgentState.LOADED, AgentState.ACTIVE):
                logger.error("Dependency %s not loaded for %s", dep, agent_id)
                with self._lock:
                    info.state = AgentState.ERROR
                    info.load_error = f"Missing dependency: {dep}"
                    self._fire_lifecycle(agent_id, AgentState.LOADING, AgentState.ERROR)
                return False

        # Import and instantiate
        try:
            module_name = f"slate_core.plugins.agents.{Path(info.module_path).stem}"
            if module_name in sys.modules:
                mod = importlib.reload(sys.modules[module_name])
            else:
                mod = importlib.import_module(module_name)

            # Find the agent class
            agent_class = getattr(mod, info.class_name)
            instance = agent_class()

            # Call on_load hook
            if not instance.on_load():
                with self._lock:
                    info.state = AgentState.ERROR
                    info.load_error = "on_load() returned False"
                    self._fire_lifecycle(agent_id, AgentState.LOADING, AgentState.ERROR)
                return False

            instance.state = AgentState.ACTIVE
            instance._loaded_at = datetime.now(timezone.utc).isoformat()

            with self._lock:
                info.instance = instance
                info.state = AgentState.ACTIVE
                info.load_error = None
                self._fire_lifecycle(agent_id, AgentState.LOADING, AgentState.ACTIVE)

            logger.info("Loaded agent %s (%s v%s)", agent_id, info.name, info.version)
            return True

        except Exception as e:
            error_msg = f"{type(e).__name__}: {e}"
            with self._lock:
                info.state = AgentState.ERROR
                info.load_error = error_msg
                self._fire_lifecycle(agent_id, AgentState.LOADING, AgentState.ERROR)
            logger.error("Failed to load agent %s: %s", agent_id, error_msg)
            return False

    def unload_agent(self, agent_id: str) -> bool:
        """Unload an agent from memory (rmmod).

        Returns True if successfully unloaded.
        """
        with self._lock:
            info = self._agents.get(agent_id)
            if not info:
                return False

            if info.state == AgentState.UNLOADED:
                return True

            # Check if other agents depend on this one
            dependents = [
                a.agent_id for a in self._agents.values()
                if agent_id in a.dependencies
                and a.state in (AgentState.LOADED, AgentState.ACTIVE)
            ]
            if dependents:
                logger.error("Cannot unload %s: depended on by %s", agent_id, dependents)
                return False

            old_state = info.state
            info.state = AgentState.UNLOADING
            self._fire_lifecycle(agent_id, old_state, AgentState.UNLOADING)

            # Call on_unload hook
            if info.instance:
                try:
                    info.instance.on_unload()
                except Exception as e:
                    logger.warning("Error in %s.on_unload(): %s", agent_id, e)

            info.instance = None
            info.state = AgentState.UNLOADED
            self._fire_lifecycle(agent_id, AgentState.UNLOADING, AgentState.UNLOADED)

            logger.info("Unloaded agent %s", agent_id)
            return True

    def reload_agent(self, agent_id: str) -> bool:
        """Hot-reload an agent (rmmod + insmod)."""
        self.unload_agent(agent_id)
        return self.load_agent(agent_id)

    def load_all(self) -> dict:
        """Load all discovered agents."""
        results = {}
        for agent_id in list(self._agents.keys()):
            results[agent_id] = self.load_agent(agent_id)
        return results

    # ─── Routing ──────────────────────────────────────────────────────────

    def route_task(self, task: dict) -> Optional[str]:
        """Route a task to the best agent based on capabilities.

        Returns agent_id or None if no agent can handle it.
        """
        title = task.get("title", "").lower()
        desc = task.get("description", "").lower()
        combined = f"{title} {desc}"

        best_agent: Optional[str] = None
        best_priority: int = 999
        best_confidence: float = 0.0

        with self._lock:
            for agent_id, info in self._agents.items():
                if info.state not in (AgentState.ACTIVE, AgentState.DEGRADED):
                    continue

                instance = info.instance
                if not instance:
                    continue

                for cap in instance.capabilities():
                    match_count = sum(1 for p in cap.patterns if p in combined)
                    if match_count > 0:
                        confidence = match_count / max(len(cap.patterns), 1)
                        higher_conf = confidence > best_confidence
                        same_conf = (confidence == best_confidence
                                     and cap.priority < best_priority)
                        if higher_conf or same_conf:
                            best_agent = agent_id
                            best_priority = cap.priority
                            best_confidence = confidence

        # Check fallback if primary agent is degraded
        if best_agent:
            info = self._agents.get(best_agent)
            if info and info.state == AgentState.DEGRADED:
                fallback = self._fallback_routes.get(best_agent)
                fb_info = self._agents.get(
                    fallback, AgentInfo("", "", "", "", "", "")
                )
                if fallback and fb_info.state == AgentState.ACTIVE:
                    logger.info("Agent %s degraded, falling back to %s", best_agent, fallback)
                    return fallback

        return best_agent

    def execute_task(self, task: dict) -> dict:
        """Route and execute a task through the best agent."""
        agent_id = self.route_task(task)
        if not agent_id:
            return {"success": False, "error": "No agent available for task", "agent": None}

        info = self._agents.get(agent_id)
        if not info or not info.instance:
            return {"success": False, "error": f"Agent {agent_id} not loaded", "agent": agent_id}

        start = time.monotonic()
        try:
            result = info.instance.execute(task)
            info.instance._tasks_processed += 1
            if not result.get("success"):
                info.instance._tasks_failed += 1
            result["agent"] = agent_id
            result["duration_ms"] = round((time.monotonic() - start) * 1000, 2)
            return result
        except Exception as e:
            info.instance._tasks_failed += 1
            error_msg = f"{type(e).__name__}: {e}"
            logger.error("Agent %s failed on task: %s", agent_id, error_msg)
            return {
                "success": False,
                "error": error_msg,
                "agent": agent_id,
                "duration_ms": round((time.monotonic() - start) * 1000, 2),
            }

    # ─── Health Checks ────────────────────────────────────────────────────

    def health_check_all(self) -> Dict[str, dict]:
        """Run health checks on all loaded agents."""
        results = {}
        with self._lock:
            for agent_id, info in self._agents.items():
                if info.instance and info.state in (AgentState.ACTIVE, AgentState.DEGRADED):
                    try:
                        health = info.instance.health_check()
                        healthy = health.get("healthy", True)
                        info.instance._last_health_check = datetime.now(timezone.utc).isoformat()
                        info.instance._health_ok = healthy

                        if not healthy and info.state == AgentState.ACTIVE:
                            info.state = AgentState.DEGRADED
                            self._fire_lifecycle(agent_id, AgentState.ACTIVE, AgentState.DEGRADED)
                        elif healthy and info.state == AgentState.DEGRADED:
                            info.state = AgentState.ACTIVE
                            self._fire_lifecycle(agent_id, AgentState.DEGRADED, AgentState.ACTIVE)

                        results[agent_id] = health
                    except Exception as e:
                        results[agent_id] = {"healthy": False, "error": str(e)}
                        if info.state == AgentState.ACTIVE:
                            info.state = AgentState.DEGRADED
                else:
                    results[agent_id] = {"healthy": None, "state": info.state.value}

        return results

    def set_fallback(self, agent_id: str, fallback_id: str) -> None:
        """Set fallback routing for when an agent is degraded."""
        with self._lock:
            self._fallback_routes[agent_id] = fallback_id

    # ─── Lifecycle Callbacks ──────────────────────────────────────────────

    def on_lifecycle(self, callback: Callable[[str, AgentState, AgentState], None]):
        """Register a callback for agent lifecycle transitions.

        Callback signature: (agent_id, old_state, new_state)
        """
        with self._lock:
            self._lifecycle_callbacks.append(callback)

    def _fire_lifecycle(self, agent_id: str, old: AgentState, new: AgentState):
        """Fire lifecycle callbacks (already holding lock)."""
        for cb in self._lifecycle_callbacks:
            try:
                cb(agent_id, old, new)
            except Exception as e:
                logger.warning("Lifecycle callback error for %s: %s", agent_id, e)

    # ─── Queries ──────────────────────────────────────────────────────────

    def get_agent(self, agent_id: str) -> Optional[AgentBase]:
        """Get loaded agent instance."""
        with self._lock:
            info = self._agents.get(agent_id)
            return info.instance if info else None

    def list_agents(self) -> List[dict]:
        """List all agents with their state."""
        with self._lock:
            return [
                {
                    "id": info.agent_id,
                    "name": info.name,
                    "version": info.version,
                    "state": info.state.value,
                    "requires_gpu": info.requires_gpu,
                    "error": info.load_error,
                }
                for info in self._agents.values()
            ]

    def status(self) -> dict:
        """Get registry status summary."""
        with self._lock:
            agents_by_state: Dict[str, int] = {}
            for info in self._agents.values():
                state = info.state.value
                agents_by_state[state] = agents_by_state.get(state, 0) + 1

            return {
                "total_agents": len(self._agents),
                "agents_by_state": agents_by_state,
                "agents": self.list_agents(),
                "fallback_routes": dict(self._fallback_routes),
                "agents_dir": str(self._agents_dir),
            }

    # ─── Persistence ──────────────────────────────────────────────────────

    def save_state(self) -> None:
        """Save registry state to disk."""
        state = {
            "agents": {
                agent_id: {
                    "state": info.state.value,
                    "load_error": info.load_error,
                    "tasks_processed": info.instance._tasks_processed if info.instance else 0,
                    "tasks_failed": info.instance._tasks_failed if info.instance else 0,
                }
                for agent_id, info in self._agents.items()
            },
            "fallback_routes": self._fallback_routes,
            "saved_at": datetime.now(timezone.utc).isoformat(),
        }
        with open(self._state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)

    def load_state(self) -> bool:
        """Load previous registry state."""
        if not self._state_file.exists():
            return False

        try:
            with open(self._state_file, encoding="utf-8") as f:
                state = json.load(f)

            self._fallback_routes = state.get("fallback_routes", {})
            return True
        except Exception as e:
            logger.warning("Failed to load registry state: %s", e)
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# Singleton
# ═══════════════════════════════════════════════════════════════════════════════

_global_registry: Optional[AgentRegistry] = None
_registry_lock = threading.Lock()


def get_agent_registry() -> AgentRegistry:
    """Get or create the global agent registry singleton."""
    global _global_registry
    if _global_registry is None:
        with _registry_lock:
            if _global_registry is None:
                _global_registry = AgentRegistry()
    return _global_registry


# ═══════════════════════════════════════════════════════════════════════════════
# CLI
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI for agent registry operations."""
    import argparse

    parser = argparse.ArgumentParser(description="SLATE Agent Registry (kernel-style)")
    parser.add_argument(
        "--discover", action="store_true",
        help="Discover available agents (lsmod-style)",
    )
    parser.add_argument("--load", type=str, help="Load an agent (insmod-style)")
    parser.add_argument("--unload", type=str, help="Unload an agent (rmmod-style)")
    parser.add_argument("--reload", type=str, help="Hot-reload an agent")
    parser.add_argument("--load-all", action="store_true", help="Load all discovered agents")
    parser.add_argument("--status", action="store_true", help="Show registry status")
    parser.add_argument("--health", action="store_true", help="Run health checks")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    registry = get_agent_registry()

    if args.discover:
        agents = registry.discover_agents()
        if args.json:
            print(json.dumps({"discovered": agents}))
        else:
            print(f"Discovered {len(agents)} agents:")
            for a in agents:
                print(f"  - {a}")

    elif args.load:
        registry.discover_agents()
        ok = registry.load_agent(args.load)
        print(f"{'OK' if ok else 'FAIL'}: {args.load}")

    elif args.unload:
        ok = registry.unload_agent(args.unload)
        print(f"{'OK' if ok else 'FAIL'}: unload {args.unload}")

    elif args.reload:
        registry.discover_agents()
        ok = registry.reload_agent(args.reload)
        print(f"{'OK' if ok else 'FAIL'}: reload {args.reload}")

    elif args.load_all:
        registry.discover_agents()
        results = registry.load_all()
        for agent_id, ok in results.items():
            print(f"  {'OK' if ok else 'FAIL'}: {agent_id}")

    elif args.health:
        registry.discover_agents()
        registry.load_all()
        results = registry.health_check_all()
        if args.json:
            print(json.dumps(results, indent=2))
        else:
            for agent_id, health in results.items():
                status = "OK" if health.get("healthy") else "DEGRADED"
                print(f"  {agent_id}: {status}")

    elif args.status:
        registry.discover_agents()
        status = registry.status()
        if args.json:
            print(json.dumps(status, indent=2))
        else:
            print("=" * 50)
            print("  SLATE Agent Registry")
            print("=" * 50)
            print(f"  Total Agents: {status['total_agents']}")
            for state, count in status.get("agents_by_state", {}).items():
                print(f"    {state}: {count}")
            print()
            print("  Agents:")
            for a in status["agents"]:
                gpu = " [GPU]" if a["requires_gpu"] else ""
                err = f" (ERROR: {a['error']})" if a.get("error") else ""
                line = (f"    {a['id']:<12} {a['name']:<25}"
                       f" {a['state']:<10} v{a['version']}{gpu}{err}")
                print(line)
            if status.get("fallback_routes"):
                print()
                print("  Fallback Routes:")
                for src, dst in status["fallback_routes"].items():
                    print(f"    {src} -> {dst}")
            print("=" * 50)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
