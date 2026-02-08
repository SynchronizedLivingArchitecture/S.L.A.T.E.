// Modified: 2026-02-08T04:00:00Z | Author: COPILOT | Change: Broaden GPU detection beyond RTX — support any NVIDIA/AMD/Intel GPU for end-user installs
import * as vscode from 'vscode';
import { execSlateCommand, execSlateCommandLong, execSlateCommandWithTimeout } from './slateRunner';

// ─── Shared State for Adaptive Follow-ups ───────────────────────────────
// This module-level state is updated by tool results and consumed by
// the follow-up provider to generate context-aware buttons.

export interface SlateSystemState {
	servicesUp: boolean;
	runnerOnline: boolean;
	gpuLoaded: boolean;
	pendingTasks: number;
	discoveredTasks: number;
	autonomousRunning: boolean;
	lastCommand: string;
	lastToolResults: string[];
	updatedAt: number;
	// Extended: Roadmap/Plan awareness
	currentDevStage: string;
	activeSpecs: string[];
	learningProgress: number;
	planContext: string;
	codeGuidance: string[];
}

let _systemState: SlateSystemState = {
	servicesUp: false,
	runnerOnline: false,
	gpuLoaded: false,
	pendingTasks: 0,
	discoveredTasks: 0,
	autonomousRunning: false,
	lastCommand: 'chat',
	lastToolResults: [],
	updatedAt: 0,
	// Extended: Roadmap/Plan awareness
	currentDevStage: 'code',
	activeSpecs: [],
	learningProgress: 0,
	planContext: '',
	codeGuidance: [],
};

export function getSystemState(): SlateSystemState {
	return { ..._systemState };
}

/** Parse tool output to update system state heuristics */
function updateStateFromOutput(toolName: string, output: string): void {
	const lower = output.toLowerCase();
	_systemState.updatedAt = Date.now();

	// Service detection
	if (toolName === 'slate_orchestrator') {
		_systemState.servicesUp = lower.includes('running') && !lower.includes('all stopped');
	}

	// Runner detection
	if (toolName === 'slate_runnerStatus') {
		_systemState.runnerOnline = lower.includes('online') || lower.includes('idle') || lower.includes('listening');
	}

	// GPU detection — detect any NVIDIA/AMD/Intel GPU, not just RTX
	if (toolName === 'slate_hardwareInfo' || toolName === 'slate_gpuManager') {
		_systemState.gpuLoaded = lower.includes('gpu') && (lower.includes('cuda') || lower.includes('nvidia') || lower.includes('rtx') || lower.includes('gtx') || lower.includes('geforce') || lower.includes('radeon') || lower.includes('gpu 0'));
	}

	// Task detection
	if (toolName === 'slate_workflow' || toolName === 'slate_autonomous' || toolName === 'slate_agentStatus') {
		const pendingMatch = output.match(/(\d+)\s*pending/i);
		if (pendingMatch) { _systemState.pendingTasks = parseInt(pendingMatch[1]); }
		const discoveredMatch = output.match(/(\d+)\s*discovered/i);
		if (discoveredMatch) { _systemState.discoveredTasks = parseInt(discoveredMatch[1]); }
		_systemState.autonomousRunning = lower.includes('running') && !lower.includes('never started');
	}

	// Track recent tool results (keep last 3)
	_systemState.lastToolResults.push(toolName);
	if (_systemState.lastToolResults.length > 3) {
		_systemState.lastToolResults = _systemState.lastToolResults.slice(-3);
	}
}

// ─── Tool Implementations ──────────────────────────────────────────────

interface IStatusParams { quick?: boolean }
interface IRuntimeParams { /* no params */ }
interface IRunnerParams { action?: string; workflow?: string }
interface IHardwareParams { optimize?: boolean }
interface IOrchestratorParams { action?: string }
interface IWorkflowParams { action?: string }
interface IBenchmarkParams { /* no params */ }
interface IRunCommandParams { command: string }
interface IInstallParams { target?: string; beta?: boolean }
interface IUpdateParams { /* no params */ }
interface ICheckDepsParams { /* no params */ }
interface IForkCheckParams { action?: string }
interface ISecurityAuditParams { scan?: string }
interface IAgentStatusParams { action?: string }
interface IGpuManagerParams { action?: string }
interface IAutonomousParams { action?: string; max?: number }
interface ISlateRunProtocolParams { /* no params */ }
interface IHandoffParams { task: string; priority?: string }
interface IStartServicesParams { services?: string }
interface IExecuteWorkParams { scope?: string; max?: number }
interface IAgentBridgeParams { action: string; taskId?: string; result?: string; success?: boolean }

// ─── NEW: Roadmap & Plan Awareness Interfaces ───────────────────────────
interface IDevCycleParams { action?: string; stage?: string; reason?: string }
interface ISpecKitParams { action?: string; specId?: string }
interface ILearningParams { action?: string; stepId?: string }
interface IPlanContextParams { scope?: string }
interface ICodeGuidanceParams { file?: string; context?: string }

class SystemStatusTool implements vscode.LanguageModelTool<IStatusParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IStatusParams>, token: vscode.CancellationToken) {
		const flag = options.input.quick ? '--quick' : '--json';
		const output = await execSlateCommand(`slate/slate_status.py ${flag}`, token);
		updateStateFromOutput('slate_systemStatus', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<IStatusParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Checking SLATE system status...' };
	}
}

