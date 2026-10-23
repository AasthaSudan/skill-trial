# SkillTrial flow audit — 23 October 2026

The local candidate journey has been exercised against the running frontend, FastAPI server, persistent SQLite database and actual Docker language containers. This is a local hackathon rehearsal, not a production deployment qualification or a guarantee that every possible defect has been eliminated.

## Results

- **51 backend tests passed**, including five actual Docker execution tests and 25 added regression/account/admin/upload cases.
- **3 frontend transport tests passed**. TypeScript and the Vite production build passed.
- Live API checks: 24 onboarding/catalog/persistence checks and 47 assessment/supporting-flow checks passed. These are journey assertions, separate from the automated test totals above.
- Formal submissions produced SQL **75%, Partially Verified** and Python, JavaScript, Java and Spring Boot **100%, Verified**. The intentionally incorrect SQL task demonstrates a real evidence gap.
- Browser practice completed through both the plain-text editor and Monaco, including real SQL sample execution, autosave, submission/finalization and **100%** result screens. Finish also finalized a saved draft.
- Fourteen candidate screens rendered with authenticated real data. The Spring Boot practice filter, selected-report share creation, anonymous public viewing and immediate revocation were exercised in the UI.
- Seven local remote-runner integration checks passed: readiness, actual signed client/API/Docker execution, unsigned and invalid-signature rejection, replay rejection and payload bounds. This used a temporary localhost runner, not a deployed remote host.
- Both Alembic revisions applied to an isolated SQLite database; migration-gated initialization succeeded at `0002_resource_badge_features` with 28 tables. PostgreSQL was not qualified.

## What was tested

The running API covered registration/login, role-based onboarding, resume extraction, pending claim confirmation, dashboard persistence, formal assessment creation, task samples, revisioned drafts, stale-revision rejection, idempotent submission, persisted grading jobs, evidence results, owner PDF downloads, local email verification, verified-account ZIP export, selected-report sharing and revocation, comparisons, learning read-time and quick checks, sequential unlocks, linked practice, quest claiming, XP idempotency, cosmetics, preferences, notifications and league membership.

Isolated tests additionally covered password-reset session invalidation and single-use tokens; scoped admin access and suspension/restoration; resource revisions, validation, independent review and publication; persistent badge award history; real TXT/PDF/DOCX parsing; malformed and oversized uploads; active-Trial/cooldown guards; locked and archived path behavior; repeat quest claims; and distinct-skill badge progression.

QA accounts and reports contain synthetic rehearsal data. Existing active Python work encountered on the main QA account was preserved; a separate account was used to complete Python. Reference solutions were supplied by the test harness to verify evaluators. The application does not replace candidate answers or fabricate scores.

## Bugs fixed

1. **Dashboard 500 after selecting a career role/goal:** derive assessability from available assessment levels instead of reading a missing catalog field.
2. **Active Trial/cooldown 500:** remove a duplicated error-code argument; return the intended conflict response with useful details.
3. **Repeat weekly quest claims could refill a consumed shield:** return without issuing a second reward once claimed.
4. **Standalone practice could complete locked/archived path steps:** restrict completion to active paths and enforce completed prerequisites.
5. **Previously seeded advanced drafts did not enter the development preview:** recognize both supported seed author identities while retaining attestation and environment gates.
6. **League leave immediately returned joined=true:** flush membership deletion before building the response.
7. **Higher First steps badge tiers were unreachable:** count distinct confirmed skills and preserve historical/legacy credit without duplicating confirmation XP.
8. **Practice filters omitted Spring Boot:** derive skill choices from published practice data.
9. **Navigation at intermediate widths:** fix bottom navigation positioning through the tablet breakpoint.
10. **Misleading journal/practice labels:** describe general daily activity accurately and link results back to the journal.

## Presentation runbook

1. Keep the currently running API, Vite and Docker Desktop open. Avoid starting duplicate servers.
2. Open [the live side-by-side project guide](http://127.0.0.1:5174/audit.html). Its left pane is the real app at 5173; the right pane explains the implementation.
3. Follow the ten-minute walkthrough in `HACKATHON_GUIDE.md`. Use the saved SQL and Spring Boot formal reports for evidence, then the documented short SQL practice for live execution.
4. Explain that curated YAML questions, answer keys, policies, role mappings and reward thresholds are fixed inputs. Claims, submissions, grading, results, paths and progress are persisted/computed user data.
5. For email verification locally, use Settings → Security → Development inbox. Keep formal Trials and practice rewards conceptually separate.
6. An assessment with too few completed tasks may honestly produce Insufficient Evidence. A cooldown or existing active Trial may prevent a fresh formal start; use practice for a short live run.

## Remaining boundaries

- Real SMTP delivery and Anthropic calls are unconfigured and were not exercised. The core local journey works without them.
- Spring Boot uses decision scenarios, not compilation of a complete Spring project. Algorithm challenges use the current `solve(nums)` interface.
- Expanded content is explicitly marked as a development preview; independent content publication review remains a release step.
- This rehearsal does not cover every challenge, level, browser, concurrency condition or failure combination. Production provisioning, PostgreSQL, security/load/restore qualification remain outside the checked scope.
- The build retains a nonfatal large Monaco/editor bundle warning. The editor loaded and executed successfully in the browser rehearsal.
- The older visual comparison on ports 5174/5175 uses fixed sample data. The **audit page embeds the real app** and is the walkthrough to use for functionality.

## Reproduce the checks

From `backend/`, with the existing virtual environment and Docker running:

```sh
PYTHONDONTWRITEBYTECODE=1 SMTP_HOST='' LLM_ENABLED=false SKILLTRIAL_ENV=development .venv/bin/python -m pytest tests -q
```

From the repository root:

```sh
npm --prefix frontend test
npm --prefix frontend run build
```

Backend tests use isolated databases. Live rehearsal checks intentionally created synthetic QA records in the local app.
