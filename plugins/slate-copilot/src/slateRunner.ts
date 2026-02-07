// Modified: 2026-02-07T02:00:00Z | Author: COPILOT | Change: SLATE Python command runner with cancellation support
import * as cp from 'child_process';
import * as vscode from 'vscode';
import { getSlateConfig } from './extension';

/**
 * Execute a SLATE Python command and return stdout.
 * Supports cancellation via CancellationToken.
 * All commands bind to 127.0.0.1 only (security rule).
 */
export function execSlateCommand(command: string, token: vscode.CancellationToken): Promise<string> {
	const config = getSlateConfig();

	return new Promise<string>((resolve, reject) => {
		// Security: block dangerous patterns
		const blocked = ['eval(', 'exec(os', 'rm -rf /', 'base64.b64decode', '0.0.0.0'];
		for (const pattern of blocked) {
			if (command.includes(pattern)) {
				reject(new Error(`Blocked command pattern: ${pattern}`));
				return;
			}
		}

		const proc = cp.spawn(config.pythonPath, command.split(' '), {
			cwd: config.workspacePath,
			env: {
				...process.env,
				PYTHONPATH: config.workspacePath,
				PYTHONIOENCODING: 'utf-8',
				CUDA_VISIBLE_DEVICES: '0,1',
				SLATE_WORKSPACE: config.workspacePath,
			},
			stdio: ['ignore', 'pipe', 'pipe'],
		});

		let stdout = '';
		let stderr = '';

		proc.stdout.on('data', (data: Buffer) => {
			stdout += data.toString('utf-8');
		});

		proc.stderr.on('data', (data: Buffer) => {
			stderr += data.toString('utf-8');
		});

		// Handle cancellation
		const disposable = token.onCancellationRequested(() => {
			proc.kill('SIGTERM');
			reject(new Error('Command cancelled'));
		});

		proc.on('close', (code) => {
			disposable.dispose();
			if (code === 0) {
				resolve(stdout.trim());
			} else {
				// Include stderr in output for diagnostics
				const output = stdout.trim() + (stderr ? `\n[stderr]: ${stderr.trim()}` : '');
				resolve(output || `Command exited with code ${code}`);
			}
		});

		proc.on('error', (err) => {
			disposable.dispose();
			reject(new Error(`Failed to run command: ${err.message}`));
		});

		// Timeout after 60 seconds
		setTimeout(() => {
			if (!proc.killed) {
				proc.kill('SIGTERM');
				resolve(stdout.trim() + '\n[timeout after 60s]');
			}
		}, 60_000);
	});
}
