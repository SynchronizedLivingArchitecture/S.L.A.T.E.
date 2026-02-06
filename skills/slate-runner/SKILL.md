# /slate-runner

Manage the GitHub Actions self-hosted runner for SLATE.

## Usage
/slate-runner [--status | --setup | --dispatch <workflow>]

## Description
SLATE uses a self-hosted GitHub Actions runner for agentic task execution. This skill manages:
- Runner status and configuration
- Auto-detection of GPU and environment
- Workflow dispatch for agentic execution
- Hook configuration for environment setup

## Instructions

When the user invokes this skill:

**Check runner status:**
```powershell
.\.venv\Scripts\python.exe slate/slate_runner_manager.py --status
```

**Auto-configure runner:**
```powershell
.\.venv\Scripts\python.exe slate/slate_runner_manager.py --setup
```

**Dispatch a workflow:**
```powershell
.\.venv\Scripts\python.exe slate/slate_runner_manager.py --dispatch "ci.yml"
```

Report findings including:
1. Runner online/offline status
2. GPU configuration detected
3. Labels configured (self-hosted, slate, gpu, cuda, etc.)
4. Pre-job hooks status
5. Recent workflow runs

## Auto-Detected Labels
The runner manager automatically generates labels:
- `self-hosted` - Always present
- `slate` - SLATE environment configured
- `gpu` - GPU available
- `cuda` - CUDA toolkit available
- `blackwell` - NVIDIA Blackwell architecture (5xxx series)
- `multi-gpu` - Multiple GPUs detected

## Examples

User: "/slate-runner"
→ Check runner status

User: "/slate-runner --setup"
→ Auto-configure runner with hooks and labels

User: "/slate-runner --dispatch ci.yml"
→ Trigger the CI workflow

User: "Is the GitHub runner online?"
→ Check runner status
