// Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Agentic transformation — @slate is now an autonomous agent brain that plans, decides, delegates, and executes
import * as vscode from 'vscode';
import { getSystemState, type SlateSystemState } from './tools';

const SLATE_PARTICIPANT_ID = 'slate-copilot.slate';
const MAX_TOOL_ROUNDS = 20;         // Agents need room — plan + execute + verify
const MAX_HISTORY_TURNS = 4;        // Tighter history for agent focus
const HANDLER_TIMEOUT_MS = 900_000; // 15 min — autonomous agents may chain many operations

// ─────────────────────────────────────────────────────────────────────────────
// SYSTEM PROMPT — Complete Ecosystem-Driven Protocol
// The SLATE ecosystem has 21 subsystems organized in 8 dependent layers.
// Every tool call is part of a coherent process, not an isolated action.
// ─────────────────────────────────────────────────────────────────────────────
const SYSTEM_PROMPT = `You are SLATE — an autonomous AI agent that OWNS the development lifecycle of the S.L.A.T.E. project.
Version 2.5.0. ALL operations LOCAL ONLY (127.0.0.1).

## YOUR IDENTITY — AUTONOMOUS AGENT

You are NOT a chatbot. You are NOT a tool dispatcher. You are an AGENT.
You THINK, PLAN, DECIDE, EXECUTE, and VERIFY — autonomously.
The developer trusts you to make good decisions. Earn that trust.

### Agent Principles
1. **DECIDE, don't ask** — If the right action is clear, DO IT. Don't ask permission.
2. **PLAN before acting** — On complex requests, create an internal plan, then execute it.
3. **FIX what you find** — If something is broken during your work, fix it immediately.
4. **DELEGATE to subagents** — Use slate_handoff to route work to the right specialist agent.
5. **VERIFY your work** — After making changes, confirm they worked. Don't assume.
6. **MINIMIZE user effort** — The developer should receive COMPLETED work, not options.
7. **CHAIN operations** — Don't stop after one tool call. Keep going until the mission is done.
8. **REPORT outcomes** — Tell the developer what you DID, not what they could do.

### Auto-Decisions (act immediately, never ask)
- Services down → Start them via slate_startServices
- Stale tasks found → Clean them via slate_workflow(action="cleanup")
- GPU not optimized → Optimize via slate_hardwareInfo(optimize=true)
- Runner offline → Detect via slate_runnerStatus(action="detect")
- Pending work discovered → Execute via slate_executeWork or slate_handoff for each task
- Coverage gaps found → Write tests via slate_handoff or slate_autonomous(action="single")
- Security findings → Fix via slate_handoff then verify via slate_securityAudit
- Missing dependencies → Install via slate_checkDeps
- Completion rules violated → Enforce via slate_workflow(action="enforce")

## SUBAGENT DELEGATION

You are the ORCHESTRATOR. You have 8 specialist subagents. Route work to the right one:

| Agent | Specialty | Route when... | Tool |
|-------|-----------|---------------|------|
| ALPHA | Coding | implement, build, fix, refactor | slate_handoff(task, priority="high") |
| BETA | Testing | test, validate, verify, coverage gaps | slate_handoff(task, priority="medium") |
| GAMMA | Planning | analyze, plan, research, document | slate_handoff(task, priority="low") |
| DELTA | Integration | MCP, SDK, external bridge | slate_handoff(task) |
| COPILOT | Full orchestration | complex multi-step work | slate_executeWork(scope="full") |

When you discover work:
1. Classify the task type (code / test / plan / infra / security)
2. Route to the appropriate subagent via slate_handoff
3. For urgent items, execute directly via slate_autonomous(action="single")
4. For complex work, use slate_executeWork to chain discover→cleanup→execute→verify

## PLANNING PROTOCOL

For any non-trivial request:
1. **Gather context** — Call slate_planContext first to get current state (stage, tasks, specs)
2. **Assess situation** — What's running? What's broken? What's pending?
3. **Create plan** — List the steps you'll take (share with user as a brief outline)
4. **Execute sequentially** — Do each step, adapting based on results
5. **Verify outcome** — Confirm the mission succeeded
6. **Report delta** — Show BEFORE → AFTER for what changed

## ENVIRONMENT

- Python: 3.11.9 at <workspace>/.venv/Scripts/python.exe
- Runner: slate-runner [self-hosted, Windows, X64, slate, gpu, cuda, gpu-2, blackwell]
- GPUs: 2x NVIDIA GeForce RTX 5070 Ti (Blackwell, CC 12.0, 16 GB each)
- CUDA_VISIBLE_DEVICES: 0,1
- SLATE Models: slate-coder (12B, GPU 0), slate-fast (3B, GPU 1), slate-planner (7B, GPU 0)
- Agents: 8 registered (ALPHA, BETA, GAMMA, DELTA, EPSILON, ZETA, COPILOT, COPILOT_CHAT)

## ECOSYSTEM — 8 LAYERS

SLATE is layered. Fix the LOWEST broken layer first. Progress upward.

| # | Layer | Tools |
|---|-------|-------|
| 1 | Foundation | slate_systemStatus, slate_runtimeCheck, slate_checkDeps |
| 2 | Hardware | slate_hardwareInfo, slate_gpuManager |
| 3 | Infrastructure | slate_runnerStatus, slate_orchestrator, slate_startServices |
| 4 | AI Pipeline | slate_gpuManager(preload), slate_runtimeCheck |
| 5 | Agent Registry | slate_agentStatus, slate_agentBridge |
| 6 | Services | slate_orchestrator, slate_startServices |
| 7 | Task Mgmt | slate_workflow, slate_autonomous, slate_executeWork, slate_handoff |
| 8 | Quality | slate_securityAudit, slate_benchmark, slate_forkCheck |
| + | Roadmap | slate_planContext, slate_devCycle, slate_specKit, slate_codeGuidance |

## TOOL USAGE — 20 rounds available

You have 20 tool rounds. Use them aggressively:
- Rounds 1-2: Context gathering (slate_planContext + slate_systemStatus)
- Rounds 3-8: Primary mission execution
- Rounds 9-14: Subagent delegation and secondary work
- Rounds 15-18: Verification and remediation
- Rounds 19-20: Final state report

Call MULTIPLE tools per round when they're independent. Don't waste rounds on single calls.
The escape hatch is slate_runCommand — any SLATE Python script can be run.

## OUTPUT FORMAT
- ✅/❌/⚠️ indicators for quick scanning
- Markdown tables for structured data
- BEFORE → AFTER for state changes
- End with what you DID and what you DELEGATED
- Never end with "you can" or "try running" — end with ACTIONS TAKEN
- Keep it concise — developers don't read walls of text`;

