#!/usr/bin/env python3
"""
Starburst Logo Generator
========================

Generates the SLATE starburst logo with radiating rays
inspired by Anthropic's geometric visual identity.

The starburst represents ideas radiating outward from a central core,
symbolizing SLATE's role as a hub for synchronized living architecture.
"""

import math
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from pathlib import Path


@dataclass
class StarburstConfig:
    """Configuration for starburst logo generation."""

    # Dimensions
    size: int = 200
    padding: int = 20

    # Rays
    ray_count: int = 8
    ray_length_min: float = 0.5  # Ratio of available radius
    ray_length_max: float = 1.0
    ray_width: float = 3.0
    ray_cap: str = "round"  # round, square, butt

    # Center
    center_radius: float = 0.2  # Ratio of available radius
    center_letter: str = "S"
    center_font_size: float = 0.12  # Ratio of size

    # Rotation
    rotation_offset: float = 22.5  # Degrees offset from cardinal

    # Colors (defaults, can be overridden by theme)
    ray_color: str = "#B85A3C"
    center_fill: str = "#B85A3C"
    center_stroke: str = "#B85A3C"
    letter_color: str = "#FFFFFF"
    background: Optional[str] = None

    # Animation
    animate_pulse: bool = False
    animate_rotate: bool = False
    animation_duration: int = 2000  # ms

    # Alternating ray lengths for dynamic look
    alternate_rays: bool = True
    short_ray_ratio: float = 0.7


@dataclass
class StarburstLogo:
    """
    Generates a starburst logo with radiating rays.

    The logo consists of:
    - 8 rays radiating at 45° intervals
    - A central circle with the letter "S"
    - Alternating ray lengths for visual interest
    """

    config: StarburstConfig = field(default_factory=StarburstConfig)

    def _calculate_ray_points(self) -> List[Tuple[float, float, float, float]]:
        """Calculate start and end points for each ray."""
        rays = []
        center = self.config.size / 2
        available_radius = (self.config.size / 2) - self.config.padding
        center_radius = available_radius * self.config.center_radius

        for i in range(self.config.ray_count):
            # Calculate angle in radians
            angle_deg = (360 / self.config.ray_count) * i + self.config.rotation_offset
            angle_rad = math.radians(angle_deg)

            # Determine ray length (alternate if enabled)
            if self.config.alternate_rays and i % 2 == 1:
                length_ratio = self.config.ray_length_min + (
                    (self.config.ray_length_max - self.config.ray_length_min)
                    * self.config.short_ray_ratio
                )
            else:
                length_ratio = self.config.ray_length_max

            # Calculate start (at center circle edge) and end points
            start_x = center + math.cos(angle_rad) * center_radius
            start_y = center + math.sin(angle_rad) * center_radius

            ray_length = available_radius * length_ratio
            end_x = center + math.cos(angle_rad) * ray_length
            end_y = center + math.sin(angle_rad) * ray_length

            rays.append((start_x, start_y, end_x, end_y))

        return rays

    def generate_svg(self) -> str:
        """Generate the complete SVG logo."""
        size = self.config.size
        center = size / 2
        available_radius = (size / 2) - self.config.padding
        center_radius = available_radius * self.config.center_radius

        # Build SVG
        svg_parts = [
            f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {size} {size}" width="{size}" height="{size}">'
        ]

        # Add background if specified
        if self.config.background:
            svg_parts.append(
                f'<rect width="{size}" height="{size}" fill="{self.config.background}"/>'
            )

        # Add defs for animations and gradients
        svg_parts.append('<defs>')

        # Pulse animation
        if self.config.animate_pulse:
            svg_parts.append(f'''
                <style>
                    @keyframes pulse {{
                        0%, 100% {{ opacity: 1; transform: scale(1); }}
                        50% {{ opacity: 0.8; transform: scale(0.98); }}
                    }}
                    .rays {{ animation: pulse {self.config.animation_duration}ms ease-in-out infinite; transform-origin: center; }}
                </style>
            ''')

        # Rotate animation
        if self.config.animate_rotate:
            svg_parts.append(f'''
                <style>
                    @keyframes rotate {{
                        from {{ transform: rotate(0deg); }}
                        to {{ transform: rotate(360deg); }}
                    }}
                    .rays {{ animation: rotate {self.config.animation_duration * 10}ms linear infinite; transform-origin: center; }}
                </style>
            ''')

        svg_parts.append('</defs>')

        # Rays group
        ray_class = 'class="rays"' if (self.config.animate_pulse or self.config.animate_rotate) else ''
        svg_parts.append(f'<g {ray_class}>')

        # Draw rays
        rays = self._calculate_ray_points()
        for x1, y1, x2, y2 in rays:
            svg_parts.append(
                f'<line x1="{x1:.2f}" y1="{y1:.2f}" x2="{x2:.2f}" y2="{y2:.2f}" '
                f'stroke="{self.config.ray_color}" stroke-width="{self.config.ray_width}" '
                f'stroke-linecap="{self.config.ray_cap}"/>'
            )

        svg_parts.append('</g>')

        # Center circle
        svg_parts.append(
            f'<circle cx="{center}" cy="{center}" r="{center_radius}" '
            f'fill="{self.config.center_fill}" stroke="{self.config.center_stroke}" stroke-width="2"/>'
        )

        # Center letter
        font_size = self.config.size * self.config.center_font_size
        svg_parts.append(
            f'<text x="{center}" y="{center}" '
            f'font-family="\'Styrene A\', \'Inter\', system-ui, sans-serif" '
            f'font-size="{font_size}" font-weight="700" '
            f'fill="{self.config.letter_color}" '
            f'text-anchor="middle" dominant-baseline="central">'
            f'{self.config.center_letter}</text>'
        )

        svg_parts.append('</svg>')

        return '\n'.join(svg_parts)

    def save(self, path: Path) -> None:
        """Save logo to file."""
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(self.generate_svg(), encoding='utf-8')


