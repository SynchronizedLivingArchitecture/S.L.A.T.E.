# API Reference

Complete API documentation for SLATE modules.

## Core Package (aurora_core)

### Package Initialization

```python
import aurora_core

# Package info
print(aurora_core.__version__)  # "2.4.0"
print(aurora_core.__author__)   # "SLATE Team"
```

### Available Exports

```python
from aurora_core import (
    # Status functions
    get_status,
    get_quick_status,

    # Task functions
    get_tasks,
    create_task,
    complete_task,

    # AI functions
    generate,

    # Utilities
    greet,
    fibonacci,
)
```

---

## Status Module

### get_status()

Get comprehensive system status.

```python
from aurora_core import get_status

status = get_status()
print(status)
```

**Returns:**
```python
{
    "version": "2.4.0",
    "python": "3.11.9",
    "platform": "Windows",
    "hardware": {
        "gpu_count": 2,
        "gpu_names": ["NVIDIA RTX 5070 Ti", "NVIDIA RTX 5070 Ti"],
        "total_vram": "32GB",
        "ram": "32GB"
    },
    "backends": {
        "ollama": {"status": "connected", "model": "mistral-nemo"},
        "foundry": {"status": "available"}
    },
    "tasks": {
        "pending": 3,
        "in_progress": 1,
        "completed": 24
    },
    "status": "ready"
}
```

### get_quick_status()

Get minimal status check.

```python
from aurora_core import get_quick_status

status = get_quick_status()
# Returns: {"status": "ready", "version": "2.4.0"}
```

---

## Task Module

### Task Schema

```python
from dataclasses import dataclass
from typing import Optional
from datetime import datetime

@dataclass
class Task:
    task_id: str
    title: str
    description: str
    status: str  # "pending", "in_progress", "completed", "blocked"
    priority: str  # "low", "medium", "high", "urgent"
    assigned_to: str  # "ALPHA", "BETA", "GAMMA", "DELTA", "auto"
    created_at: datetime
    updated_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[str] = None
```

### get_tasks()

Retrieve all tasks from the queue.

```python
from aurora_core import get_tasks

tasks = get_tasks()
for task in tasks:
    print(f"{task['task_id']}: {task['title']} [{task['status']}]")
```

**Parameters:**
- `status_filter` (optional): Filter by status ("pending", "in_progress", "completed")
- `assigned_to` (optional): Filter by agent

**Returns:** List of task dictionaries.

### create_task()

Create a new task.

```python
from aurora_core import create_task

task = create_task(
    title="Implement login feature",
    description="Add user authentication with JWT",
    priority="high",
    assigned_to="ALPHA"
)
print(f"Created task: {task['task_id']}")
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| title | str | Yes | - | Short task title |
| description | str | Yes | - | Detailed description |
| priority | str | No | "medium" | Priority level |
| assigned_to | str | No | "auto" | Target agent |

**Returns:** Created task dictionary.

### complete_task()

Mark a task as completed.

```python
from aurora_core import complete_task

result = complete_task(
    task_id="task_001",
    result="Implemented JWT authentication with refresh tokens"
)
```

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| task_id | str | Yes | Task to complete |
| result | str | No | Completion summary |

---

## AI Module

### generate()

Generate text using the unified AI backend.

```python
from aurora_core import generate

response = generate(
    prompt="Write a Python function to calculate factorial",
    task_type="code_generation"
)
print(response)
```

**Parameters:**
| Parameter | Type | Required | Default | Description |
|-----------|------|----------|---------|-------------|
| prompt | str | Yes | - | Input prompt |
| task_type | str | No | "general" | Task type for routing |
| backend | str | No | "auto" | Force specific backend |
| model | str | No | None | Force specific model |
| temperature | float | No | 0.7 | Sampling temperature |
| max_tokens | int | No | 2048 | Maximum tokens |

**Task Types:**
- `code_generation` - Writing new code
- `code_review` - Reviewing existing code
- `test_generation` - Writing tests
- `bug_fix` - Fixing bugs
- `refactoring` - Code refactoring
- `documentation` - Writing docs
- `analysis` - Code analysis
- `general` - General queries

**Returns:** Generated text string.

---

## Ollama Client

### OllamaClient

Direct interface to Ollama.

```python
from aurora_core.ollama_client import OllamaClient