// ─────────────────────────────────────────────────────────────────────────────
// COMMAND PROMPTS — Each maps to a multi-phase ecosystem process
// ─────────────────────────────────────────────────────────────────────────────
const COMMAND_PROMPTS: Record<string, string> = {
	// ─── /run — AUTONOMOUS FULL PROTOCOL ─────────────────────────────────
	run: `MISSION: Execute the complete SLATE protocol autonomously. You are the agent — own this.

Your plan:
1. Gather state: slate_planContext(scope="full") + slate_systemStatus(quick=true) + slate_runtimeCheck (parallel)
2. Assess hardware: slate_hardwareInfo + slate_gpuManager(action="status") — optimize if needed
3. Infrastructure: slate_orchestrator(action="status") + slate_runnerStatus(action="status") — start services if ANY are down
4. Agents: slate_agentStatus(action="status") — verify all 8 agents
5. Tasks: slate_workflow(action="status") → cleanup stale → enforce completion
6. Work: slate_autonomous(action="discover") → execute or delegate discovered tasks
7. Security: slate_securityAudit(scan="quick") — hand off fixes if needed
8. Verify: slate_systemStatus(quick=true) final check

AUTO-DECISIONS during execution:
- Services down → start them immediately, don't report and wait
- Stale tasks → clean them, don't ask
- Coverage gaps → delegate to BETA agent via slate_handoff
- Security findings → delegate fixes to ALPHA agent via slate_handoff
- GPU not optimized → optimize immediately

Report a concise BEFORE→AFTER delta table at the end. Show what you FIXED, not just what you checked.`,
  Call slate_agentStatus(action="status").
  Check: all 8 agents discovered and healthy (ALPHA, BETA, GAMMA, DELTA, EPSILON, ZETA, COPILOT, COPILOT_CHAT).
  If agents missing → note for remediation.

PHASE 5 — Task Management:
  Call slate_workflow(action="status").
  If stale tasks → call slate_workflow(action="cleanup").
  Call slate_workflow(action="enforce") to ensure completion rules.

PHASE 6 — Work Discovery & Execution:
  Call slate_autonomous(action="discover").
  If tasks found → call slate_executeWork(scope="full") or slate_handoff for each significant task.

PHASE 7 — Security & Quality:
  Call slate_securityAudit(scan="quick").
  If findings → hand off code fixes with slate_handoff.
  Call slate_checkDeps to verify dependency health.

PHASE 8 — Final Verification:
  Call slate_systemStatus(quick=true) one final time.
  Compare against Phase 1 results. Report BEFORE→AFTER delta for every layer.
  Show ecosystem status table: Layer | Status | Action Taken.`,

	// ─── /status — Quick autonomous health scan ─────────────────────────
	status: `MISSION: Rapid health assessment + auto-fix. Be an agent, not a reporter.

1. Call slate_systemStatus(quick=true) AND slate_runtimeCheck AND slate_orchestrator(action="status") — all in parallel
2. Call slate_workflow(action="status") AND slate_runnerStatus(action="status")
3. AUTO-FIX anything broken: start services, clean stale tasks, detect runner
4. Present ONE unified table: Subsystem | Status | Action Taken

Don't just report — FIX and report what you fixed.`,

	// ─── /debug — Autonomous deep diagnostic agent ─────────────────────
	debug: `MISSION: Deep diagnostic with full auto-remediation. You are a repair agent.

1. Scan ALL layers: slate_systemStatus + slate_runtimeCheck + slate_hardwareInfo + slate_orchestrator(action="status")
2. Check agents + tasks: slate_agentStatus + slate_workflow(action="status") + slate_autonomous(action="discover")
3. For EVERY issue found, FIX IT immediately — don't list issues to fix later:
   - Services down → slate_startServices(services="all")
   - Stale tasks → slate_workflow(action="cleanup")
   - GPU issues → slate_hardwareInfo(optimize=true)
   - Pending work → slate_handoff for each significant task
   - Runner offline → slate_runnerStatus(action="detect")
4. Verify: slate_systemStatus(quick=true) again
5. Report: BEFORE→AFTER table for every layer. Show what you repaired.

You are a REPAIR agent. Don't diagnose and report — diagnose and FIX.`,

	// ─── /deploy — Autonomous service deployment ───────────────────────
	deploy: `MISSION: Bring ALL services online. Don't check first — just start everything.

1. slate_startServices(services="all") — start immediately
2. slate_orchestrator(action="status") + slate_runnerStatus(action="status") — verify
3. slate_agentStatus(action="status") — confirm agents reachable
4. If anything failed → retry once, then report the failure

Report: service name | was | now. Concise table.`,

	// ─── /runner — Runner agent ─────────────────────────────────────────
	runner: `MISSION: Ensure the runner is healthy and ready to accept work.

1. slate_runnerStatus(action="status") — check current state
2. If offline → slate_runnerStatus(action="detect") AND stale tasks → slate_workflow(action="cleanup")
3. Report runner state and actions taken.`,

	// ─── /ci — CI dispatch agent ───────────────────────────────────────
	ci: `MISSION: Check CI and dispatch if appropriate.

1. slate_runnerStatus(action="status") — check for active/queued runs
2. If runner is idle and user wants dispatch → slate_runnerStatus(action="dispatch", workflow="ci.yml")
3. Clean stale tasks if found: slate_workflow(action="cleanup")
4. Report: active runs, dispatched workflows, cleaned tasks.`,

	// ─── /hardware — GPU optimization agent ─────────────────────────────
	hardware: `MISSION: Optimize GPU and AI pipeline. Don't just check — optimize.

1. slate_hardwareInfo + slate_gpuManager(action="status") — gather GPU state
2. If not optimized → slate_hardwareInfo(optimize=true) immediately
3. If models not loaded → slate_gpuManager(action="preload") immediately
4. slate_runtimeCheck — verify Ollama/PyTorch/ChromaDB
5. Report: GPU table with VRAM, model assignments, optimizations applied.`,

	// ─── /agents — Agent orchestration mission ─────────────────────────
	agents: `MISSION: You are the orchestrator. Discover work, delegate it, execute it.

1. slate_agentStatus(action="status") + slate_autonomous(action="discover") — find what needs doing
2. slate_agentBridge(action="poll") — check for bridge tasks from autonomous loop
3. For EACH discovered task, make a DECISION:
   - Code task → slate_handoff(task, priority="high") to ALPHA agent
   - Test task → slate_handoff(task, priority="medium") to BETA agent
   - Plan task → slate_handoff(task, priority="low") to GAMMA agent
   - Quick fix → slate_autonomous(action="single") to execute immediately
4. If copilot runner is stopped → slate_startServices immediately
5. Report: tasks discovered | tasks delegated (to which agent) | tasks executed directly

You are an ORCHESTRATOR. Don't just list tasks — assign them and start execution.`,

	// ─── /security — Security agent ─────────────────────────────────────
	security: `MISSION: Audit security and auto-remediate findings.

1. slate_securityAudit(scan="full") + slate_checkDeps — parallel scan
2. slate_forkCheck(action="check") — fork security
3. For ANY finding → slate_handoff to ALPHA agent for code fix
4. Re-scan to verify remediation
5. Report: finding | severity | action taken | verified.`,

	// ─── /benchmark — Performance agent ────────────────────────────────
	benchmark: `MISSION: Run benchmarks and report performance.

1. slate_benchmark + slate_hardwareInfo — parallel execution
2. Present results table with pass/fail
3. If GPU underperforming → slate_hardwareInfo(optimize=true)`,

	// ─── /orchestrator — Service lifecycle agent ────────────────────────
	orchestrator: `MISSION: Ensure all services are running. Start first, ask questions never.

1. slate_orchestrator(action="status") — check what's running
2. If ANYTHING is stopped → slate_startServices(services="all") immediately
3. Verify with slate_orchestrator(action="status")
4. Report: service | was | now.`,

	// ─── /install — Installation agent ─────────────────────────────────
	install: `MISSION: Full ecosystem install. Execute slate_install and monitor all 21 steps.
Don't pause between steps — let the installer run and report the outcome.`,

	// ─── /update — Update agent ────────────────────────────────────────
	update: `MISSION: Update SLATE and verify nothing broke.

1. slate_update — pull + refresh deps
2. slate_forkCheck(action="check") — sync forks if updates available
3. slate_runtimeCheck + slate_checkDeps — verify everything still works
4. Report: what changed, what was verified, any issues.`,

	// ─── /forks — Fork sync agent ──────────────────────────────────────
	forks: `MISSION: Sync all forks and verify security.

1. slate_forkCheck(action="check") — scan
2. If updates → slate_forkCheck(action="sync") immediately
3. slate_securityAudit(scan="quick") — verify security post-sync
4. Report: forks synced, security status.`,

	// ─── /roadmap — Roadmap alignment agent ─────────────────────────────
	roadmap: `MISSION: Assess roadmap alignment and take corrective action.

1. slate_planContext(scope="full") + slate_devCycle(action="status") — parallel
2. slate_specKit(action="list") + slate_workflow(action="status") — parallel
3. DECIDE: Are tasks aligned with the current dev stage? If not, create/delegate alignment tasks.
4. Report: stage, iteration, specs status, task alignment, recommended actions — then DO the recommendations.`,

	// ─── /stage — Dev stage agent ───────────────────────────────────────
	stage: `MISSION: Manage development stage transitions.

1. slate_devCycle(action="status") + slate_devCycle(action="guidance")
2. If user wants transition → slate_devCycle(action="transition", stage="<target>") immediately
3. After transition → auto-update task priorities to match new stage

Stages: PLAN → CODE → TEST → DEPLOY → FEEDBACK → (cycle)`,

	// ─── /guidance — Code guidance agent ────────────────────────────────
	guidance: `MISSION: Provide actionable code guidance based on current stage.

1. slate_planContext(scope="full") + slate_codeGuidance — parallel
2. slate_specKit(action="roadmap") — get spec requirements
3. Synthesize into a CONCRETE list: what to code next, patterns to follow, files to touch.`,

	// ─── /learn — Learning agent ───────────────────────────────────────
	learn: `MISSION: Track and advance learning progress.

1. slate_learningProgress(action="status") + slate_learningProgress(action="achievements")
2. slate_learningProgress(action="next") — get next step
3. If step is completable now → slate_learningProgress(action="complete", stepId) immediately
4. Report: XP, level, next step, progress bar.`,

	// ─── /specs — Spec processing agent ────────────────────────────────
	specs: `MISSION: Process all specifications autonomously.

1. slate_specKit(action="status") + slate_specKit(action="list")
2. If unprocessed specs → slate_specKit(action="process") immediately
3. If analysis needed → slate_specKit(action="analyze") immediately
4. Report: specs processed, analysis results, any wiki generated.`,

	// ─── /context — Fast context agent ─────────────────────────────────
	context: `MISSION: Get compressed context in one call for efficient operation.

Call slate_planContext(scope="full"). Return the compressed context line.
This is the TOKEN SAVER — use before complex operations.`,

	help: '',
};

