#!/usr/bin/env python3
# Modified: 2026-02-07T13:00:00Z | Author: COPILOT | Change: ProArt copper/B&W menu-driven dashboard redesign
# Purpose: Generates the SLATE dashboard HTML template with ProArt-inspired design
"""
SLATE Dashboard Template Builder
=================================
Generates the complete DASHBOARD_HTML string for slate_dashboard_server.py

Design principles:
  1. ASUS ProArt Design Language: Copper accents, true black substrate, precision aesthetics
  2. Anthropic geometric art: Crystalline tessellations, network constellations
  3. Menu-driven guided UX: Assume user is NOT a systems engineer or AI expert
  4. Two control layers: Dashboard (background CLI) + SLATE Controls (local Copilot)
  5. Data-dense editorial layout with warm-white typography on true-black surfaces

The template is self-contained (inline CSS/JS, no external deps) for 127.0.0.1 serving.
"""

from pathlib import Path
from slate_web.design_system import SlateDesignTokens, SlateLogoGenerator, GeometricPatternGenerator

import base64


def _svg_to_data_uri(svg: str) -> str:
    """Convert SVG string to data URI for CSS background-image."""
    encoded = base64.b64encode(svg.encode('utf-8')).decode('ascii')
    return f"data:image/svg+xml;base64,{encoded}"


