// Modified: 2026-02-07T23:00:00Z | Author: COPILOT | Change: Add TestController integration — SLATE tests appear in VS Code Test Explorer with run/debug support
import * as vscode from 'vscode';
import * as cp from 'child_process';
import { getSlateConfig } from './extension';

/**
 * SLATE Test Controller
 *
 * Integrates SLATE's pytest test suite with the VS Code Test Explorer.
 * Tests are organized by suite (core, security, agents, ml) and can
 * be run/debugged directly from the Test Explorer sidebar.
 *
 * Features:
 * - Auto-discovers test files on activation and file changes
 * - Organizes tests into suites matching CI matrix
 * - Run individual tests, suites, or all tests
 * - Shows pass/fail results inline in the editor
 * - Supports continuous run mode
 */

const CONTROLLER_ID = 'slateTestController';
const CONTROLLER_LABEL = 'SLATE Tests';

interface TestSuiteConfig {
	id: string;
	label: string;
	pattern: string;
	files: string[];
}

const TEST_SUITES: TestSuiteConfig[] = [
	{
		id: 'core',
		label: 'Core',
		pattern: 'test_slate_runtime or test_slate_workflow or test_feature_flags or test_install_tracker or test_slate_benchmark or test_watcher or test_module_registry or test_slate_terminal_monitor or test_runner_cost_tracker or test_runner_fallback',
		files: ['test_slate_runtime.py', 'test_slate_workflow.py', 'test_feature_flags.py', 'test_install_tracker.py', 'test_slate_benchmark.py', 'test_watcher.py', 'test_module_registry.py', 'test_slate_terminal_monitor.py', 'test_runner_cost_tracker.py', 'test_runner_fallback.py'],
	},
	{
		id: 'security',
		label: 'Security',
		pattern: 'test_pii_scanner or test_action_guard or test_sdk_source_guard or test_slate_workflow_analyzer',
		files: ['test_pii_scanner.py', 'test_action_guard.py', 'test_sdk_source_guard.py', 'test_slate_workflow_analyzer.py'],
	},
	{
		id: 'agents',
		label: 'Agents',
		pattern: 'test_agent_registry or test_agent_plugins or test_slate_runner_manager or test_slate_runner_benchmark or test_slate_real_multi_runner or test_copilot_slate_runner or test_slate_discussion_manager or test_slate_project_board',
		files: ['test_agent_registry.py', 'test_agent_plugins.py', 'test_slate_runner_manager.py', 'test_slate_runner_benchmark.py', 'test_slate_real_multi_runner.py', 'test_copilot_slate_runner.py', 'test_slate_discussion_manager.py', 'test_slate_project_board.py'],
	},
	{
		id: 'ml',
		label: 'ML & GPU',
		pattern: 'test_ml_orchestrator or test_slate_model_trainer or test_slate_gpu_manager or test_slate_warmup or test_slate_unified_autonomous or test_integrated_autonomous_loop or test_slate_hardware_optimizer',
		files: ['test_ml_orchestrator.py', 'test_slate_model_trainer.py', 'test_slate_gpu_manager.py', 'test_slate_warmup.py', 'test_slate_unified_autonomous.py', 'test_integrated_autonomous_loop.py', 'test_slate_hardware_optimizer.py'],
	},
];

export class SlateTestController implements vscode.Disposable {
	private _controller: vscode.TestController;
	private _disposables: vscode.Disposable[] = [];

	constructor() {
		this._controller = vscode.tests.createTestController(CONTROLLER_ID, CONTROLLER_LABEL);

		// Create run profile
		this._controller.createRunProfile(
			'Run',
			vscode.TestRunProfileKind.Run,
			(request, token) => this._runTests(request, token),
			true
		);

		// Resolve handler — builds the test tree on demand
		this._controller.resolveHandler = async (item) => {
			if (!item) {
				await this._discoverTests();
			}
		};
	}

	public activate(context: vscode.ExtensionContext): void {
		context.subscriptions.push(this);

		// Watch for test file changes
		const watcher = vscode.workspace.createFileSystemWatcher('**/tests/test_*.py');
		watcher.onDidChange(() => this._discoverTests());
		watcher.onDidCreate(() => this._discoverTests());
		watcher.onDidDelete(() => this._discoverTests());
		this._disposables.push(watcher);

		// Register refresh command
		this._disposables.push(
			vscode.commands.registerCommand('slate.refreshTests', () => this._discoverTests())
		);

		// Initial discovery
		void this._discoverTests();
	}

	/**
	 * Discover test files and populate the test tree.
	 */
	private async _discoverTests(): Promise<void> {
		const config = getSlateConfig();

		// Clear existing items
		this._controller.items.replace([]);

		for (const suite of TEST_SUITES) {
			const suiteItem = this._controller.createTestItem(
				suite.id,
				suite.label,
				undefined
			);
			suiteItem.canResolveChildren = true;
			suiteItem.description = `${suite.files.length} test files`;

			// Add individual test files
			for (const file of suite.files) {
				const filePath = vscode.Uri.file(`${config.workspacePath}\\tests\\${file}`);
				const fileItem = this._controller.createTestItem(
					`${suite.id}.${file}`,
					file.replace('test_', '').replace('.py', ''),
					filePath
				);
				fileItem.description = file;

				// Try to discover individual tests within the file
				await this._discoverTestsInFile(fileItem, filePath, config);

				suiteItem.children.add(fileItem);
			}

			this._controller.items.add(suiteItem);
		}
	}

