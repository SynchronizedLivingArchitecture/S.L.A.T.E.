#!/usr/bin/env python3
# Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Initial creation of feedback stream component
"""
Feedback Stream UI Component.

Generates the Claude feedback stream visualization for the SLATE dashboard.

Features:
- Real-time tool execution feed
- Pattern insight cards
- Success/failure indicators
- Session grouping
- AI suggestion bubbles
- Animated entry effects
"""

from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Dict, Any


# Tool icons (inline SVG paths)
TOOL_ICONS = {
    "Read": "M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8l-6-6zm4 18H6V4h7v5h5v11z",
    "Write": "M14.06 9.02l.92.92L5.92 19H5v-.92l9.06-9.06M17.66 3c-.25 0-.51.1-.7.29l-1.83 1.83 3.75 3.75 1.83-1.83a.996.996 0 000-1.41l-2.34-2.34c-.2-.2-.45-.29-.71-.29zm-3.6 3.19L3 17.25V21h3.75L17.81 9.94l-3.75-3.75z",
    "Edit": "M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04a.996.996 0 000-1.41l-2.34-2.34a.996.996 0 00-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z",
    "Bash": "M20 19v-2H4v2h16zm0-6v-2H4v2h16zm-1-6l-5 4 5 4V7z",
    "Glob": "M10 4H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2h-8l-2-2z",
    "Grep": "M15.5 14h-.79l-.28-.27A6.471 6.471 0 0016 9.5 6.5 6.5 0 109.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
    "Task": "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l7.59-7.59L21 8l-9 9z",
    "TodoWrite": "M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-2 10H7v-2h10v2z",
    "WebFetch": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z",
    "WebSearch": "M15.5 14h-.79l-.28-.27c1.2-1.4 1.82-3.31 1.48-5.34-.47-2.78-2.79-5-5.59-5.34-4.23-.52-7.79 3.04-7.27 7.27.34 2.8 2.56 5.12 5.34 5.59 2.03.34 3.94-.28 5.34-1.48l.27.28v.79l4.25 4.25c.41.41 1.08.41 1.49 0 .41-.41.41-1.08 0-1.49L15.5 14zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z",
    "default": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
}

PATTERN_ICONS = {
    "repetitive_action": "M12 6v3l4-4-4-4v3c-4.42 0-8 3.58-8 8 0 1.57.46 3.03 1.24 4.26L6.7 14.8c-.45-.83-.7-1.79-.7-2.8 0-3.31 2.69-6 6-6zm6.76 1.74L17.3 9.2c.44.84.7 1.79.7 2.8 0 3.31-2.69 6-6 6v-3l-4 4 4 4v-3c4.42 0 8-3.58 8-8 0-1.57-.46-3.03-1.24-4.26z",
    "error_recovery": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z",
    "workflow_sequence": "M3.5 18.49l6-6.01 4 4L22 6.92l-1.41-1.41-7.09 7.97-4-4L2 16.99z",
    "tool_preference": "M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z",
    "efficiency_opportunity": "M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9z",
    "common_error": "M1 21h22L12 2 1 21zm12-3h-2v-2h2v2zm0-4h-2v-4h2v4z",
    "success_pattern": "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
}


@dataclass
class FeedbackStreamConfig:
    """Configuration for the feedback stream."""
    max_visible_events: int = 15
    show_patterns: bool = True
    show_insights: bool = True
    animate_entries: bool = True
    compact_mode: bool = False


