#!/usr/bin/env python3
# Modified: 2026-02-07T15:45:00Z | Author: COPILOT | Change: Initial creation of learning panel component
"""
Learning Panel UI Component.

Generates the interactive learning panel HTML/CSS/JS for the SLATE dashboard.

Features:
- Current step display with AI narrator
- Progress bar with XP counter and level
- Achievement badges (unlocked/locked)
- Hint system with progressive reveal
- Skip/Next controls
- Streak indicator
"""

from dataclasses import dataclass
from typing import List, Optional, Dict, Any


# Achievement icons (inline SVG paths)
ACHIEVEMENT_ICONS = {
    "first_step": "M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z",
    "curious_mind": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 17h-2v-2h2v2zm2.07-7.75l-.9.92C13.45 12.9 13 13.5 13 15h-2v-.5c0-1.1.45-2.1 1.17-2.83l1.24-1.26c.37-.36.59-.86.59-1.41 0-1.1-.9-2-2-2s-2 .9-2 2H8c0-2.21 1.79-4 4-4s4 1.79 4 4c0 .88-.36 1.68-.93 2.25z",
    "quick_learner": "M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9zm-1 5v5l4.28 2.54.72-1.21-3.5-2.08V8H12z",
    "code_warrior": "M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z",
    "test_master": "M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z",
    "deployer": "M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z",
    "feedback_guru": "M20 2H4c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h14l4 4V4c0-1.1-.9-2-2-2zm-2 12H6v-2h12v2zm0-3H6V9h12v2zm0-3H6V6h12v2z",
    "streak_3": "M13.5.67s.74 2.65.74 4.8c0 2.06-1.35 3.73-3.41 3.73-2.07 0-3.63-1.67-3.63-3.73l.03-.36C5.21 7.51 4 10.62 4 14c0 4.42 3.58 8 8 8s8-3.58 8-8C20 8.61 17.41 3.8 13.5.67zM11.71 19c-1.78 0-3.22-1.4-3.22-3.14 0-1.62 1.05-2.76 2.81-3.12 1.77-.36 3.6-1.21 4.62-2.58.39 1.29.59 2.65.59 4.04 0 2.65-2.15 4.8-4.8 4.8z",
    "streak_7": "M17.66 11.2C17.43 10.9 17.15 10.64 16.89 10.38C16.22 9.78 15.46 9.35 14.82 8.72C13.33 7.26 13 4.85 13.95 3C13 3.23 12.17 3.75 11.46 4.32C8.87 6.4 7.85 10.07 9.07 13.22C9.11 13.32 9.15 13.42 9.15 13.55C9.15 13.77 9 13.97 8.8 14.05C8.57 14.15 8.33 14.09 8.14 13.93C8.08 13.88 8.04 13.83 8 13.76C6.87 12.33 6.69 10.28 7.45 8.64C5.78 10 4.87 12.3 5 14.47C5.06 14.97 5.12 15.47 5.29 15.97C5.43 16.57 5.7 17.17 6 17.7C7.08 19.43 8.95 20.67 10.96 20.92C13.1 21.19 15.39 20.8 17.03 19.32C18.86 17.66 19.5 15 18.56 12.72L18.43 12.46C18.22 12 17.66 11.2 17.66 11.2Z",
    "perfectionist": "M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z",
    "completionist": "M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z",
    "ai_whisperer": "M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z",
    "master": "M5 16L3 5l5.5 5L12 4l3.5 6L21 5l-2 11H5zm14 3c0 .6-.4 1-1 1H6c-.6 0-1-.4-1-1v-1h14v1z",
}

TIER_COLORS = {
    "beginner": "#78B89A",     # Sage green
    "intermediate": "#7EA8BE", # Steel blue
    "advanced": "#B87333",     # Copper
    "mastery": "#D4A054",      # Gold amber
}


@dataclass
class LearningPanelConfig:
    """Configuration for the learning panel."""
    panel_width: str = "100%"
    max_height: str = "500px"
    show_narrator: bool = True
    show_achievements: bool = True
    show_streak: bool = True
    animation_enabled: bool = True