class RuntimeCheckTool implements vscode.LanguageModelTool<IRuntimeParams> {
	async invoke(_options: vscode.LanguageModelToolInvocationOptions<IRuntimeParams>, token: vscode.CancellationToken) {
		const output = await execSlateCommand('slate/slate_runtime.py --check-all', token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<IRuntimeParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Checking SLATE runtime integrations...' };
	}
}

class RunnerStatusTool implements vscode.LanguageModelTool<IRunnerParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IRunnerParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		let cmd: string;
		switch (action) {
			case 'detect':
				cmd = 'slate/slate_runner_manager.py --detect';
				break;
			case 'dispatch':
				cmd = `slate/slate_runner_manager.py --dispatch "${options.input.workflow ?? 'ci.yml'}"`;
				break;
			default:
				cmd = 'slate/slate_runner_manager.py --status';
		}
		const output = await execSlateCommand(cmd, token);
		updateStateFromOutput('slate_runnerStatus', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IRunnerParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking runner status...',
			detect: 'Detecting runner configuration...',
			dispatch: `Dispatching workflow ${options.input.workflow ?? 'ci.yml'}...`,
		};
		return { invocationMessage: messages[action] ?? 'Checking runner...' };
	}
}

class HardwareInfoTool implements vscode.LanguageModelTool<IHardwareParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IHardwareParams>, token: vscode.CancellationToken) {
		const flag = options.input.optimize ? '--optimize' : '';
		const output = await execSlateCommand(`slate/slate_hardware_optimizer.py ${flag}`.trim(), token);
		updateStateFromOutput('slate_hardwareInfo', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IHardwareParams>, _token: vscode.CancellationToken) {
		return {
			invocationMessage: options.input.optimize ? 'Optimizing GPU settings...' : 'Detecting hardware...',
		};
	}
}

class OrchestratorTool implements vscode.LanguageModelTool<IOrchestratorParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IOrchestratorParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const output = await execSlateCommand(`slate/slate_orchestrator.py ${action}`, token);
		updateStateFromOutput('slate_orchestrator', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IOrchestratorParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking service status...',
			start: 'Starting SLATE services...',
			stop: 'Stopping SLATE services...',
		};
		return { invocationMessage: messages[action] ?? 'Managing orchestrator...' };
	}
}

class WorkflowTool implements vscode.LanguageModelTool<IWorkflowParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IWorkflowParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const flags: Record<string, string> = {
			status: '--status',
			cleanup: '--cleanup',
			enforce: '--enforce',
		};
		const output = await execSlateCommand(`slate/slate_workflow_manager.py ${flags[action] ?? '--status'}`, token);
		updateStateFromOutput('slate_workflow', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IWorkflowParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: `Workflow manager: ${options.input.action ?? 'status'}...` };
	}
}

class BenchmarkTool implements vscode.LanguageModelTool<IBenchmarkParams> {
	async invoke(_options: vscode.LanguageModelToolInvocationOptions<IBenchmarkParams>, token: vscode.CancellationToken) {
		const output = await execSlateCommand('slate/slate_benchmark.py', token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<IBenchmarkParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Running SLATE benchmarks...' };
	}
}

class RunCommandTool implements vscode.LanguageModelTool<IRunCommandParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IRunCommandParams>, token: vscode.CancellationToken) {
		const output = await execSlateCommand(options.input.command, token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IRunCommandParams>, _token: vscode.CancellationToken) {
		return {
			invocationMessage: `Running: ${options.input.command}`,
			confirmationMessages: {
				title: 'Run SLATE Command',
				message: new vscode.MarkdownString(`Run this command?\n\n\`\`\`\n${options.input.command}\n\`\`\``),
			},
		};
	}
}

class InstallTool implements vscode.LanguageModelTool<IInstallParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IInstallParams>, token: vscode.CancellationToken) {
		let cmd = 'slate/slate_installer.py --install';
		if (options.input.target) {
			cmd += ` --target "${options.input.target}"`;
		}
		if (options.input.beta) {
			cmd += ' --beta';
		}
		const output = await execSlateCommandLong(cmd, token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IInstallParams>, _token: vscode.CancellationToken) {
		const target = options.input.target ? ` to ${options.input.target}` : '';
		const beta = options.input.beta ? ' (BETA fork)' : '';
		return {
			invocationMessage: `Installing SLATE ecosystem${target}${beta}...`,
			confirmationMessages: {
				title: 'Install SLATE Ecosystem',
				message: new vscode.MarkdownString(
					`This will set up the full SLATE ecosystem${target}${beta}:\n\n` +
					'- Git repository clone/verify\n' +
					'- Python virtual environment\n' +
					'- pip dependencies (requirements.txt)\n' +
					'- PyTorch (GPU-aware)\n' +
					'- Ollama (local LLM)\n' +
					'- Docker (containerization)\n' +
					'- VS Code extension\n' +
					'- SLATE custom models\n' +
					'- Workspace configuration\n\n' +
					'Continue?'
				),
			},
		};
	}
}

