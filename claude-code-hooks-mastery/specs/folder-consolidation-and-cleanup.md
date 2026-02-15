# Plan: Folder Consolidation and Cleanup

## Task Description
Consolidate multiple potential-parakeet folders into a single working folder (potential-parakeet-2), remove duplicates, merge .claude configurations, organize the folder structure, and update GitHub with the consolidated repository. The claude-code-hooks-mastery folder is protected and should not have files deleted from it.

## Objective
When this plan is complete:
1. potential-parakeet-2 will be the single working folder with all necessary files
2. Duplicate files from potential-parakeet and potential-parakeet-1 will be removed
3. Unique .claude configuration files will be merged into claude-code-hooks-mastery/.claude
4. The folder structure will be logically organized
5. GitHub will be updated with the consolidated repository

## Problem Statement
The project currently has multiple duplicate folders:
- **Root level**: Contains .claude, backend, data, strategy, tests folders + various Python scripts
- **potential-parakeet**: Original folder with .claude, backend, data folders (has .venv, .cache)
- **potential-parakeet-1**: Extended folder with more agents/skills + docker files, monitoring
- **potential-parakeet-2**: Current working folder with claude-code-hooks-mastery, has most evolved structure

The duplication causes confusion, wastes space, and makes it difficult to maintain a single source of truth.

## Solution Approach
1. **Audit all folders** to identify unique vs duplicate files
2. **Establish potential-parakeet-2 as master** - keep all unique content
3. **Merge unique .claude files** into claude-code-hooks-mastery/.claude (the most complete .claude setup)
4. **Clean up duplicates** from other folders after verification
5. **Reorganize folder structure** in potential-parakeet-2 for logical organization
6. **Update GitHub** with the consolidated structure

## Relevant Files

### Source Folders (to analyze and merge from):
- `potential-parakeet/` - Original folder, mostly duplicates
- `potential-parakeet-1/` - Extended folder with unique scripts/, monitoring/, docker files
- Root `.claude/` - Contains agents: error-detective, ml-engineer, quant-analyst, task-decomposition-expert, ui-ux-designer

### Target Folder (to consolidate into):
- `potential-parakeet-2/` - Master working folder
- `potential-parakeet-2/claude-code-hooks-mastery/.claude/` - Master .claude configuration

### Key Unique Files to Merge:
- Root `.claude/agents/`: error-detective.md, ml-engineer.md, quant-analyst.md, task-decomposition-expert.md, ui-ux-designer.md
- `potential-parakeet/.claude/agents/`: database-architect.md, debugger.md, document-structure-analyzer.md
- `potential-parakeet-1/.claude/`: commands/code-review.md, commands/design-database-schema.md, commands/generate-api-documentation.md
- `potential-parakeet-1/`: scripts/, monitoring/, traefik/, docker files

### Files to Delete (temp/junk):
- `potential-parakeet-2/tmpclaude-*-cwd` files (35+ temp files)
- `.venv/`, `.cache/`, `node_modules/`, `__pycache__/` in all folders

## Implementation Phases

### Phase 1: Foundation
- Catalog all files across folders
- Identify unique vs duplicate files
- Create backup of current state
- Map which files go where

### Phase 2: Core Implementation
- Remove temp files from potential-parakeet-2
- Merge unique .claude files into claude-code-hooks-mastery/.claude
- Copy unique application files into potential-parakeet-2
- Remove duplicate folders after verification

### Phase 3: Integration & Polish
- Reorganize folder structure in potential-parakeet-2
- Update any path references
- Verify folder functionality
- Update GitHub repository

## Team Orchestration

- You operate as the team lead and orchestrate the team to execute the plan.
- You're responsible for deploying the right team members with the right context to execute the plan.
- IMPORTANT: You NEVER operate directly on the codebase. You use `Task` and `Task*` tools to deploy team members to do the building, validating, testing, deploying, and other tasks.
  - This is critical. Your job is to act as a high level director of the team, not a builder.
  - Your role is to validate all work is going well and make sure the team is on track to complete the plan.
  - You'll orchestrate this by using the Task* Tools to manage coordination between the team members.
  - Communication is paramount. You'll use the Task* Tools to communicate with the team members and ensure they're on track to complete the plan.
