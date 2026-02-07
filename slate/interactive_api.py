#!/usr/bin/env python3
# Modified: 2026-02-07T15:15:00Z | Author: COPILOT | Change: Initial creation of interactive API router
"""
Interactive API Router - FastAPI endpoints for SLATE interactive experience.

Provides REST API endpoints for:
- Learning paths and progress (InteractiveTutor)
- Development cycle management (DevCycleEngine)
- Feedback and insights (ClaudeFeedbackLayer)

Mount this router in the dashboard server to enable all interactive features.
"""

import logging
import sys
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

from slate.dev_cycle_engine import (
    DevCycleEngine,
    DevCycleStage,
    StageActivity,
    ActivityStatus,
    get_engine as get_dev_cycle_engine,
)
from slate.interactive_tutor import (
    InteractiveTutor,
    get_tutor,
)
from slate.claude_feedback_layer import (
    ClaudeFeedbackLayer,
    ToolEvent,
    FeedbackEvent,
    EventType,
    get_feedback_layer,
)

logger = logging.getLogger("slate.interactive_api")


# ── Pydantic Models ─────────────────────────────────────────────────────────


# Learning Models
class StartSessionRequest(BaseModel):
    path_id: str = Field(..., description="Learning path ID to start")


class CompleteStepRequest(BaseModel):
    step_id: str = Field(..., description="Step ID to complete")
    result: dict = Field(default_factory=dict, description="Step completion result")


class AIExplainRequest(BaseModel):
    topic: str = Field(..., description="Topic to explain")
    context: dict = Field(default_factory=dict, description="Additional context")


# Dev Cycle Models
class TransitionRequest(BaseModel):
    to_stage: str = Field(..., description="Target stage (PLAN, CODE, TEST, DEPLOY, FEEDBACK)")


class AddActivityRequest(BaseModel):
    stage: str = Field(..., description="Stage for the activity")
    title: str = Field(..., description="Activity title")
    description: str = Field(default="", description="Activity description")


class UpdateActivityRequest(BaseModel):
    status: str = Field(..., description="New status (pending, in_progress, completed, failed)")
    progress_percent: Optional[int] = Field(None, description="Progress percentage 0-100")
    metrics: Optional[dict] = Field(None, description="Additional metrics")


# Feedback Models
class ToolEventRequest(BaseModel):
    tool_name: str = Field(..., description="Name of the tool")
    tool_input: dict = Field(..., description="Tool input parameters")
    tool_output: Optional[str] = Field(None, description="Tool output")
    success: bool = Field(True, description="Whether the tool succeeded")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    duration_ms: int = Field(0, description="Execution duration in milliseconds")
    session_id: Optional[str] = Field(None, description="Session ID")


class RecoveryRequest(BaseModel):
    error: str = Field(..., description="Error message to recover from")
    context: Optional[dict] = Field(None, description="Additional context")


# ── Learning Router ─────────────────────────────────────────────────────────

learning_router = APIRouter(prefix="/api/interactive", tags=["Learning"])


@learning_router.get("/paths")
async def list_learning_paths():
    """List all available learning paths."""
    tutor = get_tutor()
    paths = tutor.get_learning_paths()
    progress = tutor.get_progress()

    result = []
    for path in paths:
        completed_in_path = len([
            sid for sid in progress.completed_steps
            if sid.startswith(path["id"])
        ])
        step_count = path.get("step_count", 0)  # Use step_count, not total_steps
        result.append({
            **path,
            "completed_steps": completed_in_path,
            "progress_percent": int(completed_in_path / step_count * 100)
            if step_count > 0 else 0,
        })

    return {"paths": result}


@learning_router.post("/start")
async def start_learning_session(request: StartSessionRequest):
    """Start a new learning session."""
    tutor = get_tutor()
    result = await tutor.start_learning_session(request.path_id)
    return result


