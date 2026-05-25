# CLAUDE.md

This file is a pointer for Claude Code.

The canonical agent instructions are in `AGENTS.md`.

Before making changes, read:

1. `AGENTS.md`
2. `HANDOFF.md`
3. `TASKS.md`
4. `DECISIONS.md`
5. `docs/adr/`
6. Relevant phase documentation

Do not treat this file as the source of truth.

After making changes, update:

- `HANDOFF.md`
- `TASKS.md`
- `DECISIONS.md` or `docs/adr/` if a meaningful decision was made

Current next major phase:

Phase 3: offline replay/backtesting engine.

Do not implement live trading unless the user explicitly starts the live trading phase.