class UpdateTool implements vscode.LanguageModelTool<IUpdateParams> {
	async invoke(_options: vscode.LanguageModelToolInvocationOptions<IUpdateParams>, token: vscode.CancellationToken) {
		const output = await execSlateCommandLong('slate/slate_installer.py --update', token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<IUpdateParams>, _token: vscode.CancellationToken) {
		return {
			invocationMessage: 'Updating SLATE from git...',
			confirmationMessages: {
				title: 'Update SLATE',
				message: new vscode.MarkdownString(
					'This will:\n\n' +
					'- Pull latest code from git\n' +
					'- Update pip dependencies\n' +
					'- Rebuild VS Code extension\n' +
					'- Re-validate ecosystem\n\n' +
					'Continue?'
				),
			},
		};
	}
}

class CheckDepsTool implements vscode.LanguageModelTool<ICheckDepsParams> {
	async invoke(_options: vscode.LanguageModelToolInvocationOptions<ICheckDepsParams>, token: vscode.CancellationToken) {
		const output = await execSlateCommand('slate/slate_installer.py --check', token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<ICheckDepsParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Checking SLATE ecosystem dependencies...' };
	}
}

// ─── Registration ───────────────────────────────────────────────────────

// ─── New Tools for Button Control Interface ─────────────────────────────

class ForkCheckTool implements vscode.LanguageModelTool<IForkCheckParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IForkCheckParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const flags: Record<string, string> = {
			status: '--status',
			sync: '--sync-all',
			check: '--check-updates',
			list: '--list',
		};
		const output = await execSlateCommand(`slate/slate_fork_manager.py ${flags[action] ?? '--status'}`, token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IForkCheckParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking fork status...',
			sync: 'Syncing all forks with upstream...',
			check: 'Checking forks for updates...',
			list: 'Listing all registered forks...',
		};
		return { invocationMessage: messages[action] ?? 'Checking forks...' };
	}
}

class SecurityAuditTool implements vscode.LanguageModelTool<ISecurityAuditParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<ISecurityAuditParams>, token: vscode.CancellationToken) {
		const scan = options.input.scan ?? 'full';
		const results: string[] = [];

		if (scan === 'full') {
			// Run all 3 scans CONCURRENTLY to prevent sequential blocking
			const [agOutput, piiOutput, sdkOutput] = await Promise.allSettled([
				execSlateCommand('slate/action_guard.py --scan', token),
				execSlateCommand('slate/pii_scanner.py --scan', token),
				execSlateCommand('slate/sdk_source_guard.py --check', token),
			]);

			results.push('=== ActionGuard ===');
			results.push(agOutput.status === 'fulfilled' ? agOutput.value : `[ERROR] ${(agOutput as PromiseRejectedResult).reason}`);
			results.push('\n=== PII Scanner ===');
			results.push(piiOutput.status === 'fulfilled' ? piiOutput.value : `[ERROR] ${(piiOutput as PromiseRejectedResult).reason}`);
			results.push('\n=== SDK Source Guard ===');
			results.push(sdkOutput.status === 'fulfilled' ? sdkOutput.value : `[ERROR] ${(sdkOutput as PromiseRejectedResult).reason}`);
		} else {
			// Single scan
			const cmds: Record<string, string> = {
				actionguard: 'slate/action_guard.py --scan',
				pii: 'slate/pii_scanner.py --scan',
				sdk: 'slate/sdk_source_guard.py --check',
			};
			const cmd = cmds[scan];
			if (cmd) {
				const output = await execSlateCommand(cmd, token);
				results.push(`=== ${scan.toUpperCase()} ===\n${output}`);
			} else {
				results.push(`Unknown scan type: ${scan}`);
			}
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<ISecurityAuditParams>, _token: vscode.CancellationToken) {
		const scan = options.input.scan ?? 'full';
		return {
			invocationMessage: `Running security audit (${scan})...`,
		};
	}
}

class AgentStatusTool implements vscode.LanguageModelTool<IAgentStatusParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IAgentStatusParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const results: string[] = [];

		switch (action) {
			case 'status': {
				// Run both status checks CONCURRENTLY
				const [unifiedResult, copilotResult] = await Promise.allSettled([
					execSlateCommand('slate/slate_unified_autonomous.py --status', token),
					execSlateCommand('slate/copilot_slate_runner.py --status', token),
				]);
				results.push('=== Unified Autonomous ===');
				results.push(unifiedResult.status === 'fulfilled' ? unifiedResult.value : `[ERROR] ${(unifiedResult as PromiseRejectedResult).reason}`);
				results.push('\n=== Copilot Runner ===');
				results.push(copilotResult.status === 'fulfilled' ? copilotResult.value : `[ERROR] ${(copilotResult as PromiseRejectedResult).reason}`);
				break;
			}
			case 'discover': {
				const discoverOut = await execSlateCommand('slate/slate_unified_autonomous.py --discover', token);
				results.push('=== Available Tasks ===\n' + discoverOut);
				break;
			}
			case 'integrated': {
				const intOut = await execSlateCommand('slate/integrated_autonomous_loop.py --status', token);
				results.push('=== Integrated Loop ===\n' + intOut);
				break;
			}
			default: {
				const defaultOut = await execSlateCommand('slate/slate_unified_autonomous.py --status', token);
				results.push(defaultOut);
			}
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IAgentStatusParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: `Checking agent status (${options.input.action ?? 'status'})...` };
	}
}

class GpuManagerTool implements vscode.LanguageModelTool<IGpuManagerParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IGpuManagerParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const flags: Record<string, string> = {
			status: '--status',
			configure: '--configure',
			preload: '--preload',
		};
		const output = await execSlateCommand(`slate/slate_gpu_manager.py ${flags[action] ?? '--status'}`, token);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IGpuManagerParams>, _token: vscode.CancellationToken) {
		const messages: Record<string, string> = {
			status: 'Checking dual-GPU status...',
			configure: 'Configuring dual-GPU load balancing...',
			preload: 'Preloading models to GPUs...',
		};
		return { invocationMessage: messages[options.input.action ?? 'status'] ?? 'Managing GPUs...' };
	}
}