@learning_router.get("/progress")
async def get_learning_progress():
    """Get current learning progress."""
    tutor = get_tutor()
    progress = tutor.get_progress()
    return {
        "completed_steps": list(progress.completed_steps),
        "achievements": [a.to_dict() for a in progress.achievements],
        "total_xp": progress.total_xp,
        "level": tutor.calculate_level(progress.total_xp),
        "streak_days": progress.streak_days,
        "last_activity": progress.last_activity,
    }


@learning_router.get("/current-step")
async def get_current_step():
    """Get the current learning step."""
    tutor = get_tutor()
    step = await tutor.get_next_step()
    if step is None:
        return {"step": None, "message": "No active learning session or path completed"}
    return {"step": step.to_dict()}


@learning_router.post("/complete-step")
async def complete_step(request: CompleteStepRequest):
    """Complete a learning step."""
    tutor = get_tutor()
    result = await tutor.complete_step(request.step_id, request.result)
    return result


@learning_router.get("/achievements")
async def get_achievements():
    """Get all achievements and unlock status."""
    tutor = get_tutor()
    all_achievements = tutor.get_all_achievements()
    unlocked = {a.id for a in tutor.get_progress().achievements}

    return {
        "achievements": [
            {
                **a.to_dict(),
                "unlocked": a.id in unlocked,
            }
            for a in all_achievements
        ]
    }


@learning_router.post("/ai-explain")
async def get_ai_explanation(request: AIExplainRequest):
    """Get an AI-powered explanation for a topic."""
    tutor = get_tutor()
    explanation = await tutor.get_ai_explanation(request.topic, request.context)
    return {"topic": request.topic, "explanation": explanation}


@learning_router.get("/hints/{step_id}")
async def get_step_hints(step_id: str, reveal_count: int = Query(1, ge=1, le=5)):
    """Get hints for a learning step."""
    tutor = get_tutor()
    hints = tutor.get_hints(step_id, reveal_count)
    return {"step_id": step_id, "hints": hints, "revealed": reveal_count}


# ── Dev Cycle Router ────────────────────────────────────────────────────────

devcycle_router = APIRouter(prefix="/api/devcycle", tags=["Development Cycle"])


@devcycle_router.get("/state")
async def get_cycle_state():
    """Get current development cycle state."""
    engine = get_dev_cycle_engine()
    state = await engine.get_current_state()
    return state.to_dict()


@devcycle_router.post("/transition")
async def transition_stage(request: TransitionRequest):
    """Transition to a new development stage."""
    try:
        # Enum values are lowercase (plan, code, etc.)
        to_stage = DevCycleStage(request.to_stage.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {request.to_stage}. "
            f"Valid: {[s.value for s in DevCycleStage]}"
        )

    engine = get_dev_cycle_engine()
    result = await engine.transition_stage(to_stage)
    return result


@devcycle_router.get("/activities/{stage}")
async def get_stage_activities(stage: str):
    """Get activities for a specific stage."""
    try:
        stage_enum = DevCycleStage(stage.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {stage}"
        )

    engine = get_dev_cycle_engine()
    activities = await engine.get_stage_activities(stage_enum)
    return {"stage": stage, "activities": [a.to_dict() for a in activities]}


@devcycle_router.post("/activity")
async def add_activity(request: AddActivityRequest):
    """Add a new activity to a stage."""
    try:
        stage = DevCycleStage(request.stage.upper())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid stage: {request.stage}"
        )

    engine = get_dev_cycle_engine()
    import uuid
    activity = StageActivity(
        id=str(uuid.uuid4())[:8],
        stage=stage,
        title=request.title,
        description=request.description,
    )
    await engine.add_activity(activity)
    return {"success": True, "activity": activity.to_dict()}


@devcycle_router.put("/activity/{activity_id}")
async def update_activity(activity_id: str, request: UpdateActivityRequest):
    """Update an existing activity."""
    try:
        status = ActivityStatus(request.status.lower())
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid status: {request.status}"
        )

    engine = get_dev_cycle_engine()
    result = await engine.update_activity(
        activity_id,
        status=status,
        progress_percent=request.progress_percent,
        metrics=request.metrics,
    )
    return result


