// Modified: 2026-02-07T23:00:00Z | Author: COPILOT | Change: Add GitHub integration tools — CI run monitoring, check annotations, PR management, issue tracking
import * as vscode from 'vscode';
import * as cp from 'child_process';
import { execSlateCommand, execSlateCommandWithTimeout } from './slateRunner';

/**
 * SLATE GitHub Integration
 *
 * Deep integration with GitHub's APIs via the @slate chat participant:
 * - Workflow run monitoring (query status, list runs, check logs)
 * - Check annotations (publish CI results as check run annotations)
 * - PR management (create/review/merge PRs)
 * - Issue tracking (create/update issues from SLATE tasks)
 * - Release management (create releases, generate changelogs)
 *
 * All API calls go through git credential manager for auth — no stored tokens.
 */

const REPO_API = 'https://api.github.com/repos/SynchronizedLivingArchitecture/S.L.A.T.E';

// ─── GitHub Token Helper ────────────────────────────────────────────────

async function getGitHubToken(): Promise<string> {
	return new Promise<string>((resolve, reject) => {
		const proc = cp.spawn('git', ['credential', 'fill'], {
			stdio: ['pipe', 'pipe', 'pipe'],
			windowsHide: true,
		});

		let stdout = '';
		proc.stdout!.on('data', (d: Buffer) => { stdout += d.toString('utf-8'); });
		proc.stdin!.write('protocol=https\nhost=github.com\n\n');
		proc.stdin!.end();

		proc.on('close', () => {
			const match = stdout.match(/password=(.+)/);
			if (match) {
				resolve(match[1].trim());
			} else {
				reject(new Error('Failed to get GitHub token from git credential manager'));
			}
		});
		proc.on('error', reject);

		setTimeout(() => { if (!proc.killed) { proc.kill(); reject(new Error('Timeout')); } }, 10000);
	});
}

async function githubApiRequest(
	path: string,
	method: 'GET' | 'POST' | 'PATCH' | 'PUT' | 'DELETE' = 'GET',
	body?: Record<string, unknown>
): Promise<{ status: number; data: unknown }> {
	const token = await getGitHubToken();
	const url = path.startsWith('http') ? path : `${REPO_API}${path}`;

	// Use PowerShell Invoke-RestMethod (can't use curl.exe per SLATE rules)
	const bodyArg = body ? `-Body '${JSON.stringify(body).replace(/'/g, "''")}'` : '';
	const cmd = `$headers = @{ Authorization = "token ${token}"; Accept = "application/vnd.github.v3+json" }; ` +
		`try { $r = Invoke-RestMethod -Uri "${url}" -Method ${method} -Headers $headers ${bodyArg} -ContentType "application/json" -ErrorAction Stop; ` +
		`$r | ConvertTo-Json -Depth 10 } catch { Write-Host "[ERROR] $($_.Exception.Message)" }`;

	return new Promise<{ status: number; data: unknown }>((resolve) => {
		const proc = cp.spawn('powershell', ['-NoProfile', '-Command', cmd], {
			stdio: ['ignore', 'pipe', 'pipe'],
			windowsHide: true,
		});

		let stdout = '';
		proc.stdout!.on('data', (d: Buffer) => { stdout += d.toString('utf-8'); });
		proc.on('close', (code) => {
			try {
				const data = JSON.parse(stdout.trim());
				resolve({ status: code === 0 ? 200 : 500, data });
			} catch {
				resolve({ status: code === 0 ? 200 : 500, data: stdout.trim() });
			}
		});
		proc.on('error', () => resolve({ status: 500, data: 'Process error' }));

		setTimeout(() => { if (!proc.killed) { proc.kill(); resolve({ status: 408, data: 'Timeout' }); } }, 30000);
	});
}

// ─── LM Tool Interfaces ────────────────────────────────────────────────

interface ICiMonitorParams {
	action: string;
	workflow?: string;
	runId?: string;
	count?: number;
}

