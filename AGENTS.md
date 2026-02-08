# S.L.A.T.E. Agent Instructions
# Modified: 2026-02-08T04:00:00Z | Author: COPILOT | Change: Add hardware portability rules — never hardcode dev machine specs

## Overview
SLATE (Synchronized Living Architecture for Transformation and Evolution) is a local-first
AI agent orchestration framework. Version 2.4.0. All operations LOCAL ONLY (127.0.0.1).

## MANDATORY PROTOCOL  All Agents Must Follow

**Every agent session MUST begin by running SLATE protocols before performing work.**
This ensures system consistency and prevents regressions.

### Session Start Protocol (REQUIRED)
```bash
python slate/slate_status.py --quick          # 1. System health
python slate/slate_runtime.py --check-all     # 2. Verify all 7 integrations
python slate/slate_workflow_manager.py --status # 3. Check task queue
```

### Pre-Commit Protocol (REQUIRED)
```bash
python slate/slate_workflow_manager.py --enforce  # Block if tasks are stale
python slate/slate_workflow_manager.py --cleanup  # Archive deprecated tasks
```

## Agent System

### Agent Routing
Agents are routed by task pattern from `slate.config.yaml`:

| Pattern | Agent | Role | GPU |
|---------|-------|------|-----|
| implement, code, build, fix | ALPHA | Coding | Yes |
| test, validate, verify, coverage | BETA | Testing | Yes |
| analyze, plan, research, document | GAMMA | Planning | No |
| claude, mcp, sdk, integration | DELTA | External Bridge | No |
| diagnose, investigate, troubleshoot, interactive, explain | COPILOT_CHAT | Chat Participant | No |
| complex, multi-step | COPILOT | Full Orchestration | Yes |

### @slate Agent (COPILOT_CHAT)
The `@slate` agent is the primary copilot chat participant for the SLATE system.
It is registered as the **COPILOT_CHAT** agent in the agent registry, enabling
bidirectional task flow between the autonomous loop and the interactive chat interface.
It has access to all SLATE protocol commands and manages runner, workflows, and system health.

#### Bridge Architecture
```
Autonomous Loop ──▶ copilot_agent_bridge.py ──▶ .slate_copilot_bridge.json
                                                       │
@slate Participant ◀── slate_agentBridge tool ◀────────┘
       │
       ▼
.slate_copilot_bridge_results.json ──▶ Autonomous Loop picks up results
```

#### Available Tools
- **slate-status**: System health check (`python slate/slate_status.py --quick`)
- **slate-runtime**: Integration/dependency check (`python slate/slate_runtime.py --check-all`)
- **slate-hardware**: GPU detection & optimization (`python slate/slate_hardware_optimizer.py`)
- **slate-runner**: Runner management (`python slate/slate_runner_manager.py --status`)
- **slate-orchestrator**: Service lifecycle (`python slate/slate_orchestrator.py status`)
- **slate-workflow**: Task management (`python slate/slate_workflow_manager.py --status`)
- **slate-benchmark**: Performance benchmarks (`python slate/slate_benchmark.py`)
- **slate-chromadb**: Vector store operations (`python slate/slate_chromadb.py --status`)
- **slate-ci**: CI/CD workflow dispatch and monitoring via GitHub API

## Format Rules
All code edits MUST include a timestamp + author comment:
```python
# Modified: YYYY-MM-DDTHH:MM:SSZ | Author: COPILOT | Change: description
```

## Built-In Safeguards (All Agents Must Respect)

SLATE enforces these protections automatically:

1) **ActionGuard** - Blocks dangerous patterns
   - `rm -rf`, `format`, `del /s` (destructive commands)
   - `0.0.0.0` bindings (network exposure)
   - `eval()`, `exec()` (dynamic execution)
   - External paid API calls

2) **SDK Source Guard** - Trusted publishers only
   - Microsoft, NVIDIA, Meta, Google, Hugging Face
   - Unknown PyPI packages blocked

