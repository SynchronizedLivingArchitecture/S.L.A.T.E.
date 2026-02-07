# Specification: Dashboard Monochrome Theme

**Spec ID**: 005-monochrome-theme
**Status**: completed
**Created**: 2026-02-06

## Overview

Redesign the SLATE dashboard with a black and white monochrome theme, using minimal color only for critical status indicators (success/error). Add a "Workflow Pipeline" section to visualize the task execution pipeline.

## Design Principles

1. **Monochrome Base**: Near-black background (#0a0a0a) with white/gray text hierarchy
2. **Minimal Color**: Only red (#ef4444) for errors and green (#22c55e) for success
3. **Glassmorphism**: Maintain 80% opacity cards with backdrop blur
4. **Workflow Visibility**: Show GitHub Actions workflow activity in real-time
5. **Pipeline Flow**: Visualize Tasks -> Runner -> Workflows -> Results

## Color Palette

### Base Colors
| Variable | Value | Usage |
|----------|-------|-------|
| `--bg-dark` | #0a0a0a | Page background |
| `--bg-card` | rgba(18, 18, 18, 0.80) | Card backgrounds |
| `--bg-card-hover` | rgba(28, 28, 28, 0.90) | Card hover state |

### Text Hierarchy
| Variable | Value | Usage |
|----------|-------|-------|
| `--text-primary` | #ffffff | Primary content |
| `--text-secondary` | #b3b3b3 | Secondary content |
| `--text-muted` | #666666 | Muted/disabled |

### Status Colors (Minimal)
| Variable | Value | Usage |
|----------|-------|-------|
| `--status-success` | #22c55e | Success/Online |
| `--status-error` | #ef4444 | Error/Offline |
| `--status-pending` | #808080 | Pending (gray) |
| `--status-active` | #ffffff | Active/In-progress (white) |

### Pipeline Colors
| Variable | Value | Usage |
|----------|-------|-------|
| `--pipeline-task` | #808080 | Task stage |
| `--pipeline-runner` | #b3b3b3 | Runner stage |
| `--pipeline-workflow` | #ffffff | Workflow stage |
| `--pipeline-result` | #22c55e | Result stage |

## UI Components

### Workflow Pipeline Section
- Full-width card showing workflow pipeline
- Four stages: Tasks -> Runner -> Workflows -> Results
- Animated connectors between stages
- Real-time count updates

## Accessibility

- Text contrast: 16:1 (white on near-black)
- Status indicated by text labels, not just color
- Animations respect prefers-reduced-motion

## Files Modified

- `agents/slate_dashboard_server.py` - CSS and HTML updates