- Take note of the session id of each team member. This is how you'll reference them.

### Team Members

- Builder
  - Name: builder-cleanup
  - Role: Remove temp files, duplicates, and perform file deletions
  - Agent Type: general-purpose
  - Resume: true

- Builder
  - Name: builder-merger
  - Role: Merge unique .claude files into claude-code-hooks-mastery/.claude
  - Agent Type: general-purpose
  - Resume: true

- Builder
  - Name: builder-organizer
  - Role: Reorganize folder structure and update path references
  - Agent Type: general-purpose
  - Resume: true

- Builder
  - Name: builder-git
  - Role: Handle git operations and GitHub updates
  - Agent Type: general-purpose
  - Resume: true

- Validator
  - Name: validator-structure
  - Role: Verify folder consolidation is complete and functional
  - Agent Type: validator
  - Resume: false

## Step by Step Tasks

- IMPORTANT: Execute every step in order, top to bottom. Each task maps directly to a `TaskCreate` call.
- Before you start, run `TaskCreate` to create the initial task list that all team members can see and execute.

### 1. Remove Temp Files from potential-parakeet-2
- **Task ID**: remove-temp-files
- **Depends On**: none
- **Assigned To**: builder-cleanup
- **Agent Type**: general-purpose
- **Parallel**: true
- Delete all `tmpclaude-*-cwd` files from potential-parakeet-2 root
- Delete any `__pycache__` directories
- Delete any `.pytest_cache` directories
- Verify temp files are removed

### 2. Catalog Unique Claude Files
- **Task ID**: catalog-unique-files
- **Depends On**: none
- **Assigned To**: builder-merger
- **Agent Type**: general-purpose
- **Parallel**: true
- Compare .claude/agents across all folders
- Compare .claude/skills across all folders
- Compare .claude/commands across all folders
- Create list of unique files not in claude-code-hooks-mastery/.claude

### 3. Merge Unique Agents to claude-code-hooks-mastery
- **Task ID**: merge-agents
- **Depends On**: catalog-unique-files
- **Assigned To**: builder-merger
- **Agent Type**: general-purpose
- **Parallel**: false
- Copy unique agents from root .claude/agents/ to claude-code-hooks-mastery/.claude/agents/
- Copy unique agents from potential-parakeet/.claude/agents/ (database-architect.md, debugger.md, document-structure-analyzer.md)
- Copy unique agents from potential-parakeet-1/.claude/agents/ if any unique
- Verify all agents are in claude-code-hooks-mastery/.claude/agents/

### 4. Merge Unique Skills to claude-code-hooks-mastery
- **Task ID**: merge-skills
- **Depends On**: catalog-unique-files
- **Assigned To**: builder-merger
- **Agent Type**: general-purpose
- **Parallel**: false
- Identify skills unique to root .claude/skills/
- Identify skills unique to potential-parakeet/.claude/skills/
- Identify skills unique to potential-parakeet-1/.claude/skills/ (senior-backend, senior-frontend)
- Copy unique skills to claude-code-hooks-mastery/.claude/skills/

### 5. Merge Unique Commands to claude-code-hooks-mastery
- **Task ID**: merge-commands
- **Depends On**: catalog-unique-files
- **Assigned To**: builder-merger
- **Agent Type**: general-purpose
- **Parallel**: false
- Copy commands from potential-parakeet-1/.claude/commands/ (code-review.md, design-database-schema.md, generate-api-documentation.md)
- Verify commands don't conflict with existing ones
- Update any path references in commands

### 6. Merge Unique Application Files
- **Task ID**: merge-app-files
- **Depends On**: remove-temp-files
- **Assigned To**: builder-organizer
- **Agent Type**: general-purpose
- **Parallel**: false
- Copy unique scripts/ from potential-parakeet-1 to potential-parakeet-2
- Copy monitoring/ from potential-parakeet-1 if not present
- Copy docker files if needed
- Copy any unique Python scripts from root level

