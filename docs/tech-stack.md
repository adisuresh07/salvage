# Technology stack

- **Status:** Accepted baseline for the MVP
- **Registry and documentation check:** 2026-08-29

Exact versions below are the scaffold baseline. Lockfiles are authoritative
after implementation begins; update this document when a major dependency or its
architectural role changes.

## 1. Selection principles

- Mandatory runtime and libraries must be free/open source.
- The offline demo cannot require a hosted service.
- Prefer standard-library features and small, well-scoped dependencies.
- Use the language that provides the strongest correctness leverage for each
  isolated layer: Python for the decision system, TypeScript for the view.
- No business or payment policy is duplicated in TypeScript.
- No Redis, Celery, Postgres, container platform, or paid observability service
  is needed for the prototype.

## 2. Runtime baseline

| Runtime |                                                   Baseline | License/cost                | Why                                                                          |
| ------- | ---------------------------------------------------------: | --------------------------- | ---------------------------------------------------------------------------- |
| Python  |                                                   `3.14.x` | PSF; free                   | Current supported CPython line with modern typing and broad library support. |
| Node.js |                           `24.20.x` LTS, minimum `24.15.0` | MIT; free                   | Supported LTS line and satisfies jsdom 30's Node 24 engine floor.            |
| SQLite  | CPython-bundled SQLite; record runtime version in `doctor` | Public domain               | One-file durable store and queue with no service setup.                      |
| Browser | Current Chromium for CI; current Firefox/WebKit at release | Free engines via Playwright | Real layout, navigation, and browser behavior outside jsdom.                 |

Do not use Node 20: it is end-of-life as of this baseline. Python and Node
minor/patch versions are pinned through `.python-version`, `.node-version`, and
CI setup.

## 3. Python application dependencies

| Package             |  Baseline | License                  | Role and constraints                                                                                                      |
| ------------------- | --------: | ------------------------ | ------------------------------------------------------------------------------------------------------------------------- |
| `fastapi`           | `0.141.1` | MIT                      | Webhook and versioned read API. No policy in route functions.                                                             |
| `uvicorn`           |  `0.52.4` | BSD-3-Clause             | ASGI server for local/demo use.                                                                                           |
| `pydantic`          |  `2.13.5` | MIT                      | Domain/API/advisory schemas and strict validation. Advisory validation remains local even when a provider offers schemas. |
| `pydantic-settings` |  `2.15.0` | MIT                      | Typed environment configuration and safe separation of test/live-disabled modes.                                          |
| `httpx`             |  `0.28.1` | BSD-3-Clause             | Explicit async/sync HTTP adapters with fixed origins, timeouts, and test interception.                                    |
| `PyYAML`            |   `6.0.3` | MIT                      | Reviewable reason and policy data; use only `safe_load` followed by Pydantic validation.                                  |
| `typer`             |  `0.27.2` | MIT                      | Small operator/developer CLI.                                                                                             |
| `numpy`             |   `2.5.2` | BSD/compatible composite | Seeded evaluation and sensitivity sweep only; forbidden in money arithmetic.                                              |
| `Jinja2`            |   `3.1.6` | BSD-3-Clause             | Static offline report from the typed evaluation result. Autoescape enabled.                                               |
| `structlog`         |  `26.1.0` | MIT OR Apache-2.0        | Structured local logs with explicit redaction.                                                                            |

### Python standard library used deliberately

- `sqlite3` for persistence and migrations.
- `hmac`, `hashlib`, and `secrets.compare_digest` for webhook/ledger work.
- `decimal` only when parsing human fixture input; stored money remains integer.
- `dataclasses`, `enum`, `datetime`, `zoneinfo`, `json`, and `uuid` behind
  injectable interfaces where determinism matters.

### Razorpay integration choice

The core adapter uses `httpx` plus documented REST contracts and standard
library HMAC verification. The official `razorpay` Python SDK `2.0.1` is MIT
licensed and may be used in a sandbox spike or conformance test, but it is not
load-bearing because the project needs explicit timeouts, idempotency headers,
capability restrictions, and async-friendly test interception.

## 4. Python test dependencies

