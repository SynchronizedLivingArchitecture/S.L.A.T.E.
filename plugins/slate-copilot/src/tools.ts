// Modified: 2026-02-07T02:00:00Z | Author: COPILOT | Change: SLATE tool implementations for LM API
import * as vscode from 'vscode';
import { execSlateCommand } from './slateRunner';

// ─── Tool Implementations ──────────────────────────────────────────────

interface IStatusParams { quick?: boolean }
interface IRuntimeParams { /* no params */ }
interface IRunnerParams { action?: string; workflow?: string }
interface IHardwareParams { optimize?: boolean }
interface IOrchestratorParams { action?: string }
interface IWorkflowParams { action?: string }
interface IBenchmarkParams { /* no params */ }
interface IRunCommandParams { command: string }

class SystemStatusTool implements vscode.LanguageModelTool<IStatusParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IStatusParams>, token: vscode.CancellationToken) {
		const flag = options.input.quick ? '--quick' : '--json';
		const output = await execSlateCommand(`slate/slate_status.py ${flag}`, token);
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
}
