#!/usr/bin/env python3
# Modified: 2026-02-07T15:00:00Z | Author: COPILOT | Change: Initial creation of Claude feedback layer
"""
Claude Feedback Layer - Bidirectional event stream for Claude Code integration.

Provides:
- Tool event recording and history
- Pattern analysis for common usage patterns
- AI-powered insight generation via Ollama
- Error recovery suggestions
- WebSocket event broadcasting
- Session-based event grouping

Integrates with ClaudeCodeManager hooks for automatic event capture.
"""

import asyncio
import json
import logging
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Optional

# Add workspace root to path
WORKSPACE_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(WORKSPACE_ROOT))

logger = logging.getLogger("slate.claude_feedback_layer")


# ── Event Types ─────────────────────────────────────────────────────────────


class EventType(str, Enum):
    """Types of feedback events."""
    TOOL_EXECUTED = "tool_executed"
    TOOL_FAILED = "tool_failed"
    PATTERN_DETECTED = "pattern_detected"
    INSIGHT_GENERATED = "insight_generated"
    RECOVERY_SUGGESTED = "recovery_suggested"
    SESSION_STARTED = "session_started"
    SESSION_ENDED = "session_ended"
    ACHIEVEMENT_PROGRESS = "achievement_progress"


class PatternType(str, Enum):
    """Types of usage patterns detected."""
    REPETITIVE_ACTION = "repetitive_action"
    ERROR_RECOVERY = "error_recovery"
    WORKFLOW_SEQUENCE = "workflow_sequence"
    TOOL_PREFERENCE = "tool_preference"
    EFFICIENCY_OPPORTUNITY = "efficiency_opportunity"
    COMMON_ERROR = "common_error"
    SUCCESS_PATTERN = "success_pattern"


# ── Data Classes ────────────────────────────────────────────────────────────


@dataclass
class ToolEvent:
    """Record of a Claude Code tool execution."""
    id: str
    tool_name: str
    tool_input: dict
    tool_output: Optional[str] = None
    success: bool = True
    error_message: Optional[str] = None
    duration_ms: int = 0
    session_id: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "tool_name": self.tool_name,
            "tool_input": self.tool_input,
            "tool_output": self.tool_output,
            "success": self.success,
            "error_message": self.error_message,
            "duration_ms": self.duration_ms,
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ToolEvent":
        return cls(**data)


@dataclass
class PatternInsight:
    """Insight derived from usage pattern analysis."""
    id: str
    pattern_type: PatternType
    description: str
    frequency: int = 1
    confidence: float = 0.0
    affected_tools: list[str] = field(default_factory=list)
    recommendation: Optional[str] = None
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "frequency": self.frequency,
            "confidence": self.confidence,
            "affected_tools": self.affected_tools,
            "recommendation": self.recommendation,
            "first_seen": self.first_seen,
            "last_seen": self.last_seen,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "PatternInsight":
        data["pattern_type"] = PatternType(data["pattern_type"])
        return cls(**data)


@dataclass
class FeedbackEvent:
    """Event for WebSocket broadcasting."""
    event_type: EventType
    payload: dict
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    session_id: Optional[str] = None

    def to_dict(self) -> dict:
        return {
            "event_type": self.event_type.value,
            "payload": self.payload,
            "timestamp": self.timestamp,
            "session_id": self.session_id,
        }


@dataclass
class SessionStats:
    """Statistics for a Claude Code session."""
    session_id: str
    started_at: str
    ended_at: Optional[str] = None
    total_tools: int = 0
    successful_tools: int = 0
    failed_tools: int = 0
    total_duration_ms: int = 0
    most_used_tool: Optional[str] = None
    patterns_detected: int = 0
    insights_generated: int = 0

    def to_dict(self) -> dict:
        return {
            "session_id": self.session_id,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "total_tools": self.total_tools,
            "successful_tools": self.successful_tools,
            "failed_tools": self.failed_tools,
            "total_duration_ms": self.total_duration_ms,
            "most_used_tool": self.most_used_tool,
            "patterns_detected": self.patterns_detected,
            "insights_generated": self.insights_generated,
        }


# ── Claude Feedback Layer ───────────────────────────────────────────────────


