# Test catalog

This catalog names the minimum behavior tests. IDs are stable references for
issues, code, and release evidence. Implementation may split or parameterize a
case, but must not silently drop it.

## Ingress (`ING`)

| ID      | Scenario                                           | Expected result                                       |
| ------- | -------------------------------------------------- | ----------------------------------------------------- |
| ING-001 | Valid signed failure with new event ID             | 202; one event and one queued job.                    |
| ING-002 | Same valid event delivered twice                   | Both 202; one event/job.                              |
| ING-003 | Same valid event delivered concurrently            | One insert wins; one event/job; no 5xx.               |
| ING-004 | Missing signature                                  | Reject; no rows.                                      |
| ING-005 | Wrong signature                                    | Reject; no rows.                                      |
| ING-006 | Signature valid for reserialized but not raw bytes | Reject, proving raw-byte verification.                |
| ING-007 | Missing event ID                                   | Reject; no rows.                                      |
| ING-008 | Invalid JSON with otherwise valid HMAC             | Reject projection; no job.                            |
| ING-009 | Unknown extra fields                               | Accept; extras are not persisted.                     |
| ING-010 | Oversized body                                     | Reject before expensive work.                         |
| ING-011 | SQLite commit failure                              | Non-2xx; no false acknowledgement.                    |
| ING-012 | Adapter/model spy attached                         | No outbound/advisory call during request.             |
| ING-013 | Out-of-order event fixtures                        | Accept and enqueue without assuming order.            |
| ING-014 | Secret rotation old-event fixture                  | Behavior follows explicit configured rotation policy. |

## Triage and map (`TRI`)

| ID      | Scenario                                | Expected result                                            |
| ------- | --------------------------------------- | ---------------------------------------------------------- |
| TRI-001 | Approved known Class A/B/C/D reason     | Exact configured effective class.                          |
| TRI-002 | Unknown reason                          | Effective D and review required.                           |
| TRI-003 | Model suggests A for unknown            | Effective D unchanged; advisory A recorded only.           |
| TRI-004 | `source=risk` conflicts with non-D map  | Effective D.                                               |
| TRI-005 | Duplicate YAML reason                   | Startup validation failure.                                |
| TRI-006 | Invalid class/action/source restriction | Startup validation failure.                                |
| TRI-007 | Normalized map reordered                | Same fingerprint.                                          |
| TRI-008 | Material map value changed              | Different fingerprint.                                     |
| TRI-009 | Unapproved/draft map entry              | Treated as unknown/review required.                        |
| TRI-010 | Current published set comparison        | Actual deterministic coverage and fallback count reported. |

## Rulebook (`POL`)

| ID      | Scenario                                       | Expected result                                |
| ------- | ---------------------------------------------- | ---------------------------------------------- |
| POL-001 | Class A below cap after cooldown               | Schedule-retry default allowed/selected.       |
| POL-002 | Class A at cap                                 | Stop; no retry.                                |
| POL-003 | Class A before cooldown                        | No effect and next eligible time.              |
| POL-004 | Class A never contacts customer                | No message/link in allowed set.                |
| POL-005 | Class B below cap before 12h                   | No retry yet.                                  |
| POL-006 | Class B eligible later retry                   | Deterministic scheduled retry.                 |
| POL-007 | Class B pre-final contact under cap            | One outbox action if configured.               |
| POL-008 | Class B contact cap reached                    | No customer message.                           |
| POL-009 | Class C first eligible ask                     | Link/outbox allowed; no same-rail retry.       |
| POL-010 | Class C link/contact already used              | Stop.                                          |
| POL-011 | Class D any counts/time                        | Operator escalation only.                      |
| POL-012 | Manual stop list any class                     | No retry/contact.                              |
| POL-013 | Required adapter capability absent             | No executable effect.                          |
| POL-014 | Boundary exactly at cooldown                   | Eligibility matches documented inclusive rule. |
| POL-015 | Clock/random/network/database access attempted | Architecture/unit guard fails.                 |
| POL-016 | Same explicit inputs repeated                  | Equal decision and fingerprint.                |

## Gatekeeper (`GAT`)

