# Configuration

Complete guide to configuring SLATE for your environment.

## Configuration Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | Project instructions and guidelines |
| `.env` | Environment variables (create from `.env.template`) |
| `pyproject.toml` | Python dependencies and project metadata |
| `.specify/memory/constitution.md` | Project constitution (supersedes all) |
| `current_tasks.json` | Task queue state |

## Environment Variables

Create a `.env` file in the project root:

```bash
# AI Backend Configuration
SLATE_OLLAMA_HOST=127.0.0.1
SLATE_OLLAMA_PORT=11434
SLATE_FOUNDRY_PORT=5272

# Dashboard Configuration
SLATE_DASHBOARD_PORT=8080
SLATE_DASHBOARD_HOST=127.0.0.1

# Logging
SLATE_LOG_LEVEL=INFO
SLATE_LOG_FORMAT=%(asctime)s - %(name)s - %(levelname)s - %(message)s

# GPU Configuration
SLATE_GPU_DEVICE=auto
SLATE_GPU_MEMORY_FRACTION=0.9

# Security
SLATE_ALLOW_EXTERNAL=false
SLATE_RATE_LIMIT_ENABLED=true
```

## Ollama Configuration

### Default Model

Set the default Ollama model:

```python
# In aurora_core/ollama_client.py
DEFAULT_MODEL = "mistral-nemo"
```

### Model Options

```bash
# Pull recommended models
ollama pull mistral-nemo    # 7.1GB - Best for coding tasks
ollama pull phi:latest      # 1.6GB - Fast, lightweight
ollama pull llama3.2        # 2.0GB - General purpose
ollama pull codellama       # 3.8GB - Code-specialized
```

### Ollama Server Settings

```bash
# Linux/macOS - Edit systemd service
sudo systemctl edit ollama

# Add under [Service]:
Environment="OLLAMA_HOST=127.0.0.1:11434"
Environment="OLLAMA_MODELS=/path/to/models"
Environment="OLLAMA_NUM_PARALLEL=2"
```

```powershell
# Windows - Set environment variables
[Environment]::SetEnvironmentVariable("OLLAMA_HOST", "127.0.0.1:11434", "User")
[Environment]::SetEnvironmentVariable("OLLAMA_NUM_PARALLEL", "2", "User")
```

## Foundry Local Configuration

### Model Download

```powershell
# Download Phi-3.5 (recommended)
foundry model download microsoft/Phi-3.5-mini-instruct-onnx

# Download Mistral 7B
foundry model download microsoft/Mistral-7B-Instruct-v0.3-onnx
```

### Available Models

| Model | Size | Best For |
|-------|------|----------|
| Phi-3.5-mini | 2.4GB | Quick tasks, low VRAM |
| Mistral-7B | 4.1GB | General coding |
| Phi-3.5-MoE | 6.6GB | Complex reasoning |

## GPU Configuration

### Automatic Detection

SLATE automatically detects your GPU architecture:

```python
# Check detected GPU
python aurora_core/slatepi_hardware_optimizer.py --verbose
```

### Manual GPU Selection

```bash
# Force specific GPU
export CUDA_VISIBLE_DEVICES=0

# Use multiple GPUs
export CUDA_VISIBLE_DEVICES=0,1
```

### Memory Management

```python
# In aurora_core/slatepi_hardware_optimizer.py
GPU_MEMORY_CONFIGS = {
    "blackwell": {"fraction": 0.9, "allow_growth": True},
    "ada": {"fraction": 0.85, "allow_growth": True},
    "ampere": {"fraction": 0.8, "allow_growth": True},
    "turing": {"fraction": 0.75, "allow_growth": True},
}
```

## Agent Configuration

### Agent Preferences

Configure agent task preferences in `current_tasks.json`:

```json
{
  "task_id": "task_001",
  "title": "Implement feature",
  "assigned_to": "ALPHA",
  "priority": "high"
}
```

### Assignment Options

| Value | Behavior |
|-------|----------|
| `"ALPHA"` | Force to ALPHA (coding) |
| `"BETA"` | Force to BETA (testing) |
| `"GAMMA"` | Force to GAMMA (planning) |
| `"DELTA"` | Force to DELTA (integration) |
| `"auto"` | ML-based smart routing |

### Priority Levels

| Priority | Description |
|----------|-------------|
| `urgent` | Immediate attention required |
| `high` | Important, process soon |
| `medium` | Normal priority (default) |
| `low` | Process when available |

## Dashboard Configuration

### Port Configuration

```python
# In agents/aurora_dashboard_server.py
DEFAULT_PORT = 8080
DEFAULT_HOST = "127.0.0.1"
```

### Rate Limiting

```python
# Rate limit configuration
RATE_LIMITS = {
    "/api/tasks": {"requests": 100, "window": 60},
    "/api/status": {"requests": 200, "window": 60},
    "/api/generate": {"requests": 10, "window": 60},
}
```

## ChromaDB Configuration

### Collection Settings

```python
# In aurora_core/rag_memory.py
CHROMA_SETTINGS = {
    "collection_name": "slate_memory",
    "embedding_function": "default",
    "distance_function": "cosine",
}
```

### Persistence

```python
# Vector store location
CHROMA_PERSIST_DIR = ".slate_index"
```

## Logging Configuration

### Log Levels

```python
import logging

# Available levels
logging.DEBUG    # Verbose debugging
logging.INFO     # Normal operation
logging.WARNING  # Potential issues
logging.ERROR    # Errors only
logging.CRITICAL # Critical failures
```

### Custom Log Format

```python
# In aurora_core/__init__.py
LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
```

### Log Files

Logs are stored in:
- `.slate_errors/` - Error logs with context
- Console output - Real-time logging

## Security Configuration

### ActionGuard Settings

```python
# In aurora_core/action_guard.py
BLOCKED_DOMAINS = [
    "api.openai.com",
    "api.anthropic.com",
    # All paid cloud APIs blocked
]

ALLOWED_LOCALHOST = [
    "127.0.0.1",
    "localhost",
]
```

### Network Binding

All servers bind to localhost only:

```python
# Security: Never change to 0.0.0.0
HOST = "127.0.0.1"
```

## Performance Tuning

### Batch Processing

```python
# Adjust batch sizes for your hardware
BATCH_SIZES = {
    "16GB_VRAM": 8,
    "12GB_VRAM": 4,
    "8GB_VRAM": 2,
}
```

### Caching

```python
# LLM response caching
CACHE_ENABLED = True
CACHE_DIR = "slate_cache/llm"
CACHE_TTL = 3600  # 1 hour
```

## Configuration Validation

Validate your configuration:

```bash
# Check all settings
python aurora_core/slatepi_runtime.py --check-all

# Test specific component
python aurora_core/slatepi_runtime.py --check ollama
python aurora_core/slatepi_runtime.py --check gpu
python aurora_core/slatepi_runtime.py --check chromadb
```

## Next Steps

- [Development](Development) - Contributing guide
- [Troubleshooting](Troubleshooting) - Common issues
- [CLI Reference](CLI-Reference) - Command reference
