# Thanos Workspace Cleanup Plan (Proposed)

This plan targets structural clarity, reduces duplication, and aligns documentation with actual behavior.

## Phase 1 — Immediate Consistency (Low Risk)

### Model Escalation
- **Canonical implementation:** `Tools/model_escalator_v2.py`
- **Support wrapper:** `Tools/model_feedback.py` (thin wrapper to V2 feedback)
- **Config alignment:**
  - Update `openclaw.yaml` model hierarchy to match V2 model set.
  - Update `Tools/model_escalator.py` default config model list to match V2.
- **Deprecate legacy implementations:**
  - Mark `model_escalator.py` (root) as legacy (transcript watcher).
  - Mark `Tools/model_escalation.py` as “simple helper” or fold into V2 docs.
- **Docs**
  - Update `Skills/model-escalation/SKILL.md` to reflect canonical V2 + correct model set.

### Memory System
- **Single source of truth:** `Tools/memory_v2/README.md`
- **Legacy notice:** add top-level note in `memory/README.md` that mem0 pipeline is legacy and V2 is current.
- **Embedding model clarity:** reflect actual usage and fallback logic (`Tools/memory_v2/config.py`).

## Phase 2 — Structure & Hygiene (Moderate Risk)

### Root directory cleanup
- Move report artifacts to `docs/reports/`:
  - Examples: `docs/reports/TEST_REPORT.md`, `docs/reports/*_REPORT.md`, `docs/reports/*_SUMMARY.md`, `docs/reports/*_STATUS.md`, `docs/reports/validation-report.txt`
- Add a short `docs/README.md` index to point to key docs.

### Scripts cleanup
- Resolve duplicates:
  - Choose canonical: `scripts/setup_api.sh` (or `setup-api.sh`) and remove the other.
- Move legacy scripts into `scripts/legacy/` with a short README:
  - Candidates: `scripts/migrate_chromadb_to_neon.py`, old migration utilities.

### Skills hygiene
- Remove accidental directory `Skills/*` (literal asterisk) or rename properly.
- Add `Skills/README.md` index (skill name, purpose, last updated).

## Phase 3 — Architecture Alignment (Higher Impact)

### Model Escalation
- Consolidate V1 and V2 into a single module:
  - Fold `Tools/model_escalator.py` into V2 or make V2 import it.
- Remove unused DB schemas or logs if not in use.

### Memory
- Decide whether to retire `memory/` ingestion pipeline or keep it as input to V2.
- If retiring:
  - Move `memory/` legacy modules under `memory/legacy/`
  - Update `HEARTBEAT.md` to only reference V2 + Graphiti MCP paths.

## Notes
- All deprecations should include a short note in the file header and a reference to this plan.
- Execute in order: Phase 1 → Phase 2 → Phase 3 to avoid inconsistent intermediate states.
