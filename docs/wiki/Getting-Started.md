# Getting Started
<!-- Modified: 2026-02-07T08:00:00Z | Author: CLAUDE | Change: Simplify install, add GitHub integration -->

Turn your local hardware into an AI operations center for GitHub. One command.

## Quick Install

```bash
git clone https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E.git && cd S.L.A.T.E && python install_slate.py
```

That's it. The installer handles everything:
- Python virtual environment
- PyTorch with GPU detection
- Ollama local LLM setup
- VS Code extension
- GitHub runner configuration
- ChromaDB vector store

## Prerequisites

### Required
- **Python 3.11+** - [Download](https://www.python.org/downloads/)
- **Git** - [Download](https://git-scm.com/downloads)
- **8GB RAM** minimum

### Recommended
- **NVIDIA GPU** with CUDA support (RTX 20xx or newer)
- **16GB+ RAM**
- **VS Code** with Claude Code extension

## What Gets Installed

| Component | Purpose |
|-----------|---------|
| **Ollama** | Local LLM inference (mistral-nemo, llama3.2) |
| **ChromaDB** | Vector store for codebase memory |
| **PyTorch** | GPU-optimized for your hardware |
| **GitHub Runner** | Self-hosted Actions runner with AI access |
| **Dashboard** | Real-time monitoring at localhost:8080 |

## Manual Installation

If you prefer step-by-step:

```bash
# Clone
git clone https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E.git
cd S.L.A.T.E

# Virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
source .venv/bin/activate  # Linux/macOS

# Dependencies
pip install -r requirements.txt

# Full install with dashboard
python install_slate.py
```

## Quick Start

### Verify Installation

```bash
# Check system status
python slate/slate_status.py --quick
```

Expected output:
```
SLATE Status
============
Version: 2.4.0
Python: 3.11.x
GPU: NVIDIA RTX xxxx (detected)
Ollama: Connected
Status: Ready
```

### Start the Dashboard

```bash
python agents/slate_dashboard_server.py
```

Open your browser to: http://127.0.0.1:8080

### Check All Integrations

```bash
python slate/slate_runtime.py --check-all
```

This verifies:
- Ollama connection
- Foundry Local (if installed)
- GPU detection
- ChromaDB vector store
- Task queue
- File locks
- Configuration files
- Workflow system

## Your First Task

### Using the Task Queue

Tasks are managed in `current_tasks.json`:

```json
{
  "tasks": [
    {
      "id": "task_001",
      "title": "Fix login bug",
      "description": "Users can't login with special characters in password",
      "status": "pending",
      "assigned_to": "workflow",
      "priority": 2
    }
  ]
}
```

### Using Python API

```python
from slate import create_task, get_tasks

# Create a new task
task = create_task(
    title="Implement dark mode",
    description="Add dark mode toggle to settings page",
    priority=3
)
print(f"Created task: {task.id}")

# List all tasks
tasks = get_tasks()
for t in tasks:
    print(f"- [{t.status}] {t.title}")
```

## Installing Ollama

For the best local AI experience, install Ollama:

### Windows
```bash
winget install Ollama.Ollama
```

### Linux
```bash
curl -fsSL https://ollama.com/install.sh | sh
```

### macOS
```bash
brew install ollama
```

### Pull Recommended Models

```bash
# Primary model (7B, fast)
ollama pull mistral-nemo

# Lightweight model (2.7B, very fast)
ollama pull phi

# Code-specialized model
ollama pull codellama
```

### Verify Ollama

```bash
curl http://127.0.0.1:11434/api/tags
```

## Hardware Optimization

SLATE automatically detects your hardware. For manual optimization:

```bash
# Detect hardware capabilities
python slate/slate_hardware_optimizer.py

# Install optimal PyTorch for your GPU
python slate/slate_hardware_optimizer.py --install-pytorch

# Apply runtime optimizations
python slate/slate_hardware_optimizer.py --optimize
```

## Next Steps

- [Learn about the Architecture](Architecture)
- [Understand the Agent System](Agents)
- [Configure AI Backends](AI-Backends)
- [Explore CLI Commands](CLI-Reference)