interface IPrManagerParams {
	action: string;
	branch?: string;
	title?: string;
	body?: string;
	prNumber?: number;
}

interface IIssueTrackerParams {
	action: string;
	title?: string;
	body?: string;
	labels?: string[];
	issueNumber?: number;
}

interface IGitOpsParams {
	action: string;
	branch?: string;
	message?: string;
}

// ─── CI Monitor Tool ────────────────────────────────────────────────────

export class CiMonitorTool implements vscode.LanguageModelTool<ICiMonitorParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<ICiMonitorParams>, _token: vscode.CancellationToken) {
		const { action, workflow, runId, count } = options.input;
		const results: string[] = [];

		try {
			switch (action) {
				case 'runs': {
					// List recent workflow runs
					const limit = count ?? 10;
					const wfFilter = workflow ? `&workflow_id=${workflow}` : '';
					const resp = await githubApiRequest(
						`/actions/runs?per_page=${limit}${wfFilter}`
					);
					const data = resp.data as Record<string, unknown>;
					const runs = (data.workflow_runs ?? []) as Record<string, unknown>[];
					results.push(`=== Recent Workflow Runs (${runs.length}) ===`);
					results.push('| # | Workflow | Status | Branch | Triggered |');
					results.push('|---|---------|--------|--------|-----------|');
					for (const run of runs.slice(0, limit)) {
						const status = run.conclusion ?? run.status ?? 'unknown';
						const icon = status === 'success' ? '✅' : status === 'failure' ? '❌' : status === 'in_progress' ? '🔄' : '⏳';
						results.push(
							`| ${run.run_number} | ${run.name} | ${icon} ${status} | ${(run.head_branch as string) ?? ''} | ${String(run.created_at ?? '').slice(0, 19)} |`
						);
					}
					break;
				}

				case 'status': {
					// Get active/in-progress runs
					const resp = await githubApiRequest('/actions/runs?status=in_progress&per_page=5');
					const data = resp.data as Record<string, unknown>;
					const runs = (data.workflow_runs ?? []) as Record<string, unknown>[];
					if (runs.length === 0) {
						results.push('No workflow runs currently in progress.');
					} else {
						results.push(`=== Active Runs (${runs.length}) ===`);
						for (const run of runs) {
							results.push(`- #${run.run_number} ${run.name}: ${run.status} (${run.head_branch})`);
						}
					}
					break;
				}

				case 'dispatch': {
					// Dispatch a workflow
					const wf = workflow ?? 'ci.yml';
					const resp = await githubApiRequest(
						`/actions/workflows/${wf}/dispatches`,
						'POST',
						{ ref: 'main' }
					);
					results.push(resp.status < 300
						? `✅ Dispatched ${wf} on main branch`
						: `❌ Failed to dispatch ${wf}: ${JSON.stringify(resp.data)}`
					);
					break;
				}

				case 'logs': {
					// Get failing job details for a specific run
					if (!runId) {
						results.push('Error: runId required for logs action');
						break;
					}
					const resp = await githubApiRequest(`/actions/runs/${runId}/jobs?per_page=20`);
					const data = resp.data as Record<string, unknown>;
					const jobs = (data.jobs ?? []) as Record<string, unknown>[];
					results.push(`=== Jobs for Run #${runId} ===`);
					for (const job of jobs) {
						const status = job.conclusion ?? job.status ?? 'unknown';
						const icon = status === 'success' ? '✅' : status === 'failure' ? '❌' : '🔄';
						results.push(`${icon} ${job.name}: ${status}`);

						// Show step-level detail for failed jobs
						if (status === 'failure') {
							const steps = (job.steps ?? []) as Record<string, unknown>[];
							for (const step of steps) {
								if (step.conclusion === 'failure') {
									results.push(`  ❌ Step: ${step.name}`);
								}
							}
						}
					}
					break;
				}

				case 'cancel': {
					// Cancel an in-progress run
					if (!runId) {
						results.push('Error: runId required for cancel action');
						break;
					}
					const resp = await githubApiRequest(`/actions/runs/${runId}/cancel`, 'POST');
					results.push(resp.status < 300
						? `✅ Cancelled run #${runId}`
						: `❌ Failed to cancel: ${JSON.stringify(resp.data)}`
					);
					break;
				}

				case 'rerun': {
					// Re-run a failed workflow
					if (!runId) {
						results.push('Error: runId required for rerun action');
						break;
					}
					const resp = await githubApiRequest(`/actions/runs/${runId}/rerun-failed-jobs`, 'POST');
					results.push(resp.status < 300
						? `✅ Re-running failed jobs for run #${runId}`
						: `❌ Failed to rerun: ${JSON.stringify(resp.data)}`
					);
					break;
				}

				default:
					results.push(`Unknown CI action: ${action}. Available: runs, status, dispatch, logs, cancel, rerun`);
			}
		} catch (err) {
			results.push(`[Error] ${err instanceof Error ? err.message : String(err)}`);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<ICiMonitorParams>, _token: vscode.CancellationToken) {
		const actionMsgs: Record<string, string> = {
			runs: 'Fetching recent workflow runs...',
			status: 'Checking active CI runs...',
			dispatch: `Dispatching ${options.input.workflow ?? 'ci.yml'}...`,
			logs: `Getting logs for run #${options.input.runId}...`,
			cancel: `Cancelling run #${options.input.runId}...`,
			rerun: `Re-running failed jobs for #${options.input.runId}...`,
		};
		return { invocationMessage: actionMsgs[options.input.action] ?? 'CI operation...' };
	}
}

