# Project Instructions

## Sub-agent model preferences
- Use model="haiku" for all sub-agents that handle test generation, test running, file exploration, and simple search tasks.
- Reserve model="sonnet" or default for architectural, planning, and complex reasoning sub-agents.

## Architectural guidance
- When doing architectural or design work, read `skill2026.md` in the project root before proceeding.
- Do NOT read it for simple tasks (bug fixes, small changes, test runs).

## Audit logging
- When running audits (code quality, security, coverage, architecture reviews, etc.), write findings to `audit.md` in the project root.
- Append new audit results with a timestamped heading (e.g., `## 2026-03-03 — Security Audit`).
- Keep previous entries — do not overwrite past audit results.

## Workflow
- Git workflow: local git → push to remote → CI via GitHub Actions.
- Always ensure changes are committed locally before pushing.
- CI runs on GitHub Actions — consider CI compatibility when making changes (e.g., dependencies, env vars, test commands).
- Do not push or create PRs without explicit user approval.