client = OllamaClient(
    host="127.0.0.1",
    port=11434
)

# Check connection
if client.is_available():
    print("Ollama is running")

# List models
models = client.list_models()
for model in models:
    print(f"- {model['name']}")

# Generate
response = client.generate(
    prompt="Hello, world!",
    model="mistral-nemo"
)
print(response)
```

### Methods

| Method | Description |
|--------|-------------|
| `is_available()` | Check if Ollama is running |
| `list_models()` | Get available models |
| `generate(prompt, model, **kwargs)` | Generate text |
| `chat(messages, model, **kwargs)` | Multi-turn chat |

---

## Foundry Local Client

### FoundryClient

Interface to Foundry Local.

```python
from aurora_core.foundry_local import FoundryClient

client = FoundryClient(port=5272)

# Check availability
if client.is_available():
    print("Foundry is running")

# List models
models = client.list_models()

# Generate
response = client.generate(
    prompt="Explain REST APIs",
    model="phi-3.5-mini"
)
```

---

## Unified AI Backend

### UnifiedBackend

Automatic routing across backends.

```python
from aurora_core.unified_ai_backend import UnifiedBackend

backend = UnifiedBackend()

# Check all backends
status = backend.get_status()
print(status)

# Auto-routed generation
response = backend.generate(
    prompt="Write hello world",
    task_type="code_generation"
)
```

### Backend Routing

| Task Type | Primary Backend | Fallback |
|-----------|-----------------|----------|
| code_generation | ollama_local | foundry |
| code_review | ollama_local | foundry |
| test_generation | ollama_local | foundry |
| analysis | ollama_local | foundry |

---

## Hardware Optimizer

### HardwareOptimizer

GPU detection and optimization.

```python
from aurora_core.slatepi_hardware_optimizer import HardwareOptimizer

optimizer = HardwareOptimizer()

# Detect hardware
info = optimizer.detect()
print(f"GPU: {info['gpu_name']}")
print(f"Architecture: {info['architecture']}")
print(f"VRAM: {info['vram_gb']}GB")

# Get recommendations
recs = optimizer.get_recommendations()
for rec in recs:
    print(f"- {rec}")

# Apply optimizations
optimizer.apply_optimizations()
```

### Detection Results

```python
{
    "gpu_count": 2,
    "gpu_name": "NVIDIA RTX 5070 Ti",
    "architecture": "blackwell",
    "vram_gb": 16,
    "cuda_version": "12.4",
    "cudnn_version": "9.0",
    "recommendations": [
        "Enable TF32",
        "Enable BF16",
        "Use Flash Attention v2"
    ]
}
```

---

## Utility Functions

### greet()

Simple greeting function.

```python
from aurora_core import greet

message = greet("SLATE")
print(message)  # "Hello, SLATE!"
```

### fibonacci()

Calculate Fibonacci number.

```python
from aurora_core import fibonacci

result = fibonacci(10)
print(result)  # 55
```

---

## Dashboard API

### REST Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/status` | GET | System status |
| `/api/tasks` | GET | List all tasks |
| `/api/tasks` | POST | Create task |
| `/api/tasks/{id}` | GET | Get task by ID |
| `/api/tasks/{id}/complete` | POST | Complete task |
| `/api/generate` | POST | AI generation |

### Example Requests

```bash
# Get status
curl http://127.0.0.1:8080/api/status

# List tasks
curl http://127.0.0.1:8080/api/tasks

# Create task
curl -X POST http://127.0.0.1:8080/api/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "New task", "description": "Details..."}'

# Generate text
curl -X POST http://127.0.0.1:8080/api/generate \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Hello world in Python"}'
```

---

## Error Handling

### Common Exceptions

```python
from aurora_core.exceptions import (
    SlateError,           # Base exception
    BackendError,         # AI backend issues
    TaskError,            # Task queue issues
    ConfigurationError,   # Config problems
    HardwareError,        # GPU/hardware issues
)

try:
    response = generate("prompt")
except BackendError as e:
    print(f"Backend failed: {e}")
except SlateError as e:
    print(f"SLATE error: {e}")
```

---

## Next Steps

- [Architecture](Architecture) - System design
- [Development](Development) - Contributing guide
- [CLI Reference](CLI-Reference) - Command line tools
