#!/usr/bin/env python3
# Modified: 2026-02-07T15:30:00Z | Author: COPILOT | Change: Initial creation of dev cycle ring component
"""
Development Cycle Ring Visualization Component.

Generates an animated SVG ring showing the 5-stage development cycle:
PLAN -> CODE -> TEST -> DEPLOY -> FEEDBACK

Features:
- 5 arc segments (72 degrees each)
- Active stage pulses with copper glow
- Progress arc within current stage
- Animated transitions between stages
- Click handlers for stage details
- Mini variant for compact displays
"""

import math
from dataclasses import dataclass
from typing import Optional

# Stage colors using SLATE design system
STAGE_COLORS = {
    "PLAN": "#7EA8BE",      # Steel blue - planning/thinking
    "CODE": "#B87333",      # Copper - active development
    "TEST": "#D4A054",      # Warm amber - validation
    "DEPLOY": "#78B89A",    # Sage green - success/release
    "FEEDBACK": "#9B89B3",  # Muted purple - reflection
}

STAGE_ICONS = {
    "PLAN": "M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2",
    "CODE": "M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4",
    "TEST": "M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
    "DEPLOY": "M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12",
    "FEEDBACK": "M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z",
}


@dataclass
class RingConfig:
    """Configuration for the ring visualization."""
    size: int = 300
    stroke_width: int = 24
    inner_radius: int = 80
    gap_degrees: float = 4.0
    animation_duration: float = 0.5
    glow_intensity: float = 20.0