class ClaudeFeedbackLayer:
    """
    Bidirectional feedback layer for Claude Code integration.

    Features:
    - Real-time tool event recording
    - Usage pattern detection
    - AI-powered insights via Ollama
    - Error recovery suggestions
    - WebSocket event broadcasting
    """

    STATE_FILE = ".slate_identity/feedback_state.json"
    EVENTS_FILE = ".slate_identity/feedback_events.json"
    MAX_EVENTS = 1000  # Rolling window of events

    def __init__(self, workspace: Optional[Path] = None):
        self.workspace = workspace or WORKSPACE_ROOT
        self.state_file = self.workspace / self.STATE_FILE
        self.events_file = self.workspace / self.EVENTS_FILE

        # In-memory state
        self._events: list[ToolEvent] = []
        self._patterns: dict[str, PatternInsight] = {}
        self._sessions: dict[str, SessionStats] = {}
        self._broadcast_callbacks: list[Callable[[FeedbackEvent], None]] = []
        self._tool_counts: dict[str, int] = defaultdict(int)
        self._error_sequences: list[ToolEvent] = []

        # Load persisted state
        self._load_state()

    # ── State Persistence ───────────────────────────────────────────────────

    def _ensure_state_dir(self) -> None:
        """Ensure state directory exists."""
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    def _load_state(self) -> None:
        """Load persisted state from disk."""
        self._ensure_state_dir()

        # Load events
        if self.events_file.exists():
            try:
                with open(self.events_file) as f:
                    data = json.load(f)
                    self._events = [
                        ToolEvent.from_dict(e) for e in data.get("events", [])
                    ]
                    self._patterns = {
                        pid: PatternInsight.from_dict(p)
                        for pid, p in data.get("patterns", {}).items()
                    }
                    # Rebuild tool counts
                    for event in self._events:
                        self._tool_counts[event.tool_name] += 1
                    logger.info(
                        f"Loaded {len(self._events)} events, "
                        f"{len(self._patterns)} patterns"
                    )
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to load events: {e}")
                self._events = []
                self._patterns = {}

    def _save_state(self) -> None:
        """Persist state to disk."""
        self._ensure_state_dir()

        # Trim events to max window
        if len(self._events) > self.MAX_EVENTS:
            self._events = self._events[-self.MAX_EVENTS:]

        data = {
            "events": [e.to_dict() for e in self._events],
            "patterns": {pid: p.to_dict() for pid, p in self._patterns.items()},
            "last_updated": datetime.now().isoformat(),
        }

        try:
            with open(self.events_file, "w") as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save state: {e}")

    # ── Event Recording ─────────────────────────────────────────────────────

    async def record_tool_event(self, event: ToolEvent) -> None:
        """Record a tool execution event."""
        import uuid

        if not event.id:
            event.id = str(uuid.uuid4())[:8]

        self._events.append(event)
        self._tool_counts[event.tool_name] += 1

        # Track errors for pattern detection
        if not event.success:
            self._error_sequences.append(event)
            # Keep only recent errors
            if len(self._error_sequences) > 20:
                self._error_sequences = self._error_sequences[-20:]

        # Update session stats
        if event.session_id and event.session_id in self._sessions:
            stats = self._sessions[event.session_id]
            stats.total_tools += 1
            stats.total_duration_ms += event.duration_ms
            if event.success:
                stats.successful_tools += 1
            else:
                stats.failed_tools += 1

        # Broadcast event
        feedback = FeedbackEvent(
            event_type=EventType.TOOL_EXECUTED if event.success else EventType.TOOL_FAILED,
            payload=event.to_dict(),
            session_id=event.session_id,
        )
        await self._broadcast(feedback)

        # Analyze for patterns periodically
        if len(self._events) % 10 == 0:
            await self._analyze_recent_patterns()

        # Save state
        self._save_state()
        logger.debug(f"Recorded tool event: {event.tool_name}")

    async def get_tool_history(
        self,
        limit: int = 50,
        session_id: Optional[str] = None,
        tool_name: Optional[str] = None,
        success_only: Optional[bool] = None,
    ) -> list[ToolEvent]:
        """Get tool execution history with optional filters."""
        events = self._events.copy()

        if session_id:
            events = [e for e in events if e.session_id == session_id]
        if tool_name:
            events = [e for e in events if e.tool_name == tool_name]
        if success_only is not None:
            events = [e for e in events if e.success == success_only]

        return events[-limit:]

    # ── Session Management ──────────────────────────────────────────────────

    async def start_session(self, session_id: str) -> SessionStats:
        """Start tracking a new Claude Code session."""
        stats = SessionStats(
            session_id=session_id,
            started_at=datetime.now().isoformat(),
        )
        self._sessions[session_id] = stats

        # Broadcast session start
        await self._broadcast(FeedbackEvent(
            event_type=EventType.SESSION_STARTED,
            payload=stats.to_dict(),
            session_id=session_id,
        ))

        logger.info(f"Started tracking session: {session_id}")
        return stats

    async def end_session(self, session_id: str) -> Optional[SessionStats]:
        """End a session and generate summary."""
        if session_id not in self._sessions:
            return None

        stats = self._sessions[session_id]
        stats.ended_at = datetime.now().isoformat()

        # Calculate most used tool
        session_tools: dict[str, int] = defaultdict(int)
        for event in self._events:
            if event.session_id == session_id:
                session_tools[event.tool_name] += 1
        if session_tools:
            stats.most_used_tool = max(session_tools, key=session_tools.get)

        # Generate session insights
        await self._generate_session_insights(session_id)

        # Broadcast session end
        await self._broadcast(FeedbackEvent(
            event_type=EventType.SESSION_ENDED,
            payload=stats.to_dict(),
            session_id=session_id,
        ))

        logger.info(f"Ended session: {session_id}")
        return stats

    def get_session_stats(self, session_id: str) -> Optional[SessionStats]:
        """Get statistics for a session."""
        return self._sessions.get(session_id)

    # ── Pattern Analysis ────────────────────────────────────────────────────

    async def analyze_patterns(self) -> list[PatternInsight]:
        """Analyze all events for usage patterns."""
        patterns = []

        # Pattern 1: Repetitive actions
        patterns.extend(await self._detect_repetitive_actions())

        # Pattern 2: Common errors
        patterns.extend(await self._detect_common_errors())

        # Pattern 3: Workflow sequences
        patterns.extend(await self._detect_workflow_sequences())

        # Pattern 4: Tool preferences
        patterns.extend(await self._detect_tool_preferences())

        # Update stored patterns
        for pattern in patterns:
            self._patterns[pattern.id] = pattern

        self._save_state()
        return patterns

    async def _analyze_recent_patterns(self) -> None:
        """Analyze recent events for patterns (called periodically)."""
        recent = self._events[-50:]
        if not recent:
            return

        # Check for repetitive recent actions
        tool_sequence = [e.tool_name for e in recent[-10:]]
        if len(set(tool_sequence)) == 1 and len(tool_sequence) >= 5:
            pattern = PatternInsight(
                id=f"rep_{tool_sequence[0]}_{len(self._events)}",
                pattern_type=PatternType.REPETITIVE_ACTION,
                description=f"Repeated use of {tool_sequence[0]} ({len(tool_sequence)} times)",
                frequency=len(tool_sequence),
                confidence=0.85,
                affected_tools=[tool_sequence[0]],
            )
            await self._broadcast(FeedbackEvent(
                event_type=EventType.PATTERN_DETECTED,
                payload=pattern.to_dict(),
            ))

    async def _detect_repetitive_actions(self) -> list[PatternInsight]:
        """Detect repetitive action patterns."""
        patterns = []
        window_size = 20

        for i in range(len(self._events) - window_size):
            window = self._events[i:i + window_size]
            tool_names = [e.tool_name for e in window]

            # Check for high repetition
            most_common = max(set(tool_names), key=tool_names.count)
            count = tool_names.count(most_common)

            if count >= window_size * 0.7:  # 70% or more same tool
                pattern = PatternInsight(
                    id=f"repetitive_{most_common}_{i}",
                    pattern_type=PatternType.REPETITIVE_ACTION,
                    description=f"High repetition of {most_common} tool",
                    frequency=count,
                    confidence=count / window_size,
                    affected_tools=[most_common],
                    recommendation=f"Consider batching {most_common} operations",
                )
                patterns.append(pattern)

        return patterns[-5:]  # Return recent patterns only

    async def _detect_common_errors(self) -> list[PatternInsight]:
        """Detect common error patterns."""
        patterns = []
        error_events = [e for e in self._events if not e.success]

        # Group errors by tool
        errors_by_tool: dict[str, list[ToolEvent]] = defaultdict(list)
        for event in error_events:
            errors_by_tool[event.tool_name].append(event)

        for tool, errors in errors_by_tool.items():
            if len(errors) >= 3:
                # Look for common error messages
                error_msgs = [e.error_message for e in errors if e.error_message]
                if error_msgs:
                    common_words = set.intersection(*[
                        set(msg.lower().split()) for msg in error_msgs[:5]
                    ]) if len(error_msgs) >= 2 else set()

                    pattern = PatternInsight(
                        id=f"error_{tool}",
                        pattern_type=PatternType.COMMON_ERROR,
                        description=f"Recurring errors in {tool}",
                        frequency=len(errors),
                        confidence=min(len(errors) / 10, 1.0),
                        affected_tools=[tool],
                        metadata={"common_keywords": list(common_words)[:5]},
                    )
                    patterns.append(pattern)

        return patterns

    async def _detect_workflow_sequences(self) -> list[PatternInsight]:
        """Detect common workflow sequences."""
        patterns = []

        # Look for common 3-tool sequences
        sequences: dict[tuple, int] = defaultdict(int)
        for i in range(len(self._events) - 2):
            seq = tuple(e.tool_name for e in self._events[i:i + 3])
            sequences[seq] += 1

        # Find significant sequences
        for seq, count in sequences.items():
            if count >= 5:
                pattern = PatternInsight(
                    id=f"workflow_{'_'.join(seq)}",
                    pattern_type=PatternType.WORKFLOW_SEQUENCE,
                    description=f"Common workflow: {' -> '.join(seq)}",
                    frequency=count,
                    confidence=min(count / 20, 1.0),
                    affected_tools=list(seq),
                )
                patterns.append(pattern)

        return sorted(patterns, key=lambda p: p.frequency, reverse=True)[:5]

    async def _detect_tool_preferences(self) -> list[PatternInsight]:
        """Detect tool usage preferences."""
        patterns = []

        total_uses = sum(self._tool_counts.values())
        if total_uses < 10:
            return patterns

        # Find dominant tools
        for tool, count in self._tool_counts.items():
            ratio = count / total_uses
            if ratio >= 0.25:  # Tool used 25%+ of the time
                pattern = PatternInsight(
                    id=f"preference_{tool}",
                    pattern_type=PatternType.TOOL_PREFERENCE,
                    description=f"Strong preference for {tool} ({ratio:.0%} of uses)",
                    frequency=count,
                    confidence=ratio,
                    affected_tools=[tool],
                )
                patterns.append(pattern)

        return patterns

    def get_patterns(self) -> list[PatternInsight]:
        """Get all detected patterns."""
        return list(self._patterns.values())

    # ── AI Insights ─────────────────────────────────────────────────────────

    async def generate_insights(self) -> list[dict]:
        """Generate AI-powered insights from patterns using Ollama."""
        insights = []

        # Get recent patterns
        patterns = self.get_patterns()
        if not patterns:
            return insights

        # Get recent events summary
        recent_events = self._events[-50:]
        success_rate = (
            len([e for e in recent_events if e.success]) / len(recent_events)
            if recent_events else 0
        )

        # Build context for AI
        context = {
            "patterns": [p.to_dict() for p in patterns[:5]],
            "success_rate": success_rate,
            "total_events": len(self._events),
            "tool_distribution": dict(self._tool_counts),
        }

        # Generate insight via Ollama
        try:
            insight_text = await self._query_ollama_for_insight(context)
            if insight_text:
                insight = {
                    "id": f"insight_{datetime.now().strftime('%Y%m%d%H%M%S')}",
                    "text": insight_text,
                    "context": context,
                    "generated_at": datetime.now().isoformat(),
                }
                insights.append(insight)

                # Broadcast insight
                await self._broadcast(FeedbackEvent(
                    event_type=EventType.INSIGHT_GENERATED,
                    payload=insight,
                ))
        except Exception as e:
            logger.warning(f"Failed to generate AI insight: {e}")

        return insights

    async def _query_ollama_for_insight(self, context: dict) -> Optional[str]:
        """Query Ollama for an insight based on usage patterns."""
        import aiohttp

        prompt = f"""Analyze this Claude Code usage data and provide ONE actionable insight:

Tool Distribution: {json.dumps(context['tool_distribution'])}
Success Rate: {context['success_rate']:.0%}
Total Operations: {context['total_events']}

Patterns Detected:
{chr(10).join(f"- {p['description']}" for p in context['patterns'])}

Provide a brief, actionable insight (2-3 sentences) about improving the workflow.
Focus on efficiency, error reduction, or better tool usage."""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.7, "num_predict": 150},
                    },
                    timeout=aiohttp.ClientTimeout(total=30),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip()
        except Exception as e:
            logger.debug(f"Ollama query failed: {e}")

        return None

    async def _generate_session_insights(self, session_id: str) -> None:
        """Generate insights for a completed session."""
        session_events = [e for e in self._events if e.session_id == session_id]
        if len(session_events) < 5:
            return

        stats = self._sessions.get(session_id)
        if not stats:
            return

        # Generate summary insight
        success_rate = stats.successful_tools / max(stats.total_tools, 1)
        avg_duration = stats.total_duration_ms / max(stats.total_tools, 1)

        insight_text = (
            f"Session completed with {stats.total_tools} operations "
            f"({success_rate:.0%} success rate). "
            f"Most used: {stats.most_used_tool}. "
            f"Average duration: {avg_duration:.0f}ms."
        )

        await self._broadcast(FeedbackEvent(
            event_type=EventType.INSIGHT_GENERATED,
            payload={
                "session_id": session_id,
                "text": insight_text,
                "stats": stats.to_dict(),
            },
            session_id=session_id,
        ))

    # ── Error Recovery ──────────────────────────────────────────────────────

    async def suggest_recovery(
        self,
        error: str,
        context: Optional[dict] = None,
    ) -> str:
        """Suggest recovery action for an error using AI."""
        # Check for common errors first
        common_recoveries = {
            "file not found": "Verify the file path exists. Use Glob to search for the file.",
            "permission denied": "Check file permissions or run with elevated privileges.",
            "syntax error": "Review the code for syntax issues. Check brackets and quotes.",
            "module not found": "Install the missing module with pip install.",
            "timeout": "The operation took too long. Consider breaking into smaller steps.",
            "connection refused": "Check if the service is running and accessible.",
        }

        error_lower = error.lower()
        for pattern, recovery in common_recoveries.items():
            if pattern in error_lower:
                return recovery

        # Try AI-powered recovery suggestion
        try:
            recovery = await self._query_ollama_for_recovery(error, context)
            if recovery:
                await self._broadcast(FeedbackEvent(
                    event_type=EventType.RECOVERY_SUGGESTED,
                    payload={"error": error, "suggestion": recovery},
                ))
                return recovery
        except Exception as e:
            logger.debug(f"AI recovery suggestion failed: {e}")

        return "Review the error message and try a different approach."

    async def _query_ollama_for_recovery(
        self,
        error: str,
        context: Optional[dict] = None,
    ) -> Optional[str]:
        """Query Ollama for error recovery suggestion."""
        import aiohttp

        context_str = ""
        if context:
            context_str = f"\nContext: {json.dumps(context)}"

        prompt = f"""A Claude Code operation failed with this error:
{error}
{context_str}

Provide a brief, actionable recovery suggestion (1-2 sentences).
Focus on the most likely fix."""

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    "http://localhost:11434/api/generate",
                    json={
                        "model": "mistral-nemo",
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": 0.5, "num_predict": 100},
                    },
                    timeout=aiohttp.ClientTimeout(total=20),
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data.get("response", "").strip()
        except Exception:
            pass

        return None

    # ── WebSocket Broadcasting ──────────────────────────────────────────────

    def register_broadcast_callback(
        self,
        callback: Callable[[FeedbackEvent], None],
    ) -> None:
        """Register a callback for WebSocket broadcasting."""
        self._broadcast_callbacks.append(callback)

    def unregister_broadcast_callback(
        self,
        callback: Callable[[FeedbackEvent], None],
    ) -> None:
        """Unregister a broadcast callback."""
        if callback in self._broadcast_callbacks:
            self._broadcast_callbacks.remove(callback)

    async def _broadcast(self, event: FeedbackEvent) -> None:
        """Broadcast an event to all registered callbacks."""
        for callback in self._broadcast_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
            except Exception as e:
                logger.error(f"Broadcast callback error: {e}")

    async def broadcast_event(self, event: FeedbackEvent) -> None:
        """Public method to broadcast a custom event."""
        await self._broadcast(event)

    # ── Metrics & Statistics ────────────────────────────────────────────────

    def get_metrics(self) -> dict:
        """Get comprehensive feedback metrics."""
        events = self._events
        if not events:
            return {
                "total_events": 0,
                "success_rate": 0,
                "avg_duration_ms": 0,
                "tool_distribution": {},
                "patterns_count": 0,
                "active_sessions": 0,
            }

        successful = len([e for e in events if e.success])
        total_duration = sum(e.duration_ms for e in events)

        return {
            "total_events": len(events),
            "success_rate": successful / len(events),
            "avg_duration_ms": total_duration / len(events),
            "tool_distribution": dict(self._tool_counts),
            "patterns_count": len(self._patterns),
            "active_sessions": len([
                s for s in self._sessions.values()
                if s.ended_at is None
            ]),
            "most_common_errors": self._get_common_errors()[:5],
        }

    def _get_common_errors(self) -> list[dict]:
        """Get most common error messages."""
        errors: dict[str, int] = defaultdict(int)
        for event in self._events:
            if not event.success and event.error_message:
                # Normalize error message
                key = event.error_message[:100]
                errors[key] += 1

        return [
            {"message": msg, "count": count}
            for msg, count in sorted(errors.items(), key=lambda x: -x[1])
        ]

    def get_status(self) -> dict:
        """Get feedback layer status."""
        metrics = self.get_metrics()
        return {
            "status": "active",
            "events_count": len(self._events),
            "patterns_count": len(self._patterns),
            "sessions_count": len(self._sessions),
            "active_callbacks": len(self._broadcast_callbacks),
            "metrics": metrics,
            "state_file": str(self.events_file),
        }


