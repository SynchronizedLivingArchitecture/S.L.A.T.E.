# Specification: SLATE Unified Design System

**Spec ID**: 007-slate-design-system
**Status**: implementing
**Created**: 2026-02-07
**Inspiration Sources**:
- Google M3 Material Design: https://m3.material.io/
- Anthropic Geometric Art: https://geist.co/work/anthropic
- Awwwards Dashboard Gallery: https://www.awwwards.com/

## Overview

Complete redesign of the SLATE GUI implementing a unified design system that synthesizes:
- **M3 Material Design**: Design tokens, elevation, state layers, dynamic color
- **Anthropic Geometric Art**: Starburst patterns, warm palette, human-centered philosophy
- **Awwwards Patterns**: Card architecture, data visualization, modern interactions

The system includes a procedural logo generation framework piped into the generative GUI install.

## Design Philosophy

### Core Principles

1. **Radiating Architecture**: Information flows outward from central focus points (inspired by Anthropic's starburst)
2. **Dynamic Theming**: M3-style tonal palettes with procedural dark/light interpolation
3. **Human-Centered AI**: Warm, approachable aesthetics that avoid cold "tech" tropes
4. **Geometric Precision**: Clean, intentional forms with mathematical relationships
5. **Living System**: UI that evolves and responds to system state

### SLATE Identity

S.L.A.T.E. = **S**ynchronized **L**iving **A**rchitecture for **T**ransformation and **E**volution

The visual identity reflects:
- **Synchronized**: Harmonious color relationships, balanced layouts
- **Living**: Organic color palette, responsive animations
- **Architecture**: Structured grid systems, geometric foundations
- **Transformation**: Smooth transitions, state morphing
- **Evolution**: Adaptive theming, progressive disclosure

## Color System

### Primary Palette (SLATE Warm)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--slate-primary` | #B85A3C | #D4785A | Primary actions, focus states |
| `--slate-primary-container` | #FFE4D9 | #5C2E1E | Primary backgrounds |
| `--slate-on-primary` | #FFFFFF | #2A1508 | Text on primary |
| `--slate-on-primary-container` | #3D1E10 | #FFE4D9 | Text on primary container |

### Neutral Palette (Natural Earth)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--slate-surface` | #FBF8F6 | #1A1816 | Main backgrounds |
| `--slate-surface-variant` | #F0EBE7 | #2A2624 | Card backgrounds |
| `--slate-on-surface` | #1C1B1A | #E8E2DE | Primary text |
| `--slate-on-surface-variant` | #4D4845 | #CAC4BF | Secondary text |
| `--slate-outline` | #7D7873 | #968F8A | Borders |
| `--slate-outline-variant` | #CFC8C3 | #4D4845 | Subtle borders |

### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--slate-success` | #4CAF50 | Success states, online indicators |
| `--slate-warning` | #FF9800 | Warning states, caution |
| `--slate-error` | #F44336 | Error states, offline |
| `--slate-info` | #2196F3 | Information, neutral actions |

### Tonal Palette (M3-Style)

```
Primary Tonal Scale:
  0   5   10   20   30   40   50   60   70   80   90   95   99  100
  █   █   █    █    █    █    █    █    █    █    █    █    █   █
  Black → Deep Brown → Rust → Warm Orange → Peach → Cream → White
```

## Typography System

### Font Stack

```css
--slate-font-display: 'Styrene A', 'Inter Tight', system-ui, sans-serif;
--slate-font-body: 'Tiempos Text', 'Georgia', serif;
--slate-font-mono: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
```

### Type Scale (M3-Aligned)

| Token | Size | Weight | Line Height | Usage |
|-------|------|--------|-------------|-------|
| `--slate-display-large` | 57px | 400 | 64px | Hero text |
| `--slate-display-medium` | 45px | 400 | 52px | Section headers |
| `--slate-display-small` | 36px | 400 | 44px | Card titles |
| `--slate-headline-large` | 32px | 400 | 40px | Panel headers |
| `--slate-headline-medium` | 28px | 400 | 36px | Widget titles |
| `--slate-headline-small` | 24px | 400 | 32px | Subsections |
| `--slate-title-large` | 22px | 500 | 28px | Large labels |
| `--slate-title-medium` | 16px | 500 | 24px | Card headers |
| `--slate-title-small` | 14px | 500 | 20px | Small headers |
| `--slate-body-large` | 16px | 400 | 24px | Body text |
| `--slate-body-medium` | 14px | 400 | 20px | Default text |
| `--slate-body-small` | 12px | 400 | 16px | Captions |
| `--slate-label-large` | 14px | 500 | 20px | Button text |
| `--slate-label-medium` | 12px | 500 | 16px | Badges |
| `--slate-label-small` | 11px | 500 | 16px | Micro labels |

## Elevation System

### Shadow Tokens

```css
--slate-elevation-0: none;
--slate-elevation-1: 0 1px 2px rgba(0,0,0,0.05), 0 1px 3px rgba(0,0,0,0.1);
--slate-elevation-2: 0 2px 4px rgba(0,0,0,0.05), 0 4px 8px rgba(0,0,0,0.1);
--slate-elevation-3: 0 4px 8px rgba(0,0,0,0.08), 0 8px 16px rgba(0,0,0,0.12);
--slate-elevation-4: 0 8px 16px rgba(0,0,0,0.1), 0 16px 32px rgba(0,0,0,0.15);
--slate-elevation-5: 0 16px 32px rgba(0,0,0,0.12), 0 32px 64px rgba(0,0,0,0.18);
```

### Elevation Usage

| Level | Components |
|-------|------------|
| 0 | Background surfaces |
| 1 | Cards, list items |
| 2 | Buttons (pressed), dropdowns |
| 3 | Navigation bars, floating action buttons |
| 4 | Dialogs, modals |
| 5 | Popovers, tooltips |

## State Layers (M3)

```css
--slate-state-hover: 8%;      /* Overlay opacity on hover */
--slate-state-focus: 12%;     /* Overlay opacity on focus */
--slate-state-pressed: 12%;   /* Overlay opacity when pressed */
--slate-state-dragged: 16%;   /* Overlay opacity when dragging */
```

## Geometric Art Framework

### Starburst Logo System

The SLATE logo uses a radiating starburst pattern:

```
        ╲   │   ╱
         ╲  │  ╱
    ──────  S  ──────
         ╱  │  ╲
        ╱   │   ╲

8 rays radiating at 45° intervals
Central "S" represents SLATE core
Rays represent the 5 SLATE principles:
  - Synchronized (top)
  - Living (upper-right)
  - Architecture (right)
  - Transformation (lower-right)
  - Evolution (bottom)
  + 3 additional rays for balance
```

### Logo Generation Parameters

```python
{
    "rays": 8,
    "ray_length": [0.6, 1.0],  # Min/max as ratio of container
    "ray_width": 2,            # Stroke width
    "center_radius": 0.15,     # Center circle ratio
    "rotation": 22.5,          # Offset to avoid cardinal alignment
    "color_scheme": "primary", # Uses --slate-primary
    "animation": {
        "pulse": True,
        "rotate": False,
        "duration": 2000
    }
}
```

## Component Architecture

### Card Component

```css
.slate-card {
    background: var(--slate-surface-variant);
    border: 1px solid var(--slate-outline-variant);
    border-radius: 16px;
    padding: 16px;
    box-shadow: var(--slate-elevation-1);
    transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.slate-card:hover {
    box-shadow: var(--slate-elevation-2);
    transform: translateY(-2px);
}
```

### Button Component

```css
.slate-btn {
    font-family: var(--slate-font-display);
    font-size: var(--slate-label-large);
    padding: 10px 24px;
    border-radius: 20px;
    border: none;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}

.slate-btn-filled {
    background: var(--slate-primary);
    color: var(--slate-on-primary);
}

.slate-btn-outlined {
    background: transparent;
    border: 1px solid var(--slate-outline);
    color: var(--slate-primary);
}

.slate-btn-text {
    background: transparent;
    color: var(--slate-primary);
}
```

### Navigation Rail

```css
.slate-nav-rail {
    width: 80px;
    background: var(--slate-surface);
    border-right: 1px solid var(--slate-outline-variant);
    display: flex;
    flex-direction: column;
    align-items: center;
    padding: 12px 0;
    gap: 4px;
}

.slate-nav-item {
    width: 56px;
    height: 56px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    cursor: pointer;
    transition: background 0.2s;
}

.slate-nav-item:hover {
    background: rgba(var(--slate-primary-rgb), 0.08);
}

.slate-nav-item.active {
    background: var(--slate-primary-container);
}
```

## Motion System

### Easing Curves

```css
--slate-easing-standard: cubic-bezier(0.4, 0, 0.2, 1);
--slate-easing-decelerate: cubic-bezier(0, 0, 0.2, 1);
--slate-easing-accelerate: cubic-bezier(0.4, 0, 1, 1);
--slate-easing-spring: cubic-bezier(0.34, 1.56, 0.64, 1);
```

### Duration Scale

```css
--slate-duration-short1: 50ms;
--slate-duration-short2: 100ms;
--slate-duration-short3: 150ms;
--slate-duration-short4: 200ms;
--slate-duration-medium1: 250ms;
--slate-duration-medium2: 300ms;
--slate-duration-medium3: 350ms;
--slate-duration-medium4: 400ms;
--slate-duration-long1: 450ms;
--slate-duration-long2: 500ms;
--slate-duration-long3: 550ms;
--slate-duration-long4: 600ms;
```

## Dashboard Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│ HEADER (Sticky)                                                      │
│ ┌──────┬────────────────────────────┬────────────────────────────┐  │
│ │ LOGO │ S.L.A.T.E.                 │ [Theme] [Status] [Actions] │  │
│ └──────┴────────────────────────────┴────────────────────────────┘  │
├─────────────────────────────────────────────────────────────────────┤
│ ┌────┐ ┌─────────────────────────────────────────────────────────┐  │
│ │    │ │ MAIN CONTENT (Radiating Grid)                           │  │
│ │ N  │ │                                                          │  │
│ │ A  │ │   ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐      │  │
│ │ V  │ │   │ CENTRAL │ │  WIDGET │ │  WIDGET │ │  WIDGET │      │  │
│ │    │ │   │  FOCUS  │ │         │ │         │ │         │      │  │
│ │ R  │ │   └─────────┘ └─────────┘ └─────────┘ └─────────┘      │  │
│ │ A  │ │                                                          │  │
│ │ I  │ │   ┌─────────┐ ┌─────────────────────┐ ┌─────────┐      │  │
│ │ L  │ │   │  WIDGET │ │     WIDE WIDGET     │ │  WIDGET │      │  │
│ │    │ │   │         │ │                     │ │         │      │  │
│ └────┘ │   └─────────┘ └─────────────────────┘ └─────────┘      │  │
│        └─────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

## Implementation Files

### New Files
- `slate/logo_generator/__init__.py` - Logo generation module
- `slate/logo_generator/starburst.py` - Starburst logo generator
- `slate/logo_generator/themes.py` - Theme color presets
- `slate/design_tokens.py` - Design token definitions
- `src/frontend/slate-design-system.css` - Complete CSS framework

### Modified Files
- `agents/slate_dashboard_server.py` - Complete UI rebuild
- `.slate_identity/theme.css` - Updated with M3 tokens
- `slate/slate_installer.py` - Integrated logo generation

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/design/tokens` | GET | Get current design tokens |
| `/api/design/theme` | GET/POST | Theme configuration |
| `/api/logo/generate` | POST | Generate logo variant |
| `/api/logo/preset` | GET | Get logo presets |