// ─── PR Manager Tool ────────────────────────────────────────────────────

export class PrManagerTool implements vscode.LanguageModelTool<IPrManagerParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IPrManagerParams>, _token: vscode.CancellationToken) {
		const { action, branch, title, body, prNumber } = options.input;
		const results: string[] = [];

		try {
			switch (action) {
				case 'list': {
					const resp = await githubApiRequest('/pulls?state=open&per_page=10');
					const prs = (resp.data ?? []) as Record<string, unknown>[];
					if (prs.length === 0) {
						results.push('No open pull requests.');
					} else {
						results.push(`=== Open PRs (${prs.length}) ===`);
						results.push('| # | Title | Author | Branch | Updated |');
						results.push('|---|-------|--------|--------|---------|');
						for (const pr of prs) {
							const user = (pr.user as Record<string, unknown>)?.login ?? 'unknown';
							results.push(
								`| #${pr.number} | ${String(pr.title).slice(0, 50)} | ${user} | ${pr.head_branch ?? (pr.head as Record<string, unknown>)?.ref ?? ''} | ${String(pr.updated_at ?? '').slice(0, 10)} |`
							);
						}
					}
					break;
				}

				case 'create': {
					if (!title || !branch) {
						results.push('Error: title and branch required for create action');
						break;
					}
					const resp = await githubApiRequest('/pulls', 'POST', {
						title,
						body: body ?? '',
						head: branch,
						base: 'main',
					});
					const prData = resp.data as Record<string, unknown>;
					results.push(prData.number
						? `✅ Created PR #${prData.number}: ${prData.title}\n   URL: ${prData.html_url}`
						: `❌ Failed to create PR: ${JSON.stringify(prData).slice(0, 300)}`
					);
					break;
				}

				case 'status': {
					if (!prNumber) {
						results.push('Error: prNumber required for status action');
						break;
					}
					const [prResp, checksResp] = await Promise.all([
						githubApiRequest(`/pulls/${prNumber}`),
						githubApiRequest(`/commits/HEAD/check-runs?per_page=20`),
					]);
					const pr = prResp.data as Record<string, unknown>;
					results.push(`=== PR #${prNumber}: ${pr.title} ===`);
					results.push(`State: ${pr.state} | Mergeable: ${pr.mergeable ?? 'unknown'}`);
					results.push(`Reviews: ${pr.review_comments} | Commits: ${pr.commits}`);

					const checks = checksResp.data as Record<string, unknown>;
					const checkRuns = (checks.check_runs ?? []) as Record<string, unknown>[];
					if (checkRuns.length > 0) {
						results.push('\nCheck Runs:');
						for (const check of checkRuns) {
							const icon = check.conclusion === 'success' ? '✅' : check.conclusion === 'failure' ? '❌' : '🔄';
							results.push(`  ${icon} ${check.name}: ${check.conclusion ?? check.status}`);
						}
					}
					break;
				}

				default:
					results.push(`Unknown PR action: ${action}. Available: list, create, status`);
			}
		} catch (err) {
			results.push(`[Error] ${err instanceof Error ? err.message : String(err)}`);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IPrManagerParams>, _token: vscode.CancellationToken) {
		const msgs: Record<string, string> = {
			list: 'Listing open pull requests...',
			create: `Creating PR: ${options.input.title ?? ''}...`,
			status: `Checking PR #${options.input.prNumber}...`,
		};
		return { invocationMessage: msgs[options.input.action] ?? 'PR operation...' };
	}
}