class AutonomousLoopTool implements vscode.LanguageModelTool<IAutonomousParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IAutonomousParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const cmds: Record<string, string> = {
			status: 'slate/slate_unified_autonomous.py --status',
			discover: 'slate/slate_unified_autonomous.py --discover',
			single: 'slate/slate_unified_autonomous.py --single',
			run: `slate/slate_unified_autonomous.py --run --max ${options.input.max ?? 5}`,
		};
		const cmd = cmds[action] ?? cmds.status;
		// Use longer timeout for execution actions
		const timeout = (action === 'single' || action === 'run') ? 120_000 : 30_000;
		const output = await execSlateCommandWithTimeout(cmd, token, timeout);
		updateStateFromOutput('slate_autonomous', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IAutonomousParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking autonomous loop status...',
			discover: 'Discovering available tasks...',
			single: 'Executing next autonomous task...',
			run: `Running autonomous loop (max ${options.input.max ?? 5} tasks)...`,
		};
		return { invocationMessage: messages[action] ?? 'Autonomous loop...' };
	}
}

class SlateRunProtocolTool implements vscode.LanguageModelTool<ISlateRunProtocolParams> {
	async invoke(_options: vscode.LanguageModelToolInvocationOptions<ISlateRunProtocolParams>, token: vscode.CancellationToken) {
		const results: string[] = [];
		const steps = [
			{ label: 'Step 1: System Health', cmd: 'slate/slate_status.py --quick' },
			{ label: 'Step 2: Runtime Integrations', cmd: 'slate/slate_runtime.py --check-all' },
			{ label: 'Step 3: Workflow Status', cmd: 'slate/slate_workflow_manager.py --status' },
			{ label: 'Step 4: Enforce Completion', cmd: 'slate/slate_workflow_manager.py --enforce' },
		];

		for (const step of steps) {
			if (token.isCancellationRequested) {
				results.push(`\n=== ${step.label} === CANCELLED`);
				break;
			}

			results.push(`\n=== ${step.label} ===`);
			try {
				const output = await execSlateCommandWithTimeout(step.cmd, token, 45_000);
				results.push(output);
			} catch (err) {
				const errMsg = err instanceof Error ? err.message : String(err);
				results.push(`[FAILED] ${errMsg}`);
				// Continue to next step even if one fails — don't block the whole protocol
			}
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<ISlateRunProtocolParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Running SLATE protocol (health → runtime → workflow → enforce)...' };
	}
}

// ─── Task Handoff Tool ──────────────────────────────────────────────────
// Bridges chat participant → autonomous agent. Queues a task for the
// background SLATE agent to pick up and execute independently.

class HandoffTool implements vscode.LanguageModelTool<IHandoffParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IHandoffParams>, token: vscode.CancellationToken) {
		const task = options.input.task;
		const priority = options.input.priority ?? 'medium';
		const cmd = `slate/copilot_slate_runner.py --queue "${task.replace(/"/g, '\\"')}" --priority ${priority}`;
		const output = await execSlateCommand(cmd, token);
		updateStateFromOutput('slate_handoff', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(
			`[Task handed off to autonomous agent]\n${output}\n\nThe SLATE autonomous agent will now execute this task independently. Use /agents to monitor progress.`
		)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IHandoffParams>, _token: vscode.CancellationToken) {
		return {
			invocationMessage: `Handing off task to autonomous agent: ${options.input.task.slice(0, 60)}...`,
			confirmationMessages: {
				title: 'Hand Off to SLATE Agent',
				message: new vscode.MarkdownString(
					`Queue this task for the SLATE autonomous agent?\n\n` +
					`**Task:** ${options.input.task}\n` +
					`**Priority:** ${options.input.priority ?? 'medium'}\n\n` +
					`The agent will execute this independently while you continue working.`
				),
			},
		};
	}
}

// ─── Execute Work Tool ──────────────────────────────────────────────────
// Modified: 2026-02-07T07:15:00Z | Author: COPILOT | Change: aggressive work execution — chains discover→cleanup→execute→verify
// Chains multiple SLATE operations in one call so the participant can DO work
// instead of just reporting. This is the power tool for aggressive operation.

class ExecuteWorkTool implements vscode.LanguageModelTool<IExecuteWorkParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IExecuteWorkParams>, token: vscode.CancellationToken) {
		const scope = options.input.scope ?? 'full';
		const maxTasks = options.input.max ?? 3;
		const results: string[] = [];

		// Phase 1: Cleanup stale tasks first
		if (scope === 'full' || scope === 'cleanup') {
			try {
				const cleanupOut = await execSlateCommandWithTimeout('slate/slate_workflow_manager.py --cleanup', token, 30_000);
				results.push('=== Phase 1: Cleanup ===\n' + cleanupOut);
			} catch (e) {
				results.push(`=== Phase 1: Cleanup === SKIPPED: ${e instanceof Error ? e.message : String(e)}`);
			}
		}

		// Phase 2: Discover available tasks
		if (scope === 'full' || scope === 'discover') {
			try {
				const discoverOut = await execSlateCommandWithTimeout('slate/slate_unified_autonomous.py --discover', token, 30_000);
				results.push('\n=== Phase 2: Task Discovery ===\n' + discoverOut);
			} catch (e) {
				results.push(`\n=== Phase 2: Task Discovery === FAILED: ${e instanceof Error ? e.message : String(e)}`);
			}
		}

