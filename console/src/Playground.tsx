import { useEffect, useRef, useState, type FormEvent } from "react";
import { loadPlayground, runPlayground, type PlaygroundReceipt, type PlaygroundRequest, type PlaygroundState } from "./api/client";

const outcomes: Record<string, { title: string; description: string }> = {
  schedule_retry: { title: "A bounded retry is allowed.", description: "Salvage recorded a dry-run retry intent. No charge was attempted." },
  schedule_later_retry: { title: "Wait before trying again.", description: "Salvage recorded a later-retry intent under its cooldown policy. No charge was attempted." },
  create_payment_link: { title: "Offer a different payment path.", description: "Salvage recorded a dry-run link intent and a disabled message. No real link or message was created." },
  escalate_review: { title: "Stop. This needs human review.", description: "No retry, payment link, or customer contact was created." },
  stop: { title: "Stop safely.", description: "No automated recovery effect was created." },
};

export default function Playground() {
  const [state, setState] = useState<PlaygroundState | null>(null);
  const [available, setAvailable] = useState(true);
  const [connectionAttempt, setConnectionAttempt] = useState(0);
  const [scenario, setScenario] = useState<PlaygroundRequest["scenario"]>("gateway_timeout");
  const [amount, setAmount] = useState("1250.00");
  const [method, setMethod] = useState<PlaygroundRequest["method"]>("card");
  const [receipt, setReceipt] = useState<PlaygroundReceipt | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const retryRequest = useRef<PlaygroundRequest | null>(null);
  const inFlight = useRef(false);

  useEffect(() => {
    let active = true;
    loadPlayground().then((data) => { if (active) { setState(data); setAvailable(true); setError(""); } })
      .catch((failure) => { if (active) { setAvailable(false); setError(failure instanceof Error ? failure.message : "Connection unavailable"); } });
    return () => { active = false; };
  }, [connectionAttempt]);

  function changeInput() {
    retryRequest.current = null;
    setError("");
  }

  async function run(request: PlaygroundRequest) {
    if (inFlight.current) return;
    inFlight.current = true;
    retryRequest.current = request;
    setBusy(true);
    setError("");
    try {
      const result = await runPlayground(request);
      setReceipt(result);
      retryRequest.current = null;
      const refreshed = await loadPlayground().catch(() => null);
      if (refreshed) setState(refreshed);
    } catch (failure) {
      setError(failure instanceof Error ? failure.message : "The backend is unavailable. Retry this event safely.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    // Parse display input with integer arithmetic; the API only accepts minor units.
    if (!/^\d+(\.\d{1,2})?$/.test(amount)) {
      setError("Enter a positive rupee amount with no more than two decimal places.");
      return;
    }
    const [whole, fraction = ""] = amount.split(".");
    const amountMinor = Number(whole) * 100 + Number(fraction.padEnd(2, "0"));
    if (!Number.isSafeInteger(amountMinor) || amountMinor < 1 || amountMinor > 100_000_000) {
      setError("Use a test amount between ₹0.01 and ₹10,00,000.");
      return;
    }
    void run(retryRequest.current ?? { run_id: crypto.randomUUID(), scenario, amount_minor: amountMinor, method });
  }

  const decision = receipt?.decision;
  const outcome = decision ? outcomes[decision.effect_action ?? decision.selected_action] ?? outcomes.stop : null;

  return <section className="playground" id="playground" aria-labelledby="playground-title">
    <div className="playground-heading">
      <div><p className="eyebrow">Your hands on the controls</p><h2 id="playground-title">Try a payment failure.</h2><p>Choose a scenario. Run the real decision engine. See exactly what it permits.</p></div>
      <span className="sandbox-label">SYNTHETIC ONLY · NO MONEY MOVED</span>
    </div>
    {!available ? <div className="playground-unavailable" role="status">Interactive tests need the local Salvage backend in demo mode. This static showcase can only display the recorded evidence below.<p>{error}</p><button type="button" onClick={() => setConnectionAttempt((value) => value + 1)}>Reconnect playground</button></div> : <div className="playground-grid">
      <form onSubmit={submit} className="playground-form">
        <fieldset disabled={busy || !state}>
          <legend>1. What went wrong?</legend>
          <div className="scenario-options">{state?.scenarios.map((option) => <label key={option.id} className={`scenario-option ${scenario === option.id ? "chosen" : ""}`}>
            <input type="radio" name="failure-scenario" value={option.id} checked={scenario === option.id} onChange={() => { changeInput(); setScenario(option.id); if (option.id === "card_expired") setMethod("card"); }} />
            <span><b>{option.label}</b><small>{option.description}</small></span>
          </label>)}</div>
          <div className="playground-inputs">
            <label>2. Test amount (INR)<input aria-label="Test amount in rupees" inputMode="decimal" value={amount} maxLength={12} onChange={(event) => { changeInput(); setAmount(event.target.value); }} required /></label>
            <label>Payment method<select value={method} disabled={scenario === "card_expired"} onChange={(event) => { changeInput(); setMethod(event.target.value as PlaygroundRequest["method"]); }}><option value="card">Card</option><option value="upi">UPI</option><option value="netbanking">Netbanking</option></select></label>
          </div>
          <button className="run-button" type="submit" disabled={!state || state.remaining_runs === 0}>{busy ? "Processing your test…" : retryRequest.current ? "Retry this test safely →" : "Run recovery test →"}</button>
        </fieldset>
        <p className="playground-fineprint">Generated payment IDs only. No credentials or personal data needed. Tests are saved separately from the evaluation batch.</p>
        {state?.remaining_runs === 0 ? <p role="status">The 200-test local safety limit is reached. Existing tests can still be replayed.</p> : null}
        {error ? <p role="alert" className="playground-error">{error}</p> : null}
      </form>
      <div className="playground-result" aria-live="polite" aria-busy={busy}>
        {receipt && decision && outcome ? <>
          <div className="result-kicker"><span>{receipt.duplicate ? "DUPLICATE EVENT · NO EXTRA EFFECT" : "TEST COMPLETE · REAL BACKEND"}</span><span className={`class-badge class-${decision.effective_class}`}>{decision.effective_class}</span></div>
          <p className="result-input">Result for {state?.scenarios.find((item) => item.id === receipt.request.scenario)?.label ?? receipt.request.scenario} · ₹{(receipt.request.amount_minor / 100).toLocaleString("en-IN")} · {receipt.request.method}</p>
          <h3>{outcome.title}</h3><p className="result-description">{outcome.description}</p>
          <ol className="playground-stages">
            <li><span>✓</span><div><b>Synthetic event verified & stored</b><p>The same raw-byte verifier and durable queue used by webhook ingress.</p></div></li>
            <li><span>✓</span><div><b>Rulebook selected Class {decision.effective_class}</b><p>{decision.triage_rationale}</p></div></li>
            <li><span>✓</span><div><b>{decision.gate_checks.filter((check) => check.passed).length}/{decision.gate_checks.length} Gatekeeper checks passed</b><p>{decision.effect_state ? "Only a dry-run intent was recorded." : "No automated effect was allowed."}</p></div></li>
            <li><span>{receipt.ledger_valid ? "✓" : "!"}</span><div><b>{receipt.ledger_valid ? "Audit ledger verified" : "Audit ledger check failed"}</b><p>Recorded in {receipt.elapsed_ms} ms · no external payment API called.</p></div></li>
          </ol>
          {decision.advisory_class ? <div className="playground-advice"><b>AI shadow suggested {decision.advisory_class}. Effective class stays {decision.effective_class}.</b><p>{decision.advisory_rationale}</p></div> : null}
          {decision.next_eligible_at ? <p className="next-eligible">Policy next eligible time: {new Date(decision.next_eligible_at).toLocaleString()} <span>(not an active charge schedule)</span></p> : null}
          <div className="receipt-counts"><span><b>{receipt.event_count}</b> event</span><span><b>{receipt.decision_count}</b> decision</span><span><b>{receipt.effect_count}</b> dry-run effect</span><span><b>{receipt.ledger_entry_count}</b> ledger entry</span></div>
          <div className="receipt-actions"><button type="button" disabled={busy} onClick={() => void run(receipt.request)}>Replay same event</button><a href={`/demo/v1/runs/${receipt.request.run_id}/receipt`} download>Download evidence ↓</a></div>
          <details className="playground-evidence"><summary>Inspect decision, checks & fingerprints</summary><p className="test-id">Test ID: {receipt.request.run_id}</p>{decision.gate_checks.map((check) => <p key={check.name}><b>{check.passed ? "✓" : "×"} {check.name.replaceAll("_", " ")}</b><br />{check.explanation}</p>)}<code>{decision.decision_hash}</code></details>
        </> : <div className="playground-empty"><span className="empty-symbol">↳</span><h3>Your next failure is a safe experiment.</h3><p>Run a test to see the decision, safety checks, dry-run effect, and a verifiable receipt here.</p><div><span>01 Choose</span><span>02 Run</span><span>03 Inspect</span></div></div>}
      </div>
    </div>}
    {state && state.recent.length > 0 ? <div className="playground-history"><b>Your recent tests</b><p>Saved locally · replay a previous event without creating another effect.</p><div>{state.recent.map((item) => <button type="button" key={item.decision_id} disabled={busy} onClick={() => void run({ run_id: item.event_id.replace("evt_play_", ""), scenario: item.reason as PlaygroundRequest["scenario"], amount_minor: item.amount_minor, method: item.method as PlaygroundRequest["method"] })}><span className={`class-badge class-${item.effective_class}`}>{item.effective_class}</span><span>{state.scenarios.find((option) => option.id === item.reason)?.label ?? item.reason}<small>₹{(item.amount_minor / 100).toLocaleString("en-IN")} · {new Date(item.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</small></span><span aria-hidden="true">↻</span></button>)}</div></div> : null}
  </section>;
}