@devcycle_router.delete("/activity/{activity_id}")
async def complete_activity(activity_id: str):
    """Mark an activity as completed."""
    engine = get_dev_cycle_engine()
    result = await engine.complete_activity(activity_id)
    return result


@devcycle_router.get("/visualization")
async def get_visualization_data():
    """Get data for the animated dev cycle ring visualization."""
    engine = get_dev_cycle_engine()
    return engine.generate_visualization_data()


@devcycle_router.get("/metrics")
async def get_cycle_metrics():
    """Get development cycle metrics."""
    engine = get_dev_cycle_engine()
    return engine.get_metrics()


@devcycle_router.post("/advance")
async def advance_stage():
    """Advance to the next stage in the cycle."""
    engine = get_dev_cycle_engine()
    result = await engine.advance_stage()
    return result


# ── Feedback Router ─────────────────────────────────────────────────────────

feedback_router = APIRouter(prefix="/api/feedback", tags=["Feedback"])


@feedback_router.post("/tool-event")
async def record_tool_event(request: ToolEventRequest):
    """Record a tool execution event."""
    import uuid

    layer = get_feedback_layer()
    event = ToolEvent(
        id=str(uuid.uuid4())[:8],
        tool_name=request.tool_name,
        tool_input=request.tool_input,
        tool_output=request.tool_output,
        success=request.success,
        error_message=request.error_message,
        duration_ms=request.duration_ms,
        session_id=request.session_id,
    )
    await layer.record_tool_event(event)
    return {"success": True, "event_id": event.id}


@feedback_router.get("/history")
async def get_tool_history(
    limit: int = Query(50, ge=1, le=500),
    session_id: Optional[str] = None,
    tool_name: Optional[str] = None,
    success_only: Optional[bool] = None,
):
    """Get tool execution history."""
    layer = get_feedback_layer()
    events = await layer.get_tool_history(
        limit=limit,
        session_id=session_id,
        tool_name=tool_name,
        success_only=success_only,
    )
    return {"events": [e.to_dict() for e in events], "count": len(events)}


@feedback_router.get("/patterns")
async def get_patterns():
    """Get detected usage patterns."""
    layer = get_feedback_layer()
    patterns = await layer.analyze_patterns()
    return {"patterns": [p.to_dict() for p in patterns]}


@feedback_router.get("/insights")
async def get_insights():
    """Generate AI-powered insights."""
    layer = get_feedback_layer()
    insights = await layer.generate_insights()
    return {"insights": insights}


@feedback_router.post("/recovery")
async def suggest_recovery(request: RecoveryRequest):
    """Get AI-powered error recovery suggestion."""
    layer = get_feedback_layer()
    suggestion = await layer.suggest_recovery(request.error, request.context)
    return {"error": request.error, "suggestion": suggestion}


@feedback_router.get("/metrics")
async def get_feedback_metrics():
    """Get feedback layer metrics."""
    layer = get_feedback_layer()
    return layer.get_metrics()


@feedback_router.post("/session/start")
async def start_feedback_session(session_id: str):
    """Start tracking a new feedback session."""
    layer = get_feedback_layer()
    stats = await layer.start_session(session_id)
    return stats.to_dict()