class FeedbackStreamGenerator:
    """
    Generates Claude feedback stream visualization.
    """

    def __init__(self, config: Optional[FeedbackStreamConfig] = None):
        self.config = config or FeedbackStreamConfig()

    def generate_stream_html(
        self,
        events: Optional[List[Dict]] = None,
        patterns: Optional[List[Dict]] = None,
        insights: Optional[List[Dict]] = None,
        metrics: Optional[Dict] = None,
    ) -> str:
        """Generate the complete feedback stream HTML."""
        # Defaults
        if events is None:
            events = []
        if patterns is None:
            patterns = []
        if insights is None:
            insights = []
        if metrics is None:
            metrics = {"total_events": 0, "success_rate": 0}

        html_parts = [
            '<div class="feedback-stream">',
            self._generate_header(metrics),
        ]

        if self.config.show_insights and insights:
            html_parts.append(self._generate_insights_section(insights))

        if self.config.show_patterns and patterns:
            html_parts.append(self._generate_patterns_section(patterns))

        html_parts.append(self._generate_events_section(events))
        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _generate_header(self, metrics: Dict) -> str:
        """Generate stream header with metrics."""
        total = metrics.get("total_events", 0)
        success_rate = metrics.get("success_rate", 0) * 100
        avg_duration = metrics.get("avg_duration_ms", 0)

        success_color = "#78B89A" if success_rate >= 90 else "#D4A054" if success_rate >= 70 else "#C47070"

        return f'''
<div class="stream-header">
    <div class="stream-title">
        <svg viewBox="0 0 24 24" width="20" height="20">
            <path d="M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z" fill="#B87333"/>
        </svg>
        <span>Claude Feedback Stream</span>
    </div>
    <div class="stream-metrics">
        <div class="metric">
            <span class="metric-value">{total}</span>
            <span class="metric-label">Events</span>
        </div>
        <div class="metric">
            <span class="metric-value" style="color: {success_color}">{success_rate:.0f}%</span>
            <span class="metric-label">Success</span>
        </div>
        <div class="metric">
            <span class="metric-value">{avg_duration:.0f}ms</span>
            <span class="metric-label">Avg Time</span>
        </div>
    </div>
</div>'''

    def _generate_insights_section(self, insights: List[Dict]) -> str:
        """Generate AI insights section."""
        if not insights:
            return ""

        insights_html = []
        for insight in insights[:3]:
            text = insight.get("text", "")
            generated_at = insight.get("generated_at", "")

            insights_html.append(f'''
<div class="insight-card">
    <div class="insight-icon">
        <svg viewBox="0 0 24 24" width="18" height="18">
            <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z" fill="#D4A054"/>
        </svg>
    </div>
    <div class="insight-content">
        <p class="insight-text">{text}</p>
        <span class="insight-time">{self._format_time(generated_at)}</span>
    </div>
</div>''')

        return f'''
<div class="insights-section">
    <div class="section-header">
        <span>AI Insights</span>
        <button class="refresh-btn" onclick="refreshInsights()">
            <svg viewBox="0 0 24 24" width="14" height="14">
                <path d="M17.65 6.35C16.2 4.9 14.21 4 12 4c-4.42 0-7.99 3.58-7.99 8s3.57 8 7.99 8c3.73 0 6.84-2.55 7.73-6h-2.08c-.82 2.33-3.04 4-5.65 4-3.31 0-6-2.69-6-6s2.69-6 6-6c1.66 0 3.14.69 4.22 1.78L13 11h7V4l-2.35 2.35z" fill="currentColor"/>
            </svg>
        </button>
    </div>
    {''.join(insights_html)}
</div>'''

    def _generate_patterns_section(self, patterns: List[Dict]) -> str:
        """Generate patterns section."""
        if not patterns:
            return ""

        patterns_html = []
        for pattern in patterns[:4]:
            pattern_type = pattern.get("pattern_type", "")
            description = pattern.get("description", "")
            frequency = pattern.get("frequency", 0)
            confidence = pattern.get("confidence", 0) * 100
            recommendation = pattern.get("recommendation", "")

            icon_path = PATTERN_ICONS.get(pattern_type, PATTERN_ICONS["success_pattern"])
            type_color = self._get_pattern_color(pattern_type)

            patterns_html.append(f'''
<div class="pattern-card" style="border-left-color: {type_color};">
    <div class="pattern-header">
        <svg viewBox="0 0 24 24" width="16" height="16">
            <path d="{icon_path}" fill="{type_color}"/>
        </svg>
        <span class="pattern-type">{pattern_type.replace("_", " ").title()}</span>
        <span class="pattern-confidence">{confidence:.0f}%</span>
    </div>
    <p class="pattern-description">{description}</p>
    {f'<p class="pattern-recommendation">{recommendation}</p>' if recommendation else ''}
    <div class="pattern-meta">
        <span>Frequency: {frequency}x</span>
    </div>
</div>''')

        return f'''
<div class="patterns-section">
    <div class="section-header">
        <span>Detected Patterns</span>
        <span class="pattern-count">{len(patterns)}</span>
    </div>
    <div class="patterns-grid">
        {''.join(patterns_html)}
    </div>
</div>'''

    def _generate_events_section(self, events: List[Dict]) -> str:
        """Generate events feed section."""
        visible_events = events[-self.config.max_visible_events:]

        events_html = []
        for i, event in enumerate(reversed(visible_events)):
            tool_name = event.get("tool_name", "Unknown")
            success = event.get("success", True)
            duration_ms = event.get("duration_ms", 0)
            timestamp = event.get("timestamp", "")
            error_message = event.get("error_message", "")

            icon_path = TOOL_ICONS.get(tool_name, TOOL_ICONS["default"])
            status_class = "success" if success else "failure"
            status_icon = "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" if success else "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"

            animation_delay = f"animation-delay: {i * 0.05}s;" if self.config.animate_entries else ""

            events_html.append(f'''
<div class="event-item {status_class}" style="{animation_delay}">
    <div class="event-icon">
        <svg viewBox="0 0 24 24" width="18" height="18">
            <path d="{icon_path}" fill="currentColor"/>
        </svg>
    </div>
    <div class="event-content">
        <div class="event-header">
            <span class="event-tool">{tool_name}</span>
            <span class="event-duration">{duration_ms}ms</span>
        </div>
        {f'<p class="event-error">{error_message[:80]}...</p>' if error_message else ''}
    </div>
    <div class="event-status">
        <svg viewBox="0 0 24 24" width="14" height="14">
            <path d="{status_icon}" fill="currentColor"/>
        </svg>
    </div>
    <span class="event-time">{self._format_time(timestamp)}</span>
</div>''')

        return f'''
<div class="events-section">
    <div class="section-header">
        <span>Recent Events</span>
        <span class="event-count">{len(events)}</span>
    </div>
    <div class="events-feed" id="eventsFeed">
        {''.join(events_html) if events_html else '<div class="empty-state">No events recorded yet</div>'}
    </div>
</div>'''

    def _get_pattern_color(self, pattern_type: str) -> str:
        """Get color for pattern type."""
        colors = {
            "repetitive_action": "#D4A054",
            "error_recovery": "#C47070",
            "workflow_sequence": "#7EA8BE",
            "tool_preference": "#B87333",
            "efficiency_opportunity": "#78B89A",
            "common_error": "#C47070",
            "success_pattern": "#78B89A",
        }
        return colors.get(pattern_type, "#A8A29E")

    def _format_time(self, timestamp: str) -> str:
        """Format timestamp for display."""
        if not timestamp:
            return ""
        try:
            dt = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
            now = datetime.now()
            diff = now - dt.replace(tzinfo=None)
            if diff.seconds < 60:
                return "just now"
            elif diff.seconds < 3600:
                return f"{diff.seconds // 60}m ago"
            elif diff.seconds < 86400:
                return f"{diff.seconds // 3600}h ago"
            else:
                return dt.strftime("%m/%d %H:%M")
        except (ValueError, TypeError):
            return ""

    def generate_css(self) -> str:
        """Generate CSS for the feedback stream."""
        return '''
.feedback-stream {
    background: linear-gradient(145deg, #111111, #0a0a0a);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px;
    font-family: "Segoe UI", sans-serif;
    color: #F5F0EB;
    max-height: 600px;
    overflow: hidden;
    display: flex;
    flex-direction: column;
}

.stream-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    margin-bottom: 16px;
}

.stream-title {
    display: flex;
    align-items: center;
    gap: 10px;
    font-size: 15px;
    font-weight: 600;
}

.stream-metrics {
    display: flex;
    gap: 20px;
}

.metric {
    display: flex;
    flex-direction: column;
    align-items: center;
}

.metric-value {
    font-size: 16px;
    font-weight: 700;
    color: #F5F0EB;
}

.metric-label {
    font-size: 10px;
    color: #A8A29E;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

/* Sections */
.section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    font-size: 12px;
    font-weight: 600;
    color: #A8A29E;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}

.refresh-btn {
    background: none;
    border: none;
    color: #A8A29E;
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    transition: all 0.2s;
}

.refresh-btn:hover {
    background: rgba(255,255,255,0.1);
    color: #F5F0EB;
}

/* Insights */
.insights-section {
    margin-bottom: 16px;
}

.insight-card {
    display: flex;
    gap: 12px;
    padding: 12px;
    background: rgba(212, 160, 84, 0.08);
    border: 1px solid rgba(212, 160, 84, 0.15);
    border-radius: 10px;
    margin-bottom: 8px;
}

.insight-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(212, 160, 84, 0.15);
    border-radius: 8px;
}

.insight-content {
    flex: 1;
    min-width: 0;
}

.insight-text {
    font-size: 13px;
    line-height: 1.5;
    color: #E8E0D8;
    margin: 0 0 4px 0;
}

.insight-time {
    font-size: 11px;
    color: #78716C;
}

/* Patterns */
.patterns-section {
    margin-bottom: 16px;
}

.patterns-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
}

.pattern-card {
    padding: 12px;
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.06);
    border-left-width: 3px;
    border-radius: 8px;
}

.pattern-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 6px;
}

.pattern-type {
    font-size: 11px;
    font-weight: 600;
    color: #A8A29E;
    flex: 1;
}

.pattern-confidence {
    font-size: 10px;
    color: #78716C;
    background: rgba(255,255,255,0.05);
    padding: 2px 6px;
    border-radius: 8px;
}

.pattern-description {
    font-size: 12px;
    color: #C9C5C0;
    margin: 0 0 4px 0;
    line-height: 1.4;
}

.pattern-recommendation {
    font-size: 11px;
    color: #78B89A;
    font-style: italic;
    margin: 0 0 4px 0;
}

.pattern-meta {
    font-size: 10px;
    color: #78716C;
}

/* Events */
.events-section {
    flex: 1;
    min-height: 0;
    display: flex;
    flex-direction: column;
}

.event-count, .pattern-count {
    font-size: 11px;
    background: rgba(184, 115, 51, 0.2);
    color: #B87333;
    padding: 2px 8px;
    border-radius: 10px;
    font-weight: 600;
}

.events-feed {
    flex: 1;
    overflow-y: auto;
    padding-right: 8px;
}

.events-feed::-webkit-scrollbar {
    width: 4px;
}

.events-feed::-webkit-scrollbar-track {
    background: rgba(255,255,255,0.02);
}

.events-feed::-webkit-scrollbar-thumb {
    background: rgba(255,255,255,0.1);
    border-radius: 2px;
}

.event-item {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px;
    background: rgba(255,255,255,0.02);
    border-radius: 8px;
    margin-bottom: 6px;
    transition: all 0.2s;
    animation: slideIn 0.3s ease-out forwards;
    opacity: 0;
}

@keyframes slideIn {
    from {
        opacity: 0;
        transform: translateX(-10px);
    }
    to {
        opacity: 1;
        transform: translateX(0);
    }
}

.event-item:hover {
    background: rgba(255,255,255,0.04);
}

.event-item.success .event-icon {
    color: #78B89A;
}

.event-item.failure .event-icon {
    color: #C47070;
}

.event-item.success .event-status {
    color: #78B89A;
}

.event-item.failure .event-status {
    color: #C47070;
}

.event-icon {
    flex-shrink: 0;
    width: 32px;
    height: 32px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.05);
    border-radius: 8px;
}

.event-content {
    flex: 1;
    min-width: 0;
}

.event-header {
    display: flex;
    align-items: center;
    gap: 8px;
}

.event-tool {
    font-size: 13px;
    font-weight: 600;
    color: #F5F0EB;
}

.event-duration {
    font-size: 11px;
    color: #78716C;
}

.event-error {
    font-size: 11px;
    color: #C47070;
    margin: 4px 0 0 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.event-status {
    flex-shrink: 0;
}

.event-time {
    font-size: 10px;
    color: #78716C;
    flex-shrink: 0;
}

.empty-state {
    text-align: center;
    padding: 40px 20px;
    color: #78716C;
    font-size: 13px;
}
'''

    def generate_javascript(self) -> str:
        """Generate JavaScript for real-time updates."""
        return '''
let feedbackEventSource = null;

function initFeedbackStream() {
    // Connect to WebSocket for real-time updates
    const wsUrl = `ws://${window.location.host}/ws`;
    const ws = new WebSocket(wsUrl);

    ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        if (data.event_type === "tool_executed" || data.event_type === "tool_failed") {
            addEventToFeed(data.payload);
        } else if (data.event_type === "pattern_detected") {
            addPatternCard(data.payload);
        } else if (data.event_type === "insight_generated") {
            addInsightCard(data.payload);
        }
    };

    ws.onerror = () => {
        console.log("WebSocket error, falling back to polling");
        startPolling();
    };
}

function startPolling() {
    setInterval(refreshFeedback, 5000);
}

function addEventToFeed(event) {
    const feed = document.getElementById("eventsFeed");
    if (!feed) return;

    const emptyState = feed.querySelector(".empty-state");
    if (emptyState) emptyState.remove();

    const eventHtml = createEventElement(event);
    feed.insertAdjacentHTML("afterbegin", eventHtml);

    // Remove old events
    const items = feed.querySelectorAll(".event-item");
    if (items.length > 15) {
        items[items.length - 1].remove();
    }
}

function createEventElement(event) {
    const statusClass = event.success ? "success" : "failure";
    const statusIcon = event.success
        ? "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"
        : "M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z";

    return `
        <div class="event-item ${statusClass}">
            <div class="event-icon">
                <svg viewBox="0 0 24 24" width="18" height="18">
                    <circle cx="12" cy="12" r="10" fill="currentColor" opacity="0.2"/>
                </svg>
            </div>
            <div class="event-content">
                <div class="event-header">
                    <span class="event-tool">${event.tool_name}</span>
                    <span class="event-duration">${event.duration_ms}ms</span>
                </div>
            </div>
            <div class="event-status">
                <svg viewBox="0 0 24 24" width="14" height="14">
                    <path d="${statusIcon}" fill="currentColor"/>
                </svg>
            </div>
            <span class="event-time">just now</span>
        </div>
    `;
}

function refreshInsights() {
    fetch("/api/feedback/insights")
        .then(r => r.json())
        .then(data => {
            // Update insights section
            window.dispatchEvent(new CustomEvent("feedbackInsightsUpdate", { detail: data }));
        })
        .catch(console.error);
}

function refreshFeedback() {
    fetch("/api/feedback/history?limit=15")
        .then(r => r.json())
        .then(data => {
            // Full refresh handled by dashboard
            window.dispatchEvent(new CustomEvent("feedbackStreamUpdate", { detail: data }));
        })
        .catch(console.error);
}

// Initialize on load
if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initFeedbackStream);
} else {
    initFeedbackStream();
}
'''

    def generate_html_component(
        self,
        events: Optional[List[Dict]] = None,
        patterns: Optional[List[Dict]] = None,
        insights: Optional[List[Dict]] = None,
        metrics: Optional[Dict] = None,
        include_styles: bool = True,
        include_scripts: bool = True,
    ) -> str:
        """Generate complete HTML component."""
        html = ['<div id="feedbackStreamContainer">']

        if include_styles:
            html.append(f'<style>{self.generate_css()}</style>')

        html.append(self.generate_stream_html(events, patterns, insights, metrics))

        if include_scripts:
            html.append(f'<script>{self.generate_javascript()}</script>')

        html.append('</div>')
        return '\n'.join(html)