def generate_logo_svg(
    size: int = 200,
    theme: str = "default",
    animate: bool = False,
    letter: str = "S"
) -> str:
    """
    Quick function to generate a logo SVG.

    Args:
        size: Logo size in pixels
        theme: Color theme name (default, light, dark, warm, cool)
        animate: Enable pulse animation
        letter: Center letter

    Returns:
        SVG string
    """
    from .themes import get_theme

    theme_config = get_theme(theme)

    config = StarburstConfig(
        size=size,
        ray_color=theme_config.primary,
        center_fill=theme_config.primary,
        center_stroke=theme_config.primary,
        letter_color=theme_config.on_primary,
        background=theme_config.background,
        center_letter=letter,
        animate_pulse=animate
    )

    logo = StarburstLogo(config)
    return logo.generate_svg()


def generate_favicon(output_dir: Path) -> None:
    """Generate favicon variants for the dashboard."""
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Generate different sizes
    for size in [16, 32, 48, 64, 128, 256]:
        config = StarburstConfig(
            size=size,
            padding=int(size * 0.1),
            ray_width=max(1, size * 0.015),
            center_radius=0.25,
            center_font_size=0.15
        )
        logo = StarburstLogo(config)
        logo.save(output_dir / f"favicon-{size}.svg")

    # Generate animated version
    config = StarburstConfig(
        size=64,
        animate_pulse=True,
        animation_duration=2000
    )
    logo = StarburstLogo(config)
    logo.save(output_dir / "favicon-animated.svg")


if __name__ == "__main__":
    # Demo: generate logo variants
    import sys

    output_dir = Path(__file__).parent.parent.parent / ".slate_identity" / "logos"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Default logo
    logo = StarburstLogo()
    logo.save(output_dir / "slate-logo.svg")
    print(f"Generated: {output_dir / 'slate-logo.svg'}")

    # Dark mode logo
    dark_config = StarburstConfig(
        ray_color="#D4785A",
        center_fill="#D4785A",
        letter_color="#1A1816",
        background="#1A1816"
    )
    dark_logo = StarburstLogo(dark_config)
    dark_logo.save(output_dir / "slate-logo-dark.svg")
    print(f"Generated: {output_dir / 'slate-logo-dark.svg'}")

    # Animated logo
    animated_config = StarburstConfig(
        animate_pulse=True,
        animation_duration=2000
    )
    animated_logo = StarburstLogo(animated_config)
    animated_logo.save(output_dir / "slate-logo-animated.svg")
    print(f"Generated: {output_dir / 'slate-logo-animated.svg'}")

    # Generate favicons
    generate_favicon(output_dir / "favicons")
    print(f"Generated favicons in: {output_dir / 'favicons'}")

    print("\nLogo generation complete!")
