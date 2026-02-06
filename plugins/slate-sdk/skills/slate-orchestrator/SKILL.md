---
name: slate-orchestrator
description: Start, stop, or check the SLATE orchestrator. Use when managing SLATE services, starting/stopping the dashboard, or checking service status.
---

# /slate

Start, stop, or check the SLATE orchestrator and all services.

## Usage
/slate [start | stop | status | restart]

## Description
The SLATE orchestrator manages all SLATE services:
- Dashboard server (port 8080)
- Workflow monitor
- Agent runners (ALPHA, BETA, GAMMA, DELTA)
- Background task processing

## Instructions

When the user invokes this skill:

**Start SLATE:**
```powershell
.\.venv\Scripts\python.exe slate/slate_orchestrator.py start
```

**Stop SLATE:**
```powershell
.\.venv\Scripts\python.exe slate/slate_orchestrator.py stop
```

**Check status:**
```powershell
.\.venv\Scripts\python.exe slate/slate_orchestrator.py status
```

**Restart (stop then start):**
```powershell
.\.venv\Scripts\python.exe slate/slate_orchestrator.py stop
.\.venv\Scripts\python.exe slate/slate_orchestrator.py start
```

Report the results showing:
1. Which services started/stopped
2. Dashboard URL (http://localhost:8080)
3. Any errors encountered
4. PID file location

## Examples

User: "/slate start"
→ Start all SLATE services

User: "/slate stop"
→ Stop all running services

User: "/slate"
→ Show current orchestrator status

User: "Start SLATE"
→ Invoke /slate start
