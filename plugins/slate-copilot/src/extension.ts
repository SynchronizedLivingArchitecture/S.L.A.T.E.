// Modified: 2026-02-07T04:57:00Z | Author: COPILOT | Change: Remove hardcoded workspace fallback path
import * as vscode from 'vscode';
import { registerSlateParticipant } from './slateParticipant';
import { registerSlateTools } from './tools';

export function activate(context: vscode.ExtensionContext) {
	registerSlateTools(context);
	registerSlateParticipant(context);

	// Register the status command
	context.subscriptions.push(
		vscode.commands.registerCommand('slate.showStatus', async () => {
			const terminal = vscode.window.createTerminal('SLATE Status');
			terminal.show();
			terminal.sendText(`"${getSlateConfig().pythonPath}" slate/slate_status.py --quick`);
		})
	);
}

export function deactivate() { }

/** SLATE workspace configuration */
export interface SlateConfig {
	pythonPath: string;
	workspacePath: string;
}

/** Get SLATE configuration from workspace */
export function getSlateConfig(): SlateConfig {
	const workspaceFolders = vscode.workspace.workspaceFolders;
	const workspacePath = workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();

	return {
		pythonPath: `${workspacePath}\\.venv\\Scripts\\python.exe`,
		workspacePath,
	};
}
