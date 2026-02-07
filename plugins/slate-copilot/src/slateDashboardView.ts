// Modified: 2026-02-07T05:50:00Z | Author: COPILOT | Change: Add sidebar webview for SLATE dashboard on 127.0.0.1:8080
import * as vscode from 'vscode';

const DASHBOARD_URL = 'http://127.0.0.1:8080';

/**
 * WebviewViewProvider for the SLATE Dashboard sidebar panel.
 * Embeds the FastAPI dashboard (127.0.0.1:8080) in an iframe inside
 * the VS Code activity-bar view container.
 */
export class SlateDashboardViewProvider implements vscode.WebviewViewProvider {
	public static readonly viewType = 'slate.dashboardView';

	private _view?: vscode.WebviewView;

	constructor(private readonly _extensionUri: vscode.Uri) {}

	public resolveWebviewView(
		webviewView: vscode.WebviewView,
		_context: vscode.WebviewViewResolveContext,
		_token: vscode.CancellationToken,
	): void {
		this._view = webviewView;

		webviewView.webview.options = {
			enableScripts: true,
		};

		webviewView.webview.html = this._getHtml(webviewView.webview);

		webviewView.webview.onDidReceiveMessage((message) => {
			if (message?.type === 'openExternal') {
				void vscode.env.openExternal(vscode.Uri.parse(DASHBOARD_URL));
			} else if (message?.type === 'refresh') {
				webviewView.webview.html = this._getHtml(webviewView.webview);
			} else if (message?.type === 'openPanel') {
				void vscode.commands.executeCommand('slate.openDashboard');
			}
		});
	}

	/** Refresh the webview content */
	public refresh(): void {
		if (this._view) {
			this._view.webview.html = this._getHtml(this._view.webview);
		}
	}

	private _getHtml(webview: vscode.Webview): string {
		const nonce = getNonce();
		const csp = [
			"default-src 'none'",
			`frame-src ${DASHBOARD_URL}`,
			`img-src ${DASHBOARD_URL} data:`,
			"style-src 'unsafe-inline'",
			`script-src 'nonce-${nonce}'`,
		].join('; ');

		return /* html */ `<!DOCTYPE html>
<html lang="en">
<head>
	<meta charset="UTF-8" />
	<meta name="viewport" content="width=device-width, initial-scale=1.0" />
	<meta http-equiv="Content-Security-Policy" content="${csp}" />
	<title>SLATE Dashboard</title>
	<style>
		* { margin: 0; padding: 0; box-sizing: border-box; }
		html, body {
			height: 100%;
			width: 100%;
			background: var(--vscode-sideBar-background, #0d1117);
			color: var(--vscode-sideBar-foreground, #e5e7eb);
			font-family: var(--vscode-font-family, "Segoe UI", sans-serif);
			font-size: var(--vscode-font-size, 13px);
		}
		.toolbar {
			display: flex;
			align-items: center;
			justify-content: space-between;
			padding: 6px 10px;
			border-bottom: 1px solid var(--vscode-sideBarSectionHeader-border, #1f2937);
			background: var(--vscode-sideBarSectionHeader-background, #0f1115);
		}
		.title {
			font-size: 11px;
			letter-spacing: 0.04em;
			text-transform: uppercase;
			color: var(--vscode-sideBarSectionHeader-foreground, #9ca3af);
		}
		.actions {
			display: flex;
			gap: 4px;
		}
		button {
			background: var(--vscode-button-secondaryBackground, #1f2937);
			color: var(--vscode-button-secondaryForeground, #e5e7eb);
			border: 1px solid var(--vscode-button-border, #374151);
			border-radius: 4px;
			padding: 3px 8px;
			cursor: pointer;
			font-size: 11px;
			font-family: inherit;
		}
		button:hover {
			background: var(--vscode-button-secondaryHoverBackground, #374151);
		}
		button:focus-visible {
			outline: 2px solid var(--vscode-focusBorder, #58a6ff);
			outline-offset: 1px;
		}
		.frame {
			height: calc(100% - 34px);
			width: 100%;
			border: none;
		}
		.offline {
			display: none;
			flex-direction: column;
			align-items: center;
			justify-content: center;
			height: calc(100% - 34px);
			gap: 12px;
			text-align: center;
			padding: 16px;
		}
		.offline-icon {
			font-size: 28px;
			opacity: 0.5;
		}
		.offline-msg {
			font-size: 12px;
			color: var(--vscode-descriptionForeground, #8b949e);
			line-height: 1.5;
		}
		.offline .start-btn {
			background: var(--vscode-button-background, #238636);
			color: var(--vscode-button-foreground, #fff);
			border: none;
			padding: 6px 14px;
			font-size: 12px;
			border-radius: 6px;
		}
		.offline .start-btn:hover {
			background: var(--vscode-button-hoverBackground, #2ea043);
		}
	</style>
</head>
<body>
	<div class="toolbar">
		<span class="title">Dashboard</span>
		<div class="actions">
			<button id="btnRefresh" title="Refresh">&#x21BB;</button>
			<button id="btnExpand" title="Open in editor panel">&#x2197;</button>
			<button id="btnExternal" title="Open in browser">&#x2750;</button>
		</div>
	</div>
	<iframe class="frame" id="dashFrame" src="${DASHBOARD_URL}" title="SLATE Dashboard"></iframe>
	<div class="offline" id="offlineMsg">
		<div class="offline-icon">&#x26A0;</div>
		<div class="offline-msg">
			Dashboard server is not running.<br/>
			Start it with <strong>SLATE: Dashboard</strong> task<br/>
			or run: <code>python agents/slate_dashboard_server.py</code>
		</div>
		<button class="start-btn" id="btnRetry">Retry Connection</button>
	</div>
	<script nonce="${nonce}">
		const vscode = acquireVsCodeApi();
		const frame = document.getElementById('dashFrame');
		const offline = document.getElementById('offlineMsg');

		// Detect iframe load failure
		let loaded = false;
		frame.addEventListener('load', () => { loaded = true; });
		setTimeout(() => {
			if (!loaded) {
				frame.style.display = 'none';
				offline.style.display = 'flex';
			}
		}, 4000);

		document.getElementById('btnRefresh').addEventListener('click', () => {
			vscode.postMessage({ type: 'refresh' });
		});
		document.getElementById('btnExpand').addEventListener('click', () => {
			vscode.postMessage({ type: 'openPanel' });
		});
		document.getElementById('btnExternal').addEventListener('click', () => {
			vscode.postMessage({ type: 'openExternal' });
		});
		document.getElementById('btnRetry').addEventListener('click', () => {
			vscode.postMessage({ type: 'refresh' });
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
