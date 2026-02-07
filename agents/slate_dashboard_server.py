#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_dashboard_server [python]
# Author: Claude | Created: 2026-02-06T23:45:00Z | Modified: 2026-02-07T00:00:00Z
# Purpose: SLATE Dashboard Server - Robust FastAPI server for agentic workflow management
# ═══════════════════════════════════════════════════════════════════════════════
"""
SLATE Dashboard Server
======================
Production-grade FastAPI server for SLATE system monitoring and agentic workflow management.

Features:
- Real-time WebSocket updates for live status
- GitHub Actions integration (workflows, runners, PRs)
- Task queue management with CRUD operations
- System metrics (GPU, CPU, memory)
- Glassmorphism UI with SLATE design system

Design System:
- Theme: Glassmorphism (75% opacity, blur effects)
- Colors: Muted pastels (slate blues, soft greens, warm grays)
- Fonts: System fonts (Segoe UI, Consolas)
- Security: 127.0.0.1 binding only

Endpoints:
    GET  /                    -> Dashboard UI
    GET  /health              -> Health check
    WS   /ws                  -> WebSocket for real-time updates

    GET  /api/status          -> Full system status
    GET  /api/orchestrator    -> Orchestrator status
    GET  /api/runner          -> GitHub runner status
    GET  /api/workflows       -> Recent workflow runs
    GET  /api/tasks           -> Task queue
    POST /api/tasks           -> Create task
    PUT  /api/tasks/{id}      -> Update task
    DELETE /api/tasks/{id}    -> Delete task
    POST /api/dispatch/{name} -> Dispatch workflow

Usage:
    python agents/slate_dashboard_server.py
    # Opens http://127.0.0.1:8080
"""

import asyncio
import json
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List
import uuid

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

# ─── Dependencies ─────────────────────────────────────────────────────────────

try:
    from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Request
    from fastapi.responses import HTMLResponse, JSONResponse
    from fastapi.middleware.cors import CORSMiddleware
    from starlette.middleware.base import BaseHTTPMiddleware
    from starlette.responses import Response
    import uvicorn
except ImportError:
    print("[!] Missing dependencies. Run: pip install fastapi uvicorn websockets")
    sys.exit(1)

# ─── App Configuration ────────────────────────────────────────────────────────

app = FastAPI(
    title="SLATE Dashboard",
    description="Agentic Workflow Management System",
    version="2.4.0"
)

# CORS for local development and VSCode webviews
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins for VSCode webview compatibility
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
)

# Custom headers middleware for VSCode webview compatibility
class VSCodeCompatMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        # Add headers for VSCode webview compatibility
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
        return response

app.add_middleware(VSCodeCompatMiddleware)

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self._lock = threading.Lock()

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        with self._lock:
            self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        with self._lock:
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

    async def broadcast(self, message: dict):
        with self._lock:
            connections = list(self.active_connections)
        for connection in connections:
            try:
                await connection.send_json(message)
            except Exception:
                self.disconnect(connection)

manager = ConnectionManager()

# ─── Helper Functions ─────────────────────────────────────────────────────────

def get_gh_cli() -> str:
    """Get GitHub CLI path."""
    gh_path = WORKSPACE_ROOT / ".tools" / "gh.exe"
    if gh_path.exists():
        return str(gh_path)
    return "gh"

def load_tasks() -> List[Dict[str, Any]]:
    """Load tasks from current_tasks.json."""
    task_file = WORKSPACE_ROOT / "current_tasks.json"
    if task_file.exists():
        try:
            data = json.loads(task_file.read_text(encoding="utf-8"))
            if isinstance(data, list):
                return data
            return data.get("tasks", [])
        except Exception:
            pass
    return []

def save_tasks(tasks: List[Dict[str, Any]]):
    """Save tasks to current_tasks.json."""
    task_file = WORKSPACE_ROOT / "current_tasks.json"
    task_file.write_text(json.dumps(tasks, indent=2), encoding="utf-8")

# ─── Health & Status Endpoints ────────────────────────────────────────────────

@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "ok", "timestamp": datetime.now(timezone.utc).isoformat(), "service": "slate-dashboard"}

@app.get("/api/status")
async def api_status():
    """Get comprehensive system status."""
    try:
        from slate.slate_status import get_status
        status = get_status()
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(content={"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})

@app.get("/api/orchestrator")
async def api_orchestrator():
    """Get orchestrator status."""
    try:
        from slate.slate_orchestrator import SlateOrchestrator
        orch = SlateOrchestrator()
        return JSONResponse(content=orch.status())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/runner")
async def api_runner():
    """Get GitHub runner status with detailed info."""
    try:
        from slate.slate_runner_manager import SlateRunnerManager
        mgr = SlateRunnerManager()
        detection = mgr.detect()

        # Add GitHub API runner status
        try:
            gh_cli = get_gh_cli()
            result = subprocess.run(
                [gh_cli, "api", "repos/SynchronizedLivingArchitecture/S.L.A.T.E/actions/runners",
                 "--jq", ".runners[0]"],
                capture_output=True, text=True, timeout=10, cwd=str(WORKSPACE_ROOT)
            )
            if result.returncode == 0:
                detection["github_runner"] = json.loads(result.stdout)
        except Exception:
            pass

        return JSONResponse(content=detection)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/workflows")
async def api_workflows():
    """Get recent GitHub workflow runs."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "run", "list", "--limit", "15", "--json",
             "name,status,conclusion,createdAt,updatedAt,databaseId,headBranch,event"],
            capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            runs = json.loads(result.stdout)
            return JSONResponse(content={"runs": runs, "count": len(runs)})
        return JSONResponse(content={"error": result.stderr, "runs": []})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "runs": []})

@app.get("/api/workflow/{run_id}")
async def api_workflow_detail(run_id: int):
    """Get detailed workflow run info."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "run", "view", str(run_id), "--json",
             "name,status,conclusion,jobs,createdAt,updatedAt"],
            capture_output=True, text=True, timeout=10, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            return JSONResponse(content=json.loads(result.stdout))
        return JSONResponse(content={"error": result.stderr}, status_code=404)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/workflow-pipeline")
async def api_workflow_pipeline():
    """Get workflow pipeline data."""
    try:
        tasks = load_tasks()

        # Pipeline stats
        pipeline = {
            "tasks": len(tasks),
            "pending": len([t for t in tasks if t.get("status") == "pending"]),
            "in_progress": len([t for t in tasks if t.get("status") == "in-progress"]),
            "completed": len([t for t in tasks if t.get("status") == "completed"])
        }

        # Get workflow info
        try:
            gh_cli = get_gh_cli()
            result = subprocess.run(
                [gh_cli, "run", "list", "--limit", "10", "--json", "status,conclusion"],
                capture_output=True, text=True, timeout=10, cwd=str(WORKSPACE_ROOT)
            )
            if result.returncode == 0:
                runs = json.loads(result.stdout)
                pipeline["workflows_running"] = len([r for r in runs if r.get("status") == "in_progress"])
                pipeline["workflows_success"] = len([r for r in runs if r.get("conclusion") == "success"])
                pipeline["workflows_failed"] = len([r for r in runs if r.get("conclusion") == "failure"])
        except Exception:
            pipeline["workflows_running"] = 0
            pipeline["workflows_success"] = 0
            pipeline["workflows_failed"] = 0

        # Get runner status
        try:
            from slate.slate_runner_manager import SlateRunnerManager
            mgr = SlateRunnerManager()
            detection = mgr.detect()
            pipeline["runner_online"] = detection.get("runner_installed", False)
            pipeline["runner_busy"] = pipeline["workflows_running"] > 0
        except Exception:
            pipeline["runner_online"] = False
            pipeline["runner_busy"] = False

        return JSONResponse(content={"pipeline": pipeline})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

# ─── GitHub Integration Endpoints ────────────────────────────────────────────

@app.get("/api/github/prs")
async def api_github_prs():
    """Get open pull requests."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "pr", "list", "--state", "open", "--limit", "10",
             "--json", "number,title,author,labels,createdAt,headRefName,additions,deletions"],
            capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            prs = json.loads(result.stdout) if result.stdout.strip() else []
            return JSONResponse(content={"prs": prs, "count": len(prs)})
        return JSONResponse(content={"error": result.stderr, "prs": [], "count": 0})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "prs": [], "count": 0})

@app.get("/api/github/commits")
async def api_github_commits():
    """Get recent commits on current branch."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "api", "repos/SynchronizedLivingArchitecture/S.L.A.T.E/commits",
             "--jq", "[.[:10][] | {sha: .sha, message: .commit.message, author: .commit.author.name, date: .commit.author.date}]"],
            capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            commits = json.loads(result.stdout) if result.stdout.strip() else []
            return JSONResponse(content={"commits": commits, "count": len(commits)})
        return JSONResponse(content={"error": result.stderr, "commits": [], "count": 0})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "commits": [], "count": 0})