class DevCycleRingGenerator:
    """
    Generates animated SVG ring visualization for development cycle.
    """

    STAGES = ["PLAN", "CODE", "TEST", "DEPLOY", "FEEDBACK"]
    SEGMENT_DEGREES = 360 / 5  # 72 degrees per segment

    def __init__(self, config: Optional[RingConfig] = None):
        self.config = config or RingConfig()
        self.center = self.config.size // 2
        self.outer_radius = (self.config.size - self.config.stroke_width) // 2 - 10
        self.inner_radius = self.config.inner_radius

    def generate_ring_svg(
        self,
        current_stage: str = "PLAN",
        stage_progress: float = 0.0,
        compact: bool = False,
    ) -> str:
        """Generate the complete SVG ring visualization."""
        size = self.config.size if not compact else self.config.size // 2
        scale = 0.5 if compact else 1.0

        svg_parts = [
            f'<svg viewBox="0 0 {self.config.size} {self.config.size}" ',
            f'width="{size}" height="{size}" class="dev-cycle-ring">',
            self._generate_defs(current_stage),
            f'<g transform="scale({scale}) translate({0 if scale == 1 else self.center}, {0 if scale == 1 else self.center})">',
        ]

        # Background circle
        svg_parts.append(
            f'<circle cx="{self.center}" cy="{self.center}" r="{self.outer_radius}" '
            f'fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="{self.config.stroke_width}"/>'
        )

        # Stage segments
        for i, stage in enumerate(self.STAGES):
            is_active = stage == current_stage
            segment_svg = self._generate_segment(
                stage=stage,
                index=i,
                is_active=is_active,
                progress=stage_progress if is_active else (1.0 if self._is_completed(stage, current_stage) else 0.0),
            )
            svg_parts.append(segment_svg)

        # Center content
        if not compact:
            svg_parts.append(self._generate_center_content(current_stage, stage_progress))

        # Stage labels (not for compact)
        if not compact:
            svg_parts.append(self._generate_stage_labels(current_stage))

        svg_parts.append('</g></svg>')
        return '\n'.join(svg_parts)

    def _generate_defs(self, current_stage: str) -> str:
        """Generate SVG definitions (gradients, filters)."""
        color = STAGE_COLORS.get(current_stage, STAGE_COLORS["PLAN"])

        return f'''
<defs>
    <!-- Active stage glow filter -->
    <filter id="activeGlow" x="-50%" y="-50%" width="200%" height="200%">
        <feGaussianBlur in="SourceGraphic" stdDeviation="{self.config.glow_intensity / 3}" result="blur"/>
        <feColorMatrix in="blur" type="matrix"
            values="1 0 0 0 0
                    0 1 0 0 0
                    0 0 1 0 0
                    0 0 0 0.6 0"/>
        <feMerge>
            <feMergeNode/>
            <feMergeNode in="SourceGraphic"/>
        </feMerge>
    </filter>

    <!-- Progress gradient -->
    <linearGradient id="progressGradient" x1="0%" y1="0%" x2="100%" y2="0%">
        <stop offset="0%" stop-color="{color}" stop-opacity="1"/>
        <stop offset="100%" stop-color="{color}" stop-opacity="0.6"/>
    </linearGradient>

    <!-- Segment gradients -->
    {self._generate_segment_gradients()}

    <!-- Pulse animation -->
    <style>
        @keyframes stagePulse {{
            0%, 100% {{ filter: drop-shadow(0 0 5px var(--pulse-color)); opacity: 1; }}
            50% {{ filter: drop-shadow(0 0 {self.config.glow_intensity}px var(--pulse-color)); opacity: 0.9; }}
        }}
        @keyframes stageTransition {{
            0% {{ transform: scale(1); }}
            50% {{ transform: scale(1.03); }}
            100% {{ transform: scale(1); }}
        }}
        @keyframes progressSweep {{
            0% {{ stroke-dashoffset: var(--dash-full); }}
            100% {{ stroke-dashoffset: var(--dash-target); }}
        }}
        .active-segment {{
            animation: stagePulse 2s ease-in-out infinite;
            --pulse-color: {color};
        }}
        .segment {{
            transition: all {self.config.animation_duration}s ease-out;
            cursor: pointer;
        }}
        .segment:hover {{
            filter: brightness(1.2);
            transform-origin: center;
        }}
        .progress-arc {{
            animation: progressSweep 1s ease-out forwards;
        }}
    </style>
</defs>'''

    def _generate_segment_gradients(self) -> str:
        """Generate gradient definitions for each segment."""
        gradients = []
        for stage, color in STAGE_COLORS.items():
            gradients.append(f'''
    <linearGradient id="gradient{stage}" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" stop-color="{color}" stop-opacity="0.9"/>
        <stop offset="100%" stop-color="{color}" stop-opacity="0.6"/>
    </linearGradient>''')
        return '\n'.join(gradients)

    def _generate_segment(
        self,
        stage: str,
        index: int,
        is_active: bool,
        progress: float,
    ) -> str:
        """Generate a single arc segment."""
        # Calculate arc angles
        start_angle = index * self.SEGMENT_DEGREES - 90 + self.config.gap_degrees / 2
        end_angle = (index + 1) * self.SEGMENT_DEGREES - 90 - self.config.gap_degrees / 2
        arc_degrees = end_angle - start_angle

        # Create arc path
        arc_path = self._create_arc_path(
            self.center,
            self.center,
            self.outer_radius,
            start_angle,
            end_angle,
        )

        # Base segment
        color = STAGE_COLORS[stage]
        opacity = 1.0 if is_active else (0.7 if progress >= 1.0 else 0.3)
        segment_class = "segment active-segment" if is_active else "segment"

        segment = f'''
<g class="{segment_class}" data-stage="{stage}" onclick="selectStage('{stage}')">
    <path d="{arc_path}"
        fill="none"
        stroke="url(#gradient{stage})"
        stroke-width="{self.config.stroke_width}"
        stroke-linecap="round"
        opacity="{opacity}"
        {f'filter="url(#activeGlow)"' if is_active else ''}/>'''

        # Progress overlay for active segment
        if is_active and progress > 0:
            progress_arc = self._create_arc_path(
                self.center,
                self.center,
                self.outer_radius,
                start_angle,
                start_angle + arc_degrees * progress,
            )
            segment += f'''
    <path d="{progress_arc}"
        fill="none"
        stroke="{color}"
        stroke-width="{self.config.stroke_width + 2}"
        stroke-linecap="round"
        opacity="1"
        class="progress-arc"/>'''

        # Stage icon at midpoint
        mid_angle = (start_angle + end_angle) / 2
        icon_radius = self.outer_radius + self.config.stroke_width / 2 + 20
        icon_x = self.center + icon_radius * math.cos(math.radians(mid_angle))
        icon_y = self.center + icon_radius * math.sin(math.radians(mid_angle))

        segment += '</g>'
        return segment

    def _create_arc_path(
        self,
        cx: float,
        cy: float,
        radius: float,
        start_angle: float,
        end_angle: float,
    ) -> str:
        """Create SVG arc path string."""
        start_rad = math.radians(start_angle)
        end_rad = math.radians(end_angle)

        x1 = cx + radius * math.cos(start_rad)
        y1 = cy + radius * math.sin(start_rad)
        x2 = cx + radius * math.cos(end_rad)
        y2 = cy + radius * math.sin(end_rad)

        arc_sweep = end_angle - start_angle
        large_arc = 1 if arc_sweep > 180 else 0

        return f"M {x1:.2f} {y1:.2f} A {radius} {radius} 0 {large_arc} 1 {x2:.2f} {y2:.2f}"

    def _generate_center_content(self, current_stage: str, progress: float) -> str:
        """Generate center content with stage info and progress."""
        color = STAGE_COLORS[current_stage]

        return f'''
<g class="center-content">
    <!-- Center circle background -->
    <circle cx="{self.center}" cy="{self.center}" r="{self.inner_radius}"
        fill="#0a0a0a" stroke="rgba(255,255,255,0.1)" stroke-width="1"/>

    <!-- Stage icon -->
    <g transform="translate({self.center - 12}, {self.center - 30})">
        <path d="{STAGE_ICONS[current_stage]}"
            fill="none" stroke="{color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
    </g>

    <!-- Stage name -->
    <text x="{self.center}" y="{self.center + 10}"
        text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="16"
        font-weight="600" fill="{color}">{current_stage}</text>

    <!-- Progress percentage -->
    <text x="{self.center}" y="{self.center + 35}"
        text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="24"
        font-weight="700" fill="#F5F0EB">{int(progress * 100)}%</text>

    <!-- Progress label -->
    <text x="{self.center}" y="{self.center + 52}"
        text-anchor="middle" font-family="Segoe UI, sans-serif" font-size="11"
        fill="#A8A29E" text-transform="uppercase" letter-spacing="0.1em">Progress</text>
</g>'''

    def _generate_stage_labels(self, current_stage: str) -> str:
        """Generate labels around the ring."""
        labels = []
        label_radius = self.outer_radius + self.config.stroke_width / 2 + 35

        for i, stage in enumerate(self.STAGES):
            mid_angle = i * self.SEGMENT_DEGREES - 90 + self.SEGMENT_DEGREES / 2
            x = self.center + label_radius * math.cos(math.radians(mid_angle))
            y = self.center + label_radius * math.sin(math.radians(mid_angle))

            color = STAGE_COLORS[stage]
            is_active = stage == current_stage
            opacity = 1.0 if is_active else 0.6
            font_weight = "600" if is_active else "400"

            labels.append(f'''
<text x="{x:.2f}" y="{y:.2f}"
    text-anchor="middle" dominant-baseline="middle"
    font-family="Segoe UI, sans-serif" font-size="11"
    font-weight="{font_weight}" fill="{color}" opacity="{opacity}"
    class="stage-label">{stage}</text>''')

        return '\n'.join(labels)

    def _is_completed(self, stage: str, current_stage: str) -> bool:
        """Check if a stage is completed (before current)."""
        try:
            stage_idx = self.STAGES.index(stage)
            current_idx = self.STAGES.index(current_stage)
            return stage_idx < current_idx
        except ValueError:
            return False

    def generate_css(self) -> str:
        """Generate CSS for the ring component."""
        return '''
.dev-cycle-ring {
    filter: drop-shadow(0 4px 12px rgba(0,0,0,0.4));
}

.dev-cycle-ring .segment {
    transition: all 0.3s ease-out;
}

.dev-cycle-ring .segment:hover {
    filter: brightness(1.15);
}

.dev-cycle-ring .active-segment {
    --pulse-color: var(--sl-accent, #B87333);
}

.dev-cycle-ring .stage-label {
    pointer-events: none;
    user-select: none;
}

.dev-cycle-ring .center-content {
    pointer-events: none;
}

/* Mini variant styles */
.dev-cycle-ring-mini {
    width: 120px;
    height: 120px;
}

.dev-cycle-ring-mini .stage-label,
.dev-cycle-ring-mini .center-content {
    display: none;
}
'''

    def generate_javascript(self) -> str:
        """Generate JavaScript for interactivity."""
        return '''
function selectStage(stage) {
    // Dispatch custom event for stage selection
    window.dispatchEvent(new CustomEvent('devCycleStageSelect', {
        detail: { stage: stage }
    }));

    // Update via API
    fetch('/api/devcycle/transition', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ to_stage: stage })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            refreshDevCycleRing();
        }
    })
    .catch(console.error);
}

function refreshDevCycleRing() {
    fetch('/api/devcycle/visualization')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('devCycleRingContainer');
            if (container) {
                // Update will be handled by the dashboard
                window.dispatchEvent(new CustomEvent('devCycleUpdate', {
                    detail: data
                }));
            }
        })
        .catch(console.error);
}

// Auto-refresh every 30 seconds
setInterval(refreshDevCycleRing, 30000);
'''

    def generate_html_component(
        self,
        current_stage: str = "PLAN",
        stage_progress: float = 0.0,
        include_styles: bool = True,
        include_scripts: bool = True,
    ) -> str:
        """Generate complete HTML component."""
        html = ['<div id="devCycleRingContainer" class="dev-cycle-ring-container">']

        if include_styles:
            html.append(f'<style>{self.generate_css()}</style>')

        html.append(self.generate_ring_svg(current_stage, stage_progress))

        if include_scripts:
            html.append(f'<script>{self.generate_javascript()}</script>')

        html.append('</div>')
        return '\n'.join(html)