export function registerSlateParticipant(context: vscode.ExtensionContext) {
	const handler: vscode.ChatRequestHandler = async (
		request: vscode.ChatRequest,
		chatContext: vscode.ChatContext,
		stream: vscode.ChatResponseStream,
		token: vscode.CancellationToken
	) => {
		const startTime = Date.now();

		// Handle /help command directly (no LLM needed)
		if (request.command === 'help') {
			renderHelp(stream);
			return { metadata: { command: 'help' } };
		}

		// Build the prompt — Agent Brain Architecture
		// Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Auto-context injection for autonomous agent
		let systemMessage = SYSTEM_PROMPT;
		if (request.command && COMMAND_PROMPTS[request.command]) {
			systemMessage += '\n\n## ACTIVE MISSION\n' + COMMAND_PROMPTS[request.command];
		}

		// Inject auto-context: always tell the agent what resources it has
		systemMessage += `\n\n## AUTO-CONTEXT (injected by handler)
Available tool count: ${vscode.lm.tools.filter(t => t.tags.includes('slate')).length} SLATE tools
Handler config: MAX_TOOL_ROUNDS=${MAX_TOOL_ROUNDS}, TIMEOUT=${HANDLER_TIMEOUT_MS / 1000}s
Current time: ${new Date().toISOString()}
Last command: ${request.command ?? 'free-chat'}
User prompt length: ${(request.prompt || '').length} chars

REMEMBER: You are an AGENT. Plan → Execute → Verify → Report outcomes. Don't ask — DO.`;

		const messages: vscode.LanguageModelChatMessage[] = [
			vscode.LanguageModelChatMessage.User(systemMessage),
		];

		// Add LIMITED conversation history (prevent context overflow)
		const previousTurns = chatContext.history.filter(
			(h) => h instanceof vscode.ChatResponseTurn
		);
		const recentTurns = previousTurns.slice(-MAX_HISTORY_TURNS);
		for (const m of recentTurns) {
			let fullMessage = '';
			for (const r of m.response) {
				const mdPart = r as vscode.ChatResponseMarkdownPart;
				if (mdPart?.value?.value) {
					fullMessage += mdPart.value.value;
				}
			}
			// Truncate long history entries to prevent context overflow
			if (fullMessage.length > 1500) {
				fullMessage = fullMessage.slice(0, 1500) + '\n[...truncated]';
			}
			if (fullMessage) {
				messages.push(vscode.LanguageModelChatMessage.Assistant(fullMessage));
			}
		}

		// Add user message — enhance vague requests so the agent takes action
		let userPrompt = request.prompt || (request.command ? `Run /${request.command}` : 'Show system status');
		// For bare commands with no user text, inject agentic framing
		if (!request.prompt && request.command) {
			userPrompt = `Execute the /${request.command} mission autonomously. Follow the mission plan. Fix anything broken. Report outcomes.`;
		}
		messages.push(vscode.LanguageModelChatMessage.User(userPrompt));

		// Get SLATE-tagged tools  
		const slateTools = vscode.lm.tools.filter(tool => tool.tags.includes('slate'));
		if (slateTools.length === 0) {
			stream.markdown('⚠️ **No SLATE tools registered.** The extension may not have activated properly.\n\n');
			stream.markdown('Try reloading VS Code: `Ctrl+Shift+P` → "Developer: Reload Window"\n');
			return { metadata: { command: request.command ?? 'chat', error: 'no-tools' } };
		}

		const options: vscode.LanguageModelChatRequestOptions = {
			justification: 'SLATE system operations via @slate',
			tools: slateTools.map(t => ({
				name: t.name,
				description: t.description,
				inputSchema: t.inputSchema,
			})),
		};

		// If user explicitly referenced a tool, force it for the first round
		const toolReferences = [...request.toolReferences];
		const requestedTool = toolReferences.shift();
		if (requestedTool) {
			options.toolMode = vscode.LanguageModelChatToolMode.Required;
			options.tools = slateTools
				.filter(tool => tool.name === requestedTool.name)
				.map(t => ({ name: t.name, description: t.description, inputSchema: t.inputSchema }));
		}

		// ─── Tool-Calling Loop with Progress Streaming ───────────────────
		let totalToolCalls = 0;

		for (let round = 0; round < MAX_TOOL_ROUNDS; round++) {
			// Check cancellation and timeout at top of each round
			if (token.isCancellationRequested) {
				stream.markdown('\n\n⚠️ *Operation cancelled.*\n');
				break;
			}
			if (Date.now() - startTime > HANDLER_TIMEOUT_MS) {
				stream.markdown('\n\n⏱ *Agent timed out after 15 minutes. Use a more specific command to narrow the mission.*\n');
				break;
			}

			// Show progress for rounds after the first
			if (round > 0) {
				stream.progress(`Processing results (step ${round + 1})...`);
			}

			let response: vscode.LanguageModelChatResponse;
			try {
				response = await request.model.sendRequest(messages, options, token);
			} catch (err) {
				const errMsg = err instanceof Error ? err.message : String(err);
				if (errMsg.includes('cancelled') || token.isCancellationRequested) {
					stream.markdown('\n\n⚠️ *Operation cancelled.*\n');
				} else {
					stream.markdown(`\n\n❌ **Model error:** ${errMsg}\n\n`);
					stream.markdown('Try again or use a specific command like `/status` or `/debug`.\n');
				}
				return { metadata: { command: request.command ?? 'chat', error: errMsg } };
			}

			const toolCalls: vscode.LanguageModelToolCallPart[] = [];
			let responseText = '';

			try {
				for await (const part of response.stream) {
					if (token.isCancellationRequested) { break; }
					if (part instanceof vscode.LanguageModelTextPart) {
						stream.markdown(part.value);
						responseText += part.value;
					} else if (part instanceof vscode.LanguageModelToolCallPart) {
						toolCalls.push(part);
					}
				}
			} catch (streamErr) {
				const errMsg = streamErr instanceof Error ? streamErr.message : String(streamErr);
				if (!errMsg.includes('cancelled')) {
					stream.markdown(`\n\n⚠️ *Stream interrupted: ${errMsg}*\n`);
				}
				break;
			}

			// If no tool calls, LLM is done responding
			if (toolCalls.length === 0) {
				break;
			}

			// Process tool calls with progress feedback
			messages.push(vscode.LanguageModelChatMessage.Assistant(
				toolCalls.map(tc => new vscode.LanguageModelToolCallPart(tc.callId, tc.name, tc.input))
			));

			for (const toolCall of toolCalls) {
				if (token.isCancellationRequested) { break; }

				totalToolCalls++;
				const toolDisplayName = getToolDisplayName(toolCall.name);
				stream.progress(`⚙ ${toolDisplayName}...`);

				const toolStartTime = Date.now();
				try {
					const result = await vscode.lm.invokeTool(toolCall.name, {
						input: toolCall.input,
						toolInvocationToken: request.toolInvocationToken,
					}, token);

					const elapsed = ((Date.now() - toolStartTime) / 1000).toFixed(1);

					// Extract text from result
					const textParts: string[] = [];
					for (const part of result.content) {
						if (part instanceof vscode.LanguageModelTextPart) {
							textParts.push(part.value);
						}
					}

					const resultText = textParts.join('\n') || '[no output]';
					messages.push(vscode.LanguageModelChatMessage.User([
						new vscode.LanguageModelToolResultPart(toolCall.callId, [
							new vscode.LanguageModelTextPart(`[${toolDisplayName} completed in ${elapsed}s]\n${resultText}`)
						])
					]));
				} catch (err) {
					const elapsed = ((Date.now() - toolStartTime) / 1000).toFixed(1);
					const errorMsg = err instanceof Error ? err.message : String(err);

					// Don't silently swallow errors — put them in context so the LLM can report them
					messages.push(vscode.LanguageModelChatMessage.User([
						new vscode.LanguageModelToolResultPart(toolCall.callId, [
							new vscode.LanguageModelTextPart(
								`[${toolDisplayName} FAILED after ${elapsed}s]\nError: ${errorMsg}\n\nReport this error to the user and suggest how to fix it.`
							)
						])
					]));
				}
			}

			// After first round, clear forced tool mode so LLM can synthesize results
			options.toolMode = undefined;
			options.tools = slateTools.map(t => ({
				name: t.name,
				description: t.description,
				inputSchema: t.inputSchema,
			}));
		}

		// Show elapsed time for operations that used tools
		if (totalToolCalls > 0) {
			const totalElapsed = ((Date.now() - startTime) / 1000).toFixed(1);
			stream.progress(`✓ Completed ${totalToolCalls} operation${totalToolCalls > 1 ? 's' : ''} in ${totalElapsed}s`);
		}

		return { metadata: { command: request.command ?? 'chat', prompt: request.prompt, toolCalls: totalToolCalls, systemState: getSystemState() } };
	};

	const slate = vscode.chat.createChatParticipant(SLATE_PARTICIPANT_ID, handler);
	slate.iconPath = new vscode.ThemeIcon('server-environment');

	// ─── State-Aware Adaptive Follow-up Provider ────────────────────────
	slate.followupProvider = {
		provideFollowups(result: vscode.ChatResult, _context: vscode.ChatContext, _token: vscode.CancellationToken) {
			const meta = result.metadata as Record<string, unknown> ?? {};
			const command = (meta.command as string) ?? 'chat';
			const state = (meta.systemState as SlateSystemState) ?? getSystemState();
			return getStateAwareFollowups(command, state);
		}
	};

	context.subscriptions.push(slate);
}

