# SkillTrial: screen-by-screen pitch and technical speaker notes
Prepared from the implemented repository and local rehearsal on 23 October 2026. This is the read-along companion to the editable 36-slide deck.
## How to use this
For a short pitch, use slides 1–4, 8–10, 14, 16, 20–21 and 32–36. Keep the other screens available for questions. For the complete project walkthrough, follow all screens in order. The live demo should use saved formal reports and one short SQL practice rather than rush a full timed Trial.
## 30-second opening
“SkillTrial turns resume claims into practical assessment evidence. Candidates confirm extracted claims, complete timed tasks and inspect reports that explain the result. Evidence gaps guide learning and practice. Activity rewards support motivation while a separate policy decides formal verification. Candidates control which reports they share.”
## System in plain language
The frontend is the screen. The API is the application coordinator. SQLAlchemy writes persistent records. The queue records work waiting for evaluation. The worker executes the evaluator. The verification policy interprets evidence. The report freezes that interpretation. Gemini is an optional assistant behind consent controls.

## 01. SkillTrial
Pitch

### Slide content
- Practical evidence for resume skill claims
- Assessment results with reasons
- Learning and practice guided by evidence gaps

### What to say
SkillTrial helps a candidate check whether a resume claim holds up in practical tasks. The candidate reviews extracted skills, completes a formal Trial, and receives a report explaining the evidence. Gaps lead to learning and practice. The candidate controls when selected reports leave the account.

### How it is implemented
The project combines a React frontend with a FastAPI application, persistent SQLAlchemy records, a database evaluation queue and constrained code execution. The current product targets candidates. Recruiter search and a recruiter workspace are outside the implemented scope.

### Code / source
README.md; docs/SkillTrial_Product_Spec.md

## 02. The problem and product boundary
Pitch

### Slide content
- A claimed skill does not show how someone performed
- A score alone hides competency gaps
- Candidates need a concrete next step

### What to say
A resume tells us what a candidate says they know. A generic quiz score tells us little about which competency failed. We connect each claim to observable task evidence and then to a learning step. This is bounded assessment evidence. We do not claim professional certification, proctoring or proof of code authorship.

### How it is implemented
Claim level, extraction confidence and demonstrated proficiency are separate fields. Formal results have four states. Practice and XP never determine a formal verification outcome. No measured hiring or business impact is claimed.

### Code / source
backend/app/verification.py; backend/app/service.py

## 03. The candidate journey
Pitch

### Slide content
- Review resume claims, then choose a formal Trial
- Inspect evidence, then follow the learning path
- Practice again, then choose what to share

### What to say
The complete sequence is landing, account setup, onboarding, journal, resume upload, claim review, Trial selection, briefing, workspace, grading, result, learning and practice, then report sharing. Quests, achievements and the league are supporting loops. Settings keeps privacy and account control accessible.

### How it is implemented
The navigation expresses Play for progress and practice, Focus for the assessment workspace, and Proof for reports. A new assessment can establish new formal evidence. Completing a learning step or accumulating XP does not revise an old report.

### Code / source
frontend/src/App.tsx; backend/app/service.py

## 04. Technical architecture
Architecture

### Slide content
- React and TypeScript render the browser UI
- FastAPI coordinates persistence and evaluation
- A worker runs SQL, Docker tasks and scenario rubrics

### What to say
The browser calls our versioned API. The API validates requests, checks ownership and commits records through SQLAlchemy. Submission creates a persisted evaluation job. A worker claims the job, invokes the evaluator and stores evidence. The frontend polls for completion and renders the report. Gemini supplies optional assistance behind consent gates.

### How it is implemented
Local runtime: Vite at 5173 proxies /api to FastAPI at 8000. SQLite stores application data. Uploaded resume bytes use Fernet encryption on disk. Python, JavaScript and Java execute in Docker. SQL executes in a separate restricted SQLite process. A separate HMAC runner is an optional deployment mode.

### Code / source
frontend/vite.config.ts; frontend/src/api.ts; backend/app/main.py; backend/app/db.py; backend/app/service.py

## 05. Landing and product explanation
Screen 01

### Slide content
- The product promise and primary call to action
- How it works and privacy information
- A path to registration or sign-in

### What to say
This screen explains the purpose before asking for a resume. I introduce the claim-to-evidence journey, then open the account flow. The public explanation and privacy pages define the scope and candidate controls.

### How it is implemented
Routes /, /how-it-works and /privacy render in Public.tsx. Their content and illustrations are static explanatory material. They do not represent authenticated assessment results.