@app.get("/api/github/issues")
async def api_github_issues():
    """Get open issues."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "issue", "list", "--state", "open", "--limit", "15",
             "--json", "number,title,labels,author,createdAt"],
            capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            issues = json.loads(result.stdout) if result.stdout.strip() else []
            return JSONResponse(content={"issues": issues, "count": len(issues)})
        return JSONResponse(content={"error": result.stderr, "issues": [], "count": 0})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "issues": [], "count": 0})

@app.get("/api/github/releases")
async def api_github_releases():
    """Get latest release."""
    try:
        gh_cli = get_gh_cli()
        result = subprocess.run(
            [gh_cli, "release", "list", "--limit", "1",
             "--json", "tagName,name,publishedAt,isPrerelease"],
            capture_output=True, text=True, timeout=10, cwd=str(WORKSPACE_ROOT)
        )
        if result.returncode == 0:
            releases = json.loads(result.stdout) if result.stdout.strip() else []
            release = releases[0] if releases else None
            return JSONResponse(content={"release": release})
        return JSONResponse(content={"error": result.stderr, "release": None})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "release": None})

# ─── System Health Endpoints ─────────────────────────────────────────────────

@app.get("/api/system/gpu")
async def api_system_gpu():
    """Get real-time GPU utilization."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=index,name,utilization.gpu,utilization.memory,memory.used,memory.total,temperature.gpu",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            gpus = []
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 7:
                    gpus.append({
                        "index": int(parts[0]),
                        "name": parts[1],
                        "gpu_util": int(parts[2]) if parts[2].isdigit() else 0,
                        "memory_util": int(parts[3]) if parts[3].isdigit() else 0,
                        "memory_used": int(parts[4]) if parts[4].isdigit() else 0,
                        "memory_total": int(parts[5]) if parts[5].isdigit() else 0,
                        "temperature": int(parts[6]) if parts[6].isdigit() else None
                    })
            return JSONResponse(content={"available": True, "gpus": gpus})
        return JSONResponse(content={"available": False, "gpus": []})
    except Exception:
        return JSONResponse(content={"available": False, "gpus": []})

