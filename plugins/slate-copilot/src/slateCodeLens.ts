// Modified: 2026-02-07T23:00:00Z | Author: COPILOT | Change: Add CodeLens provider — inline SLATE actions on Python files (run test, check status, scan security)
import * as vscode from 'vscode';

/**
 * SLATE CodeLens Provider
 *
 * Adds inline action buttons (CodeLens) above key SLATE patterns:
 * - Test functions → "Run Test" / "Debug Test" buttons
 * - SLATE module imports → "Check Status" button
 * - Security-sensitive patterns → "Scan" button
 * - Modified timestamps → "Show History" button
 *
 * This creates a seamless developer experience where SLATE operations
 * are accessible directly from the code editor.
 */

export class SlateCodeLensProvider implements vscode.CodeLensProvider, vscode.Disposable {
	private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
	public readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;
	private _disposables: vscode.Disposable[] = [];

	public activate(context: vscode.ExtensionContext): void {
		// Register for Python files
		this._disposables.push(
			vscode.languages.registerCodeLensProvider(
				{ language: 'python', scheme: 'file' },
				this
			)
		);

		// Register for YAML workflow files
		this._disposables.push(
			vscode.languages.registerCodeLensProvider(
				{ language: 'yaml', pattern: '**/.github/workflows/*.yml' },
				this
			)
		);

		// Register CodeLens action commands
		this._disposables.push(
			vscode.commands.registerCommand('slate.codeLens.runTest', (testName: string, filePath: string) => {
				const terminal = vscode.window.createTerminal('SLATE Test');
				terminal.show();
				const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
				terminal.sendText(
					`"${workspacePath}\\.venv\\Scripts\\python.exe" -m pytest "${filePath}" -v -k "${testName}"`
				);
			})
		);

		this._disposables.push(
			vscode.commands.registerCommand('slate.codeLens.runModule', (module: string) => {
				const terminal = vscode.window.createTerminal('SLATE');
				terminal.show();
				const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
				terminal.sendText(`"${workspacePath}\\.venv\\Scripts\\python.exe" ${module} --status`);
			})
		);

		this._disposables.push(
			vscode.commands.registerCommand('slate.codeLens.scanFile', (filePath: string) => {
				const terminal = vscode.window.createTerminal('SLATE Security');
				terminal.show();
				const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
				terminal.sendText(
					`"${workspacePath}\\.venv\\Scripts\\python.exe" slate/action_guard.py --scan`
				);
			})
		);

		this._disposables.push(
			vscode.commands.registerCommand('slate.codeLens.dispatchWorkflow', (workflow: string) => {
				const terminal = vscode.window.createTerminal('SLATE CI');
				terminal.show();
				const workspacePath = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? '';
				terminal.sendText(
					`"${workspacePath}\\.venv\\Scripts\\python.exe" slate/slate_runner_manager.py --dispatch "${workflow}"`
				);
			})
		);

		// Trigger refresh on save
		this._disposables.push(
			vscode.workspace.onDidSaveTextDocument(() => {
				this._onDidChangeCodeLenses.fire();
			})
		);

		context.subscriptions.push(this);
	}

	provideCodeLenses(document: vscode.TextDocument, _token: vscode.CancellationToken): vscode.CodeLens[] {
		const lenses: vscode.CodeLens[] = [];
		const text = document.getText();
		const filePath = document.uri.fsPath;

		if (document.languageId === 'python') {
			this._addPythonLenses(document, text, filePath, lenses);
		} else if (document.languageId === 'yaml') {
			this._addWorkflowLenses(document, text, filePath, lenses);
		}

		return lenses;
	}

	private _addPythonLenses(
		document: vscode.TextDocument,
		text: string,
		filePath: string,
		lenses: vscode.CodeLens[]
	): void {
		// Test function detection
		const testFuncRegex = /^(def\s+(test_\w+))\s*\(/gm;
		let match: RegExpExecArray | null;
		while ((match = testFuncRegex.exec(text)) !== null) {
			const line = document.positionAt(match.index).line;
			const range = new vscode.Range(line, 0, line, 0);
			const testName = match[2];

			lenses.push(new vscode.CodeLens(range, {
				title: '$(play) Run Test',
				command: 'slate.codeLens.runTest',
				arguments: [testName, filePath],
				tooltip: `Run pytest: ${testName}`,
			}));
		}

		// Test class detection
		const testClassRegex = /^(class\s+(Test\w+))\s*[:(]/gm;
		while ((match = testClassRegex.exec(text)) !== null) {
			const line = document.positionAt(match.index).line;
			const range = new vscode.Range(line, 0, line, 0);
			const className = match[2];

			lenses.push(new vscode.CodeLens(range, {
				title: '$(testing-run-all-icon) Run Class Tests',
				command: 'slate.codeLens.runTest',
				arguments: [className, filePath],
				tooltip: `Run all tests in ${className}`,
			}));
		}

		// SLATE module detection — show status buttons on slate/ files
		if (filePath.includes('slate') && !filePath.includes('test_')) {
			const moduleMatch = filePath.match(/slate[/\\](\w+)\.py$/);
			if (moduleMatch) {
				const modulePath = `slate/${moduleMatch[1]}.py`;
				lenses.push(new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
					title: '$(info) Check Status',
					command: 'slate.codeLens.runModule',
					arguments: [modulePath],
					tooltip: `Run ${modulePath} --status`,
				}));
			}
		}

		// Security pattern detection
		const securityPatterns = [
			/\b(0\.0\.0\.0)\b/g,
			/\beval\s*\(/g,
			/\bexec\s*\(/g,
			/\bbase64\.b64decode\b/g,
		];
		for (const pattern of securityPatterns) {
			while ((match = pattern.exec(text)) !== null) {
				const line = document.positionAt(match.index).line;
				const range = new vscode.Range(line, 0, line, 0);

				lenses.push(new vscode.CodeLens(range, {
					title: '$(shield) Security Warning',
					command: 'slate.codeLens.scanFile',
					arguments: [filePath],
					tooltip: 'Potential security concern — click to scan',
				}));
			}
		}
	}

	private _addWorkflowLenses(
		document: vscode.TextDocument,
		text: string,
		filePath: string,
		lenses: vscode.CodeLens[]
	): void {
		// Detect workflow file name for dispatch button
		const workflowFile = filePath.split(/[/\\]/).pop() ?? '';

		// Add dispatch button at the top
		lenses.push(new vscode.CodeLens(new vscode.Range(0, 0, 0, 0), {
			title: '$(rocket) Dispatch Workflow',
			command: 'slate.codeLens.dispatchWorkflow',
			arguments: [workflowFile],
			tooltip: `Dispatch ${workflowFile} via GitHub Actions`,
		}));

		// Detect job definitions
		const jobRegex = /^\s{2}(\w[\w-]*):\s*$/gm;
		let match: RegExpExecArray | null;
		while ((match = jobRegex.exec(text)) !== null) {
			const line = document.positionAt(match.index).line;
			// Check if next lines contain "runs-on" (it's a job, not a field)
			const nextLines = text.slice(match.index, match.index + 200);
			if (nextLines.includes('runs-on')) {
				const range = new vscode.Range(line, 0, line, 0);
				lenses.push(new vscode.CodeLens(range, {
					title: `$(server) Job: ${match[1]}`,
					command: '',
					arguments: [],
					tooltip: `CI job definition: ${match[1]}`,
				}));
			}
		}
	}

	dispose(): void {
		this._onDidChangeCodeLenses.dispose();
		for (const d of this._disposables) { d.dispose(); }
	}
}