# ── Factory Function ────────────────────────────────────────────────────────


def generate_dev_cycle_ring(
    current_stage: str = "PLAN",
    stage_progress: float = 0.0,
    compact: bool = False,
    config: Optional[RingConfig] = None,
) -> str:
    """Factory function to generate dev cycle ring SVG."""
    generator = DevCycleRingGenerator(config)
    return generator.generate_ring_svg(current_stage, stage_progress, compact)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main():
    """CLI to generate and preview the ring component."""
    import argparse

    parser = argparse.ArgumentParser(
        description="SLATE Dev Cycle Ring Generator"
    )
    parser.add_argument(
        "--stage",
        choices=["PLAN", "CODE", "TEST", "DEPLOY", "FEEDBACK"],
        default="CODE",
        help="Current active stage",
    )
    parser.add_argument(
        "--progress",
        type=float,
        default=0.45,
        help="Stage progress (0.0-1.0)",
    )
    parser.add_argument(
        "--compact",
        action="store_true",
        help="Generate compact/mini version",
    )
    parser.add_argument(
        "--output",
        type=str,
        help="Output file path (default: stdout)",
    )
    parser.add_argument(
        "--html",
        action="store_true",
        help="Generate full HTML component",
    )
    args = parser.parse_args()

    generator = DevCycleRingGenerator()

    if args.html:
        output = generator.generate_html_component(
            current_stage=args.stage,
            stage_progress=args.progress,
        )
    else:
        output = generator.generate_ring_svg(
            current_stage=args.stage,
            stage_progress=args.progress,
            compact=args.compact,
        )

    if args.output:
        with open(args.output, 'w') as f:
            f.write(output)
        print(f"Generated: {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()