# ── Hook Integration ────────────────────────────────────────────────────────


class FeedbackCaptureHook:
    """
    Hook for ClaudeCodeManager that captures tool events into the feedback layer.

    Usage:
        from slate.claude_code_manager import get_manager
        from slate.claude_feedback_layer import get_feedback_layer, FeedbackCaptureHook

        manager = get_manager()
        layer = get_feedback_layer()
        hook = FeedbackCaptureHook(layer)

        manager.register_hook("PostToolUse", ".*", hook.capture_tool_use)
    """

    def __init__(self, layer: ClaudeFeedbackLayer):
        self.layer = layer
        self._start_times: dict[str, datetime] = {}

    def pre_tool_use(self, context) -> None:
        """Record tool start time."""
        self._start_times[context.tool_use_id] = datetime.now()

    def capture_tool_use(self, context) -> "HookResult":
        """Capture tool execution as a feedback event."""
        from slate.claude_code_manager import HookResult
        import uuid

        # Calculate duration
        start_time = self._start_times.pop(context.tool_use_id, None)
        duration_ms = 0
        if start_time:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        # Create tool event
        event = ToolEvent(
            id=str(uuid.uuid4())[:8],
            tool_name=context.tool_name,
            tool_input=context.tool_input,
            success=True,
            duration_ms=duration_ms,
            session_id=context.session_id,
        )

        # Record async
        asyncio.create_task(self.layer.record_tool_event(event))

        return HookResult(permission_decision="allow")

    def capture_tool_failure(self, context, error: str) -> "HookResult":
        """Capture failed tool execution."""
        from slate.claude_code_manager import HookResult
        import uuid

        start_time = self._start_times.pop(context.tool_use_id, None)
        duration_ms = 0
        if start_time:
            duration_ms = int((datetime.now() - start_time).total_seconds() * 1000)

        event = ToolEvent(
            id=str(uuid.uuid4())[:8],
            tool_name=context.tool_name,
            tool_input=context.tool_input,
            success=False,
            error_message=error,
            duration_ms=duration_ms,
            session_id=context.session_id,
        )

        asyncio.create_task(self.layer.record_tool_event(event))

        return HookResult(permission_decision="allow")


