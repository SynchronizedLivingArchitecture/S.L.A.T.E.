// Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Fix freezing — proper arg parsing, streaming progress, categorized timeouts, error recovery
import * as cp from 'child_process';
import * as vscode from 'vscode';
import { getSlateConfig } from './extension';

// ─── Timeout Categories ─────────────────────────────────────────────────
const TIMEOUT_QUICK = 30_000;    // 30s — status, detect, quick checks
const TIMEOUT_NORMAL = 90_000;   // 90s — most operations
const TIMEOUT_LONG = 300_000;    // 5m  — benchmarks, installs, multi-step
const TIMEOUT_INSTALL = 600_000; // 10m — full ecosystem install/update

/** Commands that need longer timeouts (substring match) */
const LONG_COMMANDS = [
	'slate_benchmark', '--benchmark', '--optimize', '--install-pytorch',
	'--build-all', '--index-now', '--train-now', '--run',
	'--sync-all',
];

const QUICK_COMMANDS = [
	'--quick', '--status', '--check', '--detect', '--json',
	'--discover', 'status',
];

/**
 * Parse a command string into args, respecting quoted strings.
 * e.g., 'slate/runner.py --dispatch "ci.yml"' → ['slate/runner.py', '--dispatch', 'ci.yml']
 */
function parseArgs(command: string): string[] {
	const args: string[] = [];
	let current = '';
	let inQuote: string | null = null;

	for (let i = 0; i < command.length; i++) {
		const ch = command[i];
		if (inQuote) {
			if (ch === inQuote) {
				inQuote = null;
			} else {
				current += ch;
			}
		} else if (ch === '"' || ch === "'") {
			inQuote = ch;
		} else if (ch === ' ' || ch === '\t') {
			if (current.length > 0) {
				args.push(current);
				current = '';
			}
		} else {
			current += ch;
		}
	}
	if (current.length > 0) {
		args.push(current);
	}
	return args;
}

/** Auto-detect timeout based on command content */
function detectTimeout(command: string): number {
	const cmdLower = command.toLowerCase();
	if (QUICK_COMMANDS.some(q => cmdLower.includes(q))) {
		return TIMEOUT_QUICK;
	}
	if (LONG_COMMANDS.some(q => cmdLower.includes(q))) {
		return TIMEOUT_LONG;
	}
	return TIMEOUT_NORMAL;
}

/**
 * Execute a SLATE Python command and return stdout.
 * Auto-detects appropriate timeout from command content.
 * Supports cancellation via CancellationToken.
 */
export function execSlateCommand(command: string, token: vscode.CancellationToken): Promise<string> {
	return _execCommand(command, token, detectTimeout(command));
}

/**
 * Execute a long-running SLATE command (install/update).
 * Timeout: 10 minutes.
 */
export function execSlateCommandLong(command: string, token: vscode.CancellationToken): Promise<string> {
	return _execCommand(command, token, TIMEOUT_INSTALL);
}

/**
 * Execute a SLATE command with a specific timeout override.
 */
export function execSlateCommandWithTimeout(command: string, token: vscode.CancellationToken, timeoutMs: number): Promise<string> {
	return _execCommand(command, token, timeoutMs);
}

function _execCommand(command: string, token: vscode.CancellationToken, timeoutMs: number): Promise<string> {
	const config = getSlateConfig();

	return new Promise<string>((resolve, reject) => {
		// Bail immediately if already cancelled
		if (token.isCancellationRequested) {
			reject(new Error('Command cancelled before start'));
			return;
		}

		// Security: block dangerous patterns
		const blocked = ['eval(', 'exec(os', 'rm -rf /', 'base64.b64decode', '0.0.0.0'];
		for (const pattern of blocked) {
			if (command.includes(pattern)) {
				reject(new Error(`Blocked command pattern: ${pattern}`));
				return;
			}
		}

		const args = parseArgs(command);
		const startTime = Date.now();

		let proc: cp.ChildProcess;
		try {
			proc = cp.spawn(config.pythonPath, args, {
				cwd: config.workspacePath,
				env: {
					...process.env,
					PYTHONPATH: config.workspacePath,
					PYTHONIOENCODING: 'utf-8',
					CUDA_VISIBLE_DEVICES: '0,1',
					SLATE_WORKSPACE: config.workspacePath,
				},
				stdio: ['ignore', 'pipe', 'pipe'],
				windowsHide: true,
			});
		} catch (spawnErr) {
			reject(new Error(`Failed to spawn process: ${spawnErr instanceof Error ? spawnErr.message : String(spawnErr)}`));
			return;
		}

		let stdout = '';
		let stderr = '';
		let settled = false;

		const settle = (value: string) => {
			if (!settled) {
				settled = true;
				disposable.dispose();
				clearTimeout(timer);
				resolve(value);
			}
		};

		const fail = (err: Error) => {
			if (!settled) {
				settled = true;
				disposable.dispose();
				clearTimeout(timer);
				reject(err);
			}
		};

		proc.stdout!.on('data', (data: Buffer) => {
			stdout += data.toString('utf-8');
		});

		proc.stderr!.on('data', (data: Buffer) => {
			stderr += data.toString('utf-8');
		});

		// Handle cancellation
		const disposable = token.onCancellationRequested(() => {
			if (!proc.killed) { proc.kill('SIGTERM'); }
			fail(new Error('Command cancelled by user'));
		});

		proc.on('close', (code) => {
			const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
			if (code === 0) {
				settle(stdout.trim() || `[completed in ${elapsed}s — no output]`);
			} else {
				// Include both stdout and stderr for diagnostics, don't silently fail
				const parts: string[] = [];
				if (stdout.trim()) { parts.push(stdout.trim()); }
				if (stderr.trim()) { parts.push(`[stderr]: ${stderr.trim()}`); }
				if (parts.length === 0) { parts.push(`[command exited with code ${code} after ${elapsed}s]`); }
				settle(parts.join('\n'));
			}
		});

		proc.on('error', (err) => {
			fail(new Error(`Process error: ${err.message}`));
		});

		// Timeout with partial output
		const timer = setTimeout(() => {
			if (!proc.killed) {
				proc.kill('SIGTERM');
				const partial = stdout.trim();
				settle(
					(partial ? partial + '\n' : '') +
					`[⏱ timeout after ${timeoutMs / 1000}s — command: ${args[0] ?? command}]`
				);
			}
		}, timeoutMs);
	});
}
