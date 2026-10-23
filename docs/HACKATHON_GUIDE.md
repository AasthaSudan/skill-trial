# Know SkillTrial: project guide and demo notes

Verified locally on 23 October 2026. This guide reflects the actual repository at `/Users/aasthasudan/skill_trial/skill-trial/`.

Open the interactive side-by-side guide at [the live walkthrough](http://127.0.0.1:5174/audit.html). The app pane uses the real frontend at port 5173 and the backend at port 8000. The older design comparison is a separate sample-data preview.

## A one-sentence pitch

“SkillTrial turns resume claims into practical assessment evidence, explains the gaps, and supports improvement through targeted learning and practice.”

## A ten-minute walkthrough

1. Show the journal and explain that counts, XP and status are persisted user data.
2. Upload `content/sample_resumes/sample_resume.txt`, or show its extracted claims. Explain pending review, evidence snippets, and why extraction confidence is separate from proficiency.
3. Confirm SQL and open its Trial briefing. Explain coverage, the server deadline, draft revisions and final submission.
4. Show the completed SQL report: **75%, Partially Verified**. Explain why an overall score alone does not establish every required competency.
5. Show the generated learning path. Complete a guide/quick check; the backend enforces the reading period and sequential unlocks.
6. Start **Practice: Customers without orders**. Run the query below, submit and finish. This produces real SQL execution and practice feedback.
7. Show XP, quests and achievements. Explain that practice rewards cannot alter the formal result.
8. Show the completed Spring Boot report, PDF download and Share Manager. Explain frozen snapshots, expiring links and candidate control.

A complete formal assessment has several tasks. Use the saved rehearsal reports to explain formal outcomes, and a short practice task for live execution. An incomplete formal attempt can honestly return Insufficient Evidence.

For the visible SQL practice prompt:

```sql
SELECT c.id, c.name
FROM customers AS c
WHERE NOT EXISTS (
  SELECT 1
  FROM orders AS o
  WHERE o.customer_id = c.id
)
ORDER BY c.id;
```

Why this query: `NOT EXISTS` checks the relationship without the NULL trap of `NOT IN`; one output row is returned per customer. The sample includes a customer with no orders and a practice-only extra customer.

## 01 · What problem does SkillTrial solve?

**Pitch:** A resume contains claims. SkillTrial turns selected claims into inspectable assessment evidence, then recommends practice for the gaps.

The product separates **Play** (practice and motivation), **Focus** (timed assessment), and **Proof** (results and reports). XP never changes formal verification.

There is no recruiter search portal or professional certification claim.

[Open this feature](http://127.0.0.1:5173/app)

## 02 · Architecture and data flow

React + TypeScript + Vite
↓ React Router / TanStack Query
FastAPI · /api/v1
↓ SQLAlchemy transactions
SQLite · persisted local data
↓ persisted evaluation jobs
Worker → SQL / Docker / scenario rubric

Vite proxies API requests to port 8000. The backend stores accounts, claims, attempts, jobs, evidence, activity, paths and rewards. The database—not a frontend array—is the source of user results.

`frontend/src/api.ts`
`backend/app/main.py`
`backend/app/models.py`

[Open this feature](http://127.0.0.1:5173/app)

## 03 · Registration, login and privacy

FastAPI validates registration and hashes passwords with **Argon2**. Login creates a random session token; its hash is stored server-side. The browser receives an HttpOnly session cookie and a CSRF cookie.

Mutation requests send `X-CSRF-Token`. Ownership checks protect resumes, attempts and reports. Admin permissions are checked on the server.

Email verification uses expiring tokens. Locally, Settings → Security shows an owner-only development inbox; real email delivery needs SMTP.

`backend/app/security.py`
`backend/app/main.py`

[Open this feature](http://127.0.0.1:5173/app/settings)

## 04 · Resume upload → extracted claims

The UI sends a multipart file upload. The backend reads PDF, DOCX or TXT, extracts text, matches catalog skill aliases and nearby proficiency language, and creates **pending review** claims.

The uploaded bytes are encrypted at rest. Evidence snippets and extraction confidence support review; confidence does not measure proficiency.

Default extraction is deterministic. Optional Gemini/Anthropic suggestions require configuration and consent; they also remain pending review.

`backend/app/parsing.py`
`backend/app/main.py · /resumes`

[Open this feature](http://127.0.0.1:5173/app/resumes)

## 05 · Claim review and skill catalog

The candidate corrects the extracted level, confirms or removes claims, or adds a skill manually. PATCH requests persist the changes and refresh query caches.

The skill catalog and competency names are curated content. Assessability is computed from published challenge coverage. Tools such as Git/Docker can be recognized without having a formal assessment.

**Claim ≠ verification.** A confirmed SQL claim still has “Not assessed” until an assessment produces evidence.

`frontend/src/pages/Dashboard.tsx · Skills`
`backend/app/catalog.py`

[Open this feature](http://127.0.0.1:5173/app/skills)

## 06 · Trial briefing, timer and autosave

The briefing retrieves available levels, competencies, scoring rules, duration and eligibility. Starting creates a server deadline and a snapshot of the claim, policy and assigned challenge versions.

The editor sends revisioned drafts; stale revisions are rejected. Final submissions use idempotency keys so retries do not create duplicate work.

The server enforces deadlines, finalizes substantive drafts and preserves unattempted tasks as unattempted.

`frontend/src/pages/Workspace.tsx`
`backend/app/main.py · /assessments`
`backend/app/service.py`

[Open this feature](http://127.0.0.1:5173/app/trials)

## 07 · How actual grading works

Submissions create **persisted jobs**. A worker claims jobs, runs evaluation, saves item evidence and finalizes the attempt.

**SQL:** a read-only, time-limited SQLite subprocess.
**Python/JS/Java:** Docker containers with network disabled and resource limits.
**Scenarios:** versioned answer keys and criteria.
**AI Trust:** candidate decisions plus executed counterexamples and fixes.

Sample and hidden test outcomes feed competency scores. The four-state policy computes Verified, Partially Verified, Not Verified or Insufficient Evidence. The report retains why.

`backend/app/execution.py`
`backend/app/evaluation.py`
`backend/app/verification.py`

[Open this feature](http://127.0.0.1:5173/app/history)

## 08 · Reports, PDFs and share links

A completed attempt freezes a JSON evidence snapshot with a SHA-256 fingerprint. ReportLab creates the downloadable PDF; downloading needs a verified email.

Share links contain a random token whose hash is stored. The candidate chooses reports, expiry and display options, then can revoke access.

Public sharing exposes selected evidence—not resumes, emails, code, full history or game rewards.

`backend/app/reports.py`
`backend/app/main.py · /reports, /me/shares`

[Open this feature](http://127.0.0.1:5173/app/reports)

## 09 · Evidence → learning → practice

Undemonstrated competencies create a targeted learning path. It snapshots published learning resources and links relevant practice challenges.

Guides can contain Markdown, external HTTPS resources and quick checks. Completion requires the reading period and correct answers. Earlier waypoints must be completed before later ones unlock.

Practice uses real evaluation but never changes formal verification. A later formal reassessment establishes new evidence.

`backend/app/service.py · complete`
`backend/app/resources.py`
`frontend/src/pages/LearningReader.tsx`

[Open this feature](http://127.0.0.1:5173/app/learning)

## 10 · XP, quests, streaks and badges

XP is stored as a ledger with unique event keys. Server-side activity records drive daily/weekly quests, timezone-aware streaks, per-skill Orbit familiarity and the opt-in practice league.

Badges use versioned rules and permanently saved earned tiers. Cosmetics unlock from activity. Quests count practice only; formal Trials have separate evidence and rewards.

The rank names, XP thresholds and starter badge definitions are product rules. Your XP, streak, quest completion and earned badges are database-derived.

`backend/app/game.py`
`backend/app/models.py · XP, Activity, Quest, BadgeAward`

[Open this feature](http://127.0.0.1:5173/app/quests)

## 11 · Admin and content lifecycle

Authorized admins manage versioned challenges, learning resources, badge rules, coverage, users and platform settings. Candidates cannot grant themselves admin access.

Challenges pass validation, independent review and publication. Content hashes bind validation to the exact version. Development preview makes attested draft content available locally and labels that status.

The source includes optional AI content proposals, but proposals still need human validation/review. Spring Boot assessments are scenarios, not full Spring project execution.

`backend/app/admin_catalog.py`
`frontend/src/pages/Admin.tsx`
`content/challenges/*.yaml`

[Open this feature](http://127.0.0.1:5173/app/settings)

## 12 · What is fixed, dynamic or optional?

**Fixed/curated:** copy, skill catalog, challenge statements, tests, scoring policy, starter guides and reward thresholds. These are input content and rules.

**Dynamic/persisted:** your account, uploaded file, claim corrections, submissions, grading results, reports, learning progress, rewards and notifications.

**Optional external setup:** Anthropic AI, SMTP email, and the remote runner. Local Docker execution does not require cloud AI.

**Visual comparison only:** ports 5174/5175 originally showed fixed sample data. The embedded app here is port 5173 and uses the real database.

[Open this feature](http://127.0.0.1:5173/app)

## 13 · Database entities and consistency

The core chain is **User → Resume → Claim → Attempt → Item → Job → Evidence snapshot**. An attempt has assigned challenge versions; each item has its own draft, final submission and evaluation.

Other tables track sessions, email tokens, XP, activities, quests, badge awards, learning paths, notifications, league membership and report shares.

SQLAlchemy transactions commit related changes together. Unique keys protect duplicate claims, XP events, jobs and badge tiers. SQLite enables foreign keys, WAL and a busy timeout.

`backend/app/models.py`
`backend/app/db.py`

[Open this feature](http://127.0.0.1:5173/app/history)

## 14 · Background work, notifications and maintenance

A local worker thread repeatedly calls `tick()`. It atomically claims queued database jobs, evaluates work, saves outcomes and recovers stale jobs after interruption. A separate worker process is also available.

It is a **database-backed queue**, not Redis/Celery. Maintenance handles scheduled account deletion, retention, expired tokens, optional reminder/recap notices and bounded resource-link checks.

The in-app inbox is persisted. Email reminders start off; SMTP is needed for real delivery. The development inbox substitutes only for local email delivery.

`backend/app/service.py · tick`
`backend/app/main.py · worker, maintenance`
`backend/app/worker.py`

[Open this feature](http://127.0.0.1:5173/app/settings)

## 15 · Settings, export and deletion

Profile, role/goal, timezone, theme, sounds, celebrations, Minimal mode, AI consent and mail preferences are persisted on the server.

A verified account can download a ZIP export. Resume deletion removes the encrypted file and clears associated extraction evidence. Account deletion has a seven-day cancellation period; maintenance removes due accounts and associated records.

Report links can be revoked immediately. A PDF already downloaded by someone is an external copy and cannot be recalled.

`backend/app/main.py · /me/preferences, /me/export, /me/delete-account`

[Open this feature](http://127.0.0.1:5173/app/settings)

## 16 · Optional AI and the remote runner

Gemini or Anthropic integration can suggest resume claims, assess an optional scenario explanation, or propose admin challenge content. It needs provider configuration, an administrator switch and the applicable candidate consent.

Explanations are capped at 20% of the scenario score and require supporting quotes; deterministic grading is retained when the provider is unavailable. Candidate code and hidden tests are not sent to the AI provider.

The optional remote runner accepts bounded, timestamped HMAC-signed requests and rejects replayed nonces. It runs Docker execution without the application database. Local Docker is the configuration used in this demo.

`backend/app/llm.py`
`backend/app/execution.py · remote_code_run`
`runner_service/app.py`

[Open this feature](http://127.0.0.1:5173/app/settings)

## 17 · Running, testing and deployment

Locally: FastAPI listens on port 8000, Vite on 5173, and Docker supplies Python/JavaScript/Java containers. SQL and scenario evaluations do not require Docker.

For a single local server, build the frontend and restart the API; FastAPI serves the compiled SPA. Deployment files describe PostgreSQL, the API, Caddy/TLS and a separate private runner.

Alembic versions the schema. Production initialization requires the expected migration head. These local checks are not a claim of a deployed or production-qualified system.

Run the backend pytest suite, frontend Vitest suite and frontend build before demoing. Keep Docker running, use the included sample resume, and verify email using the local inbox.

`README.md`
`deploy/production.compose.yml`
`backend/migrations/`

[Open this feature](http://127.0.0.1:5173/app)

## 18 · Honest answers for judges

**Is this just an AI wrapper?** No. Core grading is deterministic execution/rubrics. Gemini is configured locally and a synthetic live call passed. Candidate feature use requires explicit consent.

**Is the data hardcoded?** Challenge content and policies are curated inputs. User claims, work, results and progress are stored and computed. Role recommendations currently use explicit role-to-skill mappings.

**Does practice verify a skill?** No. Formal assessment evidence determines verification. Practice drives learning and activity rewards.

**What does the coding runner support?** The current algorithm tasks use `solve(nums)` with integer arrays. Spring Boot uses decision scenarios; it does not build full Spring projects.

**Is it cheating-proof?** No. Tasks are not proctored, and the product does not establish code authorship or detect AI use.

**What would you improve next?** Broader independently reviewed content, richer role mappings, deployment qualification and external mail/AI setup where needed.

[Open this feature](http://127.0.0.1:5173/app)

## Verification policy you should be able to explain

The pure function in `backend/app/verification.py` averages evaluable task ratios, computes per-competency evidence and coverage, checks target-difficulty passes, and applies the versioned policy. It does not import the reward system.

- **Beginner:** at least 2 evaluable tasks, full required competency coverage, 70% competency threshold, 75% overall, and at least 1 passing task at the assessed level or higher.
- **Intermediate:** at least 3 evaluable tasks, 80% required competency coverage, 70% competency threshold, 75% overall, and at least 2 passing tasks at the assessed level or higher.
- **Advanced:** at least 4 evaluable tasks, 90% required competency coverage, 75% competency threshold, 80% overall, and at least 3 passing tasks at the assessed level.

Too few evaluable tasks or insufficient coverage leads to **Insufficient Evidence**. With enough evidence, meeting all required criteria leads to **Verified**. Otherwise, demonstrating some competencies yields **Partially Verified**, and demonstrating none yields **Not Verified**. Untouched tasks are excluded; infrastructure failures are identified and make a free retake available.

The current beginner/intermediate offerings use the baseline challenge pool; the policy and target-level requirements differ. The system is not an adaptive difficulty model.

## Local startup

Keep Docker Desktop running for coding tasks. From the repository root, use two terminals:

```sh
backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000 --reload --reload-dir backend/app
```

```sh
npm --prefix frontend run dev
```

Open [the live app](http://127.0.0.1:5173/) and [the API schema](http://127.0.0.1:8000/docs). In the current session these services are already running. Do not start another copy on the same ports.

For verification links locally, use **Settings → Security → Development inbox**. SMTP remains unconfigured. Gemini is configured locally and a synthetic live check passed. Candidate AI feature use still requires consent.

## What was actually checked

See `FLOW_AUDIT.md` for the tested paths, fixes, and remaining limits. The checks use real local requests, a disposable QA account, isolated test databases, and actual Docker language containers. QA reference answers are used only by the test harness to establish expected outcomes; the application does not substitute them for user submissions.
