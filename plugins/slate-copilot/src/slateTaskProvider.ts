// Modified: 2026-02-07T23:00:00Z | Author: COPILOT | Change: Add dynamic TaskProvider — SLATE tasks auto-discovered and contributed to VS Code task system
import * as vscode from 'vscode';
import { getSlateConfig } from './extension';

/**
 * SLATE Task Provider
 *
 * Dynamically provides SLATE tasks to the VS Code task system.
 * Instead of relying solely on static tasks.json, this provider
 * auto-discovers available SLATE operations and contributes them
 * as runnable tasks. Users see them in Terminal > Run Task.
 *
 * Integration with VS Code:
 * - Tasks appear under the "slate" task type
 * - Problem matchers parse Python tracebacks
 * - Tasks can be bound to keyboard shortcuts
 * - Tasks appear in the Command Palette via "Tasks: Run Task"
 */

const TASK_SOURCE = 'SLATE';

interface SlateTaskDefinition extends vscode.TaskDefinition {
	operation: string;
	args?: string[];
}

const SLATE_TASKS: { id: string; label: string; detail: string; cmd: string; args: string[]; group?: string; isBackground?: boolean }[] = [
	// System Health
	{ id: 'status-quick', label: 'Quick Status', detail: 'System health check', cmd: 'slate/slate_status.py', args: ['--quick'] },
	{ id: 'status-json', label: 'Full Status (JSON)', detail: 'Machine-readable system status', cmd: 'slate/slate_status.py', args: ['--json'] },
	{ id: 'runtime-check', label: 'Runtime Check', detail: 'Verify all 7 integrations', cmd: 'slate/slate_runtime.py', args: ['--check-all'] },

	// Workflow
	{ id: 'workflow-status', label: 'Workflow Status', detail: 'Task queue status', cmd: 'slate/slate_workflow_manager.py', args: ['--status'] },
	{ id: 'workflow-cleanup', label: 'Workflow Cleanup', detail: 'Clean stale tasks', cmd: 'slate/slate_workflow_manager.py', args: ['--cleanup'] },
	{ id: 'workflow-enforce', label: 'Workflow Enforce', detail: 'Enforce task completion', cmd: 'slate/slate_workflow_manager.py', args: ['--enforce'] },

	// GPU & Hardware
	{ id: 'hardware-detect', label: 'Detect Hardware', detail: 'GPU detection & CUDA', cmd: 'slate/slate_hardware_optimizer.py', args: [] },
	{ id: 'hardware-optimize', label: 'Optimize GPU', detail: 'Apply GPU optimizations', cmd: 'slate/slate_hardware_optimizer.py', args: ['--optimize'] },
	{ id: 'gpu-status', label: 'GPU Status', detail: 'Dual-GPU load balancing', cmd: 'slate/slate_gpu_manager.py', args: ['--status'] },

	// Services
	{ id: 'services-start', label: 'Start Services', detail: 'Start all SLATE services', cmd: 'slate/slate_orchestrator.py', args: ['start'], group: 'build' },
	{ id: 'services-stop', label: 'Stop Services', detail: 'Stop all SLATE services', cmd: 'slate/slate_orchestrator.py', args: ['stop'] },
	{ id: 'services-status', label: 'Service Status', detail: 'Check all service status', cmd: 'slate/slate_orchestrator.py', args: ['status'] },

	// Runner
	{ id: 'runner-status', label: 'Runner Status', detail: 'GitHub Actions runner', cmd: 'slate/slate_runner_manager.py', args: ['--status'] },
	{ id: 'runner-detect', label: 'Detect Runner', detail: 'Find runner config', cmd: 'slate/slate_runner_manager.py', args: ['--detect'] },

	// Tests
	{ id: 'test-all', label: 'Run All Tests', detail: 'Run full pytest suite', cmd: '-m', args: ['pytest', 'tests/', '-v', '--tb=short'], group: 'test' },
	{ id: 'test-core', label: 'Run Core Tests', detail: 'Core SDK tests', cmd: '-m', args: ['pytest', 'tests/', '-v', '-k', 'test_slate_runtime or test_slate_workflow or test_feature_flags'], group: 'test' },
	{ id: 'test-security', label: 'Run Security Tests', detail: 'Security guard tests', cmd: '-m', args: ['pytest', 'tests/', '-v', '-k', 'test_pii_scanner or test_action_guard or test_sdk_source_guard'], group: 'test' },

	// Security
	{ id: 'security-scan', label: 'Full Security Scan', detail: 'ActionGuard + PII + SDK Guard', cmd: 'slate/action_guard.py', args: ['--scan'] },
	{ id: 'pii-scan', label: 'PII Scan', detail: 'Scan for credentials/PII', cmd: 'slate/pii_scanner.py', args: ['--scan'] },

	// Autonomous
	{ id: 'auto-discover', label: 'Discover Tasks', detail: 'Find available autonomous tasks', cmd: 'slate/slate_unified_autonomous.py', args: ['--discover'] },
	{ id: 'auto-single', label: 'Execute Single Task', detail: 'Run next autonomous task', cmd: 'slate/slate_unified_autonomous.py', args: ['--single'] },

	// Benchmarks
	{ id: 'benchmark', label: 'Run Benchmarks', detail: 'CPU, memory, disk, GPU benchmarks', cmd: 'slate/slate_benchmark.py', args: [] },

	// ML
	{ id: 'ml-status', label: 'ML Pipeline Status', detail: 'ML orchestrator status', cmd: 'slate/ml_orchestrator.py', args: ['--status'] },
	{ id: 'ml-benchmarks', label: 'ML Benchmarks', detail: 'Inference benchmarks', cmd: 'slate/ml_orchestrator.py', args: ['--benchmarks'] },
];

