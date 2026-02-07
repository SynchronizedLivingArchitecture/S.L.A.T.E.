// Modified: 2026-02-07T02:00:00Z | Author: COPILOT | Change: @slate chat participant with command routing and tool integration
import * as vscode from 'vscode';

const SLATE_PARTICIPANT_ID = 'slate-copilot.slate';

const SYSTEM_PROMPT = `You are SLATE (Synchronized Living Architecture for Transformation and Evolution), a local-first AI agent orchestration system.
You manage a self-hosted GitHub Actions runner (slate-runner) with 2x NVIDIA RTX 5070 Ti GPUs (Blackwell, compute 12.0).

Key facts:
- Python: 3.11.9 at E:\\11132025\\.venv\\Scripts\\python.exe
- Runner: slate-runner, labels [self-hosted, Windows, X64, slate, gpu, cuda, gpu-2, blackwell]
- GPUs: 2x NVIDIA GeForce RTX 5070 Ti, CUDA_VISIBLE_DEVICES=0,1
- Workspace: E:\\11132025
- ALL operations LOCAL ONLY (127.0.0.1)
- Version: 2.4.0

You have access to SLATE tools for system management. Use them to answer questions about status, runner, CI, hardware, services, and benchmarks.
When the user asks about system health, use the slate_systemStatus tool.
When asked about the runner or CI, use the slate_runnerStatus tool.
When asked about GPUs or hardware, use the slate_hardwareInfo tool.
When asked about services, use the slate_orchestrator tool.
When asked about tasks or workflows, use the slate_workflow tool.
When asked about dependencies, use the slate_runtimeCheck tool.
Keep responses concise and technical. Format output as markdown.`;

const COMMAND_PROMPTS: Record<string, string> = {
	status: 'Run a full system health check. Use the slate_systemStatus and slate_runtimeCheck tools, then summarize the results clearly.',
	runner: 'Check the GitHub Actions runner status. Use the slate_runnerStatus tool and report: online/offline, busy/idle, labels, and any active runs.',
	ci: 'Help the user manage CI/CD workflows. Use the slate_runnerStatus tool with dispatch action if they want to trigger a run, or status to check current runs.',
	hardware: 'Check GPU and hardware status. Use the slate_hardwareInfo tool and report: GPU models, CUDA version, memory usage, and optimization status.',
	benchmark: 'Run performance benchmarks. Use the slate_benchmark tool and present the results in a table.',
	orchestrator: 'Check or manage SLATE services. Use the slate_orchestrator tool and report the status of all services.',
	help: '',
};