### Screen route
`/`

### What to show
Show the landing page and its call to action.

### Code / source
frontend/src/pages/Public.tsx

## 06. Account creation and recovery
Screen 02

### Slide content
- Registration and sign-in
- Email verification and password recovery
- Private sessions for candidate data

### What to say
The account keeps uploads and assessment evidence private. Registration creates an account, then sign-in establishes a session. Verification is required for export and report sharing. Locally, verification and recovery links appear in the owner-only development inbox. Real delivery uses SMTP.

### How it is implemented
Routes /register, /login, /forgot-password, /verify-email and /reset-password. POST /auth/register, /auth/login, /auth/forgot-password and /auth/token. Argon2 hashes passwords. Opaque session tokens are hashed server-side. The browser holds an HttpOnly session cookie and sends X-CSRF-Token on mutations. Reset tokens expire and are single-use.

### Screen route
`/login`

### What to show
Use an existing rehearsal account to keep the live demo short.

### Code / source
backend/app/security.py; backend/app/main.py; frontend/src/pages/Public.tsx

## 07. Onboarding and career direction
Screen 03

### Slide content
- Candidate name and career interests
- Selected roles or a written goal
- A direction for the journal

### What to say
The candidate tells us their career direction. We save these choices and use role-to-skill mappings to prioritize relevant claims. This recommendation logic is explicit and explainable. We are not presenting a trained career prediction model.

### How it is implemented
Route /app/onboarding saves profile data through PATCH /me/profile. The backend stores roles, goal, timezone and onboarded state in User.profile. GET /dashboard uses role_skills and goal keyword matches to build recommendations. Confirmation and onboarding activity can issue unique setup rewards.

### Screen route
`/app/onboarding`

### What to show
Show the saved role and explain how it changes recommended skills.

### Code / source
frontend/src/pages/Dashboard.tsx; backend/app/main.py: dashboard

## 08. The training journal
Screen 04

### Slide content
- Confirmed claims and completed Trial evidence
- Current recommendation and recent activity
- Quests, learning links and earned progress

### What to say
This is the candidate's home. The evidence counts summarize saved records. The next step connects to the chosen career direction. XP, rank and streak describe activity. Verified skill counts describe formal evidence, so the dashboard keeps those meanings separate.

### How it is implemented
Route /app requests GET /dashboard. TanStack Query caches server data and invalidates relevant queries after mutations. The backend combines claims, attempts, role priorities, XP ledger, quests and badge definitions. Mobile navigation and the paper/forest design adapt to the available width.

### Screen route
`/app`

### What to show
Show the difference between confirmed claims and verified skills.

### Code / source
frontend/src/pages/Dashboard.tsx; backend/app/main.py: dashboard

## 09. Resume upload and extraction
Screen 05

### Slide content
- TXT, DOCX and text-based PDF upload
- Evidence snippets for each detected skill
- Encrypted original file and duplicate detection

### What to say
I upload the sample resume. The parser reads the document and matches known skill aliases with nearby proficiency language. These are proposed claims for the candidate to review. Extraction confidence describes the extraction rule, not how skilled the candidate is.

### How it is implemented
Route /app/resumes. POST /resumes uses multipart upload, pdfplumber for PDF, python-docx for Word and UTF-8 decoding for TXT. It normalizes text, checks file size and structure and hashes content to deduplicate. Uploaded bytes are encrypted with Fernet. Scanned image-only PDFs are unsupported. Optional Gemini suggestions use redacted text and require consent.

### Screen route
`/app/resumes`

### What to show
Upload content/sample_resumes/sample_resume.txt or show its existing review.

### Code / source
backend/app/parsing.py; backend/app/main.py: upload; backend/app/security.py

## 10. Claim review and My skills
Screen 06

### Slide content
- Pending claims and source evidence
- Candidate corrections and explicit confirmation
- Separate claim and formal verification states

### What to say
The candidate can correct the proposed level or remove a claim. Confirming means the candidate agrees this is their claim. Only a formal Trial can establish verification. A manual skill addition also becomes a candidate claim and still needs assessment evidence.

### How it is implemented
Routes /app/resumes/:id/review and /app/skills. GET /skills and /me/skills, POST /me/skills and PATCH /me/skills/{id}. Claim stores skill, level, original_level, status, source, evidence and confidence. User/skill uniqueness prevents duplicate skill claims. Distinct confirmed skills drive setup badges without repeating confirmation XP.

### Screen route
`/app/skills`

### What to show
Point out pending_review, confirmed and the independent verification label.

