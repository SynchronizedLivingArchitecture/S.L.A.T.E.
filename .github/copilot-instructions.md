# S.L.A.T.E. Copilot Instructions
format_rules:
  code_edits: timestamp_author_required
  timestamp_format: ISO8601

commands:
  status: python aurora_core/slate_status.py --quick
  runtime: python aurora_core/slate_runtime.py --check-all
  hardware: python aurora_core/slate_hardware_optimizer.py

rules:
  do:
    - Use timestamp+author on all edits
    - Use isBackground=true for long commands
  dont:
    - Use curl.exe (freezes)
    - Bind to 0.0.0.0