### 7. Organize Folder Structure
- **Task ID**: organize-folders
- **Depends On**: merge-app-files, merge-agents, merge-skills, merge-commands
- **Assigned To**: builder-organizer
- **Agent Type**: general-purpose
- **Parallel**: false
- Organize loose Python scripts into appropriate directories (scripts/, data/, etc.)
- Ensure consistent folder naming conventions
- Remove any empty directories
- Verify folder structure is logical

### 8. Remove Duplicate Folders
- **Task ID**: remove-duplicates
- **Depends On**: organize-folders
- **Assigned To**: builder-cleanup
- **Agent Type**: general-purpose
- **Parallel**: false
- Delete potential-parakeet folder (after verification)
- Delete potential-parakeet-1 folder (after verification)
- Delete root-level .claude folder (merged into claude-code-hooks-mastery)
- Delete any other duplicate/obsolete files at root level

### 9. Validate Folder Structure
- **Task ID**: validate-structure
- **Depends On**: remove-duplicates
- **Assigned To**: validator-structure
- **Agent Type**: validator
- **Parallel**: false
- Verify potential-parakeet-2 has all necessary files
- Verify claude-code-hooks-mastery/.claude has all merged configs
- Check no critical files were lost
- Verify no temp files remain

### 10. Update GitHub Repository
- **Task ID**: update-github
- **Depends On**: validate-structure
- **Assigned To**: builder-git
- **Agent Type**: general-purpose
- **Parallel**: false
- Stage all changes with appropriate file additions/deletions
- Create descriptive commit message
- Push changes to GitHub
- Verify push was successful

### 11. Final Validation
- **Task ID**: validate-all
- **Depends On**: update-github
- **Assigned To**: validator-structure
- **Agent Type**: validator
- **Parallel**: false
- Run final structure verification
- Verify GitHub repository is updated
- Confirm potential-parakeet-2 is the sole working folder
- Verify acceptance criteria met

## Acceptance Criteria
- [ ] All tmpclaude-* temp files removed from potential-parakeet-2
- [ ] All unique .claude/agents merged into claude-code-hooks-mastery/.claude/agents/
- [ ] All unique .claude/skills merged into claude-code-hooks-mastery/.claude/skills/
- [ ] All unique .claude/commands merged into claude-code-hooks-mastery/.claude/commands/
- [ ] potential-parakeet folder deleted
- [ ] potential-parakeet-1 folder deleted
- [ ] Root .claude folder deleted (merged)
- [ ] potential-parakeet-2 folder structure is logically organized
- [ ] GitHub repository updated with consolidated structure
- [ ] No duplicate files remain
- [ ] claude-code-hooks-mastery folder is intact (not deleted from)

## Validation Commands
Execute these commands to validate the task is complete:

- `ls -la potential-parakeet-2/` - Verify folder structure
- `ls -la potential-parakeet-2/tmpclaude* 2>/dev/null || echo "No temp files"` - Verify temp files removed
- `ls -la potential-parakeet-2/claude-code-hooks-mastery/.claude/agents/` - Verify agents merged
- `ls -la potential-parakeet-2/claude-code-hooks-mastery/.claude/skills/` - Verify skills merged
- `ls -la potential-parakeet-2/claude-code-hooks-mastery/.claude/commands/` - Verify commands merged
- `ls potential-parakeet 2>/dev/null || echo "Folder removed"` - Verify potential-parakeet deleted
- `ls potential-parakeet-1 2>/dev/null || echo "Folder removed"` - Verify potential-parakeet-1 deleted
- `git status` - Verify git status
- `git log -1` - Verify latest commit

## Notes
- **CRITICAL**: Do not delete anything from claude-code-hooks-mastery folder - only add to it
- The .venv, node_modules, .cache folders should NOT be copied (they can be regenerated)
- Keep .env files as they may contain local configuration (but don't commit secrets)
- Consider creating a .gitignore update if needed
- PDF files (OLMAR.pdf, RMR.pdf) and large data files should be evaluated for necessity
- The root folder contains the main git repository - ensure git operations are done there
