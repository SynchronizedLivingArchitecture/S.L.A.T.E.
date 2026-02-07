#!/usr/bin/env python3
# Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Create personalization system for user forks
"""
S.L.A.T.E. Personalization System
==================================
Enables users to personalize their SLATE fork with:
- Custom name for their fork (e.g., "PHOENIX", "ATLAS", "NEXUS")
- Custom logo generation with their fork name
- Theme preferences (colors, UI style)
- Generative UI options

This creates a unique identity for each user's SLATE installation.
"""

import json
import math
import os
import re
import sys
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Setup path
WORKSPACE_ROOT = Path(__file__).parent.parent
if str(WORKSPACE_ROOT) not in sys.path:
    sys.path.insert(0, str(WORKSPACE_ROOT))


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: color_palettes [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Predefined color palettes for theming
# ═══════════════════════════════════════════════════════════════════════════════

COLOR_PALETTES = {
    "midnight": {
        "name": "Midnight",
        "description": "Deep blue darkness with cool accents",
        "primary": "#0d1117",
        "secondary": "#161b22",
        "accent": "#58a6ff",
        "highlight": "#1f6feb",
        "text": "#c9d1d9",
        "muted": "#484f58",
        "success": "#238636",
        "warning": "#d29922",
        "error": "#f85149",
        "border": "#30363d",
    },
    "aurora": {
        "name": "Aurora",
        "description": "Northern lights with purple and green glow",
        "primary": "#0f0a1a",
        "secondary": "#1a1225",
        "accent": "#a855f7",
        "highlight": "#22d3ee",
        "text": "#e2e8f0",
        "muted": "#64748b",
        "success": "#4ade80",
        "warning": "#fbbf24",
        "error": "#ef4444",
        "border": "#3b2d5c",
    },
    "ember": {
        "name": "Ember",
        "description": "Warm fire tones with orange and red",
        "primary": "#1a0a0a",
        "secondary": "#251212",
        "accent": "#f97316",
        "highlight": "#dc2626",
        "text": "#fef2f2",
        "muted": "#78716c",
        "success": "#84cc16",
        "warning": "#fbbf24",
        "error": "#ef4444",
        "border": "#44403c",
    },
    "ocean": {
        "name": "Ocean",
        "description": "Deep sea blue with teal accents",
        "primary": "#0a1a1a",
        "secondary": "#0f2937",
        "accent": "#06b6d4",
        "highlight": "#0ea5e9",
        "text": "#e0f2fe",
        "muted": "#64748b",
        "success": "#10b981",
        "warning": "#f59e0b",
        "error": "#f43f5e",
        "border": "#164e63",
    },
    "forest": {
        "name": "Forest",
        "description": "Natural greens with earthy tones",
        "primary": "#0a1a0f",
        "secondary": "#14261a",
        "accent": "#22c55e",
        "highlight": "#10b981",
        "text": "#dcfce7",
        "muted": "#6b7280",
        "success": "#22c55e",
        "warning": "#eab308",
        "error": "#ef4444",
        "border": "#166534",
    },
    "cyber": {
        "name": "Cyber",
        "description": "Neon cyberpunk with pink and cyan",
        "primary": "#0a0a0f",
        "secondary": "#12121a",
        "accent": "#ec4899",
        "highlight": "#06b6d4",
        "text": "#f8fafc",
        "muted": "#71717a",
        "success": "#22d3ee",
        "warning": "#fde047",
        "error": "#fb7185",
        "border": "#27272a",
    },
    "solar": {
        "name": "Solar",
        "description": "Warm solar energy with gold and amber",
        "primary": "#1a1408",
        "secondary": "#292211",
        "accent": "#fbbf24",
        "highlight": "#f59e0b",
        "text": "#fef9c3",
        "muted": "#78716c",
        "success": "#84cc16",
        "warning": "#f97316",
        "error": "#dc2626",
        "border": "#44403c",
    },
    "monochrome": {
        "name": "Monochrome",
        "description": "Clean grayscale elegance",
        "primary": "#0a0a0a",
        "secondary": "#171717",
        "accent": "#f5f5f5",
        "highlight": "#a3a3a3",
        "text": "#f5f5f5",
        "muted": "#525252",
        "success": "#a3a3a3",
        "warning": "#d4d4d4",
        "error": "#737373",
        "border": "#262626",
    },
}

UI_THEMES = {
    "glassmorphism": {
        "name": "Glassmorphism",
        "description": "Frosted glass effect with blur and transparency",
        "style": "glass",
        "blur": "10px",
        "opacity": 0.75,
        "border_style": "solid",
        "shadow": True,
    },
    "neumorphism": {
        "name": "Neumorphism",
        "description": "Soft 3D embossed elements",
        "style": "soft",
        "blur": "0px",
        "opacity": 1.0,
        "border_style": "none",
        "shadow": True,
    },
    "flat": {
        "name": "Flat",
        "description": "Clean minimal flat design",
        "style": "flat",
        "blur": "0px",
        "opacity": 1.0,
        "border_style": "solid",
        "shadow": False,
    },
    "terminal": {
        "name": "Terminal",
        "description": "Classic terminal/hacker aesthetic",
        "style": "terminal",
        "blur": "0px",
        "opacity": 0.95,
        "border_style": "dashed",
        "shadow": False,
    },
}


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: name_suggestions [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Cool name suggestions for user forks
# ═══════════════════════════════════════════════════════════════════════════════

# Name categories for suggestions
FORK_NAME_SUGGESTIONS = {
    "mythological": [
        "PHOENIX", "ATLAS", "TITAN", "NEXUS", "ORACLE",
        "AEGIS", "PROMETHEUS", "HYPERION", "KRONOS", "ZEUS",
    ],
    "space": [
        "NOVA", "STELLAR", "COSMOS", "PULSAR", "QUASAR",
        "NEBULA", "ECLIPSE", "AURORA", "VORTEX", "HORIZON",
    ],
    "tech": [
        "CIPHER", "MATRIX", "VECTOR", "QUANTUM", "DELTA",
        "PRISM", "HELIX", "APEX", "NEXUS", "FLUX",
    ],
    "nature": [
        "STORM", "EMBER", "FROST", "SHADOW", "THUNDER",
        "OCEAN", "SUMMIT", "FOREST", "RIVER", "CRYSTAL",
    ],
    "abstract": [
        "VOID", "ECHO", "PULSE", "SPARK", "DRIFT",
        "SHIFT", "TRACE", "FLOW", "CORE", "EDGE",
    ],
}


def get_name_suggestions(category: Optional[str] = None, count: int = 5) -> List[str]:
    """Get random name suggestions for a fork."""
    import random

    if category and category in FORK_NAME_SUGGESTIONS:
        names = FORK_NAME_SUGGESTIONS[category]
    else:
        # Mix from all categories
        names = []
        for cat_names in FORK_NAME_SUGGESTIONS.values():
            names.extend(cat_names)

    return random.sample(names, min(count, len(names)))


def validate_fork_name(name: str) -> Tuple[bool, str]:
    """
    Validate a fork name.

    Rules:
    - 2-20 characters
    - Alphanumeric, hyphens, underscores allowed
    - Must start with a letter
    - Will be converted to uppercase for display

    Returns:
        Tuple of (is_valid, error_message)
    """
    if not name:
        return False, "Name cannot be empty"

    if len(name) < 2:
        return False, "Name must be at least 2 characters"

    if len(name) > 20:
        return False, "Name must be 20 characters or less"

    if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', name):
        return False, "Name must start with a letter and contain only letters, numbers, hyphens, and underscores"

    return True, ""


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: PersonalizationConfig [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Configuration dataclass for user personalization
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class PersonalizationConfig:
    """Configuration for a user's personalized SLATE installation."""

    # Fork identity
    fork_name: str = "SLATE"
    fork_tagline: Optional[str] = None

    # Theme preferences
    color_palette: str = "midnight"
    ui_theme: str = "glassmorphism"

    # Custom colors (override palette)
    custom_primary: Optional[str] = None
    custom_accent: Optional[str] = None
    custom_highlight: Optional[str] = None

    # Generative UI options
    enable_generative_ui: bool = True
    generative_style: str = "adaptive"  # adaptive, minimal, expressive
    animation_level: str = "subtle"  # none, subtle, dynamic

    # Logo customization
    logo_shape: str = "hexagon"  # hexagon, circle, square, diamond
    logo_glow: bool = True
    logo_animated: bool = False

    # User preferences
    favorite_colors: List[str] = field(default_factory=list)
    personality_traits: List[str] = field(default_factory=list)

    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    modified_at: Optional[str] = None
    version: str = "1.0"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "fork_name": self.fork_name,
            "fork_tagline": self.fork_tagline,
            "color_palette": self.color_palette,
            "ui_theme": self.ui_theme,
            "custom_primary": self.custom_primary,
            "custom_accent": self.custom_accent,
            "custom_highlight": self.custom_highlight,
            "enable_generative_ui": self.enable_generative_ui,
            "generative_style": self.generative_style,
            "animation_level": self.animation_level,
            "logo_shape": self.logo_shape,
            "logo_glow": self.logo_glow,
            "logo_animated": self.logo_animated,
            "favorite_colors": self.favorite_colors,
            "personality_traits": self.personality_traits,
            "created_at": self.created_at,
            "modified_at": self.modified_at,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PersonalizationConfig":
        known_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in known_fields}
        return cls(**filtered)

    def get_effective_colors(self) -> Dict[str, str]:
        """Get the effective color scheme with custom overrides applied."""
        base = COLOR_PALETTES.get(self.color_palette, COLOR_PALETTES["midnight"]).copy()

        if self.custom_primary:
            base["primary"] = self.custom_primary
        if self.custom_accent:
            base["accent"] = self.custom_accent
        if self.custom_highlight:
            base["highlight"] = self.custom_highlight

        return base


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: LogoGenerator [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Generate custom SVG logos with fork name
# ═══════════════════════════════════════════════════════════════════════════════

class LogoGenerator:
    """Generates custom SVG logos for personalized SLATE forks."""

    SHAPES = {
        "hexagon": {
            "outer": "100,35 155,67.5 155,132.5 100,165 45,132.5 45,67.5",
            "inner": "100,50 140,75 140,125 100,150 60,125 60,75",
            "corners": [(100, 35), (155, 67.5), (155, 132.5), (100, 165), (45, 132.5), (45, 67.5)],
        },
        "circle": {
            "outer_cx": 100, "outer_cy": 100, "outer_r": 65,
            "inner_cx": 100, "inner_cy": 100, "inner_r": 50,
        },
        "square": {
            "outer": "35,35 165,35 165,165 35,165",
            "inner": "50,50 150,50 150,150 50,150",
            "corners": [(35, 35), (165, 35), (165, 165), (35, 165)],
        },
        "diamond": {
            "outer": "100,25 175,100 100,175 25,100",
            "inner": "100,45 155,100 100,155 45,100",
            "corners": [(100, 25), (175, 100), (100, 175), (25, 100)],
        },
    }

    def __init__(self, config: PersonalizationConfig):
        self.config = config
        self.colors = config.get_effective_colors()

    def _hex_to_rgb(self, hex_color: str) -> Tuple[int, int, int]:
        """Convert hex color to RGB tuple."""
        hex_color = hex_color.lstrip('#')
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

    def _lighten_color(self, hex_color: str, factor: float = 0.2) -> str:
        """Lighten a hex color by a factor."""
        r, g, b = self._hex_to_rgb(hex_color)
        r = min(255, int(r + (255 - r) * factor))
        g = min(255, int(g + (255 - g) * factor))
        b = min(255, int(b + (255 - b) * factor))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _darken_color(self, hex_color: str, factor: float = 0.2) -> str:
        """Darken a hex color by a factor."""
        r, g, b = self._hex_to_rgb(hex_color)
        r = max(0, int(r * (1 - factor)))
        g = max(0, int(g * (1 - factor)))
        b = max(0, int(b * (1 - factor)))
        return f"#{r:02x}{g:02x}{b:02x}"

    def _generate_grid(self) -> str:
        """Generate background grid pattern."""
        return f'''
  <!-- Grid pattern (subtle) -->
  <g stroke="{self._lighten_color(self.colors['primary'], 0.1)}" stroke-width="0.5" opacity="0.5">
    <line x1="50" y1="0" x2="50" y2="200"/>
    <line x1="100" y1="0" x2="100" y2="200"/>
    <line x1="150" y1="0" x2="150" y2="200"/>
    <line x1="0" y1="50" x2="200" y2="50"/>
    <line x1="0" y1="100" x2="200" y2="100"/>
    <line x1="0" y1="150" x2="200" y2="150"/>
  </g>'''

    def _generate_glow_filter(self) -> str:
        """Generate glow effect filter."""
        if not self.config.logo_glow:
            return ""
        return f'''
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="3" result="coloredBlur"/>
      <feMerge>
        <feMergeNode in="coloredBlur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>'''

    def _generate_hexagon_shape(self) -> str:
        """Generate hexagon shape elements."""
        shape = self.SHAPES["hexagon"]
        corners_svg = "\n".join(
            f'    <circle cx="{x}" cy="{y}" r="2"/>'
            for x, y in shape["corners"]
        )

        glow_filter = 'filter="url(#glow)"' if self.config.logo_glow else ""

        return f'''
  <!-- Central hexagon -->
  <polygon points="{shape['outer']}"
           fill="none" stroke="{self.colors['border']}" stroke-width="2" {glow_filter}/>

  <!-- Inner hexagon -->
  <polygon points="{shape['inner']}"
           fill="{self.colors['primary']}" stroke="{self.colors['muted']}" stroke-width="1"/>

  <!-- Corner dots -->
  <g fill="{self.colors['muted']}">
{corners_svg}
  </g>'''

    def _generate_circle_shape(self) -> str:
        """Generate circle shape elements."""
        shape = self.SHAPES["circle"]
        glow_filter = 'filter="url(#glow)"' if self.config.logo_glow else ""

        return f'''
  <!-- Outer circle -->
  <circle cx="{shape['outer_cx']}" cy="{shape['outer_cy']}" r="{shape['outer_r']}"
          fill="none" stroke="{self.colors['border']}" stroke-width="2" {glow_filter}/>

  <!-- Inner circle -->
  <circle cx="{shape['inner_cx']}" cy="{shape['inner_cy']}" r="{shape['inner_r']}"
          fill="{self.colors['primary']}" stroke="{self.colors['muted']}" stroke-width="1"/>'''

    def _generate_square_shape(self) -> str:
        """Generate square shape elements."""
        shape = self.SHAPES["square"]
        corners_svg = "\n".join(
            f'    <circle cx="{x}" cy="{y}" r="2"/>'
            for x, y in shape["corners"]
        )

        glow_filter = 'filter="url(#glow)"' if self.config.logo_glow else ""

        return f'''
  <!-- Outer square -->
  <polygon points="{shape['outer']}"
           fill="none" stroke="{self.colors['border']}" stroke-width="2" {glow_filter}/>

  <!-- Inner square -->
  <polygon points="{shape['inner']}"
           fill="{self.colors['primary']}" stroke="{self.colors['muted']}" stroke-width="1"/>

  <!-- Corner dots -->
  <g fill="{self.colors['muted']}">
{corners_svg}
  </g>'''

    def _generate_diamond_shape(self) -> str:
        """Generate diamond shape elements."""
        shape = self.SHAPES["diamond"]
        corners_svg = "\n".join(
            f'    <circle cx="{x}" cy="{y}" r="2"/>'
            for x, y in shape["corners"]
        )

        glow_filter = 'filter="url(#glow)"' if self.config.logo_glow else ""

        return f'''
  <!-- Outer diamond -->
  <polygon points="{shape['outer']}"
           fill="none" stroke="{self.colors['border']}" stroke-width="2" {glow_filter}/>

  <!-- Inner diamond -->
  <polygon points="{shape['inner']}"
           fill="{self.colors['primary']}" stroke="{self.colors['muted']}" stroke-width="1"/>

  <!-- Corner dots -->
  <g fill="{self.colors['muted']}">
{corners_svg}
  </g>'''

    def _generate_shape(self) -> str:
        """Generate the appropriate shape based on config."""
        shape_generators = {
            "hexagon": self._generate_hexagon_shape,
            "circle": self._generate_circle_shape,
            "square": self._generate_square_shape,
            "diamond": self._generate_diamond_shape,
        }
        generator = shape_generators.get(self.config.logo_shape, self._generate_hexagon_shape)
        return generator()

    def _calculate_font_size(self, text: str) -> int:
        """Calculate appropriate font size based on text length."""
        base_size = 22
        if len(text) <= 6:
            return base_size
        elif len(text) <= 10:
            return max(14, base_size - (len(text) - 6) * 2)
        else:
            return max(10, base_size - (len(text) - 6) * 1.5)

    def _format_display_name(self, name: str) -> str:
        """Format the fork name for display (e.g., add dots like S.L.A.T.E.)."""
        name = name.upper()

        # Short names (2-4 chars) get dots between letters
        if len(name) <= 4:
            return ".".join(name) + "."

        # Longer names just displayed as-is
        return name

    def generate_svg(self) -> str:
        """Generate the complete SVG logo."""
        display_name = self._format_display_name(self.config.fork_name)
        font_size = self._calculate_font_size(display_name)

        # Calculate positions based on shape
        text_y = 92 if self.config.logo_shape != "diamond" else 100
        tagline_y = text_y + 8

        tagline_svg = ""
        if self.config.fork_tagline:
            words = self.config.fork_tagline.upper().split()
            if len(words) <= 2:
                tagline_svg = f'''
  <text x="100" y="{tagline_y + 18}" text-anchor="middle" font-family="Consolas, 'Courier New', monospace"
        font-size="7" fill="{self.colors['muted']}" letter-spacing="1">
    {self.config.fork_tagline.upper()}
  </text>'''
            else:
                # Split into two lines
                mid = len(words) // 2
                line1 = " ".join(words[:mid])
                line2 = " ".join(words[mid:])
                tagline_svg = f'''
  <text x="100" y="{tagline_y + 18}" text-anchor="middle" font-family="Consolas, 'Courier New', monospace"
        font-size="7" fill="{self.colors['muted']}" letter-spacing="1">
    {line1}
  </text>
  <text x="100" y="{tagline_y + 28}" text-anchor="middle" font-family="Consolas, 'Courier New', monospace"
        font-size="7" fill="{self.colors['muted']}" letter-spacing="1">
    {line2}
  </text>'''

        # Animation for logo (optional)
        animation_svg = ""
        if self.config.logo_animated:
            animation_svg = '''
  <style>
    @keyframes pulse {
      0%, 100% { opacity: 1; }
      50% { opacity: 0.7; }
    }
    .status-dot { animation: pulse 2s ease-in-out infinite; }
  </style>'''

        status_class = 'class="status-dot"' if self.config.logo_animated else ""

        svg = f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 200" width="200" height="200">
  <defs>
    <linearGradient id="bgGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['primary']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['secondary']};stop-opacity:1" />
    </linearGradient>
    <linearGradient id="accentGrad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:{self.colors['accent']};stop-opacity:1" />
      <stop offset="100%" style="stop-color:{self.colors['highlight']};stop-opacity:1" />
    </linearGradient>{self._generate_glow_filter()}
  </defs>
{animation_svg}
  <!-- Background -->
  <rect x="0" y="0" width="200" height="200" rx="20" fill="url(#bgGrad)"/>

  <!-- Outer border -->
  <rect x="4" y="4" width="192" height="192" rx="18" fill="none" stroke="{self.colors['border']}" stroke-width="1"/>
{self._generate_grid()}
{self._generate_shape()}

  <!-- Fork name -->
  <text x="100" y="{text_y}" text-anchor="middle" font-family="Consolas, 'Courier New', monospace"
        font-size="{font_size}" font-weight="bold" fill="{self.colors['text']}" letter-spacing="2">
    {display_name}
  </text>

  <!-- Underline -->
  <line x1="55" y1="{tagline_y}" x2="145" y2="{tagline_y}" stroke="{self.colors['muted']}" stroke-width="1"/>
{tagline_svg}

  <!-- Status indicator -->
  <circle {status_class} cx="170" cy="30" r="4" fill="{self.colors['success']}"/>
</svg>
'''
        return svg

    def save_logo(self, output_path: Path) -> bool:
        """Save the generated logo to a file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            svg_content = self.generate_svg()
            output_path.write_text(svg_content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving logo: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: ThemeGenerator [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Generate CSS theme files based on personalization
# ═══════════════════════════════════════════════════════════════════════════════

class ThemeGenerator:
    """Generates CSS theme files for personalized SLATE forks."""

    def __init__(self, config: PersonalizationConfig):
        self.config = config
        self.colors = config.get_effective_colors()
        self.ui_theme = UI_THEMES.get(config.ui_theme, UI_THEMES["glassmorphism"])

    def generate_css_variables(self) -> str:
        """Generate CSS custom properties for theming."""
        return f''':root {{
  /* {self.config.fork_name} Theme - Generated by SLATE Personalization */
  /* Color Palette: {self.config.color_palette} */
  /* UI Theme: {self.config.ui_theme} */

  /* Primary Colors */
  --color-primary: {self.colors['primary']};
  --color-secondary: {self.colors['secondary']};
  --color-accent: {self.colors['accent']};
  --color-highlight: {self.colors['highlight']};

  /* Text Colors */
  --color-text: {self.colors['text']};
  --color-muted: {self.colors['muted']};

  /* Status Colors */
  --color-success: {self.colors['success']};
  --color-warning: {self.colors['warning']};
  --color-error: {self.colors['error']};

  /* Border */
  --color-border: {self.colors['border']};

  /* UI Theme Properties */
  --blur-amount: {self.ui_theme['blur']};
  --glass-opacity: {self.ui_theme['opacity']};
  --border-style: {self.ui_theme['border_style']};
  --enable-shadow: {1 if self.ui_theme['shadow'] else 0};

  /* Animation */
  --animation-level: {self.config.animation_level};

  /* Fork Identity */
  --fork-name: "{self.config.fork_name}";
}}

/* Glass panel style */
.glass-panel {{
  background: rgba({self._hex_to_rgba(self.colors['secondary'])}, var(--glass-opacity));
  backdrop-filter: blur(var(--blur-amount));
  -webkit-backdrop-filter: blur(var(--blur-amount));
  border: 1px var(--border-style) var(--color-border);
  {self._generate_shadow()}
}}

/* Card style */
.card {{
  background: var(--color-secondary);
  border: 1px var(--border-style) var(--color-border);
  border-radius: 8px;
  {self._generate_shadow()}
}}

/* Button styles */
.btn-primary {{
  background: var(--color-accent);
  color: var(--color-primary);
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 4px;
  cursor: pointer;
  transition: all 0.2s ease;
}}

.btn-primary:hover {{
  background: var(--color-highlight);
}}

/* Status indicators */
.status-success {{ color: var(--color-success); }}
.status-warning {{ color: var(--color-warning); }}
.status-error {{ color: var(--color-error); }}

/* Animation classes */
@media (prefers-reduced-motion: no-preference) {{
  .animate-subtle {{
    transition: all 0.2s ease;
  }}

  .animate-dynamic {{
    transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }}
}}
'''

    def _hex_to_rgba(self, hex_color: str) -> str:
        """Convert hex color to RGB values for rgba()."""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f"{r}, {g}, {b}"

    def _generate_shadow(self) -> str:
        """Generate box shadow CSS if enabled."""
        if not self.ui_theme['shadow']:
            return ""
        return f"box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06);"

    def save_theme(self, output_path: Path) -> bool:
        """Save the generated theme to a CSS file."""
        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            css_content = self.generate_css_variables()
            output_path.write_text(css_content, encoding="utf-8")
            return True
        except Exception as e:
            print(f"Error saving theme: {e}")
            return False


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: PersonalizationManager [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# Main manager for personalization workflow
# ═══════════════════════════════════════════════════════════════════════════════

class PersonalizationManager:
    """
    Manages the personalization workflow for SLATE forks.

    This orchestrates:
    1. Interactive questionnaire for user preferences
    2. Logo generation
    3. Theme file generation
    4. Configuration storage
    """

    CONFIG_FILE = ".slate_identity/config.json"
    LOGO_FILE = ".slate_identity/logo.svg"
    THEME_FILE = ".slate_identity/theme.css"

    def __init__(self, workspace_dir: Optional[Path] = None):
        self.workspace = workspace_dir or WORKSPACE_ROOT
        self.identity_dir = self.workspace / ".slate_identity"
        self.config_path = self.workspace / self.CONFIG_FILE
        self.logo_path = self.workspace / self.LOGO_FILE
        self.theme_path = self.workspace / self.THEME_FILE

        self.config: Optional[PersonalizationConfig] = None
        self._load()

    def _load(self):
        """Load existing configuration."""
        if self.config_path.exists():
            try:
                data = json.loads(self.config_path.read_text(encoding="utf-8"))
                self.config = PersonalizationConfig.from_dict(data)
            except Exception as e:
                print(f"Warning: Could not load personalization config: {e}")

    def _save(self):
        """Save configuration to disk."""
        self.identity_dir.mkdir(parents=True, exist_ok=True)

        if self.config:
            self.config.modified_at = datetime.utcnow().isoformat()
            self.config_path.write_text(
                json.dumps(self.config.to_dict(), indent=2),
                encoding="utf-8"
            )

    def run_interactive_setup(self) -> PersonalizationConfig:
        """
        Run the interactive personalization setup.

        This guides the user through naming their fork, choosing colors,
        and setting UI preferences.
        """
        print()
        print("=" * 64)
        print("  S.L.A.T.E. Personalization Setup")
        print("  Create your unique SLATE identity")
        print("=" * 64)
        print()

        # Step 1: Fork Name
        fork_name = self._ask_fork_name()

        # Step 2: Tagline (optional)
        fork_tagline = self._ask_tagline()

        # Step 3: Color Palette
        color_palette, custom_colors = self._ask_color_preferences()

        # Step 4: UI Theme
        ui_theme = self._ask_ui_theme()

        # Step 5: Generative UI Options
        gen_ui_options = self._ask_generative_ui()

        # Step 6: Logo Shape
        logo_shape = self._ask_logo_shape()

        # Create config
        self.config = PersonalizationConfig(
            fork_name=fork_name,
            fork_tagline=fork_tagline,
            color_palette=color_palette,
            ui_theme=ui_theme,
            custom_primary=custom_colors.get("primary"),
            custom_accent=custom_colors.get("accent"),
            custom_highlight=custom_colors.get("highlight"),
            enable_generative_ui=gen_ui_options["enabled"],
            generative_style=gen_ui_options["style"],
            animation_level=gen_ui_options["animation"],
            logo_shape=logo_shape,
            logo_glow=True,
        )

        # Generate assets
        self._generate_assets()

        # Save config
        self._save()

        print()
        print("=" * 64)
        print(f"  Welcome to {fork_name}!")
        print("  Your personalized SLATE is ready.")
        print("=" * 64)
        print()
        print(f"  Generated files:")
        print(f"    - Logo:   {self.logo_path}")
        print(f"    - Theme:  {self.theme_path}")
        print(f"    - Config: {self.config_path}")
        print()

        return self.config

    def _ask_fork_name(self) -> str:
        """Ask user to name their fork."""
        print("Step 1: Name Your SLATE")
        print("-" * 40)
        print()
        print("Give your SLATE fork a unique identity!")
        print("This name will be displayed in your logo and throughout the UI.")
        print()

        # Show suggestions
        suggestions = get_name_suggestions(count=8)
        print("Suggestions:", ", ".join(suggestions))
        print()

        while True:
            name = input("Enter your fork name (2-20 chars): ").strip()

            if not name:
                # Use a suggestion
                import random
                name = random.choice(suggestions)
                print(f"Using suggestion: {name}")

            valid, error = validate_fork_name(name)
            if valid:
                return name.upper()
            else:
                print(f"  Invalid: {error}")
                print()

    def _ask_tagline(self) -> Optional[str]:
        """Ask for optional tagline."""
        print()
        print("Step 2: Tagline (Optional)")
        print("-" * 40)
        print()
        print("Add a short tagline that describes your SLATE's purpose.")
        print("Examples: 'YOUR VISION', 'CODE UNLEASHED', 'DEV EVOLVED'")
        print()

        tagline = input("Enter tagline (or press Enter to skip): ").strip()

        if tagline and len(tagline) > 40:
            tagline = tagline[:40]
            print(f"  Truncated to: {tagline}")

        return tagline if tagline else None

    def _ask_color_preferences(self) -> Tuple[str, Dict[str, str]]:
        """Ask user about color preferences."""
        print()
        print("Step 3: Choose Your Colors")
        print("-" * 40)
        print()
        print("Select a color palette for your SLATE theme:")
        print()

        for i, (key, palette) in enumerate(COLOR_PALETTES.items(), 1):
            print(f"  {i}. {palette['name']:<12} - {palette['description']}")

        print()

        while True:
            choice = input(f"Enter choice (1-{len(COLOR_PALETTES)}): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(COLOR_PALETTES):
                    palette_key = list(COLOR_PALETTES.keys())[idx]
                    print(f"  Selected: {COLOR_PALETTES[palette_key]['name']}")
                    break
            except ValueError:
                pass
            print("  Invalid choice, try again.")

        # Ask about custom colors
        print()
        custom = input("Would you like to customize specific colors? (y/n): ").strip().lower()
        custom_colors = {}

        if custom == 'y':
            print()
            print("Enter hex colors (e.g., #ff6b6b) or press Enter to skip:")

            accent = input("  Custom accent color: ").strip()
            if accent and accent.startswith('#') and len(accent) == 7:
                custom_colors["accent"] = accent

            highlight = input("  Custom highlight color: ").strip()
            if highlight and highlight.startswith('#') and len(highlight) == 7:
                custom_colors["highlight"] = highlight

        return palette_key, custom_colors

    def _ask_ui_theme(self) -> str:
        """Ask about UI theme style."""
        print()
        print("Step 4: UI Theme Style")
        print("-" * 40)
        print()
        print("Choose your preferred UI style:")
        print()

        for i, (key, theme) in enumerate(UI_THEMES.items(), 1):
            print(f"  {i}. {theme['name']:<14} - {theme['description']}")

        print()

        while True:
            choice = input(f"Enter choice (1-{len(UI_THEMES)}): ").strip()
            try:
                idx = int(choice) - 1
                if 0 <= idx < len(UI_THEMES):
                    theme_key = list(UI_THEMES.keys())[idx]
                    print(f"  Selected: {UI_THEMES[theme_key]['name']}")
                    return theme_key
            except ValueError:
                pass
            print("  Invalid choice, try again.")

    def _ask_generative_ui(self) -> Dict[str, Any]:
        """Ask about generative UI preferences."""
        print()
        print("Step 5: Generative UI Options")
        print("-" * 40)
        print()
        print("Generative UI adapts the interface based on your usage patterns.")
        print()

        enable = input("Enable Generative UI features? (y/n) [y]: ").strip().lower()
        enabled = enable != 'n'

        style = "adaptive"
        animation = "subtle"

        if enabled:
            print()
            print("Generative style:")
            print("  1. Adaptive  - Learns and adapts to your workflow")
            print("  2. Minimal   - Clean and focused")
            print("  3. Expressive - Dynamic and visually rich")

            style_choice = input("Enter choice (1-3) [1]: ").strip()
            if style_choice == '2':
                style = "minimal"
            elif style_choice == '3':
                style = "expressive"

            print()
            print("Animation level:")
            print("  1. None    - No animations")
            print("  2. Subtle  - Smooth, minimal animations")
            print("  3. Dynamic - Rich motion and transitions")

            anim_choice = input("Enter choice (1-3) [2]: ").strip()
            if anim_choice == '1':
                animation = "none"
            elif anim_choice == '3':
                animation = "dynamic"

        return {
            "enabled": enabled,
            "style": style,
            "animation": animation,
        }

    def _ask_logo_shape(self) -> str:
        """Ask about logo shape preference."""
        print()
        print("Step 6: Logo Shape")
        print("-" * 40)
        print()
        print("Choose the shape for your SLATE logo:")
        print()
        print("  1. Hexagon  - Technical, modern (default)")
        print("  2. Circle   - Smooth, unified")
        print("  3. Square   - Bold, stable")
        print("  4. Diamond  - Dynamic, unique")
        print()

        shapes = ["hexagon", "circle", "square", "diamond"]

        choice = input("Enter choice (1-4) [1]: ").strip()
        try:
            idx = int(choice) - 1
            if 0 <= idx < len(shapes):
                print(f"  Selected: {shapes[idx].title()}")
                return shapes[idx]
        except ValueError:
            pass

        return "hexagon"

    def _generate_assets(self):
        """Generate logo and theme files."""
        if not self.config:
            return

        print()
        print("Generating assets...")

        # Generate logo
        logo_gen = LogoGenerator(self.config)
        if logo_gen.save_logo(self.logo_path):
            print(f"  Created logo: {self.logo_path.name}")

        # Also copy to docs/assets for visibility
        docs_logo = self.workspace / "docs" / "assets" / f"{self.config.fork_name.lower()}-logo.svg"
        logo_gen.save_logo(docs_logo)

        # Generate theme
        theme_gen = ThemeGenerator(self.config)
        if theme_gen.save_theme(self.theme_path):
            print(f"  Created theme: {self.theme_path.name}")

    def quick_setup(
        self,
        fork_name: str,
        color_palette: str = "midnight",
        ui_theme: str = "glassmorphism",
        tagline: Optional[str] = None,
    ) -> PersonalizationConfig:
        """
        Quick non-interactive setup.

        Args:
            fork_name: Name for the fork (will be validated)
            color_palette: Palette key from COLOR_PALETTES
            ui_theme: Theme key from UI_THEMES
            tagline: Optional tagline

        Returns:
            PersonalizationConfig
        """
        valid, error = validate_fork_name(fork_name)
        if not valid:
            raise ValueError(f"Invalid fork name: {error}")

        if color_palette not in COLOR_PALETTES:
            color_palette = "midnight"

        if ui_theme not in UI_THEMES:
            ui_theme = "glassmorphism"

        self.config = PersonalizationConfig(
            fork_name=fork_name.upper(),
            fork_tagline=tagline,
            color_palette=color_palette,
            ui_theme=ui_theme,
            enable_generative_ui=True,
            generative_style="adaptive",
            animation_level="subtle",
            logo_shape="hexagon",
            logo_glow=True,
        )

        self._generate_assets()
        self._save()

        return self.config

    def get_config(self) -> Optional[PersonalizationConfig]:
        """Get current personalization config."""
        return self.config

    def is_configured(self) -> bool:
        """Check if personalization is already configured."""
        return self.config is not None and self.config_path.exists()


# ═══════════════════════════════════════════════════════════════════════════════
# CELL: cli [python]
# Author: COPILOT | Created: 2026-02-07T12:00:00Z
# CLI entry point
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """CLI entry point for SLATE Personalization."""
    import argparse

    parser = argparse.ArgumentParser(
        description="S.L.A.T.E. Personalization - Create your unique SLATE identity",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Interactive setup (recommended for first time)
  python slate_personalization.py --setup

  # Quick setup with name
  python slate_personalization.py --quick --name PHOENIX

  # Quick setup with all options
  python slate_personalization.py --quick --name NOVA --palette aurora --theme cyber

  # Regenerate assets only
  python slate_personalization.py --regenerate

  # Show current configuration
  python slate_personalization.py --status

  # List available palettes and themes
  python slate_personalization.py --list
"""
    )

    parser.add_argument("--setup", action="store_true", help="Run interactive setup")
    parser.add_argument("--quick", action="store_true", help="Quick non-interactive setup")
    parser.add_argument("--name", type=str, help="Fork name for quick setup")
    parser.add_argument("--palette", type=str, help="Color palette (use --list to see options)")
    parser.add_argument("--theme", type=str, help="UI theme (use --list to see options)")
    parser.add_argument("--tagline", type=str, help="Optional tagline")
    parser.add_argument("--regenerate", action="store_true", help="Regenerate assets from existing config")
    parser.add_argument("--status", action="store_true", help="Show current configuration")
    parser.add_argument("--list", action="store_true", dest="list_options", help="List available palettes and themes")
    parser.add_argument("--json", action="store_true", dest="json_output", help="Output as JSON")

    args = parser.parse_args()

    manager = PersonalizationManager()

    if args.list_options:
        print("\nAvailable Color Palettes:")
        print("-" * 40)
        for key, palette in COLOR_PALETTES.items():
            print(f"  {key:<12} - {palette['description']}")

        print("\nAvailable UI Themes:")
        print("-" * 40)
        for key, theme in UI_THEMES.items():
            print(f"  {key:<14} - {theme['description']}")

        print("\nFork Name Suggestions:")
        print("-" * 40)
        for category, names in FORK_NAME_SUGGESTIONS.items():
            print(f"  {category.title()}: {', '.join(names[:5])}")
        print()
        return 0

    if args.status:
        if manager.is_configured():
            config = manager.get_config()
            if args.json_output:
                print(json.dumps(config.to_dict(), indent=2))
            else:
                print()
                print(f"SLATE Identity: {config.fork_name}")
                print("=" * 40)
                print(f"  Tagline:        {config.fork_tagline or 'None'}")
                print(f"  Color Palette:  {config.color_palette}")
                print(f"  UI Theme:       {config.ui_theme}")
                print(f"  Logo Shape:     {config.logo_shape}")
                print(f"  Generative UI:  {'Enabled' if config.enable_generative_ui else 'Disabled'}")
                print(f"  Gen Style:      {config.generative_style}")
                print(f"  Animation:      {config.animation_level}")
                print(f"  Created:        {config.created_at}")
                print()
        else:
            print("No personalization configured. Run with --setup to configure.")
        return 0

    if args.setup:
        manager.run_interactive_setup()
        return 0

    if args.quick:
        if not args.name:
            print("Error: --quick requires --name")
            return 1

        try:
            config = manager.quick_setup(
                fork_name=args.name,
                color_palette=args.palette or "midnight",
                ui_theme=args.theme or "glassmorphism",
                tagline=args.tagline,
            )

            if args.json_output:
                print(json.dumps(config.to_dict(), indent=2))
            else:
                print(f"Created personalization for: {config.fork_name}")
                print(f"  Logo: {manager.logo_path}")
                print(f"  Theme: {manager.theme_path}")
        except ValueError as e:
            print(f"Error: {e}")
            return 1

        return 0

    if args.regenerate:
        if not manager.is_configured():
            print("No configuration found. Run --setup first.")
            return 1

        manager._generate_assets()
        print("Assets regenerated.")
        return 0

    # Default: show help
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