| Package          |   Baseline | License      | Role                                                                            |
| ---------------- | ---------: | ------------ | ------------------------------------------------------------------------------- |
| `pytest`         |    `9.1.1` | MIT          | Test runner and fixtures.                                                       |
| `pytest-asyncio` |    `1.4.0` | Apache-2.0   | Async API/adapter tests.                                                        |
| `hypothesis`     | `6.165.10` | MPL-2.0      | Property and state-machine tests for invariants, caps, dedupe, and replay.      |
| `respx`          |   `0.23.1` | BSD-3-Clause | Strict HTTPX request/response interception. Unmatched network calls fail tests. |
| `pytest-cov`     |    `7.1.0` | MIT          | Branch coverage and targeted domain gates.                                      |

`freezegun` is intentionally omitted. Domain time is injected. If code becomes
hard to test without freezing global time, fix the boundary rather than hiding
it with a clock patch.

## 5. Console application dependencies

| Package                | Baseline | License    | Role and constraints                                       |
| ---------------------- | -------: | ---------- | ---------------------------------------------------------- |
| `react` / `react-dom`  | `19.2.8` | MIT        | Read-only operator UI.                                     |
| `vite`                 |  `8.2.2` | MIT        | Development server and static build.                       |
| `typescript`           |  `5.9.3` | Apache-2.0 | Strict UI and generated API typing; pinned to the `openapi-typescript` 7 peer range. |
| `@vitejs/plugin-react` |  `6.1.1` | MIT        | React/Vite integration.                                    |
| `openapi-typescript`   | `7.13.0` | MIT        | Generate types from FastAPI's checked-in OpenAPI artifact. |

The demo-only synthetic playground uses the same stack and a separate SQLite
file (ADR-0013). Its generated request types do not expose payment controls.

No router, global state library, chart library, UI kit, or CSS framework is
required. One read-only application can use platform `fetch`, React state,
semantic HTML tables, accessible SVG/CSS bars, and plain CSS tokens. Recharts,
Redux, TanStack Query, Tailwind, and component kits remain optional future
choices, not hidden dependencies.

## 6. Console test dependencies, including jsdom

| Package                       | Baseline | License    | Role                                                      |
| ----------------------------- | -------: | ---------- | --------------------------------------------------------- |
| `vitest`                      | `4.1.11` | MIT        | Unit/component runner aligned with Vite.                  |
| `@vitest/coverage-v8`         | `4.1.11` | MIT        | JavaScript/TypeScript coverage.                           |
| `jsdom`                       | `30.0.1` | MIT        | DOM environment for component tests under Node.           |
| `@testing-library/react`      | `16.3.3` | MIT        | Render and query React like a user.                       |
| `@testing-library/dom`        | `10.4.1` | MIT        | Accessible DOM queries used by React Testing Library.     |
| `@testing-library/jest-dom`   |  `7.0.1` | MIT        | DOM-specific assertions.                                  |
| `@testing-library/user-event` | `14.6.6` | MIT        | Realistic keyboard/pointer interactions.                  |
| `msw`                         | `2.15.0` | MIT        | Shared HTTP mocks for jsdom and browser tests.            |
| `axe-core`                    | `4.13.0` | MPL-2.0    | Automated accessibility rules in rendered views.          |
| `@playwright/test`            | `1.62.1` | Apache-2.0 | Real-browser E2E, navigation, layout, and trace evidence. |
| `@axe-core/playwright`        | `4.13.0` | MPL-2.0    | Accessibility checks in a real browser.                   |

### jsdom contract

Vitest uses `environment: "jsdom"` for React component tests. jsdom is for DOM
structure, accessible names/roles, events, state transitions, async fetch
behavior, and text escaping. It does not render layout or implement real
navigation. Tests involving CSS geometry, responsive layout, focus visibility,
downloads, browser navigation, or cross-browser behavior belong in Playwright.

Never enable arbitrary untrusted script execution in jsdom. API descriptions and
model rationale are rendered through React text nodes.

## 7. Model options

No model provider is mandatory.

For ADR-0014's opt-in connected simulator the only online model provider is
Ollama Cloud over existing `httpx`, defaulting to the discovered `gpt-oss:20b`
model. It never falls back to local Ollama, Groq, or fixtures. Offline evaluation
remains provider-free. No JavaScript AI SDK, database, or queue dependency was
added. A temporary webhook-only tunnel may use checksum-verified cloudflared
2026.8.2; it is not a mandatory build dependency or production host.

