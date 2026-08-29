# ADR-0008: Provider-neutral, free, and offline advisory layer

Status: Accepted

Date: 2026-08-29

## Context

Ollama Cloud and Groq offer free access with differing features/limits. Hosted
models can be unavailable, rate-limited, changed, or retired. Ollama Cloud does
not currently enforce structured outputs; Groq supports strict output only for
some models. The MVP must run at zero cost without keys.

## Decision

Define task-specific provider-neutral interfaces over `httpx`. Support model
off, cache-only, local Ollama, Ollama Cloud Free, and Groq Free adapters as
optional configurations. Always validate locally with Pydantic.

Cache only validated/redacted semantic tasks with provider/model/schema/prompt
provenance. Bound timeouts, repair, provider fallback, and retries. End every
ladder with deterministic omission/review. Never automatically enter a paid
tier.

## Alternatives considered

- Bind to one provider SDK: rejected due to lock-in and inconsistent safety
  features.
- Require a cloud provider for demo: rejected for cost/reliability.
- Trust strict provider schema without local validation: rejected because
  application invariants remain our responsibility.
- Self-host a large model as mandatory: rejected due to hardware burden.

## Consequences

### Positive

- Offline demo and CI are reliable.
- Provider comparison becomes measurable rather than architectural.
- Free-tier changes degrade gracefully.

### Negative / trade-offs

- Custom adapter code and contract tests.
- Cached examples must be transparently identified.
- Optional model capabilities may differ.

## Verification

- Same deterministic action with all providers/offline.
- Provider timeout, 429, malformed output, repair, fallback, and cache tests.
- No unmatched network in offline suite.
- Results record provider/model or `off/cache-only` provenance.

## Supersedes / superseded by

Supersedes a fixed Ollama-then-Groq requirement as a mandatory runtime path.
