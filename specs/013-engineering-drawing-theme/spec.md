# Spec 013: Engineering Drawing Theme System

**Status**: implementing
**Priority**: P0 (Core System Ethos)
**Created**: 2026-02-07
**Author**: Claude Opus 4.5

## Overview

This specification establishes SLATE's visual identity based on engineering drawing standards. All UI elements, schematics, diagrams, and visual outputs must adhere to these conventions, creating a unified "hardware design" aesthetic that visually organizes code like hardware designs.

## Core Ethos

> **"Systems Evolve With Progress"**
>
> Every visual element in SLATE should reflect the living, evolving nature of the system.
> Schematics are not static decorations—they are real-time reflections of system state.

## Standards Foundation

### ISO 128 - Technical Drawing Conventions

Reference: [ISO 128-2:2022](https://www.iso.org/standard/83355.html)

| Line Type | Designation | SLATE Usage | CSS/SVG |
|-----------|-------------|-------------|---------|
| **Continuous thick** | Type 01 | Component outlines, active connections | `stroke-width: 2px; stroke-dasharray: none` |
| **Continuous thin** | Type 02 | Dimension lines, leader lines | `stroke-width: 1px; stroke-dasharray: none` |
| **Dashed thick** | Type 03 | Hidden components, inactive services | `stroke-width: 2px; stroke-dasharray: 8,4` |
| **Dashed thin** | Type 04 | Hidden details, pending tasks | `stroke-width: 1px; stroke-dasharray: 6,3` |
| **Chain thin** | Type 05 | Center lines, symmetry axes | `stroke-width: 1px; stroke-dasharray: 12,3,3,3` |
| **Chain thick** | Type 06 | Cut planes, section indicators | `stroke-width: 2px; stroke-dasharray: 16,4,4,4` |
| **Dotted thin** | Type 07 | Projection lines, data flow | `stroke-width: 1px; stroke-dasharray: 2,2` |
| **Long-dash double-short** | Type 08 | Boundaries, system limits | `stroke-width: 1px; stroke-dasharray: 18,3,3,3,3,3` |

### IEC 60617 - Electronic Schematic Symbols

Reference: [IEC 60617:2025 Database](https://std.iec.ch/iec60617)

SLATE component mapping to IEC symbol conventions:

| SLATE Component | IEC Symbol Type | Visual Representation |
|-----------------|-----------------|----------------------|
| **Service/Server** | Amplifier (general) | Rectangle with triangle corner |
| **Database** | Capacitor | Cylinder (parallel plates) |
| **GPU/Compute** | Integrated Circuit | Hexagon with pin indicators |
| **AI/ML Service** | Processor | Rectangle with internal grid |
| **API Endpoint** | Terminal | Circle with directional arrow |
| **Message Bus** | Bus bar | Thick line with tap points |
| **Data Flow** | Signal flow | Arrow with dashed line |
| **Power/Active** | Voltage source | Filled circle with glow |
| **Ground/Inactive** | Ground symbol | Three horizontal lines |

### ASME Y14.44 - Reference Designators

Reference: [ASME Y14.44-2008](https://www.asme.org/codes-standards)

Component naming conventions for SLATE schematics:

| Component Type | Designator | Examples |
|----------------|------------|----------|
| **Core Services** | SVC | SVC1 (orchestrator), SVC2 (dashboard) |
| **Databases** | DB | DB1 (ChromaDB), DB2 (SQLite) |
| **GPU Units** | GPU | GPU0, GPU1 |
| **AI Models** | AI | AI1 (Ollama), AI2 (Foundry) |
| **API Routes** | API | API1 (status), API2 (workflow) |
| **Connectors** | J | J1-J2 (connection between components) |
| **Buses** | BUS | BUS1 (data bus), BUS2 (event bus) |
| **Terminals** | T | T1 (input), T2 (output) |

### PCB Silkscreen Conventions

Reference: [Cadence PCB Silkscreen Guidelines](https://resources.pcb.cadence.com/blog/2022-essential-pcb-silkscreen-guidelines-for-layout)

Text and labeling standards:

| Element | Size | Font | Color |
|---------|------|------|-------|
| **Component Labels** | 14px | Consolas | #A8A29E (warm gray) |
| **Reference Designators** | 12px | Consolas Bold | #C9956B (copper) |
| **Pin Numbers** | 10px | Consolas | #78716C (muted) |
| **Status Indicators** | 8px | Consolas | Varies by state |
| **Section Headers** | 16px | Segoe UI Semibold | #E7E0D8 (cream) |

Polarity and orientation markers:
- **Pin 1 indicator**: Filled circle (●)
- **Active/Power**: Plus sign (+) or filled dot
- **Ground/Inactive**: Minus sign (-) or empty circle (○)
- **Bidirectional**: Double arrow (↔)
- **Unidirectional**: Single arrow (→ or ←)

## Color Palette (Engineering Drawing)

Based on engineering drawing conventions with SLATE theming:

```
┌─────────────────────────────────────────────────────────────────┐
│ SLATE Engineering Drawing Color System                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BLUEPRINT BACKGROUND                                           │
│  ┌──────────────────────────────────────────────┐              │
│  │ Primary:    #0D1B2A (deep blueprint blue)    │              │
│  │ Secondary:  #0a0a0a (SLATE dark)             │              │
│  │ Tertiary:   #1B2838 (lighter blueprint)      │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
│  TRACE COLORS (by priority/type)                                │
│  ┌──────────────────────────────────────────────┐              │
│  │ Signal:     #B87333 (copper - primary)       │              │
│  │ Power:      #C47070 (warm red)               │              │
│  │ Ground:     #78716C (cool gray)              │              │
│  │ Data:       #7EA8BE (soft blue)              │              │
│  │ Control:    #D4A054 (gold)                   │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
│  STATUS INDICATORS                                              │
│  ┌──────────────────────────────────────────────┐              │
│  │ Active:     #22C55E (green - live)           │              │
│  │ Pending:    #D4A054 (gold - waiting)         │              │
│  │ Error:      #C47070 (red - fault)            │              │
│  │ Disabled:   #333333 (dim gray)               │              │
│  │ Unknown:    #4B5563 (neutral gray)           │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
│  COMPONENT FILLS                                                │
│  ┌──────────────────────────────────────────────┐              │
│  │ Service:    #1a1510 (dark warm)              │              │
│  │ Database:   #101520 (dark cool)              │              │
│  │ GPU:        #15120a (dark copper)            │              │
│  │ AI:         #0a1515 (dark teal)              │              │
│  │ External:   #151015 (dark purple)            │              │
│  └──────────────────────────────────────────────┘              │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Grid System

Engineering drawings use standardized grid systems:

```
┌─────────────────────────────────────────────────────────────────┐
│ SLATE Engineering Grid                                          │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  BASE UNIT: 8px (matches ISO drawing module)                    │
│                                                                 │
│  Grid Levels:                                                   │
│  ├── Major Grid:  64px (8 × base)  │ Component placement       │
│  ├── Minor Grid:  16px (2 × base)  │ Element alignment         │
│  └── Micro Grid:   8px (1 × base)  │ Fine adjustments          │
│                                                                 │
│  Component Sizes (multiples of major grid):                     │
│  ├── Small:    64×64px   (1×1 major)  │ Status indicators      │
│  ├── Medium:  128×64px   (2×1 major)  │ Services, APIs         │
│  ├── Large:   128×128px  (2×2 major)  │ Databases, AI models   │
│  └── XLarge:  256×128px  (4×2 major)  │ System groups          │
│                                                                 │
│  Spacing:                                                       │
│  ├── Between components: 32px (4 × base)                        │
│  ├── Between groups:     64px (8 × base)                        │
│  └── Margin to edge:     48px (6 × base)                        │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Component Shapes

Standard schematic component shapes following IEC conventions:

### Service Node (SVC)
```svg
<rect x="0" y="0" width="128" height="64" rx="4"
      fill="#1a1510" stroke="#B87333" stroke-width="2"/>
<!-- Pin 1 indicator -->
<circle cx="8" cy="8" r="3" fill="#B87333"/>
<!-- Reference designator -->
<text x="64" y="40" text-anchor="middle"
      fill="#C9956B" font-family="Consolas" font-size="12">SVC1</text>
```

### Database Node (DB)
```svg
<!-- Cylinder representation -->
<ellipse cx="64" cy="16" rx="48" ry="12"
         fill="#101520" stroke="#7EA8BE" stroke-width="2"/>
<rect x="16" y="16" width="96" height="48"
      fill="#101520" stroke="#7EA8BE" stroke-width="2"/>
<ellipse cx="64" cy="64" rx="48" ry="12"
         fill="#101520" stroke="#7EA8BE" stroke-width="2"/>
<text x="64" y="44" text-anchor="middle"
      fill="#7EA8BE" font-family="Consolas" font-size="12">DB1</text>
```

### GPU Node (GPU)
```svg
<!-- Hexagon for compute resources -->
<polygon points="64,0 120,24 120,72 64,96 8,72 8,24"
         fill="#15120a" stroke="#D4A054" stroke-width="2"/>
<!-- Grid pattern inside -->
<pattern id="gpuGrid" width="8" height="8" patternUnits="userSpaceOnUse">
  <path d="M 0 0 L 8 0 M 0 0 L 0 8" stroke="#D4A054" stroke-width="0.5" opacity="0.3"/>
</pattern>
<text x="64" y="52" text-anchor="middle"
      fill="#D4A054" font-family="Consolas" font-size="12">GPU0</text>
```

### AI/ML Node (AI)
```svg
<!-- Processor-style rectangle with brain icon suggestion -->
<rect x="0" y="0" width="128" height="96" rx="0"
      fill="#0a1515" stroke="#78B89A" stroke-width="2"/>
<!-- Internal circuit pattern -->
<path d="M 32 24 L 96 24 M 32 48 L 96 48 M 32 72 L 96 72"
      stroke="#78B89A" stroke-width="1" opacity="0.5"/>
<text x="64" y="56" text-anchor="middle"
      fill="#78B89A" font-family="Consolas" font-size="12">AI1</text>
```

### Terminal/Endpoint (T)
```svg
<!-- Circle with directional arrow -->
<circle cx="24" cy="24" r="20"
        fill="#151015" stroke="#B07AAE" stroke-width="2"/>
<polygon points="24,8 32,24 24,16 16,24"
         fill="#B07AAE"/>
<text x="24" y="58" text-anchor="middle"
      fill="#B07AAE" font-family="Consolas" font-size="10">T1</text>
```

## Connection Types

### Data Flow (continuous thin with arrow)
```svg
<line x1="0" y1="0" x2="100" y2="0"
      stroke="#7EA8BE" stroke-width="1"/>
<polygon points="100,0 92,-4 92,4" fill="#7EA8BE"/>
```

### Power/Active Connection (continuous thick)
```svg
<line x1="0" y1="0" x2="100" y2="0"
      stroke="#C47070" stroke-width="2"/>
```

### Pending/Processing (dashed thin)
```svg
<line x1="0" y1="0" x2="100" y2="0"
      stroke="#D4A054" stroke-width="1" stroke-dasharray="6,3"/>
```

### Inactive/Disabled (dashed thick gray)
```svg
<line x1="0" y1="0" x2="100" y2="0"
      stroke="#333333" stroke-width="2" stroke-dasharray="8,4"/>
```

### Bus Connection (thick with taps)
```svg
<line x1="0" y1="0" x2="200" y2="0"
      stroke="#B87333" stroke-width="4"/>
<!-- Tap points -->
<line x1="50" y1="-8" x2="50" y2="8" stroke="#B87333" stroke-width="2"/>
<line x1="100" y1="-8" x2="100" y2="8" stroke="#B87333" stroke-width="2"/>
<line x1="150" y1="-8" x2="150" y2="8" stroke="#B87333" stroke-width="2"/>
```

## Title Block

Every SLATE schematic must include a title block (engineering drawing convention):

```
┌─────────────────────────────────────────────────────────────────┐
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    [SCHEMATIC CONTENT]                   │   │
│  │                                                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌──────────────────────────────────┬──────────────────────┐   │
│  │ SLATE Schematic                  │ Rev: 1.0             │   │
│  │ System Architecture              │ Date: 2026-02-07     │   │
│  ├──────────────────────────────────┼──────────────────────┤   │
│  │ Scale: 1:1                       │ Sheet: 1 of 1        │   │
│  │ Generated by: Schematic SDK      │ Approved: SLATE      │   │
│  └──────────────────────────────────┴──────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

## Animation Standards

For live/evolving schematics:

| State | Animation | Duration | Easing |
|-------|-----------|----------|--------|
| **Active pulse** | Opacity 0.7→1.0→0.7 | 2s | ease-in-out |
| **Data flow** | Dash offset animation | 1s | linear |
| **Connection establish** | Stroke-dashoffset 100→0 | 0.5s | ease-out |
| **Component appear** | Scale 0.8→1.0, opacity 0→1 | 0.3s | ease-out |
| **Status change** | Fill color transition | 0.3s | ease-in-out |
| **Error flash** | 3× opacity pulse | 0.2s each | ease-in-out |

## Application Points

This engineering drawing theme must be applied to:

| System | Implementation |
|--------|----------------|
| **GitHub Pages** | `docs/pages/index.html` - Blueprint background, schematic hero |
| **Dashboard** | `slate_web/dashboard_template.py` - Grid overlay, component cards |
| **Schematic SDK** | `slate/schematic_sdk/` - All diagram generation |
| **VS Code Theme** | `plugins/slate-copilot/themes/` - Token colors, backgrounds |
| **Tech Tree** | D3.js visualization - Node shapes, connection styles |
| **Wiki Diagrams** | Auto-generated from specs using engineering conventions |
| **Logo/Branding** | All SVG assets follow line type standards |

## Validation Checklist

- [ ] All line types follow ISO 128 designations
- [ ] All components use IEC 60617-inspired shapes
- [ ] All labels follow ASME Y14.44 reference designator format
- [ ] Grid alignment verified (8px base unit)
- [ ] Color palette matches specification
- [ ] Title block present on all schematics
- [ ] Animation standards followed for live elements
- [ ] Font families restricted to Consolas (mono) and Segoe UI (sans)

## References

- [ISO 128 - Wikipedia](https://en.wikipedia.org/wiki/ISO_128)
- [ISO 128-2:2022](https://www.iso.org/standard/83355.html) - Basic conventions for lines
- [IEC 60617:2025 Database](https://std.iec.ch/iec60617) - Graphical symbols for diagrams
- [ASME Y14.44-2008](https://www.ultralibrarian.com/2021/07/07/standard-pcb-reference-designators-to-know-ulc/) - Reference designators
- [Cadence PCB Silkscreen Guidelines](https://resources.pcb.cadence.com/blog/2022-essential-pcb-silkscreen-guidelines-for-layout)

---

*This specification is a core SLATE ethos document. All visual systems must comply.*
