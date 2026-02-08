// Modified: 2026-02-08T05:00:00Z | Author: Claude Opus 4.5 | Change: Create dynamic schematic background system
/**
 * SLATE Schematic Background System
 * ==================================
 * Generates a living, evolving schematic background for VS Code that reflects
 * the current state of the SLATE system. The background updates as:
 * - Tech tree nodes are completed
 * - Services come online/offline
 * - Specs progress through lifecycle
 * - System capabilities expand
 *
 * This embodies the SLATE ethos: systems evolve with progress.
 */

import * as vscode from 'vscode';
import * as fs from 'fs';
import * as path from 'path';
import { exec } from 'child_process';
import { promisify } from 'util';

const execAsync = promisify(exec);

// SLATE Design Tokens
const SLATE_COLORS = {
    primary: '#B85A3C',
    primaryLight: '#D4785A',
    primaryDark: '#8B4530',
    surface: '#0a0a0a',
    surfaceVariant: '#161616',
    blueprintBg: '#0D1B2A',
    blueprintGrid: '#1B3A4B',
    statusActive: '#22C55E',
    statusPending: '#F59E0B',
    statusInactive: '#6B7280',
    textPrimary: '#E8E2DE',
    textDim: '#78716C',
};

interface SystemState {
    techTreeProgress: number;
    completedNodes: string[];
    activeServices: string[];
    specsCompleted: number;
    specsTotal: number;
    gpuCount: number;
    aiBackendsOnline: number;
}

interface SchematicNode {
    id: string;
    label: string;
    x: number;
    y: number;
    status: 'active' | 'pending' | 'inactive' | 'complete';
    connections: string[];
}

/**
 * Generate the SLATE schematic SVG background
 */