3) **PII Scanner** - Before GitHub sync
   - API keys, tokens, credentials detected
   - Personal info blocked from public boards

4) **Resource Limits**
   - Max concurrent tasks enforced
   - Stale tasks (>4h) flagged
   - GPU memory monitored

## Protocol Commands
```bash
# System status
python slate/slate_status.py --quick          # Quick health check
python slate/slate_status.py --json           # Machine-readable status

# Runtime integration check
python slate/slate_runtime.py --check-all     # All 7 integrations (Python, GPU, PyTorch, Transformers, Ollama, ChromaDB, venv)
python slate/slate_runtime.py --json          # JSON output

# Hardware & GPU optimization
python slate/slate_hardware_optimizer.py       # Detect GPUs
python slate/slate_hardware_optimizer.py --optimize       # Apply optimizations
python slate/slate_hardware_optimizer.py --install-pytorch # Install correct PyTorch

# Runner management
python slate/slate_runner_manager.py --detect  # Detect runner
python slate/slate_runner_manager.py --status  # Runner status
python slate/slate_runner_manager.py --dispatch "ci.yml"  # Dispatch workflow

# Orchestrator (all services)
python slate/slate_orchestrator.py start       # Start all services
python slate/slate_orchestrator.py stop        # Stop all services
python slate/slate_orchestrator.py status      # Service status

# Workflow manager
python slate/slate_workflow_manager.py --status   # Task status
python slate/slate_workflow_manager.py --cleanup   # Clean stale tasks
python slate/slate_workflow_manager.py --enforce   # Enforce completion

# ChromaDB vector store
python slate/slate_chromadb.py --status        # ChromaDB status & collections
python slate/slate_chromadb.py --index         # Index codebase into ChromaDB
python slate/slate_chromadb.py --search "query" # Semantic search
python slate/slate_chromadb.py --reset         # Reset all collections

# Benchmarks
python slate/slate_benchmark.py                # Run benchmarks
```

## Project Structure
```
slate/              # Core SDK modules (30+ Python files)
  slate_status.py           # System health checker
  slate_runtime.py          # Integration & dependency checker (7 integrations)
  slate_hardware_optimizer.py  # GPU detection & PyTorch optimization
  slate_gpu_manager.py      # Dual-GPU load balancing for Ollama
  slate_runner_manager.py   # GitHub Actions runner management
  slate_orchestrator.py     # Unified service orchestrator
  slate_workflow_manager.py # Task lifecycle & PR workflows
  slate_workflow_analyzer.py # Meta-workflow analysis & deprecation detection
  slate_benchmark.py        # Performance benchmarks
  slate_fork_manager.py     # Fork contribution workflow
  slate_chromadb.py         # ChromaDB vector store integration
  ml_orchestrator.py        # ML inference orchestrator (Ollama + PyTorch)
  slate_model_trainer.py    # Custom SLATE model builder
  slate_unified_autonomous.py   # Unified autonomous task loop
  integrated_autonomous_loop.py # Self-healing autonomous brain
  copilot_slate_runner.py   # Copilot  autonomous bridge
  slate_project_board.py    # GitHub Projects V2 integration
  mcp_server.py             # MCP server for Claude Code
  action_guard.py           # Security enforcement (ActionGuard)
  sdk_source_guard.py       # SDK source validation
  pii_scanner.py            # PII detection
  slate_terminal_monitor.py # Terminal activity tracking
  install_tracker.py        # Installation tracking

agents/             # API servers & agent modules
  runner_api.py             # RunnerAPI class for CI integration
  slate_dashboard_server.py # FastAPI dashboard (127.0.0.1:8080)
  install_api.py            # Installation API

models/             # Ollama Modelfiles for SLATE custom models
  Modelfile.slate-coder     # 12B code generation (mistral-nemo base)
  Modelfile.slate-fast      # 3B classification/summary (llama3.2 base)
  Modelfile.slate-planner   # 7B planning/analysis (mistral base)

plugins/            # VS Code & Claude extensions
  slate-copilot/            # @slate chat participant (TypeScript)
  slate-sdk/                # Claude Code plugin

skills/             # Copilot Chat skill definitions
  slate-status/             # Status checking skill
  slate-runner/             # Runner management skill
  slate-orchestrator/       # Service orchestration skill
  slate-workflow/           # Workflow management skill
  slate-help/               # Help & documentation skill
```

