# Separate difficulty banks and full local skill coverage

The local app now offers **21 skills at beginner, intermediate and advanced levels**. Each formal Trial and briefing selects only its exact level. A missing bank produces an unavailable-level response instead of falling back to another level.

## What changed

- Added 179 challenge definitions, each with formal and practice versions: **358 new validated versions**.
- Added genuine beginner coding tasks for Python, JavaScript and Java, beginner SQL tasks and beginner/intermediate Spring Boot scenarios.
- Enabled the 16 previously recognised-only skills through distinct scenario banks: React, Docker, Git, Node.js, AWS, MongoDB, TypeScript, FastAPI, Kubernetes, Redis, HTML, CSS, C#, C++, Go and .NET.
- Added skill, difficulty and challenge-type selectors to Practice. Briefings explicitly identify the selected question level.
- Kept existing attempts, assigned challenge versions and completed report snapshots intact.
- Admin skill choices and AI scenario-proposal support now follow the full catalog.

## What the levels demonstrate

- **Beginner:** foundations and basic operations. C++ examples include owned allocation, container bounds and read-only parameters. Python/Java/JavaScript include counting even readings, finding a maximum and adjacent-pair counting.
- **Intermediate:** applied use and common implementation errors. C++ examples include move ownership, iterator validity and checked boundaries. Existing core language debugging, collection and trust tasks remain intermediate.
- **Advanced:** failure analysis, concurrency and lifetime reasoning. C++ examples include exception safety, dangling views, overflow and concurrent lifetime. Core algorithm and advanced SQL packs remain separate.

Python, JavaScript and Java run executable coding tasks. SQL uses SQLite. Spring Boot and the additional 16 skills use scenario decisions and optional written explanations. These scenario packs do not run a C++ compiler, Kubernetes cluster or full framework project.

## Current question inventory

There are 223 formal challenge families and 223 matching practice variants, making 446 seeded versions in total. Python, JavaScript and Java each have 3 beginner, 6 intermediate and 4 advanced tasks. SQL has 3, 4 and 4. Spring Boot has 3, 4 and 6. Each additional skill has 3, 3 and 4 scenario tasks.

These are curated inputs. The app still computes and stores the candidate's submitted results. New content has matching validation attestations and is labelled as a development preview. Independent publication review remains required outside development.

## Checks

- **80 backend tests passed**. The new tests inspect all 63 skill/level combinations, verify briefing/attempt agreement, prevent cross-level fallback and check that answer fields remain private.
- C++ formal scenario Trials completed through grading and reporting at all three levels in isolated accounts.
- **358/358 new content versions passed validation**. Coding and SQL references executed against their expected outputs. Scenario checks verify content structure and answer-key references, not independent subject-matter review.
- **3 frontend tests passed**, and the final production build passed with the existing nonfatal editor bundle warning.
- Browser verification showed different C++ titles at each level. The final skill/level selector view had no horizontal page overflow.

Open http://127.0.0.1:5173/app/practice, select **C++**, and change **Practice difficulty**. For formal Trials, open a confirmed skill's briefing and change **Assessment level**. Refresh an older open page to pick up the new catalog. An already-started Trial retains its original assigned questions.