### Code / source
frontend/src/pages/Dashboard.tsx: Skills; backend/app/models.py: Claim

## 11. Competency map
Screen 07

### Slide content
- The competencies behind each skill
- Available claim and evidence information
- A route back to relevant assessment or practice

### What to say
A broad label such as SQL hides several competencies. The map lets the candidate inspect the skill structure and the available evidence rather than treating a skill as one opaque score.

### How it is implemented
Route /app/map renders SkillMap using the skill catalog and dashboard/claim evidence. Competency definitions are curated. Candidate state comes from persisted claims and attempts. Role recommendations and this visualization are not embedding search or machine learning.

### Screen route
`/app/map`

### What to show
Show SQL competencies and relate one gap to its task evidence.

### Code / source
frontend/src/pages/Dashboard.tsx: SkillMap; backend/app/catalog.py

## 12. Trial selection
Screen 08

### Slide content
- Confirmed skill claims eligible for a Trial
- Available assessment levels
- Existing active Trial and cooldown guidance

### What to say
The candidate chooses a confirmed skill and an available assessment level. The backend checks that published content can support that offering. It also prevents overlapping formal attempts for the same skill and enforces the reassessment cooldown.

### How it is implemented
Route /app/trials reuses Skills in Trial mode. Available levels derive from published challenge versions and policy requirements. Formal POST /assessments requires a confirmed claim and supported level. Active-attempt or cooldown conflicts return 409 with details. Practice has a separate creation path.

### Screen route
`/app/trials`

### What to show
Choose a supported skill without starting a long formal attempt during the short demo.

### Code / source
backend/app/main.py: eligibility, assessment_levels, create_attempt

## 13. Trial briefing and consent
Screen 09

### Slide content
- Duration, task scope and assessed level
- Verification criteria and limitations
- Optional explanation consent before starting

### What to say
The briefing establishes what the Trial can measure. The candidate sees the duration and relevant criteria before entering Focus mode. If optional AI explanation feedback is available, the candidate must consent for this specific Trial as well as enabling the account preference.

### How it is implemented
Route /app/briefing/:id uses a claim ID. GET /assessments/briefing/{claim_id} returns scope and eligibility. Attempt creation snapshots the claim and versioned policy. POST /assessments/{id}/start establishes the server deadline. Development content carries a visible preview limitation.

### Screen route
`/app/trials`

### What to show
Explain the timer and scope, then use an already completed formal report for the outcome.

### Code / source
frontend/src/pages/Assessments.tsx: Briefing; backend/app/main.py

## 14. Assessment workspace
Screen 10

### Slide content
- Task prompt, editor or structured choices
- Server timer, autosave and task status
- Sample execution and final submission

### What to say
The workspace shows only what the task needs. The candidate can write code or SQL, answer scenarios, run allowed samples and submit. Autosave protects drafts. The timer uses server time, and the backend rejects work after the deadline. Finishing finalizes substantive saved drafts.

### How it is implemented
Route /app/assessments/:id. Monaco loads for the code editor, with a plain-text alternative. PUT /assessments/{id}/items/{item_id}/draft uses increasing revisions and rejects stale updates. POST run executes visible samples. POST submit uses an Idempotency-Key and queues grading. POST finish finalizes remaining substantive drafts. Formal hidden outputs stay hidden.

### Screen route
`/app/practice`

### What to show
Use the short SQL practice and show All changes saved before finishing.

### Code / source
frontend/src/pages/Assessments.tsx: Workspace; frontend/src/CodeEditor.tsx; backend/app/main.py

## 15. Grading and the evaluation queue
Screen 11

### Slide content
- Submission persists before grading starts
- A worker claims jobs and stores evaluations
- The UI follows progress until completion

### What to say
Submission returns quickly because the request does not perform every grading step synchronously. We persist a job, run the evaluator in a worker and store the result. The interface waits for evidence, then opens the completed report. Infrastructure failures remain distinct from wrong answers.

### How it is implemented
Job has queue state and lease information. tick() claims work with database updates and recovers stale leases. Local mode runs a worker thread, with an optional separate app.worker process. Each Item evaluation stores ratio, competency evidence, tests and evaluator metadata. complete() freezes the final snapshot. This queue does not use Redis or Celery.

### What to show
Explain the analyzing state using the recorded completed run.

### Code / source
backend/app/service.py: enqueue, tick, complete; backend/app/models.py: Job

## 16. Formal result and evidence
Screen 12

