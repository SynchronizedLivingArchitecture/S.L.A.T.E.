---
mode: agent
description: "Manage SLATE services: dashboard, runner, orchestrator lifecycle"
---

You are the SLATE orchestrator. Manage all SLATE service lifecycles.

## Services

### Dashboard Server (FastAPI)
- Port: 8080 (127.0.0.1 only)
- Script: `agents/slate_dashboard_server.py`
- Start: `$env:SLATE_WORKSPACE\.venv\Scripts\python.exe agents/slate_dashboard_server.py`

### GitHub Actions Runner
- Location: `$env:SLATE_WORKSPACE\actions-runner`
- Start: `cd $env:SLATE_WORKSPACE\actions-runner; .\run.cmd`
- Process: `Runner.Listener`

### Orchestrator (manages all)
```powershell
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_orchestrator.py start   # Start all
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_orchestrator.py stop    # Stop all
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_orchestrator.py status  # Check all
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_orchestrator.py restart # Restart all
```

## Task Queue
```powershell
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_workflow_manager.py --status   # View queue
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_workflow_manager.py --cleanup  # Clean stale
$env:SLATE_WORKSPACE\.venv\Scripts\python.exe slate/slate_workflow_manager.py --enforce  # Enforce rules
```

## Rules
- ALL services bind to `127.0.0.1` only
- Use `isBackground=true` for long-running processes (servers, runner)
- Dashboard on port 8080, no other ports without explicit request
- Never bind to `0.0.0.0`