export class SlateTaskProvider implements vscode.TaskProvider, vscode.Disposable {
	static readonly taskType = 'slate';
	private _disposables: vscode.Disposable[] = [];

	public activate(context: vscode.ExtensionContext): void {
		this._disposables.push(
			vscode.tasks.registerTaskProvider(SlateTaskProvider.taskType, this)
		);
		context.subscriptions.push(this);
	}

	provideTasks(_token: vscode.CancellationToken): vscode.ProviderResult<vscode.Task[]> {
		const config = getSlateConfig();
		return SLATE_TASKS.map(taskDef => {
			const definition: SlateTaskDefinition = {
				type: SlateTaskProvider.taskType,
				operation: taskDef.id,
				args: taskDef.args,
			};

			const execution = new vscode.ShellExecution(
				config.pythonPath,
				[taskDef.cmd, ...taskDef.args],
				{ cwd: config.workspacePath }
			);

			const task = new vscode.Task(
				definition,
				vscode.TaskScope.Workspace,
				`${TASK_SOURCE}: ${taskDef.label}`,
				TASK_SOURCE,
				execution,
				'$python' // Python problem matcher
			);

			task.detail = taskDef.detail;

			if (taskDef.group === 'test') {
				task.group = vscode.TaskGroup.Test;
			} else if (taskDef.group === 'build') {
				task.group = vscode.TaskGroup.Build;
			}

			task.presentationOptions = {
				reveal: vscode.TaskRevealKind.Always,
				panel: vscode.TaskPanelKind.Shared,
				clear: true,
			};

			return task;
		});
	}

	resolveTask(task: vscode.Task, _token: vscode.CancellationToken): vscode.ProviderResult<vscode.Task> {
		const definition = task.definition as SlateTaskDefinition;
		if (definition.operation) {
			const taskDef = SLATE_TASKS.find(t => t.id === definition.operation);
			if (taskDef) {
				const config = getSlateConfig();
				task.execution = new vscode.ShellExecution(
					config.pythonPath,
					[taskDef.cmd, ...(definition.args ?? taskDef.args)],
					{ cwd: config.workspacePath }
				);
				return task;
			}
		}
		return undefined;
	}

	dispose(): void {
		for (const d of this._disposables) { d.dispose(); }
	}
}