## Self-Hosted Runner
- **Name**: slate-runner
- **Labels**: `[self-hosted, Windows, X64, slate, gpu, cuda]`
- **Work folder**: `slate_work`
- **GPUs**: Detected at runtime via `nvidia-smi` or `torch.cuda` — NEVER hardcode GPU models/counts
- **Pre-job hook**: Sets `CUDA_VISIBLE_DEVICES`, SLATE env vars, Python PATH
- **Python**: `<workspace>\.venv\Scripts\python.exe`
- **No `actions/setup-python`**: All jobs use `GITHUB_PATH` to prepend venv
- **SLATE Custom Models**: Detected via Ollama at runtime — query the API, never assume

## Workflow Conventions
- All jobs: `runs-on: [self-hosted, slate]`
- Default shell: `powershell`
- Python setup step: `"$env:GITHUB_WORKSPACE\.venv\Scripts" | Out-File -Append $env:GITHUB_PATH`
- YAML paths: Always single-quoted (avoid backslash escape issues)
- Workflows: ci.yml, slate.yml, pr.yml, nightly.yml, cd.yml, docs.yml, fork-validation.yml, contributor-pr.yml, agentic.yml, docker.yml, release.yml

## Security Rules
- ALL network bindings: `127.0.0.1` ONLY  never `0.0.0.0`
- No external telemetry (ChromaDB telemetry disabled)
- No `curl.exe` (freezes on this system  use `urllib.request`)
- Protected files in forks: `.github/workflows/*`, `CODEOWNERS`, action guards
- Blocked patterns: `eval(`, `exec(os`, `rm -rf /`, `base64.b64decode`

## Hardware Portability Rules (ENFORCED)
SLATE is installed on many different machines. Code MUST detect hardware at runtime:
- **NEVER** hardcode GPU model names (e.g., "RTX 5070 Ti"), counts (e.g., "2x"), or VRAM sizes
- **NEVER** hardcode `CUDA_VISIBLE_DEVICES` values — detect device count dynamically
- **ALWAYS** use `nvidia-smi`, `torch.cuda`, or SLATE detection scripts to get actual hardware
- **ALWAYS** use placeholder/generic text in UI that gets replaced by runtime detection
- **Dashboard/Extension**: Service cards, status text, and prompts must show detected values
- **System prompts**: Never include specific GPU specs — instruct the agent to detect at runtime
- **Ollama models**: Never assume which models are installed — query the API
- When writing GPU-related code, test the path where `gpuCount == 0` (CPU-only installs)

## Terminal Rules
- Use `isBackground=true` for long-running commands (servers, watchers, runner)
- Never use `curl.exe`  use Python `urllib.request` or PowerShell `Invoke-RestMethod`
- Python executable: `./.venv/Scripts/python.exe` (Windows) or `./.venv/bin/python` (Linux/macOS)
- Always use `encoding='utf-8'` when opening files in Python on Windows
- Git credential: `git credential fill` with `protocol=https` / `host=github.com`

## GitHub API Access
```python
# Get token from git credential manager
import subprocess
result = subprocess.run(['git', 'credential', 'fill'],
    input='protocol=https\nhost=github.com\n',
    capture_output=True, text=True)
token = [l.split('=',1)[1] for l in result.stdout.splitlines()
         if l.startswith('password=')][0]
```
Repository API base: `https://api.github.com/repos/SynchronizedLivingArchitecture/S.L.A.T.E`