| ID      | Scenario                                     | Expected result                             |
| ------- | -------------------------------------------- | ------------------------------------------- |
| GAT-001 | Valid deterministic action and fresh state   | Approved with all check records.            |
| GAT-002 | Action not in allowed set                    | Rejected, `off_list`.                       |
| GAT-003 | Retry/contact on Class D                     | Rejected, `hard_stop`.                      |
| GAT-004 | Attempt cap reached after decision           | Rejected, `attempt_cap`.                    |
| GAT-005 | Cooldown no longer elapsed under fresh facts | Rejected, `cooldown`.                       |
| GAT-006 | Contact cap reached after decision           | Rejected, `contact_cap`.                    |
| GAT-007 | Manual stop added after decision             | Rejected, `manual_stop`.                    |
| GAT-008 | Adapter capability removed                   | Rejected, `capability_missing`.             |
| GAT-009 | Amount/currency mismatch                     | Rejected, `immutable_fact_mismatch`.        |
| GAT-010 | Refund/credit/discount action injected       | Rejected, `prohibited_action`.              |
| GAT-011 | Stale state version                          | Abort/recompute; no intent.                 |
| GAT-012 | Any rejected action                          | Operator escalation/no aggressive fallback. |

## Queue, persistence, and effects (`PER`)

| ID      | Scenario                                | Expected result                                      |
| ------- | --------------------------------------- | ---------------------------------------------------- |
| PER-001 | Two workers claim one job               | Exactly one active lease.                            |
| PER-002 | Lease expires after worker crash        | Job becomes claimable.                               |
| PER-003 | Job exceeds attempts                    | Dead letter plus operator escalation.                |
| PER-004 | Decision transaction fails halfway      | No partial decision/check/intent/state/ledger rows.  |
| PER-005 | State version changes before commit     | Rollback and recompute.                              |
| PER-006 | Duplicate idempotency key               | Existing logical intent returned; no second intent.  |
| PER-007 | Crash before external call              | Pending intent resumes with same key.                |
| PER-008 | Timeout with ambiguous provider outcome | Intent remains reconcilable; retry bounded/same key. |
| PER-009 | External success then local crash       | Recovery does not create a new logical effect.       |
| PER-010 | Outbox created                          | No real transport call; console-visible message.     |
| PER-011 | Migration from empty                    | Current schema/checksums and readiness pass.         |
| PER-012 | Modified applied migration              | Checksum/startup failure.                            |

## Advisory (`ADV`)

| ID      | Scenario                                | Expected result                                           |
| ------- | --------------------------------------- | --------------------------------------------------------- |
| ADV-001 | Valid advisory JSON                     | Stored with provenance; no action change.                 |
| ADV-002 | Malformed JSON                          | Bounded repair/fallback then omit.                        |
| ADV-003 | Wrong enum/missing field/oversized text | Local validation failure.                                 |
| ADV-004 | Off-list refund suggestion              | Rejected/recorded; deterministic action unchanged.        |
| ADV-005 | Prompt injection in description         | Deterministic action unchanged; safe annotation behavior. |
| ADV-006 | Provider timeout/429/5xx                | Bounded fallback; job succeeds.                           |
| ADV-007 | All providers off                       | Complete decision with advice absent.                     |
| ADV-008 | Cache hit                               | No network call.                                          |
| ADV-009 | Prompt/schema/provider/model changes    | Cache miss with distinct key.                             |
| ADV-010 | Cache contains invalid legacy output    | Reject and follow normal fallback.                        |
| ADV-011 | Captured provider request               | No amount, secret, or contact PII.                        |
| ADV-012 | 50-call manual characterization         | Rates/latency reported, exact prose not asserted.         |

## Ledger and replay (`AUD`)

| ID      | Scenario                           | Expected result                                                    |
| ------- | ---------------------------------- | ------------------------------------------------------------------ |
| AUD-001 | Empty/valid chain                  | Verification passes.                                               |
| AUD-002 | Entry content changed              | First affected hash reported.                                      |
| AUD-003 | Previous hash changed              | Mismatch reported.                                                 |
| AUD-004 | Entry removed/inserted/reordered   | Chain fails at boundary.                                           |
| AUD-005 | Canonical object key order differs | Same entry hash.                                                   |
| AUD-006 | Material value differs             | Different hash.                                                    |
| AUD-007 | Same demo rebuilt twice            | Same batch/result/decision hash.                                   |
| AUD-008 | Live receive times differ          | Operational ledger may differ; deterministic claim remains scoped. |

## Console jsdom (`UIJ`)

