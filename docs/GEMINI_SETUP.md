# Gemini setup for SkillTrial

The native Gemini adapter is implemented. The owner entered a local key and a small synthetic Google API request succeeded. The full backend suite passed **71 tests**, including 20 provider cases. No resume or personal information was used in the live connectivity check.

## Where to enter the key

Edit the repository root file:

`/Users/aasthasudan/skill_trial/skill-trial/.env`

Use this configuration. Set **one** key field. `LLM_API_KEY` accepts the Gemini key when the provider is `gemini`. If both key fields contain values, `GEMINI_API_KEY` takes precedence.

```env
LLM_ENABLED=true
LLM_PROVIDER=gemini
LLM_API_KEY=YOUR_GEMINI_KEY_HERE
GEMINI_API_KEY=
LLM_MODEL=gemini-3.5-flash-lite
LLM_API_BASE_URL=https://generativelanguage.googleapis.com
```

The key stays in the backend environment. The root `.env` is ignored by Git. Do not put it in a `VITE_` variable or frontend code. No new package installation is required.

## Activation

1. Save `.env` and restart the API whenever you change it. Uvicorn's normal source reload does not reliably reload `.env` edits.
2. An authorized administrator enables **Admin → Settings → Enable optional AI features**. This local setup enables that platform switch after confirming the provider is ready.
3. The candidate chooses **Settings → Privacy → AI resume suggestions** and/or **AI feedback on written explanations**.
4. Written explanation feedback additionally needs consent on the particular Trial.

Candidate consent remains a user choice. Existing results stay frozen. Duplicate resume uploads return the existing record, so use a new synthetic document if you want to exercise optional extraction after changing consent.

## What Gemini does

- Suggest additional catalog skills supported by exact quotes in contact-redacted resume text. Suggestions remain pending review. Default parsing still works without AI.
- Give optional rubric feedback for short written scenario explanations. Valid quotes must support the result. The AI share is capped at 20% of that scenario score.
- Propose unpublished admin challenge content for human validation and independent review.

The backend never sends candidate code or hidden tests to Gemini. Core coding/SQL grading and formal verification remain deterministic. Admin proposals still need validation and review before publication.

## Failure behavior

The adapter handles HTTP errors, quota/auth failures, timeout, blocked or incomplete answers, malformed JSON and oversized responses as unavailable AI. Resume extraction and scenario scoring retain deterministic behavior. A 12-second request timeout and a response-size bound apply. The free tier is subject to account/model quotas and does not promise unlimited availability.

## Keeping the demo running

- Keep Docker Desktop open for Python, JavaScript and Java tasks.
- Keep the existing frontend at http://127.0.0.1:5173 and backend at http://127.0.0.1:8000 running.
- The side-by-side guide stays at http://127.0.0.1:5174/audit.html.
- The extra design-only preview on 5175 was stopped and its generated build/cache files removed, reclaiming 29.4 MB. Project source, database and reports were retained.

## Provider references

- [Gemini API keys](https://ai.google.dev/gemini-api/docs/api-key)
- [Native generation API](https://ai.google.dev/api/generate-content)
- [Gemini 3.5 Flash-Lite](https://ai.google.dev/gemini-api/docs/models/gemini-3.5-flash-lite)
- [Free-tier availability and data terms](https://ai.google.dev/gemini-api/docs/pricing)

Google lists free-tier content as usable for product improvement. Use synthetic data for the hackathon rehearsal. Model access and quota depend on your account.
