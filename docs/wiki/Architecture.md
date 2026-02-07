# Architecture
<!-- Modified: 2026-02-07T08:00:00Z | Author: CLAUDE | Change: Add GitHub integration, update security section -->

SLATE creates an AI operations layer on your local hardware that bridges to GitHub's cloud infrastructure.

## System Overview

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              SLATE System                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         Presentation Layer                          │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │  Dashboard   │  │  CLI Tools   │  │  VS Code     │             │ │
│  │  │  (Port 8080) │  │              │  │  Extension   │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         Orchestration Layer                         │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │    Task      │  │   Workflow   │  │    Load      │             │ │
│  │  │   Router     │  │  Dispatcher  │  │  Balancer    │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         Execution Layer                             │ │
│  │  ┌──────────────────────────────────────────────────────────────┐ │ │
│  │  │              GitHub Actions (Self-hosted Runner)              │ │ │
│  │  │                    GPU-enabled, Local Execution               │ │ │
│  │  └──────────────────────────────────────────────────────────────┘ │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                         AI Backend Layer                            │ │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐             │ │
│  │  │   Ollama     │  │   Foundry    │  │  External    │             │ │
│  │  │  (Primary)   │  │    Local     │  │    APIs      │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                        Infrastructure Layer                         │ │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐           │ │
│  │  │ Message  │  │   RAG    │  │   GPU    │  │   LLM    │           │ │
│  │  │ Broker   │  │  Memory  │  │Scheduler │  │  Cache   │           │ │
│  │  └──────────┘  └──────────┘  └──────────┘  └──────────┘           │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

## Core Components

### Message Broker (`message_broker.py`)

Handles inter-agent communication using pub/sub messaging.

```python
from slate import get_broker, create_event

broker = get_broker()

# Publish an event
event = create_event(
    event_type="task_completed",
    data={"task_id": "t001", "result": "success"}
)
broker.publish("tasks", event)

# Subscribe to events
def handle_event(event):
    print(f"Received: {event}")

broker.subscribe("tasks", handle_event)
```

**Features:**
- In-memory default (no Redis required)
- Optional Redis for distributed deployments
- Topic-based routing
- Event persistence

### RAG Memory (`rag_memory.py`)

Vector-based memory system using ChromaDB.

```python
from slate import get_memory_manager

memory = get_memory_manager()

# Store context
memory.store_short_term("user_preference", {"theme": "dark"})

# Retrieve with semantic search
results = memory.search("authentication flow", top_k=5)
```

**Memory Types:**
- **Short-term**: Session data, current context
- **Long-term**: Persistent knowledge, learned patterns
- **Episodic**: Task history, outcomes

### GPU Scheduler (`gpu_scheduler.py`)

Manages GPU workload distribution across devices.

```python
from slate import get_scheduler, ComputeType

scheduler = get_scheduler()

# Get optimal device for task
device = scheduler.get_device(
    compute_type=ComputeType.GPU_PREFERRED,
    memory_required_mb=4096
)

# Monitor utilization
stats = scheduler.get_stats()
print(f"GPU 0: {stats['gpu_0_utilization']}%")
```

**Features:**
- Multi-GPU support
- Memory-aware allocation
- Workload balancing
- Fallback to CPU

### LLM Cache (`llm_cache.py`)

Response caching to reduce redundant API calls.

```python
from slate import LLMCache

cache = LLMCache()

# Check cache before calling API
cached = cache.get(prompt_hash)
if cached:
    return cached

# Store response
cache.set(prompt_hash, response, ttl=3600)
```

**Features:**
- Content-addressed storage
- TTL-based expiration
- Disk persistence
- Hit rate metrics

## Data Flow

### Task Execution Flow

```
1. Task Created
       │
       ▼
2. Task Router
   - Analyzes complexity
   - Determines agent
   - Checks dependencies
       │
       ▼
3. Agent Scheduler
   - Selects available agent
   - Allocates resources
   - Queues if busy
       │
       ▼
4. Agent Execution
   - Retrieves context
   - Calls AI backend
   - Generates response
       │
       ▼
5. Result Processing
   - Validates output
   - Updates memory
   - Triggers events
       │
       ▼
6. Task Completed
```

