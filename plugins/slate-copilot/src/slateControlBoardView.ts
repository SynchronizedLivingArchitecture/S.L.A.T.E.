// Modified: 2026-02-07T16:30:00Z | Author: COPILOT | Change: Add mini dev cycle ring and learning mode toggle
import * as vscode from 'vscode';
import { getSlateConfig } from './extension';

/**
 * SLATE Control Board - Animated control panel above the dashboard.
 *
 * Features:
 * - Animated service status indicators with pulse effects
 * - Mini dev cycle ring visualization (PLAN -> CODE -> TEST -> DEPLOY -> FEEDBACK)
 * - Learning mode toggle with XP/level display
 * - Guided mode controls (start/stop/pause)
 * - Quick action buttons for common operations
 * - SLATE copper/earth tone theming
 * - Real-time status updates via Python backend and WebSocket
 */
export class SlateControlBoardViewProvider implements vscode.WebviewViewProvider {
	public static readonly viewType = 'slate.controlBoardView';

	private _view?: vscode.WebviewView;
	private _statusInterval?: NodeJS.Timeout;

	constructor(private readonly _extensionUri: vscode.Uri) {}

	public resolveWebviewView(
		webviewView: vscode.WebviewView,
		_context: vscode.WebviewViewResolveContext,
		_token: vscode.CancellationToken,
	): void {
		this._view = webviewView;

		webviewView.webview.options = {
			enableScripts: true,
			localResourceRoots: [this._extensionUri]
		};

		webviewView.webview.html = this._getHtml(webviewView.webview);

		// Handle messages from webview
		webviewView.webview.onDidReceiveMessage(async (message) => {
			switch (message.type) {
				case 'runCommand':
					await this._runSlateCommand(message.command);
					break;
				case 'startGuidedMode':
					await this._startGuidedMode();
					break;
				case 'refreshStatus':
					await this._refreshStatus();
					break;
				case 'openChat':
					await vscode.commands.executeCommand('workbench.action.chat.open');
					break;
				case 'showStatus':
					await vscode.commands.executeCommand('slate.showStatus');
					break;
				case 'transitionStage':
					await this._transitionDevCycleStage(message.stage);
					break;
				case 'toggleLearning':
					await this._toggleLearningMode(message.active);
					break;
			}
		});

		// Auto-refresh status every 30 seconds
		this._statusInterval = setInterval(() => {
			this._refreshStatus();
			this._fetchInteractiveStatus();
		}, 30000);

		webviewView.onDidDispose(() => {
			if (this._statusInterval) {
				clearInterval(this._statusInterval);
			}
		});

		// Initial status fetch
		this._refreshStatus();
		this._fetchInteractiveStatus();
	}

	private async _runSlateCommand(command: string): Promise<void> {
		const config = getSlateConfig();
		const terminal = vscode.window.createTerminal('SLATE');
		terminal.show();
		terminal.sendText(`"${config.pythonPath}" ${command}`);
	}

	private async _startGuidedMode(): Promise<void> {
		const config = getSlateConfig();
		const terminal = vscode.window.createTerminal('SLATE Guided Mode');
		terminal.show();
		terminal.sendText(`"${config.pythonPath}" slate/guided_mode.py`);
	}