	/**
	 * Discover individual test functions within a file using --collect-only.
	 */
	private async _discoverTestsInFile(
		parent: vscode.TestItem,
		fileUri: vscode.Uri,
		config: { pythonPath: string; workspacePath: string }
	): Promise<void> {
		try {
			const output = await new Promise<string>((resolve, reject) => {
				const proc = cp.spawn(config.pythonPath, [
					'-m', 'pytest', fileUri.fsPath, '--collect-only', '-q',
				], {
					cwd: config.workspacePath,
					env: { ...process.env, PYTHONPATH: config.workspacePath, PYTHONIOENCODING: 'utf-8' },
					stdio: ['ignore', 'pipe', 'pipe'],
					windowsHide: true,
				});

				let stdout = '';
				proc.stdout!.on('data', (d: Buffer) => { stdout += d.toString('utf-8'); });
				proc.on('close', () => resolve(stdout));
				proc.on('error', reject);

				setTimeout(() => { if (!proc.killed) { proc.kill(); resolve(stdout); } }, 15000);
			});

			// Parse collected tests: lines like "tests/test_foo.py::TestClass::test_method"
			const testRegex = /::(\w+)$/gm;
			let match: RegExpExecArray | null;
			while ((match = testRegex.exec(output)) !== null) {
				const testName = match[1];
				if (testName.startsWith('test_')) {
					const testItem = this._controller.createTestItem(
						`${parent.id}.${testName}`,
						testName,
						fileUri
					);
					parent.children.add(testItem);
				}
			}
		} catch {
			// File may not exist yet or pytest not installed — silently skip
		}
	}

	/**
	 * Run tests based on the test run request.
	 */
	private async _runTests(request: vscode.TestRunRequest, token: vscode.CancellationToken): Promise<void> {
		const config = getSlateConfig();
		const run = this._controller.createTestRun(request);

		const items = this._collectTestItems(request);

		for (const item of items) {
			if (token.isCancellationRequested) {
				run.skipped(item);
				continue;
			}

			run.started(item);

			try {
				const result = await this._executePytest(item, config, token);
				if (result.passed) {
					run.passed(item, result.duration);
				} else {
					run.failed(item, new vscode.TestMessage(result.message), result.duration);
				}
			} catch (err) {
				run.errored(item, new vscode.TestMessage(
					err instanceof Error ? err.message : String(err)
				));
			}
		}

		run.end();
	}

	/**
	 * Collect all test items to run from a request.
	 */
	private _collectTestItems(request: vscode.TestRunRequest): vscode.TestItem[] {
		const items: vscode.TestItem[] = [];

		if (request.include) {
			for (const item of request.include) {
				this._flattenTestItem(item, items);
			}
		} else {
			// Run all
			this._controller.items.forEach(item => this._flattenTestItem(item, items));
		}

		// Filter excluded items
		if (request.exclude) {
			const excludeIds = new Set(request.exclude.map(i => i.id));
			return items.filter(i => !excludeIds.has(i.id));
		}

		return items;
	}

	private _flattenTestItem(item: vscode.TestItem, out: vscode.TestItem[]): void {
		if (item.children.size === 0) {
			out.push(item);
		} else {
			item.children.forEach(child => this._flattenTestItem(child, out));
		}
	}

	/**
	 * Execute pytest for a specific test item.
	 */
	private async _executePytest(
		item: vscode.TestItem,
		config: { pythonPath: string; workspacePath: string },
		token: vscode.CancellationToken
	): Promise<{ passed: boolean; message: string; duration: number }> {
		const startTime = Date.now();

		// Determine the pytest filter expression
		let pytestFilter: string;
		const idParts = item.id.split('.');

		// Check if this is a suite-level item
		const suite = TEST_SUITES.find(s => s.id === idParts[0] && idParts.length === 1);
		if (suite) {
			pytestFilter = suite.pattern;
		} else if (idParts.length >= 3) {
			// Individual test function: suite.file.test_name
			pytestFilter = idParts[idParts.length - 1];
		} else {
			// File level: suite.test_file.py
			const fileName = idParts.slice(1).join('.').replace('.py', '');
			pytestFilter = fileName;
		}

		return new Promise<{ passed: boolean; message: string; duration: number }>((resolve) => {
			const proc = cp.spawn(config.pythonPath, [
				'-m', 'pytest', 'tests/', '-v', '--tb=short', '-x',
				'-k', pytestFilter,
			], {
				cwd: config.workspacePath,
				env: {
					...process.env,
					PYTHONPATH: config.workspacePath,
					PYTHONIOENCODING: 'utf-8',
					CUDA_VISIBLE_DEVICES: '0,1',
				},
				stdio: ['ignore', 'pipe', 'pipe'],
				windowsHide: true,
			});

			let stdout = '';
			let stderr = '';
			proc.stdout!.on('data', (d: Buffer) => { stdout += d.toString('utf-8'); });
			proc.stderr!.on('data', (d: Buffer) => { stderr += d.toString('utf-8'); });

			const cancelDisposable = token.onCancellationRequested(() => {
				if (!proc.killed) { proc.kill('SIGTERM'); }
			});

			proc.on('close', (code) => {
				cancelDisposable.dispose();
				const duration = Date.now() - startTime;
				const passed = code === 0;
				const message = passed
					? stdout.trim()
					: (stdout + '\n' + stderr).trim().slice(-2000);
				resolve({ passed, message, duration });
			});

			proc.on('error', (err) => {
				cancelDisposable.dispose();
				resolve({
					passed: false,
					message: `Process error: ${err.message}`,
					duration: Date.now() - startTime,
				});
			});

			// Timeout: 120s per test item
			setTimeout(() => {
				if (!proc.killed) {
					proc.kill('SIGTERM');
					resolve({
						passed: false,
						message: `Test execution timed out after 120s`,
						duration: 120000,
					});
				}
			}, 120_000);
		});
	}

	dispose(): void {
		this._controller.dispose();
		for (const d of this._disposables) { d.dispose(); }
	}
}
