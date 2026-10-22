# SkillTrial — Project Context & Handoff

> Updated 2026-10-23. This file reflects the current local application. Earlier statements in this document or the original planning notes that say no code exists are obsolete. For exact implementation boundaries, see `docs/IMPLEMENTATION_STATUS.md`.

## What the product does

SkillTrial helps candidates turn resume claims into practical assessment evidence. Candidates review extracted claims, select skills, complete timed challenges, inspect four-state results, download frozen reports, and follow evidence-based practice paths. XP and other game features never affect verification status.

The product has three zones: Play (candidate progress), Focus (assessment workspace), and Proof (results/reports). The original implementation plan is `docs/SkillTrial_Implementation_Plan_LLD.md`; the product requirements are in `docs/SkillTrial_Product_Spec.md`.

## Current code layout

```text
backend/       FastAPI, SQLAlchemy, persisted evaluation queue, worker entry point
frontend/      React, TypeScript, Vite application
content/       YAML challenges, validation attestations, sample resume
scripts/       Windows setup, local/production runner prep, backups, content tools
runner_service/ HMAC-authenticated private runner API and isolated code container dispatch
deploy/         Docker, Caddy, PostgreSQL, and separate-runner deployment assets
docs/           product specification, implementation plan, status, production runbook
var/           ignored runtime database, encrypted resumes, keys, and development mail
```

## Decisions and current behavior

- Backend: Python + FastAPI + SQLAlchemy. Frontend: React + TypeScript + Vite + Tailwind.
- SQLite is the default local database. A psycopg PostgreSQL URL and a frozen Alembic baseline for the current schema exist. Production startup now requires the database revision to match the image's migration heads; production database operation remains unqualified, and future model changes need new revisions.
- Local evaluations use a persistent database queue. Run the worker in the API for local use, or set `RUN_BACKGROUND_WORKER=false` and run `python -m app.worker` from `backend/`. Stale queue leases are recovered. This is not Redis/Celery infrastructure.
- Candidate code runs in Docker containers with network disabled, read-only mounts, and resource limits. `RUNNER_MODE=docker` supports local work; `RUNNER_MODE=remote` signs requests to a separate HMAC-authenticated runner API. `OCI_RUNTIME=runsc` selects gVisor. Runner deployment assets exist, but the private host is not provisioned or qualified.
- Content uses YAML plus hash-bound validation reports. The 22-family starter pack spans SQL, Python, Java, and JavaScript. An additional 22-family pack adds 12 advanced algorithm families, four advanced SQL families, and six Spring Boot scenario families, all with practice variants. The 44 new variants have validation attestations; the 12 changed/new Spring Boot variants passed validation on 2026-10-23. Development defaults to `DEMO_CONTENT=true`, making attested seed drafts available as marked local previews after startup. Independent review/publication is still required outside development or with preview disabled. Spring Boot assessments are scenario-based, not full Spring application builds.
- PDFs use frozen report snapshots. Candidate-controlled, expiring share links expose only selected report evidence; the raw token is hashed at rest, and the candidate can revoke the link. Recruiter accounts, candidate search, and recruiter workspaces are not built.
- Admin stays in scope and now includes scoped permissions, user suspension, registration/cooldown settings, content lifecycle, coverage, statistics, and audit inspection.
- Optional Anthropic features are wired for contact-redacted resume claim suggestions, written scenario explanations capped at 20%, and admin challenge proposals. They require environment configuration, an admin-level switch, candidate preference, and per-Trial explanation consent. AI claims remain pending review; scoring falls back to deterministic results. No code or hidden tests are sent.

## Current implementation

The owner clarified the delivery target: usable features, without requiring production hardening or live qualification. Resource forms now support kind, Markdown/HTTPS URL, multiple competencies, difficulty/duration, optional 2–5 MCQs, linked published practice, revisions and archive. Published paths snapshot the resource and hide answer keys. Badge rules are editable with history/versioning, and `badge_awards` preserves earned tiers and their rule snapshots. Development startup adds the two metadata columns; Alembic revision `0002_resource_badge_features` handles migrated databases.

Registration, sessions/CSRF, verification/reset, resume processing and claim review, timed assessment lifecycle, evaluation and reports, history/comparison, practice, learning paths, quests, achievements, and privacy controls are connected. Dashboard recommendations use selected roles/goals; learning paths support archive/restore and sequential waypoint locks. Practice builds separate per-skill Orbit progress and unlocks candidate-only cosmetics. The Practice League is opt-in and shows aliases and practice XP only. A private inbox stores milestone and report-ready events. Reminder and weekly recap email settings start off and respect local quiet hours. Share links default to no candidate name and can be revoked. Data export includes the user's progress, notification, learning, and share records.

Recent migration, retention, AI, admin, runner, and deployment code was deliberately left untested/unbuilt at the owner's request. The current validation manifest has attestations for all 44 expanded variants; the dedicated content validator passed the 12 changed/new Spring Boot variants on 2026-10-23. The prior application test suite and local browser QA happened before this continuation.

## Remaining scope

See `docs/IMPLEMENTATION_STATUS.md` and `docs/PRODUCTION_DEPLOYMENT.md` for the current list. The requested feature paths are implemented in source and await the owner's manual runtime check. AI and the remote runner need their external configuration; Docker is required for local code execution. Independent publication review and production provisioning/qualification remain future release tasks. Do not treat source syntax inspection as functional proof.

## Local setup

See `README.md` for Windows and Linux/macOS setup. Docker Desktop and the language images are required for code challenges. Keep `var/encryption.key` with backups; losing it makes encrypted resumes unreadable. Use `PUBLIC_APP_URL` for browser links and configure SMTP credentials outside source control.