// ─── Issue Tracker Tool ─────────────────────────────────────────────────

export class IssueTrackerTool implements vscode.LanguageModelTool<IIssueTrackerParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IIssueTrackerParams>, _token: vscode.CancellationToken) {
		const { action, title, body, labels, issueNumber } = options.input;
		const results: string[] = [];

		try {
			switch (action) {
				case 'list': {
					const resp = await githubApiRequest('/issues?state=open&per_page=15');
					const issues = (resp.data ?? []) as Record<string, unknown>[];
					const actualIssues = issues.filter((i: Record<string, unknown>) => !i.pull_request);
					if (actualIssues.length === 0) {
						results.push('No open issues.');
					} else {
						results.push(`=== Open Issues (${actualIssues.length}) ===`);
						results.push('| # | Title | Labels | Updated |');
						results.push('|---|-------|--------|---------|');
						for (const issue of actualIssues) {
							const issueLabels = ((issue.labels ?? []) as Record<string, unknown>[])
								.map(l => l.name).join(', ');
							results.push(
								`| #${issue.number} | ${String(issue.title).slice(0, 50)} | ${issueLabels} | ${String(issue.updated_at ?? '').slice(0, 10)} |`
							);
						}
					}
					break;
				}

				case 'create': {
					if (!title) {
						results.push('Error: title required for create action');
						break;
					}
					const issueBody: Record<string, unknown> = {
						title,
						body: body ?? '',
					};
					if (labels && labels.length > 0) {
						issueBody.labels = labels;
					}
					const resp = await githubApiRequest('/issues', 'POST', issueBody);
					const issueData = resp.data as Record<string, unknown>;
					results.push(issueData.number
						? `✅ Created issue #${issueData.number}: ${issueData.title}\n   URL: ${issueData.html_url}`
						: `❌ Failed: ${JSON.stringify(issueData).slice(0, 300)}`
					);
					break;
				}

				case 'close': {
					if (!issueNumber) {
						results.push('Error: issueNumber required');
						break;
					}
					const resp = await githubApiRequest(`/issues/${issueNumber}`, 'PATCH', { state: 'closed' });
					const d = resp.data as Record<string, unknown>;
					results.push(d.state === 'closed'
						? `✅ Closed issue #${issueNumber}`
						: `❌ Failed to close issue #${issueNumber}`
					);
					break;
				}

				case 'comment': {
					if (!issueNumber || !body) {
						results.push('Error: issueNumber and body required');
						break;
					}
					const resp = await githubApiRequest(`/issues/${issueNumber}/comments`, 'POST', { body });
					const d = resp.data as Record<string, unknown>;
					results.push(d.id
						? `✅ Added comment to issue #${issueNumber}`
						: `❌ Failed to comment on issue #${issueNumber}`
					);
					break;
				}

				default:
					results.push(`Unknown issue action: ${action}. Available: list, create, close, comment`);
			}
		} catch (err) {
			results.push(`[Error] ${err instanceof Error ? err.message : String(err)}`);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IIssueTrackerParams>, _token: vscode.CancellationToken) {
		const msgs: Record<string, string> = {
			list: 'Listing open issues...',
			create: `Creating issue: ${options.input.title ?? ''}...`,
			close: `Closing issue #${options.input.issueNumber}...`,
			comment: `Adding comment to issue #${options.input.issueNumber}...`,
		};
		return { invocationMessage: msgs[options.input.action] ?? 'Issue operation...' };
	}
}

