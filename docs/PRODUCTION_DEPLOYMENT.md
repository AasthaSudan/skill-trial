# Production deployment and qualification

This repository now has a single-host application stack and a separately hosted code runner. The deployment is prepared, but it has **not** been deployed or qualified against a real domain, database, SMTP account, AI provider, or Linux runner. Do not treat local source inspection as production proof.

The API image contains a frozen Alembic baseline for the current PostgreSQL schema. Production startup refuses to seed or serve unless the database's applied Alembic revisions match the migration heads shipped in that image. A fresh production database must be migrated before the API starts. For an existing database created before Alembic tracking, take a verified backup and compare its schema to the frozen baseline before using `alembic stamp`; do not run the initial create-table migration blindly against existing tables.

## Network layout

- Public traffic reaches Caddy on ports 80/443. Caddy obtains and renews the site's TLS certificate and proxies to the API.
- The API and PostgreSQL share a private Compose network. PostgreSQL is not published to the host.
- The code runner belongs on a separate Linux VM. Connect it to the API host through WireGuard or another private encrypted network. Publish runner port 8080 only on its private interface and allow inbound traffic only from the API host.
- The runner has access to its host's Docker socket. Treat that VM as a dedicated security boundary: no unrelated workloads, credentials, customer data, or public administrative endpoints. Configure `runsc` on that VM before production use.

## Provisioning

1. Provision a Linux host for the app, a separate Linux host for the runner, a DNS name pointing at the app host, and a private route between them. Configure firewall rules before starting either service.
2. Install Docker Engine and the Compose plugin on both hosts. On the runner, install and configure the gVisor `runsc` runtime, then run `OCI_RUNTIME=runsc bash scripts/setup-runner.sh` to verify it and pre-pull the language images (the image names are also recorded in `backend/app/execution.py`).
   The runner's `RUNNER_HOST_WORKDIR` must be the same absolute path inside the service container and on the host: the API creates temporary source directories there, then the host Docker daemon bind-mounts those paths into the isolated language containers. Keep this directory on local storage with restrictive parent permissions.
3. Copy the source to both hosts. On the app host, create `.env.production` from `.env.production.example`. On the runner host, create `.env.runner` from `.env.runner.example`. Generate one random secret of at least 32 characters and put the same value in both files. Never send it through chat or commit it.
4. Set `APP_DOMAIN`, `APP_URL`, `PUBLIC_APP_URL`, `ALLOWED_ORIGINS`, PostgreSQL credentials, SMTP settings, and `RUNNER_URL`. `RUNNER_URL` is the base URL only; use the runner's private address, for example `http://10.20.0.2:8080`, not a public address. The route must be protected by the private network. Percent-encode reserved characters in the PostgreSQL URL password.
5. On the runner host, set `RUNNER_BIND_ADDRESS` to its WireGuard IP, not `0.0.0.0`, then start it:

   ```sh
   docker compose --env-file .env.runner -f deploy/runner.compose.yml up -d --build
   ```

6. On the app host, start PostgreSQL, then build and start the application:

   ```sh
   docker compose --env-file .env.production -f deploy/production.compose.yml up -d db
   docker compose --env-file .env.production -f deploy/production.compose.yml build api
   docker compose --env-file .env.production -f deploy/production.compose.yml run --rm api alembic -c backend/alembic.ini upgrade head
   docker compose --env-file .env.production -f deploy/production.compose.yml up -d
   ```

7. Create the first administrator with an interactive password prompt:

   ```sh
   docker compose --env-file .env.production -f deploy/production.compose.yml exec -e PYTHONPATH=/srv/skilltrial/backend api python -m app.cli create-admin --email admin@example.com
   ```

   Create a second administrator so challenge content and resources can receive independent review. Keep the API at one Uvicorn worker until database seeding and worker coordination are separately qualified.

8. After the domain resolves and all three app services are healthy, run the read-only deployment qualification script from the app host:

   ```sh
   bash scripts/qualify-production.sh
   ```

   It checks Compose interpolation, PostgreSQL readiness, that applied revisions match the image's Alembic heads, public HTTPS health, and authenticated end-to-end Python, JavaScript, and Java executions through the private runner. It also confirms that the runner rejects invalid HMAC signatures, expired timestamps, and replayed nonces. Qualification executes four short-lived isolated code samples and sends three rejected authentication requests; it creates no candidate records and sends no email. Keep the check output with the release record, then complete the manual/provider/security items below.

## Optional AI configuration

AI remains off by default. To make it available, set `LLM_ENABLED=true`, `LLM_API_KEY`, and `LLM_MODEL` in the app environment, confirm the provider's privacy and retention terms, restart the API, then enable optional AI in Admin → Settings. Candidates separately enable the relevant preference; explanation feedback also requires a per-Trial consent checkbox. Resume text is contact-redacted and AI claims remain pending review. AI feedback is capped at 20% of a scenario score, and provider failures leave deterministic scoring in place. AI challenge proposals are suggestions and still require normal executable validation and independent review.

## Backups

Run `scripts/backup-production.sh` from the app host with the production Compose stack running and an age recipient configured:

```sh
AGE_RECIPIENT=age1... bash scripts/backup-production.sh
```

It streams a PostgreSQL dump and a separate application-data archive (including the resume-encryption key) directly through `age`; plaintext backup files are not written to disk. Keep the matching private identity separately from the backup host, set a written retention period, and store checksums with the encrypted files. Verify a backup in isolated staging by decrypting each stream to `pg_restore` or `tar`; never restore over production as a test. A backup that has not been restored is not a qualified recovery plan.

Install the age CLI on the app host. Generate and retain the age private identity on a separate secure system, then configure only its public recipient on the app host. For an isolated restore drill, decrypt `database.dump.age` into the staging database with `pg_restore`, and stream `application-data.tar.gz.age` into the staging API volume with `tar`. Confirm the restored resume-encryption key can decrypt a sample staging resume before recording the drill as successful.

## Qualification checklist

Before real users or assessments are enabled, record evidence for each item:

- [ ] DNS, public TLS issuance/renewal, redirect behavior, secure cookies, and browser origin policy.
- [ ] PostgreSQL migration from an empty database; for any pre-existing database, verify the baseline/schema match before stamping or migrating. Confirm concurrent startup and worker lease behavior.
- [ ] Runner private-network reachability, HMAC rejection, timestamp expiry, replay rejection, response timeout, size limit, and `runsc` execution.
- [ ] Real Python, JavaScript, and Java compile/runtime cases, output limits, cleanup, and failed-run isolation on the remote host.
- [ ] Challenge authoring validation plus independent review and publication, including all new advanced and Spring Boot drafts.
- [ ] SMTP verification, password reset, deletion notice deliverability, SPF/DKIM/DMARC, and bounce handling.
- [ ] Backup encryption, restore of both database and application data, resume decryption with restored key, and measured recovery time.
- [ ] Security review, dependency review, accessibility review, load/soak behavior, monitoring/alerting, incident response, and retention/deletion checks.
- [ ] If AI is enabled: provider data-processing terms, region, retention, rate limits, cost controls, redaction review, candidate consent text, and deterministic fallback behavior.

These checks have not been run in this workspace. The user requested no tests or builds, and no production host or provider credentials were supplied. Challenge content that lacks a content-hash-bound executed attestation remains draft and cannot be used in an assessment until an administrator validates it, obtains independent review, and publishes it.
