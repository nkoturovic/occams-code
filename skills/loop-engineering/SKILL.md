---
name: loop-engineering
description: Guidance for execute/verify loop design and monitoring. Prefer the official /loop command for normal user-facing loops.
---

# Loop Engineering Skill

Use the official `/loop` command for normal user-facing execute/verify loops.
This skill is for designing, debugging, or explaining loop behavior. Do not
invent a separate loop runner when `/loop` fits. For broad, risky, or
multi-phase work, prefer DeepWork with verification gates.

## Grill Guidance

Keep loop intake short:

1. Goal: what should change?
2. Success criteria: how will we know it worked?
3. Success type: `test`, `build`, `lint`, `command`, `fileExists`, `oracle`, `observer`, or `manual`.
4. Execute agent: usually `fixer`; use `designer`, `explorer`, or `librarian` only when the loop needs that specialty.
5. Verify agent/check: automated command first; `oracle`, `observer`, or `manual` only when automation is insufficient.
6. Max attempts: default 3.
7. Context files/directories to read before execution.

## Monitor Guidance

- Report each attempt count and current state.
- On success, summarize the final outcome.
- On escalation or manual review, show the reason before asking the user.
- Manual verification must pause until the user resolves it; do not auto-pass.
- If the user cancels, stop the loop cleanly.

## Notes

- `.opencode/loop-history/` is local loop state and should normally stay uncommitted.
- Background job errors/timeouts are runtime signals; surface them briefly and escalate when repeated.
