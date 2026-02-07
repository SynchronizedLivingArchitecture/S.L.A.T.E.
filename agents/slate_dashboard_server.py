#!/usr/bin/env python3
# ═══════════════════════════════════════════════════════════════════════════════
# CELL: slate_dashboard_server [python]
# Author: Claude | Created: 2026-02-06T23:45:00Z
# Modified: 2026-02-07T05:00:00Z | Author: COPILOT | Change: Mono theme refinement, WCAG AAA accessibility, missing JS functions
# Modified: 2026-02-07T06:00:00Z | Author: COPILOT | Change: Add /reload and /watcher-event endpoints, enhanced WebSocket broadcast
# Modified: 2026-02-07T09:00:00Z | Author: COPILOT | Change: Add /api/slate/* control endpoints for dashboard button interface
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

# Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Replace BaseHTTPMiddleware with pure ASGI middleware to prevent event loop blocking
# Custom headers middleware for VSCode webview compatibility
# NOTE: BaseHTTPMiddleware wraps responses and can block the event loop when
# there are concurrent WebSocket connections. Using raw ASGI middleware instead.
class VSCodeCompatMiddleware:
    """Pure ASGI middleware that adds cache-control headers without blocking."""

    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            # Pass through WebSocket and other non-HTTP connections unchanged
            await self.app(scope, receive, send)
            return

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.append((b"x-content-type-options", b"nosniff"))
                headers.append((b"cache-control", b"no-cache, no-store, must-revalidate"))
                headers.append((b"pragma", b"no-cache"))
                headers.append((b"expires", b"0"))
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_headers)

app.add_middleware(VSCodeCompatMiddleware)

# ─── Interactive Experience API Routers ──────────────────────────────────────
# Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Add interactive learning, dev cycle, and feedback routers

try:
    from slate.interactive_api import create_interactive_router
    from slate.claude_feedback_layer import get_feedback_layer, FeedbackEvent, EventType

    # Mount interactive API router (learning, dev cycle, feedback endpoints)
    interactive_router = create_interactive_router()
    app.include_router(interactive_router)
    print("[+] Interactive Experience API mounted")

    # Register WebSocket broadcast callback with feedback layer
    _feedback_layer = get_feedback_layer()

    async def _broadcast_feedback_event(event: FeedbackEvent):
        """Broadcast feedback events to all connected WebSocket clients."""
        await manager.broadcast({
            "type": "feedback",
            "event_type": event.event_type.value,
            "payload": event.payload,
            "timestamp": event.timestamp,
            "session_id": event.session_id,
        })

    _feedback_layer.register_broadcast_callback(_broadcast_feedback_event)

except ImportError as e:
    print(f"[-] Interactive API not available: {e}")
    _feedback_layer = None

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
def api_status():
    """Get comprehensive system status.

    Uses def (not async def) so FastAPI runs in thread pool, keeping event loop free.
    """
    # Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Use sync def for thread pool execution
    try:
        from slate.slate_status import get_status
        status = get_status()
        return JSONResponse(content=status)
    except Exception as e:
        return JSONResponse(content={"error": str(e), "timestamp": datetime.now(timezone.utc).isoformat()})

@app.get("/api/orchestrator")
def api_orchestrator():
    """Get orchestrator status.

    Uses def (not async def) so FastAPI runs in thread pool, keeping event loop free.
    """
    # Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Use sync def for thread pool execution
    try:
        from slate.slate_orchestrator import SlateOrchestrator
        orch = SlateOrchestrator()
        return JSONResponse(content=orch.status(skip_dashboard_check=True))
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@app.get("/api/runner")
def api_runner():
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

# ─── Theme API Endpoint ───────────────────────────────────────────────────────

@app.get("/api/theme")
async def api_theme_get():
    """Get current theme value."""
    theme_file = WORKSPACE_ROOT / ".slate_identity" / "theme_value.json"
    try:
        if theme_file.exists():
            data = json.loads(theme_file.read_text(encoding="utf-8"))
            return JSONResponse(content={"theme_value": data.get("value", 0.15)})
    except Exception:
        pass
    return JSONResponse(content={"theme_value": 0.15})

@app.post("/api/theme")
async def api_theme_set(request: Request):
    """Set theme value (0=dark, 1=light)."""
    try:
        data = await request.json()
        value = float(data.get("value", 0.15))
        value = max(0.0, min(1.0, value))
        theme_file = WORKSPACE_ROOT / ".slate_identity" / "theme_value.json"
        theme_file.parent.mkdir(parents=True, exist_ok=True)
        theme_file.write_text(json.dumps({"value": value}), encoding="utf-8")
        return JSONResponse(content={"success": True, "theme_value": value})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

# ─── Guided Mode API Endpoints ─────────────────────────────────────────────────

@app.get("/api/guided/status")
async def api_guided_status():
    """Get current guided mode status."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        return JSONResponse(content=executor.get_status())
    except Exception as e:
        return JSONResponse(content={"state": "inactive", "error": str(e)})

@app.post("/api/guided/start")
async def api_guided_start():
    """Start guided mode."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        result = await executor.start()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/guided/execute")
async def api_guided_execute():
    """Execute the current guided step."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        result = await executor.execute_current_step()
        return JSONResponse(content={
            "success": result.success,
            "message": result.message,
            "details": result.details,
            "auto_advance": result.auto_advance,
            "delay_seconds": result.delay_seconds
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/guided/advance")
async def api_guided_advance():
    """Advance to the next guided step."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        result = await executor.advance()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

@app.post("/api/guided/reset")
async def api_guided_reset():
    """Reset guided mode to initial state."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        executor.reset()
        return JSONResponse(content={"success": True, "state": "inactive"})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

@app.get("/api/guided/step")
async def api_guided_step():
    """Get current step information."""
    try:
        from slate.guided_mode import get_executor
        executor = get_executor()
        step_info = executor.get_current_step_info()
        return JSONResponse(content={"step": step_info})
    except Exception as e:
        return JSONResponse(content={"step": None, "error": str(e)})

# ─── Logo Generation API Endpoints ────────────────────────────────────────────

@app.get("/api/logo/generate")
async def api_logo_generate():
    """Generate logo SVG with current theme."""
    try:
        from slate.logo_generator import generate_logo_svg, get_theme
        theme_file = WORKSPACE_ROOT / ".slate_identity" / "theme_value.json"
        theme_name = "default"
        if theme_file.exists():
            data = json.loads(theme_file.read_text(encoding="utf-8"))
            theme_name = "dark" if data.get("value", 0.15) < 0.5 else "light"
        svg = generate_logo_svg(size=64, theme=theme_name, animate=False)
        return JSONResponse(content={"svg": svg, "theme": theme_name})
    except Exception as e:
        return JSONResponse(content={"error": str(e)})

@app.get("/api/logo/presets")
async def api_logo_presets():
    """Get available logo theme presets."""
    try:
        from slate.logo_generator.themes import SLATE_THEMES
        presets = {name: {"primary": t.primary, "name": t.name} for name, t in SLATE_THEMES.items()}
        return JSONResponse(content={"presets": presets})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "presets": {}})

@app.post("/api/logo/custom")
async def api_logo_custom(request: Request):
    """Generate custom logo with specified parameters."""
    try:
        from slate.logo_generator.starburst import StarburstLogo, StarburstConfig
        data = await request.json()
        config = StarburstConfig(
            size=data.get("size", 200),
            ray_count=data.get("rays", 8),
            ray_color=data.get("primary", "#B85A3C"),
            center_fill=data.get("primary", "#B85A3C"),
            letter_color=data.get("onPrimary", "#FFFFFF"),
            center_letter=data.get("letter", "S"),
            animate_pulse=data.get("animate", False)
        )
        logo = StarburstLogo(config)
        svg = logo.generate_svg()
        return JSONResponse(content={"svg": svg, "success": True})
    except Exception as e:
        return JSONResponse(content={"error": str(e), "success": False})

# ─── Design Tokens API Endpoints ──────────────────────────────────────────────

@app.get("/api/design/tokens")
async def api_design_tokens():
    """Get current design tokens."""
    try:
        from slate.design_tokens import get_tokens
        tokens = get_tokens()
        return JSONResponse(content={
            "tokens": {
                "colors": vars(tokens.colors),
                "spacing": vars(tokens.spacing),
                "typography": vars(tokens.typography),
                "radius": vars(tokens.radius),
                "motion": vars(tokens.motion)
            }
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e)})

@app.get("/api/design/css")
async def api_design_css():
    """Get design tokens as CSS variables."""
    try:
        from slate.design_tokens import get_tokens
        tokens = get_tokens()
        css = tokens.to_css_variables()
        return JSONResponse(content={"css": css})
    except Exception as e:
        return JSONResponse(content={"error": str(e)})

# ─── Docker API Endpoints ─────────────────────────────────────────────────────

@app.get("/api/docker/containers")
async def api_docker_containers():
    """Get Docker container list."""
    try:
        result = subprocess.run(
            ["docker", "ps", "-a", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            containers = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        c = json.loads(line)
                        containers.append({
                            "id": c.get("ID", ""),
                            "name": c.get("Names", ""),
                            "image": c.get("Image", ""),
                            "status": c.get("State", ""),
                            "ports": c.get("Ports", ""),
                            "created": c.get("CreatedAt", "")
                        })
                    except json.JSONDecodeError:
                        pass
            return JSONResponse(content={"available": True, "containers": containers})
        return JSONResponse(content={"available": False, "containers": [], "error": "Docker not running"})
    except FileNotFoundError:
        return JSONResponse(content={"available": False, "containers": [], "error": "Docker not installed"})
    except Exception as e:
        return JSONResponse(content={"available": False, "containers": [], "error": str(e)})

@app.get("/api/docker/images")
async def api_docker_images():
    """Get Docker image list."""
    try:
        result = subprocess.run(
            ["docker", "images", "--format", "{{json .}}"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            images = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    try:
                        img = json.loads(line)
                        images.append({
                            "id": img.get("ID", ""),
                            "repository": img.get("Repository", ""),
                            "tag": img.get("Tag", ""),
                            "size": img.get("Size", ""),
                            "created": img.get("CreatedAt", "")
                        })
                    except json.JSONDecodeError:
                        pass
            return JSONResponse(content={"available": True, "images": images})
        return JSONResponse(content={"available": False, "images": []})
    except Exception as e:
        return JSONResponse(content={"available": False, "images": [], "error": str(e)})

@app.post("/api/docker/action")
async def api_docker_action(request: Request):
    """Perform Docker container action (start/stop/restart)."""
    try:
        data = await request.json()
        container = data.get("container")
        action = data.get("action")
        if not container or action not in ["start", "stop", "restart"]:
            return JSONResponse(content={"success": False, "error": "Invalid request"})
        result = subprocess.run(
            ["docker", action, container],
            capture_output=True, text=True, timeout=30
        )
        return JSONResponse(content={
            "success": result.returncode == 0,
            "output": result.stdout,
            "error": result.stderr if result.returncode != 0 else None
        })
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

# ─── Benchmark API Endpoints ──────────────────────────────────────────────────

@app.get("/api/benchmark/history")
async def api_benchmark_history():
    """Get benchmark history."""
    benchmark_file = WORKSPACE_ROOT / ".slate_identity" / "benchmarks.json"
    try:
        if benchmark_file.exists():
            data = json.loads(benchmark_file.read_text(encoding="utf-8"))
            return JSONResponse(content={"available": True, "benchmarks": data.get("history", [])})
    except Exception:
        pass
    return JSONResponse(content={"available": True, "benchmarks": []})

@app.post("/api/benchmark/run")
async def api_benchmark_run():
    """Run GPU benchmark."""
    try:
        # Get GPU info
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,compute_cap,power.draw",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=10
        )
        benchmark_result = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "gpus": [],
            "inference_speed": 0,
            "memory_bandwidth": 0
        }
        if result.returncode == 0 and result.stdout.strip():
            for line in result.stdout.strip().split("\n"):
                parts = [p.strip() for p in line.split(",")]
                if len(parts) >= 4:
                    benchmark_result["gpus"].append({
                        "name": parts[0],
                        "memory_total": int(parts[1]) if parts[1].isdigit() else 0,
                        "compute_cap": parts[2],
                        "power": float(parts[3]) if parts[3].replace(".", "").isdigit() else 0
                    })
        # Estimate inference speed based on GPU capability
        if benchmark_result["gpus"]:
            gpu = benchmark_result["gpus"][0]
            mem = gpu.get("memory_total", 0)
            benchmark_result["inference_speed"] = round(mem * 0.003, 1)  # Rough estimate
            benchmark_result["memory_bandwidth"] = round(mem * 0.028, 1)  # Rough estimate

        # Save to history
        benchmark_file = WORKSPACE_ROOT / ".slate_identity" / "benchmarks.json"
        benchmark_file.parent.mkdir(parents=True, exist_ok=True)
        history = []
        if benchmark_file.exists():
            try:
                history = json.loads(benchmark_file.read_text(encoding="utf-8")).get("history", [])
            except Exception:
                pass
        history.append(benchmark_result)
        history = history[-20:]  # Keep last 20
        benchmark_file.write_text(json.dumps({"history": history}, indent=2), encoding="utf-8")

        return JSONResponse(content={"success": True, "benchmark": benchmark_result})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)})

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

# ─── SLATE Control Panel API ─────────────────────────────────────────────────
# Modified: 2026-02-07T09:00:00Z | Author: COPILOT | Change: Add control endpoints for dashboard buttons

def _run_slate_cmd(script: str, args: str = "", timeout: int = 60) -> Dict[str, Any]:
    """Run a SLATE Python script and return structured result."""
    python = str(WORKSPACE_ROOT / ".venv" / "Scripts" / "python.exe")
    cmd_parts = [python, str(WORKSPACE_ROOT / script)]
    if args:
        cmd_parts.extend(args.split())
    try:
        result = subprocess.run(
            cmd_parts,
            capture_output=True, text=True, timeout=timeout,
            cwd=str(WORKSPACE_ROOT),
            env={**dict(__import__('os').environ),
                 "PYTHONPATH": str(WORKSPACE_ROOT),
                 "PYTHONIOENCODING": "utf-8",
                 "CUDA_VISIBLE_DEVICES": "0,1",
                 "SLATE_WORKSPACE": str(WORKSPACE_ROOT)},
        )
        return {
            "success": result.returncode == 0,
            "output": result.stdout.strip(),
            "error": result.stderr.strip() if result.returncode != 0 else "",
        }
    except subprocess.TimeoutExpired:
        return {"success": False, "output": "", "error": f"Timeout after {timeout}s"}
    except Exception as e:
        return {"success": False, "output": "", "error": str(e)}


@app.post("/api/slate/run-protocol")
async def slate_run_protocol():
    """Run the guided SLATE protocol: status -> runtime -> workflow -> enforce."""
    steps = []
    for label, script, args in [
        ("System Health", "slate/slate_status.py", "--quick"),
        ("Runtime Integrations", "slate/slate_runtime.py", "--check-all"),
        ("Workflow Status", "slate/slate_workflow_manager.py", "--status"),
        ("Enforce Completion", "slate/slate_workflow_manager.py", "--enforce"),
    ]:
        result = _run_slate_cmd(script, args)
        steps.append({"step": label, **result})
    all_ok = all(s["success"] for s in steps)
    await manager.broadcast({"type": "slate_protocol", "status": "ok" if all_ok else "error"})
    return JSONResponse(content={"success": all_ok, "steps": steps})


@app.post("/api/slate/update")
async def slate_update():
    """Update from git and check forks."""
    steps = []
    # Git pull
    try:
        git_result = subprocess.run(
            ["git", "pull", "--ff-only"],
            capture_output=True, text=True, timeout=30, cwd=str(WORKSPACE_ROOT)
        )
        steps.append({"step": "Git Pull", "success": git_result.returncode == 0,
                       "output": git_result.stdout.strip(), "error": git_result.stderr.strip()})
    except Exception as e:
        steps.append({"step": "Git Pull", "success": False, "output": "", "error": str(e)})
    # Fork check
    result = _run_slate_cmd("slate/slate_fork_manager.py", "--status")
    steps.append({"step": "Fork Status", **result})
    # Deps check
    result = _run_slate_cmd("slate/slate_runtime.py", "--check-all")
    steps.append({"step": "Runtime Check", **result})
    all_ok = all(s["success"] for s in steps)
    return JSONResponse(content={"success": all_ok, "steps": steps})


@app.post("/api/slate/debug")
async def slate_debug():
    """Run diagnostics across all systems."""
    steps = []
    for label, script, args in [
        ("System Status", "slate/slate_status.py", "--quick"),
        ("Services", "slate/slate_orchestrator.py", "status"),
        ("GPU Manager", "slate/slate_gpu_manager.py", "--status"),
        ("Workflow", "slate/slate_workflow_manager.py", "--status"),
        ("Runner", "slate/slate_runner_manager.py", "--status"),
    ]:
        result = _run_slate_cmd(script, args)
        steps.append({"step": label, **result})
    errors = [s for s in steps if not s["success"]]
    return JSONResponse(content={"success": len(errors) == 0, "steps": steps, "error_count": len(errors)})


@app.post("/api/slate/security")
async def slate_security():
    """Run full security audit."""
    steps = []
    for label, script, args in [
        ("ActionGuard", "slate/action_guard.py", "--scan"),
        ("PII Scanner", "slate/pii_scanner.py", "--scan"),
        ("SDK Source Guard", "slate/sdk_source_guard.py", "--check"),
    ]:
        result = _run_slate_cmd(script, args)
        steps.append({"step": label, **result})
    all_ok = all(s["success"] for s in steps)
    return JSONResponse(content={"success": all_ok, "steps": steps})


@app.post("/api/slate/deploy/{action}")
async def slate_deploy(action: str):
    """Manage services: start, stop, or status."""
    if action not in ("start", "stop", "status"):
        raise HTTPException(status_code=400, detail="Invalid action. Use: start, stop, status")
    result = _run_slate_cmd("slate/slate_orchestrator.py", action, timeout=30)
    return JSONResponse(content=result)


@app.post("/api/slate/agents")
async def slate_agents():
    """Check agent system status."""
    steps = []
    for label, script, args in [
        ("Unified Autonomous", "slate/slate_unified_autonomous.py", "--status"),
        ("Copilot Runner", "slate/copilot_slate_runner.py", "--status"),
        ("Integrated Loop", "slate/integrated_autonomous_loop.py", "--status"),
    ]:
        result = _run_slate_cmd(script, args)
        steps.append({"step": label, **result})
    return JSONResponse(content={"steps": steps})


@app.post("/api/slate/gpu")
async def slate_gpu():
    """GPU management status."""
    steps = []
    for label, script, args in [
        ("GPU Manager", "slate/slate_gpu_manager.py", "--status"),
        ("Hardware Optimizer", "slate/slate_hardware_optimizer.py", ""),
    ]:
        result = _run_slate_cmd(script, args)
        steps.append({"step": label, **result})
    return JSONResponse(content={"steps": steps})


@app.post("/api/slate/benchmark")
async def slate_benchmark():
    """Run performance benchmarks."""
    result = _run_slate_cmd("slate/slate_benchmark.py", "", timeout=120)
    return JSONResponse(content=result)


# ─── Agentic AI Intelligence Endpoints ────────────────────────────────────────
# Modified: 2026-02-07T10:45:00Z | Author: COPILOT | Change: Add AI-powered control intelligence

@app.get("/api/slate/ai/recommend")
async def slate_ai_recommend():
    """Get AI-powered recommendation for next action based on system state."""
    try:
        from slate.slate_control_intelligence import get_intelligence
        intel = get_intelligence()
        # Collect system state
        state = {
            "gpu_count": 2,
            "pending_tasks": len([t for t in tasks if t.get("status") == "pending"]),
            "runner_online": True,
            "ollama_online": True,
        }
        rec = intel.pre_flight(state)
        order = intel.get_recommended_order()
        stats = intel.get_usage_stats()
        return JSONResponse(content={
            "recommendation": rec or "Run SLATE protocol check to verify system health.",
            "recommended_order": order,
            "usage_stats": stats,
        })
    except Exception as e:
        return JSONResponse(content={"recommendation": None, "error": str(e)})


@app.post("/api/slate/ai/record")
async def slate_ai_record(request: Request):
    """Record a control action for usage pattern learning."""
    try:
        from slate.slate_control_intelligence import get_intelligence
        body = await request.json()
        intel = get_intelligence()
        intel.record_action(
            action=body.get("action", "unknown"),
            success=body.get("success", True),
            duration_ms=body.get("duration_ms", 0),
        )
        return JSONResponse(content={"recorded": True})
    except Exception as e:
        return JSONResponse(content={"recorded": False, "error": str(e)})


@app.post("/api/slate/ai/summarize")
async def slate_ai_summarize(request: Request):
    """Get AI-generated summary of an action result."""
    try:
        from slate.slate_control_intelligence import get_intelligence
        body = await request.json()
        intel = get_intelligence()
        summary = intel.post_action_summary(
            action=body.get("action", ""),
            output=body.get("output", ""),
        )
        return JSONResponse(content={"summary": summary})
    except Exception as e:
        return JSONResponse(content={"summary": None, "error": str(e)})


@app.post("/api/slate/ai/recovery")
async def slate_ai_recovery(request: Request):
    """Get AI-suggested fix for a failed action."""
    try:
        from slate.slate_control_intelligence import get_intelligence
        body = await request.json()
        intel = get_intelligence()
        suggestion = intel.error_recovery(
            action=body.get("action", ""),
            error=body.get("error", ""),
        )
        return JSONResponse(content={"suggestion": suggestion})
    except Exception as e:
        return JSONResponse(content={"suggestion": None, "error": str(e)})


# Modified: 2025-07-21T10:30:00Z | Author: COPILOT | Change: Add background CLI action endpoints
# ─── Background CLI Actions (Copilot Background Mode) ────────────────────────

import threading
_background_actions: list = []
_background_lock = threading.Lock()

@app.post("/api/slate/background/{action}")
async def slate_background_action(action: str):
    """Queue a SLATE action for background execution.

    This is the 'background mode' control layer — Copilot pushes
    commands through this endpoint to run SLATE operations without
    blocking the UI.

    Supported actions: status, update, benchmark, security, agents,
    gpu, autonomous-discover, autonomous-single, workflow-cleanup,
    workflow-enforce, health-check
    """
    import subprocess
    import time

    WORKSPACE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    PYTHON = os.path.join(WORKSPACE, ".venv", "Scripts", "python.exe")

    action_map = {
        "status": ["slate/slate_status.py", "--quick"],
        "runtime": ["slate/slate_runtime.py", "--check-all"],
        "update": ["slate/slate_workflow_manager.py", "--status"],
        "benchmark": ["slate/slate_benchmark.py"],
        "security": ["slate/action_guard.py"],
        "agents": ["slate/slate_unified_autonomous.py", "--status"],
        "gpu": ["slate/slate_hardware_optimizer.py"],
        "autonomous-discover": ["slate/slate_unified_autonomous.py", "--discover"],
        "autonomous-single": ["slate/slate_unified_autonomous.py", "--single"],
        "workflow-cleanup": ["slate/slate_workflow_manager.py", "--cleanup"],
        "workflow-enforce": ["slate/slate_workflow_manager.py", "--enforce"],
        "health-check": ["slate/slate_status.py", "--json"],
    }

    if action not in action_map:
        return JSONResponse(
            status_code=400,
            content={"error": f"Unknown action: {action}", "available": list(action_map.keys())}
        )

    cmd_args = action_map[action]
    action_id = f"{action}-{int(time.time())}"

    entry = {
        "id": action_id,
        "action": action,
        "status": "running",
        "started_at": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "output": None,
        "error": None,
    }

    with _background_lock:
        _background_actions.insert(0, entry)
        if len(_background_actions) > 100:
            _background_actions[:] = _background_actions[:100]

    def run_bg():
        try:
            result = subprocess.run(
                [PYTHON] + cmd_args,
                capture_output=True, text=True, timeout=120,
                cwd=WORKSPACE, encoding="utf-8"
            )
            entry["status"] = "completed" if result.returncode == 0 else "failed"
            entry["output"] = (result.stdout or "")[:2000]
            if result.stderr:
                entry["error"] = result.stderr[:1000]
        except subprocess.TimeoutExpired:
            entry["status"] = "timeout"
            entry["error"] = "Command timed out after 120 seconds"
        except Exception as e:
            entry["status"] = "failed"
            entry["error"] = str(e)
        entry["completed_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ")

    thread = threading.Thread(target=run_bg, daemon=True)
    thread.start()

    return JSONResponse(content={
        "id": action_id,
        "action": action,
        "status": "queued",
        "message": f"Background action '{action}' started"
    })


@app.get("/api/slate/background/history")
async def slate_background_history():
    """Get the history of background actions."""
    with _background_lock:
        return JSONResponse(content={"actions": list(_background_actions)})


@app.get("/api/slate/background/result/{action_id}")
async def slate_background_result(action_id: str):
    """Get the result of a specific background action."""
    with _background_lock:
        for entry in _background_actions:
            if entry["id"] == action_id:
                return JSONResponse(content=entry)
    return JSONResponse(status_code=404, content={"error": "Action not found"})


# ─── Guided Workflow Submission API ───────────────────────────────────────────
# Modified: 2026-02-07T12:00:00Z | Author: CLAUDE | Change: Add guided workflow submission endpoints

@app.get("/api/workflow/guide/status")
async def workflow_guide_status():
    """Get current guided workflow status."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        return JSONResponse(content=engine.get_status())
    except Exception as e:
        return JSONResponse(content={"active": False, "error": str(e)})