### AI Backend Selection

```
Request
   │
   ▼
Unified Backend
   │
   ├── Check Ollama ──→ Available? ──→ Use Ollama
   │                         │
   │                         ▼ No
   ├── Check Foundry ─→ Available? ──→ Use Foundry
   │                         │
   │                         ▼ No
   └── External APIs ─→ Available? ──→ Use API
                             │
                             ▼ No
                        Error: No backend
```

## Module Dependencies

```
slate/
├── Core (no dependencies)
│   ├── message_broker.py
│   ├── file_lock.py
│   └── llm_cache.py
│
├── Infrastructure (depends on Core)
│   ├── rag_memory.py      → message_broker
│   ├── gpu_scheduler.py   → file_lock
│   └── gpu_embeddings.py  → rag_memory
│
├── AI Layer (depends on Infrastructure)
│   ├── unified_ai_backend.py → llm_cache, gpu_scheduler
│   ├── ollama_client.py      → llm_cache
│   └── foundry_local.py      → llm_cache
│
├── Agent Layer (depends on AI)
│   ├── slate_agent_v2.py → unified_ai_backend, rag_memory
│   └── slate_orchestrator.py → agent_v2
│
└── Tools (depends on various)
    ├── metrics_aggregator.py → gpu_scheduler
    ├── load_balancer.py → message_broker
    └── feature_flags.py → (standalone)
```

## GitHub Integration

SLATE bridges your local hardware to GitHub's cloud:

```
GitHub Issues → SLATE local queue → Local AI processes → Results → GitHub PRs/Comments
```

### Self-Hosted Runner

SLATE auto-configures a GitHub Actions runner with AI access:
- GPU labels auto-detected (cuda, multi-gpu, blackwell)
- Pre-job hooks set environment variables
- Workflows call local LLMs without external APIs

### Project Board Sync

| Board | Auto-Route Keywords |
|-------|---------------------|
| KANBAN | Default for pending |
| BUG TRACKING | bug, fix, crash, error |
| ROADMAP | feat, add, implement |
| PLANNING | plan, design, architect |

### Workflow Architecture

| Workflow | Trigger | Purpose |
|----------|---------|---------|
| CI Pipeline | Push/PR | Linting, tests, AI code review |
| AI Maintenance | Every 4h | Codebase analysis, auto-docs |
| Nightly Jobs | Daily 4am | Full test suite, dependency audit |
| Project Automation | Every 30min | Sync Issues/PRs to boards |

## Built-In Safeguards

### ActionGuard

Every action goes through validation:

```python
from slate.action_guard import validate_action

validate_action("rm -rf /")  # BLOCKED
validate_action("pip install pkg")  # Allowed
```

**Blocked patterns:**
- `rm -rf`, `format`, `del /s` - Destructive commands
- `0.0.0.0` bindings - Network exposure
- `eval()`, `exec()` - Dynamic execution
- External paid API calls

### SDK Source Guard

Only trusted publishers:
- Microsoft, NVIDIA, Meta, Google, Hugging Face
- Unknown PyPI packages blocked

### PII Scanner

Before GitHub sync:
- Scans for API keys, tokens, credentials
- Blocks sensitive data from public boards

### Network Isolation

All services bind to localhost only:

```python
host = "127.0.0.1"  # Never "0.0.0.0"
```

## Configuration Hierarchy

```
1. Environment Variables (highest priority)
   SLATE_OLLAMA_HOST, SLATE_LOG_LEVEL, etc.
       │
       ▼
2. Local Configuration
   .env, config/local.yaml
       │
       ▼
3. Project Configuration
   pyproject.toml, .specify/memory/constitution.md
       │
       ▼
4. Default Values (lowest priority)
   Hardcoded in modules
```

## Next Steps

- [Learn about Agents](Agents)
- [Configure AI Backends](AI-Backends)
- [CLI Reference](CLI-Reference)
