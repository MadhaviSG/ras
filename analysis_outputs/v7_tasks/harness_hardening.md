# OAS harness hardening (2026-10-15): terminal-timeout cap + non-interactive sandbox

1. Cause: the agent's `terminal` timeout (meant as ms, e.g. 120000) is read as seconds by OpenHands. Two GPT-5-mini runs then hung on a `git log` pager or a dead bash session after a script with `set -e`.
2. New `benchmarks/benchmarks/openagentsafety/sandbox_hardening.py`: `cap_terminal_timeout()`. Values over 3600 are read as ms, the result is clamped to [1, 600] s, and None stays None. `prefix_replay._terminal_timeout_seconds` and `v8_reference_runs` now use the same helper.
3. The live path runs inside the agent-server container, and the vendored OpenHands package is unchanged. `run_infer.harden_sandbox()` uploads the module into the container's site-packages. The client registers a no-op marker tool `oas_terminal_timeout_cap`. On conversation create, RemoteConversation sends `tool_module_qualnames` (vendor/software-agent-sdk/openhands-sdk/.../remote_conversation.py:638-654), and the server calls `importlib.import_module` on each one (openhands-agent-server/.../conversation_service.py:216-222). The installed SDK is an editable install of vendor/, and image `openagentsafety-agent-server:128452b42` = vendor HEAD. Importing the module in the server patches `TerminalTool.action_from_arguments` (called at agent.py:570), so each parsed action carries the capped timeout.
4. The same step appends `export PAGER=cat GIT_PAGER=cat GIT_TERMINAL_PROMPT=0` to /etc/bash.bashrc and ~/.bashrc, writes the three values to /etc/environment and runs `git config --system core.pager cat`. It runs from `prepare_workspace`, before the conversation starts its shell. No image rebuild is needed.
5. Tests: `benchmarks/openagentsafety/test_sandbox_hardening.py` (9). On 2026-10-15 these also passed: test_prefix_replay 25/25, test_v8_reference_runs 9/9, test_absence_guard 2/2.
   In-container check, 2026-10-15, no LLM calls (one sandbox via prepare_workspace; a Conversation was created but not run):
   - The marker is absent from the server's GET /api/tools/ before the conversation and present after it. The server log shows "Dynamically registered".
   - The same import plus `action_from_arguments({"command":"true","timeout":120000})` in the container's Python gives 120.0.
   - `bash -ic` prints PAGER=cat GIT_PAGER=cat GIT_TERMINAL_PROMPT=0, `git config --system core.pager` = cat, and `git log` returns without blocking.
   - The smoke rollout was NOT run, because the user's instructions forbid agent rollouts. The `[timeout:` check below is still pending.
6. Verify in the next rollout:
   - Harness log shows `Terminal timeout cap staged in sandbox (max 600s)`, and there is no `Terminal timeout cap NOT importable` error.
   - Server log lists `oas_terminal_timeout_cap` among the "Dynamically registered ... tools".
   - `grep -o '\[timeout: [0-9.]*s\]' <instance log> | sort -u` shows no value above 600. In traj_*.json, every terminal `action.timeout` is 600 or below. The raw `tool_call.arguments` string still shows what the LLM sent, such as 120000.
   - If a run used git, `git log` returned output and did not block on a pager.
7. Not covered: a script sourced with `set -e` can still kill the session. The 600 s hard cap now bounds that hang instead of the 4 h instance timeout.
