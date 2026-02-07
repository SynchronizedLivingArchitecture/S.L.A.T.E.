#!/usr/bin/env python3
"""
SLATE Logo Generator
====================

Geometric logo generation framework inspired by:
- Anthropic's starburst/pinwheel visual identity
- M3 Material Design principles
- SLATE system architecture

Generates procedural SVG logos that can be customized
for different contexts (light/dark mode, sizes, animations).
"""

from .starburst import StarburstLogo, generate_logo_svg
from .themes import LogoTheme, get_theme, SLATE_THEMES

__all__ = [
    'StarburstLogo',
    'generate_logo_svg',
    'LogoTheme',
    'get_theme',
    'SLATE_THEMES'
]

__version__ = '1.0.0'