@app.get("/api/system/resources")
async def api_system_resources():
    """Get CPU, memory, disk usage."""
    try:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage(str(WORKSPACE_ROOT))

        return JSONResponse(content={
            "available": True,
            "cpu": {"percent": cpu, "cores": psutil.cpu_count()},
            "memory": {
                "percent": mem.percent,
                "used_gb": round(mem.used / (1024**3), 1),
                "total_gb": round(mem.total / (1024**3), 1)
            },
            "disk": {
                "percent": round((disk.used / disk.total) * 100, 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "total_gb": round(disk.total / (1024**3), 1)
            }
        })
    except ImportError:
        return JSONResponse(content={"available": False, "error": "psutil not installed"})
    except Exception as e:
        return JSONResponse(content={"available": False, "error": str(e)})

@app.get("/api/system/ollama")
async def api_system_ollama():
    """Get Ollama service and loaded models."""
    result = {"available": False, "models": [], "loaded": []}

    # Check if Ollama is running
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        if req.status == 200:
            result["available"] = True
    except Exception:
        return JSONResponse(content=result)

    # Get installed models
    try:
        proc = subprocess.run(["ollama", "list"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            lines = proc.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if parts:
                    result["models"].append({"name": parts[0], "size": parts[1] if len(parts) > 1 else ""})
    except Exception:
        pass

    # Get loaded/running models
    try:
        proc = subprocess.run(["ollama", "ps"], capture_output=True, text=True, timeout=5)
        if proc.returncode == 0:
            lines = proc.stdout.strip().split("\n")[1:]  # Skip header
            for line in lines:
                parts = line.split()
                if parts:
                    result["loaded"].append({"name": parts[0], "vram": parts[2] if len(parts) > 2 else ""})
    except Exception:
        pass

    return JSONResponse(content=result)

@app.get("/api/services")
async def api_services():
    """Get all service statuses."""
    services = []

    # Dashboard (always online if we're responding)
    services.append({"id": "dashboard", "name": "Dashboard", "online": True, "port": 8080})

    # Orchestrator
    try:
        from slate.slate_orchestrator import SlateOrchestrator
        orch = SlateOrchestrator()
        status = orch.status()
        services.append({"id": "orch", "name": "Orchestrator", "online": status.get("orchestrator", {}).get("running", False)})
    except Exception:
        services.append({"id": "orch", "name": "Orchestrator", "online": False})

    # GitHub Runner
    try:
        from slate.slate_runner_manager import SlateRunnerManager
        mgr = SlateRunnerManager()
        detection = mgr.detect()
        services.append({"id": "runner", "name": "GitHub Runner", "online": detection.get("runner_installed", False)})
    except Exception:
        services.append({"id": "runner", "name": "GitHub Runner", "online": False})

    # Ollama
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        services.append({"id": "ollama", "name": "Ollama", "online": req.status == 200, "port": 11434})
    except Exception:
        services.append({"id": "ollama", "name": "Ollama", "online": False, "port": 11434})

    # Foundry Local
    try:
        import urllib.request
        req = urllib.request.urlopen("http://127.0.0.1:5272/health", timeout=2)
        services.append({"id": "foundry", "name": "Foundry Local", "online": req.status == 200, "port": 5272})
    except Exception:
        services.append({"id": "foundry", "name": "Foundry Local", "online": False, "port": 5272})

    return JSONResponse(content={"services": services})

# ─── Activity Feed ───────────────────────────────────────────────────────────

# In-memory activity feed
ACTIVITY_FEED: List[Dict[str, Any]] = []
MAX_ACTIVITY_EVENTS = 50

def add_activity_event(event_type: str, message: str, details: Dict[str, Any] = None):
    """Add event to activity feed."""
    event = {
        "id": str(uuid.uuid4())[:8],
        "type": event_type,
        "message": message,
        "details": details or {},
        "timestamp": datetime.now(timezone.utc).isoformat()
    }
    ACTIVITY_FEED.insert(0, event)
    if len(ACTIVITY_FEED) > MAX_ACTIVITY_EVENTS:
        ACTIVITY_FEED.pop()
    return event

@app.get("/api/activity")
async def api_activity():
    """Get recent activity events."""
    return JSONResponse(content={"events": ACTIVITY_FEED[:20]})

@app.get("/api/task-activity")
async def api_task_activity():
    """Get task activity data for heatmap visualization.

    Returns aggregated task counts per day for the last 365 days,
    including success/failure breakdown for objective feedback.
    """
    from datetime import timedelta

    try:
        tasks = load_tasks()

        # Initialize activity data for last 365 days
        today = datetime.now(timezone.utc).date()
        activity = {}
        for i in range(365):
            date = today - timedelta(days=i)
            activity[date.isoformat()] = {"total": 0, "completed": 0, "failed": 0}

        # Count tasks by creation/completion date
        total_tasks = 0
        total_completed = 0
        total_failed = 0

        for task in tasks:
            # Use created_at or updated_at date
            task_date = None
            if task.get("created_at"):
                try:
                    dt = datetime.fromisoformat(task["created_at"].replace("Z", "+00:00"))
                    task_date = dt.date().isoformat()
                except Exception:
                    pass

            if task_date and task_date in activity:
                activity[task_date]["total"] += 1
                total_tasks += 1

                status = task.get("status", "pending")
                if status == "completed":
                    activity[task_date]["completed"] += 1
                    total_completed += 1
                elif status in ("failed", "error"):
                    activity[task_date]["failed"] += 1
                    total_failed += 1

        # Also count workflow runs from GitHub for a more complete picture
        try:
            gh_cli = get_gh_cli()
            result = subprocess.run(
                [gh_cli, "run", "list", "--limit", "100", "--json", "conclusion,createdAt"],
                capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
            )
            if result.returncode == 0 and result.stdout.strip():
                runs = json.loads(result.stdout)
                for run in runs:
                    try:
                        run_date = datetime.fromisoformat(
                            run["createdAt"].replace("Z", "+00:00")
                        ).date().isoformat()
                        if run_date in activity:
                            activity[run_date]["total"] += 1
                            total_tasks += 1
                            if run.get("conclusion") == "success":
                                activity[run_date]["completed"] += 1
                                total_completed += 1
                            elif run.get("conclusion") == "failure":
                                activity[run_date]["failed"] += 1
                                total_failed += 1
                    except Exception:
                        pass
        except Exception:
            pass

        # Calculate current streak (consecutive days with activity)
        streak = 0
        for i in range(365):
            date = (today - timedelta(days=i)).isoformat()
            if activity.get(date, {}).get("total", 0) > 0:
                streak += 1
            else:
                break

        return JSONResponse(content={
            "activity": activity,
            "stats": {
                "total": total_tasks,
                "completed": total_completed,
                "failed": total_failed,
                "streak": streak
            }
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "activity": {}, "stats": {}})

# ─── Task Management Endpoints ────────────────────────────────────────────────

@app.get("/api/tasks")
async def api_tasks():
    """Get all tasks."""
    tasks = load_tasks()

    # Calculate stats
    stats = {"total": len(tasks), "pending": 0, "in_progress": 0, "completed": 0}
    for t in tasks:
        status = t.get("status", "pending")
        if status in stats:
            stats[status] += 1

    return JSONResponse(content={"tasks": tasks, "stats": stats})

@app.post("/api/tasks")
async def create_task(request: Request):
    """Create a new task."""
    try:
        data = await request.json()
        tasks = load_tasks()

        new_task = {
            "id": str(uuid.uuid4())[:8],
            "title": data.get("title", "Untitled Task"),
            "description": data.get("description", ""),
            "status": "pending",
            "priority": data.get("priority", 3),
            "assigned_to": data.get("assigned_to", "auto"),
            "created_at": datetime.now(timezone.utc).isoformat(),
            "created_by": "dashboard"
        }

        tasks.append(new_task)
        save_tasks(tasks)

        # Broadcast update
        await manager.broadcast({"type": "task_created", "task": new_task})

        return JSONResponse(content=new_task, status_code=201)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.put("/api/tasks/{task_id}")
async def update_task(task_id: str, request: Request):
    """Update a task."""
    try:
        data = await request.json()
        tasks = load_tasks()

        for task in tasks:
            if task.get("id") == task_id:
                task.update(data)
                task["updated_at"] = datetime.now(timezone.utc).isoformat()
                save_tasks(tasks)
                await manager.broadcast({"type": "task_updated", "task": task})
                return JSONResponse(content=task)

        raise HTTPException(status_code=404, detail="Task not found")
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@app.delete("/api/tasks/{task_id}")
async def delete_task(task_id: str):
    """Delete a task."""
    tasks = load_tasks()
    original_len = len(tasks)
    tasks = [t for t in tasks if t.get("id") != task_id]

    if len(tasks) == original_len:
        raise HTTPException(status_code=404, detail="Task not found")

    save_tasks(tasks)
    await manager.broadcast({"type": "task_deleted", "task_id": task_id})
    return JSONResponse(content={"deleted": task_id})

# ─── Workflow Dispatch ────────────────────────────────────────────────────────

@app.post("/api/dispatch/{workflow_name}")
async def dispatch_workflow(workflow_name: str, request: Request):
    """Dispatch a GitHub workflow."""
    try:
        gh_cli = get_gh_cli()

        # Get optional inputs
        try:
            inputs = await request.json()
        except Exception:
            inputs = {}

        cmd = [gh_cli, "workflow", "run", workflow_name]
        for key, value in inputs.items():
            cmd.extend(["-f", f"{key}={value}"])

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30, cwd=str(WORKSPACE_ROOT))

        if result.returncode == 0:
            await manager.broadcast({"type": "workflow_dispatched", "workflow": workflow_name})
            return JSONResponse(content={"success": True, "workflow": workflow_name})
        return JSONResponse(content={"success": False, "error": result.stderr}, status_code=400)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)

# ─── WebSocket ────────────────────────────────────────────────────────────────

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates."""
    await manager.connect(websocket)
    try:
        # Send initial status
        try:
            from slate.slate_orchestrator import SlateOrchestrator
            orch = SlateOrchestrator()
            await websocket.send_json({"type": "status", "data": orch.status()})
        except Exception:
            pass

        while True:
            # Keep connection alive and handle client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)

                if msg.get("type") == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg.get("type") == "refresh":
                    try:
                        from slate.slate_orchestrator import SlateOrchestrator
                        orch = SlateOrchestrator()
                        await websocket.send_json({"type": "status", "data": orch.status()})
                    except Exception:
                        pass
            except asyncio.TimeoutError:
                # Send periodic status update
                try:
                    from slate.slate_orchestrator import SlateOrchestrator
                    orch = SlateOrchestrator()
                    await websocket.send_json({"type": "status", "data": orch.status()})
                except Exception:
                    await websocket.send_json({"type": "ping"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# ─── Dashboard HTML ───────────────────────────────────────────────────────────

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; img-src 'self' data:;">
    <meta http-equiv="X-UA-Compatible" content="IE=edge">
    <title>S.L.A.T.E. Dashboard</title>
    <style>
        :root {
            /* Monochrome Base Palette */
            --bg-dark: #0a0a0a;
            --bg-card: rgba(18, 18, 18, 0.80);
            --bg-card-hover: rgba(28, 28, 28, 0.90);
            --bg-elevated: rgba(38, 38, 38, 0.85);

            /* Border System */
            --border: rgba(255, 255, 255, 0.08);
            --border-hover: rgba(255, 255, 255, 0.15);
            --border-focus: rgba(255, 255, 255, 0.25);

            /* Text Hierarchy */
            --text-primary: #ffffff;
            --text-secondary: #b3b3b3;
            --text-muted: #666666;
            --text-dim: #404040;

            /* Status Colors (CRITICAL - Red/Green only) */
            --status-success: #22c55e;
            --status-error: #ef4444;
            --status-success-bg: rgba(34, 197, 94, 0.12);
            --status-error-bg: rgba(239, 68, 68, 0.12);

            /* Neutral Status (monochrome) */
            --status-pending: #808080;
            --status-active: #ffffff;
            --status-pending-bg: rgba(128, 128, 128, 0.12);
            --status-active-bg: rgba(255, 255, 255, 0.08);

            /* Workflow Pipeline */
            --pipeline-task: #808080;
            --pipeline-runner: #b3b3b3;
            --pipeline-workflow: #ffffff;
            --pipeline-result: #22c55e;

            /* Legacy compatibility */
            --accent-blue: #ffffff;
            --accent-green: #22c55e;
            --accent-yellow: #808080;
            --accent-red: #ef4444;
            --accent-purple: #b3b3b3;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
            background: var(--bg-dark);
            background-image:
                radial-gradient(ellipse at 20% 30%, rgba(255, 255, 255, 0.02) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 70%, rgba(255, 255, 255, 0.015) 0%, transparent 50%);
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.5;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 24px;
        }

        /* Header */
        .header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 32px;
            padding-bottom: 24px;
            border-bottom: 1px solid var(--border);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: 16px;
        }

        .logo-icon {
            width: 48px;
            height: 48px;
            background: linear-gradient(135deg, #ffffff, #666666);
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 24px;
            font-weight: bold;
            font-family: Consolas, monospace;
            color: var(--bg-dark);
        }

        .logo-text h1 {
            font-size: 1.5rem;
            font-weight: 600;
            letter-spacing: -0.02em;
        }

        .logo-text span {
            font-size: 0.75rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }

        .header-status {
            display: flex;
            align-items: center;
            gap: 24px;
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 0.875rem;
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s infinite;
        }

        .status-dot.online { background: var(--status-success); }
        .status-dot.offline { background: var(--status-error); }
        .status-dot.pending { background: var(--status-pending); }
        .status-dot.active { background: var(--status-active); }

        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }

        /* Grid Layout */
        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: 20px;
        }

        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }

        @media (max-width: 1024px) {
            .col-3, .col-4, .col-6, .col-8 { grid-column: span 12; }
        }

        /* Cards */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 20px;
            transition: all 0.2s ease;
        }

        .card:hover {
            background: var(--bg-card-hover);
            border-color: rgba(148, 163, 184, 0.2);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 16px;
        }

        .card-title {
            font-size: 0.875rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .card-action {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 6px 12px;
            border-radius: 6px;
            font-size: 0.75rem;
            cursor: pointer;
            transition: all 0.2s;
        }

        .card-action:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }

        /* Stat Cards */
        .stat-value {
            font-size: 2rem;
            font-weight: 700;
            font-family: Consolas, monospace;
            margin-bottom: 4px;
        }

        .stat-label {
            font-size: 0.875rem;
            color: var(--text-muted);
        }

        .stat-value.green { color: var(--status-success); }
        .stat-value.blue { color: var(--text-primary); }
        .stat-value.yellow { color: var(--text-secondary); }
        .stat-value.red { color: var(--status-error); }

        /* Service Status */
        .service-list {
            display: flex;
            flex-direction: column;
            gap: 12px;
        }

        .service-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 12px 16px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
        }

        .service-name {
            display: flex;
            align-items: center;
            gap: 12px;
            font-weight: 500;
        }

        .service-icon {
            width: 32px;
            height: 32px;
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 14px;
            background: rgba(255, 255, 255, 0.05);
        }

        .badge {
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 600;
        }

        .badge.online { background: var(--status-success-bg); color: var(--status-success); }
        .badge.offline { background: var(--status-error-bg); color: var(--status-error); }
        .badge.pending { background: var(--status-pending-bg); color: var(--status-pending); }
        .badge.busy { background: var(--status-active-bg); color: var(--status-active); border: 1px solid rgba(255,255,255,0.2); }
        .badge.in-progress { background: var(--status-active-bg); color: var(--status-active); border: 1px solid rgba(255,255,255,0.2); }

        /* Task List */
        .task-list {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 400px;
            overflow-y: auto;
        }

        .task-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 3px solid transparent;
        }

        .task-item.pending { border-left-color: var(--status-pending); }
        .task-item.in-progress { border-left-color: var(--status-active); }
        .task-item.completed { border-left-color: var(--status-success); }

        .task-content { flex: 1; }

        .task-title {
            font-weight: 500;
            margin-bottom: 2px;
        }

        .task-meta {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Workflow List */
        .workflow-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .workflow-name {
            font-weight: 500;
            font-size: 0.875rem;
        }

        .workflow-time {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* GPU Info */
        .gpu-card {
            display: flex;
            align-items: center;
            gap: 16px;
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            margin-bottom: 8px;
        }

        .gpu-icon {
            width: 40px;
            height: 40px;
            background: linear-gradient(135deg, #ffffff, #666666);
            border-radius: 8px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 18px;
            color: var(--bg-dark);
        }

        .gpu-info h4 {
            font-size: 0.875rem;
            font-weight: 600;
            margin-bottom: 2px;
        }

        .gpu-info span {
            font-size: 0.75rem;
            color: var(--text-muted);
        }

        /* Buttons */
        .btn {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            border-radius: 8px;
            font-size: 0.875rem;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all 0.2s;
        }

        .btn-primary {
            background: var(--text-primary);
            color: var(--bg-dark);
        }

        .btn-primary:hover {
            background: var(--text-secondary);
        }

        .btn-ghost {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
        }

        .btn-ghost:hover {
            background: rgba(255, 255, 255, 0.05);
        }

        /* Empty State */
        .empty-state {
            text-align: center;
            padding: 40px 20px;
            color: var(--text-muted);
        }

        /* Connection Status */
        #connection-status {
            position: fixed;
            bottom: 20px;
            right: 20px;
            padding: 8px 16px;
            border-radius: 20px;
            font-size: 0.75rem;
            font-weight: 500;
            z-index: 1000;
        }

        #connection-status.connected {
            background: var(--status-success-bg);
            color: var(--status-success);
            border: 1px solid rgba(34, 197, 94, 0.3);
        }

        #connection-status.disconnected {
            background: var(--status-error-bg);
            color: var(--status-error);
            border: 1px solid rgba(239, 68, 68, 0.3);
        }

        /* Scrollbar */
        ::-webkit-scrollbar { width: 6px; }
        ::-webkit-scrollbar-track { background: transparent; }
        ::-webkit-scrollbar-thumb { background: var(--text-muted); border-radius: 3px; }
        ::-webkit-scrollbar-thumb:hover { background: var(--text-secondary); }

        /* Agentic Flow Visualization */
        .agentic-flow {
            display: flex;
            flex-direction: column;
            gap: 24px;
        }

        .flow-pipeline {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: 20px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            overflow-x: auto;
        }

        .flow-stage {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 8px;
            min-width: 100px;
        }

        .flow-stage-icon {
            width: 56px;
            height: 56px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
            font-weight: bold;
            font-family: Consolas, monospace;
            border: 2px solid var(--border);
            transition: all 0.3s ease;
            background: rgba(0, 0, 0, 0.3);
        }

        .flow-stage-icon.task { border-color: var(--status-pending); }
        .flow-stage-icon.agent { border-color: var(--text-primary); }
        .flow-stage-icon.workflow { border-color: var(--text-secondary); }
        .flow-stage-icon.pr { border-color: var(--status-success); }

        .flow-stage-icon.active {
            box-shadow: 0 0 20px rgba(255, 255, 255, 0.2);
            animation: flow-pulse 2s infinite;
        }

        @keyframes flow-pulse {
            0%, 100% { box-shadow: 0 0 20px rgba(255, 255, 255, 0.2); }
            50% { box-shadow: 0 0 30px rgba(255, 255, 255, 0.4); }
        }

        .flow-stage-label {
            font-size: 0.7rem;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .flow-stage-value {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-primary);
            font-family: Consolas, monospace;
        }

        .flow-connector {
            flex: 1;
            height: 2px;
            background: var(--border);
            min-width: 30px;
            position: relative;
        }

        .flow-connector::after {
            content: '';
            position: absolute;
            right: 0;
            top: 50%;
            transform: translateY(-50%);
            border: 4px solid transparent;
            border-left-color: var(--text-muted);
        }

        .flow-connector.active {
            background: linear-gradient(90deg, var(--text-muted), var(--text-primary), var(--text-muted));
        }

        /* Activity Feed */
        .activity-feed {
            display: flex;
            flex-direction: column;
            gap: 8px;
            max-height: 300px;
            overflow-y: auto;
        }

        .activity-item {
            display: flex;
            align-items: flex-start;
            gap: 12px;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 2px solid var(--border);
        }

        .activity-item.workflow { border-left-color: var(--text-secondary); }
        .activity-item.task { border-left-color: var(--status-pending); }
        .activity-item.success { border-left-color: var(--status-success); }
        .activity-item.error { border-left-color: var(--status-error); }

        .activity-icon {
            width: 28px;
            height: 28px;
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: bold;
            background: rgba(255, 255, 255, 0.05);
            flex-shrink: 0;
        }

        .activity-content {
            flex: 1;
            min-width: 0;
        }

        .activity-text {
            font-size: 0.8rem;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .activity-time {
            font-size: 0.65rem;
            color: var(--text-muted);
        }

        /* Task Form */
        .task-form {
            display: flex;
            gap: 8px;
            margin-bottom: 12px;
            padding-bottom: 12px;
            border-bottom: 1px solid var(--border);
        }

        .task-input {
            flex: 1;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 12px;
            color: var(--text-primary);
            font-size: 0.875rem;
            font-family: inherit;
        }

        .task-input:focus {
            outline: none;
            border-color: var(--border-focus);
        }

        .task-input::placeholder {
            color: var(--text-muted);
        }

        .task-select {
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 6px;
            padding: 8px 12px;
            color: var(--text-primary);
            font-size: 0.875rem;
            cursor: pointer;
        }

        .task-item-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s;
        }

        .task-item:hover .task-item-actions {
            opacity: 1;
        }

        .task-action-btn {
            background: transparent;
            border: none;
            color: var(--text-muted);
            cursor: pointer;
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.7rem;
        }

        .task-action-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }

        .task-action-btn.delete:hover {
            color: var(--status-error);
        }

        /* Workflow Expanded */
        .workflow-item-expanded {
            padding: 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 10px;
            margin-bottom: 10px;
            border: 1px solid var(--border);
            cursor: pointer;
            transition: all 0.2s;
        }

        .workflow-item-expanded:hover {
            border-color: var(--border-hover);
        }

        .workflow-item-expanded.expanded {
            background: rgba(0, 0, 0, 0.3);
        }

        .workflow-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
        }

        .workflow-info {
            flex: 1;
        }

        .workflow-jobs {
            display: none;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }

        .workflow-item-expanded.expanded .workflow-jobs {
            display: block;
        }

        .workflow-job {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 8px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin-bottom: 6px;
            font-size: 0.75rem;
        }

        .workflow-job-icon {
            width: 20px;
            height: 20px;
            border-radius: 4px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 10px;
        }

        .workflow-job-icon.success { background: var(--status-success-bg); color: var(--status-success); }
        .workflow-job-icon.failure { background: var(--status-error-bg); color: var(--status-error); }
        .workflow-job-icon.in_progress { background: var(--status-active-bg); color: var(--status-active); }
        .workflow-job-icon.pending { background: var(--status-pending-bg); color: var(--status-pending); }

        .workflow-job-name { flex: 1; color: var(--text-secondary); }
        .workflow-job-duration { color: var(--text-muted); font-family: Consolas, monospace; }

        /* Tech Tree Container */
        .tech-tree-container {
            width: 100%;
            height: 400px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 12px;
            overflow: hidden;
            position: relative;
        }

        .tech-tree-svg {
            width: 100%;
            height: 100%;
        }

        .tech-node {
            cursor: pointer;
        }

        .tech-node circle {
            fill: rgba(0, 0, 0, 0.5);
            stroke: var(--text-muted);
            stroke-width: 2;
            transition: all 0.2s;
        }

        .tech-node.completed circle {
            stroke: var(--status-success);
            fill: var(--status-success-bg);
        }

        .tech-node.in_progress circle {
            stroke: var(--status-active);
            fill: var(--status-active-bg);
        }

        .tech-node.locked circle {
            stroke: var(--text-dim);
            fill: rgba(0, 0, 0, 0.3);
        }

        .tech-node:hover circle {
            stroke-width: 3;
        }

        .tech-node text {
            fill: var(--text-primary);
            font-size: 10px;
            text-anchor: middle;
            pointer-events: none;
        }

        .tech-link {
            stroke: var(--border);
            stroke-width: 1.5;
            fill: none;
        }

        .tech-link.unlocked {
            stroke: var(--text-muted);
        }

        .tech-tooltip {
            position: absolute;
            background: var(--bg-card);
            backdrop-filter: blur(16px);
            border: 1px solid var(--border);
            border-radius: 8px;
            padding: 12px;
            font-size: 0.8rem;
            max-width: 250px;
            pointer-events: none;
            opacity: 0;
            transition: opacity 0.2s;
            z-index: 100;
        }

        .tech-tooltip.visible {
            opacity: 1;
        }

        .tech-tooltip-title {
            font-weight: 600;
            margin-bottom: 4px;
        }

        .tech-tooltip-desc {
            color: var(--text-secondary);
            font-size: 0.75rem;
        }

        .tech-controls {
            position: absolute;
            top: 12px;
            right: 12px;
            display: flex;
            gap: 8px;
        }

        .tech-control-btn {
            background: rgba(0, 0, 0, 0.5);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: 6px 10px;
            border-radius: 6px;
            cursor: pointer;
            font-size: 0.75rem;
        }

        .tech-control-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }

        /* GitHub Integration Grid */
        .github-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 16px;
        }

        @media (max-width: 1200px) {
            .github-grid { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 768px) {
            .github-grid { grid-template-columns: 1fr; }
        }

        .github-section {
            background: rgba(0, 0, 0, 0.25);
            border-radius: 10px;
            padding: 12px;
            max-height: 280px;
            overflow-y: auto;
        }

        .section-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: 10px;
            padding-bottom: 8px;
            border-bottom: 1px solid var(--border);
        }

        .section-title {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }

        .section-count {
            font-size: 0.75rem;
            font-weight: 600;
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.08);
            padding: 2px 8px;
            border-radius: 10px;
            font-family: Consolas, monospace;
        }

        .github-list {
            display: flex;
            flex-direction: column;
            gap: 6px;
        }

        .pr-item, .issue-item, .commit-item {
            display: flex;
            flex-direction: column;
            gap: 2px;
            padding: 8px 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            border-left: 2px solid var(--border);
            font-size: 0.75rem;
        }

        .pr-item { border-left-color: var(--status-success); }
        .issue-item { border-left-color: var(--status-error); }
        .commit-item { border-left-color: var(--text-secondary); }

        .item-title {
            font-weight: 500;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .item-meta {
            font-size: 0.65rem;
            color: var(--text-muted);
        }

        .release-section {
            display: flex;
            flex-direction: column;
            justify-content: center;
        }

        .release-info {
            text-align: center;
            padding: 16px;
        }

        .release-tag {
            font-size: 1.5rem;
            font-weight: 700;
            font-family: Consolas, monospace;
            color: var(--text-primary);
            margin-bottom: 4px;
        }

        .release-name {
            font-size: 0.875rem;
            color: var(--text-secondary);
            margin-bottom: 4px;
        }

        .release-date {
            font-size: 0.7rem;
            color: var(--text-muted);
        }

        /* System Health Section */
        .health-section {
            margin-bottom: 16px;
            padding-bottom: 16px;
            border-bottom: 1px solid var(--border);
        }

        .health-section:last-child {
            margin-bottom: 0;
            padding-bottom: 0;
            border-bottom: none;
        }

        .section-title-sm {
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }

        /* GPU Utilization Cards */
        .gpu-util-card {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            margin-bottom: 8px;
        }

        .gpu-index {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 4px;
            font-size: 0.7rem;
            font-weight: 600;
            font-family: Consolas, monospace;
            color: var(--text-secondary);
        }

        .gpu-details { flex: 1; }

        .gpu-name {
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-primary);
            margin-bottom: 2px;
        }

        .gpu-stats {
            display: flex;
            gap: 12px;
            font-size: 0.65rem;
            color: var(--text-muted);
            font-family: Consolas, monospace;
        }

        .gpu-temp {
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 0.65rem;
            font-weight: 500;
            font-family: Consolas, monospace;
        }

        .gpu-temp.cool { background: var(--status-success-bg); color: var(--status-success); }
        .gpu-temp.warm { background: rgba(255, 200, 100, 0.15); color: #ffc864; }
        .gpu-temp.hot { background: var(--status-error-bg); color: var(--status-error); }

        /* Resource Bars */
        .resource-bars {
            display: flex;
            flex-direction: column;
            gap: 10px;
        }

        .resource-bar {
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .resource-label {
            width: 60px;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-secondary);
        }

        .bar-container {
            flex: 1;
            height: 8px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
            overflow: hidden;
        }

        .bar-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--text-muted), var(--text-primary));
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .bar-fill.high {
            background: linear-gradient(90deg, var(--status-error), #ff8080);
        }

        .resource-value {
            width: 45px;
            font-size: 0.75rem;
            font-family: Consolas, monospace;
            color: var(--text-primary);
            text-align: right;
        }

        /* Ollama Models */
        .ollama-model {
            display: flex;
            align-items: center;
            gap: 10px;
            padding: 8px 10px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
            margin-bottom: 6px;
        }

        .model-status {
            width: 8px;
            height: 8px;
            border-radius: 50%;
        }

        .model-status.loaded { background: var(--status-success); }
        .model-status.available { background: var(--text-muted); }

        .model-name {
            flex: 1;
            font-size: 0.75rem;
            font-weight: 500;
            color: var(--text-primary);
        }

        .model-size {
            font-size: 0.65rem;
            color: var(--text-muted);
            font-family: Consolas, monospace;
        }

        /* Contribution Heatmap (GitHub-style) */
        .heatmap-container {
            padding: 16px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 10px;
        }

        .heatmap-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 12px;
        }

        .heatmap-title {
            font-size: 0.875rem;
            font-weight: 500;
            color: var(--text-primary);
        }

        .heatmap-legend {
            display: flex;
            align-items: center;
            gap: 4px;
            font-size: 0.65rem;
            color: var(--text-muted);
        }

        .legend-label { margin: 0 4px; }

        .heatmap-grid {
            display: grid;
            grid-template-columns: repeat(52, 1fr);
            gap: 3px;
        }

        .heatmap-week {
            display: flex;
            flex-direction: column;
            gap: 3px;
        }

        .heatmap-day {
            width: 10px;
            height: 10px;
            border-radius: 2px;
            background: rgba(255, 255, 255, 0.05);
            transition: all 0.15s ease;
        }

        .heatmap-day:hover {
            transform: scale(1.3);
            outline: 1px solid var(--text-secondary);
        }

        .heatmap-day[data-level="0"] { background: rgba(255, 255, 255, 0.05); }
        .heatmap-day[data-level="1"] { background: rgba(34, 197, 94, 0.25); }
        .heatmap-day[data-level="2"] { background: rgba(34, 197, 94, 0.45); }
        .heatmap-day[data-level="3"] { background: rgba(34, 197, 94, 0.65); }
        .heatmap-day[data-level="4"] { background: rgba(34, 197, 94, 0.85); }

        .heatmap-day.failure { background: rgba(239, 68, 68, 0.6); }

        .heatmap-months {
            display: flex;
            justify-content: space-between;
            margin-top: 6px;
            padding: 0 2px;
        }

        .heatmap-month {
            font-size: 0.6rem;
            color: var(--text-muted);
        }

        .heatmap-stats {
            display: flex;
            gap: 24px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }

        .heatmap-stat {
            text-align: center;
        }

        .heatmap-stat-value {
            font-size: 1.25rem;
            font-weight: 700;
            font-family: Consolas, monospace;
            color: var(--text-primary);
        }

        .heatmap-stat-value.success { color: var(--status-success); }
        .heatmap-stat-value.error { color: var(--status-error); }

        .heatmap-stat-label {
            font-size: 0.65rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        .legend-box {
            width: 10px;
            height: 10px;
            border-radius: 2px;
        }
    </style>
</head>
<body>
    <div class="container">
        <!-- Header -->
        <header class="header">
            <div class="logo">
                <div class="logo-icon">S</div>
                <div class="logo-text">
                    <h1>S.L.A.T.E.</h1>
                    <span>Synchronized Living Architecture</span>
                </div>
            </div>
            <div class="header-status">
                <div class="status-indicator">
                    <span class="status-dot" id="runner-dot"></span>
                    <span id="runner-status-text">Runner: Checking...</span>
                </div>
                <button class="btn btn-ghost" onclick="refreshAll()">Refresh</button>
            </div>
        </header>

        <!-- Main Grid -->
        <div class="grid">
            <!-- Stats Row -->
            <div class="card col-3">
                <div class="stat-value green" id="stat-online">-</div>
                <div class="stat-label">Services Online</div>
            </div>
            <div class="card col-3">
                <div class="stat-value blue" id="stat-tasks">-</div>
                <div class="stat-label">Active Tasks</div>
            </div>
            <div class="card col-3">
                <div class="stat-value yellow" id="stat-pending">-</div>
                <div class="stat-label">Pending</div>
            </div>
            <div class="card col-3">
                <div class="stat-value" id="stat-workflows">-</div>
                <div class="stat-label">Workflows Today</div>
            </div>

            <!-- Workflow Pipeline -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">Workflow Pipeline</span>
                    <button class="card-action" onclick="refreshWorkflowPipeline()">Refresh</button>
                </div>
                <div class="agentic-flow">
                    <!-- Pipeline Visualization -->
                    <div class="flow-pipeline" id="flow-pipeline">
                        <div class="flow-stage">
                            <div class="flow-stage-icon task" id="flow-task">T</div>
                            <div class="flow-stage-label">Tasks</div>
                            <div class="flow-stage-value" id="flow-task-count">0</div>
                        </div>
                        <div class="flow-connector" id="flow-conn-1"></div>
                        <div class="flow-stage">
                            <div class="flow-stage-icon workflow" id="flow-runner">R</div>
                            <div class="flow-stage-label">Runner</div>
                            <div class="flow-stage-value" id="flow-runner-status">Idle</div>
                        </div>
                        <div class="flow-connector" id="flow-conn-2"></div>
                        <div class="flow-stage">
                            <div class="flow-stage-icon workflow" id="flow-workflow">W</div>
                            <div class="flow-stage-label">Workflows</div>
                            <div class="flow-stage-value" id="flow-workflow-count">0</div>
                        </div>
                        <div class="flow-connector" id="flow-conn-3"></div>
                        <div class="flow-stage">
                            <div class="flow-stage-icon pr" id="flow-pr">PR</div>
                            <div class="flow-stage-label">Results</div>
                            <div class="flow-stage-value" id="flow-pr-count">0</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- GitHub Integration Panel -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">GitHub Integration</span>
                    <button class="card-action" onclick="refreshGitHub()">Refresh</button>
                </div>
                <div class="github-grid">
                    <div class="github-section">
                        <div class="section-header">
                            <span class="section-title">Open PRs</span>
                            <span class="section-count" id="pr-count">0</span>
                        </div>
                        <div class="github-list" id="pr-list">
                            <div class="empty-state">Loading PRs...</div>
                        </div>
                    </div>
                    <div class="github-section">
                        <div class="section-header">
                            <span class="section-title">Recent Commits</span>
                        </div>
                        <div class="github-list" id="commit-list">
                            <div class="empty-state">Loading commits...</div>
                        </div>
                    </div>
                    <div class="github-section">
                        <div class="section-header">
                            <span class="section-title">Open Issues</span>
                            <span class="section-count" id="issue-count">0</span>
                        </div>
                        <div class="github-list" id="issue-list">
                            <div class="empty-state">Loading issues...</div>
                        </div>
                    </div>
                    <div class="github-section release-section">
                        <div class="section-header">
                            <span class="section-title">Latest Release</span>
                        </div>
                        <div class="release-info" id="release-info">
                            <div class="empty-state">Loading...</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- System Health -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">System Health</span>
                    <button class="card-action" onclick="refreshSystemHealth()">Refresh</button>
                </div>
                <div class="health-section">
                    <div class="section-title-sm">GPU Utilization</div>
                    <div id="gpu-utilization">
                        <div class="empty-state">Loading GPU info...</div>
                    </div>
                </div>
                <div class="health-section">
                    <div class="section-title-sm">System Resources</div>
                    <div class="resource-bars">
                        <div class="resource-bar">
                            <span class="resource-label">CPU</span>
                            <div class="bar-container"><div class="bar-fill" id="cpu-bar" style="width: 0%"></div></div>
                            <span class="resource-value" id="cpu-value">--%</span>
                        </div>
                        <div class="resource-bar">
                            <span class="resource-label">Memory</span>
                            <div class="bar-container"><div class="bar-fill" id="memory-bar" style="width: 0%"></div></div>
                            <span class="resource-value" id="memory-value">--%</span>
                        </div>
                        <div class="resource-bar">
                            <span class="resource-label">Disk</span>
                            <div class="bar-container"><div class="bar-fill" id="disk-bar" style="width: 0%"></div></div>
                            <span class="resource-value" id="disk-value">--%</span>
                        </div>
                    </div>
                </div>
                <div class="health-section">
                    <div class="section-title-sm">Ollama Models</div>
                    <div id="ollama-status">
                        <div class="empty-state">Loading Ollama...</div>
                    </div>
                </div>
            </div>

            <!-- Services -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Services</span>
                    <button class="card-action" onclick="refreshServices()">Refresh</button>
                </div>
                <div class="service-list" id="services-list">
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">D</div>
                            <span>Dashboard</span>
                        </div>
                        <span class="badge online">Online</span>
                    </div>
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">O</div>
                            <span>Orchestrator</span>
                        </div>
                        <span class="badge pending" id="orch-badge">Checking</span>
                    </div>
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">R</div>
                            <span>GitHub Runner</span>
                        </div>
                        <span class="badge pending" id="runner-badge">Checking</span>
                    </div>
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">A</div>
                            <span>Ollama</span>
                        </div>
                        <span class="badge pending" id="ollama-badge">Checking</span>
                    </div>
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">F</div>
                            <span>Foundry Local</span>
                        </div>
                        <span class="badge pending" id="foundry-badge">Checking</span>
                    </div>
                </div>
            </div>

            <!-- Quick Actions -->
            <div class="card col-4">
                <div class="card-header">
                    <span class="card-title">Quick Actions</span>
                </div>
                <div style="display: flex; flex-direction: column; gap: 8px;">
                    <button class="btn btn-primary" onclick="dispatchWorkflow('ci.yml')">Run CI Pipeline</button>
                    <button class="btn btn-ghost" onclick="dispatchWorkflow('slate.yml')">Run SLATE Checks</button>
                    <button class="btn btn-ghost" onclick="dispatchWorkflow('nightly.yml')">Run Nightly Suite</button>
                </div>
            </div>

            <!-- Task Queue -->
            <div class="card col-8">
                <div class="card-header">
                    <span class="card-title">Task Queue</span>
                    <button class="card-action" onclick="refreshTasks()">Refresh</button>
                </div>
                <div class="task-form">
                    <input type="text" class="task-input" id="new-task-title" placeholder="New task title..." onkeypress="if(event.key==='Enter')createTask()">
                    <select class="task-select" id="new-task-priority">
                        <option value="3">Normal</option>
                        <option value="1">High</option>
                        <option value="5">Low</option>
                    </select>
                    <button class="btn btn-primary" onclick="createTask()">Add</button>
                </div>
                <div class="task-list" id="task-list">
                    <div class="empty-state">Loading tasks...</div>
                </div>
            </div>

            <!-- Recent Workflows -->
            <div class="card col-4">
                <div class="card-header">
                    <span class="card-title">Recent Workflows</span>
                </div>
                <div id="workflow-list">
                    <div class="empty-state">Loading workflows...</div>
                </div>
            </div>

            <!-- Task Activity Heatmap -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">Task Activity</span>
                    <button class="card-action" onclick="refreshHeatmap()">Refresh</button>
                </div>
                <div class="heatmap-container">
                    <div class="heatmap-header">
                        <span class="heatmap-title" id="heatmap-total">0 tasks in the last year</span>
                        <div class="heatmap-legend">
                            <span class="legend-label">Less</span>
                            <div class="legend-box" style="background: rgba(255,255,255,0.05)"></div>
                            <div class="legend-box" style="background: rgba(34,197,94,0.25)"></div>
                            <div class="legend-box" style="background: rgba(34,197,94,0.45)"></div>
                            <div class="legend-box" style="background: rgba(34,197,94,0.65)"></div>
                            <div class="legend-box" style="background: rgba(34,197,94,0.85)"></div>
                            <span class="legend-label">More</span>
                        </div>
                    </div>
                    <div class="heatmap-grid" id="heatmap-grid"></div>
                    <div class="heatmap-months" id="heatmap-months"></div>
                    <div class="heatmap-stats">
                        <div class="heatmap-stat">
                            <div class="heatmap-stat-value" id="heatmap-total-count">0</div>
                            <div class="heatmap-stat-label">Total Tasks</div>
                        </div>
                        <div class="heatmap-stat">
                            <div class="heatmap-stat-value success" id="heatmap-success-count">0</div>
                            <div class="heatmap-stat-label">Completed</div>
                        </div>
                        <div class="heatmap-stat">
                            <div class="heatmap-stat-value error" id="heatmap-failure-count">0</div>
                            <div class="heatmap-stat-label">Failed</div>
                        </div>
                        <div class="heatmap-stat">
                            <div class="heatmap-stat-value" id="heatmap-streak">0</div>
                            <div class="heatmap-stat-label">Current Streak</div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Activity Feed -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Activity Feed</span>
                    <button class="card-action" onclick="refreshActivity()">Refresh</button>
                </div>
                <div class="activity-feed" id="activity-feed">
                    <div class="empty-state">No recent activity</div>
                </div>
            </div>

            <!-- Tech Tree -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Tech Tree</span>
                    <button class="card-action" onclick="refreshTechTree()">Refresh</button>
                </div>
                <div class="tech-tree-container" id="tech-tree-container">
                    <svg class="tech-tree-svg" id="tech-tree-svg"></svg>
                    <div class="tech-tooltip" id="tech-tooltip">
                        <div class="tech-tooltip-title"></div>
                        <div class="tech-tooltip-desc"></div>
                    </div>
                    <div class="tech-controls">
                        <button class="tech-control-btn" onclick="zoomTechTree(1.2)">+</button>
                        <button class="tech-control-btn" onclick="zoomTechTree(0.8)">-</button>
                        <button class="tech-control-btn" onclick="resetTechTree()">Reset</button>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <div id="connection-status" class="disconnected">Connecting...</div>

    <script>
        let ws = null;
        let reconnectAttempts = 0;

        // WebSocket Connection
        function connectWebSocket() {
            ws = new WebSocket(`ws://${window.location.host}/ws`);

            ws.onopen = () => {
                document.getElementById('connection-status').className = 'connected';
                document.getElementById('connection-status').textContent = 'Live';
                reconnectAttempts = 0;
            };

            ws.onmessage = (event) => {
                const msg = JSON.parse(event.data);
                if (msg.type === 'status') {
                    updateStatus(msg.data);
                } else if (msg.type === 'task_created' || msg.type === 'task_updated' || msg.type === 'task_deleted') {
                    refreshTasks();
                } else if (msg.type === 'workflow_dispatched') {
                    refreshWorkflows();
                }
            };

            ws.onclose = () => {
                document.getElementById('connection-status').className = 'disconnected';
                document.getElementById('connection-status').textContent = 'Reconnecting...';
                reconnectAttempts++;
                setTimeout(connectWebSocket, Math.min(1000 * reconnectAttempts, 10000));
            };

            ws.onerror = () => ws.close();
        }

        // Update Functions
        function updateStatus(data) {
            // Orchestrator
            const orchBadge = document.getElementById('orch-badge');
            if (data.orchestrator?.running) {
                orchBadge.className = 'badge online';
                orchBadge.textContent = 'Running';
            } else {
                orchBadge.className = 'badge offline';
                orchBadge.textContent = 'Stopped';
            }

            // Runner
            const runnerBadge = document.getElementById('runner-badge');
            const runnerDot = document.getElementById('runner-dot');
            const runnerText = document.getElementById('runner-status-text');

            if (data.runner?.running) {
                runnerBadge.className = data.runner.busy ? 'badge busy' : 'badge online';
                runnerBadge.textContent = data.runner.busy ? 'Busy' : 'Online';
                runnerDot.className = 'status-dot online';
                runnerText.textContent = 'Runner: Online';
            } else {
                runnerBadge.className = 'badge offline';
                runnerBadge.textContent = data.runner?.status || 'Offline';
                runnerDot.className = 'status-dot offline';
                runnerText.textContent = 'Runner: Offline';
            }

            // Stats
            let online = 1; // Dashboard always online
            if (data.orchestrator?.running) online++;
            if (data.runner?.running) online++;
            document.getElementById('stat-online').textContent = online + '/3';
            document.getElementById('stat-tasks').textContent = data.workflow?.task_count || 0;
            document.getElementById('stat-pending').textContent = data.workflow?.in_progress || 0;
        }

        async function refreshTasks() {
            try {
                const res = await fetch('/api/tasks');
                const data = await res.json();
                const list = document.getElementById('task-list');

                if (data.tasks && data.tasks.length > 0) {
                    list.innerHTML = data.tasks.slice(0, 10).map(t => `
                        <div class="task-item ${t.status || 'pending'}">
                            <div class="task-content">
                                <div class="task-title">${t.title || t.name || 'Untitled'}</div>
                                <div class="task-meta">${t.assigned_to || 'auto'} | ${t.status || 'pending'}</div>
                            </div>
                            <span class="badge ${t.status === 'completed' ? 'online' : t.status === 'in-progress' ? 'busy' : 'pending'}">
                                ${t.status || 'pending'}
                            </span>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state">No tasks in queue</div>';
                }

                document.getElementById('stat-tasks').textContent = data.stats?.total || 0;
                document.getElementById('stat-pending').textContent = data.stats?.in_progress || 0;
            } catch (e) {
                console.error('Failed to fetch tasks:', e);
            }
        }

        async function refreshWorkflows() {
            try {
                const res = await fetch('/api/workflows');
                const data = await res.json();
                const list = document.getElementById('workflow-list');

                if (data.runs && data.runs.length > 0) {
                    list.innerHTML = data.runs.slice(0, 8).map(w => {
                        const status = w.conclusion || w.status;
                        const badgeClass = status === 'success' ? 'online' :
                                          status === 'in_progress' ? 'busy' :
                                          status === 'failure' ? 'offline' : 'pending';
                        const time = new Date(w.createdAt).toLocaleTimeString();
                        return `
                            <div class="workflow-item">
                                <div>
                                    <div class="workflow-name">${w.name}</div>
                                    <div class="workflow-time">${time}</div>
                                </div>
                                <span class="badge ${badgeClass}">${status}</span>
                            </div>
                        `;
                    }).join('');

                    document.getElementById('stat-workflows').textContent = data.runs.length;
                } else {
                    list.innerHTML = '<div class="empty-state">No recent workflows</div>';
                }
            } catch (e) {
                console.error('Failed to fetch workflows:', e);
            }
        }

        async function refreshRunner() {
            try {
                const res = await fetch('/api/runner');
                const data = await res.json();
                const list = document.getElementById('gpu-list');

                if (data.gpu_info?.gpus && data.gpu_info.gpus.length > 0) {
                    list.innerHTML = data.gpu_info.gpus.map(gpu => `
                        <div class="gpu-card">
                            <div class="gpu-icon">G</div>
                            <div class="gpu-info">
                                <h4>${gpu.name}</h4>
                                <span>${gpu.architecture} | ${gpu.memory}</span>
                            </div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state">No GPUs detected</div>';
                }
            } catch (e) {
                console.error('Failed to fetch runner:', e);
            }
        }

        async function dispatchWorkflow(name) {
            try {
                const res = await fetch(`/api/dispatch/${name}`, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    alert(`Workflow ${name} dispatched successfully!`);
                    setTimeout(refreshWorkflows, 2000);
                } else {
                    alert(`Failed to dispatch: ${data.error}`);
                }
            } catch (e) {
                alert(`Error: ${e.message}`);
            }
        }

        // Workflow Pipeline Functions
        async function refreshWorkflowPipeline() {
            try {
                const res = await fetch('/api/workflow-pipeline');
                const data = await res.json();
                const pipeline = data.pipeline || {};

                // Update task count
                document.getElementById('flow-task-count').textContent = pipeline.tasks || 0;
                document.getElementById('flow-task').classList.toggle('active', (pipeline.pending || 0) > 0);
                document.getElementById('flow-conn-1').classList.toggle('active', (pipeline.in_progress || 0) > 0);

                // Update runner status
                const runnerStatus = pipeline.runner_busy ? 'Busy' : (pipeline.runner_online ? 'Ready' : 'Offline');
                document.getElementById('flow-runner-status').textContent = runnerStatus;
                document.getElementById('flow-runner').classList.toggle('active', pipeline.runner_busy);
                document.getElementById('flow-conn-2').classList.toggle('active', pipeline.workflows_running > 0);

                // Update workflow count
                document.getElementById('flow-workflow-count').textContent = pipeline.workflows_running || 0;
                document.getElementById('flow-workflow').classList.toggle('active', (pipeline.workflows_running || 0) > 0);
                document.getElementById('flow-conn-3').classList.toggle('active', (pipeline.workflows_success || 0) > 0);

                // Update results count
                document.getElementById('flow-pr-count').textContent = pipeline.workflows_success || 0;
                document.getElementById('flow-pr').classList.toggle('active', (pipeline.workflows_success || 0) > 0);

            } catch (e) {
                console.error('Failed to refresh workflow pipeline:', e);
            }
        }

        // GitHub Integration Functions
        async function refreshGitHub() {
            refreshPRs();
            refreshCommits();
            refreshIssues();
            refreshRelease();
        }

        async function refreshPRs() {
            try {
                const res = await fetch('/api/github/prs');
                const data = await res.json();
                const list = document.getElementById('pr-list');
                document.getElementById('pr-count').textContent = data.count || 0;

                if (data.prs && data.prs.length > 0) {
                    list.innerHTML = data.prs.slice(0, 5).map(pr => `
                        <div class="pr-item">
                            <div class="item-title">#${pr.number} ${pr.title}</div>
                            <div class="item-meta">${pr.author?.login || 'unknown'} · ${pr.headRefName}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No open PRs</div>';
                }
            } catch (e) {
                console.error('Failed to fetch PRs:', e);
            }
        }

        async function refreshCommits() {
            try {
                const res = await fetch('/api/github/commits');
                const data = await res.json();
                const list = document.getElementById('commit-list');

                if (data.commits && data.commits.length > 0) {
                    list.innerHTML = data.commits.slice(0, 5).map(c => `
                        <div class="commit-item">
                            <div class="item-title">${c.sha?.substring(0, 7)} ${c.message?.split('\\n')[0]?.substring(0, 40)}</div>
                            <div class="item-meta">${c.author || 'unknown'}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No commits</div>';
                }
            } catch (e) {
                console.error('Failed to fetch commits:', e);
            }
        }

        async function refreshIssues() {
            try {
                const res = await fetch('/api/github/issues');
                const data = await res.json();
                const list = document.getElementById('issue-list');
                document.getElementById('issue-count').textContent = data.count || 0;

                if (data.issues && data.issues.length > 0) {
                    list.innerHTML = data.issues.slice(0, 5).map(issue => `
                        <div class="issue-item">
                            <div class="item-title">#${issue.number} ${issue.title}</div>
                            <div class="item-meta">${issue.author?.login || 'unknown'}</div>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No open issues</div>';
                }
            } catch (e) {
                console.error('Failed to fetch issues:', e);
            }
        }

        async function refreshRelease() {
            try {
                const res = await fetch('/api/github/releases');
                const data = await res.json();
                const info = document.getElementById('release-info');

                if (data.release) {
                    const date = new Date(data.release.publishedAt).toLocaleDateString();
                    info.innerHTML = `
                        <div class="release-tag">${data.release.tagName}</div>
                        <div class="release-name">${data.release.name || ''}</div>
                        <div class="release-date">${date}</div>
                    `;
                } else {
                    info.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No releases</div>';
                }
            } catch (e) {
                console.error('Failed to fetch release:', e);
            }
        }

        // System Health Functions
        async function refreshSystemHealth() {
            refreshGPUUtilization();
            refreshSystemResources();
            refreshOllamaStatus();
        }

        async function refreshGPUUtilization() {
            try {
                const res = await fetch('/api/system/gpu');
                const data = await res.json();
                const container = document.getElementById('gpu-utilization');

                if (data.available && data.gpus && data.gpus.length > 0) {
                    container.innerHTML = data.gpus.map(gpu => {
                        const tempClass = gpu.temperature < 60 ? 'cool' : (gpu.temperature < 80 ? 'warm' : 'hot');
                        return `
                            <div class="gpu-util-card">
                                <div class="gpu-index">${gpu.index}</div>
                                <div class="gpu-details">
                                    <div class="gpu-name">${gpu.name}</div>
                                    <div class="gpu-stats">
                                        <span>GPU: ${gpu.gpu_util}%</span>
                                        <span>Mem: ${Math.round(gpu.memory_used/1024)}/${Math.round(gpu.memory_total/1024)}GB</span>
                                    </div>
                                </div>
                                <div class="gpu-temp ${tempClass}">${gpu.temperature}°C</div>
                            </div>
                        `;
                    }).join('');
                } else {
                    container.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No GPU detected</div>';
                }
            } catch (e) {
                console.error('Failed to fetch GPU:', e);
            }
        }

        async function refreshSystemResources() {
            try {
                const res = await fetch('/api/system/resources');
                const data = await res.json();

                if (data.available) {
                    // CPU
                    const cpuBar = document.getElementById('cpu-bar');
                    const cpuVal = document.getElementById('cpu-value');
                    cpuBar.style.width = `${data.cpu.percent}%`;
                    cpuBar.classList.toggle('high', data.cpu.percent > 80);
                    cpuVal.textContent = `${Math.round(data.cpu.percent)}%`;

                    // Memory
                    const memBar = document.getElementById('memory-bar');
                    const memVal = document.getElementById('memory-value');
                    memBar.style.width = `${data.memory.percent}%`;
                    memBar.classList.toggle('high', data.memory.percent > 80);
                    memVal.textContent = `${Math.round(data.memory.percent)}%`;

                    // Disk
                    const diskBar = document.getElementById('disk-bar');
                    const diskVal = document.getElementById('disk-value');
                    diskBar.style.width = `${data.disk.percent}%`;
                    diskBar.classList.toggle('high', data.disk.percent > 80);
                    diskVal.textContent = `${Math.round(data.disk.percent)}%`;
                }
            } catch (e) {
                console.error('Failed to fetch resources:', e);
            }
        }

        async function refreshOllamaStatus() {
            try {
                const res = await fetch('/api/system/ollama');
                const data = await res.json();
                const container = document.getElementById('ollama-status');
                const badge = document.getElementById('ollama-badge');

                if (data.available) {
                    badge.className = 'badge online';
                    badge.textContent = 'Online';

                    if (data.models && data.models.length > 0) {
                        const loadedNames = data.loaded?.map(l => l.name) || [];
                        container.innerHTML = data.models.slice(0, 4).map(m => {
                            const isLoaded = loadedNames.some(n => n.startsWith(m.name));
                            return `
                                <div class="ollama-model">
                                    <div class="model-status ${isLoaded ? 'loaded' : 'available'}"></div>
                                    <span class="model-name">${m.name}</span>
                                    <span class="model-size">${m.size}</span>
                                </div>
                            `;
                        }).join('');
                    } else {
                        container.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No models installed</div>';
                    }
                } else {
                    badge.className = 'badge offline';
                    badge.textContent = 'Offline';
                    container.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">Ollama not running</div>';
                }
            } catch (e) {
                console.error('Failed to fetch Ollama:', e);
            }
        }

        // Services
        async function refreshServices() {
            try {
                const res = await fetch('/api/services');
                const data = await res.json();

                if (data.services) {
                    let online = 0;
                    data.services.forEach(s => {
                        if (s.online) online++;
                        const badge = document.getElementById(`${s.id}-badge`);
                        if (badge) {
                            badge.className = s.online ? 'badge online' : 'badge offline';
                            badge.textContent = s.online ? 'Online' : 'Offline';
                        }
                    });
                    document.getElementById('stat-online').textContent = `${online}/${data.services.length}`;
                }
            } catch (e) {
                console.error('Failed to fetch services:', e);
            }
        }

        // Activity Feed
        async function refreshActivity() {
            try {
                const res = await fetch('/api/activity');
                const data = await res.json();
                const feed = document.getElementById('activity-feed');

                if (data.events && data.events.length > 0) {
                    feed.innerHTML = data.events.slice(0, 10).map(e => {
                        const typeClass = e.type === 'workflow' ? 'workflow' :
                                         e.type === 'task' ? 'task' :
                                         e.type === 'success' ? 'success' :
                                         e.type === 'error' ? 'error' : '';
                        const icon = e.type === 'workflow' ? 'W' :
                                    e.type === 'task' ? 'T' :
                                    e.type === 'success' ? '✓' :
                                    e.type === 'error' ? '!' : '·';
                        const time = new Date(e.timestamp).toLocaleTimeString();
                        return `
                            <div class="activity-item ${typeClass}">
                                <div class="activity-icon">${icon}</div>
                                <div class="activity-content">
                                    <div class="activity-text">${e.message}</div>
                                    <div class="activity-time">${time}</div>
                                </div>
                            </div>
                        `;
                    }).join('');
                } else {
                    feed.innerHTML = '<div class="empty-state">No recent activity</div>';
                }
            } catch (e) {
                console.error('Failed to fetch activity:', e);
            }
        }

        // Contribution Heatmap
        async function refreshHeatmap() {
            try {
                const res = await fetch('/api/task-activity');
                const data = await res.json();
                const grid = document.getElementById('heatmap-grid');
                const monthsContainer = document.getElementById('heatmap-months');

                // Update stats
                const stats = data.stats || {};
                document.getElementById('heatmap-total').textContent = `${stats.total || 0} tasks in the last year`;
                document.getElementById('heatmap-total-count').textContent = stats.total || 0;
                document.getElementById('heatmap-success-count').textContent = stats.completed || 0;
                document.getElementById('heatmap-failure-count').textContent = stats.failed || 0;
                document.getElementById('heatmap-streak').textContent = stats.streak || 0;

                // Build heatmap grid (52 weeks x 7 days)
                const activity = data.activity || {};
                const today = new Date();
                let html = '';
                const months = [];

                for (let week = 51; week >= 0; week--) {
                    html += '<div class="heatmap-week">';
                    for (let day = 0; day < 7; day++) {
                        const date = new Date(today);
                        date.setDate(date.getDate() - (week * 7 + (6 - day)));
                        const dateStr = date.toISOString().split('T')[0];
                        const dayData = activity[dateStr] || { total: 0, failed: 0 };

                        // Determine level (0-4) based on activity
                        let level = 0;
                        if (dayData.total >= 10) level = 4;
                        else if (dayData.total >= 5) level = 3;
                        else if (dayData.total >= 3) level = 2;
                        else if (dayData.total >= 1) level = 1;

                        const hasFailure = dayData.failed > 0;
                        const failClass = hasFailure ? ' failure' : '';
                        const tooltip = `${dateStr}: ${dayData.total} tasks, ${dayData.failed} failed`;

                        html += `<div class="heatmap-day${failClass}" data-level="${level}" title="${tooltip}"></div>`;

                        // Track months for labels
                        if (day === 0 && week % 4 === 0) {
                            months.push(date.toLocaleString('default', { month: 'short' }));
                        }
                    }
                    html += '</div>';
                }

                grid.innerHTML = html;
                monthsContainer.innerHTML = months.map(m => `<span class="heatmap-month">${m}</span>`).join('');

            } catch (e) {
                console.error('Failed to fetch heatmap:', e);
            }
        }

        function refreshAll() {
            refreshTasks();
            refreshWorkflows();
            refreshRunner();
            refreshWorkflowPipeline();
            refreshGitHub();
            refreshSystemHealth();
            refreshServices();
            refreshActivity();
            refreshHeatmap();
            if (ws && ws.readyState === WebSocket.OPEN) {
                ws.send(JSON.stringify({ type: 'refresh' }));
            }
        }

        // Initial status fetch (works even without WebSocket)
        async function fetchInitialStatus() {
            try {
                const res = await fetch('/api/orchestrator');
                const data = await res.json();
                updateStatus(data);
            } catch (e) {
                console.log('Initial status fetch failed, will retry');
            }
        }

        // Initialize - fetch data immediately, then connect WebSocket
        fetchInitialStatus();
        refreshAll();

        // Try WebSocket, but polling will keep working regardless
        try {
            connectWebSocket();
        } catch (e) {
            console.log('WebSocket failed, using polling only');
        }

        // More frequent polling for VSCode webview compatibility (every 10s)
        setInterval(refreshAll, 10000);
    </script>
</body>
</html>
"""

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the SLATE dashboard."""
    return DASHBOARD_HTML

# ─── Main ─────────────────────────────────────────────────────────────────────

def main():
    """Run the dashboard server."""
    print()
    print("=" * 60)
    print("  S.L.A.T.E. Dashboard Server")
    print("=" * 60)
    print()
    print("  URL:      http://127.0.0.1:8080")
    print("  WebSocket: ws://127.0.0.1:8080/ws")
    print()
    print("  Press Ctrl+C to stop")
    print()

    uvicorn.run(
        app,
        host="127.0.0.1",
        port=8080,
        log_level="warning",
        access_log=False
    )


if __name__ == "__main__":
    main()
