// Modified: 2026-02-07T23:00:00Z | Author: COPILOT | Change: Add DiagnosticCollection for SLATE security scans — publishes findings to VS Code Problems panel
import * as vscode from 'vscode';
import { execSlateCommand } from './slateRunner';

/**
 * SLATE Diagnostics Provider
 *
 * Integrates SLATE security scans (ActionGuard, PII Scanner, SDK Source Guard)
 * with the VS Code Problems panel via DiagnosticCollection. This lets developers
 * see security findings inline in their editor with squiggly underlines and
 * navigate directly to the problematic lines.
 *
 * Also watches for file saves to re-scan automatically.
 */

const SCAN_DEBOUNCE_MS = 3000;

export class SlateDiagnosticsProvider implements vscode.Disposable {
	private readonly _diagnosticCollection: vscode.DiagnosticCollection;
	private readonly _disposables: vscode.Disposable[] = [];
	private _scanTimer: NodeJS.Timeout | undefined;
	private _scanning = false;

	constructor() {
		this._diagnosticCollection = vscode.languages.createDiagnosticCollection('slate');
	}

	/**
	 * Start watching for file changes and run initial scan.
	 */
	public activate(context: vscode.ExtensionContext): void {
		// Watch for Python/YAML/JSON file saves in the workspace
		const watcher = vscode.workspace.onDidSaveTextDocument((doc) => {
			const ext = doc.uri.fsPath.split('.').pop()?.toLowerCase();
			if (['py', 'yml', 'yaml', 'json', 'ts', 'js'].includes(ext ?? '')) {
				this._debounceScan();
			}
		});
		this._disposables.push(watcher);

		// Register manual scan command
		this._disposables.push(
			vscode.commands.registerCommand('slate.scanDiagnostics', () => this.runFullScan())
		);

		// Register clear command
		this._disposables.push(
			vscode.commands.registerCommand('slate.clearDiagnostics', () => {
				this._diagnosticCollection.clear();
				vscode.window.showInformationMessage('SLATE diagnostics cleared.');
			})
		);

		context.subscriptions.push(this);

		// Initial scan on activation (non-blocking)
		setTimeout(() => this.runFullScan(), 5000);
	}

	/**
	 * Run all three SLATE security scans and publish diagnostics.
	 */
	public async runFullScan(): Promise<void> {
		if (this._scanning) { return; }
		this._scanning = true;

		try {
			const token = new vscode.CancellationTokenSource().token;
			const diagnosticsMap = new Map<string, vscode.Diagnostic[]>();

			// Run ActionGuard scan
			try {
				const agOutput = await execSlateCommand('slate/action_guard.py --scan --json', token);
				this._parseActionGuardOutput(agOutput, diagnosticsMap);
			} catch { /* scan failed — skip */ }

			// Run PII scan
			try {
				const piiOutput = await execSlateCommand('slate/pii_scanner.py --scan --json', token);
				this._parsePiiOutput(piiOutput, diagnosticsMap);
			} catch { /* scan failed — skip */ }

			// Run SDK Source Guard scan
			try {
				const sdkOutput = await execSlateCommand('slate/sdk_source_guard.py --check --json', token);
				this._parseSdkOutput(sdkOutput, diagnosticsMap);
			} catch { /* scan failed — skip */ }

			// Publish all diagnostics
			this._diagnosticCollection.clear();
			for (const [filePath, diags] of diagnosticsMap) {
				this._diagnosticCollection.set(vscode.Uri.file(filePath), diags);
			}
		} finally {
			this._scanning = false;
		}
	}

	private _debounceScan(): void {
		if (this._scanTimer) { clearTimeout(this._scanTimer); }
		this._scanTimer = setTimeout(() => this.runFullScan(), SCAN_DEBOUNCE_MS);
	}