export function generateSchematicSVG(state: SystemState): string {
    const width = 1920;
    const height = 1080;

    // Calculate progress-based opacity (more visible as system matures)
    const progressOpacity = Math.min(0.15, 0.05 + (state.techTreeProgress * 0.1));

    // Define schematic nodes based on SLATE architecture
    const nodes: SchematicNode[] = [
        // Core layer
        { id: 'core', label: 'SLATE CORE', x: width * 0.5, y: height * 0.15, status: 'active', connections: ['dashboard', 'mcp', 'orchestrator'] },

        // Service layer
        { id: 'dashboard', label: 'Dashboard', x: width * 0.25, y: height * 0.35, status: state.activeServices.includes('dashboard') ? 'active' : 'inactive', connections: ['ollama', 'chromadb'] },
        { id: 'mcp', label: 'MCP Server', x: width * 0.5, y: height * 0.35, status: state.activeServices.includes('mcp') ? 'active' : 'inactive', connections: ['claude', 'tools'] },
        { id: 'orchestrator', label: 'Orchestrator', x: width * 0.75, y: height * 0.35, status: state.activeServices.includes('orchestrator') ? 'active' : 'inactive', connections: ['runner', 'workflow'] },

        // AI layer
        { id: 'ollama', label: 'Ollama', x: width * 0.15, y: height * 0.55, status: state.aiBackendsOnline > 0 ? 'active' : 'inactive', connections: ['gpu'] },
        { id: 'chromadb', label: 'ChromaDB', x: width * 0.35, y: height * 0.55, status: state.activeServices.includes('chromadb') ? 'active' : 'inactive', connections: [] },
        { id: 'claude', label: 'Claude Code', x: width * 0.5, y: height * 0.55, status: 'active', connections: [] },
        { id: 'tools', label: 'AI Tools', x: width * 0.65, y: height * 0.55, status: state.completedNodes.length > 5 ? 'active' : 'pending', connections: [] },

        // Infrastructure layer
        { id: 'runner', label: 'GH Runner', x: width * 0.75, y: height * 0.55, status: state.activeServices.includes('runner') ? 'active' : 'inactive', connections: ['workflow'] },
        { id: 'workflow', label: 'Workflows', x: width * 0.85, y: height * 0.55, status: state.specsCompleted > 0 ? 'active' : 'pending', connections: [] },

        // Hardware layer
        { id: 'gpu', label: `GPU x${state.gpuCount}`, x: width * 0.15, y: height * 0.75, status: state.gpuCount > 0 ? 'active' : 'inactive', connections: [] },

        // Progress indicators (positioned along bottom)
        { id: 'specs', label: `Specs ${state.specsCompleted}/${state.specsTotal}`, x: width * 0.35, y: height * 0.85, status: state.specsCompleted === state.specsTotal ? 'complete' : 'pending', connections: [] },
        { id: 'techtree', label: `Tech ${Math.round(state.techTreeProgress * 100)}%`, x: width * 0.65, y: height * 0.85, status: state.techTreeProgress > 0.8 ? 'complete' : 'pending', connections: [] },
    ];

    // Build SVG
    let svg = `<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${width} ${height}" width="${width}" height="${height}">
  <defs>
    <!-- Grid pattern -->
    <pattern id="grid" width="40" height="40" patternUnits="userSpaceOnUse">
      <path d="M 40 0 L 0 0 0 40" fill="none" stroke="${SLATE_COLORS.blueprintGrid}" stroke-width="0.5" opacity="0.3"/>
    </pattern>

    <!-- Glow filter for active nodes -->
    <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
      <feGaussianBlur stdDeviation="4" result="blur"/>
      <feMerge>
        <feMergeNode in="blur"/>
        <feMergeNode in="SourceGraphic"/>
      </feMerge>
    </filter>

    <!-- Pulse animation -->
    <style>
      @keyframes pulse {
        0%, 100% { opacity: ${progressOpacity}; }
        50% { opacity: ${progressOpacity * 1.5}; }
      }
      .pulse { animation: pulse 3s ease-in-out infinite; }
      @keyframes flow {
        0% { stroke-dashoffset: 20; }
        100% { stroke-dashoffset: 0; }
      }
      .flow { animation: flow 2s linear infinite; }
    </style>
  </defs>

  <!-- Background -->
  <rect width="100%" height="100%" fill="${SLATE_COLORS.surface}"/>

  <!-- Grid overlay -->
  <rect width="100%" height="100%" fill="url(#grid)" opacity="${progressOpacity}"/>

  <!-- SLATE watermark text -->
  <text x="${width * 0.5}" y="${height * 0.5}"
        font-family="Consolas, monospace" font-size="200" font-weight="bold"
        fill="${SLATE_COLORS.primary}" opacity="${progressOpacity * 0.5}"
        text-anchor="middle" dominant-baseline="middle"
        letter-spacing="40">S.L.A.T.E.</text>

  <!-- Connection lines -->
  <g class="connections" opacity="${progressOpacity}">
`;

    // Draw connections
    for (const node of nodes) {
        for (const targetId of node.connections) {
            const target = nodes.find(n => n.id === targetId);
            if (target) {
                const isActive = node.status === 'active' && target.status === 'active';
                const color = isActive ? SLATE_COLORS.statusActive : SLATE_COLORS.blueprintGrid;
                svg += `    <line x1="${node.x}" y1="${node.y}" x2="${target.x}" y2="${target.y}"
          stroke="${color}" stroke-width="2" stroke-dasharray="${isActive ? '0' : '8,4'}"
          ${isActive ? 'class="flow"' : ''}/>\n`;
            }
        }
    }

    svg += `  </g>\n\n  <!-- Nodes -->\n  <g class="nodes pulse">\n`;

    // Draw nodes
    for (const node of nodes) {
        const statusColor = {
            'active': SLATE_COLORS.statusActive,
            'pending': SLATE_COLORS.statusPending,
            'inactive': SLATE_COLORS.statusInactive,
            'complete': SLATE_COLORS.primary,
        }[node.status];

        const nodeOpacity = node.status === 'active' ? progressOpacity * 2 : progressOpacity;
        const isCore = node.id === 'core';
        const radius = isCore ? 60 : 35;

        svg += `
    <!-- ${node.label} -->
    <g opacity="${nodeOpacity}" ${node.status === 'active' ? 'filter="url(#glow)"' : ''}>
      <circle cx="${node.x}" cy="${node.y}" r="${radius}"
              fill="${SLATE_COLORS.surfaceVariant}" stroke="${statusColor}" stroke-width="2"/>
      <circle cx="${node.x}" cy="${node.y}" r="${radius - 8}"
              fill="none" stroke="${statusColor}" stroke-width="1" stroke-dasharray="4,4"/>
      <text x="${node.x}" y="${node.y}"
            font-family="Consolas, monospace" font-size="${isCore ? 14 : 10}"
            fill="${SLATE_COLORS.textPrimary}" text-anchor="middle" dominant-baseline="middle">
        ${node.label}
      </text>
      <!-- Status indicator -->
      <circle cx="${node.x + radius - 5}" cy="${node.y - radius + 5}" r="5"
              fill="${statusColor}"/>
    </g>\n`;
    }

    svg += `  </g>\n`;

    // Add progress bar at bottom
    const progressWidth = width * 0.6;
    const progressX = (width - progressWidth) / 2;
    const progressY = height - 40;

    svg += `
  <!-- Progress Bar -->
  <g opacity="${progressOpacity * 2}">
    <rect x="${progressX}" y="${progressY}" width="${progressWidth}" height="8" rx="4"
          fill="${SLATE_COLORS.surfaceVariant}" stroke="${SLATE_COLORS.blueprintGrid}" stroke-width="1"/>
    <rect x="${progressX}" y="${progressY}" width="${progressWidth * state.techTreeProgress}" height="8" rx="4"
          fill="${SLATE_COLORS.primary}"/>
    <text x="${width * 0.5}" y="${progressY + 25}"
          font-family="Consolas, monospace" font-size="11"
          fill="${SLATE_COLORS.textDim}" text-anchor="middle">
      SLATE EVOLUTION: ${Math.round(state.techTreeProgress * 100)}% COMPLETE
    </text>
  </g>
`;

    svg += `</svg>`;

    return svg;
}

