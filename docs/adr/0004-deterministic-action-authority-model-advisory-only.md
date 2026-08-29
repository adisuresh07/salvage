# ADR-0004: Deterministic action authority; models are advisory only

Status: Accepted

Date: 2026-08-29

## Context

Historical concept documents described a model “Planner” choosing one action
from a deterministic allowed list while also claiming the model was not in the
money path. If the model chooses between retry, contact, and stop, it still
influences a monetary/customer effect even when constrained. The claim and the
design therefore conflicted.

## Decision

The Rulebook deterministically returns both the allowed action set and selected
default action. Only that deterministic action can reach the Gatekeeper and
effect-intent path.

Models are renamed the Advisor and may provide wording, explanations, batch
summaries, and shadow suggestions. Advisory action/class suggestions are stored
for evaluation but cannot mutate effective class, selected action, time, caps,
amounts, recipients, or adapter calls.

## Alternatives considered

- Constrained model selects from allowed list: safer than free-form but still
  places model output in the effect decision.
- Model selects, Gatekeeper revalidates: prevents off-list behavior but does not
  make a model-selected on-list retry deterministic.
- Remove models entirely: safest, but loses useful language/shadow evaluation
  and the buildathon AI judgment demonstration.

## Consequences

### Positive

- “The model is not in the money path” is literally testable.
- Provider variance cannot change an effect.
- Offline behavior is first-class.

### Negative / trade-offs

- The model appears less agentic.
- Demonstration must explain the value of advisory/shadow AI honestly.
- Policy data must encode a deterministic default for every allowed state.

## Verification

- Domain types do not accept provider/advisory output when constructing an
  executable `PolicyDecision`.
- Adversarial advisory tests assert identical selected action with model off,
  malformed, injected, or provider-swapped.
- Architecture test forbids advisory module imports from policy/gatekeeper.

## Supersedes / superseded by

Supersedes the historical Planner-as-action-selector concept.