	/**
	 * Parse ActionGuard JSON output into diagnostics.
	 * Expected format: { "findings": [{ "file": "...", "line": N, "pattern": "...", "severity": "..." }] }
	 */
	private _parseActionGuardOutput(output: string, map: Map<string, vscode.Diagnostic[]>): void {
		try {
			const data = JSON.parse(output);
			const findings = data.findings ?? data.violations ?? [];
			for (const f of findings) {
				if (!f.file) { continue; }
				const line = Math.max(0, (f.line ?? 1) - 1);
				const severity = f.severity === 'error'
					? vscode.DiagnosticSeverity.Error
					: f.severity === 'warning'
						? vscode.DiagnosticSeverity.Warning
						: vscode.DiagnosticSeverity.Information;

				const diag = new vscode.Diagnostic(
					new vscode.Range(line, 0, line, 200),
					`[ActionGuard] ${f.pattern ?? f.message ?? 'Blocked pattern detected'}`,
					severity
				);
				diag.source = 'SLATE Security';
				diag.code = 'action-guard';

				const filePath = f.file;
				if (!map.has(filePath)) { map.set(filePath, []); }
				map.get(filePath)!.push(diag);
			}
		} catch {
			// Non-JSON output — try line-by-line parsing
			this._parseLineOutput(output, 'ActionGuard', 'action-guard', map);
		}
	}

	/**
	 * Parse PII Scanner output into diagnostics.
	 */
	private _parsePiiOutput(output: string, map: Map<string, vscode.Diagnostic[]>): void {
		try {
			const data = JSON.parse(output);
			const findings = data.findings ?? data.detections ?? [];
			for (const f of findings) {
				if (!f.file) { continue; }
				const line = Math.max(0, (f.line ?? 1) - 1);
				const diag = new vscode.Diagnostic(
					new vscode.Range(line, 0, line, 200),
					`[PII] ${f.type ?? 'Potential PII'}: ${f.message ?? f.pattern ?? 'Sensitive data detected'}`,
					vscode.DiagnosticSeverity.Warning
				);
				diag.source = 'SLATE Security';
				diag.code = 'pii-detected';

				const filePath = f.file;
				if (!map.has(filePath)) { map.set(filePath, []); }
				map.get(filePath)!.push(diag);
			}
		} catch {
			this._parseLineOutput(output, 'PII Scanner', 'pii-detected', map);
		}
	}

	/**
	 * Parse SDK Source Guard output into diagnostics.
	 */
	private _parseSdkOutput(output: string, map: Map<string, vscode.Diagnostic[]>): void {
		try {
			const data = JSON.parse(output);
			const findings = data.findings ?? data.violations ?? [];
			for (const f of findings) {
				if (!f.file) { continue; }
				const line = Math.max(0, (f.line ?? 1) - 1);
				const diag = new vscode.Diagnostic(
					new vscode.Range(line, 0, line, 200),
					`[SDK Guard] ${f.package ?? f.message ?? 'Untrusted package source'}`,
					vscode.DiagnosticSeverity.Warning
				);
				diag.source = 'SLATE Security';
				diag.code = 'sdk-source';

				const filePath = f.file;
				if (!map.has(filePath)) { map.set(filePath, []); }
				map.get(filePath)!.push(diag);
			}
		} catch {
			this._parseLineOutput(output, 'SDK Guard', 'sdk-source', map);
		}
	}

	/**
	 * Fallback: parse line-based output like "file.py:10: warning message"
	 */
	private _parseLineOutput(
		output: string,
		source: string,
		code: string,
		map: Map<string, vscode.Diagnostic[]>
	): void {
		const lineRegex = /^(.+?):(\d+):\s*(.+)$/gm;
		let match: RegExpExecArray | null;
		while ((match = lineRegex.exec(output)) !== null) {
			const [, file, lineStr, message] = match;
			const line = Math.max(0, parseInt(lineStr) - 1);
			const diag = new vscode.Diagnostic(
				new vscode.Range(line, 0, line, 200),
				`[${source}] ${message}`,
				vscode.DiagnosticSeverity.Warning
			);
			diag.source = 'SLATE Security';
			diag.code = code;

			if (!map.has(file)) { map.set(file, []); }
			map.get(file)!.push(diag);
		}
	}

	dispose(): void {
		this._diagnosticCollection.clear();
		this._diagnosticCollection.dispose();
		if (this._scanTimer) { clearTimeout(this._scanTimer); }
		for (const d of this._disposables) { d.dispose(); }
	}
}