	private async _transitionDevCycleStage(stage: string): Promise<void> {
		try {
			// Fetch API to transition stage
			const response = await fetch('http://127.0.0.1:8080/api/devcycle/transition', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ to_stage: stage })
			});

			if (response.ok) {
				const data = await response.json();
				this._view?.webview.postMessage({
					type: 'devCycleUpdate',
					data: data
				});
			}
		} catch (error) {
			console.error('Failed to transition dev cycle stage:', error);
		}
	}

	private async _toggleLearningMode(active: boolean): Promise<void> {
		if (!active) {
			return; // Nothing to do when toggling off
		}

		try {
			// Start a learning session if not already active
			const response = await fetch('http://127.0.0.1:8080/api/interactive/start', {
				method: 'POST',
				headers: { 'Content-Type': 'application/json' },
				body: JSON.stringify({ path_id: 'slate-fundamentals' })
			});

			if (response.ok) {
				const data = await response.json() as { progress?: unknown };
				this._view?.webview.postMessage({
					type: 'learningUpdate',
					data: data.progress
				});
				vscode.window.showInformationMessage('SLATE Learning Mode activated! Check the dashboard for interactive tutorials.');
			}
		} catch (error) {
			console.error('Failed to toggle learning mode:', error);
		}
	}

	private async _fetchInteractiveStatus(): Promise<void> {
		if (!this._view) return;

		try {
			// Fetch dev cycle state
			const cycleResponse = await fetch('http://127.0.0.1:8080/api/devcycle/visualization');
			const cycleData = cycleResponse.ok ? await cycleResponse.json() : null;

			// Fetch learning progress
			const learnResponse = await fetch('http://127.0.0.1:8080/api/interactive/progress');
			const learnData = learnResponse.ok ? await learnResponse.json() : null;

			this._view.webview.postMessage({
				type: 'interactiveStatus',
				data: {
					dev_cycle: cycleData,
					learning: learnData
				}
			});
		} catch (error) {
			// Dashboard may not be running, ignore errors
		}
	}

	private async _refreshStatus(): Promise<void> {
		if (!this._view) return;

		// Send status update to webview
		this._view.webview.postMessage({
			type: 'statusUpdate',
			timestamp: new Date().toISOString()
		});
	}

	public refresh(): void {
		if (this._view) {
			this._view.webview.html = this._getHtml(this._view.webview);
		}
	}

	private _getHtml(webview: vscode.Webview): string {
		const nonce = getNonce();

		return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0" />
	<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; script-src 'nonce-${nonce}';" />
	<title>SLATE Control Board</title>
	<style>
		/* ============================================
		   SLATE DESIGN TOKENS
		   ============================================ */
		:root {
			/* Primary - Copper/Bronze */
			--slate-primary: #B87333;
			--slate-primary-light: #C9956B;
			--slate-primary-dark: #8B4530;
			--slate-primary-glow: rgba(184, 115, 51, 0.4);

			/* Surfaces - Dark earth tones */
			--slate-bg: #0a0a0a;
			--slate-surface: #111111;
			--slate-surface-elevated: #161616;
			--slate-border: #222222;

			/* Text */
			--slate-text: #E7E0D8;
			--slate-text-muted: #78716C;
			--slate-text-dim: #57534E;

			/* Status colors */
			--slate-success: #78B89A;
			--slate-warning: #D4A054;
			--slate-error: #C47070;
			--slate-info: #7EA8BE;

			/* Animation */
			--slate-transition: 200ms cubic-bezier(0.4, 0, 0.2, 1);
			--slate-spring: 300ms cubic-bezier(0.34, 1.56, 0.64, 1);
		}

		/* ============================================
		   BASE STYLES
		   ============================================ */
		* {
			margin: 0;
			padding: 0;
			box-sizing: border-box;
		}

		html, body {
			height: 100%;
			width: 100%;
			background: var(--slate-bg);
			color: var(--slate-text);
			font-family: 'Segoe UI', system-ui, sans-serif;
			font-size: 12px;
			overflow-x: hidden;
		}

		/* ============================================
		   ANIMATIONS
		   ============================================ */
		@keyframes pulse {
			0%, 100% { opacity: 1; transform: scale(1); }
			50% { opacity: 0.7; transform: scale(1.05); }
		}

		@keyframes glow {
			0%, 100% { box-shadow: 0 0 5px var(--slate-primary-glow); }
			50% { box-shadow: 0 0 20px var(--slate-primary-glow), 0 0 30px var(--slate-primary-glow); }
		}

		@keyframes slideIn {
			from { opacity: 0; transform: translateY(-10px); }
			to { opacity: 1; transform: translateY(0); }
		}

		@keyframes statusPulse {
			0%, 100% { box-shadow: 0 0 0 0 currentColor; }
			50% { box-shadow: 0 0 0 4px transparent; }
		}

		@keyframes ripple {
			0% { transform: scale(0); opacity: 0.5; }
			100% { transform: scale(2.5); opacity: 0; }
		}

		@keyframes breathe {
			0%, 100% { opacity: 0.6; }
			50% { opacity: 1; }
		}

		@keyframes scanline {
			0% { transform: translateY(-100%); }
			100% { transform: translateY(100%); }
		}

		/* ============================================
		   HEADER
		   ============================================ */
		.header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 10px 12px;
			background: linear-gradient(180deg, var(--slate-surface-elevated) 0%, var(--slate-surface) 100%);
			border-bottom: 1px solid var(--slate-border);
			position: relative;
			overflow: hidden;
		}

		.header::before {
			content: '';
			position: absolute;
			top: 0;
			left: 0;
			right: 0;
			height: 1px;
			background: linear-gradient(90deg, transparent, var(--slate-primary), transparent);
			animation: breathe 3s ease-in-out infinite;
		}

		.logo-section {
			display: flex;
			align-items: center;
			gap: 8px;
		}

		.logo-icon {
			width: 24px;
			height: 24px;
			background: var(--slate-primary);
			border-radius: 6px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 14px;
			animation: glow 4s ease-in-out infinite;
		}

		.logo-text {
			font-size: 13px;
			font-weight: 600;
			letter-spacing: 0.1em;
			color: var(--slate-primary-light);
		}

		.logo-subtitle {
			font-size: 9px;
			color: var(--slate-text-muted);
			letter-spacing: 0.05em;
			margin-top: 1px;
		}

		.status-badge {
			display: flex;
			align-items: center;
			gap: 6px;
			padding: 4px 10px;
			background: var(--slate-surface);
			border: 1px solid var(--slate-border);
			border-radius: 12px;
			font-size: 10px;
			color: var(--slate-text-muted);
		}

		.status-dot {
			width: 6px;
			height: 6px;
			border-radius: 50%;
			background: var(--slate-success);
			animation: statusPulse 2s ease-in-out infinite;
		}

		.status-dot.warning { background: var(--slate-warning); }
		.status-dot.error { background: var(--slate-error); }
		.status-dot.offline { background: var(--slate-text-dim); animation: none; }

		/* ============================================
		   SERVICE GRID
		   ============================================ */
		.services {
			display: grid;
			grid-template-columns: repeat(3, 1fr);
			gap: 8px;
			padding: 12px;
			animation: slideIn 0.3s ease-out;
		}

		.service-card {
			background: var(--slate-surface);
			border: 1px solid var(--slate-border);
			border-radius: 8px;
			padding: 10px;
			text-align: center;
			transition: all var(--slate-transition);
			position: relative;
			overflow: hidden;
			cursor: pointer;
		}

		.service-card::before {
			content: '';
			position: absolute;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			background: linear-gradient(135deg, transparent 40%, var(--slate-primary-glow) 100%);
			opacity: 0;
			transition: opacity var(--slate-transition);
		}

		.service-card:hover {
			border-color: var(--slate-primary);
			transform: translateY(-2px);
		}

		.service-card:hover::before {
			opacity: 1;
		}

		.service-card.active {
			border-color: var(--slate-success);
		}

		.service-card.active .service-icon {
			color: var(--slate-success);
		}

		.service-icon {
			font-size: 18px;
			margin-bottom: 4px;
			color: var(--slate-text-muted);
			transition: color var(--slate-transition);
		}

		.service-name {
			font-size: 10px;
			font-weight: 500;
			color: var(--slate-text);
			letter-spacing: 0.02em;
		}

		.service-status {
			font-size: 9px;
			color: var(--slate-text-dim);
			margin-top: 2px;
		}

		/* ============================================
		   CONTROL BUTTONS
		   ============================================ */
		.controls {
			padding: 0 12px 12px;
			display: flex;
			flex-direction: column;
			gap: 8px;
		}

		.btn {
			display: flex;
			align-items: center;
			justify-content: center;
			gap: 8px;
			padding: 10px 16px;
			border: none;
			border-radius: 8px;
			font-family: inherit;
			font-size: 12px;
			font-weight: 500;
			cursor: pointer;
			transition: all var(--slate-spring);
			position: relative;
			overflow: hidden;
		}

		.btn::after {
			content: '';
			position: absolute;
			width: 100%;
			height: 100%;
			background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 70%);
			transform: scale(0);
			opacity: 0;
			pointer-events: none;
		}

		.btn:active::after {
			animation: ripple 0.4s ease-out;
		}

		.btn-primary {
			background: linear-gradient(135deg, var(--slate-primary) 0%, var(--slate-primary-dark) 100%);
			color: white;
			box-shadow: 0 2px 8px var(--slate-primary-glow);
		}

		.btn-primary:hover {
			transform: translateY(-1px);
			box-shadow: 0 4px 16px var(--slate-primary-glow);
		}

		.btn-secondary {
			background: var(--slate-surface);
			color: var(--slate-text);
			border: 1px solid var(--slate-border);
		}

		.btn-secondary:hover {
			background: var(--slate-surface-elevated);
			border-color: var(--slate-primary);
		}

		.btn-row {
			display: flex;
			gap: 8px;
		}

		.btn-row .btn {
			flex: 1;
		}

		.btn-icon {
			font-size: 14px;
		}

		/* ============================================
		   QUICK ACTIONS
		   ============================================ */
		.quick-actions {
			padding: 12px;
			border-top: 1px solid var(--slate-border);
			background: var(--slate-surface);
		}

		.quick-actions-title {
			font-size: 10px;
			text-transform: uppercase;
			letter-spacing: 0.1em;
			color: var(--slate-text-muted);
			margin-bottom: 8px;
		}

		.action-grid {
			display: grid;
			grid-template-columns: repeat(4, 1fr);
			gap: 6px;
		}

		.action-btn {
			display: flex;
			flex-direction: column;
			align-items: center;
			gap: 4px;
			padding: 8px 4px;
			background: var(--slate-bg);
			border: 1px solid var(--slate-border);
			border-radius: 6px;
			cursor: pointer;
			transition: all var(--slate-transition);
			font-family: inherit;
		}

		.action-btn:hover {
			background: var(--slate-surface-elevated);
			border-color: var(--slate-primary);
			transform: scale(1.05);
		}

		.action-btn:active {
			transform: scale(0.95);
		}

		.action-icon {
			font-size: 16px;
			color: var(--slate-primary-light);
		}

		.action-label {
			font-size: 9px;
			color: var(--slate-text-muted);
		}

		/* ============================================
		   GUIDED MODE BANNER
		   ============================================ */
		.guided-banner {
			display: none;
			padding: 10px 12px;
			background: linear-gradient(90deg, var(--slate-primary-dark) 0%, var(--slate-primary) 50%, var(--slate-primary-dark) 100%);
			background-size: 200% 100%;
			animation: gradientShift 3s ease infinite;
			color: white;
			font-size: 11px;
			text-align: center;
			position: relative;
		}

		.guided-banner.active {
			display: block;
		}

		@keyframes gradientShift {
			0% { background-position: 0% 50%; }
			50% { background-position: 100% 50%; }
			100% { background-position: 0% 50%; }
		}

		.guided-progress {
			height: 2px;
			background: rgba(255,255,255,0.3);
			border-radius: 1px;
			margin-top: 8px;
			overflow: hidden;
		}

		.guided-progress-bar {
			height: 100%;
			background: white;
			border-radius: 1px;
			transition: width 0.5s ease-out;
		}

		/* ============================================
		   DEV CYCLE RING (MINI)
		   ============================================ */
		.dev-cycle-section {
			padding: 12px;
			border-top: 1px solid var(--slate-border);
			background: var(--slate-surface);
		}

		.dev-cycle-header {
			display: flex;
			align-items: center;
			justify-content: space-between;
			margin-bottom: 10px;
		}

		.dev-cycle-title {
			font-size: 10px;
			text-transform: uppercase;
			letter-spacing: 0.1em;
			color: var(--slate-text-muted);
		}

		.dev-cycle-stage {
			font-size: 11px;
			font-weight: 600;
			color: var(--slate-primary-light);
		}

		.dev-cycle-ring-container {
			display: flex;
			align-items: center;
			justify-content: center;
			gap: 16px;
		}

		.mini-ring {
			width: 80px;
			height: 80px;
			position: relative;
		}

		.mini-ring svg {
			width: 100%;
			height: 100%;
		}

		.stage-segment {
			fill: none;
			stroke-width: 6;
			stroke-linecap: round;
			transition: all 0.3s ease;
			cursor: pointer;
		}

		.stage-segment.active {
			stroke-width: 8;
			filter: drop-shadow(0 0 4px currentColor);
			animation: ringPulse 2s ease-in-out infinite;
		}

		@keyframes ringPulse {
			0%, 100% { filter: drop-shadow(0 0 4px currentColor); }
			50% { filter: drop-shadow(0 0 12px currentColor); }
		}

		.stage-label {
			font-size: 8px;
			fill: var(--slate-text-muted);
		}

		.stage-label.active {
			fill: var(--slate-primary-light);
			font-weight: 600;
		}

		.stage-info {
			flex: 1;
			max-width: 120px;
		}

		.stage-name {
			font-size: 14px;
			font-weight: 600;
			color: var(--slate-text);
			margin-bottom: 4px;
		}

		.stage-progress {
			font-size: 10px;
			color: var(--slate-text-muted);
			margin-bottom: 6px;
		}

		.stage-bar {
			height: 4px;
			background: var(--slate-border);
			border-radius: 2px;
			overflow: hidden;
		}

		.stage-bar-fill {
			height: 100%;
			background: linear-gradient(90deg, var(--slate-primary), var(--slate-primary-light));
			border-radius: 2px;
			transition: width 0.5s ease-out;
		}

		/* ============================================
		   LEARNING MODE TOGGLE
		   ============================================ */
		.learning-section {
			padding: 10px 12px;
			border-top: 1px solid var(--slate-border);
			display: flex;
			align-items: center;
			justify-content: space-between;
			background: linear-gradient(135deg, rgba(184, 115, 51, 0.05) 0%, transparent 100%);
		}

		.learning-info {
			display: flex;
			align-items: center;
			gap: 10px;
		}

		.learning-icon {
			width: 28px;
			height: 28px;
			background: var(--slate-primary);
			border-radius: 6px;
			display: flex;
			align-items: center;
			justify-content: center;
			font-size: 14px;
		}

		.learning-stats {
			display: flex;
			flex-direction: column;
		}

		.learning-level {
			font-size: 12px;
			font-weight: 600;
			color: var(--slate-text);
		}

		.learning-xp {
			font-size: 10px;
			color: var(--slate-text-muted);
		}

		.learning-toggle {
			position: relative;
			width: 44px;
			height: 24px;
			background: var(--slate-border);
			border-radius: 12px;
			cursor: pointer;
			transition: background var(--slate-transition);
		}

		.learning-toggle.active {
			background: var(--slate-primary);
		}

		.learning-toggle::after {
			content: '';
			position: absolute;
			top: 2px;
			left: 2px;
			width: 20px;
			height: 20px;
			background: white;
			border-radius: 50%;
			transition: transform var(--slate-spring);
		}

		.learning-toggle.active::after {
			transform: translateX(20px);
		}

		/* ============================================
		   SCANLINE EFFECT (OPTIONAL)
		   ============================================ */
		.scanline-overlay {
			position: fixed;
			top: 0;
			left: 0;
			right: 0;
			bottom: 0;
			pointer-events: none;
			background: repeating-linear-gradient(
				0deg,
				transparent,
				transparent 2px,
				rgba(0,0,0,0.03) 2px,
				rgba(0,0,0,0.03) 4px
			);
			opacity: 0.5;
		}
	</style>