/**
 * Get current SLATE system state
 */
export async function getSystemState(workspacePath: string): Promise<SystemState> {
    const state: SystemState = {
        techTreeProgress: 0,
        completedNodes: [],
        activeServices: [],
        specsCompleted: 0,
        specsTotal: 0,
        gpuCount: 0,
        aiBackendsOnline: 0,
    };

    try {
        // Read tech tree
        const techTreePath = path.join(workspacePath, '.slate_tech_tree', 'tech_tree.json');
        if (fs.existsSync(techTreePath)) {
            const techTree = JSON.parse(fs.readFileSync(techTreePath, 'utf-8'));
            const nodes = techTree.nodes || [];
            state.completedNodes = nodes.filter((n: any) => n.status === 'complete').map((n: any) => n.id);
            state.techTreeProgress = nodes.length > 0 ? state.completedNodes.length / nodes.length : 0;
        }

        // Check specs
        const specsPath = path.join(workspacePath, 'specs');
        if (fs.existsSync(specsPath)) {
            const specDirs = fs.readdirSync(specsPath).filter(d => d.match(/^\d{3}-/));
            state.specsTotal = specDirs.length;

            for (const specDir of specDirs) {
                const specFile = path.join(specsPath, specDir, 'spec.md');
                if (fs.existsSync(specFile)) {
                    const content = fs.readFileSync(specFile, 'utf-8');
                    if (content.includes('Status**: complete') || content.includes('Status**: implementing')) {
                        state.specsCompleted++;
                    }
                }
            }
        }

        // Check services via Python
        try {
            const pythonPath = path.join(workspacePath, '.venv', 'Scripts', 'python.exe');
            const { stdout } = await execAsync(`"${pythonPath}" -c "import json; from slate.slate_status import quick_status; print(json.dumps(quick_status()))"`, {
                cwd: workspacePath,
                timeout: 5000,
            });
            const status = JSON.parse(stdout.trim());

            if (status.dashboard?.status === 'running') state.activeServices.push('dashboard');
            if (status.ollama?.status === 'running') {
                state.activeServices.push('ollama');
                state.aiBackendsOnline++;
            }
            if (status.runner?.status === 'running') state.activeServices.push('runner');
            if (status.gpu?.count) state.gpuCount = status.gpu.count;
        } catch {
            // Fallback: assume basic services
            state.activeServices = ['dashboard'];
        }

    } catch (error) {
        console.error('Error getting system state:', error);
    }

    return state;
}

/**
 * Apply schematic background to VS Code
 */
