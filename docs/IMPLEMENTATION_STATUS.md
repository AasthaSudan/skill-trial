# Implementation status — 2026-10-23

## Current delivery scope

The owner clarified that usable product features are the priority; production hardening and live production qualification are outside the immediate scope. The requested feature paths are implemented in source. This is not an assertion that every flow has passed a fresh runtime check.

## Implemented feature paths

- Candidate registration, login, local verification/reset inbox, onboarding, resume extraction and claim review, skill selection, timed assessments, autosave, submissions, evaluation, evidence reports/PDFs, history/comparison, practice, and learning paths.
- Broader challenge content: 22 original formal families with practice variants plus 22 advanced/Spring Boot families with practice variants. The 44 expanded variants have hash-bound attestations: 32 coding/SQL reference executions and 12 Spring Boot scenario answer-key validations. Those validations predate the latest feature edits; content YAML was not changed in this continuation.
- Spring Boot: six advanced scenarios covering REST contracts, validation, services, persistence, transactions, and exceptions, with practice variants, guides, and optional explanation rubrics. These are scenario assessments; full Spring project compilation and execution are not included.
- Optional Gemini/Anthropic AI: redacted resume suggestions, consented written-explanation feedback capped at 20% of a scenario score, deterministic fallback, and unpublished admin challenge proposals. Proposal schemas and available types now match the supported SQL, language, and Spring Boot flows.
- Resource administration: create, edit/delete drafts, create revisions, validate, independent review, publish, unpublish/archive; articles, videos, guides, interactive links, and linked published practice challenges; multiple competencies, difficulty, estimated duration, HTTPS links or Markdown, optional two-to-five-question checks, manual link checking, and weekly link-health checks through the worker. Existing one-question guides and path snapshots remain readable.
- Resource consumption: learning paths snapshot the published version, select resources for each competency, respect linked practice choices, render Markdown/external links, and validate all quick-check answers after a 30-second reading period. Answer keys stay out of candidate path responses.
- Badge administration: rule registry, category, supported icons, editable rules/thresholds, active/archive state, optimistic version checks, and rule history. Earned tiers are persisted with their rule snapshot/version, retained after rule changes or streak resets, displayed with earning history, and included in account exports.
- Other existing game/admin flows: quests, XP, streak shields, achievements, skill Orbits, cosmetics, opt-in practice league, inbox, reminder/recap preferences, scoped admin permissions, user suspension, settings, challenge lifecycle, audit events, and coverage statistics.
- Separate runner: timestamped HMAC requests, nonce replay rejection, bounded payloads, no application database, and dispatch into resource-limited, network-disabled Docker containers. Local Docker mode is also available.
- Privacy: resume deletion/retention clears extracted evidence and encrypted files; scheduled account deletion removes associated jobs and user data, including badge awards.

## Local use and configuration

Restart the API after these changes. Development startup adds the resource/badge metadata columns and creates the permanent award table for an existing local SQLite database. Deployment migrations now include `0002_resource_badge_features` for migrated databases.

`DEMO_CONTENT=true` is the development default. On startup, matching successfully attested seed drafts become marked development previews so advanced and Spring Boot flows are available locally. Briefings, admin tables, and report limitations identify preview content. The validation manifest's independent-review state is unchanged. Set `DEMO_CONTENT=false` to restore normal draft/publication gates; preview publication never applies outside development.

Coding needs Docker and the language images, or configured remote runner credentials/address. Optional AI needs a real provider key/model, the admin switch, and relevant candidate consent. The development inbox allows local account flows without SMTP. A deployed remote runner or email provider still needs configuration; the remote-runner protocol and Docker dispatch were exercised on localhost.

## Verification boundary

The 2026-10-23 local audit passed 71 backend tests (including actual Docker execution), three frontend tests, and the production frontend build. Live submissions exercised all five supported assessment skills. Browser practice completed in both editor modes; main candidate screens and public share revocation were checked. Seven localhost signed-runner integration checks passed. Both Alembic revisions and migration-gated initialization passed on isolated SQLite. See [flow audit](FLOW_AUDIT.md) for the fixes and exact scope, and [hackathon guide](HACKATHON_GUIDE.md) for the demo. A synthetic live Gemini request passed after the owner configured a local key. Real SMTP, Anthropic calls, PostgreSQL and production deployment were not qualified.

Production Compose/TLS, separate runner deployment, encrypted backup scripts, migration enforcement, and qualification tooling remain available in the repository. No production deployment is claimed. Production security/load/accessibility/restore qualification and independent content review remain future release work, not prerequisites for trying the local development preview. Recruiter accounts/search are outside the current candidate-controlled report-sharing scope.