def build_template() -> str:
    """Build the complete dashboard HTML template."""

    # Generate assets inline
    logo_icon_svg = SlateLogoGenerator.generate(48, "icon")
    constellation_svg = GeometricPatternGenerator.constellation_grid(1920, 1080, 60, seed=42)
    constellation_uri = _svg_to_data_uri(constellation_svg)

    tokens = SlateDesignTokens.generate_tokens("dark")

    # Build CSS custom properties string
    token_css_lines = []
    for key, value in tokens.items():
        token_css_lines.append(f"            {key}: {value};")
    tokens_css = "\n".join(token_css_lines)

    return f'''<!DOCTYPE html>
<html lang="en" data-theme="dark">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta http-equiv="Content-Security-Policy" content="default-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self' http://127.0.0.1:* ws://127.0.0.1:*; img-src 'self' data:;">
    <title>S.L.A.T.E.</title>
    <style>
        /* ═══════════════════════════════════════════════════════════════
           SLATE Design System v4.0
           ASUS ProArt + Anthropic Geometric + Menu-Driven UX
           ═══════════════════════════════════════════════════════════════ */

        :root {{
{tokens_css}
        }}

        /* ─── Reset & Base ─────────────────────────────────────────── */
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        html {{
            scroll-behavior: smooth;
            -webkit-font-smoothing: antialiased;
            -moz-osx-font-smoothing: grayscale;
            font-size: 15px;
        }}

        body {{
            font-family: var(--sl-font-sans);
            background: var(--sl-bg-root);
            color: var(--sl-text-primary);
            min-height: 100vh;
            line-height: 1.6;
            overflow-x: hidden;
        }}

        /* ─── Geometric Background ─────────────────────────────────── */
        body::before {{
            content: '';
            position: fixed;
            inset: 0;
            background:
                url("{constellation_uri}") center/cover no-repeat,
                radial-gradient(ellipse at 20% 0%, rgba(184,115,51,0.04) 0%, transparent 50%),
                radial-gradient(ellipse at 80% 100%, rgba(184,115,51,0.03) 0%, transparent 50%);
            opacity: 0.6;
            pointer-events: none;
            z-index: 0;
        }}

        /* Scanline overlay for depth */
        body::after {{
            content: '';
            position: fixed;
            inset: 0;
            background: repeating-linear-gradient(
                0deg,
                transparent,
                transparent 2px,
                rgba(0,0,0,0.015) 2px,
                rgba(0,0,0,0.015) 4px
            );
            pointer-events: none;
            z-index: 0;
        }}

        /* ─── Layout Shell ─────────────────────────────────────────── */
        .shell {{
            position: relative;
            z-index: 1;
            max-width: 1440px;
            margin: 0 auto;
            padding: var(--sl-space-6) var(--sl-space-8);
        }}

        /* ─── Topbar ───────────────────────────────────────────────── */
        .topbar {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-4) 0;
            margin-bottom: var(--sl-space-8);
            border-bottom: 1px solid var(--sl-border);
        }}

        .topbar-brand {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-4);
        }}

        .topbar-logo {{
            width: 40px;
            height: 40px;
            flex-shrink: 0;
        }}

        .topbar-title {{
            display: flex;
            flex-direction: column;
        }}

        .topbar-title h1 {{
            font-size: var(--sl-space-5);
            font-weight: 700;
            letter-spacing: 0.12em;
            color: var(--sl-text-primary);
            line-height: 1.1;
        }}

        .topbar-title .subtitle {{
            font-size: 0.65rem;
            color: var(--sl-text-tertiary);
            letter-spacing: 0.2em;
            text-transform: uppercase;
        }}

        .topbar-actions {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-3);
        }}

        .topbar-status {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
            padding: var(--sl-space-1) var(--sl-space-3);
            background: var(--sl-bg-container);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-full);
            font-size: 0.7rem;
            color: var(--sl-text-secondary);
        }}

        .pulse-dot {{
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--sl-success);
            box-shadow: 0 0 8px var(--sl-success);
            animation: pulse 2s ease-in-out infinite;
        }}

        .pulse-dot.offline {{ background: var(--sl-error); box-shadow: 0 0 8px var(--sl-error); animation: none; }}
        .pulse-dot.warning {{ background: var(--sl-warning); box-shadow: 0 0 8px var(--sl-warning); }}

        @keyframes pulse {{
            0%, 100% {{ opacity: 1; }}
            50% {{ opacity: 0.4; }}
        }}

        /* ─── Grid System ──────────────────────────────────────────── */
        .grid {{
            display: grid;
            grid-template-columns: repeat(12, 1fr);
            gap: var(--sl-space-4);
        }}

        .col-12 {{ grid-column: span 12; }}
        .col-8 {{ grid-column: span 8; }}
        .col-6 {{ grid-column: span 6; }}
        .col-4 {{ grid-column: span 4; }}
        .col-3 {{ grid-column: span 3; }}

        @media (max-width: 1024px) {{
            .col-8, .col-6 {{ grid-column: span 12; }}
            .col-4, .col-3 {{ grid-column: span 6; }}
        }}
        @media (max-width: 640px) {{
            .col-4, .col-3 {{ grid-column: span 12; }}
        }}

        /* ─── Cards (M3 Surface + Glassmorphism) ───────────────────── */
        .card {{
            background: var(--sl-glass-bg);
            backdrop-filter: blur(var(--sl-glass-blur)) saturate(var(--sl-glass-saturate));
            -webkit-backdrop-filter: blur(var(--sl-glass-blur)) saturate(var(--sl-glass-saturate));
            border: 1px solid var(--sl-glass-border);
            border-radius: var(--sl-radius-lg);
            padding: var(--sl-space-5);
            transition: border-color var(--sl-duration-medium) var(--sl-ease-standard),
                        box-shadow var(--sl-duration-medium) var(--sl-ease-standard);
        }}

        .card:hover {{
            border-color: var(--sl-border-variant);
            box-shadow: var(--sl-elevation-2);
        }}

        .card-header {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            margin-bottom: var(--sl-space-4);
        }}

        .card-title {{
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--sl-text-tertiary);
        }}

        .card-action {{
            background: none;
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-sm);
            padding: var(--sl-space-1) var(--sl-space-3);
            color: var(--sl-text-tertiary);
            font-size: 0.65rem;
            cursor: pointer;
            transition: all var(--sl-duration-short) var(--sl-ease-standard);
            font-family: inherit;
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        .card-action:hover {{
            color: var(--sl-accent);
            border-color: var(--sl-accent-dim);
        }}

        /* ─── Buttons (M3-inspired) ────────────────────────────────── */
        .btn {{
            display: inline-flex;
            align-items: center;
            justify-content: center;
            gap: var(--sl-space-2);
            padding: var(--sl-space-2) var(--sl-space-4);
            border-radius: var(--sl-radius-sm);
            font-family: inherit;
            font-size: 0.75rem;
            font-weight: 500;
            cursor: pointer;
            border: none;
            transition: all var(--sl-duration-short) var(--sl-ease-standard);
            text-transform: uppercase;
            letter-spacing: 0.06em;
        }}

        .btn-filled {{
            background: var(--sl-accent);
            color: var(--sl-text-on-accent);
        }}
        .btn-filled:hover {{
            box-shadow: var(--sl-elevation-2);
            filter: brightness(0.9);
        }}

        .btn-tonal {{
            background: var(--sl-accent-container);
            color: var(--sl-accent-on-container);
            border: 1px solid var(--sl-accent-dim);
        }}
        .btn-tonal:hover {{
            background: rgba(184,115,51,0.18);
        }}

        .btn-outline {{
            background: transparent;
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
        }}
        .btn-outline:hover {{
            border-color: var(--sl-accent-dim);
            color: var(--sl-accent);
            background: rgba(184,115,51,0.06);
        }}

        .btn-ghost {{
            background: transparent;
            border: none;
            color: var(--sl-text-tertiary);
        }}
        .btn-ghost:hover {{
            color: var(--sl-text-primary);
            background: rgba(255,255,255,0.03);
        }}

        /* ─── SLATE Control Panel ──────────────────────────────────── */
        .ctrl-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--sl-space-3);
        }}
        @media (max-width: 900px) {{ .ctrl-grid {{ grid-template-columns: repeat(2, 1fr); }} }}
        @media (max-width: 540px) {{ .ctrl-grid {{ grid-template-columns: 1fr; }} }}

        .ctrl-btn {{
            position: relative;
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--sl-space-2);
            padding: var(--sl-space-5) var(--sl-space-3);
            border-radius: var(--sl-radius-md);
            background: var(--sl-bg-container);
            border: 1px solid var(--sl-border);
            color: var(--sl-text-secondary);
            cursor: pointer;
            transition: all var(--sl-duration-medium) var(--sl-ease-emphasized);
            font-family: inherit;
            font-size: 0.7rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            overflow: hidden;
        }}

        .ctrl-btn::before {{
            content: '';
            position: absolute;
            inset: 0;
            background: linear-gradient(135deg, rgba(184,115,51,0.05) 0%, transparent 60%);
            opacity: 0;
            transition: opacity var(--sl-duration-medium);
        }}

        .ctrl-btn:hover {{
            border-color: var(--sl-accent-dim);
            background: var(--sl-bg-container-high);
            transform: translateY(-2px);
            box-shadow: var(--sl-elevation-3);
        }}
        .ctrl-btn:hover::before {{ opacity: 1; }}
        .ctrl-btn:active {{ transform: translateY(0); }}

        .ctrl-btn.running {{
            border-color: var(--sl-accent);
            pointer-events: none;
        }}
        .ctrl-btn.running .ctrl-icon {{
            animation: spin 1.2s linear infinite;
        }}
        .ctrl-btn.ok {{ border-color: var(--sl-success); }}
        .ctrl-btn.err {{ border-color: var(--sl-error); }}

        @keyframes spin {{ to {{ transform: rotate(360deg); }} }}

        .ctrl-icon {{
            font-size: 1.5rem;
            line-height: 1;
            position: relative;
            z-index: 1;
        }}

        .ctrl-label {{ position: relative; z-index: 1; }}

        .ctrl-dot {{
            position: absolute;
            top: var(--sl-space-2);
            right: var(--sl-space-2);
            width: 6px;
            height: 6px;
            border-radius: 50%;
            background: var(--sl-text-disabled);
        }}
        .ctrl-dot.ok {{ background: var(--sl-success); box-shadow: 0 0 6px var(--sl-success); }}
        .ctrl-dot.err {{ background: var(--sl-error); box-shadow: 0 0 6px var(--sl-error); }}
        .ctrl-dot.warn {{ background: var(--sl-warning); box-shadow: 0 0 6px var(--sl-warning); }}

        /* Control output terminal */
        .ctrl-term {{
            display: none;
            margin-top: var(--sl-space-4);
            padding: var(--sl-space-4);
            background: rgba(0,0,0,0.5);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-sm);
            font-family: var(--sl-font-mono);
            font-size: 0.7rem;
            line-height: 1.7;
            color: var(--sl-text-tertiary);
            max-height: 280px;
            overflow-y: auto;
            white-space: pre-wrap;
            word-break: break-word;
        }}
        .ctrl-term.open {{ display: block; animation: fadeIn 0.2s ease; }}
        .ctrl-term .ok {{ color: var(--sl-success); }}
        .ctrl-term .err {{ color: var(--sl-error); }}
        .ctrl-term .lbl {{ color: var(--sl-text-secondary); font-weight: 600; }}

        /* CI dispatch row */
        .ci-row {{
            display: flex;
            gap: var(--sl-space-2);
            flex-wrap: wrap;
            margin-top: var(--sl-space-4);
            padding-top: var(--sl-space-4);
            border-top: 1px solid var(--sl-border);
        }}
        .ci-row .btn {{ flex: 1; min-width: 100px; font-size: 0.65rem; }}

        @keyframes fadeIn {{
            from {{ opacity: 0; transform: translateY(4px); }}
            to {{ opacity: 1; transform: translateY(0); }}
        }}

        /* ─── Pipeline Visualization ───────────────────────────────── */
        .pipeline {{
            display: flex;
            align-items: center;
            justify-content: center;
            gap: 0;
            padding: var(--sl-space-4) 0;
        }}

        .pipe-node {{
            display: flex;
            flex-direction: column;
            align-items: center;
            gap: var(--sl-space-1);
        }}

        .pipe-icon {{
            width: 44px;
            height: 44px;
            border-radius: var(--sl-radius-md);
            display: flex;
            align-items: center;
            justify-content: center;
            font-weight: 700;
            font-size: 0.85rem;
            border: 1px solid var(--sl-border);
            background: var(--sl-bg-container);
            color: var(--sl-text-secondary);
            transition: all var(--sl-duration-medium) var(--sl-ease-standard);
        }}

        .pipe-icon.active {{
            border-color: var(--sl-accent);
            color: var(--sl-accent);
            box-shadow: 0 0 16px var(--sl-accent-glow);
        }}

        .pipe-label {{
            font-size: 0.6rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        .pipe-value {{
            font-size: 0.65rem;
            color: var(--sl-text-tertiary);
            font-family: var(--sl-font-mono);
        }}

        .pipe-connector {{
            width: 48px;
            height: 1px;
            background: var(--sl-border);
            margin: 0 var(--sl-space-1);
            margin-bottom: 28px;
        }}
        .pipe-connector.active {{
            background: var(--sl-accent-dim);
            box-shadow: 0 0 4px var(--sl-accent-glow);
        }}

        /* ─── Metrics & Progress Bars ──────────────────────────────── */
        .metric {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-2) 0;
        }}
        .metric + .metric {{ border-top: 1px solid rgba(255,255,255,0.03); }}

        .metric-label {{
            font-size: 0.7rem;
            color: var(--sl-text-tertiary);
        }}

        .metric-bar {{
            flex: 1;
            margin: 0 var(--sl-space-3);
            height: 4px;
            background: var(--sl-bg-container-highest);
            border-radius: var(--sl-radius-full);
            overflow: hidden;
        }}

        .metric-fill {{
            height: 100%;
            background: var(--sl-accent);
            border-radius: var(--sl-radius-full);
            transition: width var(--sl-duration-long) var(--sl-ease-decelerate);
        }}

        .metric-value {{
            font-size: 0.7rem;
            font-family: var(--sl-font-mono);
            color: var(--sl-text-secondary);
            min-width: 36px;
            text-align: right;
        }}

        /* ─── Status Badges ────────────────────────────────────────── */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 2px 8px;
            border-radius: var(--sl-radius-full);
            font-size: 0.6rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.08em;
        }}

        .badge.online {{ background: var(--sl-success-container); color: var(--sl-success); }}
        .badge.offline {{ background: var(--sl-error-container); color: var(--sl-error); }}
        .badge.pending {{ background: rgba(255,255,255,0.05); color: var(--sl-text-disabled); }}
        .badge.warning {{ background: var(--sl-warning-container); color: var(--sl-warning); }}

        /* ─── Service List ─────────────────────────────────────────── */
        .svc-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-2) var(--sl-space-3);
            border-radius: var(--sl-radius-sm);
            transition: background var(--sl-duration-short);
        }}
        .svc-item:hover {{ background: rgba(255,255,255,0.02); }}
        .svc-item + .svc-item {{ border-top: 1px solid rgba(255,255,255,0.03); }}

        .svc-name {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
            font-size: 0.75rem;
            color: var(--sl-text-secondary);
        }}

        .svc-icon {{
            width: 28px;
            height: 28px;
            border-radius: var(--sl-radius-sm);
            background: var(--sl-bg-container-high);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 700;
            color: var(--sl-text-tertiary);
        }}

        /* ─── Task List ────────────────────────────────────────────── */
        .task-form {{
            display: flex;
            gap: var(--sl-space-2);
            margin-bottom: var(--sl-space-3);
        }}

        .task-input {{
            flex: 1;
            padding: var(--sl-space-2) var(--sl-space-3);
            background: var(--sl-bg-container);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-sm);
            color: var(--sl-text-primary);
            font-family: inherit;
            font-size: 0.75rem;
            outline: none;
            transition: border-color var(--sl-duration-short);
        }}
        .task-input:focus {{ border-color: var(--sl-accent); }}
        .task-input::placeholder {{ color: var(--sl-text-disabled); }}

        .task-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-2) var(--sl-space-3);
            border-radius: var(--sl-radius-sm);
            font-size: 0.75rem;
            color: var(--sl-text-secondary);
        }}
        .task-item + .task-item {{ border-top: 1px solid rgba(255,255,255,0.03); }}

        /* ─── Workflow List ─────────────────────────────────────────── */
        .wf-item {{
            display: flex;
            align-items: center;
            justify-content: space-between;
            padding: var(--sl-space-2) 0;
            font-size: 0.7rem;
        }}
        .wf-item + .wf-item {{ border-top: 1px solid rgba(255,255,255,0.03); }}

        .wf-name {{
            color: var(--sl-text-secondary);
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
        }}

        .wf-meta {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-3);
            color: var(--sl-text-disabled);
            font-family: var(--sl-font-mono);
            font-size: 0.6rem;
        }}

        /* ─── Heatmap ──────────────────────────────────────────────── */
        .heatmap-grid {{
            display: grid;
            grid-template-columns: repeat(52, 1fr);
            gap: 3px;
        }}
        .heatmap-week {{ display: flex; flex-direction: column; gap: 3px; }}
        .heatmap-day {{
            width: 10px; height: 10px;
            border-radius: 2px;
            background: rgba(255,255,255,0.04);
            transition: transform 0.15s;
        }}
        .heatmap-day:hover {{ transform: scale(1.4); }}
        .heatmap-day[data-level="1"] {{ background: rgba(184,115,51,0.2); }}
        .heatmap-day[data-level="2"] {{ background: rgba(184,115,51,0.4); }}
        .heatmap-day[data-level="3"] {{ background: rgba(184,115,51,0.6); }}
        .heatmap-day[data-level="4"] {{ background: rgba(184,115,51,0.85); }}

        /* ─── GitHub Sections ──────────────────────────────────────── */
        .gh-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: var(--sl-space-4);
        }}
        @media (max-width: 900px) {{ .gh-grid {{ grid-template-columns: repeat(2, 1fr); }} }}

        .gh-section-title {{
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.12em;
            color: var(--sl-text-disabled);
            margin-bottom: var(--sl-space-3);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }}

        .gh-section-title .count {{
            background: var(--sl-bg-container-high);
            padding: 1px 6px;
            border-radius: var(--sl-radius-full);
            font-family: var(--sl-font-mono);
            font-size: 0.6rem;
        }}

        .gh-item {{
            padding: var(--sl-space-2) 0;
            font-size: 0.7rem;
            color: var(--sl-text-tertiary);
            border-bottom: 1px solid rgba(255,255,255,0.02);
        }}

        /* ─── Hardware Meters ──────────────────────────────────────── */
        .hw-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: var(--sl-space-4); }}
        @media (max-width: 640px) {{ .hw-grid {{ grid-template-columns: 1fr; }} }}

        .hw-panel {{
            padding: var(--sl-space-4);
            background: var(--sl-bg-container);
            border-radius: var(--sl-radius-md);
            border: 1px solid rgba(255,255,255,0.03);
        }}

        .hw-title {{
            font-size: 0.65rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.1em;
            color: var(--sl-text-disabled);
            margin-bottom: var(--sl-space-3);
        }}

        .hw-stat {{
            text-align: center;
            padding: var(--sl-space-3);
        }}
        .hw-stat-value {{
            font-size: 1.8rem;
            font-weight: 700;
            font-family: var(--sl-font-mono);
            color: var(--sl-accent);
        }}
        .hw-stat-label {{
            font-size: 0.6rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
            margin-top: 2px;
        }}

        /* ─── Onboarding Overlay ───────────────────────────────────── */
        .onboard-overlay {{
            position: fixed;
            inset: 0;
            background: rgba(0,0,0,0.85);
            backdrop-filter: blur(12px);
            z-index: 1000;
            display: none;
            align-items: center;
            justify-content: center;
        }}
        .onboard-overlay.active {{ display: flex; }}

        .onboard-card {{
            max-width: 560px;
            width: 90%;
            background: var(--sl-bg-surface);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-xl);
            padding: var(--sl-space-10);
            text-align: center;
            animation: fadeIn 0.4s ease;
        }}

        .onboard-card h2 {{
            font-size: 1.5rem;
            font-weight: 700;
            color: var(--sl-text-primary);
            margin-bottom: var(--sl-space-2);
        }}

        .onboard-card p {{
            color: var(--sl-text-tertiary);
            font-size: 0.85rem;
            margin-bottom: var(--sl-space-6);
            line-height: 1.7;
        }}

        .onboard-steps {{
            display: flex;
            flex-direction: column;
            gap: var(--sl-space-3);
            text-align: left;
            margin-bottom: var(--sl-space-6);
        }}

        .onboard-step {{
            display: flex;
            align-items: flex-start;
            gap: var(--sl-space-3);
            padding: var(--sl-space-3);
            border-radius: var(--sl-radius-sm);
            background: var(--sl-bg-container);
        }}

        .onboard-step-num {{
            width: 24px;
            height: 24px;
            border-radius: 50%;
            background: var(--sl-accent-container);
            color: var(--sl-accent);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 0.7rem;
            font-weight: 700;
            flex-shrink: 0;
        }}

        .onboard-step-text {{
            font-size: 0.8rem;
            color: var(--sl-text-secondary);
            line-height: 1.5;
        }}

        .onboard-step-text strong {{
            color: var(--sl-accent);
        }}

        /* ─── Empty State ──────────────────────────────────────────── */
        .empty {{
            text-align: center;
            padding: var(--sl-space-8) var(--sl-space-4);
            color: var(--sl-text-disabled);
            font-size: 0.75rem;
        }}

        /* ─── Connection Status ────────────────────────────────────── */
        #conn-status {{
            position: fixed;
            bottom: var(--sl-space-4);
            right: var(--sl-space-4);
            padding: var(--sl-space-1) var(--sl-space-3);
            background: var(--sl-bg-container);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-full);
            font-size: 0.6rem;
            color: var(--sl-text-disabled);
            z-index: 100;
            display: flex;
            align-items: center;
            gap: var(--sl-space-1);
        }}

        /* ─── Activity Feed ────────────────────────────────────────── */
        .feed-item {{
            display: flex;
            align-items: flex-start;
            gap: var(--sl-space-3);
            padding: var(--sl-space-2) 0;
        }}
        .feed-item + .feed-item {{ border-top: 1px solid rgba(255,255,255,0.02); }}

        .feed-dot {{
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--sl-accent-dim);
            margin-top: 5px;
            flex-shrink: 0;
        }}

        .feed-text {{
            font-size: 0.7rem;
            color: var(--sl-text-tertiary);
            line-height: 1.5;
        }}

        .feed-time {{
            font-size: 0.6rem;
            color: var(--sl-text-disabled);
            font-family: var(--sl-font-mono);
        }}

        /* ─── Scrollbar ────────────────────────────────────────────── */
        ::-webkit-scrollbar {{ width: 5px; height: 5px; }}
        ::-webkit-scrollbar-track {{ background: transparent; }}
        ::-webkit-scrollbar-thumb {{ background: rgba(255,255,255,0.08); border-radius: 4px; }}
        ::-webkit-scrollbar-thumb:hover {{ background: rgba(255,255,255,0.15); }}

        /* ─── Skip Link ────────────────────────────────────────────── */
        .skip-link {{
            position: absolute; left: -9999px; top: -9999px;
            padding: var(--sl-space-2) var(--sl-space-4);
            background: var(--sl-accent); color: #000;
            z-index: 9999; font-weight: 600;
        }}
        .skip-link:focus {{ left: 0; top: 0; }}

        /* ─── Nav Sidebar (Menu-Driven) ────────────────────────────── */
        .dashboard-layout {{
            display: flex;
            min-height: 100vh;
        }}

        .nav-sidebar {{
            width: 220px;
            min-height: 100vh;
            background: #060606;
            border-right: 1px solid rgba(255,255,255,0.06);
            position: fixed;
            left: 0;
            top: 0;
            z-index: 50;
            display: flex;
            flex-direction: column;
            padding: var(--sl-space-5) 0;
            overflow-y: auto;
        }}

        .nav-brand {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-3);
            padding: 0 var(--sl-space-5);
            margin-bottom: var(--sl-space-6);
        }}

        .nav-brand-text {{
            display: flex;
            flex-direction: column;
        }}

        .nav-brand-name {{
            font-size: 0.9rem;
            font-weight: 700;
            letter-spacing: 0.1em;
            color: var(--sl-text-primary);
        }}

        .nav-brand-sub {{
            font-size: 0.55rem;
            color: var(--sl-text-disabled);
            letter-spacing: 0.15em;
            text-transform: uppercase;
        }}

        .nav-section {{
            padding: 0;
            margin-bottom: var(--sl-space-2);
        }}

        .nav-section-label {{
            font-size: 0.55rem;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.15em;
            color: var(--sl-text-disabled);
            padding: var(--sl-space-2) var(--sl-space-5);
        }}

        .nav-item {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-3);
            padding: var(--sl-space-2) var(--sl-space-5);
            color: var(--sl-text-tertiary);
            cursor: pointer;
            font-size: 0.75rem;
            font-weight: 500;
            transition: all 0.15s ease;
            border-left: 2px solid transparent;
            text-decoration: none;
            background: none;
            border-top: none;
            border-bottom: none;
            border-right: none;
            width: 100%;
            font-family: inherit;
        }}

        .nav-item:hover {{
            color: var(--sl-text-secondary);
            background: rgba(255,255,255,0.02);
        }}

        .nav-item.active {{
            color: var(--sl-accent);
            border-left-color: var(--sl-accent);
            background: rgba(184,115,51,0.06);
        }}

        .nav-item-icon {{
            width: 18px;
            text-align: center;
            font-size: 0.85rem;
        }}

        .nav-item-badge {{
            margin-left: auto;
            background: var(--sl-accent-container);
            color: var(--sl-accent);
            padding: 1px 6px;
            border-radius: var(--sl-radius-full);
            font-size: 0.55rem;
            font-weight: 700;
            font-family: var(--sl-font-mono);
        }}

        .nav-footer {{
            margin-top: auto;
            padding: var(--sl-space-4) var(--sl-space-5);
            border-top: 1px solid rgba(255,255,255,0.04);
        }}

        .nav-footer-status {{
            display: flex;
            align-items: center;
            gap: var(--sl-space-2);
            font-size: 0.6rem;
            color: var(--sl-text-disabled);
        }}

        /* Main content area offset for sidebar */
        .main-content {{
            margin-left: 220px;
            flex: 1;
            min-height: 100vh;
        }}

        /* Dashboard sections (show/hide by nav) */
        .dash-section {{
            display: none;
        }}
        .dash-section.active {{
            display: block;
            animation: fadeIn 0.25s ease;
        }}

        @media (max-width: 900px) {{
            .nav-sidebar {{ width: 56px; overflow: hidden; }}
            .nav-sidebar .nav-brand-text,
            .nav-sidebar .nav-section-label,
            .nav-sidebar .nav-item span:not(.nav-item-icon),
            .nav-sidebar .nav-item-badge,
            .nav-sidebar .nav-footer-status span {{ display: none; }}
            .nav-item {{ padding: var(--sl-space-2) var(--sl-space-3); justify-content: center; }}
            .main-content {{ margin-left: 56px; }}
        }}

        /* ─── Docker Containers ────────────────────────────────────── */
        .docker-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
            gap: var(--sl-space-3);
        }}

        /* ─── Tech Tree ────────────────────────────────────────────── */
        .tech-tree-stats {{
            display: flex;
            gap: var(--sl-space-4);
            flex-wrap: wrap;
        }}
        .tt-stat {{
            text-align: center;
            padding: var(--sl-space-2) var(--sl-space-4);
            background: var(--sl-bg-container);
            border-radius: var(--sl-radius-sm);
            border: 1px solid rgba(255,255,255,0.03);
        }}
        .tt-stat-val {{
            font-size: 1.2rem;
            font-weight: 700;
            font-family: var(--sl-font-mono);
            color: var(--sl-accent);
        }}
        .tt-stat-lbl {{
            font-size: 0.55rem;
            color: var(--sl-text-disabled);
            text-transform: uppercase;
            letter-spacing: 0.1em;
        }}

        /* ─── Select Dropdown ──────────────────────────────────────── */
        select {{
            padding: var(--sl-space-2) var(--sl-space-3);
            background: var(--sl-bg-container);
            border: 1px solid var(--sl-border);
            border-radius: var(--sl-radius-sm);
            color: var(--sl-text-primary);
            font-family: inherit;
            font-size: 0.75rem;
            outline: none;
        }}
        select:focus {{ border-color: var(--sl-accent); }}

    </style>
</head>
<body>
    <a class="skip-link" href="#main">Skip to main content</a>

    <!-- Onboarding Overlay -->
    <div class="onboard-overlay" id="onboard">
        <div class="onboard-card">
            <div style="margin-bottom: 20px;">{logo_icon_svg}</div>
            <h2>Welcome to S.L.A.T.E.</h2>
            <p>Synchronized Living Architecture for Transformation and Evolution.<br>
            Your local AI orchestration system is ready to get started.</p>
            <div class="onboard-steps">
                <div class="onboard-step">
                    <div class="onboard-step-num">1</div>
                    <div class="onboard-step-text"><strong>Quick Health Check</strong> &mdash; Click "Run SLATE" in the Controls panel to verify your system is working. This checks all 7 components automatically.</div>
                </div>
                <div class="onboard-step">
                    <div class="onboard-step-num">2</div>
                    <div class="onboard-step-text"><strong>Navigate with the Sidebar</strong> &mdash; Use the left-hand menu to explore different areas: Controls, Hardware, Workflows, and more.</div>
                </div>
                <div class="onboard-step">
                    <div class="onboard-step-num">3</div>
                    <div class="onboard-step-text"><strong>Ask @slate in VS Code</strong> &mdash; Open VS Code Chat (Ctrl+L) and type <strong>@slate</strong> to interact with the system using natural language.</div>
                </div>
                <div class="onboard-step">
                    <div class="onboard-step-num">4</div>
                    <div class="onboard-step-text"><strong>Apply the Theme</strong> &mdash; Press Ctrl+K then Ctrl+T and search for "SLATE Dark" to match your editor to the dashboard design.</div>
                </div>
            </div>
            <button class="btn btn-filled" onclick="dismissOnboard()">Get Started</button>
        </div>
    </div>

    <div class="dashboard-layout">
        <!-- ═══ Sidebar Navigation ═══ -->
        <nav class="nav-sidebar" role="navigation" aria-label="Main navigation">
            <div class="nav-brand">
                <div style="width:28px;height:28px;flex-shrink:0;">{logo_icon_svg}</div>
                <div class="nav-brand-text">
                    <span class="nav-brand-name">S.L.A.T.E.</span>
                    <span class="nav-brand-sub">Architecture</span>
                </div>
            </div>

            <div class="nav-section">
                <div class="nav-section-label">Operate</div>
                <button class="nav-item active" onclick="showSection('overview', this)">
                    <span class="nav-item-icon">&#9670;</span><span>Overview</span>
                </button>
                <button class="nav-item" onclick="showSection('controls', this)">
                    <span class="nav-item-icon">&#9881;</span><span>Controls</span>
                </button>
                <button class="nav-item" onclick="showSection('hardware', this)">
                    <span class="nav-item-icon">&#9889;</span><span>Hardware</span>
                </button>
            </div>

            <div class="nav-section">
                <div class="nav-section-label">Build</div>
                <button class="nav-item" onclick="showSection('workflows', this)">
                    <span class="nav-item-icon">&#8635;</span><span>Workflows</span>
                    <span class="nav-item-badge" id="nav-wf-count">0</span>
                </button>
                <button class="nav-item" onclick="showSection('tasks', this)">
                    <span class="nav-item-icon">&#9744;</span><span>Tasks</span>
                    <span class="nav-item-badge" id="nav-task-count">0</span>
                </button>
                <button class="nav-item" onclick="showSection('github', this)">
                    <span class="nav-item-icon">&#128279;</span><span>GitHub</span>
                </button>
            </div>

            <div class="nav-section">
                <div class="nav-section-label">Intelligence</div>
                <button class="nav-item" onclick="showSection('agents', this)">
                    <span class="nav-item-icon">&#129302;</span><span>Agents</span>
                </button>
                <button class="nav-item" onclick="showSection('activity', this)">
                    <span class="nav-item-icon">&#128200;</span><span>Activity</span>
                </button>
            </div>

            <div class="nav-footer">
                <div class="nav-footer-status">
                    <span class="pulse-dot" id="runner-dot"></span>
                    <span id="runner-status-text">Connecting...</span>
                </div>
            </div>
        </nav>

        <!-- ═══ Main Content ═══ -->
        <div class="main-content">
            <div class="shell">
                <!-- Topbar -->
                <header class="topbar" role="banner">
                    <div class="topbar-brand">
                        <div class="topbar-title">
                            <h1 id="section-title">Overview</h1>
                            <span class="subtitle" id="section-subtitle">System status and quick actions</span>
                        </div>
                    </div>
                    <div class="topbar-actions">
                        <div class="topbar-status">
                            <span class="pulse-dot" id="topbar-dot"></span>
                            <span id="topbar-status-text">v2.4.0</span>
                        </div>
                        <button class="btn btn-outline" onclick="refreshAll()">Refresh</button>
                    </div>
                </header>

                <main id="main" role="main">

                <!-- ═══ SECTION: Overview ═══ -->
                <div class="dash-section active" id="sec-overview">
                <div class="grid">
                    <!-- Quick Actions -->
                    <div class="card col-12" role="region" aria-label="Quick Actions">
                        <div class="card-header">
                            <span class="card-title">Quick Actions</span>
                            <span style="font-size:0.6rem;color:var(--sl-text-disabled);">Common operations</span>
                        </div>
                        <div class="ctrl-grid" style="grid-template-columns: repeat(4, 1fr);">
                            <button class="ctrl-btn" onclick="slateCtrl('run-protocol', this)">
                                <span class="ctrl-dot" id="dot-protocol"></span>
                                <span class="ctrl-icon">&#9881;</span>
                                <span class="ctrl-label">Health Check</span>
                            </button>
                            <button class="ctrl-btn" onclick="slateCtrl('debug', this)">
                                <span class="ctrl-dot" id="dot-debug"></span>
                                <span class="ctrl-icon">&#128269;</span>
                                <span class="ctrl-label">Diagnostics</span>
                            </button>
                            <button class="ctrl-btn" onclick="slateDeploy('start', this)">
                                <span class="ctrl-dot" id="dot-deploy"></span>
                                <span class="ctrl-icon">&#9654;</span>
                                <span class="ctrl-label">Start Services</span>
                            </button>
                            <button class="ctrl-btn" onclick="dispatchWorkflow('ci.yml')">
                                <span class="ctrl-icon">&#9654;</span>
                                <span class="ctrl-label">Run CI</span>
                            </button>
                        </div>
                    </div>

                    <!-- System Health -->
                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">System Health</span>
                            <button class="card-action" onclick="refreshSystemHealth()">Refresh</button>
                        </div>
                        <div>
                            <div class="hw-title">Resources</div>
                            <div class="metric">
                                <span class="metric-label">CPU</span>
                                <div class="metric-bar"><div class="metric-fill" id="cpu-bar" style="width:0%"></div></div>
                                <span class="metric-value" id="cpu-value">--%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Memory</span>
                                <div class="metric-bar"><div class="metric-fill" id="memory-bar" style="width:0%"></div></div>
                                <span class="metric-value" id="memory-value">--%</span>
                            </div>
                            <div class="metric">
                                <span class="metric-label">Disk</span>
                                <div class="metric-bar"><div class="metric-fill" id="disk-bar" style="width:0%"></div></div>
                                <span class="metric-value" id="disk-value">--%</span>
                            </div>
                        </div>
                        <div style="margin-top: var(--sl-space-4);">
                            <div class="hw-title">GPU</div>
                            <div id="gpu-utilization"><div class="empty">Loading GPU...</div></div>
                        </div>
                    </div>

                    <!-- Services -->
                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Services</span>
                            <button class="card-action" onclick="refreshServices()">Refresh</button>
                        </div>
                        <div id="services-list">
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">D</div><span>Dashboard</span></div><span class="badge online">Online</span></div>
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">O</div><span>Orchestrator</span></div><span class="badge pending" id="orch-badge">Checking</span></div>
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">R</div><span>Runner</span></div><span class="badge pending" id="runner-badge">Checking</span></div>
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">A</div><span>Ollama</span></div><span class="badge pending" id="ollama-badge">Checking</span></div>
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">F</div><span>Foundry</span></div><span class="badge pending" id="foundry-badge">Checking</span></div>
                            <div class="svc-item"><div class="svc-name"><div class="svc-icon">&#128051;</div><span>Docker</span></div><span class="badge pending" id="docker-badge">Checking</span></div>
                        </div>
                    </div>

                    <!-- Pipeline -->
                    <div class="card col-12" role="region" aria-label="Pipeline">
                        <div class="card-header">
                            <span class="card-title">Workflow Pipeline</span>
                            <button class="card-action" onclick="refreshWorkflowPipeline()">Refresh</button>
                        </div>
                        <div class="pipeline" id="flow-pipeline">
                            <div class="pipe-node">
                                <div class="pipe-icon" id="flow-task">T</div>
                                <div class="pipe-label">Tasks</div>
                                <div class="pipe-value" id="flow-task-count">0</div>
                            </div>
                            <div class="pipe-connector" id="flow-conn-1"></div>
                            <div class="pipe-node">
                                <div class="pipe-icon" id="flow-runner">R</div>
                                <div class="pipe-label">Runner</div>
                                <div class="pipe-value" id="flow-runner-status">Idle</div>
                            </div>
                            <div class="pipe-connector" id="flow-conn-2"></div>
                            <div class="pipe-node">
                                <div class="pipe-icon" id="flow-workflow">W</div>
                                <div class="pipe-label">Workflows</div>
                                <div class="pipe-value" id="flow-workflow-count">0</div>
                            </div>
                            <div class="pipe-connector" id="flow-conn-3"></div>
                            <div class="pipe-node">
                                <div class="pipe-icon" id="flow-pr">PR</div>
                                <div class="pipe-label">Results</div>
                                <div class="pipe-value" id="flow-pr-count">0</div>
                            </div>
                        </div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Controls ═══ -->
                <div class="dash-section" id="sec-controls">
                <div class="grid">
                    <div class="card col-12" role="region" aria-label="SLATE Controls">
                        <div class="card-header">
                            <span class="card-title">System Controls</span>
                            <div style="display:flex;gap:var(--sl-space-2);align-items:center;">
                                <button class="card-action" onclick="loadAiRecommend()">AI Suggest</button>
                                <button class="card-action" onclick="toggleTerm()">Output</button>
                            </div>
                        </div>
                        <div id="ai-rec" style="display:none;padding:var(--sl-space-3);margin-bottom:var(--sl-space-3);background:var(--sl-accent-container);border:1px solid var(--sl-accent-dim);border-radius:var(--sl-radius-sm);font-size:0.75rem;color:var(--sl-accent-on-container);line-height:1.6;">
                            <span style="font-weight:700;margin-right:var(--sl-space-2);">&#9672; AI:</span>
                            <span id="ai-rec-text">Analyzing system state...</span>
                        </div>
                        <div class="ctrl-grid">
                            <button class="ctrl-btn" id="ctrl-protocol" onclick="slateCtrl('run-protocol', this)">
                                <span class="ctrl-dot" id="dot-protocol2"></span>
                                <span class="ctrl-icon">&#9881;</span>
                                <span class="ctrl-label">Run SLATE</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-update" onclick="slateCtrl('update', this)">
                                <span class="ctrl-dot" id="dot-update"></span>
                                <span class="ctrl-icon">&#8635;</span>
                                <span class="ctrl-label">Update</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-debug" onclick="slateCtrl('debug', this)">
                                <span class="ctrl-dot" id="dot-debug2"></span>
                                <span class="ctrl-icon">&#128269;</span>
                                <span class="ctrl-label">Debug</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-benchmark" onclick="slateCtrl('benchmark', this)">
                                <span class="ctrl-dot" id="dot-benchmark"></span>
                                <span class="ctrl-icon">&#9889;</span>
                                <span class="ctrl-label">Benchmark</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-deploy" onclick="slateDeploy('start', this)">
                                <span class="ctrl-dot" id="dot-deploy2"></span>
                                <span class="ctrl-icon">&#9654;</span>
                                <span class="ctrl-label">Deploy</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-security" onclick="slateCtrl('security', this)">
                                <span class="ctrl-dot" id="dot-security"></span>
                                <span class="ctrl-icon">&#128274;</span>
                                <span class="ctrl-label">Security</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-agents" onclick="slateCtrl('agents', this)">
                                <span class="ctrl-dot" id="dot-agents"></span>
                                <span class="ctrl-icon">&#129302;</span>
                                <span class="ctrl-label">Agents</span>
                            </button>
                            <button class="ctrl-btn" id="ctrl-gpu" onclick="slateCtrl('gpu', this)">
                                <span class="ctrl-dot" id="dot-gpu"></span>
                                <span class="ctrl-icon">&#9670;</span>
                                <span class="ctrl-label">GPU</span>
                            </button>
                        </div>
                        <div class="ctrl-term" id="ctrl-term"></div>
                        <div class="ci-row">
                            <button class="btn btn-filled" onclick="dispatchWorkflow('ci.yml')">CI Pipeline</button>
                            <button class="btn btn-outline" onclick="dispatchWorkflow('slate.yml')">SLATE Checks</button>
                            <button class="btn btn-outline" onclick="dispatchWorkflow('nightly.yml')">Nightly</button>
                            <button class="btn btn-outline" onclick="dispatchWorkflow('agentic.yml')">Agentic AI</button>
                        </div>
                    </div>

                    <!-- Action History / Tracking -->
                    <div class="card col-12" role="region" aria-label="Action Tracking">
                        <div class="card-header">
                            <span class="card-title">Action History</span>
                            <button class="card-action" onclick="refreshActionHistory()">Refresh</button>
                        </div>
                        <div id="action-history" style="max-height:240px;overflow-y:auto;">
                            <div class="empty">No actions recorded yet</div>
                        </div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Hardware ═══ -->
                <div class="dash-section" id="sec-hardware">
                <div class="grid">
                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">GPU Performance</span>
                            <button class="card-action" onclick="runBenchmark()">Benchmark</button>
                        </div>
                        <div id="hw-gpu-meters">
                            <div class="metric"><span class="metric-label">GPU 0</span><div class="metric-bar"><div class="metric-fill" id="hw-gpu0-bar" style="width:0%"></div></div><span class="metric-value" id="hw-gpu0-val">--%</span></div>
                            <div class="metric"><span class="metric-label">GPU 1</span><div class="metric-bar"><div class="metric-fill" id="hw-gpu1-bar" style="width:0%"></div></div><span class="metric-value" id="hw-gpu1-val">--%</span></div>
                        </div>
                        <div style="display:flex;gap:var(--sl-space-4);margin-top:var(--sl-space-4);">
                            <div class="hw-stat"><div class="hw-stat-value" id="bench-speed">--</div><div class="hw-stat-label">tok/s</div></div>
                            <div class="hw-stat"><div class="hw-stat-value" id="bench-bandwidth">--</div><div class="hw-stat-label">GB/s</div></div>
                        </div>
                    </div>

                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Ollama Models</span>
                            <button class="card-action" onclick="refreshSystemHealth()">Refresh</button>
                        </div>
                        <div id="ollama-status"><div class="empty">Loading...</div></div>
                    </div>

                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Docker</span>
                            <button class="card-action" onclick="refreshDocker()">Refresh</button>
                        </div>
                        <div class="docker-grid" id="docker-containers"><div class="empty">Loading...</div></div>
                        <div style="display:flex;gap:var(--sl-space-2);margin-top:var(--sl-space-3);padding-top:var(--sl-space-3);border-top:1px solid var(--sl-border);">
                            <button class="btn btn-outline" onclick="dockerActionAll('start')" style="flex:1;font-size:0.65rem;">Start All</button>
                            <button class="btn btn-outline" onclick="dockerActionAll('stop')" style="flex:1;font-size:0.65rem;">Stop All</button>
                        </div>
                    </div>

                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Multi-Runner</span>
                            <button class="card-action" onclick="refreshMultiRunner()">Refresh</button>
                        </div>
                        <div id="multi-runner-status"><div class="empty">Loading...</div></div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Workflows ═══ -->
                <div class="dash-section" id="sec-workflows">
                <div class="grid">
                    <div class="card col-8">
                        <div class="card-header">
                            <span class="card-title">Recent Workflows</span>
                            <button class="card-action" onclick="refreshWorkflows()">Refresh</button>
                        </div>
                        <div id="workflow-list" style="max-height:400px;overflow-y:auto;"><div class="empty">Loading...</div></div>
                    </div>

                    <div class="card col-4">
                        <div class="card-header">
                            <span class="card-title">Tech Tree</span>
                            <button class="card-action" onclick="refreshTechTree()">Refresh</button>
                        </div>
                        <div class="tech-tree-stats" id="tech-tree-stats"><div class="empty">Loading...</div></div>
                    </div>

                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Specifications</span>
                            <button class="card-action" onclick="refreshSpecs()">Refresh</button>
                        </div>
                        <div id="spec-list"><div class="empty">Loading...</div></div>
                    </div>

                    <div class="card col-6">
                        <div class="card-header">
                            <span class="card-title">Forks</span>
                            <button class="card-action" onclick="refreshForks()">Refresh</button>
                        </div>
                        <div id="fork-list"><div class="empty">Loading...</div></div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Tasks ═══ -->
                <div class="dash-section" id="sec-tasks">
                <div class="grid">
                    <div class="card col-12">
                        <div class="card-header">
                            <span class="card-title">Task Queue</span>
                            <button class="card-action" onclick="refreshTasks()">Refresh</button>
                        </div>
                        <div class="task-form">
                            <input type="text" class="task-input" id="new-task-title" placeholder="Add a new task..." onkeypress="if(event.key==='Enter')createTask()">
                            <select id="new-task-priority">
                                <option value="3">Normal</option>
                                <option value="1">High</option>
                                <option value="5">Low</option>
                            </select>
                            <button class="btn btn-tonal" onclick="createTask()">Add</button>
                        </div>
                        <div id="task-list" style="max-height:400px;overflow-y:auto;"><div class="empty">Loading tasks...</div></div>
                    </div>

                    <div class="card col-12">
                        <div class="card-header">
                            <span class="card-title">Task Activity Heatmap</span>
                            <button class="card-action" onclick="refreshHeatmap()">Refresh</button>
                        </div>
                        <div id="heatmap-total" style="font-size:0.65rem;color:var(--sl-text-disabled);margin-bottom:var(--sl-space-2);">0 tasks</div>
                        <div class="heatmap-grid" id="heatmap-grid"></div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: GitHub ═══ -->
                <div class="dash-section" id="sec-github">
                <div class="grid">
                    <div class="card col-12">
                        <div class="card-header">
                            <span class="card-title">GitHub Integration</span>
                            <button class="card-action" onclick="refreshGitHub()">Refresh</button>
                        </div>
                        <div class="gh-grid">
                            <div>
                                <div class="gh-section-title">Open PRs <span class="count" id="pr-count">0</span></div>
                                <div id="pr-list"><div class="empty">Loading...</div></div>
                            </div>
                            <div>
                                <div class="gh-section-title">Commits</div>
                                <div id="commit-list"><div class="empty">Loading...</div></div>
                            </div>
                            <div>
                                <div class="gh-section-title">Issues <span class="count" id="issue-count">0</span></div>
                                <div id="issue-list"><div class="empty">Loading...</div></div>
                            </div>
                            <div>
                                <div class="gh-section-title">Release</div>
                                <div id="release-info"><div class="empty">Loading...</div></div>
                            </div>
                        </div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Agents ═══ -->
                <div class="dash-section" id="sec-agents">
                <div class="grid">
                    <div class="card col-12">
                        <div class="card-header">
                            <span class="card-title">Agent System</span>
                            <button class="card-action" onclick="refreshAgents()">Refresh</button>
                        </div>
                        <div id="agent-list"><div class="empty">Loading agents...</div></div>
                    </div>
                </div>
                </div>

                <!-- ═══ SECTION: Activity ═══ -->
                <div class="dash-section" id="sec-activity">
                <div class="grid">
                    <div class="card col-12">
                        <div class="card-header">
                            <span class="card-title">Activity Feed</span>
                            <button class="card-action" onclick="refreshActivity()">Refresh</button>
                        </div>
                        <div id="activity-feed" style="max-height:400px;overflow-y:auto;"><div class="empty">No activity</div></div>
                    </div>
                </div>
                </div>

                </main>
            </div>
        </div>
    </div>

    <div id="conn-status"><span class="pulse-dot" id="ws-dot"></span> <span id="ws-text">Connecting...</span></div>
'''


