# SLATE Schematic-Integrated GUI Layout Specification

**Spec ID**: 012-schematic-gui-layout
**Status**: implementing
**Created**: 2026-02-08
**Author**: Claude Opus 4.5
**Depends On**: spec-007 (Design System), spec-008 (Guided Experience), spec-011 (Schematic SDK)

## Overview

This specification defines layout standards for integrating schematic diagrams as first-class visualization components within the SLATE dashboard and other GUI surfaces. Schematics become part of SLATE's **Generative UI protocols** alongside the locked theme (v3.0.0).

## Design Philosophy

### Schematic as UI Component
1. **Visual Hierarchy** - Schematics serve as hero elements and status indicators
2. **Information Density** - Circuit-board aesthetic conveys technical depth
3. **Real-Time Reflection** - Live system state reflected in diagram status
4. **Progressive Detail** - Overview → focused component → full architecture

### Layout Zones
1. **Hero Zone** - Full-width schematic as primary visual anchor
2. **Widget Zone** - Compact schematics in sidebars/panels
3. **Detail Zone** - Focused component diagrams in modals/overlays
4. **Background Zone** - Subtle schematic patterns as visual texture

## Layout Grid System

### Dashboard Main Layout
```
┌─────────────────────────────────────────────────────────────────────────────┐
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                        HEADER / NAVIGATION                               │ │
│ │  Logo   │   Status Bar   │   Nav Links   │   Actions   │   User         │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌───────────────────────────────────────────────────────────────┐ ┌───────┐ │
│ │                                                               │ │ SIDE  │ │
│ │                     HERO SCHEMATIC ZONE                       │ │ PANEL │ │
│ │                  (System Architecture Live)                   │ │       │ │
│ │                                                               │ │ Compact│ │
│ │  ┌─────────┐      ┌─────────┐      ┌─────────┐               │ │ Schema │ │
│ │  │Dashboard├──────┤ Router  ├──────┤ Ollama  │               │ │ Widget │ │
│ │  └─────────┘      └─────────┘      └─────────┘               │ │       │ │
│ │                         │                │                    │ │ ───── │ │
│ │                         ▼                ▼                    │ │       │ │
│ │                   ┌─────────┐      ┌─────────┐               │ │ Quick │ │
│ │                   │ Runner  │      │  GPU    │               │ │ Actions│ │
│ │                   └─────────┘      └─────────┘               │ │       │ │
│ │                                                               │ │ Status │ │
│ └───────────────────────────────────────────────────────────────┘ └───────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                        CONTENT GRID                                      │ │
│ │  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐                 │ │
│ │  │ Task     │  │ Activity │  │ Workflow │  │ GPU      │                 │ │
│ │  │ Queue    │  │ Feed     │  │ Status   │  │ Metrics  │                 │ │
│ │  └──────────┘  └──────────┘  └──────────┘  └──────────┘                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
│ ┌─────────────────────────────────────────────────────────────────────────┐ │
│ │                        FOOTER / CONTROLS                                 │ │
│ └─────────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Grid Specifications

| Zone | Width | Height | Content |
|------|-------|--------|---------|
| Header | 100% | 64px | Logo, status, nav |
| Hero Schematic | 70-80% | 300-500px | Live system diagram |
| Side Panel | 20-30% | auto | Compact widgets |
| Content Grid | 100% | auto | Cards, lists, metrics |
| Footer | 100% | 48px | Actions, controls |

### Breakpoints

| Breakpoint | Width | Layout |
|------------|-------|--------|
| Desktop XL | ≥1440px | Full grid, hero + side panel |
| Desktop | ≥1200px | Full grid, hero + collapsible side |
| Tablet | ≥768px | Stacked, hero above content |
| Mobile | <768px | Stacked, compact schematic |

## Schematic Widget Types

### 1. Hero Schematic Widget
Full-width primary visualization

```css
.schematic-hero {
    width: 100%;
    max-width: 1200px;
    height: clamp(300px, 50vh, 500px);
    background: var(--blueprint-bg);
    border: 1px solid var(--blueprint-grid);
    border-radius: 16px;
    overflow: hidden;
    position: relative;
}

.schematic-hero .schematic-overlay {
    position: absolute;
    top: 16px;
    left: 16px;
    right: 16px;
    display: flex;
    justify-content: space-between;
    pointer-events: none;
}

.schematic-hero .schematic-title {
    font-family: var(--font-display);
    font-size: 20px;
    font-weight: 600;
    color: var(--text-primary);
}

