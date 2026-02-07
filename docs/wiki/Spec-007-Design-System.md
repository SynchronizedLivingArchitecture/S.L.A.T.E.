# Specification 007: SLATE Unified Design System
<!-- Modified: 2026-02-07T12:00:00Z | Author: CLAUDE | Change: Create wiki page for spec 007 -->

**Status**: Implementing | **Created**: 2026-02-07

## Overview

Complete redesign of the SLATE GUI implementing a unified design system that synthesizes:
- **M3 Material Design**: Design tokens, elevation, state layers, dynamic color
- **Anthropic Geometric Art**: Starburst patterns, warm palette, human-centered philosophy
- **Awwwards Patterns**: Card architecture, data visualization, modern interactions

## Design Philosophy

### Core Principles

1. **Radiating Architecture** - Information flows outward from central focus points
2. **Dynamic Theming** - M3-style tonal palettes with procedural dark/light interpolation
3. **Human-Centered AI** - Warm, approachable aesthetics that avoid cold "tech" tropes
4. **Geometric Precision** - Clean, intentional forms with mathematical relationships
5. **Living System** - UI that evolves and responds to system state

### SLATE Identity

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

### Neutral Palette (Natural Earth)

| Token | Light Mode | Dark Mode | Usage |
|-------|------------|-----------|-------|
| `--slate-surface` | #FBF8F6 | #1A1816 | Main backgrounds |
| `--slate-surface-variant` | #F0EBE7 | #2A2624 | Card backgrounds |
| `--slate-on-surface` | #1C1B1A | #E8E2DE | Primary text |
| `--slate-outline` | #7D7873 | #968F8A | Borders |

### Semantic Colors

| Token | Value | Usage |
|-------|-------|-------|
| `--slate-success` | #4CAF50 | Success states, online indicators |
| `--slate-warning` | #FF9800 | Warning states, caution |
| `--slate-error` | #F44336 | Error states, offline |
| `--slate-info` | #2196F3 | Information, neutral actions |

## Typography System

### Font Stack

```css
--slate-font-display: 'Styrene A', 'Inter Tight', system-ui, sans-serif;
--slate-font-body: 'Tiempos Text', 'Georgia', serif;
--slate-font-mono: 'Cascadia Code', 'JetBrains Mono', 'Consolas', monospace;
```

### Type Scale (M3-Aligned)

| Token | Size | Weight | Usage |
|-------|------|--------|-------|
| `display-large` | 57px | 400 | Hero text |
| `headline-large` | 32px | 400 | Panel headers |
| `title-medium` | 16px | 500 | Card headers |
| `body-large` | 16px | 400 | Body text |
| `label-large` | 14px | 500 | Button text |

## Starburst Logo System

The SLATE logo uses a radiating starburst pattern:

```
        \   |   /
         \  |  /
    ------  S  ------
         /  |  \
        /   |   \

8 rays radiating at 45 degree intervals
Central "S" represents SLATE core
```

### Logo Parameters

- 8 rays with variable length (0.6 to 1.0 ratio)
- Center circle at 15% of container
- 22.5 degree rotation offset
- Pulse animation available

## Implementation Files

### New Files
- `slate/logo_generator/__init__.py` - Logo generation module
- `slate/logo_generator/starburst.py` - Starburst logo generator
- `slate/design_tokens.py` - Design token definitions
- `src/frontend/slate-design-system.css` - Complete CSS framework

### Modified Files
- `agents/slate_dashboard_server.py` - Complete UI rebuild
- `.slate_identity/theme.css` - Updated with M3 tokens
- `slate/slate_installer.py` - Integrated logo generation

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

### Button Variants

| Variant | Style | Usage |
|---------|-------|-------|
| Filled | Solid primary background | Primary actions |
| Outlined | Border only | Secondary actions |
| Text | No background | Tertiary actions |

### Elevation System

| Level | Shadow | Usage |
|-------|--------|-------|
| 0 | none | Background surfaces |
| 1 | subtle | Cards, list items |
| 2 | medium | Buttons, dropdowns |
| 3 | strong | Navigation, FABs |
| 4 | heavy | Dialogs, modals |
| 5 | maximum | Popovers, tooltips |

## Implementation Progress

- [x] Design token definitions
- [x] Starburst logo generator
- [x] Logo variants (dark, warm, animated)
- [x] CSS framework with M3 tokens
- [~] Dashboard UI rebuild
- [ ] Navigation rail
- [ ] Widget component library
- [ ] Animation system

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/design/tokens` | GET | Get current design tokens |
| `/api/design/theme` | GET/POST | Theme configuration |
| `/api/logo/generate` | POST | Generate logo variant |
| `/api/logo/preset` | GET | Get logo presets |

## CLI Commands

```bash
# Generate logo variants
python slate/logo_generator/starburst.py --output .slate_identity/logos/

# Export design tokens
python slate/design_tokens.py --export json > tokens.json

# Preview dashboard
python agents/slate_dashboard_server.py
```

## Related Specs

- [Spec 005: Monochrome Theme](Spec-005-Monochrome-Theme) - Predecessor
- [Spec 006: Natural Theme System](Spec-006-Natural-Theme-System) - Theme interpolation
- [Spec 008: Guided Experience](Spec-008-Guided-Experience) - Uses design system