		// Phase 3: Execute tasks
		if (scope === 'full' || scope === 'execute') {
			if (token.isCancellationRequested) {
				results.push('\n=== Phase 3: Execution === CANCELLED');
			} else {
				try {
					const execOut = await execSlateCommandWithTimeout(
						`slate/slate_unified_autonomous.py --run --max ${maxTasks}`,
						token, 180_000 // 3 min for execution
					);
					results.push(`\n=== Phase 3: Execution (max ${maxTasks} tasks) ===\n` + execOut);
				} catch (e) {
					results.push(`\n=== Phase 3: Execution === FAILED: ${e instanceof Error ? e.message : String(e)}`);
				}
			}
		}

		// Phase 4: Verify final state
		if (scope === 'full' || scope === 'verify') {
			try {
				const statusOut = await execSlateCommandWithTimeout('slate/slate_workflow_manager.py --status', token, 20_000);
				results.push('\n=== Phase 4: Final State ===\n' + statusOut);
			} catch (e) {
				results.push(`\n=== Phase 4: Final State === FAILED: ${e instanceof Error ? e.message : String(e)}`);
			}
		}

		const output = results.join('\n');
		updateStateFromOutput('slate_autonomous', output);
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IExecuteWorkParams>, _token: vscode.CancellationToken) {
		const scope = options.input.scope ?? 'full';
		const max = options.input.max ?? 3;
		return {
			invocationMessage: `Executing SLATE work pipeline (${scope}, max ${max} tasks)...`,
			confirmationMessages: {
				title: 'Execute SLATE Work Pipeline',
				message: new vscode.MarkdownString(
					`Run the full SLATE work pipeline?\n\n` +
					`1. **Cleanup** stale/deprecated tasks\n` +
					`2. **Discover** available tasks from all sources\n` +
					`3. **Execute** up to ${max} tasks via autonomous agent\n` +
					`4. **Verify** final system state\n\n` +
					`Scope: ${scope}`
				),
			},
		};
	}
}

// ─── Start Services Tool ────────────────────────────────────────────────
// Starts SLATE services (dashboard, orchestrator, runner) as a single action.

class StartServicesTool implements vscode.LanguageModelTool<IStartServicesParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IStartServicesParams>, token: vscode.CancellationToken) {
		const target = options.input.services ?? 'all';
		const results: string[] = [];

		if (target === 'all' || target === 'orchestrator') {
			try {
				const out = await execSlateCommandWithTimeout('slate/slate_orchestrator.py start', token, 60_000);
				results.push('=== Orchestrator ===\n' + out);
			} catch (e) {
				results.push(`=== Orchestrator === FAILED: ${e instanceof Error ? e.message : String(e)}`);
			}
		}

		if (target === 'all' || target === 'runner') {
			try {
				const out = await execSlateCommandWithTimeout('slate/copilot_slate_runner.py --start --max-tasks 50 --stop-on-empty', token, 60_000);
				results.push('=== Copilot Runner ===\n' + out);
			} catch (e) {
				results.push(`=== Copilot Runner === FAILED: ${e instanceof Error ? e.message : String(e)}`);
			}
		}

		const output = results.join('\n\n');
		updateStateFromOutput('slate_orchestrator', output);
		_systemState.servicesUp = !output.toLowerCase().includes('failed');
		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IStartServicesParams>, _token: vscode.CancellationToken) {
		const target = options.input.services ?? 'all';
		return {
			invocationMessage: `Starting SLATE services (${target})...`,
			confirmationMessages: {
				title: 'Start SLATE Services',
				message: new vscode.MarkdownString(
					`Start the following services?\n\n` +
					(target === 'all'
						? '- Dashboard (127.0.0.1:8080)\n- Orchestrator\n- Copilot Runner'
						: `- ${target}`)
				),
			},
		};
	}
}

// ─── Copilot Agent Bridge Tool ──────────────────────────────────────────
// Modified: 2026-02-07T12:00:00Z | Author: COPILOT | Change: Bridge tool for @slate participant as COPILOT_CHAT subagent
// Allows the @slate participant to poll for tasks dispatched by the autonomous loop
// and write results back, completing the bidirectional agent bridge.

class CopilotAgentBridgeTool implements vscode.LanguageModelTool<IAgentBridgeParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IAgentBridgeParams>, token: vscode.CancellationToken) {
		const action = options.input.action;
		let cmd: string;

		switch (action) {
			case 'poll':
				cmd = 'slate/copilot_agent_bridge.py --pending --json';
				break;
			case 'status':
				cmd = 'slate/copilot_agent_bridge.py --status --json';
				break;
			case 'complete':
				if (!options.input.taskId) {
					return new vscode.LanguageModelToolResult([
						new vscode.LanguageModelTextPart('Error: taskId is required for complete action'),
					]);
				}
				// Write completion via Python CLI
				const successFlag = options.input.success !== false ? 'true' : 'false';
				const resultText = (options.input.result ?? 'completed').replace(/"/g, '\\"').substring(0, 2000);
				cmd = `slate/copilot_agent_bridge.py --complete "${options.input.taskId}" --success ${successFlag} --result "${resultText}"`;
				break;
			case 'cleanup':
				cmd = 'slate/copilot_agent_bridge.py --cleanup';
				break;
			default:
				cmd = 'slate/copilot_agent_bridge.py --status';
		}

		const output = await execSlateCommand(cmd, token);

		// Track bridge state
		if (action === 'poll') {
			const pendingMatch = output.match(/(\d+)\s*pending/i);
			if (pendingMatch) {
				_systemState.pendingTasks = Math.max(_systemState.pendingTasks, parseInt(pendingMatch[1]));
			}
		}
		updateStateFromOutput('slate_agentBridge', output);

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(output)]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IAgentBridgeParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const actionLabels: Record<string, string> = {
			poll: 'Polling for bridge tasks from autonomous loop...',
			status: 'Checking agent bridge status...',
			complete: `Completing bridge task ${options.input.taskId ?? ''}...`,
			cleanup: 'Cleaning up stale bridge tasks...',
		};
		return { invocationMessage: actionLabels[action] ?? 'Agent bridge operation...' };
	}
}