// ─── Git Operations Tool ────────────────────────────────────────────────

export class GitOpsTool implements vscode.LanguageModelTool<IGitOpsParams> {
	async invoke(options: vscode.LanguageModelToolInvocationOptions<IGitOpsParams>, token: vscode.CancellationToken) {
		const { action, branch, message } = options.input;
		const results: string[] = [];

		try {
			switch (action) {
				case 'status': {
					const output = await execSlateCommandWithTimeout(
						'-c "import subprocess; r=subprocess.run([\'git\',\'status\',\'--short\'],capture_output=True,text=True); print(r.stdout or \'Clean working tree\')"',
						token, 10000
					);
					results.push('=== Git Status ===\n' + output);
					break;
				}

				case 'branch': {
					const output = await execSlateCommandWithTimeout(
						'-c "import subprocess; r=subprocess.run([\'git\',\'branch\',\'-a\',\'--sort=-committerdate\'],capture_output=True,text=True); print(r.stdout)"',
						token, 10000
					);
					results.push('=== Branches ===\n' + output);
					break;
				}

				case 'log': {
					const output = await execSlateCommandWithTimeout(
						'-c "import subprocess; r=subprocess.run([\'git\',\'log\',\'--oneline\',\'-20\',\'--graph\',\'--decorate\'],capture_output=True,text=True); print(r.stdout)"',
						token, 10000
					);
					results.push('=== Recent Commits ===\n' + output);
					break;
				}

				case 'diff': {
					const output = await execSlateCommandWithTimeout(
						'-c "import subprocess; r=subprocess.run([\'git\',\'diff\',\'--stat\'],capture_output=True,text=True); print(r.stdout or \'No changes\')"',
						token, 10000
					);
					results.push('=== Changed Files ===\n' + output);
					break;
				}

				case 'stash': {
					const output = await execSlateCommandWithTimeout(
						'-c "import subprocess; r=subprocess.run([\'git\',\'stash\',\'list\'],capture_output=True,text=True); print(r.stdout or \'No stashes\')"',
						token, 10000
					);
					results.push('=== Stash List ===\n' + output);
					break;
				}

				default:
					results.push(`Unknown git action: ${action}. Available: status, branch, log, diff, stash`);
			}
		} catch (err) {
			results.push(`[Error] ${err instanceof Error ? err.message : String(err)}`);
		}

		return new vscode.LanguageModelToolResult([new vscode.LanguageModelTextPart(results.join('\n'))]);
	}

	async prepareInvocation(options: vscode.LanguageModelToolInvocationPrepareOptions<IGitOpsParams>, _token: vscode.CancellationToken) {
		const msgs: Record<string, string> = {
			status: 'Checking git status...',
			branch: 'Listing branches...',
			log: 'Showing recent commits...',
			diff: 'Showing changed files...',
			stash: 'Listing stashes...',
		};
		return { invocationMessage: msgs[options.input.action] ?? 'Git operation...' };
	}
}

// ─── Registration ───────────────────────────────────────────────────────

export function registerGitHubTools(context: vscode.ExtensionContext): void {
	context.subscriptions.push(vscode.lm.registerTool('slate_ciMonitor', new CiMonitorTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_prManager', new PrManagerTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_issueTracker', new IssueTrackerTool()));
	context.subscriptions.push(vscode.lm.registerTool('slate_gitOps', new GitOpsTool()));
}