### Slide content
- Verified, Partially Verified, Not Verified or Insufficient Evidence
- Reasons, competency evidence and task outcomes
- The exact scope and limitations of the report

### What to say
Here is a real SQL rehearsal result: 75 percent overall, Partially Verified. The overall average does not establish every competency. The report explains the missing evidence. A 100 percent practice result also cannot change formal verification.

### How it is implemented
Route /app/assessments/:id/result. GET /reports/{id} returns a frozen snapshot with policy, claim, challenge versions, competency evidence, reasons, limitations and a SHA-256 fingerprint. verification.decide is a pure function that never imports the reward engine. Untouched tasks are excluded and may leave insufficient evidence.

### Screen route
`/app/reports`

### What to show
Show the SQL 75% result, then expand a task to connect the outcome to evidence.

### Code / source
backend/app/verification.py; backend/app/service.py: complete; frontend/src/pages/Assessments.tsx: ResultPage

## 17. Reports and PDF export
Screen 13

### Slide content
- A private library of formal evidence
- Frozen report snapshots
- Portable PDF downloads

### What to say
The Reports screen lets the candidate return to completed formal evidence. The PDF contains the same assessment scope and outcome rather than recomputing against today's content. A report fingerprint identifies that stored snapshot. It is not a blockchain certificate.

### How it is implemented
Routes /app/reports and /app/reports/:id. GET /history supplies the report list and GET /reports/{id}/pdf renders with ReportLab. Ownership and verified-email checks protect export. Challenge versions, policy and claim data are copied into Attempt.result so later content edits do not rewrite a historical result.

### Screen route
`/app/reports`

### What to show
Open a saved report and show its PDF.

### Code / source
backend/app/reports.py; backend/app/main.py: report_pdf; backend/app/models.py: Attempt

## 18. Share Manager and public report
Screen 14

### Slide content
- Candidate-selected reports and disclosure options
- Expiring links with immediate revocation
- A limited public view without account access

### What to say
The candidate chooses which formal reports to share and whether to include a display name or evidence details. Sharing is off until they create a link. The recipient receives a limited report view. Revoking the link stops future access, although an external downloaded copy cannot be recalled.

### How it is implemented
Routes /app/shares and /r/:token. POST /me/shares requires verified email. ReportShare and ReportShareItem store selected reports, expiry and disclosure options. The server stores a token hash. GET /public/shares/{token} verifies expiry/revocation and builds a redacted view. DELETE /me/shares/{id} revokes it. Resumes, email and source submissions stay private.

### Screen route
`/app/shares`

### What to show
Use the existing rehearsal record to explain create, public view and revoke.

### Code / source
backend/app/main.py: share_create, share_public_view, public_share; frontend/src/pages/Assessments.tsx: ShareManager

## 19. History and comparison
Screen 15

### Slide content
- Formal and practice attempt history
- A timeline of previous evidence
- Comparability checks before interpreting changes

### What to say
History preserves each attempt as the candidate improves. We can select two formal results to inspect what changed. The app explains whether the assessments are comparable. Scores across unrelated skills or incompatible scopes should not be treated as a reliable improvement measurement.

### How it is implemented
Routes /app/history and /app/history/compare?a=...&b=.... GET /history and /history/compare enforce ownership and compare snapshot skill, level, policy and content scope. The timeline reads persisted formal scores. Practice entries remain labeled separately.

### Screen route
`/app/history`

### What to show
Show a completed attempt and the comparison scope explanation.

### Code / source
frontend/src/pages/Assessments.tsx: HistoryPage, ComparePage; backend/app/main.py: compare

## 20. Practice arena
Screen 16

### Slide content
- Published tasks filtered by skill and type
- Real execution with detailed feedback
- Repeated learning without formal verification changes

### What to say
Practice provides a safe place to inspect failures and repeat a skill. It uses real evaluators. The difference is the product contract: practice drives feedback and activity progress, while formal Trials establish verification evidence.

### How it is implemented
Route /app/practice. GET /practice returns published practice challenge versions. Skill filters derive from this response, including Spring Boot. POST /assessments with mode practice and challenge_id creates a single task, followed by start. Practice exposes detailed evaluation output. It contributes to practice-only quests, Orbit progress and the opt-in league.

### Screen route
`/app/practice`

### What to show
Start Practice: Customers without orders. Run the SQL from the companion script, save, submit and finish.

### Code / source
frontend/src/pages/Assessments.tsx: Practice; backend/app/main.py: practice, create_attempt

## 21. Learning paths and reader
Screen 17

### Slide content
- Resources selected for assessment competency gaps
- Reading time and quick checks
- Sequential practice steps with saved progress

