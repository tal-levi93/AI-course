# CI Pipeline (GitHub Actions) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a GitHub Actions CI pipeline that gates PR merges into `develop`, `release`, and `production` with progressively stricter checks.

**Architecture:** A single workflow file (`.github/workflows/ci.yml`) triggered on PRs into the three branches, with four parallel jobs on `ubuntu-latest`. `backend-tests` and `frontend-tests` always run; `lint` and `build` are gated to production PRs via `if: github.base_ref == 'production'`. Branch protection rules (set via `gh.exe`) turn the checks into real merge gates.

**Tech Stack:** GitHub Actions, `actions/checkout@v4`, `actions/setup-python@v5` (Python 3.12), `actions/setup-node@v4` (Node 20), existing pytest + vitest + eslint + vite tooling.

**Repo:** `tal-levi93/AI-course` (the `github` remote — github.com).

**Spec:** `docs/superpowers/specs/2026-06-16-ci-pipeline-design.md`

---

## File Structure

- **Create:** `.github/workflows/ci.yml` — the entire pipeline. One file, four jobs. This is the only code artifact.
- **No application code changes.** Everything else in this plan is repo/GitHub configuration (branches, branch protection) and live verification, which GitHub Actions cannot be meaningfully unit-tested for — the verification *is* the test, run against real PRs.

## Note on testing approach

A CI workflow is configuration, not a unit. There is nothing to TDD locally. The discipline here is: (1) validate the YAML parses before pushing, (2) prove each branch in the matrix behaves correctly with a real PR, (3) prove the gate actually blocks a red check. Each verification step lists the exact expected observation.

---

### Task 1: Create the three long-lived branches on the remote

The workflow triggers on PRs *into* `develop`/`release`/`production`. Those branches don't exist yet (only `master` and feature branches), so create them from `master` first.

**Files:** none (remote git refs only)

- [ ] **Step 1: Fetch and confirm current remote branches**

Run:
```powershell
git fetch github
git branch -r
```
Expected: you see `github/master` and `github/feat/household-shopping`, but **no** `github/develop`, `github/release`, or `github/production`.

- [ ] **Step 2: Create the three branches from master on the remote**

