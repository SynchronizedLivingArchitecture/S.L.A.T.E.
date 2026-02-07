# Agent & Runner Capacity Specification
<!-- Modified: 2026-02-08T06:00:00Z | Author: COPILOT | Change: Create agents-capacity spec -->

**Version:** 1.0.0  
**System:** S.L.A.T.E. v2.4.0  
**Hardware:** 2x NVIDIA GeForce RTX 5070 Ti (Blackwell, 16 GB each), 24 CPU cores, 64 GB RAM

---

## Agent Roster (7 Agents)

| Agent | ID | Role | GPU | GPU (MB) | CPU | Ollama Model | Priority |
|-------|----|------|-----|----------|-----|-------------|----------|
| Alpha Coder | ALPHA | Code generation, refactoring, bug fixes | Yes | 4096 | 2 | slate-coder (12B) | 10 |
| Beta Tester | BETA | Test generation, validation, linting | Yes | 2048 | 2 | slate-coder (12B) | 20 |
| Gamma Planner | GAMMA | Analysis, planning, documentation | No | 0 | 1 | slate-planner (7B) | 30 |
| Delta Integrator | DELTA | Claude, MCP, SDK, API integrations | No | 0 | 1 | slate-planner (7B) | 40 |
| **Epsilon Spec-Weaver** | **EPSILON** | **Specs, architecture, capacity plans** | **No** | **0** | **1** | **slate-planner (7B)** | **35** |
| **Zeta Benchmark Oracle** | **ZETA** | **Benchmarking, profiling, optimization** | **Yes** | **1024** | **2** | **slate-fast (3B)** | **25** |
| Copilot Orchestrator | COPILOT | Complex multi-step, deployment, releases | Yes | 8192 | 4 | slate-coder (12B) | 5 |

### Agent Routing Patterns

```yaml
ALPHA:   [implement, code, build, fix, create, add, refactor, write]
BETA:    [test, validate, verify, coverage, check, lint, format]
GAMMA:   [analyze, plan, research, document, review, design]
DELTA:   [claude, mcp, sdk, integration, api, plugin]
EPSILON: [spec, specification, architecture, blueprint, schema, rfc, capacity]
ZETA:    [benchmark, performance, profile, throughput, latency, optimize]
COPILOT: [complex, multi-step, orchestrate, deploy, release]
```

### Agent Dependencies & Fallbacks

| Agent | Dependencies | Fallback |
|-------|-------------|----------|
| ALPHA | None | COPILOT |
| BETA | None | ALPHA |
| GAMMA | None | EPSILON |
| DELTA | None | GAMMA |
| EPSILON | None | GAMMA |
| ZETA | None | BETA |
| COPILOT | None | ALPHA |

---

## Runner Profiles (5 Tiers)

| Profile | Description | GPU (MB) | CPU | RAM (MB) | Examples |
|---------|-------------|----------|-----|----------|----------|
| light | Lint, format, simple checks | 0 | 1 | 512 | ruff, black, mypy |
| standard | Tests, SDK validation, security | 0 | 2 | 1024 | pytest, bandit |
| gpu_light | Small model inference, embeddings | 2048 | 2 | 2048 | slate-fast, embeddings |
| gpu_heavy | Large model inference, training | 8192 | 4 | 8192 | slate-coder, fine-tuning |
| gpu_max | Maximum single-GPU allocation | 14000 | 4 | 16384 | large models, multi-GPU |

---

## Scaling Configuration (50 Runners)

### Dual-GPU Distribution

```
GPU 0 (16 GB):
  ├── 1x gpu_heavy  (8 GB)   — slate-coder inference
  └── 4x gpu_light  (2 GB each) — embeddings, classification

GPU 1 (16 GB):
  ├── 6x gpu_light  (2 GB each) — parallel inference
  └── 4x standard   (CPU-only)  — test runners

CPU Pool (24 cores):
  ├── 10x standard  (2 cores each) — pytest, validation
  └── 25x light     (1 core each)  — lint, format, checks
```