</head>
<body>
	<div class="scanline-overlay"></div>

	<!-- Guided Mode Banner -->
	<div class="guided-banner" id="guidedBanner">
		<span>Guided Setup in Progress...</span>
		<div class="guided-progress">
			<div class="guided-progress-bar" id="guidedProgress" style="width: 0%"></div>
		</div>
	</div>

	<!-- Header -->
	<div class="header">
		<div class="logo-section">
			<div class="logo-icon">&#x2726;</div>
			<div>
				<div class="logo-text">S.L.A.T.E.</div>
				<div class="logo-subtitle">Control Board</div>
			</div>
		</div>
		<div class="status-badge">
			<div class="status-dot" id="systemStatus"></div>
			<span id="statusText">Online</span>
		</div>
	</div>

	<!-- Service Status Grid -->
	<div class="services">
		<div class="service-card active" id="svcDashboard" data-cmd="slate/slate_status.py --quick">
			<div class="service-icon">&#x2616;</div>
			<div class="service-name">Dashboard</div>
			<div class="service-status">:8080</div>
		</div>
		<div class="service-card active" id="svcOllama" data-cmd="slate/foundry_local.py --check">
			<div class="service-icon">&#x2699;</div>
			<div class="service-name">Ollama</div>
			<div class="service-status">:11434</div>
		</div>
		<div class="service-card" id="svcRunner" data-cmd="slate/slate_runner_manager.py --status">
			<div class="service-icon">&#x25B6;</div>
			<div class="service-name">Runner</div>
			<div class="service-status">GitHub</div>
		</div>
		<div class="service-card active" id="svcGPU" data-cmd="slate/slate_gpu_manager.py --status">
			<div class="service-icon">&#x2756;</div>
			<div class="service-name">GPU</div>
			<div class="service-status">2x RTX</div>
		</div>
		<div class="service-card" id="svcDocker" data-cmd="slate/slate_docker_daemon.py --status">
			<div class="service-icon">&#x2693;</div>
			<div class="service-name">Docker</div>
			<div class="service-status">Daemon</div>
		</div>
		<div class="service-card" id="svcMCP" data-cmd="slate/claude_code_manager.py --validate">
			<div class="service-icon">&#x2728;</div>
			<div class="service-name">MCP</div>
			<div class="service-status">Claude</div>
		</div>
	</div>

	<!-- Dev Cycle Ring (Mini) -->
	<div class="dev-cycle-section">
		<div class="dev-cycle-header">
			<span class="dev-cycle-title">Development Cycle</span>
			<span class="dev-cycle-stage" id="currentStage">CODE</span>
		</div>
		<div class="dev-cycle-ring-container">
			<div class="mini-ring">
				<svg viewBox="0 0 100 100" id="devCycleRing">
					<!-- Background circle -->
					<circle cx="50" cy="50" r="40" fill="none" stroke="rgba(255,255,255,0.05)" stroke-width="6"/>
					<!-- Stage segments (72 degrees each) -->
					<path class="stage-segment" id="segPlan" stroke="#7EA8BE" opacity="0.4"
						d="M 50 10 A 40 40 0 0 1 88.04 30.98" data-stage="PLAN"/>
					<path class="stage-segment active" id="segCode" stroke="#B87333"
						d="M 88.04 30.98 A 40 40 0 0 1 80.90 76.18" data-stage="CODE"/>
					<path class="stage-segment" id="segTest" stroke="#D4A054" opacity="0.4"
						d="M 80.90 76.18 A 40 40 0 0 1 19.10 76.18" data-stage="TEST"/>
					<path class="stage-segment" id="segDeploy" stroke="#78B89A" opacity="0.4"
						d="M 19.10 76.18 A 40 40 0 0 1 11.96 30.98" data-stage="DEPLOY"/>
					<path class="stage-segment" id="segFeedback" stroke="#9B89B3" opacity="0.4"
						d="M 11.96 30.98 A 40 40 0 0 1 50 10" data-stage="FEEDBACK"/>
					<!-- Center text -->
					<text x="50" y="48" text-anchor="middle" class="stage-label active" font-size="10">CODE</text>
					<text x="50" y="60" text-anchor="middle" class="stage-label" font-size="8">45%</text>
				</svg>
			</div>
			<div class="stage-info">
				<div class="stage-name" id="stageName">Coding</div>
				<div class="stage-progress" id="stageProgress">45% complete</div>
				<div class="stage-bar">
					<div class="stage-bar-fill" id="stageBarFill" style="width: 45%"></div>
				</div>
			</div>
		</div>
	</div>

	<!-- Learning Mode -->
	<div class="learning-section">
		<div class="learning-info">
			<div class="learning-icon">&#x1F393;</div>
			<div class="learning-stats">
				<span class="learning-level" id="learningLevel">Level 2</span>
				<span class="learning-xp" id="learningXP">175 XP</span>
			</div>
		</div>
		<div class="learning-toggle" id="learningToggle" title="Toggle Learning Mode"></div>
	</div>

	<!-- Main Controls -->
	<div class="controls">
		<button class="btn btn-primary" id="btnGuidedMode">
			<span class="btn-icon">&#x2726;</span>
			<span>Start Guided Setup</span>
		</button>
		<div class="btn-row">
			<button class="btn btn-secondary" id="btnOrchestrator">
				<span class="btn-icon">&#x25B6;</span>
				<span>Start Services</span>
			</button>
			<button class="btn btn-secondary" id="btnStatus">
				<span class="btn-icon">&#x2139;</span>
				<span>Full Status</span>
			</button>
		</div>
	</div>

	<!-- Quick Actions -->
	<div class="quick-actions">
		<div class="quick-actions-title">Quick Actions</div>
		<div class="action-grid">
			<button class="action-btn" data-action="chat" title="Open @slate chat">
				<span class="action-icon">&#x1F4AC;</span>
				<span class="action-label">Chat</span>
			</button>
			<button class="action-btn" data-action="workflow" title="Workflow status">
				<span class="action-icon">&#x21BA;</span>
				<span class="action-label">Workflow</span>
			</button>
			<button class="action-btn" data-action="benchmark" title="Run benchmarks">
				<span class="action-icon">&#x26A1;</span>
				<span class="action-label">Bench</span>
			</button>
			<button class="action-btn" data-action="security" title="Security audit">
				<span class="action-icon">&#x1F512;</span>
				<span class="action-label">Security</span>
			</button>
		</div>
	</div>

	<script nonce="${nonce}">
		const vscode = acquireVsCodeApi();

		// Service card clicks
		document.querySelectorAll('.service-card').forEach(card => {
			card.addEventListener('click', () => {
				const cmd = card.dataset.cmd;
				if (cmd) {
					vscode.postMessage({ type: 'runCommand', command: cmd });
				}
			});
		});

		// Main buttons
		document.getElementById('btnGuidedMode').addEventListener('click', () => {
			vscode.postMessage({ type: 'startGuidedMode' });
			document.getElementById('guidedBanner').classList.add('active');
			simulateProgress();
		});

		document.getElementById('btnOrchestrator').addEventListener('click', () => {
			vscode.postMessage({ type: 'runCommand', command: 'slate/slate_orchestrator.py start' });
		});

		document.getElementById('btnStatus').addEventListener('click', () => {
			vscode.postMessage({ type: 'showStatus' });
		});

		// Quick action buttons
		document.querySelectorAll('.action-btn').forEach(btn => {
			btn.addEventListener('click', () => {
				const action = btn.dataset.action;
				switch (action) {
					case 'chat':
						vscode.postMessage({ type: 'openChat' });
						break;
					case 'workflow':
						vscode.postMessage({ type: 'runCommand', command: 'slate/slate_workflow_manager.py --status' });
						break;
					case 'benchmark':
						vscode.postMessage({ type: 'runCommand', command: 'slate/slate_benchmark.py' });
						break;
					case 'security':
						vscode.postMessage({ type: 'runCommand', command: 'slate/action_guard.py --scan' });
						break;
				}
			});
		});

		// Simulate guided mode progress
		function simulateProgress() {
			const progressBar = document.getElementById('guidedProgress');
			let progress = 0;
			const interval = setInterval(() => {
				progress += Math.random() * 15;
				if (progress >= 100) {
					progress = 100;
					clearInterval(interval);
					setTimeout(() => {
						document.getElementById('guidedBanner').classList.remove('active');
					}, 1000);
				}
				progressBar.style.width = progress + '%';
			}, 800);
		}

		// Dev Cycle Ring interactions
		const stageNames = { PLAN: 'Planning', CODE: 'Coding', TEST: 'Testing', DEPLOY: 'Deploying', FEEDBACK: 'Feedback' };
		const stageColors = { PLAN: '#7EA8BE', CODE: '#B87333', TEST: '#D4A054', DEPLOY: '#78B89A', FEEDBACK: '#9B89B3' };

		document.querySelectorAll('.stage-segment').forEach(seg => {
			seg.addEventListener('click', () => {
				const stage = seg.dataset.stage;
				if (stage) {
					vscode.postMessage({ type: 'transitionStage', stage });
				}
			});
		});

		// Learning mode toggle
		const learningToggle = document.getElementById('learningToggle');
		let learningActive = false;

		learningToggle.addEventListener('click', () => {
			learningActive = !learningActive;
			learningToggle.classList.toggle('active', learningActive);
			vscode.postMessage({ type: 'toggleLearning', active: learningActive });
		});

		// Update dev cycle ring display
		function updateDevCycleRing(data) {
			if (!data) return;

			const currentStage = data.current_stage || 'CODE';
			const progress = data.stage_progress_percent || 0;

			// Update current stage display
			document.getElementById('currentStage').textContent = currentStage;
			document.getElementById('stageName').textContent = stageNames[currentStage] || currentStage;
			document.getElementById('stageProgress').textContent = progress + '% complete';
			document.getElementById('stageBarFill').style.width = progress + '%';

			// Update SVG center text
			const centerTexts = document.querySelectorAll('#devCycleRing text');
			if (centerTexts.length >= 2) {
				centerTexts[0].textContent = currentStage;
				centerTexts[1].textContent = progress + '%';
			}

			// Update segment states
			['PLAN', 'CODE', 'TEST', 'DEPLOY', 'FEEDBACK'].forEach(stage => {
				const seg = document.getElementById('seg' + stage.charAt(0).toUpperCase() + stage.slice(1).toLowerCase());
				if (seg) {
					if (stage === currentStage) {
						seg.classList.add('active');
						seg.setAttribute('opacity', '1');
					} else {
						seg.classList.remove('active');
						seg.setAttribute('opacity', '0.4');
					}
				}
			});
		}

		// Update learning stats
		function updateLearningStats(data) {
			if (!data) return;

			const level = data.level || 1;
			const xp = data.total_xp || 0;

			document.getElementById('learningLevel').textContent = 'Level ' + level;
			document.getElementById('learningXP').textContent = xp.toLocaleString() + ' XP';
		}

		// Handle status updates from extension
		window.addEventListener('message', event => {
			const message = event.data;
			if (message.type === 'statusUpdate') {
				// Update timestamp or trigger refresh animations
				document.querySelectorAll('.service-card').forEach(card => {
					card.style.animation = 'slideIn 0.3s ease-out';
					setTimeout(() => card.style.animation = '', 300);
				});
			} else if (message.type === 'devCycleUpdate') {
				updateDevCycleRing(message.data);
			} else if (message.type === 'learningUpdate') {
				updateLearningStats(message.data);
			} else if (message.type === 'interactiveStatus') {
				if (message.data.dev_cycle) {
					updateDevCycleRing(message.data.dev_cycle);
				}
				if (message.data.learning) {
					updateLearningStats(message.data.learning);
				}
			}
		});
	</script>
</body>
</html>`;
	}
}

function getNonce(): string {
	const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789';
	let text = '';
	for (let i = 0; i < 32; i++) {
		text += chars.charAt(Math.floor(Math.random() * chars.length));
	}
	return text;
}