/** Map internal tool names to user-friendly display names */
function getToolDisplayName(toolName: string): string {
	const names: Record<string, string> = {
		slate_systemStatus: 'System Health',
		slate_runtimeCheck: 'Runtime Check',
		slate_runnerStatus: 'Runner Status',
		slate_hardwareInfo: 'Hardware Info',
		slate_orchestrator: 'Orchestrator',
		slate_workflow: 'Workflow Manager',
		slate_benchmark: 'Benchmarks',
		slate_runCommand: 'Run Command',
		slate_install: 'Installer',
		slate_update: 'Updater',
		slate_checkDeps: 'Dependency Check',
		slate_forkCheck: 'Fork Check',
		slate_securityAudit: 'Security Audit',
		slate_agentStatus: 'Agent Status',
		slate_gpuManager: 'GPU Manager',
		slate_autonomous: 'Autonomous Loop',
		slate_runProtocol: 'SLATE Protocol',
		slate_handoff: 'Task Handoff',
		slate_startServices: 'Start Services',
		slate_executeWork: 'Execute Work Pipeline',
		slate_agentBridge: 'Agent Bridge',
		// Roadmap & Plan Awareness tools
		slate_devCycle: 'Dev Cycle',
		slate_specKit: 'Spec-Kit',
		slate_learningProgress: 'Learning Progress',
		slate_planContext: 'Plan Context',
		slate_codeGuidance: 'Code Guidance',
	};
	return names[toolName] ?? toolName;
}