@app.post("/api/workflow/guide/start")
async def workflow_guide_start():
    """Start the guided workflow submission process."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = engine.start()
        await manager.broadcast({"type": "guided_workflow_started", "step": result.get("step")})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/category/{category}")
async def workflow_guide_select_category(category: str):
    """Select a job category in the guided workflow."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = engine.select_category(category)
        await manager.broadcast({"type": "guided_workflow_category", "category": category})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/template/{template_id}")
async def workflow_guide_select_template(template_id: str):
    """Select a job template in the guided workflow."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = engine.select_template(template_id)
        await manager.broadcast({"type": "guided_workflow_template", "template": template_id})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/configure")
async def workflow_guide_configure(request: Request):
    """Configure job parameters in the guided workflow."""
    try:
        from slate.guided_workflow import get_engine
        body = await request.json()
        engine = get_engine()
        result = engine.configure_job(body.get("parameters", {}))
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/submit")
async def workflow_guide_submit():
    """Submit the configured job to the workflow pipeline."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = await engine.submit_job()
        if result.get("success"):
            await manager.broadcast({
                "type": "guided_workflow_submitted",
                "job_id": result.get("job_id"),
                "task": result.get("task")
            })
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/workflow/guide/pipeline")
async def workflow_guide_pipeline():
    """Get current pipeline status for submitted job."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = await engine.get_pipeline_status()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/complete")
async def workflow_guide_complete():
    """Complete the guided workflow session."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        result = engine.complete()
        await manager.broadcast({"type": "guided_workflow_complete", "job_id": result.get("job_id")})
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/workflow/guide/reset")
async def workflow_guide_reset():
    """Reset the guided workflow to start over."""
    try:
        from slate.guided_workflow import get_engine
        engine = get_engine()
        engine.reset()
        return JSONResponse(content={"success": True, "reset": True})
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/guide/combined-status")
async def guide_combined_status():
    """Get combined status of setup and workflow guides."""
    try:
        from slate.guided_mode import get_combined_guide_status
        return JSONResponse(content=get_combined_guide_status())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/guide/transition-to-workflow")
async def guide_transition_to_workflow():
    """Transition from setup guide to workflow submission guide."""
    try:
        from slate.guided_mode import transition_to_workflow_guide
        result = await transition_to_workflow_guide()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/job-templates")
async def workflow_templates():
    """Get all available job templates."""
    try:
        from slate.guided_workflow import get_available_templates
        return JSONResponse(content={"templates": get_available_templates()})
    except Exception as e:
        return JSONResponse(content={"templates": [], "error": str(e)})


@app.post("/api/workflow/quick-submit/{template_id}")
async def workflow_quick_submit(template_id: str, request: Request):
    """Quick job submission bypassing guided mode."""
    try:
        from slate.guided_workflow import quick_submit_job
        params = {}
        try:
            body = await request.json()
            params = body.get("parameters", {})
        except Exception:
            pass
        result = await quick_submit_job(template_id, params)
        if result.get("success"):
            await manager.broadcast({
                "type": "job_submitted",
                "job_id": result.get("job_id"),
                "template": template_id
            })
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# ─── Interactive Experience API ───────────────────────────────────────────────
# Modified: 2026-02-07T13:00:00Z | Author: CLAUDE | Change: Add game-like interactive experience

@app.get("/api/experience/status")
async def experience_status():
    """Get current interactive experience status."""
    try:
        from slate.slate_interactive_experience import get_experience
        exp = get_experience()
        return JSONResponse(content=exp.get_status())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/experience/navigate/{node_id}")