.schematic-hero .schematic-live-badge {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 4px 12px;
    background: rgba(34, 197, 94, 0.15);
    border-radius: 9999px;
    font-family: var(--font-mono);
    font-size: 11px;
    color: var(--status-active);
    pointer-events: auto;
}

.schematic-hero svg {
    width: 100%;
    height: 100%;
}
```

### 2. Compact Widget
Sidebar/panel schematic

```css
.schematic-compact {
    width: 100%;
    aspect-ratio: 16 / 10;
    background: var(--surface-dark);
    border: 1px solid var(--border-default);
    border-radius: 8px;
    padding: 8px;
    overflow: hidden;
}

.schematic-compact svg {
    width: 100%;
    height: auto;
    opacity: 0.85;
    transition: opacity 0.2s ease;
}

.schematic-compact:hover svg {
    opacity: 1;
}
```

### 3. Card Schematic
Embedded within content cards

```css
.card-schematic {
    background: var(--surface-container);
    border-radius: 8px;
    padding: 12px;
    margin-bottom: 12px;
}

.card-schematic svg {
    width: 100%;
    height: auto;
    max-height: 200px;
}
```

### 4. Modal Schematic
Full-detail overlay view

```css
.modal-schematic {
    position: fixed;
    top: 50%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 90vw;
    max-width: 1200px;
    height: 80vh;
    background: var(--blueprint-bg);
    border: 1px solid var(--blueprint-grid);
    border-radius: 16px;
    z-index: 1000;
    display: flex;
    flex-direction: column;
}

.modal-schematic-header {
    padding: 16px 24px;
    border-bottom: 1px solid var(--blueprint-grid);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.modal-schematic-content {
    flex: 1;
    overflow: auto;
    padding: 24px;
}

.modal-schematic svg {
    width: 100%;
    height: auto;
}
```

## Status Visualization

### Component Status Colors

| Status | Background | Border | Indicator |
|--------|------------|--------|-----------|
| Active | `rgba(34, 197, 94, 0.1)` | `#22C55E` | Green pulse |
| Pending | `rgba(245, 158, 11, 0.1)` | `#F59E0B` | Amber pulse |
| Error | `rgba(239, 68, 68, 0.1)` | `#EF4444` | Red pulse |
| Inactive | `rgba(107, 114, 128, 0.1)` | `#6B7280` | No animation |

### Live Status Indicator

```css
.status-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    animation: status-pulse 2s infinite;
}

.status-indicator.active { background: var(--status-active); }
.status-indicator.pending { background: var(--status-pending); }
.status-indicator.error { background: var(--status-error); }
.status-indicator.inactive { background: var(--status-inactive); animation: none; }

@keyframes status-pulse {
    0%, 100% { opacity: 1; transform: scale(1); }
    50% { opacity: 0.6; transform: scale(0.9); }
}
```

## Integration Patterns

### Pattern 1: Dashboard Hero

```html
<section class="dashboard-hero">
    <div class="schematic-hero" id="system-schematic" data-live="true">
        <div class="schematic-overlay">
            <span class="schematic-title">SLATE System Architecture</span>
            <span class="schematic-live-badge">
                <span class="status-indicator active"></span>
                Live
            </span>
        </div>
        <div class="schematic-content">
            <!-- SVG injected here -->
        </div>
    </div>
</section>
```

### Pattern 2: Sidebar Widget

```html
<aside class="sidebar">
    <div class="sidebar-section">
        <h3 class="section-title">System Overview</h3>
        <div class="schematic-compact" data-template="system">
            <!-- Compact SVG -->
        </div>
    </div>
    <div class="sidebar-section">
        <h3 class="section-title">AI Pipeline</h3>
        <div class="schematic-compact" data-template="inference">
            <!-- Compact SVG -->
        </div>
    </div>
</aside>
```

### Pattern 3: Activity Visualization

```html
<div class="activity-schematic">
    <div class="activity-header">
        <span>Data Flow</span>
        <button class="btn-icon" onclick="toggleSchematic()">
            <svg><!-- Expand icon --></svg>
        </button>
    </div>
    <div class="card-schematic" data-highlight="ollama">
        <!-- SVG with highlighted component -->
    </div>
</div>
```

## WebSocket Integration

### Live Update Protocol

```javascript
class SchematicManager {
    constructor() {
        this.ws = null;
        this.widgets = new Map();
    }

    init() {
        // Find all schematic containers
        document.querySelectorAll('[data-live="true"]').forEach(el => {
            this.widgets.set(el.id, el);
        });

        // Connect WebSocket
        this.connect();
    }

    connect() {
        this.ws = new WebSocket(`ws://${location.host}/api/schematic/ws/live`);

        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleUpdate(data);
        };

        this.ws.onclose = () => {
            setTimeout(() => this.connect(), 5000);
        };
    }

    handleUpdate(data) {
        if (data.type === 'schematic_update') {
            this.widgets.forEach((el, id) => {
                const content = el.querySelector('.schematic-content');
                if (content) {
                    content.innerHTML = data.svg;
                }
            });
        }
    }

    requestUpdate() {
        if (this.ws?.readyState === WebSocket.OPEN) {
            this.ws.send(JSON.stringify({ type: 'request_update' }));
        }
    }
}

