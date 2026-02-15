# Claude Code Hooks: User Guide for New Projects

This guide explains how to integrate the **Claude Code Hooks Mastery** configuration into your other projects. By following these steps, you can duplicate the powerful hooks, agents, and workflows from this repository into any codebase.

## 1. Prerequisites

Before you begin, ensure your environment is set up:

1. **Claude Code**: You must have `claude` installed and authenticated.

   ```bash
   npm install -g @anthropic-ai/claude-code
   claude login
   ```
2. **UV (Astral)**: This project relies on `uv` for fast, isolated Python script execution.

   ```bash
   # Install uv (if not already installed)
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

   *Windows users:*
   ```powershell
   powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
   ```

## 2. Fast Track Installation

To add these hooks to a new project (e.g., `my-new-app`), follow these steps:

### Step A: Copy the Configuration

The core logic lives entirely within the `.claude/` directory.

1. **Navigate to this repository's root.**
2. **Copy the `.claude` folder** to your target project's root directory.

   **Windows (PowerShell):**

   ```powershell
   Copy-Item -Path ".claude" -Destination "C:\Path\To\Your\new-project\.claude" -Recurse
   ```

   **Mac/Linux:**

   ```bash
   cp -r .claude /path/to/your/new-project/
   ```

### Step B: Initialize the Environment

Navigate to your new project directory and run the test command manually to verify uv execution works.

```bash
cd /path/to/your/new-project
uv run .claude/hooks/setup.py
```

This ensures `uv` can resolve dependencies and creates the initial log files.

## 3. Configuration & Customization

Once copied, you may need to adjust the configuration for your specific project needs.

### 1. `settings.json`

Located at `.claude/settings.json`. This file registers the hooks with Claude Code.

* **Paths**: The configuration uses `$CLAUDE_PROJECT_DIR` validation, so you generally *do not* need to edit paths unless you move scripts.
* **Enable/Disable Hooks**: To disable a specific hook (e.g., if you don't want TTS notifications), remove its entry from this file.

### 2. Status Lines (`.claude/status_lines/`)

The `settings.json` points to a specific status line script (currently `status_line_v6.py`).

* **Change Style**: Edit `settings.json` and change `status_line_v6.py` to `status_line_v9.py` (minimal) or `status_line_v1.py` (basic) to suit your preference.

### 3. Agent Prompts (`.claude/agents/`)

Your project might not need crypto research agents.

* **Cleanup**: Delete the contents of `.claude/agents/crypto/` if irrelevant to your new project.
* **Keep**: Retain `team/` (Builder/Validator) and `meta-agent.md` as they are universally useful.

## 4. How to Use

Once installed, simply run `claude` in your project directory. The hooks will fire automatically.

### Key Features You Now Have:

* **Safety**: `rm -rf` and other dangerous commands are blocked by `pre_tool_use.py`.
* **Logging**: Every interaction is logged to `logs/` (ensure `logs/` is in your `.gitignore`).
* **Team Workflows**: Use `/plan_w_team` to trigger the Builder/Validator architecture.
* **Formatting**: Python files are automatically linted/typed if you keep the validators.

## 5. Adapting for Specific Stacks

### Python Projects

* The `setup.py` hook automatically attempts to install dependencies from `requirements.txt` or `pyproject.toml`.
* Code validators (`ruff`, `ty`) in `post_tool_use.py` are pre-configured for Python.

### Node.js / TypeScript Projects

* If you are working on a JS/TS project, you might want to disable the Python-specific validators or replace them with `eslint`/`tsc`.
* Edit `.claude/hooks/post_tool_use.py` (or the relevant validator script) to add/remove checks.

## 6. Troubleshooting

**Issue: "uv: command not found"**

* Ensure `uv` is in your system PATH. Restart your terminal after installing.

**Issue: Hooks failing silently**

* Check the `logs/` directory in your project.
* Run the hook script manually to see error output:
  ```bash
  echo '{}' | uv run .claude/hooks/user_prompt_submit.py
  ```

**Issue: "Permission denied"**

* Ensure the `.claude/hooks/*.py` files are executable (Linux/Mac: `chmod +x .claude/hooks/*.py`). On Windows, this is usually not an issue if using `uv run`.

## 7. Recommended `.gitignore`

Add these lines to your new project's `.gitignore` to avoid committing logs:

```gitignore
# Claude Code Hooks
logs/
.claude/logs/
.env
```
