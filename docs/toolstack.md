# Development and delivery toolstack

- **Status:** Accepted for MVP planning
- **Last reviewed:** 2026-08-29

Every mandatory tool is free to use. Hosted features are either free for a
personal/public repository or have a local fallback.

## 1. Environment and dependency management

| Tool                |          Baseline | Purpose                                                                                     | Cost/notes                                        |
| ------------------- | ----------------: | ------------------------------------------------------------------------------------------- | ------------------------------------------------- |
| Git                 | current supported | Version control.                                                                            | Free/open source.                                 |
| GitHub CLI (`gh`)   | current supported | Personal-repository and issue operations.                                                   | Free; verify owner `rajpaladitiya` before writes. |
| `uv`                |          `0.12.7` | Python install, virtual environment, dependency resolution, locking, and command execution. | MIT OR Apache-2.0.                                |
| `pnpm`              |         `11.24.0` | Node dependency install, lockfile, and scripts.                                             | MIT.                                              |
| GNU/compatible Make |            system | Stable one-command developer interface.                                                     | Free; commands delegate to `uv` and `pnpm`.       |

Expected bootstrap interface:

```text
make bootstrap      install pinned Python and console dependencies
make doctor         validate local environment without external writes
make check          format-check, lint, types, unit/integration tests, docs
make test           all offline tests
make demo           deterministic provider-free evaluation and report
make e2e            local Chromium end-to-end tests
```

## 2. Coding and static quality

### Python

- `ruff format --check .`
- `ruff check .`
- `mypy --strict src tests`

### TypeScript/React

- `pnpm --dir console exec tsc --noEmit`
- ESLint flat configuration with type-aware, hooks, and JSX accessibility rules.
- `prettier --check` for TS/TSX/CSS/JSON/YAML/Markdown.

No editor is required. Repository settings are portable to any editor.

## 3. Test execution

| Tool           | Scope                   | Default use                                                        |
| -------------- | ----------------------- | ------------------------------------------------------------------ |
| pytest         | Python suites           | Unit, property, integration, contract, replay, adversarial.        |
| Vitest + jsdom | Console suites          | Components, API states, interactions, semantic accessibility.      |
| Playwright     | Real browser            | Chromium on pull requests; Chromium/Firefox/WebKit before release. |
| MSW            | HTTP simulation         | Same handlers for console component and E2E failure-state tests.   |
| respx          | Backend HTTP simulation | Reject unexpected Razorpay/model network calls.                    |
| Hypothesis     | Generated behavior      | Policy invariants and stateful replay/concurrency properties.      |
| axe-core       | Accessibility           | jsdom smoke plus real-browser release gate.                        |

Full suite design and commands live in `testing/test-plan.md`.

## 4. API and contract workflow

1. FastAPI produces an OpenAPI JSON artifact from Pydantic response models.
2. `openapi-typescript` generates `console/src/api/schema.d.ts`.
3. CI regenerates it and fails on an uncommitted diff.
4. HTTP tests validate error/status examples against the same schemas.

Do not hand-maintain duplicate TypeScript API interfaces.

## 5. Database workflow

- SQL migrations live in `migrations/NNNN_description.sql`.
- `salvage migrate` applies them and records checksums.
- Tests create a new temporary file database per test or suite; do not use a
  shared in-memory connection for concurrency behavior.
- `sqlite3` CLI is optional for inspection, not a migration mechanism.
- Deterministic demo databases are regenerated from text fixtures and never
  treated as source files.

## 6. Webhook exposure

Use `zrok2` 2.x for the Razorpay Test Mode evidence run. Current Razorpay docs
recommend zrok because common public tunnel domains can be blacklisted.

Safety rules:

- expose only the local webhook port/path needed for the session;
- use a random, non-product-name public share;
- never expose the SQLite file, debug console, or development inspector;
- disable the share after evidence capture;
- record the zrok and Razorpay test configuration in the incident/evidence log,
  not secrets.

`zrok` is Apache-2.0 and the public `zrok.io` service offers a free path. If the
service is unavailable, use a controlled staging host or self-hosted runner; do
not silently switch to a paid tunnel.

ADR-0014 permits an account-free temporary Cloudflare Quick Tunnel for the
connected simulator when zrok account setup is unavailable. Only the dedicated
webhook receiver port is exposed. A public URL does not prove Razorpay delivery;
dashboard registration and an authenticated received event are required.

