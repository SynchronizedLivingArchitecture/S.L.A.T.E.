# CLI Reference

Complete reference for SLATE command-line tools.

## Quick Reference

| Command | Description |
|---------|-------------|
| `slatepi_status.py` | System status check |
| `slatepi_runtime.py` | Integration verification |
| `slatepi_benchmark.py` | Performance testing |
| `slatepi_hardware_optimizer.py` | Hardware detection/optimization |
| `unified_ai_backend.py` | AI backend management |

## Status Commands

### slatepi_status.py

Check overall system status.

```bash
# Quick status
python aurora_core/slatepi_status.py --quick

# Full status with details
python aurora_core/slatepi_status.py

# Task summary
python aurora_core/slatepi_status.py --tasks

# JSON output
python aurora_core/slatepi_status.py --json
```

**Output Example:**
```
SLATE Status
============
Version: 2.4.0
Python: 3.11.9
Platform: Windows 11

Hardware:
  GPU 0: NVIDIA RTX 5070 Ti (16GB)
  GPU 1: NVIDIA RTX 5070 Ti (16GB)
  RAM: 32GB

Backends:
  Ollama: Connected (mistral-nemo)
  Foundry: Available

Tasks:
  Pending: 3
  In Progress: 1
  Completed: 24

Status: Ready
```

### slatepi_runtime.py

Verify all integrations.

```bash
# Check all integrations
python aurora_core/slatepi_runtime.py --check-all

# Check specific integration
python aurora_core/slatepi_runtime.py --check ollama
python aurora_core/slatepi_runtime.py --check gpu
python aurora_core/slatepi_runtime.py --check chromadb

# JSON output
python aurora_core/slatepi_runtime.py --check-all --json
```

**Integrations Checked:**
1. Ollama connection
2. Foundry Local
3. GPU detection
4. ChromaDB vector store
5. Task queue
6. File locks
7. Configuration files
8. Agent system
9. Dashboard server
10. AI Toolkit

## Hardware Commands

### slatepi_hardware_optimizer.py

Detect and optimize for your hardware.

```bash
# Detect hardware
python aurora_core/slatepi_hardware_optimizer.py

# Install optimal PyTorch
python aurora_core/slatepi_hardware_optimizer.py --install-pytorch

# Apply runtime optimizations
python aurora_core/slatepi_hardware_optimizer.py --optimize

# Detailed hardware report
python aurora_core/slatepi_hardware_optimizer.py --verbose
```

**Detection Output:**
```
Hardware Detection
==================
GPU Architecture: Blackwell (RTX 50xx)
GPU Count: 2
Total VRAM: 32GB
CUDA Version: 12.4
cuDNN: 9.0

Recommendations:
  - Enable TF32: Yes
  - Enable BF16: Yes
  - Flash Attention: v2
  - CUDA Graphs: Enabled

Apply with: --optimize
```

## Benchmark Commands

### slatepi_benchmark.py

Run performance benchmarks.

```bash
# Full benchmark suite
python aurora_core/slatepi_benchmark.py

# Quick benchmark
python aurora_core/slatepi_benchmark.py --quick

# CPU only
python aurora_core/slatepi_benchmark.py --cpu-only

# GPU only
python aurora_core/slatepi_benchmark.py --gpu-only

# Save results
python aurora_core/slatepi_benchmark.py --output results.json
```

**Benchmark Output:**
```
SLATE Benchmark
===============
CPU Benchmark:
  Single-threaded: 1,245 ops/sec
  Multi-threaded: 8,920 ops/sec

GPU Benchmark:
  FP32: 12.4 TFLOPS
  FP16: 24.8 TFLOPS
  Memory Bandwidth: 672 GB/s

LLM Benchmark:
  Ollama (mistral-nemo):
    Tokens/sec: 48.5
    First token: 120ms
    Context: 8192 tokens

Overall Score: 8,450 points
```

## AI Backend Commands

### unified_ai_backend.py

Manage AI backends.

```bash
# Check all backend status
python aurora_core/unified_ai_backend.py --status

# Test specific backend
python aurora_core/unified_ai_backend.py --test ollama
python aurora_core/unified_ai_backend.py --test foundry

# Generate with auto-routing
python aurora_core/unified_ai_backend.py --generate "Write hello world in Python"

# Force specific backend
python aurora_core/unified_ai_backend.py --generate "..." --backend ollama
```

### foundry_local.py

Foundry Local specific commands.

```bash
# Check Foundry status
python aurora_core/foundry_local.py --check

# List available models
python aurora_core/foundry_local.py --models

# Generate text
python aurora_core/foundry_local.py --generate "Explain REST APIs"

# Use specific model
python aurora_core/foundry_local.py --generate "..." --model phi-3.5-mini
```

### ollama_client.py

Ollama specific commands.

```bash
# Check connection
python aurora_core/ollama_client.py --check

# List loaded models
python aurora_core/ollama_client.py --list

# Generate
python aurora_core/ollama_client.py --generate "Write a function"
```

## Task Commands

### Task Queue Management

```bash
# View pending tasks
python -c "from aurora_core import get_tasks; print(get_tasks())"

# Create task via CLI
python -c "
from aurora_core import create_task
task = create_task(
    title='Fix bug',
    description='Login not working',
    priority=2
)
print(f'Created: {task.id}')
"
```

## Dashboard Commands

### Start Dashboard

```bash
# Start on default port (8080)
python agents/aurora_dashboard_server.py

# Custom port
python agents/aurora_dashboard_server.py --port 9000

# Debug mode
python agents/aurora_dashboard_server.py --debug
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `SLATE_OLLAMA_HOST` | Ollama host | 127.0.0.1 |
| `SLATE_OLLAMA_PORT` | Ollama port | 11434 |
| `SLATE_DASHBOARD_PORT` | Dashboard port | 8080 |
| `SLATE_LOG_LEVEL` | Log verbosity | INFO |
| `SLATE_GPU_DEVICE` | Force GPU device | auto |

## Common Patterns

### Health Check Script

```bash
#!/bin/bash
# health_check.sh

echo "Checking SLATE health..."

# Quick status
python aurora_core/slatepi_status.py --quick

# Check integrations
python aurora_core/slatepi_runtime.py --check-all

# Test Ollama
curl -s http://127.0.0.1:11434/api/tags > /dev/null && echo "Ollama: OK" || echo "Ollama: FAIL"

echo "Health check complete"
```

### Development Workflow

```bash
# Start development environment
python aurora_core/slatepi_hardware_optimizer.py --optimize
python agents/aurora_dashboard_server.py &
python aurora_core/slatepi_status.py --quick

# Work...

# Clean up
pkill -f aurora_dashboard_server
```

## Exit Codes

| Code | Meaning |
|------|---------|
| 0 | Success |
| 1 | General error |
| 2 | Configuration error |
| 3 | Connection error |
| 4 | Hardware error |

## Next Steps

- [Configuration](Configuration)
- [Troubleshooting](Troubleshooting)
- [Development](Development)