| ID      | Scenario                                | Expected result                                             |
| ------- | --------------------------------------- | ----------------------------------------------------------- |
| UIJ-001 | Loading/empty/error/success             | Correct accessible status and content.                      |
| UIJ-002 | A/B/C/D decision cards                  | Effective class, allowed set, action, reasons displayed.    |
| UIJ-003 | Unknown with advisory suggestion        | Effective D visually/semantically distinct from suggestion. |
| UIJ-004 | Gatekeeper rejection                    | Rejection reason and no executed effect.                    |
| UIJ-005 | Pending/dry-run/succeeded/failed effect | Accurate status labels.                                     |
| UIJ-006 | Filter by class/status/reason           | User-event interaction and query behavior.                  |
| UIJ-007 | Keyboard tabs/controls                  | Accessible names and DOM order.                             |
| UIJ-008 | Money value                             | Integer minor units format correctly with currency.         |
| UIJ-009 | Script/HTML injection fields            | Literal text; no element/script execution.                  |
| UIJ-010 | API returns invalid response/error      | Safe error UI and no crash.                                 |
| UIJ-011 | Any interaction                         | No POST/PATCH/PUT/DELETE request.                           |
| UIJ-012 | Axe component scan                      | No configured serious violation.                            |

## Browser E2E (`E2E`)

| ID      | Scenario                            | Expected result                              |
| ------- | ----------------------------------- | -------------------------------------------- |
| E2E-001 | API/worker/console startup          | Health ready and console loads.              |
| E2E-002 | Signed webhook → worker → browser   | New decision appears without internal mocks. |
| E2E-003 | Class D refusal                     | No effect/contact and full explanation.      |
| E2E-004 | Narrow/desktop layouts              | No critical overlap or horizontal overflow.  |
| E2E-005 | Keyboard-only run                   | Visible focus and reachable controls.        |
| E2E-006 | CSP/injection fixture               | No execution or CSP error.                   |
| E2E-007 | Axe page scans                      | No serious/critical violation.               |
| E2E-008 | Chromium/Firefox/WebKit release run | Core flows pass in all three.                |

## Evaluation (`EVAL`)

| ID       | Scenario                            | Expected result                                         |
| -------- | ----------------------------------- | ------------------------------------------------------- |
| EVAL-001 | Three policies, one batch           | Identical visible batch digest.                         |
| EVAL-002 | Policy attempts hidden-truth access | Type/module guard fails.                                |
| EVAL-003 | Metric denominators zero            | Defined non-misleading output.                          |
| EVAL-004 | Class D under Salvage               | Zero violations.                                        |
| EVAL-005 | Retry-all risk scenario             | Violation/waste counted per definitions.                |
| EVAL-006 | Same seed/version                   | Identical scenario/result hashes.                       |
| EVAL-007 | Different seed                      | Different batch digest.                                 |
| EVAL-008 | ±30% sensitivity                    | Each assumption variation is actually applied/reported. |
| EVAL-009 | Salvage loses raw recovery          | Report shows result without suppression.                |
| EVAL-010 | JSON vs HTML                        | Same metrics/assumptions/provenance.                    |
| EVAL-011 | Fallback coverage                   | Present and correct for every run.                      |
| EVAL-012 | Real-vs-simulated statement         | Present in artifacts.                                   |

## Sandbox (`SBX`)

| ID      | Scenario                           | Expected result                                           |
| ------- | ---------------------------------- | --------------------------------------------------------- |
| SBX-001 | Valid Test Mode failed payment     | Official-shape webhook through core pipeline.             |
| SBX-002 | Duplicate delivery/replay evidence | No duplicate logical decision/effect.                     |
| SBX-003 | Tampered signature                 | Rejected publicly.                                        |
| SBX-004 | Known injectable reason            | Expected deterministic class/policy.                      |
| SBX-005 | Hard-stop evidence unavailable     | Limitation recorded; signed official-shape fixture used.  |
| SBX-006 | Standard Payment Link capability   | Test link only within account limit, or labelled dry-run. |
| SBX-007 | zrok share teardown                | Public endpoint no longer reachable after run.            |

## Documentation and repository (`DOC`)

| ID      | Scenario                      | Expected result                                  |
| ------- | ----------------------------- | ------------------------------------------------ |
| DOC-001 | Markdown/format/spell/links   | All maintained docs pass.                        |
| DOC-002 | ADR index                     | Every listed ADR exists and status matches.      |
| DOC-003 | AGENTS vs CLAUDE skills block | Byte-identical synchronized block.               |
| DOC-004 | Stack versions vs lockfiles   | No undocumented direct dependency drift.         |
| DOC-005 | Git remote owner              | Exactly `rajpaladitiya`; no organization remote. |
| DOC-006 | Secret/history scan           | Empty before public visibility.                  |