## 7. Documentation quality

| Tool              |        Baseline | Use                                          |
| ----------------- | --------------: | -------------------------------------------- |
| Prettier          |         `3.9.6` | Consistent Markdown/YAML formatting.         |
| markdownlint-cli2 |        `0.23.2` | Heading, list, fence, and whitespace checks. |
| cspell            |        `10.1.1` | Project dictionary and typo detection.       |
| Mermaid           | GitHub renderer | Source-controlled architecture diagrams.     |

Link validation should check all relative links on every change and external
links on a scheduled/manual run to avoid flaky CI during the deadline window.

## 8. Security and dependency checks

- `pip-audit 2.10.1` scans the locked Python environment.
- `pnpm audit --prod` scans console runtime dependencies; a separate full audit
  reports developer-tool findings.
- Local `gitleaks` CLI scans the working tree and Git history. Use the open
  source CLI directly rather than relying on an organization-licensed action.
- GitHub Dependabot may be enabled for the personal repository; update PRs do
  not bypass tests.
- Pin third-party GitHub Actions to immutable commit SHAs, with the upstream
  release tag noted in a comment.
- Generate a simple dependency/license inventory for the release artifact.

No paid SAST, hosted secret manager, or advanced security product is required.

## 9. Continuous integration

GitHub Actions is the selected CI because standard hosted runners are free for
public repositories; private personal repositories have an included allowance.
To guarantee zero spend:

- keep billing limits at zero/no paid overage;
- use Ubuntu standard runners only;
- cancel superseded runs;
- cache lockfile-keyed dependencies, not build outputs containing secrets;
- run Chromium only on pull requests;
- run three-browser Playwright manually or for a release candidate;
- retain small test reports for a short period;
- preserve `make check` as the complete local fallback.

Planned workflows:

- `quality.yml`: formatting, lint, types, OpenAPI generation, docs.
- `test-backend.yml`: unit/property/integration/contract/replay/adversarial.
- `test-console.yml`: Vitest/jsdom, build, Chromium E2E.
- `security.yml`: dependency and secret scans, manually/nightly if minutes are
  constrained.
- `sandbox-evidence.yml`: never automatic; requires Test Mode secrets and an
  explicit environment approval.

## 10. Observability and evidence

No hosted monitoring service is selected. Evidence is local and reviewable:

- JSONL structured logs;
- SQLite audit/decision records;
- `results.json` and static HTML evaluation report;
- JUnit XML and coverage files in CI;
- Playwright HTML/trace only on failure;
- `INCIDENTS.md` for observed architecture-changing failures;
- sandbox evidence manifest with timestamp, policy/map versions, test event IDs,
  and redacted results.

## 11. Repository and issue operations

- Owner must be `rajpaladitiya`.
- Repository is created private first and may become public only after secret,
  history, license, and clean-clone review.
- GitHub Issues hold planned work once the personal remote is verified.
- Never pass `--org`, transfer ownership, or select an EC-aware remote.
- Before every first GitHub write in a session, inspect `nameWithOwner`.

See `agents/issue-tracker.md` for exact guardrails.

## 12. Deliberately excluded tools

- Docker Desktop as a requirement: unnecessary and its licensing varies by use
  context.
- Kubernetes/serverless hosting: no MVP need.
- Redis/Celery: SQLite job table is enough.
- Postgres: adds setup without improving the prototype proof.
- Sentry/Datadog/New Relic: hosted cost and no acceptance need.
- Paid LLM APIs: offline/local/free providers are sufficient.
- Snapshot-heavy UI testing: assertions target user-visible semantics.
- `ngrok`/`cloudflared` as the default tunnel: current Razorpay docs warn that
  common tunnel domains may be blocked and specifically document zrok.

## 13. Primary references

- [GitHub Actions billing](https://docs.github.com/en/billing/concepts/product-billing/github-actions)
- [zrok repository](https://github.com/openziti/zrok)
- [Razorpay webhook validation/testing](https://razorpay.com/docs/webhooks/validate-test/)
- [uv](https://docs.astral.sh/uv/)
- [pnpm](https://pnpm.io/)
- [Ruff](https://docs.astral.sh/ruff/)
- [Gitleaks CLI](https://github.com/gitleaks/gitleaks)