// ─── DevCycle Tool ──────────────────────────────────────────────────────
// Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Roadmap-aware dev cycle management
// Reads and manages the 5-stage development cycle (PLAN → CODE → TEST → DEPLOY → FEEDBACK)
// This is the core roadmap awareness tool for guiding Copilot's code writes.

class DevCycleTool implements vscode.LanguageModelTool<IDevCycleParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IDevCycleParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const results: string[] = [];

		switch (action) {
			case 'status': {
				// Read current dev cycle state
				const output = await execSlateCommand('slate/dev_cycle_engine.py --status --json', token);
				results.push('=== Development Cycle State ===\n' + output);
				// Update global state
				try {
					const state = JSON.parse(output);
					_systemState.currentDevStage = state.current_stage ?? 'code';
				} catch { /* ignore parse errors */ }
				break;
			}
			case 'transition': {
				if (!options.input.stage) {
					return new vscode.LanguageModelToolResult([
						new vscode.LanguageModelTextPart('Error: stage is required for transition action'),
					]);
				}
				const reason = options.input.reason ? `--reason "${options.input.reason}"` : '';
				const output = await execSlateCommand(
					`slate/dev_cycle_engine.py --transition ${options.input.stage} ${reason}`.trim(),
					token
				);
				results.push(`=== Stage Transition → ${options.input.stage.toUpperCase()} ===\n` + output);
				_systemState.currentDevStage = options.input.stage;
				break;
			}
			case 'activities': {
				const stage = options.input.stage ?? _systemState.currentDevStage;
				const output = await execSlateCommand(`slate/dev_cycle_engine.py --activities ${stage}`, token);
				results.push(`=== Activities for ${stage.toUpperCase()} ===\n` + output);
				break;
			}
			case 'guidance': {
				// Get code guidance based on current stage
				const stageGuidance: Record<string, string[]> = {
					plan: [
						'Focus on architecture and design decisions',
						'Create specs in specs/ directory',
						'Document requirements before implementing',
						'Use /slate-spec-kit to process specifications',
					],
					code: [
						'Implement features according to active specs',
						'Follow SLATE code patterns (type hints, docstrings)',
						'Keep changes focused and minimal',
						'Check dev_cycle_state.json for current iteration goals',
					],
					test: [
						'Write tests before or alongside code changes',
						'Target 50%+ coverage for slate/ and slate_core/',
						'Use pytest with -v flag for verbose output',
						'Run full test suite before transitioning to deploy',
					],
					deploy: [
						'Verify all tests pass before deploying',
						'Use GitHub Actions workflows for CI/CD',
						'Check runner status before dispatching',
						'Update documentation after successful deploy',
					],
					feedback: [
						'Review GitHub Discussions for community input',
						'Check achievement progress for motivation',
						'Analyze patterns from Claude feedback layer',
						'Plan next iteration based on insights',
					],
				};
				const stage = _systemState.currentDevStage;
				const guidance = stageGuidance[stage] ?? stageGuidance.code;
				_systemState.codeGuidance = guidance;
				results.push(`=== Code Guidance for ${stage.toUpperCase()} Stage ===`);
				guidance.forEach((g, i) => results.push(`${i + 1}. ${g}`));
				break;
			}
			default:
				const output = await execSlateCommand('slate/dev_cycle_engine.py --status', token);
				results.push(output);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IDevCycleParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Reading development cycle state...',
			transition: `Transitioning to ${options.input.stage ?? 'next'} stage...`,
			activities: 'Getting stage activities...',
			guidance: 'Getting code guidance for current stage...',
		};
		return { invocationMessage: messages[action] ?? 'Development cycle operation...' };
	}
}

// ─── SpecKit Tool ───────────────────────────────────────────────────────
// Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Spec processing and wiki integration
// Manages specifications: process, analyze, and generate wiki documentation.

class SpecKitTool implements vscode.LanguageModelTool<ISpecKitParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<ISpecKitParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const results: string[] = [];

		switch (action) {
			case 'status': {
				const output = await execSlateCommand('slate/slate_spec_kit.py --status', token);
				results.push('=== Spec-Kit Status ===\n' + output);
				// Extract active specs
				const specMatch = output.match(/Active specs?: (\d+)/i);
				if (specMatch) {
					_systemState.activeSpecs = [];
				}
				break;
			}
			case 'list': {
				const output = await execSlateCommand('slate/slate_spec_kit.py --list', token);
				results.push('=== Available Specifications ===\n' + output);
				break;
			}
			case 'process': {
				const specArg = options.input.specId ? `--spec ${options.input.specId}` : '--process-all';
				const output = await execSlateCommandLong(`slate/slate_spec_kit.py ${specArg}`, token);
				results.push('=== Specification Processing ===\n' + output);
				break;
			}
			case 'analyze': {
				const specArg = options.input.specId ? `--analyze ${options.input.specId}` : '--analyze-all';
				const output = await execSlateCommandLong(`slate/slate_spec_kit.py ${specArg}`, token);
				results.push('=== AI Specification Analysis ===\n' + output);
				break;
			}
			case 'wiki': {
				const output = await execSlateCommandLong('slate/slate_spec_kit.py --wiki', token);
				results.push('=== Wiki Generation ===\n' + output);
				break;
			}
			case 'roadmap': {
				// Get roadmap from specs for plan alignment
				const output = await execSlateCommand('slate/slate_spec_kit.py --roadmap', token);
				results.push('=== Development Roadmap ===\n' + output);
				_systemState.planContext = output;
				break;
			}
			default:
				const output = await execSlateCommand('slate/slate_spec_kit.py --status', token);
				results.push(output);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<ISpecKitParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking Spec-Kit status...',
			list: 'Listing available specifications...',
			process: 'Processing specifications...',
			analyze: 'Running AI analysis on specs...',
			wiki: 'Generating wiki documentation...',
			roadmap: 'Extracting development roadmap...',
		};
		return { invocationMessage: messages[action] ?? 'Spec-Kit operation...' };
	}
}