@feedback_router.post("/session/end")
async def end_feedback_session(session_id: str):
    """End a feedback session and get summary."""
    layer = get_feedback_layer()
    stats = await layer.end_session(session_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats.to_dict()


@feedback_router.get("/session/{session_id}")
async def get_session_stats(session_id: str):
    """Get statistics for a session."""
    layer = get_feedback_layer()
    stats = layer.get_session_stats(session_id)
    if stats is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return stats.to_dict()


# ── Combined Status ─────────────────────────────────────────────────────────

status_router = APIRouter(prefix="/api/interactive-status", tags=["Status"])


@status_router.get("")
async def get_interactive_status():
    """Get combined status of all interactive systems."""
    tutor = get_tutor()
    engine = get_dev_cycle_engine()
    layer = get_feedback_layer()

    progress = tutor.get_progress()
    state = await engine.get_current_state()
    feedback_status = layer.get_status()

    # Get GitHub achievement status
    github_status = {}
    try:
        from slate.github_achievements import get_github_tracker
        tracker = get_github_tracker()
        gh_status = tracker.get_status()
        github_status = {
            "earned": gh_status.get("earned", 0),
            "in_progress": gh_status.get("in_progress", 0),
            "total": gh_status.get("total_achievements", 0),
        }
    except ImportError:
        pass

    return {
        "learning": {
            "active_path": tutor._current_path,
            "completed_steps": len(progress.completed_steps),
            "achievements": len(progress.achievements),
            "total_xp": progress.total_xp,
            "level": tutor.calculate_level(progress.total_xp),
        },
        "dev_cycle": {
            "current_stage": state.current_stage.value,
            "stage_progress": state.stage_progress_percent,
            "cycle_count": state.cycle_count,
            "active_activities": len([
                a for a in state.activities.values()
                for act in a if act.status == ActivityStatus.IN_PROGRESS
            ]),
        },
        "feedback": {
            "events_count": feedback_status["events_count"],
            "patterns_count": feedback_status["patterns_count"],
            "success_rate": feedback_status["metrics"].get("success_rate", 0),
        },
        "github": github_status,
    }


# ── GitHub Achievements Router ──────────────────────────────────────────────

github_router = APIRouter(prefix="/api/github", tags=["GitHub Achievements"])


@github_router.get("/achievements")
async def get_github_achievements():
    """Get all GitHub achievements with progress."""
    try:
        from slate.github_achievements import get_github_tracker
        tracker = get_github_tracker()
        return {"achievements": tracker.get_all_achievements()}
    except ImportError:
        return {"achievements": [], "error": "GitHub achievements module not available"}


@github_router.get("/achievements/status")
async def get_github_achievement_status():
    """Get GitHub achievement status summary."""
    try:
        from slate.github_achievements import get_github_tracker
        tracker = get_github_tracker()
        return tracker.get_status()
    except ImportError:
        return {"error": "GitHub achievements module not available"}


@github_router.post("/achievements/refresh")
async def refresh_github_achievements():
    """Refresh achievement progress from GitHub."""
    try:
        from slate.github_achievements import get_github_tracker
        tracker = get_github_tracker()
        result = await tracker.refresh_from_github()
        return result
    except ImportError:
        return {"success": False, "error": "GitHub achievements module not available"}


@github_router.get("/achievements/recommendations")
async def get_github_recommendations():
    """Get personalized achievement recommendations."""
    try:
        from slate.github_achievements import get_github_tracker
        tracker = get_github_tracker()
        return {"recommendations": tracker.get_recommendations()}
    except ImportError:
        return {"recommendations": [], "error": "GitHub achievements module not available"}


# ── Main Router ─────────────────────────────────────────────────────────────


def create_interactive_router() -> APIRouter:
    """Create the combined interactive router."""
    router = APIRouter()
    router.include_router(learning_router)
    router.include_router(devcycle_router)
    router.include_router(feedback_router)
    router.include_router(status_router)
    router.include_router(github_router)
    return router


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    """CLI to test endpoints with uvicorn."""
    import argparse
    import uvicorn
    from fastapi import FastAPI

    parser = argparse.ArgumentParser(
        description="SLATE Interactive API Server (standalone)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8081,
        help="Port to run on (default: 8081)",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host to bind to (default: 127.0.0.1)",
    )
    args = parser.parse_args()

    app = FastAPI(
        title="SLATE Interactive API",
        description="Learning, Development Cycle, and Feedback APIs",
        version="1.0.0",
    )
    app.include_router(create_interactive_router())

    @app.get("/")
    async def root():
        return {
            "service": "SLATE Interactive API",
            "endpoints": {
                "learning": "/api/interactive/*",
                "dev_cycle": "/api/devcycle/*",
                "feedback": "/api/feedback/*",
                "status": "/api/interactive-status",
            },
        }

    print(f"\n  Starting SLATE Interactive API")
    print(f"  Listening on http://{args.host}:{args.port}")
    print(f"  Docs: http://{args.host}:{args.port}/docs\n")

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