### What to say
The formal result creates a concrete learning path for gaps. The candidate reads the guide and answers its quick checks, then moves to linked practice. The backend enforces the reading period and prerequisites. Successful practice completes an unlocked step but does not rewrite the old report.

### How it is implemented
Route /app/learning includes the reader. complete() selects resources and related published practice for gaps and snapshots resource versions. POST /learning/paths/{id}/items/{item_id}/{action} enforces a 30-second reading period and correct answers. Answer keys do not appear in candidate path responses. Archived paths and locked steps cannot be completed by unrelated standalone practice.

### Screen route
`/app/learning`

### What to show
Open an existing gap path. If it was archived after rehearsal, show the archived path and restore it through the UI.

### Code / source
backend/app/service.py; backend/app/resources.py; frontend/src/pages/LearningReader.tsx

## 22. Quests and streaks
Screen 18

### Slide content
- Daily and weekly practice goals
- Claimed rewards with duplicate protection
- Timezone-aware streaks and shields

### What to say
Quests encourage regular practice. Progress comes from server activity records. Claiming a completed quest adds its reward once. Repeating the request cannot duplicate XP or refill an already consumed shield. Formal work stays outside practice quest progress.

### How it is implemented
Route /app/quests. GET /me/quests computes progress and POST /me/quests/{id}/claim validates completion. XP uses unique event keys. Quest records store claimed state. Timezone-aware day boundaries drive streaks, and a weekly reward can issue a streak shield under its rules.

### Screen route
`/app/quests`

### What to show
Show a completed quest and its claimed state.

### Code / source
backend/app/game.py; backend/app/main.py: quest_claim

## 23. Achievements and cosmetics
Screen 19

### Slide content
- Saved badge tiers and activity ranks
- An inspectable XP ledger
- Workspace cosmetics with earned unlocks

### What to say
Achievements recognize work the candidate has completed. Badge definitions are versioned, and earned tiers remain in history even if the admin later changes a threshold. Cosmetics affect the candidate's workspace. They have no role in deciding the formal report.

### How it is implemented
Route /app/achievements. GET /me/badges evaluates supported metrics and persists BadgeAward snapshots. XP, Activity and OrbitProgress record progress. GET/PATCH /me/cosmetics lists and equips only unlocked choices. Distinct confirmed skills advance setup tiers without duplicate confirmation credit.

### Screen route
`/app/achievements`

### What to show
Show an earned tier and explain its rule.

### Code / source
backend/app/game.py; backend/app/models.py: BadgeAward; frontend/src/pages/Dashboard.tsx

## 24. Practice league
Screen 20

### Slide content
- An optional weekly practice competition
- Aliases and practice XP
- Join, change alias or leave

### What to say
The league is optional. It encourages practice using an alias and practice activity. It does not rank formal verification or expose the candidate's resume. Leaving immediately changes membership state.

### How it is implemented
Route /app/league. GET/PATCH /me/league stores LeagueMember and reads practice XP within the configured weekly window. Alias validation prevents obvious personal/offensive values. The leave endpoint flushes membership deletion before returning the updated view.

### Screen route
`/app/league`

### What to show
Show the join state and explain what appears publicly within the league.

### Code / source
backend/app/main.py: league_view, league_membership; backend/app/models.py: LeagueMember

## 25. Notifications and recap
Screen 21

### Slide content
- A persisted in-app inbox
- Report-ready and milestone events
- Optional reminder and weekly recap emails

### What to say
The bell opens saved notifications, including completed reports and milestone events. The candidate can mark an item or all items as read. Email reminders are optional and respect the configured quiet hours. SMTP is a separate integration from this in-app inbox.

### How it is implemented
The Shell requests GET /me/notifications and refetches periodically. Read mutations persist state and invalidate the query. InboxNotification stores user-specific messages and targets. Maintenance schedules opted-in notices within timezone limits, and deliver_notice sends through SMTP or the development mail route.

### Screen route
`/app`

### What to show
Open the bell and a report-ready notification.

### Code / source
frontend/src/App.tsx; backend/app/game.py: notify; backend/app/main.py: maintenance

## 26. Settings and account control
Screen 22

### Slide content
- Profile, game preferences and notification choices
- Security, email verification and password changes
- Privacy, AI consent, export and scheduled deletion

### What to say
Settings makes the candidate's choices explicit. Profile stores career details. Game controls Minimal mode, theme and cosmetics. Security manages verification and passwords. Privacy controls retention and AI consent, plus export and deletion. Account deletion has a seven-day cancellation period.