class LearningPanelGenerator:
    """
    Generates interactive learning panel HTML/CSS/JS.
    """

    def __init__(self, config: Optional[LearningPanelConfig] = None):
        self.config = config or LearningPanelConfig()

    def generate_panel_html(
        self,
        current_step: Optional[Dict] = None,
        progress: Optional[Dict] = None,
        achievements: Optional[List[Dict]] = None,
    ) -> str:
        """Generate the complete learning panel HTML."""
        # Defaults
        if progress is None:
            progress = {
                "completed_steps": 0,
                "total_steps": 10,
                "total_xp": 0,
                "level": 1,
                "streak_days": 0,
            }

        if achievements is None:
            achievements = []

        if current_step is None:
            current_step = {
                "title": "Welcome to SLATE",
                "description": "Start your learning journey with SLATE.",
                "category": "introduction",
                "xp_reward": 10,
            }

        html_parts = [
            f'<div class="learning-panel" style="width: {self.config.panel_width}; max-height: {self.config.max_height};">',
            self._generate_header(progress),
            self._generate_progress_bar(progress),
        ]

        if self.config.show_narrator:
            html_parts.append(self._generate_narrator(current_step))

        html_parts.append(self._generate_step_content(current_step))
        html_parts.append(self._generate_controls())

        if self.config.show_achievements:
            html_parts.append(self._generate_achievements_section(achievements))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _generate_header(self, progress: Dict) -> str:
        """Generate panel header with level and XP."""
        level = progress.get("level", 1)
        total_xp = progress.get("total_xp", 0)
        streak = progress.get("streak_days", 0)

        streak_html = ""
        if self.config.show_streak and streak > 0:
            streak_html = f'''
<div class="streak-badge" title="{streak} day streak!">
    <svg viewBox="0 0 24 24" width="16" height="16">
        <path d="{ACHIEVEMENT_ICONS['streak_3']}" fill="#D4A054"/>
    </svg>
    <span>{streak}</span>
</div>'''

        return f'''
<div class="learning-header">
    <div class="level-badge">
        <span class="level-number">Lv.{level}</span>
        <span class="xp-count">{total_xp:,} XP</span>
    </div>
    <div class="header-title">
        <svg viewBox="0 0 24 24" width="20" height="20" class="header-icon">
            <path d="M12 3L1 9l4 2.18v6L12 21l7-3.82v-6l2-1.09V17h2V9L12 3zm6.82 6L12 12.72 5.18 9 12 5.28 18.82 9zM17 15.99l-5 2.73-5-2.73v-3.72L12 15l5-2.73v3.72z" fill="currentColor"/>
        </svg>
        <span>Interactive Learning</span>
    </div>
    {streak_html}
</div>'''

    def _generate_progress_bar(self, progress: Dict) -> str:
        """Generate XP progress bar."""
        total_xp = progress.get("total_xp", 0)
        level = progress.get("level", 1)
        completed = progress.get("completed_steps", 0)
        total = progress.get("total_steps", 10)

        # Calculate XP progress within current level
        xp_per_level = 100  # Simplified
        current_level_xp = total_xp % xp_per_level
        progress_percent = (current_level_xp / xp_per_level) * 100

        step_progress = (completed / max(total, 1)) * 100

        return f'''
<div class="progress-section">
    <div class="progress-row">
        <span class="progress-label">Level Progress</span>
        <span class="progress-value">{current_level_xp}/{xp_per_level} XP</span>
    </div>
    <div class="progress-bar-container">
        <div class="progress-bar xp-bar" style="width: {progress_percent}%"></div>
    </div>

    <div class="progress-row" style="margin-top: 12px;">
        <span class="progress-label">Path Progress</span>
        <span class="progress-value">{completed}/{total} steps</span>
    </div>
    <div class="progress-bar-container">
        <div class="progress-bar path-bar" style="width: {step_progress}%"></div>
    </div>
</div>'''

    def _generate_narrator(self, current_step: Dict) -> str:
        """Generate AI narrator section."""
        category = current_step.get("category", "general")
        narrator_message = self._get_narrator_message(category)

        return f'''
<div class="narrator-section">
    <div class="narrator-avatar">
        <svg viewBox="0 0 24 24" width="32" height="32">
            <circle cx="12" cy="12" r="10" fill="#B87333" opacity="0.2"/>
            <path d="{ACHIEVEMENT_ICONS['ai_whisperer']}" fill="#B87333" transform="scale(0.8) translate(3, 3)"/>
        </svg>
    </div>
    <div class="narrator-bubble">
        <div class="narrator-message">{narrator_message}</div>
        <div class="narrator-typing" id="narratorTyping" style="display: none;">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
        </div>
    </div>
</div>'''

    def _get_narrator_message(self, category: str) -> str:
        """Get contextual narrator message."""
        messages = {
            "introduction": "Welcome! I'll guide you through SLATE's features. Let's start with the basics.",
            "slate-core": "SLATE's core architecture is elegant. Understanding it will unlock powerful capabilities.",
            "ai-integration": "AI integration is where SLATE shines. Let me show you how to leverage local models.",
            "workflow": "Workflows automate your development cycle. Master these and watch productivity soar.",
            "gpu": "Dual-GPU optimization is advanced territory. Ready to push performance limits?",
            "general": "Each step brings you closer to mastery. Take your time and experiment!",
        }
        return messages.get(category, messages["general"])

    def _generate_step_content(self, current_step: Dict) -> str:
        """Generate current step content."""
        title = current_step.get("title", "Current Step")
        description = current_step.get("description", "")
        xp_reward = current_step.get("xp_reward", 10)
        hints = current_step.get("hints", [])
        category = current_step.get("category", "general")

        category_color = {
            "slate-core": "#B87333",
            "ai-integration": "#7EA8BE",
            "workflow": "#78B89A",
            "gpu": "#D4A054",
        }.get(category, "#A8A29E")

        hints_html = ""
        if hints:
            hints_html = f'''
<div class="hints-section">
    <button class="hint-toggle" onclick="toggleHints()">
        <svg viewBox="0 0 24 24" width="16" height="16">
            <path d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z" fill="currentColor"/>
        </svg>
        Show Hints ({len(hints)} available)
    </button>
    <div class="hints-list" id="hintsList" style="display: none;">
        {''.join(f'<div class="hint-item"><span class="hint-number">{i+1}</span>{hint}</div>' for i, hint in enumerate(hints))}
    </div>
</div>'''

        return f'''
<div class="step-content">
    <div class="step-header">
        <span class="step-category" style="color: {category_color};">{category.replace("-", " ").title()}</span>
        <span class="step-xp">+{xp_reward} XP</span>
    </div>
    <h3 class="step-title">{title}</h3>
    <p class="step-description">{description}</p>
    {hints_html}
</div>'''

    def _generate_controls(self) -> str:
        """Generate step navigation controls."""
        return '''
<div class="step-controls">
    <button class="control-btn secondary" onclick="skipStep()">
        <span>Skip</span>
    </button>
    <button class="control-btn primary" onclick="completeStep()">
        <span>Complete Step</span>
        <svg viewBox="0 0 24 24" width="18" height="18">
            <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" fill="currentColor"/>
        </svg>
    </button>
</div>'''

    def _generate_achievements_section(self, achievements: List[Dict]) -> str:
        """Generate achievements display."""
        if not achievements:
            return '''
<div class="achievements-section collapsed">
    <div class="achievements-header" onclick="toggleAchievements()">
        <span>Achievements</span>
        <span class="achievement-count">0 unlocked</span>
    </div>
</div>'''

        unlocked = [a for a in achievements if a.get("unlocked", False)]
        locked = [a for a in achievements if not a.get("unlocked", False)]

        unlocked_html = ""
        for ach in unlocked[:6]:
            icon_path = ACHIEVEMENT_ICONS.get(ach.get("id", ""), ACHIEVEMENT_ICONS["first_step"])
            tier = ach.get("tier", "beginner")
            tier_color = TIER_COLORS.get(tier, TIER_COLORS["beginner"])

            unlocked_html += f'''
<div class="achievement-badge unlocked" title="{ach.get('name', '')}: {ach.get('description', '')}">
    <svg viewBox="0 0 24 24" width="24" height="24">
        <path d="{icon_path}" fill="{tier_color}"/>
    </svg>
</div>'''

        locked_html = ""
        for ach in locked[:4]:
            locked_html += '''
<div class="achievement-badge locked" title="Locked achievement">
    <svg viewBox="0 0 24 24" width="24" height="24">
        <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z" fill="currentColor" opacity="0.3"/>
    </svg>
</div>'''

        return f'''
<div class="achievements-section" id="achievementsSection">
    <div class="achievements-header" onclick="toggleAchievements()">
        <span>Achievements</span>
        <span class="achievement-count">{len(unlocked)} unlocked</span>
        <svg viewBox="0 0 24 24" width="16" height="16" class="expand-icon">
            <path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z" fill="currentColor"/>
        </svg>
    </div>
    <div class="achievements-grid" id="achievementsGrid">
        {unlocked_html}
        {locked_html}
    </div>
</div>'''

    def generate_css(self) -> str:
        """Generate CSS for the learning panel."""
        return '''
.learning-panel {
    background: linear-gradient(145deg, #111111, #0a0a0a);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 16px;
    padding: 20px;
    font-family: "Segoe UI", sans-serif;
    color: #F5F0EB;
    overflow: hidden;
}

.learning-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;
    padding-bottom: 16px;
    border-bottom: 1px solid rgba(255,255,255,0.06);
}

.level-badge {
    display: flex;
    flex-direction: column;
    gap: 2px;
}

.level-number {
    font-size: 18px;
    font-weight: 700;
    color: #B87333;
}

.xp-count {
    font-size: 12px;
    color: #A8A29E;
}

.header-title {
    display: flex;
    align-items: center;
    gap: 8px;
    color: #A8A29E;
    font-size: 14px;
}

.header-icon {
    color: #B87333;
}

.streak-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    background: rgba(212, 160, 84, 0.15);
    padding: 4px 10px;
    border-radius: 12px;
    font-size: 13px;
    font-weight: 600;
    color: #D4A054;
}

/* Progress Section */
.progress-section {
    margin-bottom: 20px;
}

.progress-row {
    display: flex;
    justify-content: space-between;
    margin-bottom: 6px;
    font-size: 12px;
}

.progress-label {
    color: #A8A29E;
}

.progress-value {
    color: #F5F0EB;
    font-weight: 500;
}

.progress-bar-container {
    height: 6px;
    background: rgba(255,255,255,0.06);
    border-radius: 3px;
    overflow: hidden;
}

.progress-bar {
    height: 100%;
    border-radius: 3px;
    transition: width 0.5s ease-out;
}

.progress-bar.xp-bar {
    background: linear-gradient(90deg, #B87333, #C9956B);
}

.progress-bar.path-bar {
    background: linear-gradient(90deg, #78B89A, #9BCFB3);
}

/* Narrator Section */
.narrator-section {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    padding: 16px;
    background: rgba(184, 115, 51, 0.06);
    border-radius: 12px;
    border: 1px solid rgba(184, 115, 51, 0.12);
}

.narrator-avatar {
    flex-shrink: 0;
}

.narrator-bubble {
    flex: 1;
}

.narrator-message {
    font-size: 14px;
    line-height: 1.5;
    color: #E8E0D8;
}

.narrator-typing {
    display: flex;
    gap: 4px;
    padding-top: 8px;
}

.typing-dot {
    width: 6px;
    height: 6px;
    background: #B87333;
    border-radius: 50%;
    animation: typingBounce 1.4s infinite;
}

.typing-dot:nth-child(2) { animation-delay: 0.2s; }
.typing-dot:nth-child(3) { animation-delay: 0.4s; }

@keyframes typingBounce {
    0%, 60%, 100% { transform: translateY(0); }
    30% { transform: translateY(-6px); }
}

/* Step Content */
.step-content {
    margin-bottom: 20px;
}

.step-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
}

.step-category {
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.1em;
}

.step-xp {
    font-size: 12px;
    font-weight: 600;
    color: #78B89A;
    background: rgba(120, 184, 154, 0.12);
    padding: 3px 8px;
    border-radius: 10px;
}

.step-title {
    font-size: 18px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: #F5F0EB;
}

.step-description {
    font-size: 14px;
    line-height: 1.6;
    color: #A8A29E;
    margin: 0;
}

/* Hints */
.hints-section {
    margin-top: 16px;
}

.hint-toggle {
    display: flex;
    align-items: center;
    gap: 6px;
    background: none;
    border: 1px solid rgba(255,255,255,0.1);
    border-radius: 8px;
    padding: 8px 12px;
    color: #A8A29E;
    font-size: 12px;
    cursor: pointer;
    transition: all 0.2s;
}

.hint-toggle:hover {
    background: rgba(255,255,255,0.05);
    color: #F5F0EB;
}

.hints-list {
    margin-top: 12px;
    padding: 12px;
    background: rgba(0,0,0,0.3);
    border-radius: 8px;
}

.hint-item {
    display: flex;
    gap: 10px;
    padding: 8px 0;
    font-size: 13px;
    color: #C9C5C0;
    border-bottom: 1px solid rgba(255,255,255,0.04);
}

.hint-item:last-child {
    border-bottom: none;
}

.hint-number {
    flex-shrink: 0;
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(184, 115, 51, 0.2);
    color: #B87333;
    border-radius: 50%;
    font-size: 11px;
    font-weight: 600;
}

/* Controls */
.step-controls {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
}

.control-btn {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 16px;
    border-radius: 10px;
    font-size: 14px;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s;
}

.control-btn.secondary {
    background: rgba(255,255,255,0.05);
    border: 1px solid rgba(255,255,255,0.1);
    color: #A8A29E;
}

.control-btn.secondary:hover {
    background: rgba(255,255,255,0.08);
    color: #F5F0EB;
}

.control-btn.primary {
    background: linear-gradient(135deg, #B87333, #9A5F28);
    border: none;
    color: #0a0a0a;
}

.control-btn.primary:hover {
    background: linear-gradient(135deg, #C9956B, #B87333);
    transform: translateY(-1px);
}

/* Achievements */
.achievements-section {
    border-top: 1px solid rgba(255,255,255,0.06);
    padding-top: 16px;
}

.achievements-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    cursor: pointer;
    padding: 8px 0;
}

.achievements-header span:first-child {
    font-size: 14px;
    font-weight: 600;
}

.achievement-count {
    font-size: 12px;
    color: #A8A29E;
}

.expand-icon {
    color: #A8A29E;
    transition: transform 0.2s;
}

.achievements-section.expanded .expand-icon {
    transform: rotate(180deg);
}

.achievements-grid {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    padding-top: 12px;
    max-height: 0;
    overflow: hidden;
    transition: max-height 0.3s ease-out;
}

.achievements-section.expanded .achievements-grid {
    max-height: 200px;
}

.achievement-badge {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(255,255,255,0.04);
    border-radius: 10px;
    transition: all 0.2s;
}

.achievement-badge.unlocked:hover {
    transform: scale(1.1);
    background: rgba(255,255,255,0.08);
}

.achievement-badge.locked {
    opacity: 0.4;
}
'''

    def generate_javascript(self) -> str:
        """Generate JavaScript for interactivity."""
        return '''
function toggleHints() {
    const hintsList = document.getElementById("hintsList");
    if (hintsList) {
        hintsList.style.display = hintsList.style.display === "none" ? "block" : "none";
    }
}

function toggleAchievements() {
    const section = document.getElementById("achievementsSection");
    if (section) {
        section.classList.toggle("expanded");
    }
}

function skipStep() {
    // Get current step and skip
    fetch("/api/interactive/current-step")
        .then(r => r.json())
        .then(data => {
            if (data.step) {
                return fetch("/api/interactive/complete-step", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        step_id: data.step.id,
                        result: { skipped: true }
                    })
                });
            }
        })
        .then(() => refreshLearningPanel())
        .catch(console.error);
}

function completeStep() {
    fetch("/api/interactive/current-step")
        .then(r => r.json())
        .then(data => {
            if (data.step) {
                return fetch("/api/interactive/complete-step", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({
                        step_id: data.step.id,
                        result: { completed: true }
                    })
                });
            }
        })
        .then(r => r.json())
        .then(result => {
            // Show XP animation
            if (result.xp_gained) {
                showXPGain(result.xp_gained);
            }
            // Check for achievements
            if (result.new_achievements && result.new_achievements.length > 0) {
                showAchievementUnlock(result.new_achievements[0]);
            }
            refreshLearningPanel();
        })
        .catch(console.error);
}

function showXPGain(xp) {
    const toast = document.createElement("div");
    toast.className = "xp-toast";
    toast.textContent = `+${xp} XP`;
    document.body.appendChild(toast);
    setTimeout(() => toast.remove(), 2000);
}

function showAchievementUnlock(achievement) {
    const modal = document.createElement("div");
    modal.className = "achievement-modal";
    modal.innerHTML = `
        <div class="achievement-modal-content">
            <div class="achievement-icon">&#127942;</div>
            <h3>Achievement Unlocked!</h3>
            <p>${achievement.name}</p>
        </div>
    `;
    document.body.appendChild(modal);
    setTimeout(() => modal.remove(), 3000);
}

function refreshLearningPanel() {
    window.dispatchEvent(new CustomEvent("learningPanelRefresh"));
}

// Add toast styles dynamically
const toastStyle = document.createElement("style");
toastStyle.textContent = `
    .xp-toast {
        position: fixed;
        top: 20px;
        right: 20px;
        background: linear-gradient(135deg, #78B89A, #5A9A7C);
        color: #0a0a0a;
        padding: 12px 24px;
        border-radius: 8px;
        font-weight: 700;
        font-size: 16px;
        animation: toastSlide 2s ease-out forwards;
        z-index: 9999;
    }
    @keyframes toastSlide {
        0% { transform: translateX(100px); opacity: 0; }
        10% { transform: translateX(0); opacity: 1; }
        90% { transform: translateX(0); opacity: 1; }
        100% { transform: translateX(100px); opacity: 0; }
    }
    .achievement-modal {
        position: fixed;
        top: 0;
        left: 0;
        right: 0;
        bottom: 0;
        background: rgba(0,0,0,0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 9999;
        animation: fadeIn 0.3s ease-out;
    }
    .achievement-modal-content {
        background: linear-gradient(145deg, #1a1a1a, #111);
        padding: 40px;
        border-radius: 16px;
        text-align: center;
        border: 2px solid #B87333;
        animation: popIn 0.4s ease-out;
    }
    .achievement-icon { font-size: 48px; margin-bottom: 16px; }
    .achievement-modal h3 { color: #B87333; margin: 0 0 8px 0; }
    .achievement-modal p { color: #F5F0EB; margin: 0; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    @keyframes popIn { from { transform: scale(0.8); } to { transform: scale(1); } }
`;
document.head.appendChild(toastStyle);
'''

    def generate_html_component(
        self,
        current_step: Optional[Dict] = None,
        progress: Optional[Dict] = None,
        achievements: Optional[List[Dict]] = None,
        include_styles: bool = True,
        include_scripts: bool = True,
    ) -> str:
        """Generate complete HTML component."""
        html = ['<div id="learningPanelContainer">']

        if include_styles:
            html.append(f'<style>{self.generate_css()}</style>')

        html.append(self.generate_panel_html(current_step, progress, achievements))

        if include_scripts:
            html.append(f'<script>{self.generate_javascript()}</script>')

        html.append('</div>')
        return '\n'.join(html)


