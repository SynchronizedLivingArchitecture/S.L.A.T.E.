#!/usr/bin/env python3
# Modified: 2026-02-06T19:00:00Z | Author: COPILOT | Change: New install API for dashboard integration
"""
SLATE Install API
=================
Provides HTTP + SSE endpoints for the SLATE Dashboard to display
real-time installation progress. Mounted into the dashboard server
or run standalone as a lightweight installer-GUI server.

Endpoints:
    GET  /api/install/status    → Current install state JSON
    GET  /api/install/log       → Install log lines
    GET  /api/install/events    → SSE stream of install events
    GET  /api/install/steps     → Step definitions with metadata
    POST /api/install/start     → Trigger install (standalone mode)
    GET  /install               → Install progress dashboard HTML
"""

import asyncio
import json
import os
import queue
import sys
import threading
from datetime import datetime
from pathlib import Path
from typing import Any

WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))


# ─── SSE Queue for async broadcasting ─────────────────────────────────────────
_event_queues: list = []
_queue_lock = threading.Lock()


def _sse_callback(event_type: str, data: dict):
    """Called by InstallTracker when an event occurs."""
    msg = json.dumps({"event": event_type, "data": data, "ts": datetime.now().isoformat()})
    with _queue_lock:
        dead = []
        for q in _event_queues:
            try:
                q.put_nowait(msg)
            except Exception:
                dead.append(q)
        for d in dead:
            _event_queues.remove(d)


def _register_tracker_sse():
    """Wire install_tracker SSE to our queue broadcaster."""
    try:
        from aurora_core.install_tracker import register_sse_listener
        register_sse_listener(_sse_callback)
    except ImportError:
        pass


# Auto-register on import
_register_tracker_sse()


# ─── API Route Registration (for FastAPI dashboard server) ─────────────────────

def add_install_endpoints(app):
    """Register install API endpoints on a FastAPI app instance.

    Called by aurora_dashboard_server.py to mount install tracking
    into the main dashboard.
    """
    from fastapi import Request
    from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse, FileResponse

    @app.get("/api/install/status")
    async def install_status():
        """Return current installation state."""
        from aurora_core.install_tracker import InstallTracker
        state = InstallTracker.load_state()
        if state:
            return JSONResponse(content=state)
        return JSONResponse(content={
            "status": "not_started",
            "message": "No installation in progress or recorded",
            "steps": [],
        })

    @app.get("/api/install/log")
    async def install_log():
        """Return install log lines."""
        from aurora_core.install_tracker import InstallTracker
        lines = InstallTracker.get_install_log()
        return JSONResponse(content={"lines": lines, "count": len(lines)})

    @app.get("/api/install/steps")
    async def install_steps():
        """Return step definitions with metadata."""
        from aurora_core.install_tracker import InstallTracker
        steps = []
        for s in InstallTracker.INSTALL_STEPS:
            steps.append({
                "id": s.id,
                "name": s.name,
                "description": s.description,
                "order": s.order,
            })
        return JSONResponse(content={"steps": steps, "total": len(steps)})

    @app.get("/api/install/events")
    async def install_events(request: Request):
        """SSE endpoint — streams install events in real-time."""
        q = queue.Queue(maxsize=200)
        with _queue_lock:
            _event_queues.append(q)

        async def event_generator():
            try:
                # Send initial state
                from aurora_core.install_tracker import InstallTracker
                state = InstallTracker.load_state()
                if state:
                    yield f"event: init\ndata: {json.dumps(state)}\n\n"

                while True:
                    if await request.is_disconnected():
                        break
                    try:
                        msg = q.get_nowait()
                        yield f"event: update\ndata: {msg}\n\n"
                    except queue.Empty:
                        # Send keepalive every 2s
                        yield f"event: ping\ndata: {{}}\n\n"
                        await asyncio.sleep(2)
            finally:
                with _queue_lock:
                    if q in _event_queues:
                        _event_queues.remove(q)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    @app.get("/install")
    async def install_page():
        """Serve the install progress dashboard page."""
        install_html = os.path.join(WORKSPACE_ROOT, "aurora_slate", "install.html")
        if os.path.exists(install_html):
            return FileResponse(install_html, media_type="text/html", headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
            })
        # Inline fallback — minimal install viewer
        return HTMLResponse(_FALLBACK_INSTALL_HTML)


# ─── Standalone Lightweight Server ─────────────────────────────────────────────

def create_standalone_app():
    """Create a minimal FastAPI app for install-time dashboard.

    This runs BEFORE the full dashboard server is ready (since we need
    to install dependencies first). Uses only stdlib + fastapi/uvicorn
    which are installed as the very first step.
    """
    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import HTMLResponse, JSONResponse, StreamingResponse
    except ImportError:
        return None

    standalone = FastAPI(title="SLATE Installer")

    add_install_endpoints(standalone)

    # Root serves install page directly
    @standalone.get("/")
    async def root():
        install_html = os.path.join(WORKSPACE_ROOT, "aurora_slate", "install.html")
        if os.path.exists(install_html):
            from fastapi.responses import FileResponse
            return FileResponse(install_html, media_type="text/html")
        return HTMLResponse(_FALLBACK_INSTALL_HTML)

    return standalone


def run_standalone_server(port: int = 8080):
    """Run the standalone install dashboard server."""
    app = create_standalone_app()
    if not app:
        print("[SLATE] Cannot start install dashboard — FastAPI not available")
        return None

    import uvicorn
    import threading

    def _serve():
        uvicorn.run(app, host="127.0.0.1", port=port, log_level="warning")

    t = threading.Thread(target=_serve, daemon=True, name="slate-install-dashboard")
    t.start()
    return t


