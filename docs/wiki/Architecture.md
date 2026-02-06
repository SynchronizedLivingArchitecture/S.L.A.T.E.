# Architecture

This document describes the SLATE system architecture and core components.

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
│  │  │    Task      │  │    Agent     │  │    Load      │             │ │
│  │  │   Router     │  │  Scheduler   │  │  Balancer    │             │ │
│  │  └──────────────┘  └──────────────┘  └──────────────┘             │ │
│  └────────────────────────────────────────────────────────────────────┘ │
│                                    │                                     │
│  ┌────────────────────────────────────────────────────────────────────┐ │
│  │                           Agent Layer                               │ │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐               │ │
│  │  │  ALPHA  │  │  BETA   │  │  GAMMA  │  │  DELTA  │               │ │
│  │  │ Coding  │  │ Testing │  │Planning │  │ Bridge  │               │ │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘               │ │
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
from aurora_core import get_broker, create_event

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
from aurora_core import get_memory_manager

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
from aurora_core import get_scheduler, ComputeType

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
from aurora_core import LLMCache

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
aurora_core/
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
│   ├── aurora_agent_v2.py → unified_ai_backend, rag_memory
│   └── aurora_orchestrator.py → agent_v2
│
└── Tools (depends on various)
    ├── metrics_aggregator.py → gpu_scheduler
    ├── load_balancer.py → message_broker
    └── feature_flags.py → (standalone)
```

## Security Architecture

### Network Isolation

All services bind to localhost only:

```python
# All servers use
host = "127.0.0.1"  # Never "0.0.0.0"
```

### Action Guard

The `action_guard.py` module validates all agent actions:

```python
from aurora_core.action_guard import validate_action

# Blocks dangerous operations
result = validate_action("rm -rf /")  # Blocked
result = validate_action("pip install pkg")  # Allowed
```

**Blocked Actions:**
- Paid cloud API calls (OpenAI, Anthropic direct)
- Destructive filesystem operations
- Network requests to external hosts
- Credential exposure

### Rate Limiting

API endpoints are rate-limited:

```python
from aurora_core import rate_limiter

@rate_limiter.limit("10/minute")
async def api_endpoint():
    ...
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
