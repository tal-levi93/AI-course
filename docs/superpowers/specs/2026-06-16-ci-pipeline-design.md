# CI Pipeline (GitHub Actions) — Design

**Date:** 2026-06-16
**Status:** Approved, ready for implementation planning

## Goal

Add a CI pipeline using GitHub Actions (github.com) that runs automated checks
on pull requests targeting the three long-lived branches — `develop`,
`release` (staging), and `production` — and gates merges on those checks via
branch protection rules. Checks get progressively stricter as code is promoted
toward production.

## Scope of checks

Four checks, built from tooling that already exists in the repo:

| Key             | Command (working dir)        | Source                          |
| --------------- | ---------------------------- | ------------------------------- |
| Backend tests   | `python -m pytest` (`backend/`) | existing pytest suite        |
| Frontend tests  | `npm test` → `vitest run` (`frontend/`) | existing vitest suite |
| Lint            | `npm run lint` → `eslint .` (`frontend/`) | existing eslint config |
| Build           | `npm run build` → `vite build` (`frontend/`) | existing build      |

Backend lint/format (ruff/flake8) is explicitly **out of scope** — no backend
linter is configured today. Can be added later.

## Per-branch matrix

Checks run on the **pull request _into_** each branch (a gate before merge),
not on push after the fact.

| PR target     | Backend tests | Frontend tests | Lint | Build |
| ------------- | :-----------: | :------------: | :--: | :---: |
| `develop`     | ✅            | ✅             | —    | —     |
| `release`     | ✅            | ✅             | —    | —     |
| `production`  | ✅            | ✅             | ✅   | ✅    |

Rationale: `develop` and `release` get a consistent "tests must pass" gate for
fast feedback; `production` additionally enforces lint and a clean production
build before code ships.

## Architecture (Approach 1: single workflow, conditional jobs)

A single file `.github/workflows/ci.yml`.

### Trigger

```yaml
on:
  pull_request:
    branches: [develop, release, production]
```

Fires whenever a PR targets any of the three branches. GitHub runs the checks
against the PR's merge commit; combined with branch protection, the merge
button stays blocked until they pass.

### Jobs

Four **independent jobs**, all on `ubuntu-latest`, running in parallel on
separate ephemeral runners. `lint` and `build` are gated to production with
`if: github.base_ref == 'production'` (`github.base_ref` = the branch the PR
merges into).

**`backend-tests`** (always runs, working dir `backend/`)
1. `actions/checkout@v4`
2. `actions/setup-python@v5` — Python 3.12, pip cache keyed on `requirements.txt`
3. `pip install -r requirements.txt`
4. `python -m pytest`

**`frontend-tests`** (always runs, working dir `frontend/`)
1. `actions/checkout@v4`
2. `actions/setup-node@v4` — Node 20, npm cache keyed on `package-lock.json`
3. `npm ci`
4. `npm test`

**`lint`** (production PRs only, working dir `frontend/`)
1. checkout → setup-node (Node 20, npm cache) → `npm ci`
2. `npm run lint`

**`build`** (production PRs only, working dir `frontend/`)
1. checkout → setup-node (Node 20, npm cache) → `npm ci`
2. `npm run build`

### Decisions

- **Python 3.12 / Node 20.**
- **`npm ci`** (not `npm install`) for reproducible, lockfile-driven installs.
- **`lint` and `build` are separate jobs**, not steps in one job, so they run
  in parallel and report failures independently. Each re-runs `npm ci`,
  mitigated by the npm cache. The clarity is worth it for two jobs.
- Backend test DB is in-memory SQLite (per `backend/tests/conftest.py`), so the
  runner needs **no external database service**.

## Branch protection (makes CI a real gate)

The workflow only reports pass/fail. To block merges, configure branch
protection rules on each of the three branches. These are scripted with the
GitHub CLI on Windows (**`gh.exe`**), and can also be done via
Settings → Branches in the GitHub UI.

For each branch: require status checks to pass before merging, selecting:

- `develop` & `release`: require `backend-tests` + `frontend-tests`
- `production`: require all four (`backend-tests`, `frontend-tests`, `lint`, `build`)

**Critical subtlety:** a job skipped by an `if` condition reports as
**"skipped," not "passed."** If `lint`/`build` were marked required on
`develop`/`release`, the merge would block forever waiting on jobs that never
run. Therefore the required-checks list per branch **must match what actually
runs** on that branch — `lint`/`build` are required **only on `production`**.

## Verification plan

CI workflows can't be meaningfully unit-tested locally; the real test is a live
run on GitHub.

1. **YAML sanity** — validate workflow syntax before pushing.
2. **First live run** — open a test PR into `develop`; confirm `backend-tests`
   + `frontend-tests` run and `lint`/`build` are skipped.
3. **Production-path run** — open a PR into `production`; confirm all four jobs run.
4. **Failure check** — confirm a deliberately failing test turns the PR check
   red (gate genuinely blocks).
5. **Branch protection** — apply rules via `gh.exe`, then confirm the merge
   button is blocked until checks pass.

## Out of scope / future

- Backend linting (ruff/flake8).
- Reusable workflows (Approach 2) — revisit if checks grow in number/complexity.
- A real fast-unit vs full-integration test split (requires test markers).
- Deployment/CD — this is CI only.
