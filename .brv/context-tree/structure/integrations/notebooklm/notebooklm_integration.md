## Relations
@structure/architecture/core_architecture_overview.md
@structure/mcp_servers/mcp_server_infrastructure.md

## Raw Concept
**Task:**
Integrate Google NotebookLM for advanced source synthesis and research

**Changes:**
- Installed NotebookLM CLI (nlm) via ClawdHub
- Identified auth limitation (HttpOnly cookies) and established OpenClaw browser control as the primary automation path

**Flow:**
Thanos -> OpenClaw Browser -> notebooklm.google.com -> Source Synthesis -> Thanos Memory

**Timestamp:** 2026-01-31

## Narrative
### Structure
- CLI: nlm (symlink)
- Package: notebooklm-py
- Location: ~/.local/bin/ (pipx managed)

### Dependencies
- notebooklm-cli (installed via ClawdHub)
- notebooklm-py (installed via pipx)
- Google account with interactive browser session
- OpenClaw browser control for automation

### Features
- Command: 'nlm' (symlink to notebooklm)
- Interactive access to Google NotebookLM
- Integration with OpenClaw browser control to bypass HttpOnly cookie limitations
- Ability to leverage NotebookLM's source-based synthesis for Thanos research
