# SLATE Copilot Agent (`@slate`)

The `@slate` chat participant for VS Code Copilot Chat, providing SLATE system management directly from the editor.

## Usage

In Copilot Chat, type `@slate` followed by a command:

| Command | Description |
|---------|-------------|
| `@slate /status` | Full system health check |
| `@slate /runner` | Runner status & management |
| `@slate /ci` | Dispatch & monitor CI/CD workflows |
| `@slate /hardware` | GPU detection & optimization |
| `@slate /benchmark` | Run performance benchmarks |
| `@slate /orchestrator` | Service lifecycle management |
| `@slate /help` | List available commands |

You can also ask `@slate` questions in natural language:

- `@slate are the GPUs healthy?`
- `@slate dispatch the CI workflow`
- `@slate what services are running?`

## Tools

The extension registers 8 language model tools that can be used with `#` references:

- `#slateStatus` — System health
- `#slateRuntime` — Dependency check
- `#slateRunner` — Runner management
- `#slateHardware` — GPU info
- `#slateOrchestrator` — Service management
- `#slateWorkflow` — Task lifecycle
- `#slateBenchmark` — Performance benchmarks

## Development

```bash
cd plugins/slate-copilot
npm install
npm run compile    # Build once
npm run watch      # Watch mode
```

Press **F5** to launch a new VS Code window with the extension loaded.

## Architecture

- `src/extension.ts` — Entry point, registers tools + participant
- `src/slateParticipant.ts` — `@slate` chat handler with command routing
- `src/tools.ts` — 8 tool implementations (system status, runner, hardware, etc.)
- `src/slateRunner.ts` — Python process execution with cancellation & security

All tools execute SLATE Python scripts from the workspace and return their output.
