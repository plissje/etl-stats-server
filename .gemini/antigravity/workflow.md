# 🔄 Development Workflow — etl-stats-server

## Verification & Deployment

- **Never deploy automatically**: Never run `deploy_unraid.sh` or trigger deployments automatically.
- **Present & Verify First**: Always present code/design changes to the user first.
- **Wait for Approval**: Wait for explicit user validation before marking a task complete or ready for deployment.

---

## Database Debugging

- The local SQLite DB (`etl_stats.db` / `stats.db`) is generally useless for testing real-world data.
- To debug real ingestion issues, use the staging/production instance at `etl-stats.maryan.io` and/or SSH to Unraid.
- **Permitted local exception**: You may copy the production DB locally into `scratch/` for dry-run analytics.

---

## Scratch Files & Hygiene

- Always use the root-level `scratch/` folder for temporary scripts, debug files, or DB dumps.
- Never create temp/test scripts in the repo root or within `backend/` / `frontend/`.
- **Clean up after resolution**: Delete all scratch scripts and transient test data once the task is resolved.

---

## Test-Driven Process

- When fixing bugs or updating features, update the corresponding test suite.
- Always run tests when core features are modified **before** presenting results to the user.
- **Run tests**: `PYTHONPATH=. .venv/bin/pytest tests/` from the `backend/` directory.

---

## Communication Standard

- Provide concise summaries highlighting **core reasoning** and key files changed.
- No walls of text. Find a healthy balance of critical context, key logic shifts, and next steps.