export async function applySchematicBackground(context: vscode.ExtensionContext): Promise<void> {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    const workspacePath = workspaceFolders[0].uri.fsPath;

    // Get current system state
    const state = await getSystemState(workspacePath);

    // Generate schematic SVG
    const svg = generateSchematicSVG(state);

    // Save SVG to extension storage
    const svgPath = path.join(context.globalStorageUri.fsPath, 'slate-background.svg');
    await vscode.workspace.fs.createDirectory(context.globalStorageUri);
    fs.writeFileSync(svgPath, svg, 'utf-8');

    // Convert to base64 data URI for CSS
    const base64 = Buffer.from(svg).toString('base64');
    const dataUri = `data:image/svg+xml;base64,${base64}`;

    // Generate CSS for VS Code background injection
    const css = `
/* SLATE Schematic Background - Auto-generated */
/* This background evolves with your SLATE system */

body {
    background-image: url("${dataUri}") !important;
    background-size: cover !important;
    background-position: center !important;
    background-attachment: fixed !important;
    background-repeat: no-repeat !important;
}

/* Ensure editor content remains readable */
.monaco-editor .view-lines {
    background: rgba(10, 10, 10, 0.85) !important;
}

.monaco-workbench .part.sidebar {
    background: rgba(10, 10, 10, 0.9) !important;
}

.monaco-workbench .part.panel {
    background: rgba(10, 10, 10, 0.9) !important;
}
`;

    // Save CSS file
    const cssPath = path.join(context.globalStorageUri.fsPath, 'slate-background.css');
    fs.writeFileSync(cssPath, css, 'utf-8');

    // Store paths for the custom CSS extension
    await context.globalState.update('slateBackgroundSvg', svgPath);
    await context.globalState.update('slateBackgroundCss', cssPath);
    await context.globalState.update('slateBackgroundDataUri', dataUri);

    // Notify user about background
    const config = vscode.workspace.getConfiguration('slate');
    const backgroundEnabled = config.get<boolean>('background.enabled', true);

    if (backgroundEnabled) {
        vscode.window.showInformationMessage(
            `SLATE Schematic Background generated (${Math.round(state.techTreeProgress * 100)}% evolution)`,
            'View CSS', 'Disable'
        ).then(selection => {
            if (selection === 'View CSS') {
                vscode.workspace.openTextDocument(cssPath).then(doc => {
                    vscode.window.showTextDocument(doc);
                });
            } else if (selection === 'Disable') {
                config.update('background.enabled', false, vscode.ConfigurationTarget.Global);
            }
        });
    }
}

/**
 * Register background refresh command
 */
export function registerBackgroundCommands(context: vscode.ExtensionContext): void {
    // Refresh background command
    context.subscriptions.push(
        vscode.commands.registerCommand('slate.refreshBackground', async () => {
            await applySchematicBackground(context);
            vscode.window.showInformationMessage('SLATE schematic background refreshed');
        })
    );

    // Toggle background command
    context.subscriptions.push(
        vscode.commands.registerCommand('slate.toggleBackground', async () => {
            const config = vscode.workspace.getConfiguration('slate');
            const current = config.get<boolean>('background.enabled', true);
            await config.update('background.enabled', !current, vscode.ConfigurationTarget.Global);
            vscode.window.showInformationMessage(`SLATE background ${!current ? 'enabled' : 'disabled'}`);
        })
    );

    // Get background data URI (for other extensions)
    context.subscriptions.push(
        vscode.commands.registerCommand('slate.getBackgroundDataUri', () => {
            return context.globalState.get<string>('slateBackgroundDataUri');
        })
    );
}

/**
 * Auto-update background on significant changes
 */
export function watchForStateChanges(context: vscode.ExtensionContext): void {
    const workspaceFolders = vscode.workspace.workspaceFolders;
    if (!workspaceFolders) return;

    const workspacePath = workspaceFolders[0].uri.fsPath;

    // Watch tech tree changes
    const techTreeWatcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(workspacePath, '.slate_tech_tree/tech_tree.json')
    );

    techTreeWatcher.onDidChange(async () => {
        console.log('Tech tree changed, refreshing background...');
        await applySchematicBackground(context);
    });

    context.subscriptions.push(techTreeWatcher);

    // Watch spec changes
    const specsWatcher = vscode.workspace.createFileSystemWatcher(
        new vscode.RelativePattern(workspacePath, 'specs/**/spec.md')
    );

    specsWatcher.onDidChange(async () => {
        console.log('Spec changed, refreshing background...');
        await applySchematicBackground(context);
    });

    context.subscriptions.push(specsWatcher);

    // Periodic refresh (every 30 minutes)
    const refreshInterval = setInterval(async () => {
        const config = vscode.workspace.getConfiguration('slate');
        if (config.get<boolean>('background.enabled', true)) {
            await applySchematicBackground(context);
        }
    }, 30 * 60 * 1000);

    context.subscriptions.push({
        dispose: () => clearInterval(refreshInterval)
    });
}
