# AI Backends

SLATE supports multiple AI backends for maximum flexibility and local-first operation.

## Backend Priority

SLATE automatically selects the best available backend:

```
1. Ollama (localhost:11434)     ← Primary, GPU-optimized
2. Foundry Local (localhost:5272) ← ONNX efficiency
3. External APIs                  ← Fallback only
```

## Ollama

The recommended backend for local AI inference.

### Installation

**Windows:**
```bash
winget install Ollama.Ollama
```

**Linux:**
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

**macOS:**
```bash
brew install ollama
```

### Starting Ollama

```bash
# Start the service
ollama serve

# Verify it's running
curl http://127.0.0.1:11434/api/tags
```

### Recommended Models

| Model | Size | VRAM | Use Case |
|-------|------|------|----------|
| `mistral-nemo` | 7B | 7GB | Primary coding model |
| `phi` | 2.7B | 2GB | Fast, lightweight tasks |
| `codellama` | 7B | 7GB | Code-specialized |
| `llama3.2` | 3B | 3GB | General purpose |

### Pulling Models

```bash
# Primary model
ollama pull mistral-nemo

# Lightweight alternative
ollama pull phi

# Code-focused
ollama pull codellama
```

### Configuration

```python
# In aurora_core/ollama_client.py
OLLAMA_CONFIG = {
    "host": "127.0.0.1",
    "port": 11434,
    "default_model": "mistral-nemo",
    "timeout": 120,
    "context_length": 8192
}
```

### Usage

```python
from aurora_core.ollama_client import OllamaClient

client = OllamaClient()

# Generate response
response = client.generate(
    prompt="Write a Python function to validate email",
    model="mistral-nemo",
    temperature=0.2
)
print(response.text)

# Stream response
for chunk in client.stream(prompt="Explain async/await"):
    print(chunk, end="", flush=True)
```

## Foundry Local

Microsoft's ONNX-optimized local inference runtime.

### Installation

```bash
# Install the foundry CLI
pip install foundry-local

# Download a model
foundry model download microsoft/Phi-3.5-mini-instruct-onnx
```

### Available Models

| Model | Parameters | Quantization | Performance |
|-------|------------|--------------|-------------|
| Phi-3.5-mini | 3.8B | INT4 | Fast |
| Phi-3-medium | 14B | INT4 | Balanced |
| Mistral-7B | 7B | INT4 | High quality |

### Configuration

```python
# In aurora_core/foundry_local.py
FOUNDRY_CONFIG = {
    "host": "127.0.0.1",
    "port": 5272,
    "default_model": "phi-3.5-mini",
    "max_tokens": 2048
}
```

### Usage

```python
from aurora_core.foundry_local import FoundryClient

client = FoundryClient()

# Check available models
models = client.list_models()
print(models)

# Generate
response = client.generate(
    prompt="Explain SOLID principles",
    model="phi-3.5-mini"
)
```

## Unified Backend

The `unified_ai_backend.py` module routes requests to the best available backend.

### Usage

```python
from aurora_core.unified_ai_backend import UnifiedBackend

backend = UnifiedBackend()

# Auto-selects best backend
response = backend.generate(
    prompt="Write a REST API endpoint",
    task_type="code_generation"
)

# Check which backend was used
print(f"Backend: {response.backend}")
print(f"Model: {response.model}")
```

### Task Type Routing

Different task types prefer different backends:

```python
TASK_ROUTING = {
    "code_generation": ["ollama", "foundry", "api"],
    "code_review": ["ollama", "foundry"],
    "documentation": ["foundry", "ollama"],
    "planning": ["ollama", "foundry"],
    "research": ["api", "ollama"]  # API for web search
}
```

### Backend Status

```bash
python aurora_core/unified_ai_backend.py --status
```

Output:
```
AI Backend Status
=================
Ollama:      Connected (mistral-nemo loaded)
Foundry:     Connected (phi-3.5-mini)
External:    Configured (rate limited)

Recommended: Ollama with mistral-nemo
```

## External APIs

For tasks requiring external capabilities (web search, etc.).

### Configuration

Set API keys in environment:

```bash
export ANTHROPIC_API_KEY=sk-ant-...
export OPENAI_API_KEY=sk-...
```

### Usage

External APIs are used only when:
1. Task explicitly requires internet access
2. Local backends are unavailable
3. Task complexity exceeds local model capability

### Rate Limiting

External APIs are rate-limited to prevent costs:

```python
EXTERNAL_API_LIMITS = {
    "requests_per_minute": 10,
    "requests_per_day": 100,
    "require_confirmation": True  # For tasks > 1000 tokens
}
```

## Model Selection

### Automatic Selection

SLATE selects models based on task complexity:

```python
def select_model(task):
    complexity = analyze_complexity(task)

    if complexity < 30:
        return "phi"  # Fast, lightweight
    elif complexity < 70:
        return "mistral-nemo"  # Balanced
    else:
        return "codellama"  # Complex code tasks
```

### Manual Override

```python
response = backend.generate(
    prompt="...",
    model="codellama",  # Force specific model
    backend="ollama"     # Force specific backend
)
```

## Memory Management

### VRAM Optimization

SLATE manages GPU memory across models:

```python
from aurora_core import get_vram_manager

vram = get_vram_manager()

# Check available memory
available = vram.get_available_mb()
print(f"Available VRAM: {available}MB")

# Load model only if memory available
if vram.can_load_model("mistral-nemo"):
    # Proceed with model load
    pass
else:
    # Use smaller model
    pass
```

### Model Unloading

```bash
# Unload unused models to free VRAM
ollama stop mistral-nemo

# Check loaded models
ollama ps
```

## Caching

Responses are cached to reduce redundant calls:

```python
from aurora_core import LLMCache

cache = LLMCache()

# Responses cached by prompt hash
# Cache hit rate visible in dashboard
stats = cache.get_stats()
print(f"Hit rate: {stats['hit_rate']}%")
```

## Troubleshooting

### Ollama Not Responding

```bash
# Check if running
curl http://127.0.0.1:11434/api/tags

# Restart service
ollama serve

# Check logs
ollama logs
```

### Model Loading Slow

```bash
# Pre-load frequently used models
ollama run mistral-nemo ""

# Check GPU utilization
nvidia-smi
```

### Out of VRAM

```bash
# Unload models
ollama stop --all

# Use smaller model
ollama pull phi
```

## Next Steps

- [CLI Reference](CLI-Reference)
- [Configuration](Configuration)
- [Troubleshooting](Troubleshooting)