async def experience_navigate(node_id: str):
    """Navigate to a specific node in the experience."""
    try:
        from slate.slate_interactive_experience import get_experience
        exp = get_experience()
        result = exp.navigate_to(node_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/experience/select/{option_id}")
async def experience_select_option(option_id: str):
    """Select an option from the current node."""
    try:
        from slate.slate_interactive_experience import get_experience
        exp = get_experience()
        result = exp.select_option(option_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/experience/execute/{action_id}")
async def experience_execute_action(action_id: str):
    """Execute a confirmed action."""
    try:
        from slate.slate_interactive_experience import get_experience
        exp = get_experience()
        result = await exp.execute_action(action_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/experience/learn-more/{option_id}")
async def experience_learn_more(option_id: str):
    """Get expanded information about an option."""
    try:
        from slate.slate_interactive_experience import get_experience
        exp = get_experience()
        result = exp.get_learn_more(option_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/experience/ask")
async def experience_ask_companion(request: Request):
    """Ask the AI companion a question."""
    try:
        from slate.slate_interactive_experience import get_experience
        body = await request.json()
        question = body.get("question", "")
        exp = get_experience()
        result = await exp.ask_companion(question)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# ─── Control Panel API ────────────────────────────────────────────────────────
# Modified: 2026-02-07T14:00:00Z | Author: CLAUDE | Change: Add practical button-driven control panel

@app.get("/api/control-panel/state")
async def control_panel_state():
    """Get complete control panel state."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        return JSONResponse(content=panel.get_panel_state())
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)


@app.post("/api/control-panel/execute/{action_id}")
async def control_panel_execute(action_id: str):
    """Execute a control panel action."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        result = await panel.execute_action(action_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/control-panel/sequence/start/{sequence_id}")
async def control_panel_start_sequence(sequence_id: str):
    """Start a guided sequence."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        result = panel.start_sequence(sequence_id)
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/control-panel/sequence/execute")
async def control_panel_execute_sequence_step():
    """Execute current sequence step."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        result = await panel.execute_sequence_step()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/control-panel/sequence/advance")
async def control_panel_advance_sequence():
    """Advance to next sequence step."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        result = panel.advance_sequence()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.post("/api/control-panel/sequence/cancel")
async def control_panel_cancel_sequence():
    """Cancel current sequence."""
    try:
        from slate.slate_control_panel import get_panel
        panel = get_panel()
        result = panel.cancel_sequence()
        return JSONResponse(content=result)
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


# ─── Dev Hot-Reload Endpoints ─────────────────────────────────────────────────

@app.post("/api/reload")
async def api_reload(request: Request):
    """Trigger a hot-reload of registered modules (dev mode only).

    Called by VS Code extension or manually. Reloads Python agent modules
    via importlib.reload and broadcasts the result to WebSocket clients.

    Body (optional):
        {"module": "agents.runner_api"}  — reload specific module
        {} or no body — reload all registered modules
    """
    try:
        from slate.slate_watcher import DevReloadManager
        from slate.module_registry import get_registry

        # Parse optional module name
        module_name = None
        try:
            body = await request.json()
            module_name = body.get("module")
        except Exception:
            pass

        registry = get_registry()

        # Default agent modules to register if not already
        default_modules = ["agents.runner_api", "agents.install_api"]
        for mod in default_modules:
            registry.register(mod)

        if module_name:
            registry.register(module_name)
            result = registry.reload(module_name, force=True)
            reload_info = {
                "reloaded": [result.module_name],
                "success": result.success,
                "error": result.error,
                "duration_ms": result.duration_ms,
            }
        else:
            results = registry.reload_all(force=True)
            reload_info = {
                "reloaded": [r.module_name for r in results],
                "all_success": all(r.success for r in results),
                "details": [
                    {
                        "module": r.module_name,
                        "success": r.success,
                        "error": r.error,
                        "duration_ms": r.duration_ms,
                    }
                    for r in results
                ],
            }

        # Broadcast to WebSocket clients
        await manager.broadcast({
            "type": "modules_reloaded",
            "data": reload_info,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })

        return JSONResponse(content={"success": True, **reload_info})

    except ImportError:
        return JSONResponse(
            content={"success": False, "error": "Hot-reload not available (watchfiles/module_registry not installed)"},
            status_code=501,
        )
    except Exception as e:
        return JSONResponse(content={"success": False, "error": str(e)}, status_code=500)


@app.get("/api/reload/status")
async def api_reload_status():
    """Get hot-reload registry status and history."""
    try:
        from slate.module_registry import get_registry

        registry = get_registry()
        return JSONResponse(content={
            "available": True,
            "status": registry.status(),
            "history": registry.history[-20:],  # Last 20 reloads
        })
    except ImportError:
        return JSONResponse(content={"available": False, "error": "module_registry not installed"})
    except Exception as e:
        return JSONResponse(content={"available": False, "error": str(e)})


@app.post("/api/watcher-event")
async def api_watcher_event(request: Request):
    """Receive file watcher events from the orchestrator and broadcast via WebSocket.

    This endpoint is called by the orchestrator's file watcher when files change.
    It re-broadcasts the event to all connected WebSocket clients.
    """
    try:
        event = await request.json()
        await manager.broadcast({
            "type": "file_changed",
            "data": event,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        return JSONResponse(content={"ok": True})
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=400)


# ─── SLATE Integration Endpoints ──────────────────────────────────────────────
# Modified: 2026-02-07T08:00:00Z | Author: COPILOT | Change: Add comprehensive system integration endpoints

@app.get("/api/agents")
async def api_agents():
    """Get all registered agents from the kernel-style agent registry."""
    try:
        from slate_core.plugins.agent_registry import AgentRegistry
        registry = AgentRegistry()
        discovered = registry.discover_agents()

        agents = []
        for agent_id in discovered:
            info = registry._agents.get(agent_id)
            if info:
                agents.append({
                    "id": agent_id,
                    "name": info.name,
                    "version": info.version,
                    "description": info.description,
                    "requires_gpu": info.requires_gpu,
                    "state": info.state.value if hasattr(info.state, 'value') else str(info.state),
                    "dependencies": info.dependencies,
                })

        return JSONResponse(content={
            "agents": agents,
            "total": len(agents),
            "gpu_agents": sum(1 for a in agents if a.get("requires_gpu")),
            "cpu_agents": sum(1 for a in agents if not a.get("requires_gpu")),
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "agents": []})


@app.get("/api/forks")
async def api_forks():
    """Get dependency fork status from .dependency-forks/."""
    forks_dir = WORKSPACE_ROOT / ".dependency-forks"
    forks = []

    try:
        if forks_dir.exists():
            for fork_dir in sorted(forks_dir.iterdir()):
                if fork_dir.is_dir() and not fork_dir.name.startswith("."):
                    fork_info = {
                        "name": fork_dir.name,
                        "path": str(fork_dir),
                        "has_git": (fork_dir / ".git").exists(),
                    }

                    # Try to get git info
                    if fork_info["has_git"]:
                        try:
                            result = subprocess.run(
                                ["git", "log", "-1", "--format=%H|%s|%ar"],
                                capture_output=True, text=True, timeout=5,
                                cwd=str(fork_dir)
                            )
                            if result.returncode == 0 and result.stdout.strip():
                                parts = result.stdout.strip().split("|", 2)
                                if len(parts) >= 3:
                                    fork_info["last_commit"] = parts[0][:8]
                                    fork_info["last_message"] = parts[1][:50]
                                    fork_info["last_updated"] = parts[2]
                        except Exception:
                            pass

                        # Get remote URL
                        try:
                            result = subprocess.run(
                                ["git", "remote", "get-url", "origin"],
                                capture_output=True, text=True, timeout=5,
                                cwd=str(fork_dir)
                            )
                            if result.returncode == 0:
                                fork_info["remote"] = result.stdout.strip()
                        except Exception:
                            pass

                    forks.append(fork_info)

        return JSONResponse(content={
            "forks": forks,
            "total": len(forks),
            "forks_dir": str(forks_dir),
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "forks": []})


@app.get("/api/multirunner")
async def api_multirunner():
    """Get multi-runner pool status."""
    try:
        config_file = WORKSPACE_ROOT / ".slate_runners.json"
        if config_file.exists():
            config = json.loads(config_file.read_text(encoding="utf-8"))

            runners = config.get("runners", [])
            running = sum(1 for r in runners if r.get("status") == "running")
            idle = sum(1 for r in runners if r.get("status") == "idle")
            error = sum(1 for r in runners if r.get("status") == "error")

            # GPU distribution
            gpu_dist = {}
            for r in runners:
                gpu = r.get("gpu")
                if gpu is not None:
                    gpu_dist[gpu] = gpu_dist.get(gpu, 0) + 1

            return JSONResponse(content={
                "runners": runners,
                "total": len(runners),
                "running": running,
                "idle": idle,
                "error": error,
                "max_parallel": config.get("max_parallel", 4),
                "gpu_distribution": gpu_dist,
            })
        else:
            return JSONResponse(content={
                "runners": [],
                "total": 0,
                "error": "No multi-runner config found"
            })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "runners": []})


@app.get("/api/workflow-stats")
async def api_workflow_stats():
    """Get comprehensive workflow statistics."""
    try:
        workflows_dir = WORKSPACE_ROOT / ".github" / "workflows"
        workflows = []

        if workflows_dir.exists():
            for wf_file in sorted(workflows_dir.glob("*.yml")):
                wf_info = {
                    "name": wf_file.stem,
                    "file": wf_file.name,
                    "has_concurrency": False,
                    "triggers": [],
                    "jobs": [],
                }

                try:
                    content = wf_file.read_text(encoding="utf-8")

                    # Check for concurrency
                    wf_info["has_concurrency"] = "concurrency:" in content

                    # Extract triggers
                    if "push:" in content:
                        wf_info["triggers"].append("push")
                    if "pull_request:" in content:
                        wf_info["triggers"].append("pull_request")
                    if "schedule:" in content:
                        wf_info["triggers"].append("schedule")
                    if "workflow_dispatch:" in content:
                        wf_info["triggers"].append("manual")

                    # Count jobs - look for job names after "jobs:" section
                    import re
                    jobs_match = re.search(r'^jobs:\s*$', content, re.MULTILINE)
                    if jobs_match:
                        jobs_section = content[jobs_match.end():]
                        # Jobs are at 2-space indent under jobs:
                        jobs = re.findall(r'^\s{2}(\w[\w-]*):\s*$', jobs_section, re.MULTILINE)
                        # Exclude common non-job keys
                        excluded = {'name', 'runs-on', 'needs', 'if', 'env', 'steps', 'timeout-minutes', 'permissions', 'outputs', 'strategy', 'continue-on-error', 'services', 'container', 'defaults'}
                        job_names = [j for j in jobs if j not in excluded]
                        wf_info["jobs"] = job_names[:10]
                        wf_info["job_count"] = len(job_names)

                except Exception:
                    pass

                workflows.append(wf_info)

        # Get recent run stats from GitHub
        run_stats = {"success": 0, "failure": 0, "cancelled": 0, "in_progress": 0}
        try:
            gh_cli = get_gh_cli()
            result = subprocess.run(
                [gh_cli, "run", "list", "--limit", "50", "--json", "conclusion,status"],
                capture_output=True, text=True, timeout=15, cwd=str(WORKSPACE_ROOT)
            )
            if result.returncode == 0 and result.stdout.strip():
                runs = json.loads(result.stdout)
                for run in runs:
                    conclusion = run.get("conclusion") or run.get("status", "")
                    if conclusion == "success":
                        run_stats["success"] += 1
                    elif conclusion == "failure":
                        run_stats["failure"] += 1
                    elif conclusion == "cancelled":
                        run_stats["cancelled"] += 1
                    elif run.get("status") == "in_progress":
                        run_stats["in_progress"] += 1
        except Exception:
            pass

        return JSONResponse(content={
            "workflows": workflows,
            "total": len(workflows),
            "with_concurrency": sum(1 for w in workflows if w.get("has_concurrency")),
            "run_stats": run_stats,
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "workflows": []})


@app.get("/api/modules")
async def api_modules():
    """Get module registry status for hot-reload capable modules."""
    try:
        from slate.module_registry import ModuleRegistry
        registry = ModuleRegistry()
        status = registry.status()

        return JSONResponse(content={
            "modules": status.get("modules", []),
            "total": status.get("registered", 0),
            "reload_history": status.get("reload_history", [])[:10],
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "modules": []})


@app.get("/api/specs")
async def api_specs():
    """Get specification status from specs/ directory."""
    specs_dir = WORKSPACE_ROOT / "specs"
    specs = []

    try:
        if specs_dir.exists():
            for spec_dir in sorted(specs_dir.iterdir()):
                if spec_dir.is_dir() and not spec_dir.name.startswith("."):
                    spec_info = {
                        "id": spec_dir.name,
                        "path": str(spec_dir),
                        "files": [],
                        "status": "unknown",
                    }

                    # Check for common spec files
                    for pattern in ["spec.md", "tasks.md", "README.md", "*.json"]:
                        for f in spec_dir.glob(pattern):
                            spec_info["files"].append(f.name)

                    # Try to determine status from spec.md
                    spec_file = spec_dir / "spec.md"
                    if spec_file.exists():
                        content = spec_file.read_text(encoding="utf-8")[:2000]
                        if "status: complete" in content.lower() or "## complete" in content.lower():
                            spec_info["status"] = "complete"
                        elif "status: implementing" in content.lower() or "## implementing" in content.lower():
                            spec_info["status"] = "implementing"
                        elif "status: planned" in content.lower() or "## planned" in content.lower():
                            spec_info["status"] = "planned"
                        elif "status: draft" in content.lower() or "## draft" in content.lower():
                            spec_info["status"] = "draft"

                    # Check tasks.md for progress
                    tasks_file = spec_dir / "tasks.md"
                    if tasks_file.exists():
                        content = tasks_file.read_text(encoding="utf-8")
                        completed = content.count("[x]") + content.count("[X]")
                        pending = content.count("[ ]")
                        spec_info["tasks_completed"] = completed
                        spec_info["tasks_pending"] = pending
                        spec_info["tasks_total"] = completed + pending

                    specs.append(spec_info)

        return JSONResponse(content={
            "specs": specs,
            "total": len(specs),
            "by_status": {
                "complete": sum(1 for s in specs if s.get("status") == "complete"),
                "implementing": sum(1 for s in specs if s.get("status") == "implementing"),
                "planned": sum(1 for s in specs if s.get("status") == "planned"),
                "draft": sum(1 for s in specs if s.get("status") == "draft"),
            }
        })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "specs": []})


@app.get("/api/tech-tree")
async def api_tech_tree():
    """Get tech tree data from .slate_tech_tree/tech_tree.json."""
    tech_tree_file = WORKSPACE_ROOT / ".slate_tech_tree" / "tech_tree.json"

    try:
        if tech_tree_file.exists():
            import json
            with open(tech_tree_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            nodes = data.get("nodes", [])
            edges = data.get("edges", [])

            # Calculate stats
            by_status = {}
            by_phase = {}
            for node in nodes:
                status = node.get("status", "unknown")
                phase = node.get("phase", 1)
                by_status[status] = by_status.get(status, 0) + 1
                by_phase[phase] = by_phase.get(phase, 0) + 1

            return JSONResponse(content={
                "nodes": nodes,
                "edges": edges,
                "metadata": data.get("metadata", {}),
                "version": data.get("version", "1.0.0"),
                "total": len(nodes),
                "by_status": by_status,
                "by_phase": by_phase,
            })
        else:
            return JSONResponse(content={
                "nodes": [],
                "edges": [],
                "total": 0,
                "error": "tech_tree.json not found"
            })
    except Exception as e:
        return JSONResponse(content={"error": str(e), "nodes": [], "edges": []})


# ─── WebSocket ────────────────────────────────────────────────────────────────

# Modified: 2026-02-07T07:30:00Z | Author: COPILOT | Change: Run blocking status() in thread executor to prevent event loop blocking
async def _get_status_async() -> dict:
    """Get orchestrator status without blocking the async event loop.

    SlateOrchestrator.status() makes synchronous subprocess calls (gh api, tasklist)
    which would block the entire uvicorn event loop if called directly.
    Uses skip_dashboard_check=True since we ARE the dashboard — no self-connection.
    """
    loop = asyncio.get_event_loop()
    try:
        from slate.slate_orchestrator import SlateOrchestrator
        orch = SlateOrchestrator()
        return await loop.run_in_executor(None, lambda: orch.status(skip_dashboard_check=True))
    except Exception:
        return {"error": "status unavailable"}


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates.

    Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Add interactive experience event handling

    Handles message types:
    - ping/pong: Connection keepalive
    - refresh: Request full status update
    - subscribe_interactive: Subscribe to learning/devcycle/feedback events
    - learning_action: Learning panel actions (complete_step, skip, etc.)
    - devcycle_action: Dev cycle actions (transition, add_activity, etc.)
    """
    await manager.connect(websocket)
    subscriptions = set()  # Track client subscriptions

    try:
        # Send initial status (non-blocking)
        try:
            status_data = await _get_status_async()
            await websocket.send_json({"type": "status", "data": status_data})

            # Also send initial interactive status if available
            try:
                from slate.dev_cycle_engine import get_dev_cycle_engine
                from slate.interactive_tutor import get_tutor
                from slate.claude_feedback_layer import get_feedback_layer

                engine = get_dev_cycle_engine()
                tutor = get_tutor()
                layer = get_feedback_layer()

                interactive_status = {
                    "dev_cycle": engine.generate_visualization_data(),
                    "learning": {
                        "progress": tutor.get_progress().to_dict(),
                        "active_path": tutor._current_path,
                    },
                    "feedback": layer.get_metrics(),
                }
                await websocket.send_json({"type": "interactive_status", "data": interactive_status})
            except Exception:
                pass

        except Exception:
            pass

        while True:
            # Keep connection alive and handle client messages
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                msg = json.loads(data)
                msg_type = msg.get("type", "")

                if msg_type == "ping":
                    await websocket.send_json({"type": "pong"})

                elif msg_type == "refresh":
                    try:
                        status_data = await _get_status_async()
                        await websocket.send_json({"type": "status", "data": status_data})
                    except Exception:
                        pass

                elif msg_type == "subscribe_interactive":
                    # Subscribe to interactive events
                    channels = msg.get("channels", ["learning", "devcycle", "feedback"])
                    subscriptions.update(channels)
                    await websocket.send_json({
                        "type": "subscribed",
                        "channels": list(subscriptions),
                    })

                elif msg_type == "refresh_interactive":
                    # Refresh interactive status
                    try:
                        from slate.dev_cycle_engine import get_dev_cycle_engine
                        from slate.interactive_tutor import get_tutor
                        from slate.claude_feedback_layer import get_feedback_layer

                        channel = msg.get("channel", "all")
                        response = {"type": "interactive_refresh"}

                        if channel in ("all", "devcycle"):
                            engine = get_dev_cycle_engine()
                            response["dev_cycle"] = engine.generate_visualization_data()

                        if channel in ("all", "learning"):
                            tutor = get_tutor()
                            step = await tutor.get_next_step()
                            response["learning"] = {
                                "progress": tutor.get_progress().to_dict(),
                                "current_step": step.to_dict() if step else None,
                            }

                        if channel in ("all", "feedback"):
                            layer = get_feedback_layer()
                            events = await layer.get_tool_history(limit=15)
                            response["feedback"] = {
                                "metrics": layer.get_metrics(),
                                "events": [e.to_dict() for e in events],
                            }

                        await websocket.send_json(response)
                    except Exception as e:
                        await websocket.send_json({"type": "error", "message": str(e)})

            except asyncio.TimeoutError:
                # Send periodic status update (non-blocking)
                try:
                    status_data = await _get_status_async()
                    await websocket.send_json({"type": "status", "data": status_data})
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
            /* ═══ SLATE UNIFIED DESIGN SYSTEM v2.0 ═══ */
            /* Synthesizing: M3 Material + Anthropic Geometric + Awwwards Patterns */
            /* Theme Value: 0=dark, 1=light (procedural interpolation) */
            --theme-value: 0.15;

            /* ═══ PRIMARY PALETTE (Anthropic-Inspired Warm) ═══ */
            --slate-primary: #B85A3C;
            --slate-primary-light: #D4785A;
            --slate-primary-dark: #8B4530;
            --slate-primary-container: #FFE4D9;
            --slate-on-primary: #FFFFFF;
            --slate-on-primary-container: #3D1E10;

            /* ═══ SECONDARY PALETTE ═══ */
            --slate-secondary: #5D5D74;
            --slate-secondary-light: #7A7A94;
            --slate-secondary-container: #E2E2F0;
            --slate-on-secondary: #FFFFFF;

            /* ═══ NEUTRAL SURFACES (Natural Earth) ═══ */
            /* Light Mode */
            --slate-surface-light: #FBF8F6;
            --slate-surface-container-light: #F0EBE7;
            --slate-on-surface-light: #1C1B1A;
            --slate-on-surface-variant-light: #4D4845;
            --slate-outline-light: #7D7873;
            --slate-outline-variant-light: #CFC8C3;

            /* Dark Mode */
            --slate-surface-dark: #1A1816;
            --slate-surface-container-dark: #2A2624;
            --slate-on-surface-dark: #E8E2DE;
            --slate-on-surface-variant-dark: #CAC4BF;
            --slate-outline-dark: #968F8A;
            --slate-outline-variant-dark: #4D4845;

            /* ═══ COMPUTED (Interpolated from theme-value) ═══ */
            --dark-bg-primary: #1A1816;
            --dark-bg-surface: #2A2624;
            --dark-bg-card: rgba(42, 38, 36, 0.85);
            --dark-bg-elevated: rgba(52, 48, 46, 0.9);
            --dark-text-primary: #E8E2DE;
            --dark-text-secondary: #CAC4BF;
            --dark-text-muted: #5a6a5a;
            --dark-border: rgba(168, 184, 168, 0.12);
            --dark-accent: #4ade80;

            /* Light Mode Base Colors */
            --light-bg-primary: #f5f7f5;
            --light-bg-surface: #e8ece8;
            --light-bg-card: rgba(255, 255, 255, 0.85);
            --light-bg-elevated: rgba(255, 255, 255, 0.95);
            --light-text-primary: #1a1f1a;
            --light-text-secondary: #4a524a;
            --light-text-muted: #7a827a;
            --light-border: rgba(26, 31, 26, 0.12);
            --light-accent: #16a34a;

            /* Spacing Scale (fluid) */
            --space-xs: clamp(4px, 0.5vw, 8px);
            --space-sm: clamp(8px, 1vw, 12px);
            --space-md: clamp(16px, 2vw, 24px);
            --space-lg: clamp(24px, 3vw, 36px);
            --space-xl: clamp(32px, 4vw, 48px);
            --gutter: clamp(16px, 2vw, 24px);
            --container-pad: clamp(16px, 4vw, 48px);

            /* Typography Scale (fluid clamp) */
            --font-xs: clamp(0.65rem, 0.6rem + 0.25vw, 0.75rem);
            --font-sm: clamp(0.75rem, 0.7rem + 0.25vw, 0.875rem);
            --font-base: clamp(0.875rem, 0.8rem + 0.35vw, 1rem);
            --font-lg: clamp(1rem, 0.9rem + 0.5vw, 1.25rem);
            --font-xl: clamp(1.25rem, 1rem + 1vw, 1.75rem);
            --font-2xl: clamp(1.5rem, 1.2rem + 1.5vw, 2.5rem);
            --font-display: clamp(2rem, 1.5rem + 2.5vw, 4rem);

            /* Border Radius Scale */
            --rounded-sm: 6px;
            --rounded-md: 10px;
            --rounded-lg: 16px;
            --rounded-xl: 24px;
            --rounded-full: 9999px;

            /* Computed Colors (interpolated from theme-value) */
            --bg-dark: var(--dark-bg-primary);
            --bg-surface: var(--dark-bg-surface);
            --bg-card: var(--dark-bg-card);
            --bg-card-hover: rgba(28, 36, 28, 0.92);
            --bg-elevated: var(--dark-bg-elevated);
            --bg-overlay: rgba(10, 15, 10, 0.85);

            /* Border System */
            --border: rgba(255, 255, 255, 0.06);
            --border-hover: rgba(255, 255, 255, 0.12);
            --border-focus: rgba(255, 255, 255, 0.2);
            --border-accent: rgba(255, 255, 255, 0.25);

            /* Text Hierarchy */
            --text-primary: #ffffff;
            --text-secondary: #a3a3a3;
            --text-muted: #525252;
            --text-dim: #333333;

            /* Status Colors (semantic) */
            --status-success: #22c55e;
            --status-error: #ef4444;
            --status-warning: #eab308;
            --status-info: #ffffff;
            --status-success-bg: rgba(34, 197, 94, 0.12);
            --status-error-bg: rgba(239, 68, 68, 0.12);
            --status-warning-bg: rgba(234, 179, 8, 0.12);

            /* Neutral Status (monochrome) */
            --status-pending: #737373;
            --status-active: #ffffff;
            --status-pending-bg: rgba(115, 115, 115, 0.15);
            --status-active-bg: rgba(255, 255, 255, 0.08);

            /* Workflow Pipeline */
            --pipeline-task: #737373;
            --pipeline-runner: #a3a3a3;
            --pipeline-workflow: #ffffff;
            --pipeline-result: #22c55e;

            /* Shadows (layered depth) */
            --shadow-sm: 0 1px 2px rgba(0,0,0,0.3);
            --shadow-md: 0 4px 12px rgba(0,0,0,0.4), 0 2px 4px rgba(0,0,0,0.2);
            --shadow-lg: 0 8px 32px rgba(0,0,0,0.5), 0 4px 12px rgba(0,0,0,0.3);
            --shadow-glow: 0 0 40px rgba(255,255,255,0.03);

            /* Transitions */
            --transition-fast: 0.15s cubic-bezier(0.4, 0, 0.2, 1);
            --transition-base: 0.25s cubic-bezier(0.4, 0, 0.2, 1);
            --transition-slow: 0.4s cubic-bezier(0.4, 0, 0.2, 1);

            /* Legacy compatibility */
            --accent-blue: #ffffff;
            --accent-green: #22c55e;
            --accent-yellow: #eab308;
            --accent-red: #ef4444;
            --accent-purple: #a3a3a3;
        }

        * { box-sizing: border-box; margin: 0; padding: 0; }

        html {
            scroll-behavior: smooth;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
        }

        body {
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, system-ui, sans-serif;
            background: var(--bg-dark);
            background-image:
                radial-gradient(ellipse at 0% 0%, rgba(255, 255, 255, 0.015) 0%, transparent 50%),
                radial-gradient(ellipse at 100% 100%, rgba(255, 255, 255, 0.01) 0%, transparent 50%),
                linear-gradient(180deg, var(--bg-dark) 0%, var(--bg-surface) 100%);
            background-attachment: fixed;
            color: var(--text-primary);
            min-height: 100vh;
            line-height: 1.6;
            font-size: var(--font-base);
        }

        .container {
            width: min(100% - var(--container-pad) * 2, 1480px);
            margin-inline: auto;
            padding-block: var(--space-lg);
        }

        /* ═══ HEADER (Sticky, Award-Style) ═══ */
        .header {
            position: sticky;
            top: 0;
            z-index: 100;
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: var(--space-lg);
            padding: var(--space-md);
            background: var(--bg-overlay);
            backdrop-filter: blur(20px) saturate(180%);
            border: 1px solid var(--border);
            border-radius: var(--rounded-xl);
            box-shadow: var(--shadow-lg);
        }

        .logo {
            display: flex;
            align-items: center;
            gap: var(--space-md);
        }

        .logo-icon {
            width: clamp(44px, 5vw, 60px);
            height: clamp(44px, 5vw, 60px);
            background: linear-gradient(135deg, var(--slate-primary-container, #FFE4D9) 0%, var(--slate-primary, #B85A3C) 100%);
            border-radius: var(--rounded-lg);
            display: flex;
            align-items: center;
            justify-content: center;
            color: var(--slate-primary, #B85A3C);
            box-shadow: var(--shadow-md), 0 0 20px rgba(184, 90, 60, 0.2);
            transition: transform var(--transition-base), box-shadow var(--transition-base);
            overflow: hidden;
            padding: 4px;
        }

        .logo-icon svg {
            width: 100%;
            height: 100%;
        }

        .logo-icon:hover {
            transform: scale(1.08) rotate(-3deg);
            box-shadow: var(--shadow-lg), 0 0 30px rgba(184, 90, 60, 0.35);
        }

        .logo-text h1 {
            font-size: var(--font-xl);
            font-weight: 700;
            letter-spacing: -0.03em;
            background: linear-gradient(135deg, #fff, #aaa);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .logo-text span {
            display: block;
            font-size: var(--font-xs);
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.15em;
            font-weight: 500;
        }

        .header-status {
            display: flex;
            align-items: center;
            gap: var(--space-md);
        }

        .status-indicator {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            font-size: var(--font-sm);
            padding: var(--space-sm) var(--space-md);
            background: rgba(255,255,255,0.03);
            border-radius: var(--rounded-full);
            border: 1px solid var(--border);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s cubic-bezier(0.4, 0, 0.6, 1) infinite;
        }

        .status-dot.online { background: var(--status-success); box-shadow: 0 0 12px var(--status-success); }
        .status-dot.offline { background: var(--status-error); box-shadow: 0 0 12px var(--status-error); }
        .status-dot.pending { background: var(--status-pending); }
        .status-dot.active { background: var(--status-active); box-shadow: 0 0 12px rgba(255,255,255,0.5); }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.9); }
        }

        /* ═══ GRID LAYOUT (Fluid, Responsive) ═══ */
        .grid {
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: var(--gutter);
        }

        .col-3 { grid-column: span 3; }
        .col-4 { grid-column: span 4; }
        .col-6 { grid-column: span 6; }
        .col-8 { grid-column: span 8; }
        .col-12 { grid-column: span 12; }

        @media (max-width: 1200px) {
            .col-3 { grid-column: span 6; }
            .col-4 { grid-column: span 6; }
        }

        @media (max-width: 768px) {
            .col-3, .col-4, .col-6, .col-8 { grid-column: span 12; }
        }

        /* ═══ CARDS (Award-Winning Style) ═══ */
        .card {
            background: var(--bg-card);
            backdrop-filter: blur(24px) saturate(150%);
            border: 1px solid var(--border);
            border-radius: var(--rounded-xl);
            padding: var(--space-md);
            transition: all var(--transition-base);
            position: relative;
            overflow: hidden;
        }

        .card::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.02) 0%, transparent 50%);
            pointer-events: none;
        }

        .card:hover {
            background: var(--bg-card-hover);
            border-color: var(--border-hover);
            transform: translateY(-2px);
            box-shadow: var(--shadow-lg), var(--shadow-glow);
        }

        .card-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: var(--space-md);
            padding-bottom: var(--space-sm);
            border-bottom: 1px solid var(--border);
        }

        .card-title {
            font-size: var(--font-sm);
            font-weight: 600;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }

        .card-action {
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--rounded-md);
            font-size: var(--font-xs);
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .card-action:hover {
            background: rgba(255, 255, 255, 0.08);
            border-color: var(--border-hover);
            color: var(--text-primary);
            transform: translateY(-1px);
        }

        /* ═══ STAT CARDS ═══ */
        .stat-value {
            font-size: var(--font-2xl);
            font-weight: 700;
            font-family: Consolas, 'Courier New', monospace;
            margin-bottom: var(--space-xs);
            line-height: 1;
        }

        .stat-label {
            font-size: var(--font-sm);
            color: var(--text-muted);
            font-weight: 500;
        }

        .stat-value.green { color: var(--status-success); text-shadow: 0 0 20px rgba(34,197,94,0.3); }
        .stat-value.blue { color: var(--text-primary); }
        .stat-value.yellow { color: var(--status-warning); }
        .stat-value.red { color: var(--status-error); text-shadow: 0 0 20px rgba(239,68,68,0.3); }

        /* ═══ SERVICE STATUS ═══ */
        .service-list {
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }

        .service-item {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--space-sm) var(--space-md);
            background: rgba(0, 0, 0, 0.25);
            border-radius: var(--rounded-md);
            border: 1px solid transparent;
            transition: all var(--transition-fast);
        }

        .service-item:hover {
            background: rgba(255, 255, 255, 0.03);
            border-color: var(--border);
        }

        .service-name {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            font-weight: 500;
            font-size: var(--font-sm);
        }

        .service-icon {
            width: 32px;
            height: 32px;
            border-radius: var(--rounded-sm);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: var(--font-sm);
            font-weight: 600;
            background: linear-gradient(135deg, rgba(255,255,255,0.08), rgba(255,255,255,0.02));
            border: 1px solid var(--border);
        }

        /* ═══ BADGES ═══ */
        .badge {
            padding: var(--space-xs) var(--space-sm);
            border-radius: var(--rounded-full);
            font-size: var(--font-xs);
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.03em;
            transition: all var(--transition-fast);
        }

        .badge.online {
            background: var(--status-success-bg);
            color: var(--status-success);
            box-shadow: 0 0 12px rgba(34,197,94,0.2);
        }
        .badge.offline {
            background: var(--status-error-bg);
            color: var(--status-error);
        }
        .badge.pending {
            background: var(--status-pending-bg);
            color: var(--status-pending);
        }
        .badge.busy, .badge.in-progress {
            background: var(--status-active-bg);
            color: var(--status-active);
            border: 1px solid var(--border-hover);
            animation: badgePulse 2s infinite;
        }

        @keyframes badgePulse {
            0%, 100% { box-shadow: 0 0 0 0 rgba(255,255,255,0.2); }
            50% { box-shadow: 0 0 0 4px rgba(255,255,255,0.05); }
        }

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
            margin-bottom: 4px;
        }

        .tech-tooltip-phase {
            color: var(--text-muted);
            font-size: 0.65rem;
            border-top: 1px solid var(--border);
            padding-top: 4px;
            margin-top: 4px;
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

        /* ═══ THEME SLIDER ═══ */
        .theme-slider-container {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 6px 12px;
            background: rgba(128, 128, 128, 0.1);
            border-radius: var(--rounded-full);
            border: 1px solid var(--border);
        }

        .theme-slider {
            -webkit-appearance: none;
            appearance: none;
            width: 100px;
            height: 6px;
            background: linear-gradient(to right, var(--dark-bg-primary), var(--dark-text-secondary), var(--light-bg-primary));
            border-radius: var(--rounded-full);
            cursor: pointer;
        }

        .theme-slider::-webkit-slider-thumb {
            -webkit-appearance: none;
            appearance: none;
            width: 16px;
            height: 16px;
            background: var(--status-success);
            border-radius: 50%;
            cursor: pointer;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
            transition: transform 0.15s ease;
        }

        .theme-slider::-webkit-slider-thumb:hover {
            transform: scale(1.15);
        }

        .theme-slider::-moz-range-thumb {
            width: 16px;
            height: 16px;
            background: var(--status-success);
            border: none;
            border-radius: 50%;
            cursor: pointer;
        }

        .theme-label {
            font-size: 14px;
            color: var(--text-muted);
        }

        /* ═══ DOCKER PANEL ═══ */
        .docker-grid {
            display: flex;
            flex-direction: column;
            gap: 8px;
        }

        .docker-item {
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 10px 12px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
            border-left: 3px solid var(--text-muted);
            transition: all 0.2s ease;
        }

        .docker-item:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .docker-item.running {
            border-left-color: var(--status-success);
        }

        .docker-item.exited {
            border-left-color: var(--status-error);
        }

        .docker-item.paused {
            border-left-color: var(--status-warning);
        }

        .docker-icon {
            width: 28px;
            height: 28px;
            background: rgba(255, 255, 255, 0.08);
            border-radius: 6px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
        }

        .docker-info {
            flex: 1;
            min-width: 0;
        }

        .docker-name {
            font-size: 0.8rem;
            font-weight: 500;
            color: var(--text-primary);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }

        .docker-ports {
            font-size: 0.65rem;
            color: var(--text-muted);
            font-family: Consolas, monospace;
        }

        .docker-actions {
            display: flex;
            gap: 4px;
            opacity: 0;
            transition: opacity 0.2s;
        }

        .docker-item:hover .docker-actions {
            opacity: 1;
        }

        .docker-action-btn {
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-muted);
            padding: 4px 8px;
            border-radius: 4px;
            font-size: 0.65rem;
            cursor: pointer;
            transition: all 0.15s;
        }

        .docker-action-btn:hover {
            background: rgba(255, 255, 255, 0.1);
            color: var(--text-primary);
        }

        /* ═══ HARDWARE CONTROL PANEL ═══ */
        .hw-grid {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 12px;
        }

        @media (max-width: 768px) {
            .hw-grid { grid-template-columns: 1fr; }
        }

        .hw-card {
            padding: 14px;
            background: rgba(0, 0, 0, 0.25);
            border-radius: 10px;
            border: 1px solid var(--border);
        }

        .hw-card-title {
            font-size: 0.7rem;
            font-weight: 600;
            color: var(--text-muted);
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 10px;
        }

        .hw-meter {
            display: flex;
            align-items: center;
            gap: 10px;
            margin-bottom: 8px;
        }

        .hw-meter-label {
            min-width: 70px;
            font-size: 0.75rem;
            color: var(--text-secondary);
        }

        .hw-meter-bar {
            flex: 1;
            height: 8px;
            background: rgba(0, 0, 0, 0.3);
            border-radius: 4px;
            overflow: hidden;
        }

        .hw-meter-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--status-success), var(--dark-accent));
            border-radius: 4px;
            transition: width 0.3s ease;
        }

        .hw-meter-fill.warning {
            background: linear-gradient(90deg, var(--status-warning), #f59e0b);
        }

        .hw-meter-fill.danger {
            background: linear-gradient(90deg, var(--status-error), #f87171);
        }

        .hw-meter-value {
            min-width: 45px;
            text-align: right;
            font-size: 0.75rem;
            font-family: Consolas, monospace;
            color: var(--text-primary);
        }

        .benchmark-result {
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 8px;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }

        .benchmark-stat {
            text-align: center;
            padding: 8px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 6px;
        }

        .benchmark-stat-value {
            font-size: 1rem;
            font-weight: 700;
            font-family: Consolas, monospace;
            color: var(--text-primary);
        }

        .benchmark-stat-label {
            font-size: 0.6rem;
            color: var(--text-muted);
            text-transform: uppercase;
        }

        /* WCAG AAA: Reduced motion */
        @media (prefers-reduced-motion: reduce) {
            *, *::before, *::after {
                animation-duration: 0.01ms !important;
                animation-iteration-count: 1 !important;
                transition-duration: 0.01ms !important;
            }
        }

        /* Respect system color scheme preference */
        @media (prefers-color-scheme: light) {
            :root {
                --theme-value: 0.75;
                --bg-dark: var(--light-bg-surface);
                --bg-surface: var(--light-bg-surface);
                --bg-card: var(--light-bg-card);
                --bg-card-hover: rgba(255, 255, 255, 0.95);
                --bg-overlay: rgba(245, 247, 245, 0.9);
                --text-primary: var(--light-text-primary);
                --text-secondary: var(--light-text-secondary);
                --text-muted: var(--light-text-muted);
                --border: var(--light-border);
            }
        }

        /* WCAG AAA: Focus visible outlines */
        :focus-visible {
            outline: 2px solid var(--text-primary);
            outline-offset: 2px;
        }

        button:focus-visible, .btn:focus-visible, .card-action:focus-visible,
        input:focus-visible, select:focus-visible {
            outline: 2px solid var(--text-primary);
            outline-offset: 2px;
        }

        /* Skip-to-content link (WCAG AAA) */
        .skip-link {
            position: absolute;
            top: -40px;
            left: 0;
            background: var(--text-primary);
            color: var(--bg-dark);
            padding: 8px 16px;
            z-index: 9999;
            font-weight: 600;
            transition: top 0.2s;
        }

        .skip-link:focus {
            top: 0;
        }

        /* Mono-refined: ensure no stray colors */
        .flow-connector.active {
            background: linear-gradient(90deg, var(--text-dim), var(--text-secondary), var(--text-dim));
            background-size: 200% 100%;
        }

        /* ─── SLATE Control Panel ────────────────────────────────────── */
        .slate-controls {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 12px;
        }
        @media (max-width: 900px) {
            .slate-controls { grid-template-columns: repeat(2, 1fr); }
        }
        @media (max-width: 540px) {
            .slate-controls { grid-template-columns: 1fr; }
        }
        .slate-ctrl-btn {
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: 10px;
            padding: 18px 12px;
            border-radius: 12px;
            background: rgba(255,255,255,0.03);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all 0.25s ease;
            position: relative;
            overflow: hidden;
            font-family: inherit;
            font-size: 0.8rem;
            font-weight: 500;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }
        .slate-ctrl-btn::before {
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(255,255,255,0.06) 0%, transparent 60%);
            opacity: 0;
            transition: opacity 0.25s;
        }
        .slate-ctrl-btn:hover {
            border-color: rgba(255,255,255,0.25);
            background: rgba(255,255,255,0.06);
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(0,0,0,0.3);
        }
        .slate-ctrl-btn:hover::before { opacity: 1; }
        .slate-ctrl-btn:active {
            transform: translateY(0);
            box-shadow: 0 2px 8px rgba(0,0,0,0.3);
        }
        .slate-ctrl-btn.running {
            border-color: var(--accent-green);
            pointer-events: none;
            opacity: 0.7;
        }
        .slate-ctrl-btn.running .ctrl-icon {
            animation: ctrl-spin 1.2s linear infinite;
        }
        .slate-ctrl-btn.success { border-color: var(--accent-green); }
        .slate-ctrl-btn.error { border-color: var(--accent-red); }
        @keyframes ctrl-spin {
            to { transform: rotate(360deg); }
        }
        .ctrl-icon {
            font-size: 1.6rem;
            line-height: 1;
            transition: transform 0.25s;
        }
        .ctrl-label { position: relative; z-index: 1; }
        .ctrl-status {
            position: absolute;
            top: 8px;
            right: 8px;
            width: 7px;
            height: 7px;
            border-radius: 50%;
            background: var(--text-muted);
        }
        .ctrl-status.ok { background: var(--accent-green); box-shadow: 0 0 6px var(--accent-green); }
        .ctrl-status.warn { background: var(--accent-yellow); box-shadow: 0 0 6px var(--accent-yellow); }
        .ctrl-status.err { background: var(--accent-red); box-shadow: 0 0 6px var(--accent-red); }

        /* Control output panel */
        .ctrl-output {
            display: none;
            margin-top: 12px;
            padding: 14px;
            background: rgba(0,0,0,0.4);
            border: 1px solid var(--border);
            border-radius: 8px;
            font-family: 'SF Mono', 'Cascadia Code', 'Consolas', monospace;
            font-size: 0.75rem;
            line-height: 1.5;
            color: var(--text-muted);
            max-height: 300px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }
        .ctrl-output.visible { display: block; }
        .ctrl-output .step-ok { color: var(--accent-green); }
        .ctrl-output .step-err { color: var(--accent-red); }
        .ctrl-output .step-label { color: var(--text-secondary); font-weight: 600; }

        /* Quick Actions sub-row */
        .quick-actions-row {
            display: flex;
            gap: 8px;
            flex-wrap: wrap;
            margin-top: 12px;
            padding-top: 12px;
            border-top: 1px solid var(--border);
        }
        .quick-actions-row .btn {
            flex: 1;
            min-width: 120px;
            justify-content: center;
            font-size: 0.75rem;
            padding: 8px 12px;
        }

        /* ═══════════════════════════════════════════════════════════════════════════ */
        /* ENGINEERING BLUEPRINT THEME v3.0                                            */
        /* Technical schematic-style visualization for system architecture             */
        /* ═══════════════════════════════════════════════════════════════════════════ */

        /* Blueprint Colors */
        :root {
            --blueprint-bg: #0D1B2A;
            --blueprint-grid: rgba(27, 58, 75, 0.5);
            --blueprint-line: #3D5A80;
            --blueprint-accent: #98C1D9;
            --blueprint-node: #E0FBFC;
            --blueprint-text: #EEF0F2;
            --blueprint-glow: rgba(152, 193, 217, 0.3);

            /* Connection status */
            --conn-active: #22C55E;
            --conn-pending: #F59E0B;
            --conn-error: #EF4444;
            --conn-inactive: #6B7280;

            /* Wizard steps */
            --step-active: #3B82F6;
            --step-complete: #22C55E;
            --step-pending: #9CA3AF;
        }

        /* Blueprint Background with Grid */
        .blueprint-mode {
            background: var(--blueprint-bg);
            background-image:
                linear-gradient(var(--blueprint-grid) 1px, transparent 1px),
                linear-gradient(90deg, var(--blueprint-grid) 1px, transparent 1px);
            background-size: 24px 24px;
            background-position: center center;
        }

        /* ═══ SETUP WIZARD / STEPPER ═══ */
        .setup-wizard {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: var(--bg-overlay);
            backdrop-filter: blur(20px);
            z-index: 1000;
            display: none;
            flex-direction: column;
        }

        .setup-wizard.active { display: flex; }

        .wizard-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--space-md) var(--space-lg);
            background: var(--bg-card);
            border-bottom: 1px solid var(--border);
        }

        .wizard-title {
            font-size: var(--font-xl);
            font-weight: 700;
            color: var(--text-primary);
        }

        .wizard-subtitle {
            font-size: var(--font-sm);
            color: var(--text-secondary);
        }

        .wizard-close {
            width: 40px;
            height: 40px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: transparent;
            border: 1px solid var(--border);
            border-radius: var(--rounded-md);
            color: var(--text-secondary);
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .wizard-close:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }

        .wizard-body {
            display: flex;
            flex: 1;
            overflow: hidden;
        }

        /* Stepper Sidebar */
        .wizard-steps {
            width: 280px;
            background: rgba(0, 0, 0, 0.2);
            border-right: 1px solid var(--border);
            padding: var(--space-lg) 0;
        }

        .wizard-step {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            padding: var(--space-md) var(--space-lg);
            cursor: pointer;
            border-left: 3px solid transparent;
            transition: all var(--transition-fast);
        }

        .wizard-step:hover {
            background: rgba(255, 255, 255, 0.03);
        }

        .wizard-step.active {
            background: rgba(59, 130, 246, 0.1);
            border-left-color: var(--step-active);
        }

        .wizard-step.complete {
            border-left-color: var(--step-complete);
        }

        .wizard-step.complete .step-number {
            background: var(--step-complete);
            color: white;
        }

        .wizard-step.complete .step-number::after {
            content: "✓";
        }

        .step-number {
            width: 28px;
            height: 28px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            background: var(--step-pending);
            color: white;
            font-size: var(--font-sm);
            font-weight: 600;
        }

        .wizard-step.active .step-number {
            background: var(--step-active);
            box-shadow: 0 0 12px rgba(59, 130, 246, 0.4);
        }

        .step-info { flex: 1; }

        .step-label {
            font-size: var(--font-sm);
            font-weight: 500;
            color: var(--text-primary);
        }

        .step-description {
            font-size: var(--font-xs);
            color: var(--text-muted);
        }

        /* Wizard Content */
        .wizard-content {
            flex: 1;
            padding: var(--space-xl);
            overflow-y: auto;
        }

        .wizard-footer {
            display: flex;
            justify-content: space-between;
            padding: var(--space-md) var(--space-lg);
            background: var(--bg-card);
            border-top: 1px solid var(--border);
        }

        /* Progress Bar */
        .wizard-progress {
            height: 4px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 2px;
            overflow: hidden;
            margin-bottom: var(--space-md);
        }

        .wizard-progress-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--step-active), var(--step-complete));
            border-radius: 2px;
            transition: width 0.4s ease;
        }

        /* ═══ SYSTEM ARCHITECTURE DIAGRAM ═══ */
        .architecture-diagram {
            position: relative;
            padding: var(--space-lg);
            background: var(--blueprint-bg);
            background-image:
                linear-gradient(var(--blueprint-grid) 1px, transparent 1px),
                linear-gradient(90deg, var(--blueprint-grid) 1px, transparent 1px);
            background-size: 20px 20px;
            border-radius: var(--rounded-lg);
            border: 1px solid var(--blueprint-line);
            min-height: 400px;
            overflow: hidden;
        }

        .arch-title {
            position: absolute;
            top: var(--space-md);
            left: var(--space-md);
            font-size: var(--font-xs);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--blueprint-accent);
            font-weight: 600;
        }

        /* Architecture Nodes */
        .arch-node {
            position: absolute;
            padding: var(--space-md);
            background: rgba(13, 27, 42, 0.95);
            border: 2px solid var(--blueprint-line);
            border-radius: var(--rounded-md);
            min-width: 140px;
            transition: all var(--transition-fast);
        }

        .arch-node:hover {
            border-color: var(--blueprint-accent);
            box-shadow: 0 0 20px var(--blueprint-glow);
            transform: scale(1.02);
        }

        .arch-node.active {
            border-color: var(--conn-active);
            box-shadow: 0 0 20px rgba(34, 197, 94, 0.3);
        }

        .arch-node.error {
            border-color: var(--conn-error);
            box-shadow: 0 0 20px rgba(239, 68, 68, 0.3);
        }

        .arch-node-header {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            margin-bottom: var(--space-sm);
        }

        .arch-node-icon {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(152, 193, 217, 0.2);
            border-radius: var(--rounded-sm);
            font-size: var(--font-xs);
        }

        .arch-node-name {
            font-size: var(--font-sm);
            font-weight: 600;
            color: var(--blueprint-text);
        }

        .arch-node-status {
            display: flex;
            align-items: center;
            gap: var(--space-xs);
            font-size: var(--font-xs);
            color: var(--text-muted);
        }

        .arch-status-dot {
            width: 6px;
            height: 6px;
            border-radius: 50%;
        }

        .arch-status-dot.active { background: var(--conn-active); }
        .arch-status-dot.pending { background: var(--conn-pending); animation: pulse 1.5s infinite; }
        .arch-status-dot.error { background: var(--conn-error); }
        .arch-status-dot.inactive { background: var(--conn-inactive); }

        /* Connection Lines (SVG-based) */
        .arch-connections {
            position: absolute;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
        }

        .arch-connection {
            stroke: var(--blueprint-line);
            stroke-width: 2;
            fill: none;
            stroke-linecap: round;
        }

        .arch-connection.active {
            stroke: var(--conn-active);
            filter: drop-shadow(0 0 4px var(--conn-active));
        }

        .arch-connection.data-flow {
            stroke-dasharray: 8 4;
            animation: flow 1s linear infinite;
        }

        @keyframes flow {
            to { stroke-dashoffset: -12; }
        }

        /* ═══ COPILOT GUIDANCE PANEL ═══ */
        .copilot-guide {
            position: fixed;
            bottom: var(--space-lg);
            right: var(--space-lg);
            width: 360px;
            max-height: 480px;
            background: var(--bg-card);
            backdrop-filter: blur(24px);
            border: 1px solid var(--border);
            border-radius: var(--rounded-xl);
            box-shadow: var(--shadow-lg);
            display: none;
            flex-direction: column;
            overflow: hidden;
            z-index: 200;
        }

        .copilot-guide.active { display: flex; }

        .copilot-header {
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--space-md);
            background: linear-gradient(135deg, rgba(184, 90, 60, 0.2), rgba(184, 90, 60, 0.05));
            border-bottom: 1px solid var(--border);
        }

        .copilot-title {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            font-weight: 600;
            color: var(--text-primary);
        }

        .copilot-icon {
            width: 24px;
            height: 24px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--slate-primary);
            border-radius: var(--rounded-sm);
            color: white;
            font-size: var(--font-xs);
        }

        .copilot-body {
            flex: 1;
            padding: var(--space-md);
            overflow-y: auto;
        }

        .copilot-message {
            padding: var(--space-md);
            background: rgba(255, 255, 255, 0.03);
            border-radius: var(--rounded-md);
            border-left: 3px solid var(--slate-primary);
            margin-bottom: var(--space-md);
        }

        .copilot-message-title {
            font-size: var(--font-sm);
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .copilot-message-text {
            font-size: var(--font-sm);
            color: var(--text-secondary);
            line-height: 1.5;
        }

        .copilot-suggestions {
            display: flex;
            flex-direction: column;
            gap: var(--space-sm);
        }

        .copilot-suggestion {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            background: rgba(255, 255, 255, 0.03);
            border: 1px solid var(--border);
            border-radius: var(--rounded-md);
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .copilot-suggestion:hover {
            background: rgba(255, 255, 255, 0.06);
            border-color: var(--border-hover);
        }

        .copilot-suggestion-icon {
            width: 20px;
            height: 20px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(34, 197, 94, 0.2);
            border-radius: var(--rounded-sm);
            font-size: var(--font-xs);
            color: var(--status-success);
        }

        .copilot-suggestion-text {
            flex: 1;
            font-size: var(--font-sm);
            color: var(--text-primary);
        }

        /* Copilot Toggle Button */
        .copilot-toggle {
            position: fixed;
            bottom: var(--space-lg);
            right: var(--space-lg);
            width: 56px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--slate-primary);
            border: none;
            border-radius: 50%;
            color: white;
            cursor: pointer;
            box-shadow: var(--shadow-lg), 0 0 20px rgba(184, 90, 60, 0.3);
            transition: all var(--transition-fast);
            z-index: 199;
        }

        .copilot-toggle:hover {
            transform: scale(1.1);
            box-shadow: var(--shadow-lg), 0 0 30px rgba(184, 90, 60, 0.5);
        }

        .copilot-toggle.hidden { display: none; }

        /* ═══ PRODUCT ONBOARDING HERO ═══ */
        .onboarding-hero {
            text-align: center;
            padding: var(--space-xl) 0;
            margin-bottom: var(--space-xl);
        }

        .onboarding-hero h1 {
            font-size: var(--font-display);
            font-weight: 700;
            background: linear-gradient(135deg, #fff, var(--slate-primary-light));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: var(--space-md);
        }

        .onboarding-hero p {
            font-size: var(--font-lg);
            color: var(--text-secondary);
            max-width: 600px;
            margin: 0 auto var(--space-lg);
        }

        .onboarding-cta {
            display: inline-flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-xl);
            background: var(--slate-primary);
            color: white;
            border: none;
            border-radius: var(--rounded-lg);
            font-size: var(--font-base);
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-fast);
            box-shadow: 0 4px 16px rgba(184, 90, 60, 0.3);
        }

        .onboarding-cta:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(184, 90, 60, 0.4);
        }

        /* ═══ INTEGRATION CARDS ═══ */
        .integration-grid {
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
            gap: var(--space-md);
        }

        .integration-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--rounded-lg);
            padding: var(--space-lg);
            transition: all var(--transition-fast);
        }

        .integration-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }

        .integration-card.connected {
            border-color: var(--conn-active);
        }

        .integration-card.error {
            border-color: var(--conn-error);
        }

        .integration-header {
            display: flex;
            align-items: center;
            gap: var(--space-md);
            margin-bottom: var(--space-md);
        }

        .integration-icon {
            width: 48px;
            height: 48px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: rgba(255, 255, 255, 0.05);
            border-radius: var(--rounded-md);
            font-size: var(--font-xl);
        }

        .integration-info h3 {
            font-size: var(--font-base);
            font-weight: 600;
            color: var(--text-primary);
        }

        .integration-info p {
            font-size: var(--font-sm);
            color: var(--text-muted);
        }

        .integration-status {
            display: flex;
            align-items: center;
            gap: var(--space-sm);
            padding: var(--space-sm) var(--space-md);
            background: rgba(255, 255, 255, 0.03);
            border-radius: var(--rounded-md);
            font-size: var(--font-sm);
        }

        .integration-action {
            margin-top: var(--space-md);
            width: 100%;
            padding: var(--space-sm) var(--space-md);
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: var(--rounded-md);
            color: var(--text-primary);
            font-size: var(--font-sm);
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .integration-action:hover {
            background: rgba(255, 255, 255, 0.1);
            border-color: var(--border-hover);
        }

        /* ═══════════════════════════════════════════════════════════════════════════ */
        /* BROCHURE UI STYLES - Product showcase experience                            */
        /* ═══════════════════════════════════════════════════════════════════════════ */

        .brochure-hero {
            position: relative;
            text-align: center;
            padding: var(--space-3xl) var(--space-lg);
            margin-bottom: var(--space-xl);
            background: linear-gradient(135deg, var(--blueprint-bg) 0%, rgba(13, 27, 42, 0.95) 100%);
            background-image:
                linear-gradient(var(--blueprint-grid) 1px, transparent 1px),
                linear-gradient(90deg, var(--blueprint-grid) 1px, transparent 1px),
                linear-gradient(135deg, var(--blueprint-bg) 0%, rgba(13, 27, 42, 0.95) 100%);
            background-size: 24px 24px, 24px 24px, 100% 100%;
            border-radius: var(--rounded-xl);
            border: 1px solid var(--blueprint-line);
            overflow: hidden;
        }

        .brochure-hero::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(ellipse at center, rgba(152, 193, 217, 0.1) 0%, transparent 70%);
            pointer-events: none;
        }

        .hero-content {
            position: relative;
            z-index: 1;
        }

        .hero-logo-large {
            width: 120px;
            height: 120px;
            margin: 0 auto var(--space-lg);
            color: var(--slate-primary);
        }

        .hero-title {
            font-size: var(--font-display);
            font-weight: 700;
            background: linear-gradient(135deg, #fff 0%, var(--blueprint-accent) 100%);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            margin-bottom: var(--space-sm);
            letter-spacing: -0.02em;
        }

        .hero-subtitle {
            font-size: var(--font-lg);
            color: var(--blueprint-accent);
            margin-bottom: var(--space-xl);
            opacity: 0.9;
        }

        .hero-stats {
            display: flex;
            justify-content: center;
            gap: var(--space-xl);
            margin-bottom: var(--space-xl);
        }

        .hero-stat {
            text-align: center;
        }

        .hero-stat-value {
            font-size: var(--font-2xl);
            font-weight: 700;
            color: #fff;
            font-family: Consolas, monospace;
        }

        .hero-stat-label {
            font-size: var(--font-sm);
            color: var(--blueprint-accent);
            opacity: 0.8;
        }

        .hero-cta {
            display: flex;
            justify-content: center;
            gap: var(--space-md);
        }

        .cta-primary {
            padding: var(--space-md) var(--space-xl);
            background: var(--slate-primary);
            color: #fff;
            border: none;
            border-radius: var(--rounded-lg);
            font-size: var(--font-base);
            font-weight: 600;
            cursor: pointer;
            transition: all var(--transition-fast);
            box-shadow: 0 4px 16px rgba(184, 90, 60, 0.3);
        }

        .cta-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 24px rgba(184, 90, 60, 0.4);
        }

        .cta-secondary {
            padding: var(--space-md) var(--space-xl);
            background: transparent;
            color: var(--blueprint-accent);
            border: 1px solid var(--blueprint-line);
            border-radius: var(--rounded-lg);
            font-size: var(--font-base);
            font-weight: 500;
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .cta-secondary:hover {
            background: rgba(152, 193, 217, 0.1);
            border-color: var(--blueprint-accent);
        }

        /* ═══ GUIDED MODE OVERLAY ═══ */
        .guided-overlay {
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(13, 27, 42, 0.98);
            backdrop-filter: blur(20px);
            z-index: 2000;
            display: none;
            flex-direction: column;
        }

        .guided-overlay.active { display: flex; }

        .guided-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: var(--space-md) var(--space-xl);
            background: rgba(0, 0, 0, 0.3);
            border-bottom: 1px solid var(--blueprint-line);
        }

        .guided-progress-text {
            font-size: var(--font-sm);
            color: var(--blueprint-accent);
        }

        .guided-exit {
            padding: var(--space-sm) var(--space-md);
            background: transparent;
            border: 1px solid var(--border);
            color: var(--text-secondary);
            border-radius: var(--rounded-md);
            cursor: pointer;
            transition: all var(--transition-fast);
        }

        .guided-exit:hover {
            background: rgba(255, 255, 255, 0.05);
            color: var(--text-primary);
        }

        .guided-main {
            flex: 1;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            padding: var(--space-xl);
        }

        .guided-narrator {
            display: flex;
            align-items: flex-start;
            gap: var(--space-md);
            max-width: 600px;
            margin-bottom: var(--space-xl);
        }

        .narrator-avatar {
            width: 56px;
            height: 56px;
            display: flex;
            align-items: center;
            justify-content: center;
            background: var(--slate-primary);
            border-radius: 50%;
            font-size: 1.5rem;
            flex-shrink: 0;
        }

        .narrator-bubble {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            border-radius: var(--rounded-lg);
            padding: var(--space-md);
            position: relative;
        }

        .narrator-bubble::before {
            content: '';
            position: absolute;
            left: -8px;
            top: 20px;
            border: 8px solid transparent;
            border-right-color: rgba(255, 255, 255, 0.05);
        }

        .narrator-text {
            font-size: var(--font-lg);
            color: var(--text-primary);
            line-height: 1.6;
        }

        .guided-action-display {
            text-align: center;
            margin-bottom: var(--space-xl);
        }

        .action-title {
            font-size: var(--font-xl);
            font-weight: 600;
            color: #fff;
            margin-bottom: var(--space-sm);
        }

        .action-status {
            display: flex;
            align-items: center;
            justify-content: center;
            gap: var(--space-sm);
            color: var(--text-secondary);
        }

        .action-spinner {
            width: 16px;
            height: 16px;
            border: 2px solid var(--blueprint-line);
            border-top-color: var(--blueprint-accent);
            border-radius: 50%;
            animation: spin 1s linear infinite;
        }

        @keyframes spin {
            to { transform: rotate(360deg); }
        }

        .guided-steps-bar {
            display: flex;
            gap: var(--space-sm);
            padding: var(--space-md) var(--space-xl);
            background: rgba(0, 0, 0, 0.3);
            border-top: 1px solid var(--blueprint-line);
        }

        .guided-step-dot {
            width: 32px;
            height: 32px;
            display: flex;
            align-items: center;
            justify-content: center;
            border-radius: 50%;
            font-size: var(--font-sm);
            font-weight: 600;
            transition: all var(--transition-fast);
        }

        .guided-step-dot.pending {
            background: var(--step-pending);
            color: #fff;
        }

        .guided-step-dot.active {
            background: var(--step-active);
            color: #fff;
            box-shadow: 0 0 16px rgba(59, 130, 246, 0.5);
        }

        .guided-step-dot.complete {
            background: var(--step-complete);
            color: #fff;
        }

        .guided-step-dot.error {
            background: var(--status-error);
            color: #fff;
        }

        /* Feature Showcase Grid */
        .feature-showcase {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--space-md);
            margin-bottom: var(--space-xl);
        }

        @media (max-width: 1200px) {
            .feature-showcase { grid-template-columns: repeat(2, 1fr); }
        }

        @media (max-width: 768px) {
            .feature-showcase { grid-template-columns: 1fr; }
        }

        .feature-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: var(--rounded-lg);
            padding: var(--space-lg);
            text-align: center;
            transition: all var(--transition-fast);
        }

        .feature-card:hover {
            border-color: var(--border-hover);
            transform: translateY(-2px);
        }

        .feature-icon {
            font-size: 2.5rem;
            margin-bottom: var(--space-md);
        }

        .feature-title {
            font-size: var(--font-base);
            font-weight: 600;
            color: var(--text-primary);
            margin-bottom: var(--space-xs);
        }

        .feature-desc {
            font-size: var(--font-sm);
            color: var(--text-muted);
        }
    </style>