# ─── Fallback HTML ─────────────────────────────────────────────────────────────

_FALLBACK_INSTALL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>S.L.A.T.E. — Installing</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#08090b;color:#d4d4d8;font-family:'Segoe UI',system-ui,sans-serif;min-height:100vh;display:flex;justify-content:center;align-items:center}
.container{max-width:680px;width:100%;padding:2rem}
h1{font-size:1.6rem;font-weight:600;color:#a78bfa;margin-bottom:0.25rem}
.subtitle{color:#71717a;font-size:0.875rem;margin-bottom:2rem}
.step{display:flex;align-items:center;gap:1rem;padding:0.75rem 1rem;border-radius:8px;margin-bottom:0.5rem;background:#111114;border:1px solid #1e1e24;transition:all 0.3s}
.step.running{border-color:#a78bfa;background:#13111f}
.step.success{border-color:#22c55e40;background:#0a1a10}
.step.failed{border-color:#ef444440;background:#1a0a0a}
.step.warning{border-color:#eab30840;background:#1a1a0a}
.icon{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:14px;flex-shrink:0}
.icon.pending{background:#27272a;color:#52525b}
.icon.running{background:#a78bfa30;color:#a78bfa;animation:pulse 1.5s infinite}
.icon.success{background:#22c55e20;color:#22c55e}
.icon.failed{background:#ef444420;color:#ef4444}
.icon.warning{background:#eab30820;color:#eab308}
.icon.skipped{background:#27272a;color:#52525b}
.info{flex:1}
.info .name{font-weight:500;font-size:0.9rem}
.info .detail{font-size:0.75rem;color:#71717a;margin-top:2px}
.progress-bar{height:3px;background:#27272a;border-radius:2px;margin-top:4px;overflow:hidden}
.progress-fill{height:100%;background:linear-gradient(90deg,#a78bfa,#818cf8);border-radius:2px;transition:width 0.5s}
.summary{margin-top:2rem;padding:1rem;border-radius:8px;background:#111114;border:1px solid #1e1e24;font-size:0.85rem}
.log-section{margin-top:1.5rem;max-height:200px;overflow-y:auto;padding:0.75rem;background:#0a0a0c;border-radius:6px;font-family:monospace;font-size:0.75rem;line-height:1.6}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:0.5}}
</style>
</head>
<body>
<div class="container">
  <h1>S.L.A.T.E. Installation</h1>
  <p class="subtitle">System Learning Agent for Task Execution</p>
  <div id="steps"></div>
  <div class="summary" id="summary">Waiting for installation to start...</div>
  <div class="log-section" id="log"></div>
</div>
<script>
const ICONS = {pending:'○',running:'◉',success:'✓',failed:'✗',warning:'⚠',skipped:'–'};
let state = null;

function renderSteps(steps) {
  const el = document.getElementById('steps');
  el.innerHTML = steps.map(s => `
    <div class="step ${s.status}">
      <div class="icon ${s.status}">${ICONS[s.status] || '○'}</div>
      <div class="info">
        <div class="name">${s.name}</div>
        <div class="detail">${s.details || s.description || ''}</div>
        ${s.status === 'running' ? `<div class="progress-bar"><div class="progress-fill" style="width:${s.progress_pct||10}%"></div></div>` : ''}
      </div>
    </div>
  `).join('');
}

function renderSummary(st) {
  const el = document.getElementById('summary');
  if (st.status === 'not_started') { el.textContent = 'Waiting for installation to start...'; return; }
  if (st.status === 'in_progress') {
    const done = st.steps.filter(s=>['success','warning','skipped'].includes(s.status)).length;
    el.innerHTML = `<strong>Installing...</strong> ${done}/${st.steps.length} steps complete`;
    return;
  }
  const ok = st.steps.filter(s=>s.status==='success').length;
  const fail = st.steps.filter(s=>s.status==='failed').length;
  if (st.status === 'completed') {
    el.innerHTML = `<strong style="color:#22c55e">✓ Installation Complete</strong> — ${ok} passed, ${fail} failed<br>
    <span style="color:#71717a;font-size:0.8rem">SLATE v${st.slate_version || '?'} | ${st.git_info?.branch || '?'} @ ${st.git_info?.commit || '?'}</span>`;
  } else {
    el.innerHTML = `<strong style="color:#ef4444">✗ Installation Failed</strong> — ${ok} passed, ${fail} failed`;
  }
}

function renderLog(lines) {
  const el = document.getElementById('log');
  el.innerHTML = (lines || []).map(l => `<div>${l}</div>`).join('');
  el.scrollTop = el.scrollHeight;
}

async function poll() {
  try {
    const r = await fetch('/api/install/status');
    if (r.ok) {
      state = await r.json();
      if (state.steps && state.steps.length > 0) renderSteps(state.steps);
      renderSummary(state);
      if (state.log) renderLog(state.log);
    }
  } catch(e) {}
}

// Try SSE first, fall back to polling
let useSSE = true;
function connectSSE() {
  const es = new EventSource('/api/install/events');
  es.addEventListener('init', e => {
    state = JSON.parse(e.data);
    if (state.steps) renderSteps(state.steps);
    renderSummary(state);
    if (state.log) renderLog(state.log);
  });
  es.addEventListener('update', e => { poll(); });
  es.addEventListener('ping', () => {});
  es.onerror = () => { es.close(); useSSE = false; setInterval(poll, 2000); };
}

// Init
poll();
connectSSE();
</script>
</body>
</html>"""


if __name__ == "__main__":
    print("[SLATE] Starting standalone install dashboard on http://127.0.0.1:8080")
    run_standalone_server(8080)
    import time
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[SLATE] Install dashboard stopped")