// ─── Learning Progress Tool ─────────────────────────────────────────────
// Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Interactive learning and achievement tracking
// Tracks learning progress, achievements, and provides guided learning paths.

class LearningProgressTool implements vscode.LanguageModelTool<ILearningParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<ILearningParams>, token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const results: string[] = [];

		switch (action) {
			case 'status': {
				const output = await execSlateCommand('slate/interactive_tutor.py --status --json', token);
				results.push('=== Learning Progress ===\n' + output);
				try {
					const progress = JSON.parse(output);
					_systemState.learningProgress = progress.total_xp ?? 0;
				} catch { /* ignore */ }
				break;
			}
			case 'paths': {
				const output = await execSlateCommand('slate/interactive_tutor.py --paths', token);
				results.push('=== Available Learning Paths ===\n' + output);
				break;
			}
			case 'achievements': {
				const output = await execSlateCommand('slate/interactive_tutor.py --achievements', token);
				results.push('=== Achievements ===\n' + output);
				break;
			}
			case 'next': {
				const output = await execSlateCommand('slate/interactive_tutor.py --next', token);
				results.push('=== Next Learning Step ===\n' + output);
				break;
			}
			case 'complete': {
				if (!options.input.stepId) {
					return new vscode.LanguageModelToolResult([
						new vscode.LanguageModelTextPart('Error: stepId is required for complete action'),
					]);
				}
				const output = await execSlateCommand(
					`slate/interactive_tutor.py --complete ${options.input.stepId}`,
					token
				);
				results.push('=== Step Completed ===\n' + output);
				break;
			}
			default:
				const output = await execSlateCommand('slate/interactive_tutor.py --status', token);
				results.push(output);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<ILearningParams>, _token: vscode.CancellationToken) {
		const action = options.input.action ?? 'status';
		const messages: Record<string, string> = {
			status: 'Checking learning progress...',
			paths: 'Listing learning paths...',
			achievements: 'Getting achievements...',
			next: 'Getting next learning step...',
			complete: 'Marking step complete...',
		};
		return { invocationMessage: messages[action] ?? 'Learning operation...' };
	}
}

// ─── Plan Context Tool ──────────────────────────────────────────────────
// Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Unified plan context for code guidance
// Aggregates context from dev cycle, specs, and tasks to guide code generation.
// This is the TOKEN SAVER — compresses context for efficient LLM usage.

class PlanContextTool implements vscode.LanguageModelTool<IPlanContextParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IPlanContextParams>, token: vscode.CancellationToken) {
		const scope = options.input.scope ?? 'full';
		const results: string[] = [];

		// Get compressed context based on scope
		if (scope === 'full' || scope === 'cycle') {
			// Dev cycle — minimal summary
			try {
				const cycleOut = await execSlateCommandWithTimeout('slate/dev_cycle_engine.py --status --json', token, 10_000);
				const state = JSON.parse(cycleOut);
				results.push(`STAGE: ${(state.current_stage ?? 'code').toUpperCase()} | Iteration: ${state.current_iteration ?? 'v0.1.0'} | Cycle: ${state.cycle_count ?? 0}`);
				_systemState.currentDevStage = state.current_stage ?? 'code';
			} catch (e) {
				results.push(`STAGE: ${_systemState.currentDevStage.toUpperCase()} (cached)`);
			}
		}

		if (scope === 'full' || scope === 'tasks') {
			// Task summary — just counts
			try {
				const workflowOut = await execSlateCommandWithTimeout('slate/slate_workflow_manager.py --status', token, 10_000);
				const pendingMatch = workflowOut.match(/(\d+)\s*pending/i);
				const inProgressMatch = workflowOut.match(/(\d+)\s*in.?progress/i);
				const pending = pendingMatch ? pendingMatch[1] : '0';
				const inProgress = inProgressMatch ? inProgressMatch[1] : '0';
				results.push(`TASKS: ${pending} pending, ${inProgress} in-progress`);
				_systemState.pendingTasks = parseInt(pending);
			} catch {
				results.push(`TASKS: ${_systemState.pendingTasks} pending (cached)`);
			}
		}

		if (scope === 'full' || scope === 'specs') {
			// Spec summary — just names
			try {
				const specOut = await execSlateCommandWithTimeout('slate/slate_spec_kit.py --list --brief', token, 10_000);
				const specLines = specOut.split('\n').filter(l => l.trim()).slice(0, 5);
				results.push(`SPECS: ${specLines.join(', ') || 'none'}`);
			} catch {
				results.push('SPECS: (unavailable)');
			}
		}

