# Incident log

Record only incidents that actually occur. Do not pre-write a story from the
examples in the historical strategy documents.

## Entry template

### YYYY-MM-DD — Short factual title

- **Status:** investigating | mitigated | resolved
- **Affected profile:** offline demo | local development | Razorpay Test Mode |
  optional provider
- **Related issue/commit:** link or identifier

#### Observation

What was directly observed, including the smallest useful timestamp, event ID,
command, status code, or error. Redact secrets and customer identifiers.

#### Initial hypothesis

What was first suspected and why.

#### Root cause

What evidence established the actual cause.

#### Structural change

What changed in architecture, code, policy, tests, or operations so the class of
failure is less likely or fails safely.

#### Verification

Name the regression test, drill, or evidence that now passes.

#### Follow-up

- [ ] Remaining action with owner/date.
- [ ] Documentation or ADR updated if needed.

---

## Current incidents

None recorded. The project has not begun implementation or sandbox execution.