/** Render /help output directly (no LLM round-trip needed) */
function renderHelp(stream: vscode.ChatResponseStream) {
	stream.markdown('## SLATE Autonomous Agent Commands\n\n');
	stream.markdown('SLATE is an **autonomous agent** that plans, decides, executes, and verifies.\n');
	stream.markdown('Every command is a **mission** — SLATE will work through it autonomously.\n\n');
	stream.markdown('### Full Missions\n');
	stream.markdown('| Command | Scope | Mission |\n|---------|-------|---------|\n');
	stream.markdown('| `/run` | **All layers** | Complete protocol: health → GPU → services → agents → tasks → security |\n');
	stream.markdown('| `/debug` | **All layers** | Deep diagnostic + auto-repair every issue found |\n');
	stream.markdown('| `/install` | **All layers** | Full 21-step ecosystem install |\n\n');
	stream.markdown('### Agent Missions\n');
	stream.markdown('| Command | Mission |\n|---------|---------|\n');
	stream.markdown('| `/status` | Quick health scan + auto-fix |\n');
	stream.markdown('| `/deploy` | Start all services immediately |\n');
	stream.markdown('| `/hardware` | Optimize GPU + preload models |\n');
	stream.markdown('| `/agents` | Discover work → delegate to subagents → execute |\n');
	stream.markdown('| `/security` | Audit + auto-remediate findings |\n');
	stream.markdown('| `/benchmark` | Run performance benchmarks |\n');
	stream.markdown('| `/runner` | Ensure runner is healthy |\n');
	stream.markdown('| `/ci` | Check CI + dispatch if appropriate |\n');
	stream.markdown('| `/orchestrator` | Start stopped services |\n');
	stream.markdown('| `/update` | Pull + verify nothing broke |\n');
	stream.markdown('| `/forks` | Sync forks + verify security |\n\n');
	stream.markdown('### Roadmap & Planning\n');
	stream.markdown('| Command | Mission |\n|---------|---------|\n');
	stream.markdown('| `/roadmap` | Assess alignment + take corrective action |\n');
	stream.markdown('| `/stage` | View/change dev stage (PLAN→CODE→TEST→DEPLOY→FEEDBACK) |\n');
	stream.markdown('| `/guidance` | Get actionable code guidance for current stage |\n');
	stream.markdown('| `/context` | Token-efficient compressed state (TOKEN SAVER) |\n');
	stream.markdown('| `/specs` | Process all specs autonomously |\n');
	stream.markdown('| `/learn` | Track learning progress + auto-advance |\n\n');
	stream.markdown('**26 Tools** | **20 tool rounds per request** | **15 min timeout**\n');
	stream.markdown('\n> **Tip:** Just talk to @slate naturally. Commands are optional — the agent will figure out what to do.\n');
}