		if (scope === 'full' || scope === 'guidance') {
			// Code guidance based on stage
			const stage = _systemState.currentDevStage;
			const stageDirectives: Record<string, string> = {
				plan: 'DIRECTIVE: Design-first. Create specs before code.',
				code: 'DIRECTIVE: Implement features. Follow existing patterns.',
				test: 'DIRECTIVE: Write/run tests. Target 50%+ coverage.',
				deploy: 'DIRECTIVE: CI/CD focus. Verify before merge.',
				feedback: 'DIRECTIVE: Review and iterate. Check GitHub Discussions.',
			};
			results.push(stageDirectives[stage] ?? stageDirectives.code);
		}

		// Build compressed context (optimized for token efficiency)
		const context = results.join(' | ');
		_systemState.planContext = context;

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(
			`[SLATE CONTEXT — ${new Date().toISOString().slice(11, 19)}]\n${context}\n\nUse this context to guide your code generation and decisions.`
		)]);
	}

	async prepareInvocation(_options: vscode.LanguageModelToolInvocationPrepareOptions<IPlanContextParams>, _token: vscode.CancellationToken) {
		return { invocationMessage: 'Loading SLATE plan context (token-optimized)...' };
	}
}

// ─── Code Guidance Tool ─────────────────────────────────────────────────
// Modified: 2026-02-07T14:00:00Z | Author: COPILOT | Change: Stage-aware code guidance
// Provides specific code guidance based on current file and dev stage.
// Helps Copilot write code that aligns with SLATE patterns and roadmap.

class CodeGuidanceTool implements vscode.LanguageModelTool<ICodeGuidanceParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<ICodeGuidanceParams>, token: vscode.CancellationToken) {
		const file = options.input.file ?? '';
		const context = options.input.context ?? '';
		const results: string[] = [];

		// Determine file type and provide specific guidance
		const fileGuidance: Record<string, string[]> = {
			'.py': [
				'Use type hints for all function parameters and returns',
				'Add Google-style docstrings for public functions',
				'Import WORKSPACE_ROOT for cross-module imports',
				'Use async/await for I/O operations',
				'Follow existing patterns in the module',
			],
			'.ts': [
				'Use TypeScript strict mode patterns',
				'Implement vscode.LanguageModelTool interface for tools',
				'Use async/await with proper error handling',
				'Register tools in registerSlateTools function',
				'Follow Copilot API patterns',
			],
			'.md': [
				'Use concise, action-oriented language',
				'Include code examples where appropriate',
				'Link to related documentation',
				'Keep to SLATE documentation style',
			],
			'.json': [
				'Validate against schema if available',
				'Use consistent indentation (2 spaces)',
				'Include comments where JSON5 is supported',
			],
		};

		// Match file extension
		const ext = file ? file.slice(file.lastIndexOf('.')) : '.py';
		const guidance = fileGuidance[ext] ?? fileGuidance['.py'];

		// Stage-specific additions
		const stage = _systemState.currentDevStage;
		const stageAdditions: Record<string, string[]> = {
			plan: ['Focus on interface design over implementation', 'Document expected behavior first'],
			code: ['Implement minimal code to meet requirements', 'Avoid over-engineering'],
			test: ['Add test coverage for new code', 'Use descriptive test names'],
			deploy: ['Verify CI checks pass', 'Update CHANGELOG if needed'],
			feedback: ['Consider user feedback in changes', 'Document learnings'],
		};

		results.push(`=== Code Guidance for ${file || 'current file'} ===`);
		results.push(`\nStage: ${stage.toUpperCase()}`);
		results.push('\nGeneral:');
		guidance.forEach((g, i) => results.push(`  ${i + 1}. ${g}`));

		const additions = stageAdditions[stage] ?? [];
		if (additions.length > 0) {
			results.push(`\n${stage.toUpperCase()} Stage Specific:`);
			additions.forEach((a, i) => results.push(`  ${i + 1}. ${a}`));
		}

		// Add context-specific guidance if provided
		if (context) {
			results.push('\nContext-Specific:');
			results.push(`  Based on "${context.slice(0, 100)}..." — follow existing patterns in this area.`);
		}

		_systemState.codeGuidance = [...guidance, ...additions];

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<ICodeGuidanceParams>, _token: vscode.CancellationToken) {
		const file = options.input.file ? ` for ${options.input.file}` : '';
		return { invocationMessage: `Getting code guidance${file}...` };
	}
}

// ─── Registration ───────────────────────────────────────────────────────

export function registerSlateTools(context: vscode.ExtensionContext) {
	context.subscriptions.push(vscode.lm.registerTool('slate_systemStatus', new SystemStatusTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_runtimeCheck', new RuntimeCheckTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_runnerStatus', new RunnerStatusTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_hardwareInfo', new HardwareInfoTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_orchestrator', new OrchestratorTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_workflow', new WorkflowTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_benchmark', new BenchmarkTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_runCommand', new RunCommandTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_install', new InstallTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_update', new UpdateTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_checkDeps', new CheckDepsTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_forkCheck', new ForkCheckTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_securityAudit', new SecurityAuditTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_agentStatus', new AgentStatusTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_gpuManager', new GpuManagerTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_autonomous', new AutonomousLoopTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_runProtocol', new SlateRunProtocolTool()));
	// Handoff + service control + work execution + agent bridge tools
	context.subscriptions.push(vscode.lm.registerTool('slate_handoff', new HandoffTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_startServices', new StartServicesTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_executeWork', new ExecuteWorkTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_agentBridge', new CopilotAgentBridgeTool()));
	// Roadmap & Plan Awareness tools (NEW)
	context.subscriptions.push(vscode.lm.registerTool('slate_devCycle', new DevCycleTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_specKit', new SpecKitTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_learningProgress', new LearningProgressTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_planContext', new PlanContextTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_codeGuidance', new CodeGuidanceTool()));
}