# ── Factory Function ────────────────────────────────────────────────────────


def generate_learning_panel(
    current_step: Optional[Dict] = None,
    progress: Optional[Dict] = None,
    achievements: Optional[List[Dict]] = None,
    config: Optional[LearningPanelConfig] = None,
) -> str:
    """Factory function to generate learning panel HTML."""
    generator = LearningPanelGenerator(config)
    return generator.generate_html_component(current_step, progress, achievements)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    """CLI to generate and preview the learning panel."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Learning Panel Generator"
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
        current_step = {
            "id": "step_1",
            "title": "Understanding SLATE Architecture",
            "description": "Learn how SLATE's modular architecture enables powerful AI orchestration with local-first inference.",
            "category": "slate-core",
            "xp_reward": 25,
            "hints": [
                "Start by exploring the slate/ directory structure",
                "Check CLAUDE.md for the full system overview",
                "Try running slate_status.py to see active components",
            ],
        }
        progress = {
            "completed_steps": 5,
            "total_steps": 34,
            "total_xp": 175,
            "level": 2,
            "streak_days": 3,
        }
        achievements = [
            {"id": "first_step", "name": "First Step", "tier": "beginner", "unlocked": True},
            {"id": "curious_mind", "name": "Curious Mind", "tier": "beginner", "unlocked": True},
            {"id": "code_warrior", "name": "Code Warrior", "tier": "intermediate", "unlocked": False},
        ]
    else:
        current_step = None
        progress = None
        achievements = None

    generator = LearningPanelGenerator()
    output = generator.generate_html_component(current_step, progress, achievements)

    if args.output:
        with open(args.output, 'w') as f:
            f.write(f'<!DOCTYPE html><html><head><meta charset="UTF-8"><title>Learning Panel</title></head><body style="background:#0a0a0a;padding:40px;">{output}</body></html>')
        print(f"Generated: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
