# Cursor project settings

## Auto-approve `git add` and `git commit` only

This repo allows the agent to run **only** staging and commit commands without asking each time.

| File | Used by |
|------|---------|
| [hooks.json](hooks.json) + [hooks/allow-git-stage-commit.py](hooks/allow-git-stage-commit.py) | **Cursor IDE** Agent (shell commands) |
| [cli.json](cli.json) | **Cursor CLI** in this repo |

### IDE (Agent mode)

1. Hooks must be enabled (Cursor loads `.cursor/hooks.json` from the project root).
2. In **Cursor Settings → Agents**, use an auto-run mode that respects hooks/allowlists (e.g. **Allowlist**, not sandbox-only if your build ignores the allowlist).
3. If prompts still appear, try **Legacy Terminal Tool** under Agents settings (known fix when sandbox overrides allowlists).

Matched commands (examples): `git add .`, `git commit -m "feat(m3): ..."`, including after `Set-Location ...;` on Windows.

**Still asks for approval:** `git push`, `git reset`, `git rebase`, and all non-git commands.

### CLI

`cli.json` uses `approvalMode: "allowlist"` with only `Shell(git add*)` and `Shell(git commit*)` in `allow`.

### Global override (optional)

Cursor can also use `~/.cursor/permissions.json` (user-wide, all repos). This project does **not** require it if hooks work. To mirror the same rules globally:

```json
{
  "terminalAllowlist": [
    "git add",
    "git commit"
  ]
}
```

Do **not** add bare `"git"` unless you want every git subcommand auto-approved.