### How it is implemented
Route /app/settings has Profile, Game, Notifications, Security and Privacy tabs. PATCH /me/profile and /me/preferences persist configuration. /me/export requires verified email. /me/change-password invalidates other sessions. /me/delete-account schedules deletion, and /me/cancel-deletion reverses the schedule before maintenance removes data. Resume deletion clears the encrypted file and extracted evidence.

### Screen route
`/app/settings`

### What to show
Show Privacy and the explicit AI switches. Do not schedule deletion during the presentation.

### Code / source
frontend/src/pages/Dashboard.tsx: SettingsPage; backend/app/main.py

## 27. Admin console and publication
Screen 23

### Slide content
- Versioned challenge and resource lifecycle
- Badge definitions and account administration
- Platform settings and optional AI proposals

### What to say
Authorized admins manage Content, Resources, Badges, Users and Settings. Content passes validation, a different reviewer's approval and publication. AI can propose a draft, but that proposal still needs review and execution validation. The local expanded pack is clearly marked as development preview content.

### How it is implemented
Route /app/admin checks the role in the UI, while every API operation checks scoped server permissions. /admin/challenges, /admin/resources and /admin/badges manage versions and states. /admin/users supports suspension, which removes active sessions. /admin/settings controls registration, cooldown and platform AI. Content hashes bind attestations to exact versions. Never grant an ordinary candidate admin rights for the demo.

### Screen route
`/app/admin`

### What to show
Use an existing authorized admin account to show the five tabs.

### Code / source
frontend/src/pages/Admin.tsx; backend/app/admin_catalog.py; backend/app/main.py

## 28. Frontend implementation
Technical detail

### Slide content
- React Router organizes screens and protected layouts
- TanStack Query manages API state and refreshes
- Monaco and Markdown support task and learning views

### What to say
The frontend is a React application written in TypeScript and built with Vite. React Router selects the screen and the application shell checks the current user. TanStack Query handles loading, caching and refetching. The shared API client attaches cookies and CSRF headers, and converts server errors to useful messages.

### How it is implemented
frontend/src/api.ts wraps fetch('/api/v1'+path) with credentials include, JSON bodies and X-CSRF-Token. It estimates server offset from X-Server-Time for the countdown. App.tsx selects Focus and Proof layouts. Monaco provides the code editor, react-markdown renders learning text, and Tailwind plus journal.css provide styling. The build currently warns about the large editor bundle.

### Code / source
frontend/package.json; frontend/src/api.ts; frontend/src/App.tsx

## 29. Database and consistency
Technical detail

### Slide content
- Account records and reviewed skill claims
- Versioned attempts, items and persisted jobs
- Evidence snapshots, activity ledgers and share records

### What to say
The core relationship starts with a User who owns resumes and claims. An Attempt snapshots a claim and policy and owns Items assigned to challenge versions. A Job grades an Item. Completion stores the report snapshot on the Attempt. Separate records track learning paths, XP and controlled sharing.

### How it is implemented
SQLAlchemy's tx context commits or rolls back related changes together. SQLite enables foreign keys, WAL and a busy timeout. Unique constraints and keys protect claims, jobs, idempotency records, XP events and earned badge tiers. Alembic revisions version the schema. Deployment assets support PostgreSQL, but only SQLite migrations were qualified locally.

### Code / source
backend/app/models.py; backend/app/db.py; backend/migrations/

## 30. Execution and evaluation
Technical detail

### Slide content
- Python, JavaScript and Java use constrained Docker containers
- SQL uses a separate restricted SQLite process
- Scenarios and AI Trust tasks use explicit rubrics

### What to say
Language tasks run submitted work, compare outputs and calculate competency evidence. Docker disables networking and limits resources. SQL uses an in-memory fixture with read-only query authorization in a short-lived process. Spring Boot evaluates framework decisions through scenarios. AI Trust asks the candidate to inspect suggestions and execute a counterexample.

### How it is implemented
Docker uses network none, read-only filesystem and /work mount, non-root user, dropped capabilities, memory/CPU/PID and output limits. Python uses solve(nums), JavaScript uses solve(nums), and Java uses Solution.solve(int[]). SQL has time, query-size and row-count bounds. evaluation.py compares actual values to expected test results. Containers reduce exposure but do not establish a fully qualified production sandbox.

### Code / source
backend/app/execution.py; backend/app/sql_worker.py; backend/app/evaluation.py

## 31. How verification is decided
Technical detail