export function registerSlateParticipant(context: vscode.ExtensionContext) {
	const handler: vscode.ChatRequestHandler = async (
		request: vscode.ChatRequest,
		chatContext: vscode.ChatContext,
		stream: vscode.ChatResponseStream,
		token: vscode.CancellationToken
	) => {
		// Handle /help command directly
		if (request.command === 'help') {
			stream.markdown('## SLATE Commands\n\n');
			stream.markdown('| Command | Description |\n');
			stream.markdown('|---------|-------------|\n');
			stream.markdown('| `/status` | Full system health check |\n');
			stream.markdown('| `/runner` | Runner status & management |\n');
			stream.markdown('| `/ci` | Dispatch & monitor CI/CD |\n');
			stream.markdown('| `/hardware` | GPU detection & optimization |\n');
			stream.markdown('| `/benchmark` | Run performance benchmarks |\n');
			stream.markdown('| `/orchestrator` | Service lifecycle management |\n');
			stream.markdown('| `/help` | This help message |\n\n');
			stream.markdown('**Tools available:** `#slateStatus` `#slateRuntime` `#slateRunner` `#slateHardware` `#slateOrchestrator` `#slateWorkflow` `#slateBenchmark`\n\n');
			stream.markdown('You can also ask me anything about the SLATE system in natural language.\n');
			return;
		}

		// Build the prompt
		let systemMessage = SYSTEM_PROMPT;
		if (request.command && COMMAND_PROMPTS[request.command]) {
			systemMessage += '\n\nIMPORTANT: ' + COMMAND_PROMPTS[request.command];
		}

		const messages = [
			vscode.LanguageModelChatMessage.User(systemMessage),
		];

		// Add conversation history
		const previousMessages = chatContext.history.filter(
			(h) => h instanceof vscode.ChatResponseTurn
		);
		previousMessages.forEach((m) => {
			let fullMessage = '';
			m.response.forEach((r) => {
				const mdPart = r as vscode.ChatResponseMarkdownPart;
				fullMessage += mdPart.value.value;
			});
			messages.push(vscode.LanguageModelChatMessage.Assistant(fullMessage));
		});

		// Add user message
		const userPrompt = request.prompt || (request.command ? `Run /${request.command}` : 'Show system status');
		messages.push(vscode.LanguageModelChatMessage.User(userPrompt));

		// Get SLATE-tagged tools
		const slateTools = vscode.lm.tools.filter(tool => tool.tags.includes('slate'));

		// Also include any explicitly referenced tools
		const toolReferences = [...request.toolReferences];

		const options: vscode.LanguageModelChatRequestOptions = {
			justification: 'To manage SLATE system via @slate',
			tools: slateTools.map(t => ({
				name: t.name,
				description: t.description,
				inputSchema: t.inputSchema,
			})),
		};

		// If user explicitly referenced a tool, force it
		const requestedTool = toolReferences.shift();
		if (requestedTool) {
			options.toolMode = vscode.LanguageModelChatToolMode.Required;
			options.tools = slateTools
				.filter(tool => tool.name === requestedTool.name)
				.map(t => ({ name: t.name, description: t.description, inputSchema: t.inputSchema }));
		}

		// Tool-calling loop
		const MAX_ROUNDS = 5;
		for (let round = 0; round < MAX_ROUNDS; round++) {
			if (token.isCancellationRequested) { break; }

			const response = await request.model.sendRequest(messages, options, token);

			const toolCalls: vscode.LanguageModelToolCallPart[] = [];
			let responseText = '';

			for await (const part of response.stream) {
				if (part instanceof vscode.LanguageModelTextPart) {
					stream.markdown(part.value);
					responseText += part.value;
				} else if (part instanceof vscode.LanguageModelToolCallPart) {
					toolCalls.push(part);
				}
			}

			// If no tool calls, we're done
			if (toolCalls.length === 0) {
				break;
			}

			// Process tool calls
			messages.push(vscode.LanguageModelChatMessage.Assistant(
				toolCalls.map(tc => new vscode.LanguageModelToolCallPart(tc.callId, tc.name, tc.input))
			));

			for (const toolCall of toolCalls) {
				stream.progress(`Running ${toolCall.name}...`);
				try {
					const result = await vscode.lm.invokeTool(toolCall.name, {
						input: toolCall.input,
						toolInvocationToken: request.toolInvocationToken,
					}, token);

					// Extract text from result
					const textParts: string[] = [];
					for (const part of result.content) {
						if (part instanceof vscode.LanguageModelTextPart) {
							textParts.push(part.value);
						}
					}

					messages.push(vscode.LanguageModelChatMessage.User([
						new vscode.LanguageModelToolResultPart(toolCall.callId, [new vscode.LanguageModelTextPart(textParts.join('\n'))])
					]));
				} catch (err) {
					const errorMsg = err instanceof Error ? err.message : String(err);
					messages.push(vscode.LanguageModelChatMessage.User([
						new vscode.LanguageModelToolResultPart(toolCall.callId, [new vscode.LanguageModelTextPart(`Error: ${errorMsg}`)])
					]));
				}
			}

			// After processing tools, clear the forced tool mode for subsequent rounds
			options.toolMode = undefined;
			options.tools = slateTools.map(t => ({
				name: t.name,
				description: t.description,
				inputSchema: t.inputSchema,
			}));
		}
	};

	const slate = vscode.chat.createChatParticipant(SLATE_PARTICIPANT_ID, handler);
	slate.iconPath = new vscode.ThemeIcon('server-environment');

	slate.followupProvider = {
		provideFollowups(result: vscode.ChatResult, _context: vscode.ChatContext, _token: vscode.CancellationToken) {
			return [
				{ prompt: 'Check system status', label: 'System Status', command: 'status' },
				{ prompt: 'Check runner', label: 'Runner Status', command: 'runner' },
				{ prompt: 'Show GPU info', label: 'Hardware', command: 'hardware' },
			];
		}
	};

	context.subscriptions.push(slate);
}