// Initialize
const schematicManager = new SchematicManager();
document.addEventListener('DOMContentLoaded', () => schematicManager.init());
```

## Responsive Behavior

### Desktop (≥1200px)
- Hero schematic: Full width, 400-500px height
- Side panel: 280px width, compact widgets
- Grid: 4-column layout

### Tablet (768-1199px)
- Hero schematic: Full width, 300-400px height
- Side panel: Collapsible drawer
- Grid: 2-column layout

### Mobile (<768px)
- Hero schematic: Compact card, 200px height
- Side panel: Bottom sheet
- Grid: Single column

```css
@media (max-width: 1199px) {
    .schematic-hero {
        height: clamp(250px, 40vh, 400px);
    }
    .sidebar {
        position: fixed;
        right: -280px;
        transition: right 0.3s ease;
    }
    .sidebar.open {
        right: 0;
    }
}

@media (max-width: 767px) {
    .schematic-hero {
        height: 200px;
        border-radius: 8px;
    }
    .sidebar {
        bottom: 0;
        left: 0;
        right: 0;
        height: auto;
        max-height: 60vh;
        transform: translateY(100%);
    }
    .sidebar.open {
        transform: translateY(0);
    }
}
```

## Accessibility

### ARIA Labels
```html
<div class="schematic-hero"
     role="img"
     aria-label="SLATE system architecture diagram showing connected services">
    <svg aria-hidden="true"><!-- SVG content --></svg>
</div>
```

### Keyboard Navigation
- Tab through interactive components
- Enter/Space to focus on component
- Escape to close modal view

### Screen Reader Support
- SVG includes `role="img"` and `aria-label`
- Component descriptions in `title` elements
- Status changes announced via live regions

## Performance Considerations

### SVG Optimization
- Inline styles for GitHub compatibility
- Minimal path complexity
- Lazy loading for off-screen schematics

### Update Throttling
- WebSocket updates throttled to 1/second max
- Debounce user-triggered refreshes
- Virtual DOM diffing for SVG updates

### Caching Strategy
- Template SVGs cached in-memory
- Live status updates overlay on cached base
- Service worker caches static templates

## Implementation Priority

### Phase 1: Core Integration
- [x] Schematic API module (`slate/schematic_api.py`)
- [x] Layout specification (this document)
- [x] Dashboard hero widget (`slate_web/dashboard_template.py`)
- [x] WebSocket live updates (`/api/schematic/ws/live`)
- [x] Generative UI protocol integration (`slate/slate_generative_ui.py`)

### Phase 2: Widget Library
- [x] Compact sidebar widget
- [x] Card schematic component
- [x] Modal detail view
- [x] Status overlay system

### Phase 3: Interactive Features
- [x] Component hover tooltips (`schematic-tooltip`)
- [x] Click-to-focus zoom (`zoomSchematic()`, zoom controls)
- [x] Connection highlighting (`.highlighted`, `.schematic-flow-active`)
- [x] Real-time activity flow animation (`@keyframes schematic-flow`)

## Theme Lock Declaration

```
+---------------------------------------------------------------+
|              SCHEMATIC LAYOUT SPECIFICATION LOCK               |
+---------------------------------------------------------------+
|                                                               |
|  Version: 1.0.0                                               |
|  Status: LOCKED                                               |
|  Date: 2026-02-08                                             |
|                                                               |
|  The following are immutable:                                 |
|  - Hero zone dimensions (300-500px height)                    |
|  - Breakpoint definitions                                     |
|  - Status color mappings                                      |
|  - WebSocket protocol messages                                |
|                                                               |
|  Improvements must be additive, not breaking.                 |
|                                                               |
+---------------------------------------------------------------+
```