# ── Factory Functions ───────────────────────────────────────────────────────


_layer_instance: Optional[ClaudeFeedbackLayer] = None


def get_feedback_layer(workspace: Optional[Path] = None) -> ClaudeFeedbackLayer:
    """Get or create the singleton feedback layer instance."""
    global _layer_instance
    if _layer_instance is None:
        _layer_instance = ClaudeFeedbackLayer(workspace)
    return _layer_instance


def reset_feedback_layer() -> None:
    """Reset the feedback layer instance."""
    global _layer_instance
    _layer_instance = None


# ── CLI ─────────────────────────────────────────────────────────────────────


async def main_async():
    """Async main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Claude Feedback Layer"
    )
    parser.add_argument(
        "--status",
        action="store_true",
        help="Show feedback layer status",
    )
    parser.add_argument(
        "--history",
        action="store_true",
        help="Show tool execution history",
    )
    parser.add_argument(
        "--patterns",
        action="store_true",
        help="Analyze and show patterns",
    )
    parser.add_argument(
        "--insights",
        action="store_true",
        help="Generate AI insights",
    )
    parser.add_argument(
        "--metrics",
        action="store_true",
        help="Show feedback metrics",
    )
    parser.add_argument(
        "--recovery",
        metavar="ERROR",
        help="Suggest recovery for an error",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=20,
        help="Limit for history output",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output in JSON format",
    )
    args = parser.parse_args()

    layer = get_feedback_layer()

    if args.history:
        events = await layer.get_tool_history(limit=args.limit)
        if args.json:
            print(json.dumps([e.to_dict() for e in events], indent=2))
        else:
            print(f"\n  Tool Execution History (last {len(events)})")
            print("  " + "=" * 56)
            for event in events:
                status = "OK" if event.success else "FAIL"
                print(f"  [{status}] {event.tool_name} ({event.duration_ms}ms)")
                print(f"       {event.timestamp[:19]}")
        return

    if args.patterns:
        patterns = await layer.analyze_patterns()
        if args.json:
            print(json.dumps([p.to_dict() for p in patterns], indent=2))
        else:
            print("\n  Detected Patterns")
            print("  " + "=" * 56)
            for pattern in patterns:
                print(f"  [{pattern.pattern_type.value}] {pattern.description}")
                print(f"       Frequency: {pattern.frequency}, Confidence: {pattern.confidence:.0%}")
                if pattern.recommendation:
                    print(f"       Recommendation: {pattern.recommendation}")
        return

    if args.insights:
        insights = await layer.generate_insights()
        if args.json:
            print(json.dumps(insights, indent=2))
        else:
            print("\n  AI-Generated Insights")
            print("  " + "=" * 56)
            for insight in insights:
                print(f"  {insight.get('text', 'No insight generated')}")
        return

    if args.metrics:
        metrics = layer.get_metrics()
        if args.json:
            print(json.dumps(metrics, indent=2))
        else:
            print("\n  Feedback Metrics")
            print("  " + "=" * 56)
            print(f"  Total Events: {metrics['total_events']}")
            print(f"  Success Rate: {metrics['success_rate']:.0%}")
            print(f"  Avg Duration: {metrics['avg_duration_ms']:.0f}ms")
            print(f"  Patterns: {metrics['patterns_count']}")
            print(f"  Active Sessions: {metrics['active_sessions']}")
        return

    if args.recovery:
        suggestion = await layer.suggest_recovery(args.recovery)
        if args.json:
            print(json.dumps({"error": args.recovery, "suggestion": suggestion}))
        else:
            print(f"\n  Recovery Suggestion")
            print("  " + "=" * 56)
            print(f"  Error: {args.recovery}")
            print(f"  Suggestion: {suggestion}")
        return

    # Default: status
    status = layer.get_status()
    if args.json:
        print(json.dumps(status, indent=2))
    else:
        print("=" * 60)
        print("  SLATE Claude Feedback Layer")
        print("=" * 60)
        print(f"\n  Status: {status['status']}")
        print(f"  Events: {status['events_count']}")
        print(f"  Patterns: {status['patterns_count']}")
        print(f"  Sessions: {status['sessions_count']}")
        print(f"  Callbacks: {status['active_callbacks']}")
        print(f"\n  State File: {status['state_file']}")

        metrics = status.get("metrics", {})
        if metrics.get("total_events", 0) > 0:
            print(f"\n  Success Rate: {metrics['success_rate']:.0%}")
            print(f"  Avg Duration: {metrics['avg_duration_ms']:.0f}ms")
        print("=" * 60)


def main():
    """CLI entry point."""
    asyncio.run(main_async())


if __name__ == "__main__":
    main()