def build_template_js() -> str:
    """Build the JavaScript for the dashboard template."""
    # This JS preserves all the existing API-calling functions
    # from the original dashboard, adapted to the new element IDs
    return '''
    <script>
        // ═══════════════════════════════════════════════════════════════
        // SLATE Dashboard v3.0 — JavaScript
        // ═══════════════════════════════════════════════════════════════

        // ─── Onboarding ──────────────────────────────────────────────
        (function() {
            if (!localStorage.getItem('slate_onboarded')) {
                document.getElementById('onboard').classList.add('active');
            }
        })();

        function dismissOnboard() {
            localStorage.setItem('slate_onboarded', '1');
            document.getElementById('onboard').classList.remove('active');
        }

        // ─── Section Navigation ──────────────────────────────────────
        const sectionTitles = {
            overview:  { title: 'Overview',   sub: 'System status and quick actions' },
            controls:  { title: 'Controls',   sub: 'Manage system operations, CI/CD, and AI' },
            hardware:  { title: 'Hardware',   sub: 'GPU, Docker, and resource monitoring' },
            workflows: { title: 'Workflows',  sub: 'CI/CD pipelines, specs, and tech tree' },
            tasks:     { title: 'Tasks',      sub: 'Task queue, heatmap, and scheduling' },
            github:    { title: 'GitHub',     sub: 'PRs, issues, commits, and releases' },
            agents:    { title: 'Agents',     sub: 'AI agent system and routing' },
            activity:  { title: 'Activity',   sub: 'Recent operations and events' }
        };

        let activeSection = localStorage.getItem('slate_section') || 'overview';

        function showSection(name, navBtn) {
            // Hide all sections
            document.querySelectorAll('.dash-section').forEach(s => s.classList.remove('active'));
            // Show target
            const sec = document.getElementById('sec-' + name);
            if (sec) sec.classList.add('active');
            // Update nav active state
            document.querySelectorAll('.nav-item').forEach(b => b.classList.remove('active'));
            if (navBtn) navBtn.classList.add('active');
            // Update topbar
            const info = sectionTitles[name] || { title: name, sub: '' };
            document.getElementById('section-title').textContent = info.title;
            document.getElementById('section-subtitle').textContent = info.sub;
            // Persist
            activeSection = name;
            localStorage.setItem('slate_section', name);
        }

        // Restore last section on load
        (function() {
            const saved = localStorage.getItem('slate_section') || 'overview';
            const navItems = document.querySelectorAll('.nav-item');
            const sectionNames = ['overview','controls','hardware','workflows','tasks','github','agents','activity'];
            const idx = sectionNames.indexOf(saved);
            if (idx >= 0 && navItems[idx]) {
                showSection(saved, navItems[idx]);
            }
        })();

        // Action history tracking
        const actionLog = [];
        function logAction(action, success, duration) {
            actionLog.unshift({ action, success, duration, time: new Date().toLocaleTimeString() });
            if (actionLog.length > 50) actionLog.pop();
            refreshActionHistory();
        }
        function refreshActionHistory() {
            const el = document.getElementById('action-history');
            if (!el) return;
            if (actionLog.length === 0) { el.innerHTML = '<div class="empty">No actions recorded yet</div>'; return; }
            el.innerHTML = actionLog.map(a => {
                const icon = a.success ? '<span class="ok">&#10003;</span>' : '<span class="err">&#10007;</span>';
                const dur = a.duration ? ' (' + a.duration + 'ms)' : '';
                return '<div style="padding:6px 8px;border-bottom:1px solid var(--sl-border);font-size:0.7rem;display:flex;align-items:center;gap:8px;">'
                    + icon + '<span style="flex:1;">' + a.action + dur + '</span>'
                    + '<span style="color:var(--sl-text-disabled);">' + a.time + '</span></div>';
            }).join('');
        }

        // ─── WebSocket ───────────────────────────────────────────────
        let ws = null;
        function connectWS() {
            const proto = location.protocol === 'https:' ? 'wss:' : 'ws:';
            ws = new WebSocket(proto + '//' + location.host + '/ws');
            ws.onopen = () => {
                document.getElementById('ws-dot').className = 'pulse-dot';
                document.getElementById('ws-text').textContent = 'Connected';
            };
            ws.onclose = () => {
                document.getElementById('ws-dot').className = 'pulse-dot offline';
                document.getElementById('ws-text').textContent = 'Reconnecting...';
                setTimeout(connectWS, 3000);
            };
            ws.onmessage = (e) => {
                try {
                    const data = JSON.parse(e.data);
                    if (data.type === 'status') updateStatus(data);
                    if (data.type === 'task_update') refreshTasks();
                    if (data.type === 'workflow_update') refreshWorkflows();
                } catch(err) {}
            };
        }
        connectWS();

        function updateStatus(data) {
            const dot = document.getElementById('runner-dot');
            const text = document.getElementById('runner-status-text');
            const topDot = document.getElementById('topbar-dot');
            const topText = document.getElementById('topbar-status-text');
            if (data.runner_online) {
                dot.className = 'pulse-dot';
                text.textContent = 'Runner Online';
                if (topDot) topDot.className = 'pulse-dot';
                if (topText) topText.textContent = 'Online';
            } else {
                dot.className = 'pulse-dot offline';
                text.textContent = 'Runner Offline';
                if (topDot) topDot.className = 'pulse-dot offline';
                if (topText) topText.textContent = 'Offline';
            }
        }

        // ─── SLATE Controls (with AI Intelligence) ─────────────────
        async function slateCtrl(action, btn) {
            if (btn.classList.contains('running')) return;
            btn.classList.remove('ok', 'err');
            btn.classList.add('running');
            const term = document.getElementById('ctrl-term');
            term.classList.add('open');
            term.innerHTML = '<span class="lbl">Running ' + action + '...</span>\\n';
            const t0 = performance.now();
            try {
                const res = await fetch('/api/slate/' + action, { method: 'POST' });
                const data = await res.json();
                const elapsed = Math.round(performance.now() - t0);
                btn.classList.remove('running');
                if (data.steps) {
                    let html = '';
                    data.steps.forEach(s => {
                        const icon = s.success ? '<span class="ok">&#10003;</span>' : '<span class="err">&#10007;</span>';
                        html += icon + ' <span class="lbl">' + s.step + '</span>\\n';
                        if (s.output) html += s.output + '\\n';
                        if (s.error) html += '<span class="err">' + s.error + '</span>\\n';
                    });
                    term.innerHTML = html;
                    btn.classList.add(data.success ? 'ok' : 'err');
                } else {
                    term.innerHTML = data.success
                        ? '<span class="ok">&#10003;</span> <span class="lbl">' + action + '</span>\\n' + (data.output || 'Done')
                        : '<span class="err">&#10007;</span> <span class="lbl">' + action + '</span>\\n' + (data.error || 'Failed');
                    btn.classList.add(data.success ? 'ok' : 'err');
                }
                setDot(action.replace('run-protocol','protocol'), data.success);
                logAction(action, data.success, elapsed);
                // Record action for AI learning
                fetch('/api/slate/ai/record', { method:'POST', headers:{'Content-Type':'application/json'},
                    body: JSON.stringify({ action: action.replace('run-',''), success: data.success, duration_ms: elapsed })
                }).catch(()=>{});
                // Request AI summary if failed
                if (!data.success) {
                    const errText = (data.steps || []).filter(s => !s.success).map(s => s.error || s.output || '').join('; ') || data.error || '';
                    fetch('/api/slate/ai/recovery', { method:'POST', headers:{'Content-Type':'application/json'},
                        body: JSON.stringify({ action, error: errText })
                    }).then(r => r.json()).then(d => {
                        if (d.suggestion) term.innerHTML += '\\n<span class="lbl">&#9672; AI Fix:</span> ' + d.suggestion + '\\n';
                    }).catch(()=>{});
                }
            } catch (e) {
                btn.classList.remove('running');
                btn.classList.add('err');
                term.innerHTML = '<span class="err">&#10007; ' + e.message + '</span>';
            }
        }

        async function loadAiRecommend() {
            const el = document.getElementById('ai-rec');
            const txt = document.getElementById('ai-rec-text');
            el.style.display = 'block';
            txt.textContent = 'Analyzing system state...';
            try {
                const res = await fetch('/api/slate/ai/recommend');
                const data = await res.json();
                txt.textContent = data.recommendation || 'No recommendation available.';
            } catch (e) {
                txt.textContent = 'Run SLATE protocol to check system health.';
            }
        }

        async function slateDeploy(deployAction, btn) {
            if (btn.classList.contains('running')) return;
            btn.classList.remove('ok', 'err');
            btn.classList.add('running');
            const term = document.getElementById('ctrl-term');
            term.classList.add('open');
            term.innerHTML = '<span class="lbl">Services: ' + deployAction + '...</span>\\n';
            try {
                const res = await fetch('/api/slate/deploy/' + deployAction, { method: 'POST' });
                const data = await res.json();
                btn.classList.remove('running');
                term.innerHTML = data.success
                    ? '<span class="ok">&#10003;</span> Services ' + deployAction + '\\n' + (data.output || 'Done')
                    : '<span class="err">&#10007;</span> Services ' + deployAction + '\\n' + (data.error || 'Failed');
                btn.classList.add(data.success ? 'ok' : 'err');
                setDot('deploy', data.success);
            } catch (e) {
                btn.classList.remove('running');
                btn.classList.add('err');
                term.innerHTML = '<span class="err">&#10007; ' + e.message + '</span>';
            }
        }

        function setDot(name, ok) {
            const d = document.getElementById('dot-' + name);
            if (d) d.className = 'ctrl-dot ' + (ok ? 'ok' : 'err');
        }

        function toggleTerm() {
            document.getElementById('ctrl-term').classList.toggle('open');
        }

        // Deploy right-click for stop/status
        document.getElementById('ctrl-deploy')?.addEventListener('contextmenu', function(e) {
            e.preventDefault();
            const action = prompt('Services action:', 'stop');
            if (action && ['start','stop','status'].includes(action)) slateDeploy(action, this);
        });

        // ─── Dispatch Workflow ────────────────────────────────────────
        async function dispatchWorkflow(name) {
            try {
                const res = await fetch('/api/dispatch/' + name, { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    showToast('Dispatched: ' + name);
                    setTimeout(refreshWorkflows, 3000);
                } else {
                    showToast('Failed: ' + (data.error || 'Unknown error'), true);
                }
            } catch (e) {
                showToast('Error: ' + e.message, true);
            }
        }

        function showToast(msg, isError) {
            const term = document.getElementById('ctrl-term');
            term.classList.add('open');
            const cls = isError ? 'err' : 'ok';
            term.innerHTML += '<span class="' + cls + '">' + (isError ? '&#10007; ' : '&#10003; ') + msg + '</span>\\n';
        }

        // ─── Refresh Functions ────────────────────────────────────────
        async function refreshTasks() {
            try {
                const res = await fetch('/api/tasks');
                const data = await res.json();
                const list = document.getElementById('task-list');
                if (!data.tasks || data.tasks.length === 0) {
                    list.innerHTML = '<div class="empty">No tasks</div>';
                    return;
                }
                const navBadge = document.getElementById('nav-task-count');
                if (navBadge) navBadge.textContent = data.tasks.length;
                list.innerHTML = data.tasks.map(t => {
                    const statusCls = t.status === 'completed' ? 'online' : t.status === 'in_progress' ? 'warning' : 'pending';
                    return '<div class="task-item"><span>' + (t.title || t.id) + '</span><span class="badge ' + statusCls + '">' + t.status + '</span></div>';
                }).join('');
            } catch (e) { console.log('Tasks refresh error:', e); }
        }

        async function refreshWorkflows() {
            try {
                const res = await fetch('/api/workflows');
                const data = await res.json();
                const list = document.getElementById('workflow-list');
                if (!data.runs || data.runs.length === 0) {
                    list.innerHTML = '<div class="empty">No workflows</div>';
                    return;
                }
                const navWfBadge = document.getElementById('nav-wf-count');
                if (navWfBadge) navWfBadge.textContent = data.runs.length;
                list.innerHTML = data.runs.slice(0, 10).map(w => {
                    const icon = w.conclusion === 'success' ? '<span class="ok">&#10003;</span>' :
                                 w.conclusion === 'failure' ? '<span class="err">&#10007;</span>' :
                                 w.status === 'in_progress' ? '<span style="color:var(--sl-warning)">&#9679;</span>' : '&#9679;';
                    return '<div class="wf-item"><span class="wf-name">' + icon + ' ' + (w.name || '') + '</span><span class="wf-meta">#' + (w.run_number || '') + '</span></div>';
                }).join('');
            } catch (e) { console.log('Workflows refresh error:', e); }
        }

        async function refreshRunner() {
            try {
                const res = await fetch('/api/runner');
                const data = await res.json();
                updateStatus({ runner_online: data.status === 'online' || data.runner?.status === 'online' });
            } catch (e) {}
        }

        async function refreshWorkflowPipeline() {
            try {
                const res = await fetch('/api/status');
                const data = await res.json();
                if (data.pipeline) {
                    document.getElementById('flow-task-count').textContent = data.pipeline.tasks || '0';
                    document.getElementById('flow-runner-status').textContent = data.pipeline.runner || 'Idle';
                    document.getElementById('flow-workflow-count').textContent = data.pipeline.workflows || '0';
                    document.getElementById('flow-pr-count').textContent = data.pipeline.prs || '0';
                }
                if (data.tasks) {
                    document.getElementById('flow-task-count').textContent = data.tasks.total || '0';
                }
            } catch (e) {}
        }

        async function refreshGitHub() {
            try {
                const res = await fetch('/api/github');
                const data = await res.json();
                // PRs
                const prList = document.getElementById('pr-list');
                const prCount = document.getElementById('pr-count');
                if (data.prs && data.prs.length > 0) {
                    prCount.textContent = data.prs.length;
                    prList.innerHTML = data.prs.slice(0, 5).map(pr => '<div class="gh-item">#' + pr.number + ' ' + pr.title + '</div>').join('');
                } else { prList.innerHTML = '<div class="empty">No open PRs</div>'; prCount.textContent = '0'; }
                // Commits
                const commitList = document.getElementById('commit-list');
                if (data.commits && data.commits.length > 0) {
                    commitList.innerHTML = data.commits.slice(0, 5).map(c => '<div class="gh-item" style="font-family:var(--sl-font-mono);font-size:0.6rem;">' + (c.sha || '').substring(0,7) + ' ' + (c.message || '').substring(0,50) + '</div>').join('');
                } else { commitList.innerHTML = '<div class="empty">No commits</div>'; }
                // Issues
                const issueList = document.getElementById('issue-list');
                const issueCount = document.getElementById('issue-count');
                if (data.issues && data.issues.length > 0) {
                    issueCount.textContent = data.issues.length;
                    issueList.innerHTML = data.issues.slice(0, 5).map(i => '<div class="gh-item">#' + i.number + ' ' + i.title + '</div>').join('');
                } else { issueList.innerHTML = '<div class="empty">No issues</div>'; issueCount.textContent = '0'; }
                // Release
                if (data.release) {
                    document.getElementById('release-info').innerHTML = '<div class="gh-item"><strong>' + (data.release.tag || '') + '</strong> ' + (data.release.name || '') + '</div>';
                }
            } catch (e) { console.log('GitHub refresh error:', e); }
        }

        async function refreshSystemHealth() {
            try {
                const res = await fetch('/api/system/gpu');
                const data = await res.json();
                // GPU utilization
                const gpuDiv = document.getElementById('gpu-utilization');
                if (data.gpus && data.gpus.length > 0) {
                    gpuDiv.innerHTML = data.gpus.map((g, i) => {
                        return '<div class="metric"><span class="metric-label">' + (g.name || 'GPU ' + i) + '</span><div class="metric-bar"><div class="metric-fill" style="width:' + (g.utilization || 0) + '%"></div></div><span class="metric-value">' + (g.utilization || 0) + '%</span></div>' +
                               '<div style="font-size:0.6rem;color:var(--sl-text-disabled);padding:0 0 4px var(--sl-space-3);">' + (g.memory_used || 0) + ' / ' + (g.memory_total || 0) + ' MiB</div>';
                    }).join('');
                    // Update hardware panel too
                    data.gpus.forEach((g, i) => {
                        const bar = document.getElementById('hw-gpu' + i + '-bar');
                        const val = document.getElementById('hw-gpu' + i + '-val');
                        if (bar) bar.style.width = (g.utilization || 0) + '%';
                        if (val) val.textContent = (g.utilization || 0) + '%';
                    });
                }
                // System resources
                if (data.system) {
                    const cpu = data.system.cpu_percent || 0;
                    const mem = data.system.memory_percent || 0;
                    const disk = data.system.disk_percent || 0;
                    document.getElementById('cpu-bar').style.width = cpu + '%';
                    document.getElementById('cpu-value').textContent = cpu + '%';
                    document.getElementById('memory-bar').style.width = mem + '%';
                    document.getElementById('memory-value').textContent = mem + '%';
                    document.getElementById('disk-bar').style.width = disk + '%';
                    document.getElementById('disk-value').textContent = disk + '%';
                }
                // Ollama
                if (data.ollama) {
                    const ollamaDiv = document.getElementById('ollama-status');
                    if (data.ollama.models && data.ollama.models.length > 0) {
                        ollamaDiv.innerHTML = data.ollama.models.map(m => '<div style="font-size:0.7rem;color:var(--sl-text-tertiary);padding:2px 0;">' + m.name + ' <span style="color:var(--sl-text-disabled)">' + (m.size || '') + '</span></div>').join('');
                    } else {
                        ollamaDiv.innerHTML = '<div class="empty">No models loaded</div>';
                    }
                }
            } catch (e) { console.log('System health error:', e); }
        }

        async function refreshServices() {
            try {
                const res = await fetch('/api/services');
                const data = await res.json();
                if (data.services) {
                    const mapping = {
                        'orchestrator': 'orch-badge',
                        'runner': 'runner-badge',
                        'ollama': 'ollama-badge',
                        'foundry': 'foundry-badge',
                        'docker': 'docker-badge'
                    };
                    for (const [key, elemId] of Object.entries(mapping)) {
                        const badge = document.getElementById(elemId);
                        if (badge && data.services[key] !== undefined) {
                            const online = data.services[key];
                            badge.className = 'badge ' + (online ? 'online' : 'offline');
                            badge.textContent = online ? 'Online' : 'Offline';
                        }
                    }
                }
            } catch (e) {}
        }

        async function refreshActivity() {
            try {
                const res = await fetch('/api/activity');
                const data = await res.json();
                const feed = document.getElementById('activity-feed');
                if (data.events && data.events.length > 0) {
                    feed.innerHTML = data.events.slice(0, 8).map(e => '<div class="feed-item"><div class="feed-dot"></div><div><div class="feed-text">' + e.message + '</div><div class="feed-time">' + (e.time || '') + '</div></div></div>').join('');
                } else {
                    feed.innerHTML = '<div class="empty">No activity</div>';
                }
            } catch (e) {}
        }

        async function refreshHeatmap() {
            try {
                const res = await fetch('/api/heatmap');
                const data = await res.json();
                if (data.total !== undefined) {
                    document.getElementById('heatmap-total').textContent = data.total + ' tasks';
                }
                const grid = document.getElementById('heatmap-grid');
                if (data.weeks) {
                    grid.innerHTML = data.weeks.map(week => {
                        return '<div class="heatmap-week">' + week.map(day => '<div class="heatmap-day" data-level="' + (day.level || 0) + '" title="' + (day.date || '') + ': ' + (day.count || 0) + '"></div>').join('') + '</div>';
                    }).join('');
                }
            } catch (e) {}
        }

        async function refreshTechTree() {
            try {
                const res = await fetch('/api/tech-tree');
                const data = await res.json();
                const stats = document.getElementById('tech-tree-stats');
                if (data.by_status) {
                    stats.innerHTML = Object.entries(data.by_status).map(([k,v]) => '<div class="tt-stat"><div class="tt-stat-val">' + v + '</div><div class="tt-stat-lbl">' + k + '</div></div>').join('');
                } else {
                    stats.innerHTML = '<div class="empty">No tech tree data</div>';
                }
            } catch (e) {}
        }

        async function refreshAgents() {
            try {
                const res = await fetch('/api/agents');
                const data = await res.json();
                const list = document.getElementById('agent-list');
                if (data.agents && data.agents.length > 0) {
                    list.innerHTML = data.agents.map(a => {
                        const cls = a.status === 'active' ? 'online' : 'pending';
                        return '<div class="svc-item"><div class="svc-name"><div class="svc-icon">' + (a.name || '?')[0] + '</div><span>' + (a.name || 'Unknown') + '</span></div><span class="badge ' + cls + '">' + (a.role || a.status || '') + '</span></div>';
                    }).join('');
                } else {
                    list.innerHTML = '<div class="empty">No agents registered</div>';
                }
            } catch (e) {}
        }

        async function refreshForks() {
            try {
                const res = await fetch('/api/forks');
                const data = await res.json();
                const list = document.getElementById('fork-list');
                if (data.forks && data.forks.length > 0) {
                    list.innerHTML = data.forks.slice(0, 5).map(f => '<div class="gh-item">' + f.full_name + '</div>').join('');
                } else {
                    list.innerHTML = '<div class="empty">No forks</div>';
                }
            } catch (e) {}
        }

        async function refreshSpecs() {
            try {
                const res = await fetch('/api/specs');
                const data = await res.json();
                const list = document.getElementById('spec-list');
                if (data.specs && data.specs.length > 0) {
                    list.innerHTML = data.specs.slice(0, 5).map(s => {
                        const cls = s.status === 'approved' ? 'online' : s.status === 'implementing' ? 'warning' : 'pending';
                        return '<div class="svc-item"><span style="font-size:0.7rem;color:var(--sl-text-tertiary);">' + s.title + '</span><span class="badge ' + cls + '">' + s.status + '</span></div>';
                    }).join('');
                } else {
                    list.innerHTML = '<div class="empty">No specs</div>';
                }
            } catch (e) {}
        }

        async function refreshMultiRunner() {
            try {
                const res = await fetch('/api/multirunner');
                const data = await res.json();
                const el = document.getElementById('multi-runner-status');
                if (data.runners) {
                    el.innerHTML = '<div style="font-size:0.7rem;color:var(--sl-text-tertiary);">Active: ' + (data.active || 0) + ' / ' + (data.total || 0) + '</div>';
                } else {
                    el.innerHTML = '<div class="empty">Not configured</div>';
                }
            } catch (e) {
                document.getElementById('multi-runner-status').innerHTML = '<div class="empty">Not available</div>';
            }
        }

        async function refreshWorkflowStats() {
            // Placeholder for workflow analytics
        }

        async function refreshDocker() {
            try {
                const res = await fetch('/api/docker');
                const data = await res.json();
                const el = document.getElementById('docker-containers');
                if (data.containers && data.containers.length > 0) {
                    el.innerHTML = data.containers.map(c => {
                        const cls = c.state === 'running' ? 'online' : 'offline';
                        return '<div class="svc-item"><div class="svc-name"><div class="svc-icon">&#128051;</div><span style="font-size:0.7rem;">' + (c.name || '') + '</span></div><span class="badge ' + cls + '">' + (c.state || '') + '</span></div>';
                    }).join('');
                } else {
                    el.innerHTML = '<div class="empty">No containers</div>';
                }
            } catch (e) {}
        }

        async function dockerActionAll(action) {
            try {
                await fetch('/api/docker/' + action, { method: 'POST' });
                showToast('Docker ' + action + ' initiated');
                setTimeout(refreshDocker, 2000);
            } catch (e) {}
        }

        async function createTask() {
            const title = document.getElementById('new-task-title').value.trim();
            if (!title) return;
            const priority = document.getElementById('new-task-priority').value;
            try {
                await fetch('/api/tasks', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title, priority: parseInt(priority) })
                });
                document.getElementById('new-task-title').value = '';
                refreshTasks();
            } catch (e) {}
        }

        async function runBenchmark() {
            const term = document.getElementById('ctrl-term');
            term.classList.add('open');
            term.innerHTML = '<span class="lbl">Running benchmarks...</span>\\n';
            try {
                const res = await fetch('/api/slate/benchmark', { method: 'POST' });
                const data = await res.json();
                if (data.success) {
                    term.innerHTML += '<span class="ok">&#10003;</span> ' + (data.output || 'Done') + '\\n';
                } else {
                    term.innerHTML += '<span class="err">&#10007;</span> ' + (data.error || 'Failed') + '\\n';
                }
            } catch (e) {
                term.innerHTML += '<span class="err">&#10007; ' + e.message + '</span>\\n';
            }
        }

        // ─── Refresh All ──────────────────────────────────────────────
        function refreshAll() {
            refreshTasks();
            refreshWorkflows();
            refreshRunner();
            refreshWorkflowPipeline();
            refreshGitHub();
            refreshSystemHealth();
            refreshServices();
            refreshActivity();
            refreshHeatmap();
            refreshTechTree();
            refreshAgents();
            refreshMultiRunner();
            refreshSpecs();
            refreshForks();
            refreshDocker();
        }

        // ─── Initial Load ─────────────────────────────────────────────
        async function fetchInitialStatus() {
            try {
                const res = await fetch('/api/orchestrator');
                const data = await res.json();
                updateStatus(data);
            } catch (e) {}
        }

        fetchInitialStatus();
        refreshAll();
        setInterval(refreshAll, 15000);
    </script>
</body>
</html>'''


def get_full_template() -> str:
    """Return the complete HTML template string with control panel."""
    from slate_web.control_panel_ui import get_complete_control_panel

    base_template = build_template()
    js_template = build_template_js()

    # Inject practical control panel before closing </body>
    # Button-driven interface with real commands and step-by-step guidance
    control_panel = get_complete_control_panel()

    # Insert before </body></html>
    combined = base_template + js_template
    insert_point = combined.rfind('</body>')
    if insert_point > 0:
        combined = combined[:insert_point] + control_panel + combined[insert_point:]

    return combined


if __name__ == "__main__":
    html = get_full_template()
    out = Path(__file__).parent / "generated" / "dashboard-preview.html"
    out.parent.mkdir(exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[SLATE Template] Generated -> {out} ({len(html)} bytes)")