// ─── Action-Oriented Follow-up Buttons ──────────────────────────────────
// Modified: 2026-02-07T16:00:00Z | Author: COPILOT | Change: Agentic follow-ups that drive autonomous execution
// Follow-up buttons represent MISSIONS the agent can take next.
// Focus on ACTION, not inspection. The agent should DO things.
// Always shows exactly 5 buttons.

interface SlateFollowup extends vscode.ChatFollowup {
	prompt: string;
	label: string;
	command?: string;
}

function getStateAwareFollowups(lastCommand: string, state: SlateSystemState): SlateFollowup[] {
	// ─── SLATE's 5 Agent Action Pillars ────────────────────
	// Every button triggers an AUTONOMOUS MISSION, not a report.
	// State awareness determines which missions are most valuable next.

	const pillars: SlateFollowup[] = [];

	// Pillar 1: Roadmap Alignment — always show stage-relevant action
	const devStage = state.currentDevStage || 'code';
	const stageActions: Record<string, { prompt: string; label: string }> = {
		plan: { prompt: 'Analyze active specs and create implementation tasks for PLAN stage', label: 'Plan next work' },
		code: { prompt: 'Get coding priorities, then delegate implementation tasks to ALPHA agent', label: 'Code next task' },
		test: { prompt: 'Discover test coverage gaps and delegate test writing to BETA agent', label: 'Write tests' },
		deploy: { prompt: 'Verify CI passes, check runner, prepare for merge', label: 'Prep deploy' },
		feedback: { prompt: 'Review achievements, analyze patterns, plan next iteration', label: 'Review cycle' },
	};
	const stageAction = stageActions[devStage] ?? stageActions.code;
	pillars.push({ prompt: stageAction.prompt, label: stageAction.label, command: 'guidance' });

	// Pillar 2: System Operations — prioritize broken things
	if (!state.servicesUp) {
		pillars.push({ prompt: 'Start all SLATE services immediately, verify they\'re running, report what changed', label: 'Fix services', command: 'deploy' });
	} else {
		pillars.push({ prompt: 'Execute full protocol autonomously: check all 8 layers, fix any issues, execute pending work', label: 'Full protocol', command: 'run' });
	}

	// Pillar 3: Work Execution — the agent's main value proposition
	if (state.pendingTasks > 0 || state.discoveredTasks > 5) {
		pillars.push({ prompt: 'Discover all available tasks, delegate each to the right subagent (ALPHA/BETA/GAMMA), execute immediately', label: 'Execute all work', command: 'agents' });
	} else {
		pillars.push({ prompt: 'Check roadmap alignment, find misaligned tasks, create corrective actions', label: 'Align roadmap', command: 'roadmap' });
	}

	// Pillar 4: Auto-repair
	pillars.push({ prompt: 'Run deep diagnostics on every system — find AND fix every issue automatically', label: 'Auto-repair', command: 'debug' });

	// Pillar 5: GPU/Context — fill the last slot with the most useful action
	if (!state.gpuLoaded) {
		pillars.push({ prompt: 'Optimize GPUs, preload SLATE models, configure dual-GPU load balancing', label: 'Optimize GPU', command: 'hardware' });
	} else {
		pillars.push({ prompt: 'Get compressed context, then execute the highest-priority pending task', label: 'Next task', command: 'context' });
	}

	// ─── State-driven swaps ──────────────────────────────────────────
	// If we just ran the command that a pillar maps to, swap it out
	// for an alternative so the user always sees fresh options

	const swaps: Record<string, SlateFollowup> = {
		run: { prompt: 'Show full system status: health, GPU, services, runtime integrations', label: 'System status', command: 'status' },
		deploy: { prompt: 'Check CI/CD runner status, dispatch workflows if needed', label: 'Check runner', command: 'runner' },
		agents: { prompt: 'Check GPU utilization and dual-GPU load balancing status, optimize if needed', label: 'GPU status', command: 'hardware' },
		debug: { prompt: 'Check and sync contributor forks for pending integrations', label: 'Sync forks', command: 'forks' },
		security: { prompt: 'Update SLATE from git, refresh dependencies, sync forks, verify runtime', label: 'Update SLATE', command: 'update' },
		hardware: { prompt: 'Run full SLATE lock-in protocol: health, runtime, workflow, enforce', label: 'Run protocol', command: 'run' },
		benchmark: { prompt: 'Execute the SLATE work pipeline: cleanup, discover, execute tasks, verify', label: 'Execute tasks', command: 'agents' },
		status: { prompt: 'Run deep diagnostics, fix any issues found, verify fixes', label: 'Deep diagnose', command: 'debug' },
		runner: { prompt: 'Dispatch CI workflow to validate system state', label: 'Dispatch CI', command: 'ci' },
		ci: { prompt: 'Start all SLATE services and verify deployment', label: 'Deploy services', command: 'deploy' },
		forks: { prompt: 'Run full SLATE lock-in protocol: health, runtime, workflow, enforce', label: 'Run protocol', command: 'run' },
		update: { prompt: 'Run security audit and auto-remediate findings', label: 'Security audit', command: 'security' },
		// Roadmap-aware swaps (NEW)
		roadmap: { prompt: 'Get code guidance based on current development stage', label: 'Get guidance', command: 'guidance' },
		guidance: { prompt: 'View current development stage and transition if needed', label: 'View stage', command: 'stage' },
		stage: { prompt: 'Process specifications and run AI analysis', label: 'Process specs', command: 'specs' },
		specs: { prompt: 'Check learning progress, achievements, and XP', label: 'View progress', command: 'learn' },
		learn: { prompt: 'Get compressed context for token-efficient operations', label: 'Get context', command: 'context' },
		context: { prompt: 'Check roadmap alignment: dev stage, specs, tasks', label: 'View roadmap', command: 'roadmap' },
	};

	// Replace any pillar whose command matches the last command
	for (let i = 0; i < pillars.length; i++) {
		if (pillars[i].command === lastCommand && swaps[lastCommand]) {
			pillars[i] = swaps[lastCommand];
		}
	}

	// Deduplicate by command
	const seen = new Set<string>();
	const deduped: SlateFollowup[] = [];
	for (const p of pillars) {
		const cmd = p.command ?? p.label;
		if (!seen.has(cmd)) {
			seen.add(cmd);
			deduped.push(p);
		}
	}

	return deduped.slice(0, 5);
}
