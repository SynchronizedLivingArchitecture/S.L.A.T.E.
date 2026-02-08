#!/usr/bin/env python3
"""
SLATE Design Tokens
===================

Comprehensive design token system synthesizing:
- Google M3 Material Design tokens
- Anthropic geometric art palette
- Awwwards modern dashboard patterns

These tokens are injected into the generative UI during installation
and are used by the dashboard server for consistent styling.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import json


@dataclass
class ColorTokens:
    """Color token definitions."""

    # Primary palette (Anthropic-inspired warm)
    primary: str = "#B85A3C"
    primary_light: str = "#D4785A"
    primary_dark: str = "#8B4530"
    primary_container: str = "#FFE4D9"
    on_primary: str = "#FFFFFF"
    on_primary_container: str = "#3D1E10"

    # Secondary palette
    secondary: str = "#5D5D74"
    secondary_light: str = "#7A7A94"
    secondary_dark: str = "#424258"
    secondary_container: str = "#E2E2F0"
    on_secondary: str = "#FFFFFF"
    on_secondary_container: str = "#1A1A24"

    # Tertiary palette
    tertiary: str = "#6B8E23"
    tertiary_light: str = "#8FBC3F"
    tertiary_dark: str = "#4A6418"
    tertiary_container: str = "#E8F0D8"
    on_tertiary: str = "#FFFFFF"
    on_tertiary_container: str = "#1E2A0D"

    # Neutral surfaces (natural earth tones)
    surface: str = "#FBF8F6"
    surface_dim: str = "#DCD9D6"
    surface_bright: str = "#FFFFFF"
    surface_container_lowest: str = "#FFFFFF"
    surface_container_low: str = "#F5F2F0"
    surface_container: str = "#F0EBE7"
    surface_container_high: str = "#EAE6E2"
    surface_container_highest: str = "#E4E0DC"
    on_surface: str = "#1C1B1A"
    on_surface_variant: str = "#4D4845"

    # Dark mode surfaces
    surface_dark: str = "#1A1816"
    surface_dim_dark: str = "#141210"
    surface_bright_dark: str = "#3A3634"
    surface_container_lowest_dark: str = "#0F0D0C"
    surface_container_low_dark: str = "#221F1D"
    surface_container_dark: str = "#2A2624"
    surface_container_high_dark: str = "#34302E"
    surface_container_highest_dark: str = "#3F3B38"
    on_surface_dark: str = "#E8E2DE"
    on_surface_variant_dark: str = "#CAC4BF"

    # Outline
    outline: str = "#7D7873"
    outline_variant: str = "#CFC8C3"
    outline_dark: str = "#968F8A"
    outline_variant_dark: str = "#4D4845"

    # Semantic colors
    success: str = "#4CAF50"
    success_container: str = "#C8E6C9"
    on_success: str = "#FFFFFF"
    on_success_container: str = "#1B5E20"

    warning: str = "#FF9800"
    warning_container: str = "#FFE0B2"
    on_warning: str = "#000000"
    on_warning_container: str = "#E65100"

    error: str = "#F44336"
    error_container: str = "#FFCDD2"
    on_error: str = "#FFFFFF"
    on_error_container: str = "#B71C1C"

    info: str = "#2196F3"
    info_container: str = "#BBDEFB"
    on_info: str = "#FFFFFF"
    on_info_container: str = "#0D47A1"

    # Engineering Blueprint Theme
    blueprint_bg: str = "#0D1B2A"              # Deep technical blue
    blueprint_grid: str = "#1B3A4B"            # Grid line color
    blueprint_line: str = "#3D5A80"            # Connection lines
    blueprint_accent: str = "#98C1D9"          # Highlighted connections
    blueprint_node: str = "#E0FBFC"            # Node backgrounds
    blueprint_text: str = "#EEF0F2"            # Text on blueprint

    # Light mode engineering
    blueprint_bg_light: str = "#F8FAFC"        # Light blueprint background
    blueprint_grid_light: str = "#E2E8F0"      # Light grid lines
    blueprint_line_light: str = "#64748B"      # Light connection lines
    blueprint_accent_light: str = "#3B82F6"    # Light highlighted connections
    blueprint_node_light: str = "#FFFFFF"      # Light node backgrounds
    blueprint_text_light: str = "#1E293B"      # Text on light blueprint

    # Connection status colors
    connection_active: str = "#22C55E"         # Active connection (green)
    connection_pending: str = "#F59E0B"        # Pending connection (amber)
    connection_error: str = "#EF4444"          # Error connection (red)
    connection_inactive: str = "#6B7280"       # Inactive connection (gray)

    # Wizard/Stepper colors
    step_active: str = "#3B82F6"               # Current step
    step_complete: str = "#22C55E"             # Completed step
    step_pending: str = "#9CA3AF"              # Future step
    step_error: str = "#EF4444"                # Error state


@dataclass
class TypographyTokens:
    """Typography token definitions."""

    # Font families
    font_display: str = "'Styrene A', 'Inter Tight', system-ui, sans-serif"
    font_body: str = "'Tiempos Text', 'Georgia', serif"
    font_mono: str = "'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace"

    # Font sizes (fluid with clamp)
    display_large: str = "clamp(2.5rem, 2rem + 2.5vw, 3.5625rem)"
    display_medium: str = "clamp(2rem, 1.5rem + 2vw, 2.8125rem)"
    display_small: str = "clamp(1.5rem, 1.25rem + 1.25vw, 2.25rem)"
    headline_large: str = "clamp(1.5rem, 1.25rem + 1vw, 2rem)"
    headline_medium: str = "clamp(1.25rem, 1rem + 0.75vw, 1.75rem)"
    headline_small: str = "clamp(1.125rem, 1rem + 0.5vw, 1.5rem)"
    title_large: str = "1.375rem"
    title_medium: str = "1rem"
    title_small: str = "0.875rem"
    body_large: str = "1rem"
    body_medium: str = "0.875rem"
    body_small: str = "0.75rem"
    label_large: str = "0.875rem"
    label_medium: str = "0.75rem"
    label_small: str = "0.6875rem"

    # Font weights
    weight_regular: int = 400
    weight_medium: int = 500
    weight_bold: int = 700

    # Line heights
    line_height_tight: float = 1.2
    line_height_normal: float = 1.5
    line_height_relaxed: float = 1.75


@dataclass
class SpacingTokens:
    """Spacing token definitions."""

    # Base unit: 4px
    space_0: str = "0"
    space_1: str = "0.25rem"   # 4px
    space_2: str = "0.5rem"    # 8px
    space_3: str = "0.75rem"   # 12px
    space_4: str = "1rem"      # 16px
    space_5: str = "1.25rem"   # 20px
    space_6: str = "1.5rem"    # 24px
    space_7: str = "1.75rem"   # 28px
    space_8: str = "2rem"      # 32px
    space_10: str = "2.5rem"   # 40px
    space_12: str = "3rem"     # 48px
    space_16: str = "4rem"     # 64px
    space_20: str = "5rem"     # 80px
    space_24: str = "6rem"     # 96px

    # Semantic spacing
    gutter: str = "clamp(1rem, 2vw, 1.5rem)"
    container_padding: str = "clamp(1rem, 4vw, 3rem)"


@dataclass
class ElevationTokens:
    """Elevation/shadow token definitions."""

    elevation_0: str = "none"
    elevation_1: str = "0 1px 2px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1)"
    elevation_2: str = "0 2px 4px rgba(0,0,0,0.05), 0 4px 8px rgba(0,0,0,0.1)"
    elevation_3: str = "0 4px 8px rgba(0,0,0,0.08), 0 8px 16px rgba(0,0,0,0.12)"
    elevation_4: str = "0 8px 16px rgba(0,0,0,0.1), 0 16px 32px rgba(0,0,0,0.15)"
    elevation_5: str = "0 16px 32px rgba(0,0,0,0.12), 0 32px 64px rgba(0,0,0,0.18)"


@dataclass
class RadiusTokens:
    """Border radius token definitions."""

    radius_none: str = "0"
    radius_xs: str = "4px"
    radius_sm: str = "8px"
    radius_md: str = "12px"
    radius_lg: str = "16px"
    radius_xl: str = "24px"
    radius_2xl: str = "32px"
    radius_full: str = "9999px"


@dataclass
class MotionTokens:
    """Animation/motion token definitions."""

    # Easing curves (M3)
    easing_standard: str = "cubic-bezier(0.4, 0, 0.2, 1)"
    easing_decelerate: str = "cubic-bezier(0, 0, 0.2, 1)"
    easing_accelerate: str = "cubic-bezier(0.4, 0, 1, 1)"
    easing_spring: str = "cubic-bezier(0.34, 1.56, 0.64, 1)"

    # Durations
    duration_instant: str = "50ms"
    duration_fast: str = "100ms"
    duration_normal: str = "200ms"
    duration_slow: str = "300ms"
    duration_slower: str = "400ms"
    duration_slowest: str = "500ms"


@dataclass
class StateTokens:
    """State layer token definitions (M3)."""

    state_hover: float = 0.08
    state_focus: float = 0.12
    state_pressed: float = 0.12
    state_dragged: float = 0.16
    state_disabled: float = 0.38


@dataclass
class EngineeringDrawingTokens:
    """
    Engineering Drawing Standards (Spec 013)

    Based on:
    - ISO 128 (Technical Drawing Line Types)
    - IEC 60617 (Electronic Schematic Symbols)
    - ASME Y14.44 (Reference Designators)
    - PCB Silkscreen Conventions
    """

    # ═══════════════════════════════════════════════════════════════════════════
    # ISO 128 Line Types (stroke-dasharray patterns)
    # ═══════════════════════════════════════════════════════════════════════════

    # Type 01: Continuous thick - visible outlines, active connections
    line_continuous_thick: str = "none"
    line_continuous_thick_width: str = "2px"

    # Type 02: Continuous thin - dimension lines, leaders
    line_continuous_thin: str = "none"
    line_continuous_thin_width: str = "1px"

    # Type 03: Dashed thick - hidden components, inactive services
    line_dashed_thick: str = "8,4"
    line_dashed_thick_width: str = "2px"

    # Type 04: Dashed thin - hidden details, pending tasks
    line_dashed_thin: str = "6,3"
    line_dashed_thin_width: str = "1px"

    # Type 05: Chain thin - center lines, symmetry axes
    line_chain_thin: str = "12,3,3,3"
    line_chain_thin_width: str = "1px"

    # Type 06: Chain thick - cut planes, section indicators
    line_chain_thick: str = "16,4,4,4"
    line_chain_thick_width: str = "2px"

    # Type 07: Dotted thin - projection lines, data flow
    line_dotted_thin: str = "2,2"
    line_dotted_thin_width: str = "1px"

    # Type 08: Long-dash double-short - boundaries, system limits
    line_boundary: str = "18,3,3,3,3,3"
    line_boundary_width: str = "1px"

    # ═══════════════════════════════════════════════════════════════════════════
    # Blueprint Colors (Engineering Drawing Palette)
    # ═══════════════════════════════════════════════════════════════════════════

    # Background variants
    blueprint_primary: str = "#0D1B2A"      # Deep blueprint blue
    blueprint_secondary: str = "#0a0a0a"    # SLATE dark
    blueprint_tertiary: str = "#1B2838"     # Lighter blueprint

    # Trace colors by type
    trace_signal: str = "#B87333"           # Copper - primary signals
    trace_power: str = "#C47070"            # Warm red - power lines
    trace_ground: str = "#78716C"           # Cool gray - ground
    trace_data: str = "#7EA8BE"             # Soft blue - data lines
    trace_control: str = "#D4A054"          # Gold - control signals

    # Status indicators
    status_active: str = "#22C55E"          # Green - live/active
    status_pending: str = "#D4A054"         # Gold - waiting
    status_error: str = "#C47070"           # Red - fault
    status_disabled: str = "#333333"        # Dim gray - disabled
    status_unknown: str = "#4B5563"         # Neutral gray - unknown

    # Component fills
    fill_service: str = "#1a1510"           # Dark warm - services
    fill_database: str = "#101520"          # Dark cool - databases
    fill_gpu: str = "#15120a"               # Dark copper - GPU/compute
    fill_ai: str = "#0a1515"                # Dark teal - AI/ML
    fill_external: str = "#151015"          # Dark purple - external

    # ═══════════════════════════════════════════════════════════════════════════
    # PCB Silkscreen Typography
    # ═══════════════════════════════════════════════════════════════════════════

    # Font sizes (following silkscreen conventions)
    text_component_label: str = "14px"      # Component labels
    text_reference_designator: str = "12px" # Reference designators (R1, C2)
    text_pin_number: str = "10px"           # Pin numbers
    text_status_indicator: str = "8px"      # Status text
    text_section_header: str = "16px"       # Section headers

    # Font families (engineering-style)
    font_schematic: str = "Consolas, 'Courier New', monospace"
    font_schematic_bold: str = "Consolas, 'Courier New', monospace"
    font_labels: str = "'Segoe UI', system-ui, sans-serif"

    # Text colors
    text_primary: str = "#E7E0D8"           # Cream - primary text
    text_secondary: str = "#A8A29E"         # Warm gray - secondary
    text_designator: str = "#C9956B"        # Copper - designators
    text_muted: str = "#78716C"             # Muted - tertiary text

    # ═══════════════════════════════════════════════════════════════════════════
    # Engineering Grid System (8px base unit)
    # ═══════════════════════════════════════════════════════════════════════════

    grid_base: str = "8px"                  # Base unit (ISO module)
    grid_minor: str = "16px"                # Minor grid (2 × base)
    grid_major: str = "64px"                # Major grid (8 × base)

    # Component sizes (multiples of major grid)
    component_small: str = "64px"           # 1×1 major (status)
    component_medium_w: str = "128px"       # 2×1 major width (services)
    component_medium_h: str = "64px"        # 2×1 major height
    component_large: str = "128px"          # 2×2 major (databases)
    component_xlarge_w: str = "256px"       # 4×2 major width (groups)
    component_xlarge_h: str = "128px"       # 4×2 major height

    # Spacing
    spacing_component: str = "32px"         # Between components (4 × base)
    spacing_group: str = "64px"             # Between groups (8 × base)
    spacing_margin: str = "48px"            # Edge margin (6 × base)

    # ═══════════════════════════════════════════════════════════════════════════
    # ASME Y14.44 Reference Designator Prefixes
    # ═══════════════════════════════════════════════════════════════════════════

    designator_service: str = "SVC"         # Core services
    designator_database: str = "DB"         # Databases
    designator_gpu: str = "GPU"             # GPU units
    designator_ai: str = "AI"               # AI models
    designator_api: str = "API"             # API routes
    designator_connector: str = "J"         # Connectors
    designator_bus: str = "BUS"             # Data buses
    designator_terminal: str = "T"          # Terminals

    # ═══════════════════════════════════════════════════════════════════════════
    # Animation Standards
    # ═══════════════════════════════════════════════════════════════════════════

    anim_pulse_duration: str = "2s"         # Active pulse
    anim_flow_duration: str = "1s"          # Data flow
    anim_connect_duration: str = "0.5s"     # Connection establish
    anim_appear_duration: str = "0.3s"      # Component appear
    anim_transition_duration: str = "0.3s"  # Status change
    anim_error_duration: str = "0.2s"       # Error flash

    anim_easing_pulse: str = "ease-in-out"
    anim_easing_flow: str = "linear"
    anim_easing_appear: str = "ease-out"
    anim_easing_transition: str = "ease-in-out"

    # ═══════════════════════════════════════════════════════════════════════════
    # Polarity & Orientation Markers
    # ═══════════════════════════════════════════════════════════════════════════

    marker_pin1: str = "●"                  # Pin 1 indicator (filled circle)
    marker_active: str = "+"                # Active/power marker
    marker_ground: str = "−"                # Ground/inactive marker
    marker_empty: str = "○"                 # Empty/unconnected
    marker_bidirectional: str = "↔"         # Bidirectional flow
    marker_input: str = "→"                 # Input direction
    marker_output: str = "←"                # Output direction


@dataclass
class DesignTokens:
    """Complete design token collection."""

    colors: ColorTokens = field(default_factory=ColorTokens)
    typography: TypographyTokens = field(default_factory=TypographyTokens)
    spacing: SpacingTokens = field(default_factory=SpacingTokens)
    elevation: ElevationTokens = field(default_factory=ElevationTokens)
    radius: RadiusTokens = field(default_factory=RadiusTokens)
    motion: MotionTokens = field(default_factory=MotionTokens)
    state: StateTokens = field(default_factory=StateTokens)
    engineering: EngineeringDrawingTokens = field(default_factory=EngineeringDrawingTokens)

    def to_css_variables(self, prefix: str = "slate") -> str:
        """Generate CSS custom properties from all tokens."""
        lines = [":root {"]

        # Colors
        for name, value in vars(self.colors).items():
            css_name = name.replace("_", "-")
            lines.append(f"    --{prefix}-{css_name}: {value};")

        lines.append("")

        # Typography
        for name, value in vars(self.typography).items():
            if isinstance(value, (int, float)):
                lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")
            else:
                lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # Spacing
        for name, value in vars(self.spacing).items():
            lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # Elevation
        for name, value in vars(self.elevation).items():
            lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # Radius
        for name, value in vars(self.radius).items():
            lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # Motion
        for name, value in vars(self.motion).items():
            lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # State
        for name, value in vars(self.state).items():
            lines.append(f"    --{prefix}-{name.replace('_', '-')}: {value};")

        lines.append("")

        # Engineering Drawing (Spec 013)
        lines.append("    /* Engineering Drawing Standards (ISO 128, IEC 60617, ASME Y14.44) */")
        for name, value in vars(self.engineering).items():
            css_name = name.replace("_", "-")
            lines.append(f"    --{prefix}-eng-{css_name}: {value};")

        lines.append("}")

        return "\n".join(lines)

    def to_json(self) -> str:
        """Export tokens as JSON for programmatic use."""
        data = {
            "colors": vars(self.colors),
            "typography": vars(self.typography),
            "spacing": vars(self.spacing),
            "elevation": vars(self.elevation),
            "radius": vars(self.radius),
            "motion": vars(self.motion),
            "state": vars(self.state),
            "engineering": vars(self.engineering)
        }
        return json.dumps(data, indent=2)

    def save_css(self, path: Path) -> None:
        """Save tokens as CSS file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_css_variables(), encoding='utf-8')

    def save_json(self, path: Path) -> None:
        """Save tokens as JSON file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.to_json(), encoding='utf-8')


# Global default tokens instance
DEFAULT_TOKENS = DesignTokens()


def get_tokens() -> DesignTokens:
    """Get the default design tokens."""
    return DEFAULT_TOKENS


def generate_theme_css(theme_value: float = 0.0) -> str:
    """
    Generate CSS for a specific theme value.

    Args:
        theme_value: 0.0 = full dark, 1.0 = full light

    Returns:
        CSS string with interpolated values
    """
    tokens = DEFAULT_TOKENS

    # Interpolate between dark and light values
    def lerp_color(dark: str, light: str, t: float) -> str:
        """Linear interpolate between two hex colors."""
        dark = dark.lstrip('#')
        light = light.lstrip('#')

        r1, g1, b1 = int(dark[0:2], 16), int(dark[2:4], 16), int(dark[4:6], 16)
        r2, g2, b2 = int(light[0:2], 16), int(light[2:4], 16), int(light[4:6], 16)

        r = int(r1 + (r2 - r1) * t)
        g = int(g1 + (g2 - g1) * t)
        b = int(b1 + (b2 - b1) * t)

        return f"#{r:02x}{g:02x}{b:02x}"

    # Generate interpolated colors
    surface = lerp_color(
        tokens.colors.surface_dark,
        tokens.colors.surface,
        theme_value
    )
    on_surface = lerp_color(
        tokens.colors.on_surface_dark,
        tokens.colors.on_surface,
        theme_value
    )

    css = f"""
:root {{
    --slate-theme-value: {theme_value};
    --slate-surface-computed: {surface};
    --slate-on-surface-computed: {on_surface};
}}
"""
    return css


if __name__ == "__main__":
    # Demo: generate token files
    tokens = DesignTokens()

    output_dir = Path(__file__).parent.parent / ".slate_identity"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Save CSS
    tokens.save_css(output_dir / "design-tokens.css")
    print(f"Generated: {output_dir / 'design-tokens.css'}")

    # Save JSON
    tokens.save_json(output_dir / "design-tokens.json")
    print(f"Generated: {output_dir / 'design-tokens.json'}")

    print("\nDesign token generation complete!")