Run:
```powershell
git push github github/master:refs/heads/develop
git push github github/master:refs/heads/release
git push github github/master:refs/heads/production
```
Expected: three `* [new branch]` confirmations. (Pushing `master`'s commit directly to new ref names; no local checkout needed.)

- [ ] **Step 3: Verify the branches exist**

Run:
```powershell
git fetch github
git branch -r
```
Expected: `github/develop`, `github/release`, and `github/production` now appear in the list.

*(No commit — this task only creates remote refs.)*

---

### Task 2: Create the workflow file

**Files:**
- Create: `.github/workflows/ci.yml`

- [ ] **Step 1: Create `.github/workflows/ci.yml` with the full pipeline**

Create `.github/workflows/ci.yml`:

```yaml
name: CI

on:
  pull_request:
    branches: [develop, release, production]

jobs:
  backend-tests:
    name: Backend tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: backend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
          cache: pip
          cache-dependency-path: backend/requirements.txt
      - run: pip install -r requirements.txt
      - run: python -m pytest

  frontend-tests:
    name: Frontend tests
    runs-on: ubuntu-latest
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm test

  lint:
    name: Lint
    runs-on: ubuntu-latest
    if: github.base_ref == 'production'
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run lint

  build:
    name: Build
    runs-on: ubuntu-latest
    if: github.base_ref == 'production'
    defaults:
      run:
        working-directory: frontend
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: "20"
          cache: npm
          cache-dependency-path: frontend/package-lock.json
      - run: npm ci
      - run: npm run build
```

- [ ] **Step 2: Validate the YAML parses**

Run (PowerShell — uses the repo's Python; falls back gracefully if PyYAML is missing):
```powershell
python -c "import yaml,sys; yaml.safe_load(open('.github/workflows/ci.yml')); print('YAML OK')"
```
Expected: `YAML OK`. If you get `ModuleNotFoundError: yaml`, install it first: `pip install pyyaml`, then re-run.

- [ ] **Step 3: Commit on a feature branch**

Do **not** commit directly to `master`/`develop`. Create a working branch:
```powershell
git checkout -b feat/ci-pipeline github/master
git add .github/workflows/ci.yml
git commit -m "ci: add GitHub Actions pipeline for develop/release/production"
git push github feat/ci-pipeline
```
Expected: branch pushes successfully; `gh.exe` can now open a PR from it.

---

### Task 3: Verify the develop/release path (tests only, lint+build skipped)

For `pull_request` events GitHub uses the workflow file from the PR's head branch merged with base, so the workflow on `feat/ci-pipeline` runs even though `develop` doesn't have it yet.

**Files:** none (live verification)

- [ ] **Step 1: Open a PR from the feature branch into `develop`**

Run:
```powershell
gh.exe pr create --repo tal-levi93/AI-course --base develop --head feat/ci-pipeline --title "ci: add pipeline" --body "Adds CI workflow. Verifying develop matrix."
```
Expected: prints the new PR URL.

- [ ] **Step 2: Watch the checks run**

Run:
```powershell
gh.exe pr checks --repo tal-levi93/AI-course feat/ci-pipeline --watch
```
Expected: `Backend tests` and `Frontend tests` both run and report **pass**. `Lint` and `Build` either do not appear or show as **skipped** (because `github.base_ref` is `develop`, not `production`). The PR's overall checks are green.

- [ ] **Step 3: Record the observation**

Confirm in the output: exactly two jobs executed (backend + frontend), zero lint/build execution. If lint/build actually *ran*, the `if:` condition is wrong — stop and fix `.github/workflows/ci.yml` before continuing.

*(No commit — verification only.)*

---

### Task 4: Verify the production path (all four jobs run)

**Files:** none (live verification)

- [ ] **Step 1: Open a PR from the feature branch into `production`**

Run:
```powershell
gh.exe pr create --repo tal-levi93/AI-course --base production --head feat/ci-pipeline --title "ci: verify production matrix" --body "Verifying all four checks run on production PRs."
```
Expected: prints the new PR URL.

- [ ] **Step 2: Watch the checks run**

Run:
```powershell
gh.exe pr checks --repo tal-levi93/AI-course feat/ci-pipeline --watch
```
Expected: **all four** jobs run — `Backend tests`, `Frontend tests`, `Lint`, `Build` — and all report **pass**. Overall checks green.

- [ ] **Step 3: Record the observation**

Confirm four jobs executed. If `Lint`/`Build` are skipped here, the `if: github.base_ref == 'production'` value doesn't match the actual base ref — stop and fix before continuing.

*(No commit — verification only.)*

---

### Task 5: Verify the gate fails on a broken check

Prove a failing test turns the PR check red (otherwise the "gate" is decorative).

**Files:**
- Create (temporary): `backend/tests/test_ci_canary.py`

- [ ] **Step 1: Add a deliberately failing test on a throwaway branch**

```powershell
git checkout -b chore/ci-canary github/master
```
Create `backend/tests/test_ci_canary.py`:
```python
def test_ci_canary_must_fail():
    # Temporary canary to prove CI blocks red checks. Deleted in Step 4.
    assert 1 == 2
```

- [ ] **Step 2: Push and open a PR into `develop`**

```powershell
git add backend/tests/test_ci_canary.py
git commit -m "test: temporary CI canary (expected to fail)"
git push github chore/ci-canary
gh.exe pr create --repo tal-levi93/AI-course --base develop --head chore/ci-canary --title "test: CI canary" --body "Expected to fail — verifying the gate blocks red checks."
```

- [ ] **Step 3: Confirm the check is RED**

```powershell
gh.exe pr checks --repo tal-levi93/AI-course chore/ci-canary --watch
```
Expected: `Backend tests` reports **fail**; the PR's overall status is failing. This proves the gate works.

- [ ] **Step 4: Clean up the canary**

```powershell
gh.exe pr close --repo tal-levi93/AI-course chore/ci-canary --delete-branch
```
Expected: PR closed and `chore/ci-canary` branch deleted. (No canary code ever reaches a protected branch.)

*(No commit to a long-lived branch — the canary lived only on the throwaway branch, now deleted.)*

---

### Task 6: Configure branch protection (make checks required)

Turn the checks into real merge gates. The required-checks list per branch **must match what actually runs** on that branch — `lint`/`build` are required only on `production`, because a job skipped by `if:` reports as "skipped" (not "passed") and would otherwise block the merge forever.

**Files:** none (GitHub configuration via `gh.exe` API)

- [ ] **Step 1: Confirm you are authenticated with `gh.exe`**

Run:
```powershell
gh.exe auth status
```
Expected: logged in to `github.com` as `tal-levi93` with `repo` / `admin:repo` scope. If not, run `gh.exe auth login` (interactive — run it yourself in the terminal with `! gh.exe auth login`).

- [ ] **Step 2: Protect `develop` (require backend + frontend tests)**

Run (PowerShell — JSON piped to stdin; the protection endpoint requires all four top-level keys present, nullable):
```powershell
'{"required_status_checks":{"strict":true,"contexts":["Backend tests","Frontend tests"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' | gh.exe api -X PUT repos/tal-levi93/AI-course/branches/develop/protection --input -
```
Expected: a JSON response echoing the protection settings (HTTP 200), showing `required_status_checks.contexts` = `["Backend tests","Frontend tests"]`.

- [ ] **Step 3: Protect `release` (same as develop)**

Run:
```powershell
'{"required_status_checks":{"strict":true,"contexts":["Backend tests","Frontend tests"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' | gh.exe api -X PUT repos/tal-levi93/AI-course/branches/release/protection --input -
```
Expected: JSON response with the same two contexts.

- [ ] **Step 4: Protect `production` (require all four)**

Run:
```powershell
'{"required_status_checks":{"strict":true,"contexts":["Backend tests","Frontend tests","Lint","Build"]},"enforce_admins":false,"required_pull_request_reviews":null,"restrictions":null}' | gh.exe api -X PUT repos/tal-levi93/AI-course/branches/production/protection --input -
```
Expected: JSON response with `contexts` = `["Backend tests","Frontend tests","Lint","Build"]`.

- [ ] **Step 5: Verify protection is in place on all three**

Run:
```powershell
gh.exe api repos/tal-levi93/AI-course/branches/develop/protection/required_status_checks --jq ".contexts"
gh.exe api repos/tal-levi93/AI-course/branches/release/protection/required_status_checks --jq ".contexts"
gh.exe api repos/tal-levi93/AI-course/branches/production/protection/required_status_checks --jq ".contexts"
```
Expected: `["Backend tests","Frontend tests"]`, `["Backend tests","Frontend tests"]`, and `["Backend tests","Frontend tests","Lint","Build"]` respectively.

- [ ] **Step 6: Confirm the merge button is gated**

Reopen / revisit the develop PR from Task 3:
```powershell
gh.exe pr view --repo tal-levi93/AI-course feat/ci-pipeline --web
```
Expected: with checks green, "Merge pull request" is enabled. (You already proved in Task 5 that a red check blocks it.) The develop PR is now safe to merge, landing `ci.yml` on `develop`.

*(No commit — GitHub configuration only.)*

---

## Self-Review

**Spec coverage:**
- Four checks (backend tests, frontend tests, lint, build) → Task 2 (`ci.yml`). ✅
- Per-branch matrix (develop/release = tests; production = all four) → `if:` conditions in Task 2; verified in Tasks 3 & 4. ✅
- Single-workflow / conditional-jobs architecture (Approach 1) → Task 2. ✅
- Python 3.12 / Node 20, `npm ci`, pip+npm caching, separate lint/build jobs → Task 2. ✅
- Branch protection via `gh.exe`, required-checks matching what runs per branch, skipped≠passed subtlety → Task 6. ✅
- Verification plan (YAML sanity, develop run, production run, failure check, protection) → Tasks 2.2, 3, 4, 5, 6. ✅
- Prerequisite not in spec but required by reality: the three branches must exist → Task 1 (added). ✅

**Placeholder scan:** No TBD/TODO/"handle edge cases". All commands and the full YAML are spelled out. ✅

**Type/name consistency:** Job `name:` values (`Backend tests`, `Frontend tests`, `Lint`, `Build`) are the check contexts referenced verbatim in the Task 6 protection JSON. These must stay in sync — if a job's `name:` changes, the matching `contexts` entry must change too. ✅