| Option            | Cost posture                             | MVP role                                             | Safety notes                                                                                                                                                     |
| ----------------- | ---------------------------------------- | ---------------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `SALVAGE_LLM=off` | Free, default                            | Omit advice and fail unknown reasons closed.         | Required CI/offline path.                                                                                                                                        |
| Ollama local      | MIT software; local compute              | Optional local advisory model.                       | Local structured output can be requested but is still validated with Pydantic. Model license must be checked separately.                                         |
| Ollama Cloud Free | $0 plan with session/weekly usage limits | Optional primary advisory provider for demos.        | Current Cloud docs say structured outputs are unsupported; prompt for JSON, validate locally, and bound repair. Usage is not a guaranteed fixed token allowance. |
| Groq Free Plan    | $0 plan, account/rate limits apply       | Optional strict-schema fallback/advisory experiment. | Current strict structured output supports `openai/gpt-oss-20b` and `120b`; local validation remains mandatory.                                                   |

Provider-free cached fixtures are committed only after validation and redaction.
No automatic paid fallback, credit card, or billing-enabled API is permitted.

## 8. Persistence and queue choices

SQLite uses:

- explicit SQL migrations checked into `migrations/`;
- `PRAGMA foreign_keys=ON`;
- WAL mode for local read/write coexistence;
- bounded `busy_timeout`;
- unique constraints for webhook event IDs, one job per event, one decision per
  event, and idempotency keys;
- short write transactions;
- one worker by default.

No ORM is selected. The schema is small and safety-critical SQL should remain
visible. Add a query layer with typed row conversion, not an active-record
abstraction.

## 9. Quality dependencies

| Tool/package                | Baseline | License | Role                                                   |
| --------------------------- | -------: | ------- | ------------------------------------------------------ |
| `ruff`                      | `0.16.5` | MIT     | Python lint and format.                                |
| `mypy`                      |  `2.3.1` | MIT     | Strict static checking for Python boundaries/domain.   |
| `eslint`                    | `10.9.1` | MIT     | TypeScript/React lint.                                 |
| `typescript-eslint`         | `8.68.0` | MIT     | Type-aware TypeScript lint rules.                      |
| `eslint-plugin-react-hooks` |  `7.1.1` | MIT     | Hooks correctness.                                     |
| `eslint-plugin-jsx-a11y`    | `6.10.2` | MIT     | Static accessibility checks.                           |
| `prettier`                  |  `3.9.6` | MIT     | Console/JSON/YAML/Markdown formatting.                 |
| `markdownlint-cli2`         | `0.23.2` | MIT     | Markdown structure checks.                             |
| `cspell`                    | `10.1.1` | MIT     | Documentation/code spelling with a project dictionary. |

## 10. Version policy

- Lock every direct and transitive dependency with `uv.lock` and
  `pnpm-lock.yaml`.
- Runtime files pin supported lines; CI tests the pinned runtime only during the
  deadline window.
- Patch/minor updates require the full offline suite and dependency audit.
- Major updates require a compatibility branch and ADR when behavior or
  architecture changes.
- Never use floating `latest` versions in CI or GitHub Action references.
- Record model IDs and provider behavior in generated results because hosted
  models can be retired independently of application code.

## 11. Free-only guardrail

“Free” means the project can be built, tested, and demonstrated locally without
payment. Optional free tiers are conveniences, not guarantees. If a service
changes pricing or requires billing, disable it and use the offline path. No
production deployment platform is selected for this prototype.

## 12. Primary references

- [Python active releases](https://www.python.org/downloads/)
- [Node.js release schedule](https://nodejs.org/en/about/previous-releases)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Pydantic](https://docs.pydantic.dev/)
- [SQLite](https://sqlite.org/docs.html)
- [Vitest test environments](https://vitest.dev/guide/environment.html)
- [jsdom](https://github.com/jsdom/jsdom)
- [React Testing Library](https://testing-library.com/docs/react-testing-library/intro/)
- [Playwright](https://playwright.dev/docs/intro)
- [Ollama pricing](https://ollama.com/pricing)
- [Ollama structured outputs](https://docs.ollama.com/capabilities/structured-outputs)
- [Groq structured outputs](https://console.groq.com/docs/structured-outputs)
- [Groq rate limits](https://console.groq.com/docs/rate-limits)
- [Razorpay Python SDK](https://github.com/razorpay/razorpay-python)
