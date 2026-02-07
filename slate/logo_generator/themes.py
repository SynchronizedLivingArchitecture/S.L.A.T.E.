#!/usr/bin/env python3
"""
Logo Theme System
=================

Color themes for SLATE logo generation based on:
- Anthropic's warm rust-orange palette
- M3 Material Design tonal system
- SLATE natural earth tones
"""

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class LogoTheme:
    """Color theme for logo generation."""

    name: str
    primary: str
    on_primary: str
    secondary: str
    on_secondary: str
    background: Optional[str]
    surface: str
    on_surface: str

    # Additional tonal values
    primary_light: str = ""
    primary_dark: str = ""


# SLATE Theme Collection
SLATE_THEMES: Dict[str, LogoTheme] = {
    "default": LogoTheme(
        name="SLATE Default",
        primary="#B85A3C",
        on_primary="#FFFFFF",
        secondary="#5D5D74",
        on_secondary="#FFFFFF",
        background=None,
        surface="#FBF8F6",
        on_surface="#1C1B1A",
        primary_light="#D4785A",
        primary_dark="#8B4530"
    ),

    "dark": LogoTheme(
        name="SLATE Dark",
        primary="#D4785A",
        on_primary="#2A1508",
        secondary="#A8A8B8",
        on_secondary="#1A1A24",
        background="#1A1816",
        surface="#2A2624",
        on_surface="#E8E2DE",
        primary_light="#E8967A",
        primary_dark="#B85A3C"
    ),

    "light": LogoTheme(
        name="SLATE Light",
        primary="#B85A3C",
        on_primary="#FFFFFF",
        secondary="#5D5D74",
        on_secondary="#FFFFFF",
        background="#FBF8F6",
        surface="#FFFFFF",
        on_surface="#1C1B1A",
        primary_light="#D4785A",
        primary_dark="#8B4530"
    ),

    "warm": LogoTheme(
        name="SLATE Warm",
        primary="#C15F3C",  # Anthropic Crail
        on_primary="#FFFFFF",
        secondary="#8B6914",
        on_secondary="#FFFFFF",
        background=None,
        surface="#FFF8F0",
        on_surface="#2D1F1A",
        primary_light="#E07850",
        primary_dark="#A04830"
    ),

    "cool": LogoTheme(
        name="SLATE Cool",
        primary="#3C7AB8",
        on_primary="#FFFFFF",
        secondary="#5D7474",
        on_secondary="#FFFFFF",
        background=None,
        surface="#F6F8FB",
        on_surface="#1A1B1C",
        primary_light="#5A94D4",
        primary_dark="#305F8B"
    ),

    "earth": LogoTheme(
        name="SLATE Earth",
        primary="#6B8E23",  # Olive green
        on_primary="#FFFFFF",
        secondary="#8B7355",  # Earth brown
        on_secondary="#FFFFFF",
        background=None,
        surface="#F5F5DC",  # Beige
        on_surface="#2F2F1F",
        primary_light="#8FBC3F",
        primary_dark="#4A6418"
    ),

    "monochrome": LogoTheme(
        name="SLATE Monochrome",
        primary="#404040",
        on_primary="#FFFFFF",
        secondary="#808080",
        on_secondary="#FFFFFF",
        background=None,
        surface="#F5F5F5",
        on_surface="#1A1A1A",
        primary_light="#606060",
        primary_dark="#202020"
    ),

    "high-contrast": LogoTheme(
        name="SLATE High Contrast",
        primary="#000000",
        on_primary="#FFFFFF",
        secondary="#333333",
        on_secondary="#FFFFFF",
        background="#FFFFFF",
        surface="#FFFFFF",
        on_surface="#000000",
        primary_light="#333333",
        primary_dark="#000000"
    ),

    "neon": LogoTheme(
        name="SLATE Neon",
        primary="#FF6B35",
        on_primary="#000000",
        secondary="#00D4FF",
        on_secondary="#000000",
        background="#0D0D0D",
        surface="#1A1A2E",
        on_surface="#EAEAEA",
        primary_light="#FF8B5A",
        primary_dark="#CC5428"
    ),

    "forest": LogoTheme(
        name="SLATE Forest",
        primary="#2D5A27",
        on_primary="#FFFFFF",
        secondary="#5A7A52",
        on_secondary="#FFFFFF",
        background=None,
        surface="#E8F0E8",
        on_surface="#1A2A1A",
        primary_light="#4A7A42",
        primary_dark="#1E3D1A"
    ),

    "ocean": LogoTheme(
        name="SLATE Ocean",
        primary="#1E4D6B",
        on_primary="#FFFFFF",
        secondary="#4A7A8C",
        on_secondary="#FFFFFF",
        background=None,
        surface="#E8F4F8",
        on_surface="#0D1F2D",
        primary_light="#2E6A8E",
        primary_dark="#0E3048"
    ),

    "sunset": LogoTheme(
        name="SLATE Sunset",
        primary="#D4543A",
        on_primary="#FFFFFF",
        secondary="#F4A460",
        on_secondary="#2D1A0D",
        background=None,
        surface="#FFF5E6",
        on_surface="#2D1A0D",
        primary_light="#E86B52",
        primary_dark="#B03D28"
    )
}


def get_theme(name: str) -> LogoTheme:
    """
    Get a logo theme by name.

    Args:
        name: Theme name (case-insensitive)

    Returns:
        LogoTheme instance

    Raises:
        KeyError: If theme not found
    """
    name_lower = name.lower()
    if name_lower in SLATE_THEMES:
        return SLATE_THEMES[name_lower]

    # Fuzzy match
    for key, theme in SLATE_THEMES.items():
        if name_lower in key or key in name_lower:
            return theme

    raise KeyError(f"Theme '{name}' not found. Available: {list(SLATE_THEMES.keys())}")


def list_themes() -> Dict[str, str]:
    """List all available themes with their primary colors."""
    return {name: theme.primary for name, theme in SLATE_THEMES.items()}


def create_custom_theme(
    name: str,
    primary: str,
    on_primary: str = "#FFFFFF",
    background: Optional[str] = None
) -> LogoTheme:
    """
    Create a custom logo theme.

    Args:
        name: Theme name
        primary: Primary color (hex)
        on_primary: Text color on primary (hex)
        background: Optional background color (hex)

    Returns:
        LogoTheme instance
    """
    # Auto-generate complementary colors
    # Simple approach: adjust brightness for variants
    def adjust_brightness(hex_color: str, factor: float) -> str:
        """Adjust brightness of hex color."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)

        r = min(255, max(0, int(r * factor)))
        g = min(255, max(0, int(g * factor)))
        b = min(255, max(0, int(b * factor)))

        return f"#{r:02x}{g:02x}{b:02x}"

    return LogoTheme(
        name=name,
        primary=primary,
        on_primary=on_primary,
        secondary=adjust_brightness(primary, 0.7),
        on_secondary=on_primary,
        background=background,
        surface=adjust_brightness(primary, 2.5) if not background else adjust_brightness(background, 1.1),
        on_surface=adjust_brightness(primary, 0.3),
        primary_light=adjust_brightness(primary, 1.3),
        primary_dark=adjust_brightness(primary, 0.7)
    )


if __name__ == "__main__":
    # Demo: list all themes
    print("SLATE Logo Themes")
    print("=" * 40)

    for name, theme in SLATE_THEMES.items():
        print(f"\n{theme.name}")
        print(f"  Primary: {theme.primary}")
        print(f"  On Primary: {theme.on_primary}")
        print(f"  Background: {theme.background or 'Transparent'}")