</head>
<body>
    <a class="skip-link" href="#main-content">Skip to main content</a>
    <div class="container">
        <!-- Header -->
        <header class="header" role="banner">
            <div class="logo">
                <div class="logo-icon" id="logo-starburst" title="SLATE Starburst">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
                        <style>
                            .logo-rays { animation: logo-pulse 3s ease-in-out infinite; transform-origin: center; }
                            @keyframes logo-pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.7; } }
                        </style>
                        <g class="logo-rays">
                            <line x1="114.78" y1="106.12" x2="170" y2="128" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.9"/>
                            <line x1="106.12" y1="114.78" x2="124" y2="158" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
                            <line x1="93.88" y1="114.78" x2="72" y2="170" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.9"/>
                            <line x1="85.22" y1="106.12" x2="40" y2="124" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
                            <line x1="85.22" y1="93.88" x2="30" y2="72" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.9"/>
                            <line x1="93.88" y1="85.22" x2="76" y2="40" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
                            <line x1="106.12" y1="85.22" x2="128" y2="30" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.9"/>
                            <line x1="114.78" y1="93.88" x2="158" y2="76" stroke="currentColor" stroke-width="4" stroke-linecap="round" opacity="0.7"/>
                        </g>
                        <circle cx="100" cy="100" r="22" fill="currentColor"/>
                        <text x="100" y="100" font-family="system-ui, sans-serif" font-size="26" font-weight="700" fill="var(--bg-dark, #1A1816)" text-anchor="middle" dominant-baseline="central">S</text>
                    </svg>
                </div>
                <div class="logo-text">
                    <h1>S.L.A.T.E.</h1>
                    <span>Synchronized Living Architecture</span>
                </div>
            </div>
            <div class="header-status">
                <!-- Theme Slider -->
                <div class="theme-slider-container" title="Theme: 0=Dark, 1=Light">
                    <span class="theme-label" id="theme-dark-icon">&#9790;</span>
                    <input type="range" id="theme-slider" class="theme-slider" min="0" max="100" value="15" oninput="updateTheme(this.value/100)" onchange="saveTheme(this.value/100)">
                    <span class="theme-label" id="theme-light-icon">&#9788;</span>
                </div>
                <div class="status-indicator" role="status" aria-live="polite">
                    <span class="status-dot" id="runner-dot" aria-hidden="true"></span>
                    <span id="runner-status-text">Runner: Checking...</span>
                </div>
                <button class="btn btn-ghost" onclick="refreshAll()" aria-label="Refresh all dashboard data">Refresh</button>
            </div>
        </header>

        <!-- ═══ BROCHURE HERO SECTION ═══ -->
        <section class="brochure-hero" id="brochure-hero">
            <div class="hero-content">
                <div class="hero-logo-large">
                    <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="100%" height="100%">
                        <g style="animation: logo-pulse 3s ease-in-out infinite; transform-origin: center;">
                            <line x1="114.78" y1="106.12" x2="170" y2="128" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.9"/>
                            <line x1="106.12" y1="114.78" x2="124" y2="158" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
                            <line x1="93.88" y1="114.78" x2="72" y2="170" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.9"/>
                            <line x1="85.22" y1="106.12" x2="40" y2="124" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
                            <line x1="85.22" y1="93.88" x2="30" y2="72" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.9"/>
                            <line x1="93.88" y1="85.22" x2="76" y2="40" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
                            <line x1="106.12" y1="85.22" x2="128" y2="30" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.9"/>
                            <line x1="114.78" y1="93.88" x2="158" y2="76" stroke="currentColor" stroke-width="5" stroke-linecap="round" opacity="0.7"/>
                        </g>
                        <circle cx="100" cy="100" r="28" fill="currentColor"/>
                        <text x="100" y="100" font-family="system-ui, sans-serif" font-size="32" font-weight="700" fill="#0D1B2A" text-anchor="middle" dominant-baseline="central">S</text>
                    </svg>
                </div>
                <h1 class="hero-title">S.L.A.T.E.</h1>
                <p class="hero-subtitle">Synchronized Living Architecture for Transformation and Evolution</p>

                <div class="hero-stats">
                    <div class="hero-stat">
                        <div class="hero-stat-value" id="hero-gpu-count">2x</div>
                        <div class="hero-stat-label">RTX 5070 Ti</div>
                    </div>
                    <div class="hero-stat">
                        <div class="hero-stat-value">100%</div>
                        <div class="hero-stat-label">Local AI</div>
                    </div>
                    <div class="hero-stat">
                        <div class="hero-stat-value">$0</div>
                        <div class="hero-stat-label">Cloud Costs</div>
                    </div>
                </div>

                <div class="hero-cta">
                    <button class="cta-primary" onclick="startGuidedMode()">
                        Start Guided Setup
                    </button>
                    <button class="cta-secondary" onclick="hideHero()">
                        Advanced Mode
                    </button>
                </div>
            </div>
        </section>

        <!-- Feature Showcase -->
        <div class="feature-showcase">
            <div class="feature-card">
                <div class="feature-icon">🧠</div>
                <div class="feature-title">Local AI Inference</div>
                <div class="feature-desc">Ollama + Foundry powered by dual GPUs</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">⚡</div>
                <div class="feature-title">GPU Acceleration</div>
                <div class="feature-desc">CUDA-optimized parallel processing</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🤖</div>
                <div class="feature-title">Agentic Workflows</div>
                <div class="feature-desc">Claude Code + GitHub Actions</div>
            </div>
            <div class="feature-card">
                <div class="feature-icon">🔒</div>
                <div class="feature-title">Secure by Design</div>
                <div class="feature-desc">ActionGuard + SDK Source Guard</div>
            </div>
        </div>

        <!-- Main Grid -->
        <main id="main-content" role="main">
        <div class="grid">
            <!-- Workflow Pipeline -->
            <div class="card col-12" role="region" aria-label="Workflow Pipeline">
                <div class="card-header">
                    <span class="card-title">Workflow Pipeline</span>
                    <button class="card-action" onclick="refreshWorkflowPipeline()" aria-label="Refresh pipeline">Refresh</button>
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
                    <div class="service-item">
                        <div class="service-name">
                            <div class="service-icon">&#128051;</div>
                            <span>Docker</span>
                        </div>
                        <span class="badge pending" id="docker-badge">Checking</span>
                    </div>
                </div>
            </div>

            <!-- Docker Integration -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Docker Containers</span>
                    <button class="card-action" onclick="refreshDocker()">Refresh</button>
                </div>
                <div class="docker-grid" id="docker-containers">
                    <div class="empty-state">Loading containers...</div>
                </div>
                <div style="display: flex; gap: 8px; margin-top: 12px; padding-top: 12px; border-top: 1px solid var(--border);">
                    <button class="btn btn-ghost" onclick="dockerActionAll('start')" style="flex: 1; font-size: 0.75rem;">Start All</button>
                    <button class="btn btn-ghost" onclick="dockerActionAll('stop')" style="flex: 1; font-size: 0.75rem;">Stop All</button>
                </div>
            </div>

            <!-- Hardware Control -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Hardware Control</span>
                    <button class="card-action" onclick="runBenchmark()">Run Benchmark</button>
                </div>
                <div class="hw-grid">
                    <div class="hw-card">
                        <div class="hw-card-title">GPU Performance</div>
                        <div id="hw-gpu-meters">
                            <div class="hw-meter">
                                <span class="hw-meter-label">GPU 0</span>
                                <div class="hw-meter-bar"><div class="hw-meter-fill" id="hw-gpu0-bar" style="width: 0%"></div></div>
                                <span class="hw-meter-value" id="hw-gpu0-val">--%</span>
                            </div>
                            <div class="hw-meter">
                                <span class="hw-meter-label">GPU 1</span>
                                <div class="hw-meter-bar"><div class="hw-meter-fill" id="hw-gpu1-bar" style="width: 0%"></div></div>
                                <span class="hw-meter-value" id="hw-gpu1-val">--%</span>
                            </div>
                        </div>
                    </div>
                    <div class="hw-card">
                        <div class="hw-card-title">Benchmark Results</div>
                        <div class="benchmark-result" id="benchmark-results">
                            <div class="benchmark-stat">
                                <div class="benchmark-stat-value" id="bench-speed">--</div>
                                <div class="benchmark-stat-label">Tokens/sec</div>
                            </div>
                            <div class="benchmark-stat">
                                <div class="benchmark-stat-value" id="bench-bandwidth">--</div>
                                <div class="benchmark-stat-label">GB/s</div>
                            </div>
                        </div>
                    </div>
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
                <div class="task-list" id="task-list" style="max-height: 180px; overflow-y: auto;">
                    <div class="empty-state">Loading tasks...</div>
                </div>
            </div>

            <!-- SLATE Control Panel -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">SLATE Controls</span>
                    <button class="card-action" onclick="toggleControlOutput()">Toggle Output</button>
                </div>
                <div class="slate-controls">
                    <button class="slate-ctrl-btn" id="ctrl-protocol" onclick="runSlateControl('run-protocol', this)" aria-label="Run SLATE protocol checks">
                        <span class="ctrl-status" id="ctrl-dot-protocol"></span>
                        <span class="ctrl-icon">&#9881;</span>
                        <span class="ctrl-label">Run SLATE</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-update" onclick="runSlateControl('update', this)" aria-label="Update from git and check forks">
                        <span class="ctrl-status" id="ctrl-dot-update"></span>
                        <span class="ctrl-icon">&#8635;</span>
                        <span class="ctrl-label">Update</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-debug" onclick="runSlateControl('debug', this)" aria-label="Run full diagnostics">
                        <span class="ctrl-status" id="ctrl-dot-debug"></span>
                        <span class="ctrl-icon">&#128270;</span>
                        <span class="ctrl-label">Debug</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-benchmark" onclick="runSlateControl('benchmark', this)" aria-label="Run performance benchmarks">
                        <span class="ctrl-status" id="ctrl-dot-benchmark"></span>
                        <span class="ctrl-icon">&#9889;</span>
                        <span class="ctrl-label">Benchmark</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-deploy" onclick="runSlateControlDeploy('start', this)" aria-label="Start SLATE services">
                        <span class="ctrl-status" id="ctrl-dot-deploy"></span>
                        <span class="ctrl-icon">&#9654;</span>
                        <span class="ctrl-label">Deploy</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-security" onclick="runSlateControl('security', this)" aria-label="Run security audit">
                        <span class="ctrl-status" id="ctrl-dot-security"></span>
                        <span class="ctrl-icon">&#128274;</span>
                        <span class="ctrl-label">Security</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-agents" onclick="runSlateControl('agents', this)" aria-label="Check agent system">
                        <span class="ctrl-status" id="ctrl-dot-agents"></span>
                        <span class="ctrl-icon">&#129302;</span>
                        <span class="ctrl-label">Agents</span>
                    </button>
                    <button class="slate-ctrl-btn" id="ctrl-gpu" onclick="runSlateControl('gpu', this)" aria-label="GPU management">
                        <span class="ctrl-status" id="ctrl-dot-gpu"></span>
                        <span class="ctrl-icon">&#127918;</span>
                        <span class="ctrl-label">GPU</span>
                    </button>
                </div>
                <div class="ctrl-output" id="ctrl-output"></div>
                <!-- Quick Actions -->
                <div class="quick-actions-row">
                    <button class="btn btn-primary" onclick="dispatchWorkflow('ci.yml')" aria-label="Dispatch CI pipeline">CI Pipeline</button>
                    <button class="btn btn-ghost" onclick="dispatchWorkflow('slate.yml')" aria-label="Dispatch SLATE checks">SLATE Checks</button>
                    <button class="btn btn-ghost" onclick="dispatchWorkflow('nightly.yml')" aria-label="Dispatch nightly suite">Nightly Suite</button>
                    <button class="btn btn-ghost" onclick="dispatchWorkflow('agentic.yml')" aria-label="Dispatch agentic AI">Agentic AI</button>
                </div>
            </div>

            <!-- Recent Workflows -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Recent Workflows</span>
                    <button class="card-action" onclick="refreshWorkflows()">Refresh</button>
                </div>
                <div id="workflow-list" style="max-height: 220px; overflow-y: auto;">
                    <div class="empty-state">Loading workflows...</div>
                </div>
            </div>

            <!-- Activity Feed -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Activity Feed</span>
                    <button class="card-action" onclick="refreshActivity()">Refresh</button>
                </div>
                <div class="activity-feed" id="activity-feed" style="max-height: 220px; overflow-y: auto;">
                    <div class="empty-state">No recent activity</div>
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

            <!-- Tech Tree (Full Width, Prominent) -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">Tech Tree</span>
                    <div style="display: flex; gap: 16px; align-items: center;">
                        <div style="display: flex; gap: 12px; font-size: 0.7rem;">
                            <span style="display: flex; align-items: center; gap: 4px;">
                                <span style="width: 10px; height: 10px; border-radius: 50%; background: var(--status-success);"></span>
                                Complete: <span id="tree-complete">0</span>
                            </span>
                            <span style="display: flex; align-items: center; gap: 4px;">
                                <span style="width: 10px; height: 10px; border-radius: 50%; background: var(--status-warning);"></span>
                                In Progress: <span id="tree-progress">0</span>
                            </span>
                            <span style="display: flex; align-items: center; gap: 4px;">
                                <span style="width: 10px; height: 10px; border-radius: 50%; background: var(--text-muted);"></span>
                                Available: <span id="tree-available">0</span>
                            </span>
                        </div>
                        <button class="card-action" onclick="refreshTechTree()">Refresh</button>
                    </div>
                </div>
                <div class="tech-tree-container" id="tech-tree-container" style="height: 450px;">
                    <svg class="tech-tree-svg" id="tech-tree-svg"></svg>
                    <div class="tech-tooltip" id="tech-tooltip">
                        <div class="tech-tooltip-title"></div>
                        <div class="tech-tooltip-desc"></div>
                        <div class="tech-tooltip-phase"></div>
                    </div>
                    <div class="tech-controls">
                        <button class="tech-control-btn" onclick="zoomTechTree(1.2)">+</button>
                        <button class="tech-control-btn" onclick="zoomTechTree(0.8)">-</button>
                        <button class="tech-control-btn" onclick="resetTechTree()">Reset</button>
                    </div>
                    <div class="tech-phase-legend" style="position: absolute; bottom: 10px; left: 10px; display: flex; gap: 16px; font-size: 0.65rem; color: var(--text-muted);">
                        <span style="border-left: 3px solid var(--status-success); padding-left: 6px;">Phase 1: Foundation</span>
                        <span style="border-left: 3px solid var(--status-warning); padding-left: 6px;">Phase 2: Integration</span>
                    </div>
                </div>
            </div>

            <!-- Agent Registry -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Agent Registry</span>
                    <button class="card-action" onclick="refreshAgents()">Refresh</button>
                </div>
                <div class="agent-stats" style="display: flex; gap: 16px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="agent-total">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Total</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-success);" id="agent-gpu">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">GPU</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="agent-cpu">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">CPU</div>
                    </div>
                </div>
                <div class="agent-list" id="agent-list" style="max-height: 250px; overflow-y: auto;">
                    <div class="empty-state">Loading agents...</div>
                </div>
            </div>

            <!-- Multi-Runner Pool -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Multi-Runner Pool</span>
                    <button class="card-action" onclick="refreshMultiRunner()">Refresh</button>
                </div>
                <div class="runner-stats" style="display: flex; gap: 16px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="runner-total">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Total</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-success);" id="runner-running">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Running</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="runner-idle">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Idle</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="runner-parallel">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Max Parallel</div>
                    </div>
                </div>
                <div class="runner-list" id="multirunner-list" style="max-height: 200px; overflow-y: auto;">
                    <div class="empty-state">Loading runners...</div>
                </div>
            </div>

            <!-- Workflow Statistics -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Workflow Statistics</span>
                    <button class="card-action" onclick="refreshWorkflowStats()">Refresh</button>
                </div>
                <div class="workflow-stats" style="display: flex; gap: 16px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="wf-total">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Workflows</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-success);" id="wf-concurrency">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">w/ Concurrency</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-success);" id="wf-success">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Success</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-error);" id="wf-failure">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Failed</div>
                    </div>
                </div>
                <div class="workflow-list" id="workflow-stats-list" style="max-height: 200px; overflow-y: auto;">
                    <div class="empty-state">Loading workflows...</div>
                </div>
            </div>

            <!-- Specifications -->
            <div class="card col-6">
                <div class="card-header">
                    <span class="card-title">Specifications</span>
                    <button class="card-action" onclick="refreshSpecs()">Refresh</button>
                </div>
                <div class="spec-stats" style="display: flex; gap: 16px; margin-bottom: 12px; padding-bottom: 12px; border-bottom: 1px solid var(--border);">
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="spec-total">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Total</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas; color: var(--status-success);" id="spec-complete">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Complete</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="spec-implementing">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Implementing</div>
                    </div>
                    <div style="text-align: center;">
                        <div style="font-size: 1.25rem; font-weight: 700; font-family: Consolas;" id="spec-draft">0</div>
                        <div style="font-size: 0.65rem; color: var(--text-muted); text-transform: uppercase;">Draft</div>
                    </div>
                </div>
                <div class="spec-list" id="spec-list" style="max-height: 200px; overflow-y: auto;">
                    <div class="empty-state">Loading specs...</div>
                </div>
            </div>

            <!-- Dependency Forks -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">Dependency Forks</span>
                    <button class="card-action" onclick="refreshForks()">Refresh</button>
                </div>
                <div class="fork-list" id="fork-list" style="display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: 12px;">
                    <div class="empty-state">Loading forks...</div>
                </div>
            </div>

            <!-- ═══ SYSTEM ARCHITECTURE BLUEPRINT ═══ -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">System Architecture</span>
                    <button class="card-action" onclick="refreshArchitecture()">Refresh</button>
                </div>
                <div class="architecture-diagram" id="arch-diagram">
                    <span class="arch-title">S.L.A.T.E. Architecture Blueprint</span>

                    <!-- SVG Connection Lines -->
                    <svg class="arch-connections" id="arch-svg">
                        <!-- Connections drawn dynamically by JS -->
                    </svg>

                    <!-- Core SLATE Node -->
                    <div class="arch-node active" id="node-slate" style="top: 180px; left: 50%; transform: translateX(-50%);">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">S</div>
                            <span class="arch-node-name">SLATE Core</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot active"></span>
                            <span>Orchestrator Active</span>
                        </div>
                    </div>

                    <!-- Dashboard Node -->
                    <div class="arch-node" id="node-dashboard" style="top: 40px; left: 20%;">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">D</div>
                            <span class="arch-node-name">Dashboard</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-dash-status"></span>
                            <span id="arch-dash-text">Port 8080</span>
                        </div>
                    </div>

                    <!-- Ollama LLM Node -->
                    <div class="arch-node" id="node-ollama" style="top: 40px; left: 50%; transform: translateX(-50%);">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">O</div>
                            <span class="arch-node-name">Ollama LLM</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-ollama-status"></span>
                            <span id="arch-ollama-text">Port 11434</span>
                        </div>
                    </div>

                    <!-- GPU Node -->
                    <div class="arch-node" id="node-gpu" style="top: 40px; right: 20%;">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">G</div>
                            <span class="arch-node-name">Dual GPU</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-gpu-status"></span>
                            <span id="arch-gpu-text">RTX 5070 Ti x2</span>
                        </div>
                    </div>

                    <!-- GitHub Runner Node -->
                    <div class="arch-node" id="node-runner" style="bottom: 40px; left: 20%;">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">R</div>
                            <span class="arch-node-name">GitHub Runner</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-runner-status"></span>
                            <span id="arch-runner-text">Self-Hosted</span>
                        </div>
                    </div>

                    <!-- Docker Node -->
                    <div class="arch-node" id="node-docker" style="bottom: 40px; left: 50%; transform: translateX(-50%);">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">🐳</div>
                            <span class="arch-node-name">Docker</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-docker-status"></span>
                            <span id="arch-docker-text">Containers</span>
                        </div>
                    </div>

                    <!-- Claude Code Node -->
                    <div class="arch-node" id="node-claude" style="bottom: 40px; right: 20%;">
                        <div class="arch-node-header">
                            <div class="arch-node-icon">C</div>
                            <span class="arch-node-name">Claude Code</span>
                        </div>
                        <div class="arch-node-status">
                            <span class="arch-status-dot" id="arch-claude-status"></span>
                            <span id="arch-claude-text">MCP Server</span>
                        </div>
                    </div>
                </div>
            </div>

            <!-- ═══ INTEGRATION CARDS ═══ -->
            <div class="card col-12">
                <div class="card-header">
                    <span class="card-title">Integrations</span>
                    <button class="card-action" onclick="startSetupWizard()">Setup Wizard</button>
                </div>
                <div class="integration-grid" id="integration-grid">
                    <!-- GitHub Integration -->
                    <div class="integration-card connected" id="int-github">
                        <div class="integration-header">
                            <div class="integration-icon">📦</div>
                            <div class="integration-info">
                                <h3>GitHub</h3>
                                <p>Repository & Actions</p>
                            </div>
                        </div>
                        <div class="integration-status">
                            <span class="arch-status-dot active"></span>
                            <span>Connected to S.L.A.T.E.</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('github')">Configure</button>
                    </div>

                    <!-- Docker Integration -->
                    <div class="integration-card" id="int-docker">
                        <div class="integration-header">
                            <div class="integration-icon">🐳</div>
                            <div class="integration-info">
                                <h3>Docker</h3>
                                <p>Container Management</p>
                            </div>
                        </div>
                        <div class="integration-status" id="int-docker-status">
                            <span class="arch-status-dot pending"></span>
                            <span>Checking...</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('docker')">Configure</button>
                    </div>

                    <!-- VS Code Integration -->
                    <div class="integration-card connected" id="int-vscode">
                        <div class="integration-header">
                            <div class="integration-icon">📝</div>
                            <div class="integration-info">
                                <h3>VS Code</h3>
                                <p>SLATE Copilot Extension</p>
                            </div>
                        </div>
                        <div class="integration-status">
                            <span class="arch-status-dot active"></span>
                            <span>Extension Installed</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('vscode')">Open Settings</button>
                    </div>

                    <!-- Claude Code Integration -->
                    <div class="integration-card" id="int-claude">
                        <div class="integration-header">
                            <div class="integration-icon">🤖</div>
                            <div class="integration-info">
                                <h3>Claude Code</h3>
                                <p>MCP Server & Slash Commands</p>
                            </div>
                        </div>
                        <div class="integration-status" id="int-claude-status">
                            <span class="arch-status-dot pending"></span>
                            <span>Checking...</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('claude')">Configure</button>
                    </div>

                    <!-- Ollama Integration -->
                    <div class="integration-card" id="int-ollama">
                        <div class="integration-header">
                            <div class="integration-icon">🧠</div>
                            <div class="integration-info">
                                <h3>Ollama</h3>
                                <p>Local LLM Inference</p>
                            </div>
                        </div>
                        <div class="integration-status" id="int-ollama-status">
                            <span class="arch-status-dot pending"></span>
                            <span>Checking...</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('ollama')">Manage Models</button>
                    </div>

                    <!-- Foundry Local Integration -->
                    <div class="integration-card" id="int-foundry">
                        <div class="integration-header">
                            <div class="integration-icon">⚡</div>
                            <div class="integration-info">
                                <h3>Foundry Local</h3>
                                <p>ONNX-Optimized Inference</p>
                            </div>
                        </div>
                        <div class="integration-status" id="int-foundry-status">
                            <span class="arch-status-dot pending"></span>
                            <span>Checking...</span>
                        </div>
                        <button class="integration-action" onclick="configureIntegration('foundry')">Configure</button>
                    </div>
                </div>
            </div>
        </div>
        </main>

    <!-- ═══ COPILOT GUIDANCE PANEL ═══ -->
    <div class="copilot-guide" id="copilot-guide">
        <div class="copilot-header">
            <div class="copilot-title">
                <div class="copilot-icon">S</div>
                <span>SLATE Copilot</span>
            </div>
            <button class="wizard-close" onclick="toggleCopilot()">×</button>
        </div>
        <div class="copilot-body">
            <div class="copilot-message">
                <div class="copilot-message-title">Welcome to S.L.A.T.E.</div>
                <div class="copilot-message-text">
                    Your Synchronized Living Architecture is ready. I can help you set up integrations,
                    configure services, and optimize your development workflow.
                </div>
            </div>
            <div class="copilot-suggestions" id="copilot-suggestions">
                <div class="copilot-suggestion" onclick="startSetupWizard()">
                    <div class="copilot-suggestion-icon">🚀</div>
                    <span class="copilot-suggestion-text">Run Setup Wizard</span>
                </div>
                <div class="copilot-suggestion" onclick="checkIntegrations()">
                    <div class="copilot-suggestion-icon">🔗</div>
                    <span class="copilot-suggestion-text">Check All Integrations</span>
                </div>
                <div class="copilot-suggestion" onclick="openDocs()">
                    <div class="copilot-suggestion-icon">📚</div>
                    <span class="copilot-suggestion-text">View Documentation</span>
                </div>
                <div class="copilot-suggestion" onclick="runHealthCheck()">
                    <div class="copilot-suggestion-icon">✅</div>
                    <span class="copilot-suggestion-text">Run System Health Check</span>
                </div>
            </div>
        </div>
    </div>

    <!-- Copilot Toggle Button -->
    <button class="copilot-toggle" id="copilot-toggle" onclick="toggleCopilot()" title="SLATE Copilot">
        <svg width="24" height="24" viewBox="0 0 200 200">
            <g>
                <line x1="114.78" y1="106.12" x2="160" y2="125" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="106.12" y1="114.78" x2="120" y2="150" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="93.88" y1="114.78" x2="78" y2="160" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="85.22" y1="106.12" x2="45" y2="120" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="85.22" y1="93.88" x2="40" y2="78" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="93.88" y1="85.22" x2="80" y2="45" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="106.12" y1="85.22" x2="125" y2="40" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
                <line x1="114.78" y1="93.88" x2="155" y2="80" stroke="currentColor" stroke-width="5" stroke-linecap="round"/>
            </g>
            <circle cx="100" cy="100" r="20" fill="currentColor"/>
        </svg>
    </button>

    <!-- ═══ GUIDED MODE OVERLAY ═══ -->
    <div class="guided-overlay" id="guided-overlay">
        <div class="guided-header">
            <span class="guided-progress-text" id="guided-progress-text">Step 1 of 11</span>
            <button class="guided-exit" onclick="exitGuidedMode()">Exit Guided Mode</button>
        </div>

        <div class="guided-main">
            <div class="guided-narrator">
                <div class="narrator-avatar">🤖</div>
                <div class="narrator-bubble">
                    <div class="narrator-text" id="narrator-text">
                        Welcome! I'm your SLATE assistant. Let me set up your development environment automatically...
                    </div>
                </div>
            </div>

            <div class="guided-action-display">
                <h2 class="action-title" id="guided-action-title">Welcome to S.L.A.T.E.</h2>
                <div class="action-status" id="guided-action-status">
                    <div class="action-spinner"></div>
                    <span>Initializing...</span>
                </div>
            </div>
        </div>

        <div class="guided-steps-bar" id="guided-steps-bar">
            <!-- Step dots generated dynamically -->
        </div>
    </div>

    <!-- ═══ SETUP WIZARD MODAL ═══ -->
    <div class="setup-wizard" id="setup-wizard">
        <div class="wizard-header">
            <div>
                <h2 class="wizard-title">S.L.A.T.E. Setup Wizard</h2>
                <p class="wizard-subtitle">Configure your development environment</p>
            </div>
            <button class="wizard-close" onclick="closeSetupWizard()">×</button>
        </div>
        <div class="wizard-body">
            <aside class="wizard-steps">
                <div class="wizard-step active" data-step="1" onclick="goToStep(1)">
                    <div class="step-number">1</div>
                    <div class="step-info">
                        <div class="step-label">Welcome</div>
                        <div class="step-description">Introduction to SLATE</div>
                    </div>
                </div>
                <div class="wizard-step" data-step="2" onclick="goToStep(2)">
                    <div class="step-number">2</div>
                    <div class="step-info">
                        <div class="step-label">System Detection</div>
                        <div class="step-description">Scan installed services</div>
                    </div>
                </div>
                <div class="wizard-step" data-step="3" onclick="goToStep(3)">
                    <div class="step-number">3</div>
                    <div class="step-info">
                        <div class="step-label">Core Services</div>
                        <div class="step-description">Configure SLATE core</div>
                    </div>
                </div>
                <div class="wizard-step" data-step="4" onclick="goToStep(4)">
                    <div class="step-number">4</div>
                    <div class="step-info">
                        <div class="step-label">Integrations</div>
                        <div class="step-description">Connect external services</div>
                    </div>
                </div>
                <div class="wizard-step" data-step="5" onclick="goToStep(5)">
                    <div class="step-number">5</div>
                    <div class="step-info">
                        <div class="step-label">Validation</div>
                        <div class="step-description">Test all connections</div>
                    </div>
                </div>
                <div class="wizard-step" data-step="6" onclick="goToStep(6)">
                    <div class="step-number">6</div>
                    <div class="step-info">
                        <div class="step-label">Complete</div>
                        <div class="step-description">Ready to use</div>
                    </div>
                </div>
            </aside>
            <main class="wizard-content" id="wizard-content">
                <!-- Step content loaded dynamically -->
                <div class="wizard-progress">
                    <div class="wizard-progress-fill" id="wizard-progress" style="width: 16.6%"></div>
                </div>
                <div id="wizard-step-content">
                    <h2>Welcome to S.L.A.T.E.</h2>
                    <p style="font-size: var(--font-lg); color: var(--text-secondary); margin: var(--space-lg) 0;">
                        <strong>Synchronized Living Architecture for Transformation and Evolution</strong>
                    </p>
                    <p style="color: var(--text-muted); margin-bottom: var(--space-xl);">
                        This wizard will guide you through setting up your SLATE development environment.
                        We'll configure services, connect integrations, and ensure everything is working properly.
                    </p>
                    <div style="display: grid; grid-template-columns: repeat(3, 1fr); gap: var(--space-md);">
                        <div style="padding: var(--space-md); background: rgba(255,255,255,0.03); border-radius: var(--rounded-md); text-align: center;">
                            <div style="font-size: 2rem; margin-bottom: var(--space-sm);">🧠</div>
                            <div style="font-weight: 600;">Local AI</div>
                            <div style="font-size: var(--font-sm); color: var(--text-muted);">Ollama + Foundry</div>
                        </div>
                        <div style="padding: var(--space-md); background: rgba(255,255,255,0.03); border-radius: var(--rounded-md); text-align: center;">
                            <div style="font-size: 2rem; margin-bottom: var(--space-sm);">⚡</div>
                            <div style="font-weight: 600;">Dual GPU</div>
                            <div style="font-size: var(--font-sm); color: var(--text-muted);">RTX 5070 Ti x2</div>
                        </div>
                        <div style="padding: var(--space-md); background: rgba(255,255,255,0.03); border-radius: var(--rounded-md); text-align: center;">
                            <div style="font-size: 2rem; margin-bottom: var(--space-sm);">🤖</div>
                            <div style="font-weight: 600;">Agentic</div>
                            <div style="font-size: var(--font-sm); color: var(--text-muted);">Claude Code + Copilot</div>
                        </div>
                    </div>
                </div>
            </main>
        </div>
        <div class="wizard-footer">
            <button class="btn btn-ghost" onclick="closeSetupWizard()">Cancel</button>
            <div>
                <button class="btn btn-ghost" id="wizard-back" onclick="prevStep()" style="display: none;">Back</button>
                <button class="btn btn-primary" id="wizard-next" onclick="nextStep()">Get Started</button>
            </div>
        </div>
    </div>
    </div>

    <div id="connection-status" class="disconnected" role="status" aria-live="polite">Connecting...</div>

    <script>
        let ws = null;
        let reconnectAttempts = 0;

        // ═══ THEME SYSTEM ═══
        function updateTheme(value) {
            document.documentElement.style.setProperty('--theme-value', value);

            // Interpolate colors based on theme value
            const darkBg = [10, 15, 10];
            const lightBg = [245, 247, 245];
            const darkText = [232, 240, 232];
            const lightText = [26, 31, 26];

            // Background interpolation
            const bg = darkBg.map((d, i) => Math.round(d + (lightBg[i] - d) * value));
            const text = lightText.map((l, i) => Math.round(l + (darkText[i] - l) * (1 - value)));

            document.documentElement.style.setProperty('--bg-dark', `rgb(${bg.join(',')})`);
            document.documentElement.style.setProperty('--text-primary', `rgb(${text.join(',')})`);

            // Adjust other derived values
            const cardOpacity = 0.75 + (value * 0.2);
            document.documentElement.style.setProperty('--bg-card', `rgba(${bg[0]+10}, ${bg[1]+13}, ${bg[2]+10}, ${cardOpacity})`);
        }

        async function saveTheme(value) {
            try {
                await fetch('/api/theme', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ value: value })
                });
            } catch (e) {
                console.log('Failed to save theme:', e);
            }
        }

        async function loadTheme() {
            try {
                const res = await fetch('/api/theme');
                const data = await res.json();
                const value = data.theme_value || 0.15;
                document.getElementById('theme-slider').value = value * 100;
                updateTheme(value);
            } catch (e) {
                console.log('Failed to load theme:', e);
            }
        }

        // ═══ DOCKER INTEGRATION ═══
        async function refreshDocker() {
            try {
                const res = await fetch('/api/docker/containers');
                const data = await res.json();
                const container = document.getElementById('docker-containers');
                const badge = document.getElementById('docker-badge');

                if (data.available && data.containers && data.containers.length > 0) {
                    badge.className = 'badge online';
                    badge.textContent = `${data.containers.filter(c => c.status === 'running').length}/${data.containers.length}`;

                    container.innerHTML = data.containers.slice(0, 6).map(c => {
                        const statusClass = c.status === 'running' ? 'running' : (c.status === 'paused' ? 'paused' : 'exited');
                        const ports = c.ports ? c.ports.substring(0, 30) : '';
                        return `
                            <div class="docker-item ${statusClass}">
                                <div class="docker-icon">&#128051;</div>
                                <div class="docker-info">
                                    <div class="docker-name">${c.name}</div>
                                    <div class="docker-ports">${ports || c.image}</div>
                                </div>
                                <div class="docker-actions">
                                    ${c.status !== 'running' ?
                                        `<button class="docker-action-btn" onclick="dockerAction('${c.name}', 'start')">Start</button>` :
                                        `<button class="docker-action-btn" onclick="dockerAction('${c.name}', 'stop')">Stop</button>`
                                    }
                                </div>
                            </div>
                        `;
                    }).join('');
                } else if (!data.available) {
                    badge.className = 'badge offline';
                    badge.textContent = 'Offline';
                    container.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">' + (data.error || 'Docker not running') + '</div>';
                } else {
                    badge.className = 'badge online';
                    badge.textContent = '0';
                    container.innerHTML = '<div class="empty-state" style="font-size:0.75rem;">No containers</div>';
                }
            } catch (e) {
                console.error('Failed to fetch Docker:', e);
            }
        }

        async function dockerAction(container, action) {
            try {
                const res = await fetch('/api/docker/action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ container: container, action: action })
                });
                const data = await res.json();
                if (data.success) {
                    setTimeout(refreshDocker, 1000);
                } else {
                    alert('Docker action failed: ' + (data.error || 'Unknown error'));
                }
            } catch (e) {
                alert('Docker action error: ' + e.message);
            }
        }

        async function dockerActionAll(action) {
            try {
                const res = await fetch('/api/docker/containers');
                const data = await res.json();
                if (data.containers) {
                    for (const c of data.containers) {
                        if (action === 'start' && c.status !== 'running') {
                            await dockerAction(c.name, 'start');
                        } else if (action === 'stop' && c.status === 'running') {
                            await dockerAction(c.name, 'stop');
                        }
                    }
                }
                setTimeout(refreshDocker, 2000);
            } catch (e) {
                console.error('Docker action all failed:', e);
            }
        }

        // ═══ HARDWARE CONTROL ═══
        async function refreshHardwareControl() {
            try {
                const res = await fetch('/api/system/gpu');
                const data = await res.json();

                if (data.available && data.gpus && data.gpus.length > 0) {
                    data.gpus.forEach((gpu, idx) => {
                        const bar = document.getElementById(`hw-gpu${idx}-bar`);
                        const val = document.getElementById(`hw-gpu${idx}-val`);
                        if (bar && val) {
                            const util = gpu.gpu_util || 0;
                            bar.style.width = `${util}%`;
                            bar.className = 'hw-meter-fill' + (util > 80 ? ' danger' : (util > 60 ? ' warning' : ''));
                            val.textContent = `${util}%`;
                        }
                    });
                }
            } catch (e) {
                console.error('Failed to refresh hardware:', e);
            }
        }

        async function runBenchmark() {
            try {
                document.getElementById('bench-speed').textContent = '...';
                document.getElementById('bench-bandwidth').textContent = '...';

                const res = await fetch('/api/benchmark/run', { method: 'POST' });
                const data = await res.json();

                if (data.success && data.benchmark) {
                    document.getElementById('bench-speed').textContent = data.benchmark.inference_speed || '--';
                    document.getElementById('bench-bandwidth').textContent = data.benchmark.memory_bandwidth || '--';
                } else {
                    document.getElementById('bench-speed').textContent = 'ERR';
                    document.getElementById('bench-bandwidth').textContent = 'ERR';
                }
            } catch (e) {
                console.error('Benchmark failed:', e);
                document.getElementById('bench-speed').textContent = 'ERR';
                document.getElementById('bench-bandwidth').textContent = 'ERR';
            }
        }

        async function loadBenchmarkHistory() {
            try {
                const res = await fetch('/api/benchmark/history');
                const data = await res.json();
                if (data.benchmarks && data.benchmarks.length > 0) {
                    const latest = data.benchmarks[data.benchmarks.length - 1];
                    document.getElementById('bench-speed').textContent = latest.inference_speed || '--';
                    document.getElementById('bench-bandwidth').textContent = latest.memory_bandwidth || '--';
                }
            } catch (e) {
                console.log('No benchmark history');
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // COPILOT GUIDANCE SYSTEM
        // ═══════════════════════════════════════════════════════════════════════════

        let copilotVisible = false;

        function toggleCopilot() {
            copilotVisible = !copilotVisible;
            document.getElementById('copilot-guide').classList.toggle('active', copilotVisible);
            document.getElementById('copilot-toggle').classList.toggle('hidden', copilotVisible);
        }

        function checkIntegrations() {
            refreshArchitecture();
            updateCopilotMessage('Checking Integrations', 'Scanning all system integrations...');
        }

        function openDocs() {
            window.open('https://github.com/SynchronizedLivingArchitecture/S.L.A.T.E./wiki', '_blank');
        }

        function runHealthCheck() {
            refreshAll();
            updateCopilotMessage('Health Check', 'Running complete system health check...');
        }

        function updateCopilotMessage(title, text) {
            const msgTitle = document.querySelector('.copilot-message-title');
            const msgText = document.querySelector('.copilot-message-text');
            if (msgTitle) msgTitle.textContent = title;
            if (msgText) msgText.textContent = text;
        }

        function configureIntegration(type) {
            const configs = {
                github: 'Open GitHub repository settings',
                docker: 'Configure Docker container settings',
                vscode: 'Open VS Code extension settings',
                claude: 'Configure Claude Code MCP server',
                ollama: 'Manage Ollama models',
                foundry: 'Configure Foundry Local'
            };
            updateCopilotMessage('Configure ' + type, configs[type] || 'Opening configuration...');
            toggleCopilot();
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // SETUP WIZARD SYSTEM
        // ═══════════════════════════════════════════════════════════════════════════

        let currentWizardStep = 1;
        const totalWizardSteps = 6;

        function startSetupWizard() {
            document.getElementById('setup-wizard').classList.add('active');
            currentWizardStep = 1;
            updateWizardUI();
        }

        function closeSetupWizard() {
            document.getElementById('setup-wizard').classList.remove('active');
        }

        function nextStep() {
            if (currentWizardStep < totalWizardSteps) {
                markStepComplete(currentWizardStep);
                currentWizardStep++;
                updateWizardUI();
            } else {
                closeSetupWizard();
            }
        }

        function prevStep() {
            if (currentWizardStep > 1) {
                currentWizardStep--;
                updateWizardUI();
            }
        }

        function goToStep(step) {
            const stepEl = document.querySelector('.wizard-step[data-step="' + step + '"]');
            if (step <= currentWizardStep || (stepEl && stepEl.classList.contains('complete'))) {
                currentWizardStep = step;
                updateWizardUI();
            }
        }

        function markStepComplete(step) {
            const stepEl = document.querySelector('.wizard-step[data-step="' + step + '"]');
            if (stepEl) stepEl.classList.add('complete');
        }

        function updateWizardUI() {
            document.querySelectorAll('.wizard-step').forEach(el => {
                el.classList.remove('active');
                if (parseInt(el.dataset.step) === currentWizardStep) {
                    el.classList.add('active');
                }
            });
            const progress = (currentWizardStep / totalWizardSteps) * 100;
            document.getElementById('wizard-progress').style.width = progress + '%';
            document.getElementById('wizard-back').style.display = currentWizardStep > 1 ? 'inline-block' : 'none';
            document.getElementById('wizard-next').textContent = currentWizardStep === totalWizardSteps ? 'Finish' : 'Next';
            loadWizardStepContent(currentWizardStep);
        }

        function loadWizardStepContent(step) {
            const content = document.getElementById('wizard-step-content');
            // Simplified step content
            if (step === 2) runSystemDetection();
        }

        async function runSystemDetection() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const gpuEl = document.getElementById('detect-gpu');
                if (gpuEl) {
                    gpuEl.className = data.gpu?.count > 0 ? 'arch-status-dot active' : 'arch-status-dot inactive';
                }
            } catch (e) {}
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // ARCHITECTURE DIAGRAM SYSTEM
        // ═══════════════════════════════════════════════════════════════════════════

        async function refreshArchitecture() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();

                updateArchNode('arch-dash-status', 'arch-dash-text', true, 'Port 8080');
                updateArchNode('arch-ollama-status', 'arch-ollama-text',
                    data.ollama_status === 'online', data.ollama_status === 'online' ? 'Online' : 'Offline');
                updateArchNode('arch-gpu-status', 'arch-gpu-text',
                    data.gpu && data.gpu.count > 0, data.gpu ? data.gpu.count + 'x GPU' : 'No GPU');
                updateArchNode('arch-runner-status', 'arch-runner-text',
                    data.runner_status === 'online', data.runner_status === 'online' ? 'Active' : 'Idle');
                updateIntegrationStatus();
            } catch (e) {
                console.error('Failed to refresh architecture:', e);
            }
        }

        function updateArchNode(dotId, textId, isActive, text) {
            const dot = document.getElementById(dotId);
            const textEl = document.getElementById(textId);
            if (dot) dot.className = 'arch-status-dot ' + (isActive ? 'active' : 'inactive');
            if (textEl) textEl.textContent = text;
        }

        async function updateIntegrationStatus() {
            try {
                const res = await fetch('/api/docker/containers');
                const data = await res.json();
                const card = document.getElementById('int-docker');
                const status = document.getElementById('int-docker-status');
                if (card && status) {
                    if (data.available) {
                        card.classList.add('connected');
                        status.innerHTML = '<span class="arch-status-dot active"></span><span>Available</span>';
                    } else {
                        card.classList.remove('connected');
                        status.innerHTML = '<span class="arch-status-dot inactive"></span><span>Not Available</span>';
                    }
                }
            } catch (e) {}

            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                const card = document.getElementById('int-ollama');
                const status = document.getElementById('int-ollama-status');
                if (card && status) {
                    if (data.ollama_status === 'online') {
                        card.classList.add('connected');
                        status.innerHTML = '<span class="arch-status-dot active"></span><span>Online</span>';
                    } else {
                        card.classList.remove('connected');
                        status.innerHTML = '<span class="arch-status-dot inactive"></span><span>Offline</span>';
                    }
                }
            } catch (e) {}

            const claudeCard = document.getElementById('int-claude');
            const claudeStatus = document.getElementById('int-claude-status');
            if (claudeCard && claudeStatus) {
                claudeCard.classList.add('connected');
                claudeStatus.innerHTML = '<span class="arch-status-dot active"></span><span>MCP Available</span>';
            }
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // GUIDED MODE SYSTEM - AI-driven automatic setup
        // ═══════════════════════════════════════════════════════════════════════════

        let guidedModeActive = false;
        let guidedAutoAdvance = true;

        async function startGuidedMode() {
            guidedModeActive = true;
            document.getElementById('guided-overlay').classList.add('active');
            document.getElementById('brochure-hero').style.display = 'none';

            try {
                const res = await fetch('/api/guided/start', { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    updateGuidedUI(data);
                    renderGuidedSteps(data.step);

                    // Auto-execute first step after delay
                    setTimeout(() => executeGuidedStep(), 2000);
                }
            } catch (e) {
                console.error('Failed to start guided mode:', e);
                updateNarratorText('Error starting guided mode. Please try again.');
            }
        }

        async function executeGuidedStep() {
            if (!guidedModeActive) return;

            try {
                const res = await fetch('/api/guided/execute', { method: 'POST' });
                const data = await res.json();

                if (data.success) {
                    updateActionStatus(data.message, true);

                    // Auto-advance after delay
                    if (data.auto_advance && guidedAutoAdvance) {
                        setTimeout(() => advanceGuidedStep(), (data.delay_seconds || 2) * 1000);
                    }
                } else {
                    updateActionStatus(data.message, false);
                    updateNarratorText(data.message + (data.recovery_hint ? ' ' + data.recovery_hint : ''));
                }
            } catch (e) {
                console.error('Failed to execute guided step:', e);
                updateActionStatus('Execution error', false);
            }
        }

        async function advanceGuidedStep() {
            if (!guidedModeActive) return;

            try {
                const res = await fetch('/api/guided/advance', { method: 'POST' });
                const data = await res.json();

                if (data.complete) {
                    completeGuidedMode();
                } else if (data.success) {
                    updateGuidedUI(data);
                    updateGuidedStepDots();
                    setTimeout(() => executeGuidedStep(), 1000);
                }
            } catch (e) {
                console.error('Failed to advance guided step:', e);
            }
        }

        function updateGuidedUI(data) {
            if (data.narration) {
                updateNarratorText(data.narration);
            }
            if (data.step) {
                document.getElementById('guided-action-title').textContent = data.step.title;
                document.getElementById('guided-progress-text').textContent =
                    'Step ' + (getCurrentStepIndex() + 1) + ' of 11';
            }
        }

        function updateNarratorText(text) {
            document.getElementById('narrator-text').textContent = text;
        }

        function updateActionStatus(message, success) {
            const status = document.getElementById('guided-action-status');
            if (success) {
                status.innerHTML = '<span style="color: var(--status-active);">✓</span> <span>' + message + '</span>';
            } else {
                status.innerHTML = '<span style="color: var(--status-error);">!</span> <span>' + message + '</span>';
            }
        }

        async function renderGuidedSteps() {
            const bar = document.getElementById('guided-steps-bar');
            const steps = [];
            for (let i = 1; i <= 11; i++) {
                steps.push('<span class="guided-step-dot ' + (i === 1 ? 'active' : 'pending') + '" data-step="' + i + '">' + i + '</span>');
            }
            bar.innerHTML = steps.join('');
        }

        function updateGuidedStepDots() {
            const currentIndex = getCurrentStepIndex();
            document.querySelectorAll('.guided-step-dot').forEach((dot, idx) => {
                dot.className = 'guided-step-dot ' + (idx < currentIndex ? 'complete' : (idx === currentIndex ? 'active' : 'pending'));
                if (idx < currentIndex) dot.textContent = '✓';
            });
        }

        function getCurrentStepIndex() {
            // Get from API status
            return parseInt(document.getElementById('guided-progress-text').textContent.split(' ')[1]) || 1;
        }

        function completeGuidedMode() {
            updateNarratorText('Congratulations! Your SLATE development environment is fully operational. Welcome to synchronized living architecture!');
            document.getElementById('guided-action-title').textContent = 'Setup Complete!';
            document.getElementById('guided-action-status').innerHTML = '<span style="font-size: 2rem;">🎉</span>';

            // Mark all steps complete
            document.querySelectorAll('.guided-step-dot').forEach(dot => {
                dot.className = 'guided-step-dot complete';
                dot.textContent = '✓';
            });
        }

        function exitGuidedMode() {
            guidedModeActive = false;
            document.getElementById('guided-overlay').classList.remove('active');
            fetch('/api/guided/reset', { method: 'POST' });
        }

        // ═══════════════════════════════════════════════════════════════════════════
        // BROCHURE UI FUNCTIONS
        // ═══════════════════════════════════════════════════════════════════════════

        function hideHero() {
            document.getElementById('brochure-hero').style.display = 'none';
            localStorage.setItem('slate_hero_hidden', 'true');
        }

        function checkHeroVisibility() {
            if (localStorage.getItem('slate_hero_hidden') === 'true') {
                document.getElementById('brochure-hero').style.display = 'none';
            }
        }

        // Check hero visibility on load
        checkHeroVisibility();

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

            // Stats (deprecated - now shown in individual panels)
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
                            <div class="task-item-actions">
                                ${t.status !== 'completed' ? `<button class="task-action-btn" onclick="updateTaskStatus('${t.id}', '${t.status === 'pending' ? 'in-progress' : 'completed'}')" aria-label="Advance task status">${t.status === 'pending' ? '\u25B6' : '\u2713'}</button>` : ''}
                                <button class="task-action-btn delete" onclick="deleteTask('${t.id}')" aria-label="Delete task">\u2715</button>
                            </div>
                            <span class="badge ${t.status === 'completed' ? 'online' : t.status === 'in-progress' ? 'busy' : 'pending'}">
                                ${t.status || 'pending'}
                            </span>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<div class="empty-state">No tasks in queue</div>';
                }
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
                            <div class="gpu-icon" aria-hidden="true">G</div>
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

        // Create Task
        async function createTask() {
            const titleInput = document.getElementById('new-task-title');
            const prioritySelect = document.getElementById('new-task-priority');
            const title = titleInput.value.trim();
            if (!title) return;

            try {
                const res = await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title: title, priority: parseInt(prioritySelect.value), status: 'pending' })
                });
                const data = await res.json();
                if (data.success !== false) {
                    titleInput.value = '';
                    refreshTasks();
                } else {
                    console.error('Failed to create task:', data.error);
                }
            } catch (e) {
                console.error('Failed to create task:', e);
            }
        }

        // Delete Task
        async function deleteTask(taskId) {
            try {
                await fetch(`/api/tasks/${taskId}`, { method: 'DELETE' });
                refreshTasks();
            } catch (e) {
                console.error('Failed to delete task:', e);
            }
        }

        // Update Task Status
        async function updateTaskStatus(taskId, newStatus) {
            try {
                await fetch(`/api/tasks/${taskId}`, {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ status: newStatus })
                });
                refreshTasks();
            } catch (e) {
                console.error('Failed to update task:', e);
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

        // Tech Tree Rendering (Dynamic from API)
        let techTreeScale = 1;
        let techTreeTranslateX = 0;
        let techTreeTranslateY = 0;
        let techTreeData = { nodes: [], edges: [] };

        async function refreshTechTree() {
            try {
                const res = await fetch('/api/tech-tree');
                const data = await res.json();
                techTreeData = data;

                // Update stats
                const byStatus = data.by_status || {};
                document.getElementById('tree-complete').textContent = byStatus.complete || 0;
                document.getElementById('tree-progress').textContent = byStatus.in_progress || 0;
                document.getElementById('tree-available').textContent = byStatus.available || 0;

                renderTechTree();
            } catch (e) {
                console.error('Failed to fetch tech tree:', e);
            }
        }

        function renderTechTree() {
            const svg = document.getElementById('tech-tree-svg');
            const container = document.getElementById('tech-tree-container');
            const width = container.clientWidth || 900;
            const height = container.clientHeight || 450;

            const nodes = techTreeData.nodes || [];
            const edges = techTreeData.edges || [];

            if (nodes.length === 0) {
                svg.innerHTML = '<text x="50%" y="50%" text-anchor="middle" fill="var(--text-muted)">Loading tech tree...</text>';
                return;
            }

            // Calculate positions based on phase and dependencies
            const nodePositions = calculateNodePositions(nodes, edges, width, height);

            let html = `<g transform="translate(${techTreeTranslateX},${techTreeTranslateY}) scale(${techTreeScale})">`;

            // Draw phase backgrounds
            const phases = [...new Set(nodes.map(n => n.phase))].sort();
            phases.forEach((phase, idx) => {
                const phaseNodes = nodes.filter(n => n.phase === phase);
                const minY = Math.min(...phaseNodes.map(n => nodePositions[n.id]?.y || 0)) - 40;
                const maxY = Math.max(...phaseNodes.map(n => nodePositions[n.id]?.y || 0)) + 50;
                const color = phase === 1 ? 'rgba(34,197,94,0.03)' : 'rgba(250,204,21,0.03)';
                html += `<rect x="10" y="${minY}" width="${width - 40}" height="${maxY - minY}" fill="${color}" rx="8"/>`;
                html += `<text x="20" y="${minY + 16}" fill="var(--text-muted)" font-size="10" font-weight="600">PHASE ${phase}</text>`;
            });

            // Draw edges (links)
            edges.forEach(edge => {
                const fromPos = nodePositions[edge.from];
                const toPos = nodePositions[edge.to];
                if (fromPos && toPos) {
                    const fromNode = nodes.find(n => n.id === edge.from);
                    const toNode = nodes.find(n => n.id === edge.to);
                    const unlocked = toNode && toNode.status !== 'locked' ? ' unlocked' : '';
                    html += `<line class="tech-link${unlocked}" x1="${fromPos.x}" y1="${fromPos.y}" x2="${toPos.x}" y2="${toPos.y}" stroke-width="2"/>`;
                }
            });

            // Draw nodes
            nodes.forEach(node => {
                const pos = nodePositions[node.id];
                if (!pos) return;

                const statusClass = node.status === 'complete' ? 'completed' : node.status;
                const desc = (node.description || '').replace(/'/g, "\\\\'");
                html += `<g class="tech-node ${statusClass}" onmouseenter="showTechTooltip(event, '${node.name}', '${node.status}', '${desc}', ${node.phase})" onmouseleave="hideTechTooltip()">`;
                html += `<circle cx="${pos.x}" cy="${pos.y}" r="24"/>`;

                const icon = node.status === 'complete' ? '\\u2713' : node.status === 'in_progress' ? '\\u25CB' : node.status === 'available' ? '\\u25CE' : '\\u25CF';
                html += `<text x="${pos.x}" y="${pos.y + 5}" fill="var(--text-primary)" font-size="14" text-anchor="middle">${icon}</text>`;
                html += `<text x="${pos.x}" y="${pos.y + 42}" fill="var(--text-secondary)" font-size="9" text-anchor="middle" font-weight="500">${node.name}</text>`;
                html += '</g>';
            });

            html += '</g>';
            svg.innerHTML = html;
        }

        function calculateNodePositions(nodes, edges, width, height) {
            const positions = {};
            const phases = [...new Set(nodes.map(n => n.phase))].sort();
            const phaseHeight = (height - 80) / phases.length;

            // Group nodes by phase
            phases.forEach((phase, phaseIdx) => {
                const phaseNodes = nodes.filter(n => n.phase === phase);
                const y = 60 + phaseIdx * phaseHeight;
                const xSpacing = (width - 60) / (phaseNodes.length + 1);

                phaseNodes.forEach((node, nodeIdx) => {
                    positions[node.id] = {
                        x: 30 + xSpacing * (nodeIdx + 1),
                        y: y
                    };
                });
            });

            return positions;
        }

        function showTechTooltip(event, title, status, desc, phase) {
            const tooltip = document.getElementById('tech-tooltip');
            const label = status === 'complete' ? 'Complete' : status === 'in_progress' ? 'In Progress' : status === 'available' ? 'Available' : 'Locked';
            tooltip.querySelector('.tech-tooltip-title').textContent = title;
            tooltip.querySelector('.tech-tooltip-desc').textContent = desc || 'No description';
            const phaseEl = tooltip.querySelector('.tech-tooltip-phase');
            if (phaseEl) phaseEl.textContent = 'Phase ' + phase + ' | ' + label;
            tooltip.style.left = (event.clientX + 12) + 'px';
            tooltip.style.top = (event.clientY - 60) + 'px';
            tooltip.classList.add('visible');
        }

        function hideTechTooltip() {
            document.getElementById('tech-tooltip').classList.remove('visible');
        }

        function zoomTechTree(factor) {
            techTreeScale = Math.max(0.5, Math.min(2.0, techTreeScale * factor));
            renderTechTree();
        }

        function resetTechTree() {
            techTreeScale = 1;
            techTreeTranslateX = 0;
            techTreeTranslateY = 0;
            renderTechTree();
        }

        // ─── SLATE Integration Functions ────────────────────────────────────
        async function refreshAgents() {
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                document.getElementById('agent-total').textContent = data.total || 0;
                document.getElementById('agent-gpu').textContent = data.gpu_agents || 0;
                document.getElementById('agent-cpu').textContent = data.cpu_agents || 0;
                const list = document.getElementById('agent-list');
                if (data.agents && data.agents.length > 0) {
                    list.innerHTML = data.agents.map(a => '<div style="display: flex; align-items: center; gap: 12px; padding: 10px 12px; background: rgba(0,0,0,0.2); border-radius: 8px; margin-bottom: 6px; border-left: 3px solid ' + (a.requires_gpu ? 'var(--status-success)' : 'var(--text-muted)') + ';"><div style="width: 36px; height: 36px; background: rgba(255,255,255,0.08); border-radius: 6px; display: flex; align-items: center; justify-content: center; font-weight: 700; font-family: Consolas; font-size: 0.75rem;">' + a.id.substring(0,2) + '</div><div style="flex: 1;"><div style="font-size: 0.8rem; font-weight: 500;">' + a.name + '</div><div style="font-size: 0.65rem; color: var(--text-muted);">' + (a.description || '') + '</div></div><div style="font-size: 0.65rem; color: var(--text-muted); font-family: Consolas;">v' + a.version + '</div></div>').join('');
                } else { list.innerHTML = '<div class="empty-state">No agents</div>'; }
            } catch (e) { console.error('refreshAgents:', e); }
        }
        async function refreshMultiRunner() {
            try {
                const res = await fetch('/api/multirunner');
                const data = await res.json();
                document.getElementById('runner-total').textContent = data.total || 0;
                document.getElementById('runner-running').textContent = data.running || 0;
                document.getElementById('runner-idle').textContent = data.idle || 0;
                document.getElementById('runner-parallel').textContent = data.max_parallel || 0;
                const list = document.getElementById('multirunner-list');
                if (data.runners && data.runners.length > 0) {
                    const dr = data.runners.slice(0, 8);
                    list.innerHTML = '<div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px;">' + dr.map(r => '<div style="padding: 8px; background: rgba(0,0,0,0.2); border-radius: 6px; text-align: center; border-top: 2px solid ' + (r.status === 'running' ? 'var(--status-success)' : 'var(--text-muted)') + ';"><div style="font-size: 0.7rem; font-weight: 500; font-family: Consolas;">' + r.id + '</div><div style="font-size: 0.6rem; color: var(--text-muted);">' + r.profile + '</div></div>').join('') + '</div>' + (data.runners.length > 8 ? '<div style="font-size: 0.7rem; color: var(--text-muted); text-align: center; margin-top: 8px;">+ ' + (data.runners.length - 8) + ' more</div>' : '');
                } else { list.innerHTML = '<div class="empty-state">No runners</div>'; }
            } catch (e) { console.error('refreshMultiRunner:', e); }
        }
        async function refreshWorkflowStats() {
            try {
                const res = await fetch('/api/workflow-stats');
                const data = await res.json();
                document.getElementById('wf-total').textContent = data.total || 0;
                document.getElementById('wf-concurrency').textContent = data.with_concurrency || 0;
                document.getElementById('wf-success').textContent = data.run_stats?.success || 0;
                document.getElementById('wf-failure').textContent = data.run_stats?.failure || 0;
                const list = document.getElementById('workflow-stats-list');
                if (data.workflows && data.workflows.length > 0) {
                    list.innerHTML = data.workflows.slice(0, 10).map(w => '<div style="display: flex; align-items: center; gap: 8px; padding: 6px 10px; background: rgba(0,0,0,0.2); border-radius: 6px; margin-bottom: 4px; font-size: 0.75rem;"><span style="width: 8px; height: 8px; border-radius: 50%; background: ' + (w.has_concurrency ? 'var(--status-success)' : 'var(--text-muted)') + ';"></span><span style="flex: 1; font-weight: 500;">' + w.name + '</span><span style="color: var(--text-muted); font-size: 0.65rem;">' + w.triggers.join(', ') + '</span></div>').join('');
                } else { list.innerHTML = '<div class="empty-state">No workflows</div>'; }
            } catch (e) { console.error('refreshWorkflowStats:', e); }
        }
        async function refreshSpecs() {
            try {
                const res = await fetch('/api/specs');
                const data = await res.json();
                document.getElementById('spec-total').textContent = data.total || 0;
                document.getElementById('spec-complete').textContent = data.by_status?.complete || 0;
                document.getElementById('spec-implementing').textContent = data.by_status?.implementing || 0;
                document.getElementById('spec-draft').textContent = data.by_status?.draft || 0;
                const list = document.getElementById('spec-list');
                if (data.specs && data.specs.length > 0) {
                    list.innerHTML = data.specs.map(s => { const sc = s.status === 'complete' ? 'var(--status-success)' : 'var(--text-muted)'; const p = s.tasks_total > 0 ? Math.round((s.tasks_completed / s.tasks_total) * 100) : 0; return '<div style="padding: 8px 10px; background: rgba(0,0,0,0.2); border-radius: 6px; margin-bottom: 6px; border-left: 3px solid ' + sc + ';"><div style="display: flex; align-items: center; justify-content: space-between;"><span style="font-size: 0.8rem; font-weight: 500;">' + s.id + '</span><span style="font-size: 0.65rem; color: ' + sc + '; text-transform: uppercase;">' + s.status + '</span></div>' + (s.tasks_total > 0 ? '<div style="margin-top: 6px;"><div style="height: 4px; background: rgba(255,255,255,0.1); border-radius: 2px;"><div style="height: 100%; width: ' + p + '%; background: ' + sc + '; border-radius: 2px;"></div></div><div style="font-size: 0.6rem; color: var(--text-muted); margin-top: 2px;">' + s.tasks_completed + '/' + s.tasks_total + '</div></div>' : '') + '</div>'; }).join('');
                } else { list.innerHTML = '<div class="empty-state">No specs</div>'; }
            } catch (e) { console.error('refreshSpecs:', e); }
        }
        async function refreshForks() {
            try {
                const res = await fetch('/api/forks');
                const data = await res.json();
                const list = document.getElementById('fork-list');
                if (data.forks && data.forks.length > 0) {
                    list.innerHTML = data.forks.map(f => '<div style="padding: 12px; background: rgba(0,0,0,0.2); border-radius: 8px; border-left: 3px solid ' + (f.has_git ? 'var(--status-success)' : 'var(--text-muted)') + ';"><div style="font-size: 0.875rem; font-weight: 600; margin-bottom: 4px;">' + f.name + '</div>' + (f.last_message ? '<div style="font-size: 0.7rem; color: var(--text-secondary); margin-bottom: 4px;">' + f.last_message + '</div>' : '') + '<div style="display: flex; gap: 12px; font-size: 0.65rem; color: var(--text-muted);">' + (f.last_commit ? '<span>#' + f.last_commit + '</span>' : '') + (f.last_updated ? '<span>' + f.last_updated + '</span>' : '') + '</div></div>').join('');
                } else { list.innerHTML = '<div class="empty-state" style="grid-column: 1/-1;">No forks</div>'; }
            } catch (e) { console.error('refreshForks:', e); }
        }

        // ─── SLATE Control Panel JS ─────────────────────────────────
        async function runSlateControl(action, btn) {
            if (btn.classList.contains('running')) return;
            btn.classList.remove('success', 'error');
            btn.classList.add('running');
            const output = document.getElementById('ctrl-output');
            output.classList.add('visible');
            output.innerHTML = `<span class="step-label">Running ${action}...</span>\\n`;
            try {
                const res = await fetch('/api/slate/' + action, { method: 'POST' });
                const data = await res.json();
                btn.classList.remove('running');
                if (data.steps) {
                    let html = '';
                    data.steps.forEach(s => {
                        const icon = s.success ? '<span class="step-ok">&#10003;</span>' : '<span class="step-err">&#10007;</span>';
                        html += `${icon} <span class="step-label">${s.step}</span>\\n`;
                        if (s.output) html += s.output + '\\n';
                        if (s.error) html += `<span class="step-err">${s.error}</span>\\n`;
                    });
                    output.innerHTML = html;
                    btn.classList.add(data.success ? 'success' : 'error');
                } else {
                    output.innerHTML = data.success
                        ? `<span class="step-ok">&#10003;</span> <span class="step-label">${action}</span>\\n${data.output || 'Done'}`
                        : `<span class="step-err">&#10007;</span> <span class="step-label">${action}</span>\\n${data.error || 'Failed'}`;
                    btn.classList.add(data.success ? 'success' : 'error');
                }
                updateCtrlDot('ctrl-dot-' + action.replace('run-protocol','protocol'), data.success);
            } catch (e) {
                btn.classList.remove('running');
                btn.classList.add('error');
                output.innerHTML = `<span class="step-err">&#10007; Network error: ${e.message}</span>`;
                updateCtrlDot('ctrl-dot-' + action.replace('run-protocol','protocol'), false);
            }
        }

        async function runSlateControlDeploy(deployAction, btn) {
            if (btn.classList.contains('running')) return;
            btn.classList.remove('success', 'error');
            btn.classList.add('running');
            const output = document.getElementById('ctrl-output');
            output.classList.add('visible');
            output.innerHTML = `<span class="step-label">Services: ${deployAction}...</span>\\n`;
            try {
                const res = await fetch('/api/slate/deploy/' + deployAction, { method: 'POST' });
                const data = await res.json();
                btn.classList.remove('running');
                output.innerHTML = data.success
                    ? `<span class="step-ok">&#10003;</span> <span class="step-label">Services ${deployAction}</span>\\n${data.output || 'Done'}`
                    : `<span class="step-err">&#10007;</span> <span class="step-label">Services ${deployAction}</span>\\n${data.error || 'Failed'}`;
                btn.classList.add(data.success ? 'success' : 'error');
                updateCtrlDot('ctrl-dot-deploy', data.success);
            } catch (e) {
                btn.classList.remove('running');
                btn.classList.add('error');
                output.innerHTML = `<span class="step-err">&#10007; ${e.message}</span>`;
            }
        }

        function updateCtrlDot(id, ok) {
            const dot = document.getElementById(id);
            if (dot) {
                dot.className = 'ctrl-status ' + (ok ? 'ok' : 'err');
            }
        }

        function toggleControlOutput() {
            const el = document.getElementById('ctrl-output');
            el.classList.toggle('visible');
        }

        // Deploy button context menu (right-click for stop/status)
        document.getElementById('ctrl-deploy')?.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const action = prompt('Services action:', 'stop');
            if (action && ['start','stop','status'].includes(action)) {
                runSlateControlDeploy(action, this);
            }
        });

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
            refreshTechTree();
            refreshAgents();
            refreshMultiRunner();
            refreshWorkflowStats();
            refreshSpecs();
            refreshForks();
            refreshDocker();
            refreshHardwareControl();
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
        loadTheme();
        loadBenchmarkHistory();
        refreshArchitecture();  // Load architecture diagram status

        // Try WebSocket, but polling will keep working regardless
        try {
            connectWebSocket();
        } catch (e) {
            console.log('WebSocket failed, using polling only');
        }

        // More frequent polling for VSCode webview compatibility (every 10s)
        setInterval(refreshAll, 10000);

        // Hardware monitoring at higher frequency (every 5s)
        setInterval(refreshHardwareControl, 5000);
    </script>
</body>
</html>
"""

# Modified: 2026-02-07T10:30:00Z | Author: COPILOT | Change: Use new M3/Awwwards template builder
@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the SLATE dashboard with M3/Awwwards design."""
    try:
        from slate_web.dashboard_template import get_full_template
        return get_full_template()
    except Exception:
        # Fallback to legacy template if the new builder fails
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
