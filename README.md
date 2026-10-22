# SkillTrial

Practical skill verification with transparent evidence and a private, gamified improvement journey. The Observatory connects resume review, timed assessments, evaluation, reports, practice, learning, and progress.

## Run locally on Windows

Requirements: Python 3.11+, Node 22.12+, and Docker Desktop for **coding** execution. SQL, scenarios, resume processing, and reports run without Docker. Services bind to loopback by default.

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
# Start Docker Desktop, then prepare the language images:
powershell -ExecutionPolicy Bypass -File scripts/setup-runner.ps1
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1
```

Open **http://127.0.0.1:5173**. API documentation: **http://127.0.0.1:8000/docs**. Create an account; no default account password is embedded in the app.

To run services separately:

```powershell
backend/.venv/Scripts/python.exe -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
npm.cmd --prefix frontend run dev
```

For a single-process local build, run `npm.cmd --prefix frontend run build`, then start the API **after** the build. The built app is served at http://127.0.0.1:8000. For a separate evaluation process, set `RUN_BACKGROUND_WORKER=false` for the API and start `python -m app.worker` from `backend/`. If using the in-process worker, keep the API to one Uvicorn worker. Separate workers claim persisted jobs atomically and recover stale leases.

Linux/macOS: create `backend/.venv` with `python3 -m venv`, install `backend/requirements.txt`, run `npm ci` in `frontend/`, pull local runner images using `bash scripts/setup-runner.sh` (set `OCI_RUNTIME=runc` if gVisor is not installed), then start uvicorn/Vite with equivalent shell commands.

## Working features

- Registration, Argon2 passwords, persistent cookie sessions, CSRF protection, verification/reset tokens, editable profile/goals, timezone, themes, and Minimal mode.
- PDF/DOCX/TXT uploads, encrypted files, deterministic extraction, evidence snippets, skill review/correction/confirmation/removal, and the skill catalog.
- Formal beginner/intermediate assessments for SQL, Python, Java, and JavaScript. Coding, SQL, debugging, scenario, and AI Trust types are represented across the catalog. The expanded advanced pack adds 12 algorithm and four SQL families; Spring Boot adds six API, validation, service, persistence, transaction, and exception scenario families with optional explanation rubrics. All 44 new formal/practice versions have hash-bound content attestations; the 12 revised/new Spring Boot versions passed validation on 2026-10-23. In development, `DEMO_CONTENT=true` makes the attested expanded pack available as a marked local preview; other environments require independent review and publication.
- Server deadlines, versioned autosaves, local draft recovery, idempotent submissions, draft finalization, persisted jobs, and restart recovery.
- Real Docker code execution; read-only, time-limited SQL subprocesses. No host subprocess fallback for candidate code.
- A pure four-state engine, competency evidence, immutable snapshots, owner-only PDF downloads, history, and comparison.
- Targeted guides with quick checks, linked practice, Orbit levels, ranks, streak shields, three-tier achievements, quests, celebrations, and unlocked cosmetics. The dashboard tracks career-goal progress, seven first steps, and weekly activity. A private notification inbox surfaces reports and milestones. The optional Practice League shows aliases and practice XP only. Reminders and recap email are opt-in, respect local quiet hours, and require verified email plus SMTP.
- Candidate-controlled report links to selected frozen reports, expiry and revocation, and a public evidence-only viewer. Admin also supports scoped permissions, user suspension, registration/cooldown settings, challenge lifecycle, versioned Markdown/link/practice resources with multiple competencies and optional quick checks, permanent badge awards with versioned editable rules, optional AI authoring proposals, content coverage, operational statistics, and audit inspection.
- Data export (including progress, notifications, learning paths, and share metadata), resume deletion/retention, and account deletion after a seven-day cancellation period. Verified accounts receive queued deletion notices when mail is configured.

The original starter pack has 22 formal definitions and 22 practice variants with content-hash-bound execution attestations. The expanded pack adds 22 advanced and Spring Boot families, each with a practice variant: 12 advanced algorithm families, four SQL families, and six Spring Boot scenarios. The manifest has 44 new-version attestations: 32 coding/SQL references have execution records, and 12 Spring Boot variants have scenario answer-key checks; the 12 changed/new Spring Boot variants passed validation on 2026-10-23. Expanded versions use a marked development preview by default (`DEMO_CONTENT=true`); with preview disabled, and outside development, independent review and publication are required. `scripts/generate_expanded_content.py` regenerates the added YAML files without overwriting content edits and refreshes Spring Boot assessment metadata.

## Try the connected journey

1. Register, complete onboarding, and upload `content/sample_resumes/sample_resume.txt`.
2. Review SQL/Python claims, correct proficiency if needed, and confirm a skill.
3. Open its Trial Gate, read the criteria, and begin. Use Monaco or the accessible plain-text editor (the mobile default).
4. Run samples, submit tasks, or finish with drafts. Inspect real evidence and the outcome. Untouched tasks are excluded rather than fabricated into completed work.
5. In Settings → Security, use your **owner-only development inbox** to verify email before downloading PDFs or data exports. Production needs a configured mail service.
6. Follow Learning paths, complete a guide and quick check, start practice, and inspect XP history.
7. Formal reassessment has a 24-hour cooldown, waived for infrastructure incidents. History preserves all attempts and compares two completed formal results.

Set `PUBLIC_APP_URL` to the browser origin for verification/reset/share links. Set `SMTP_HOST`, `SMTP_PORT`, `SMTP_FROM`, and, when needed, `SMTP_USER`/`SMTP_PASSWORD`. STARTTLS is enabled by default; use `SMTP_SSL=true` for implicit TLS. The development inbox is not a production mail service. Optional Anthropic AI features are off by default and require server configuration, an administrator switch, and relevant candidate consent. Resume text is contact-redacted; AI claims remain pending review. Short written explanations can be submitted for feedback only with per-Trial consent; their score share is capped at 20%. Code, hidden tests, and deterministic grading stay local.

## Administration and content

Create administrators using an interactive password prompt:

```powershell
Set-Location backend
.venv/Scripts/python.exe -m app.cli create-admin --email content-admin@example.com
```

Create a second administrator for independent review. Sign in normally and open `/app/admin`. Candidates have no role-escalation endpoint.

When intentionally changing starter content:

```powershell
backend/.venv/Scripts/python.exe scripts/generate_content.py
backend/.venv/Scripts/python.exe scripts/validate_content.py
```

Validation executes real SQL workers and Docker images. Historical challenge versions remain intact. Keep the local API on **one worker process** for this scheduler.

## Production deployment

The production app stack, TLS reverse proxy, separate authenticated runner service, backup script, and qualification checks are in `deploy/`, `runner_service/`, `scripts/backup-production.sh`, `scripts/qualify-production.sh`, and [the deployment runbook](docs/PRODUCTION_DEPLOYMENT.md). The runner must live on a separate Linux host reachable over a private network. The app has **not** been deployed or production-qualified; real domain, database, SMTP, runner, secrets, and operational evidence are required.

## Checks

```powershell
Set-Location backend
.venv/Scripts/python.exe -m pytest tests -q -m "not docker"
.venv/Scripts/python.exe -m pytest tests -q -m docker
Set-Location ../frontend
npm.cmd test
npm.cmd run build
npm.cmd audit
```

There are 21 workflow/integrity tests, five real Docker tests, and three frontend transport tests. Backend tests use an isolated temporary database and do not modify local account data.

## Boundaries and data

The requested candidate/admin feature paths are implemented in source, with **local feature use** as the current priority. Restart the API to apply local resource/badge schema additions and enable the marked development content preview. Optional AI needs provider configuration; code execution needs Docker or the remote runner. Tests, builds, and browser checks were skipped at the owner's request, so the latest changes are not runtime-qualified. Production hardening/deployment and independent publication review are future release work. Recruiter accounts/search and full Spring project execution are outside the current implementation; Spring Boot uses scenario assessments. See [implementation status](docs/IMPLEMENTATION_STATUS.md) and the [production runbook](docs/PRODUCTION_DEPLOYMENT.md) for exact boundaries.

Runtime data is ignored under `var/`. Keep its `encryption.key` with database/file backups; losing it makes encrypted resumes unreadable. Never commit runtime databases, keys, mail, or assessment submissions.

References: [context](PROJECT_CONTEXT.md), [original specification](docs/SkillTrial_Product_Spec.md), [LLD](docs/SkillTrial_Implementation_Plan_LLD.md), and [archived recruiter design](docs/archive/SkillTrial_LLD_v1.1_with_recruiter_side.md).