# ── Factory Function ────────────────────────────────────────────────────────


def generate_feedback_stream(
    events: Optional[List[Dict]] = None,
    patterns: Optional[List[Dict]] = None,
    insights: Optional[List[Dict]] = None,
    metrics: Optional[Dict] = None,
    config: Optional[FeedbackStreamConfig] = None,
) -> str:
    """Factory function to generate feedback stream HTML."""
    generator = FeedbackStreamGenerator(config)
    return generator.generate_html_component(events, patterns, insights, metrics)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    """CLI to generate and preview the feedback stream."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Feedback Stream Generator"
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="Generate demo with sample data",
    )
    args = parser.parse_args()

    # Demo data
    if args.demo:
        events = [
            {"tool_name": "Read", "success": True, "duration_ms": 45, "timestamp": datetime.now().isoformat()},
            {"tool_name": "Grep", "success": True, "duration_ms": 120, "timestamp": datetime.now().isoformat()},
            {"tool_name": "Edit", "success": True, "duration_ms": 85, "timestamp": datetime.now().isoformat()},
            {"tool_name": "Bash", "success": False, "duration_ms": 2500, "error_message": "Command not found: invalid_command", "timestamp": datetime.now().isoformat()},
            {"tool_name": "Write", "success": True, "duration_ms": 62, "timestamp": datetime.now().isoformat()},
        ]
        patterns = [
            {"pattern_type": "workflow_sequence", "description": "Common pattern: Read -> Edit -> Write", "frequency": 12, "confidence": 0.85},
            {"pattern_type": "tool_preference", "description": "Strong preference for Grep (35% of uses)", "frequency": 45, "confidence": 0.9},
        ]
        insights = [
            {"text": "Your success rate has improved by 15% this session. The workflow optimizations are paying off!", "generated_at": datetime.now().isoformat()},
        ]
        metrics = {"total_events": 156, "success_rate": 0.94, "avg_duration_ms": 185}
    else:
        events = None
        patterns = None
        insights = None
        metrics = None

    generator = FeedbackStreamGenerator()
    output = generator.generate_html_component(events, patterns, insights, metrics)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Feedback Stream</title></head><body style="background:#0a0a0a;padding:40px;">{output}</body></html>')
        print(f"Generated: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