### Slide content
- Average task evidence and competency scores
- Coverage and target-difficulty requirements
- A versioned four-state decision policy

### What to say
For each evaluable task, we compute a ratio and mapped competency evidence. The policy checks the amount of evidence, coverage, competency thresholds, overall performance and passing tasks at the target level. Too little evidence gives Insufficient Evidence. Meeting every verification criterion gives Verified. Otherwise demonstrated competencies distinguish partial from no verification.

### How it is implemented
Beginner: minimum 2 tasks, 100% coverage, competency 70%, overall 75%, at-level passes 1. Intermediate: minimum 3, coverage 80%, competency 70%, overall 75%, at-level passes 2. Advanced: minimum 4, coverage 90%, competency 75%, overall 80%, at-level passes 3. Each skill now uses separate beginner, intermediate and advanced question banks with no cross-level fallback. The system is not adaptive testing. Practice uses a separate feedback result. Reward calculations do not enter decide().

### Code / source
backend/app/verification.py; backend/app/catalog.py; backend/app/service.py

## 32. Technical integrations and API keys
Technical detail

### Slide content
- Gemini provides optional assistance through the backend
- SMTP handles real outbound email
- A signed remote runner is optional for deployment

### What to say
Gemini is now supported through the native generateContent API. The same validated extraction and explanation rules remain in place. The model can suggest claims, assess an optional written explanation or propose admin content. SMTP delivers mail. Docker runs local code, while a signed remote runner can move execution to another server.

### How it is implemented
Local .env: LLM_PROVIDER=gemini, LLM_ENABLED=true, LLM_MODEL=gemini-3.5-flash-lite and either GEMINI_API_KEY or LLM_API_KEY. Keys stay server-side. The request sends x-goog-api-key and asks for JSON. Blocked, incomplete, malformed, quota or timeout responses fall back safely. Admin AI and candidate consent gates remain. Written explanation share is capped at 20%. No code/hidden tests go to the AI provider. A synthetic live Gemini request passed. SMTP and a deployed remote host remain unconfigured.

### Code / source
backend/app/llm.py; backend/app/config.py; runner_service/app.py; https://ai.google.dev/api/generate-content; https://ai.google.dev/gemini-api/docs/pricing

## 33. Curated inputs and dynamic data
Technical detail

### Slide content
- Curated: catalog, task content, tests and policies
- Persisted: claims, submissions, outcomes and progress
- Optional: cloud AI, real mail and remote execution

### What to say
Fixed content is expected in an assessment product. The questions and policies define what we assess. The important distinction is that the application executes the candidate's submission and computes the result. User records and progress persist in the database. Role recommendations currently use explicit mappings rather than a trained model.

### How it is implemented
YAML files seed versioned Challenge records with hash-bound attestations. Skill names, reward thresholds and starter resources are product inputs. User, Resume, Claim, Attempt, Item, Job, Path, XP, BadgeAward, ReportShare and notifications are saved records. The old visual comparison used sample data. The real frontend at 5173 calls the live backend.

### Code / source
content/challenges/; backend/app/catalog.py; backend/app/models.py

## 34. What still needs configuration
Release plan

### Slide content
- Gemini consent and account-specific free-tier quota
- SMTP for real email delivery
- Production host, PostgreSQL, TLS and private runner qualification

### What to say
The local demonstration works with Docker and the two application servers. The Gemini connection has passed a synthetic live check, but actual feature use still needs the admin switch and candidate consent. Email delivery needs SMTP. Production deployment needs a provisioned host, private runner, migrations, backups and operational qualification.

### How it is implemented
Keep API keys out of the frontend and repository. Free Gemini quota and model access depend on the account and may change. Google lists free-tier data as usable for product improvement, so use synthetic resumes for rehearsal. Production Compose and Caddy files exist, but deployment, PostgreSQL, load/security/restore checks and independently reviewed expanded content remain release work. Scanned-resume OCR, full Spring project execution, recruiter search and adaptive role recommendations are future scope.

### Code / source
deploy/production.compose.yml; docs/PRODUCTION_DEPLOYMENT.md; https://ai.google.dev/gemini-api/docs/pricing

## 35. What the rehearsal established
Evidence

### Slide content
- 71 backend tests and 3 frontend tests passed
- Real grading covered five supported assessment skills
- Both browser editors completed real SQL practice

### What to say
The rehearsal exercised the local candidate journey using actual API requests and Docker execution. SQL produced a deliberate 75 percent partial result. Python, JavaScript, Java and Spring Boot produced verified results with reference submissions. Browser practice reached 100 percent in both editors. We also checked selected-report sharing and revocation.