| GPU | Profile | Count | Memory/Runner | Total Memory |
|-----|---------|-------|--------------|-------------|
| 0 | gpu_heavy | 1 | 8192 MB | 8192 MB |
| 0 | gpu_light | 4 | 2048 MB | 8192 MB |
| 1 | gpu_light | 6 | 2048 MB | 12288 MB |
| 1 | standard | 4 | 0 (CPU) | 0 |
| CPU | standard | 10 | 0 | 10240 MB RAM |
| CPU | light | 25 | 0 | 12800 MB RAM |
| **Total** | | **50** | | |

### Parallelism

- **Max Parallel Workflows:** 8
- **GPU Partitioning:** Time-slice + memory-partition
- **Task Timeout:** 30 minutes per runner
- **Queue Strategy:** Priority-based with GPU affinity

---

## Resource Budget

### GPU Memory Budget (per GPU: 16,303 MB)

| GPU | Allocated | Reserved (OS/driver) | Free |
|-----|-----------|---------------------|------|
| 0 | 16,384 MB | ~500 MB | ~0 (fully partitioned) |
| 1 | 12,288 MB | ~500 MB | ~3,500 MB headroom |

### CPU Budget (24 cores)

| Pool | Runners | Cores/Runner | Total Cores |
|------|---------|-------------|-------------|
| GPU runners | 15 | ~2 avg | 30 (oversubscribed, OK — GPU-bound) |
| CPU standard | 10 | 2 | 20 |
| CPU light | 25 | 1 | 25 |

> **Note:** CPU oversubscription is acceptable because GPU runners are I/O bound
> (waiting for GPU inference) and light runners use <100% of their allocated core.

### RAM Budget (64 GB)

| Pool | Count | RAM/Runner | Total |
|------|-------|-----------|-------|
| gpu_heavy | 1 | 8192 MB | 8 GB |
| gpu_light | 10 | 2048 MB | 20 GB |
| standard | 14 | 1024 MB | 14 GB |
| light | 25 | 512 MB | 12.5 GB |
| **Total** | **50** | | **54.5 GB** |
| OS + services | | | ~9.5 GB |

---

## Agent ↔ Runner Mapping

| Agent | Preferred Profile | GPU | Concurrency |
|-------|------------------|-----|-------------|
| ALPHA | gpu_heavy | 0 | 1 (GPU-bound) |
| BETA | gpu_light / standard | 1 / CPU | 4-6 |
| GAMMA | standard / light | CPU | 10+ |
| DELTA | standard | CPU | 4 |
| EPSILON | light | CPU | 10+ |
| ZETA | gpu_light | 0-1 | 2-4 |
| COPILOT | gpu_heavy | 0 | 1 |

---

## Health Check Protocol

1. **Agent health:** Each agent implements `health_check()` → `{healthy: bool}`
2. **Degradation:** Failed health checks set state to `DEGRADED`, routes to fallback
3. **Recovery:** Successful health check restores `ACTIVE` state
4. **Monitoring:** `AgentRegistry.health_check_all()` runs on schedule
5. **Persistence:** Registry state saved to `.slate_agent_registry.json`

---

## Dynamic Agent Registration (Kernel-Style)

```python
from slate_core.plugins import get_agent_registry

registry = get_agent_registry()

# Discover all agents in slate_core/plugins/agents/
registry.discover_agents()

# Load specific agent (insmod)
registry.load_agent("EPSILON")

# Unload agent (rmmod)
registry.unload_agent("EPSILON")

# Hot-reload (rmmod + insmod)
registry.reload_agent("EPSILON")

# Route and execute task
result = registry.execute_task({"title": "Generate capacity spec", "description": "..."})

# Health check all agents
health = registry.health_check_all()
```

---

## CLI Reference

```bash
# Agent Registry (kernel-style)
python slate_core/plugins/agent_registry.py --discover    # lsmod
python slate_core/plugins/agent_registry.py --load ALPHA  # insmod
python slate_core/plugins/agent_registry.py --unload ALPHA # rmmod
python slate_core/plugins/agent_registry.py --reload ALPHA # rmmod + insmod
python slate_core/plugins/agent_registry.py --load-all    # Load everything
python slate_core/plugins/agent_registry.py --status      # Registry overview
python slate_core/plugins/agent_registry.py --health      # Health check all

# Multi-Runner (scaled to 50)
python slate/slate_multi_runner.py --init                  # Initialize 50-runner config
python slate/slate_multi_runner.py --status                # Show runner status
python slate/slate_runner_benchmark.py                     # Benchmark capacity
```
