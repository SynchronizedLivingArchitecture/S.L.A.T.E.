# Specification: Natural Theme System with Procedural Gradient
<!-- Auto-generated from specs/006-natural-theme-system/spec.md -->
<!-- Generated: 2026-02-07T09:49:48.444057+00:00 -->

| Property | Value |
|----------|-------|
| **Spec Id** | 006-natural-theme-system |
| **Status** | completed |
| **Created** | 2026-02-07 |
| **Completed** | 2026-02-07 |
| **Inspiration** | https://www.awwwards.com/ |
| **Primary Reference** | Awwwards (https://www.awwwards.com/) |

## Contents

- [Overview](#overview)
- [Design Inspiration Source](#design-inspiration-source)
- [Procedural Theme System](#procedural-theme-system)
  - [Theme Slider Concept](#theme-slider-concept)
  - [CSS Variable Interpolation](#css-variable-interpolation)
  - [Natural Color Palette](#natural-color-palette)
- [Component Architecture](#component-architecture)
  - [Linux-Style Modular Structure](#linux-style-modular-structure)
  - [Widget Categories](#widget-categories)
- [Hardware Control Interface](#hardware-control-interface)
  - [GPU Panel](#gpu-panel)
  - [Benchmark Display](#benchmark-display)
- [Docker Integration Panel](#docker-integration-panel)
- [Typography System](#typography-system)
- [Spacing System](#spacing-system)
- [Animation System](#animation-system)
- [Responsive Breakpoints](#responsive-breakpoints)
- [Implementation Files](#implementation-files)
  - [New Files](#new-files)
  - [Modified Files](#modified-files)
- [API Endpoints (New)](#api-endpoints-new)
- [Accessibility Requirements](#accessibility-requirements)
- [Files Modified](#files-modified)

---

## Overview

Complete UI overhaul of the SLATE dashboard implementing a modern natural theme system with:
- Procedural dark/light mode slider (0=dark, 1=light)
- Natural color palette with organic tones
- Hardware control interfaces with real-time benchmarks
- Docker and integration panels
- Linux-style modular component architecture

## Design Inspiration Source

**Primary Reference**: Awwwards (https://www.awwwards.com/)

Key design patterns extracted:
- CSS Grid-heavy approach with auto-fill/auto-fit
- Fluid typography using `clamp()` functions
- Glassmorphism with layered `rgba()` backgrounds
- Smooth `.3s` transitions for micro-interactions
- Modular CSS variables for white-label customization
- Container queries for component-level responsiveness

## Procedural Theme System

### Theme Slider Concept

```
0.0 ────────────────────── 0.5 ────────────────────── 1.0
DARK                      NEUTRAL                    LIGHT
#0a0f0a                   #4a524a                    #f5f7f5
```

The slider value (0-1) interpolates ALL theme colors procedurally:
- Background colors
- Text colors
- Border colors
- Shadow intensities
- Glassmorphism opacity

### CSS Variable Interpolation

```css
:root {
  --theme-value: 0.2; /* 0=dark, 1=light */

  /* Computed from theme-value */
  --bg-primary: color-mix(in oklch, #0a0f0a calc((1 - var(--theme-value)) * 100%), #f5f7f5);
  --text-primary: color-mix(in oklch, #f5f7f5 calc((1 - var(--theme-value)) * 100%), #1a1f1a);
}
```

### Natural Color Palette

| Variable | Value | Usage |
|----------|-------|-------|
| `--status-success` | #22c55e | Success/Online |
| `--status-warning` | #eab308 | Warning/Caution |
| `--status-error` | #ef4444 | Error/Offline |
| `--status-info` | #3b82f6 | Information |

## Component Architecture

### Linux-Style Modular Structure

```
┌─────────────────────────────────────────────────────────────┐
│ HEADER (sticky)                                             │
│ ┌─────────┬─────────────────────────┬────────────────────┐  │
│ │ Logo    │ S.L.A.T.E.              │ Theme Slider [═══] │  │
│ └─────────┴─────────────────────────┴────────────────────┘  │
├─────────────────────────────────────────────────────────────┤
│ NAVIGATION (collapsible sidebar - Linux file manager style) │
│ ┌───────────┐ ┌──────────────────────────────────────────┐  │
│ │ Dashboard │ │                                          │  │
│ │ Hardware  │ │  MAIN CONTENT AREA                       │  │
│ │ Docker    │ │  (modular widget grid)                   │  │
│ │ Workflows │ │                                          │  │
│ │ Tasks     │ │                                          │  │
│ │ GitHub    │ │                                          │  │
│ │ AI        │ │                                          │  │
│ │ Settings  │ │                                          │  │
│ └───────────┘ └──────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### Widget Categories

- Theme configuration
- Integration toggles
- API key management
- System preferences

## Hardware Control Interface

### GPU Panel

```
┌─────────────────────────────────────────────┐
│ GPU 0: RTX 5070 Ti                    [72°C]│
│ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓░░░░░░  65% GPU  │
│ ▓▓▓▓▓▓▓▓░░░░░░░░░░░░  42% VRAM │
│ Memory: 6.8 / 16 GB                         │
├─────────────────────────────────────────────┤
│ GPU 1: RTX 5070 Ti                    [68°C]│
│ ▓▓▓▓▓▓▓▓▓▓░░░░░░░░░░  52% GPU  │
│ ▓▓▓▓▓▓░░░░░░░░░░░░░░  35% VRAM │
│ Memory: 5.2 / 16 GB                         │
├─────────────────────────────────────────────┤
│ [Run Benchmark] [Balance Load] [Cool Down]  │
└─────────────────────────────────────────────┘
```

### Benchmark Display

```
┌─────────────────────────────────────────────┐
│ BENCHMARK RESULTS                           │
│ ─────────────────────────────────────────── │
│ Inference Speed: 45.2 tokens/sec            │
│ Memory Bandwidth: 448 GB/s                  │
│ FP16 Performance: 28.3 TFLOPS               │
│ Power Efficiency: 0.85 tok/W                │
│ ─────────────────────────────────────────── │
│ Last Run: 2026-02-07 10:30:00               │
│ [View History] [Export Report]              │
└─────────────────────────────────────────────┘
```

## Docker Integration Panel

```
┌─────────────────────────────────────────────┐
│ CONTAINERS                                  │
├─────────────────────────────────────────────┤
│ ● slate-dashboard     Running    8080:8080  │
│ ● ollama              Running   11434:11434 │
│ ○ chromadb            Stopped    8000:8000  │
│ ● foundry-local       Running    5272:5272  │
├─────────────────────────────────────────────┤
│ COMPOSE PROJECTS                            │
├─────────────────────────────────────────────┤
│ 📁 slate-stack        3/4 containers        │
│ 📁 ai-services        2/2 containers        │
├─────────────────────────────────────────────┤
│ [Start All] [Stop All] [Prune] [Compose Up] │
└─────────────────────────────────────────────┘
```

## Typography System

Using fluid scaling with `clamp()`:

```css
:root {
  /* Fluid Typography Scale */
  --font-xs: clamp(0.625rem, 0.5rem + 0.5vw, 0.75rem);
  --font-sm: clamp(0.75rem, 0.625rem + 0.5vw, 0.875rem);
  --font-base: clamp(0.875rem, 0.75rem + 0.5vw, 1rem);
  --font-lg: clamp(1rem, 0.875rem + 0.5vw, 1.125rem);
  --font-xl: clamp(1.125rem, 1rem + 0.5vw, 1.25rem);
  --font-2xl: clamp(1.25rem, 1rem + 1vw, 1.5rem);
  --font-3xl: clamp(1.5rem, 1.25rem + 1vw, 2rem);
  --font-display: clamp(2rem, 1.5rem + 2vw, 3rem);

  /* Font Families */
  --font-mono: 'Consolas', 'Monaco', 'Courier New', monospace;
  --font-sans: 'Segoe UI', 'Inter', system-ui, sans-serif;
}
```

## Spacing System

```css
:root {
  --space-xs: 0.25rem;   /* 4px */
  --space-sm: 0.5rem;    /* 8px */
  --space-md: 1rem;      /* 16px */
  --space-lg: 1.5rem;    /* 24px */
  --space-xl: 2rem;      /* 32px */
  --space-2xl: 3rem;     /* 48px */
  --gutter: 1.5rem;      /* Grid gutter */
}
```

## Animation System

```css
:root {
  --transition-fast: 0.15s ease;
  --transition-base: 0.25s ease;
  --transition-slow: 0.4s ease;
  --transition-spring: 0.5s cubic-bezier(0.34, 1.56, 0.64, 1);
}

@media (prefers-reduced-motion: reduce) {
  :root {
    --transition-fast: 0s;
    --transition-base: 0s;
    --transition-slow: 0s;
    --transition-spring: 0s;
  }
}
```

## Responsive Breakpoints

```css
/* Mobile first */
--bp-sm: 640px;   /* Small tablets */
--bp-md: 768px;   /* Tablets */
--bp-lg: 1024px;  /* Laptops */
--bp-xl: 1280px;  /* Desktops */
--bp-2xl: 1536px; /* Large screens */
```

## Implementation Files

### New Files

- `src/frontend/theme.js` - Theme slider logic
- `src/frontend/components/` - Modular components
- `src/frontend/styles/variables.css` - CSS variables
- `docs/specs/design-inspiration.json` - Dependency tracking

### Modified Files

- `agents/slate_dashboard_server.py` - Complete HTML/CSS/JS overhaul
- `.slate_identity/theme.css` - Updated with procedural system

## API Endpoints (New)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/theme` | GET/POST | Get/Set theme value |
| `/api/docker/containers` | GET | List Docker containers |
| `/api/docker/images` | GET | List Docker images |
| `/api/docker/compose` | GET | List compose projects |
| `/api/docker/action` | POST | Container actions |
| `/api/benchmark/run` | POST | Run GPU benchmark |
| `/api/benchmark/history` | GET | Benchmark history |

## Accessibility Requirements

- WCAG AAA compliance (16:1 contrast minimum in dark mode)
- Full keyboard navigation
- Screen reader support with ARIA labels
- Respect `prefers-reduced-motion`
- Respect `prefers-color-scheme` as default

## Files Modified

1. `agents/slate_dashboard_server.py` - Main dashboard overhaul
2. `.slate_identity/theme.css` - Theme system
3. `docs/specs/design-inspiration.json` - Awwwards dependency
4. New API endpoints for Docker/benchmark control

---
*Source: [specs/006-natural-theme-system/spec.md](../../../specs/006-natural-theme-system/spec.md)*