### How it is implemented
The 71 backend cases include 20 provider regression cases. They cover Gemini request/response handling, incomplete/blocked answers, quota/auth/timeouts, privacy redaction and deterministic fallback. A real synthetic Gemini call also passed after the owner entered the key. Seven local signed-runner integration checks and isolated SQLite migrations passed earlier. These checks do not guarantee every challenge/browser/concurrency combination or production readiness.

### Code / source
backend/tests/; docs/FLOW_AUDIT.md; outputs/Flow_Test_Report.md

## 36. Demo order and judge questions
Presentation close

### Slide content
- Claim review, SQL evidence and a short live practice run
- Learning path, reports and controlled sharing
- Architecture and integration detail for questions

### What to say
My short demo shows the journal, extracted claims, the real SQL partial report, its learning path and one short SQL practice. I finish with a formal report and sharing controls. The technical takeaway is an explainable evidence pipeline with a separate motivation loop. The candidate can inspect both the outcome and its scope.

### How it is implemented
If asked about AI: optional Gemini assists three bounded tasks, while deterministic execution grades code and SQL. If asked about hardcoding: curated content feeds real persisted workflows. If asked about cheating: the app is not proctored and does not establish authorship. If asked about future work: independently reviewed content, production qualification and richer role mappings. Keep Docker, FastAPI at 8000 and Vite at 5173 running. Use the saved formal reports plus short practice for the live presentation.

### Code / source
docs/HACKATHON_GUIDE.md; docs/FLOW_AUDIT.md

## SQL practice demonstration
Choose **Practice: Customers without orders**. The query excludes customers who have at least one matching order. `NOT EXISTS` avoids the NULL problem associated with `NOT IN`. Run samples, wait for autosave, then submit and finish.
```sql
SELECT c.id, c.name
FROM customers AS c
WHERE NOT EXISTS (
  SELECT 1 FROM orders AS o WHERE o.customer_id = c.id
)
ORDER BY c.id;
```

## Simple technical answers to memorize
- **Why React?** Reusable components and local interaction state keep a complex workflow manageable. Router and Query separate screen navigation from server data.
- **Why FastAPI?** Typed request validation and an explicit REST API provide a clear boundary for the frontend, grading and administration.
- **Why SQLite locally?** It gives persistent relational records with minimal setup. PostgreSQL deployment assets exist and still need production qualification.
- **Why a persisted queue?** Grading can take longer than an API request. Saved jobs allow retries and recovery after a worker interruption.
- **Why Docker?** It provides controlled language runtimes with resource and network restrictions. It does not prove code authorship or eliminate every execution risk.
- **Why a separate verification module?** The formal decision remains testable and independent of XP or cosmetic incentives.
- **Why content versions and snapshots?** A historical report must continue to describe the exact task and policy used in that attempt.
- **Where is Gemini used?** Optional resume suggestions, written scenario explanation feedback and admin draft proposals. Core grading works without it.
- **What is not ML?** Role mappings, default extraction rules, gap-to-resource selection and scoring thresholds are explicit rules.
- **What does “AI Trust” mean here?** A task type where the candidate assesses suggestions and supplies executable evidence. It is not an AI-use detector.

## Gemini setup
Edit the root project `.env` at `/Users/aasthasudan/skill_trial/skill-trial/.env`. Use one key field, never both. The file is ignored by Git.
```env
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_API_KEY=YOUR_GEMINI_KEY_HERE
GEMINI_API_KEY=
LLM_MODEL=gemini-3.5-flash-lite
LLM_API_BASE_URL=https://generativelanguage.googleapis.com
```
Restart the backend after changing `.env`. Enable the admin AI switch, then opt in through candidate Settings → Privacy. Explanation grading also asks for per-Trial consent. The owner entered a local key and a synthetic Google API check passed. Keys never appear in this document.

## Runtime checklist
- Docker Desktop running for Python, JavaScript and Java.
- FastAPI at http://127.0.0.1:8000 and Vite at http://127.0.0.1:5173.
- Side-by-side guide at http://127.0.0.1:5174/audit.html.
- Saved formal reports available and a short practice task selected.
- SMTP remains optional and unconfigured. Use the development inbox locally.
- Gemini free-tier quotas can reject calls. The backend retains deterministic fallback.

Current level coverage: all 21 catalog skills support three distinct levels in the local development preview. See LEVEL_ASSESSMENTS.md / Level_Assessment_Update.md for inventory, execution scope and checks.
