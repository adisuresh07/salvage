import { useEffect, useRef, useState, type FormEvent } from "react";
import { createSimulatorRun, loadSimulator, loadSimulatorRun, syncSimulatorRun,
  type SimulatorInput, type SimulatorRun, type SimulatorState } from "./api/client";
import { openTestCheckout } from "./checkout";

const stages: Record<string, string> = {
  queued: "Decision queued", analyzing: "Ollama Cloud is analyzing", complete: "Evidence ready",
  creating_order: "Creating a Test Mode order", awaiting_payment: "Ready for Razorpay Checkout",
  payment_succeeded: "Payment success confirmed by Razorpay API", order_uncertain: "Order needs review",
  needs_review: "Processing needs review",
};
const errors: Record<string, string> = {
  cloud_authentication_failed: "Ollama rejected the key. Update the server-side cloud key.",
  cloud_rate_limited: "Your Ollama Cloud quota is temporarily exhausted.",
  cloud_timeout: "Ollama Cloud did not finish within the time limit.",
  cloud_response_rejected: "The cloud response did not pass our output validation.",
  generation_interrupted: "The server restarted during generation. It was not automatically repeated.",
  missing_cloud_key: "The Ollama Cloud key is not configured.",
};
const actionNames: Record<string, string> = {
  schedule_retry: "Schedule a bounded retry", schedule_later_retry: "Wait before retrying",
  create_payment_link: "Offer a fresh payment path", escalate_review: "Stop & escalate for review",
  stop: "Stop automatically", queue_customer_message: "Queue an informational message",
};
const money = (value: number) => new Intl.NumberFormat("en-IN", { style: "currency", currency: "INR" }).format(value / 100);
const refreshError = "Could not refresh this test. Its saved evidence has not been discarded.";

function Evidence({ run }: { run: SimulatorRun }) {
  const decision = run.decision;
  const advice = run.advice;
  return <div className="connected-evidence" aria-live="polite">
    <div className="connected-receipt-title"><p className="eyebrow">{stages[run.stage] ?? run.stage}</p><span className="sandbox-label">NO LIVE MONEY</span></div>
    <h3>{decision ? actionNames[decision.selected_action] ?? decision.selected_action : run.source === "razorpay_test" ? "One test. A traceable story." : "Your decision is on its way."}</h3>
    <p className="receipt-origin">{run.source === "synthetic" ? "Synthetic payment · real cloud analysis" : "Razorpay Test Mode order"} · {money(run.amount_minor)}</p>
    <ol className="connected-timeline">
      <li className="done"><span>01</span><div><b>{run.source === "synthetic" ? "Test event saved" : "Razorpay order"}</b><p>{run.order_id ?? (run.source === "synthetic" ? "Generated locally; this is not a Razorpay webhook." : "Provider confirmation pending.")}</p></div></li>
      <li className={run.webhook_received ? "done" : "waiting"}><span>02</span><div><b>{run.webhook_received ? "Signed webhook received" : run.event_source === "razorpay_api" ? "Failure verified through Razorpay API" : "Webhook evidence"}</b><p>{run.webhook_received ? `${run.webhook_deliveries} authenticated delivery(s). Duplicate delivery does not repeat the decision.` : run.source === "synthetic" ? "Not applicable to a synthetic scenario." : "No signed webhook received yet. API checks are labelled separately."}</p></div></li>
      <li className={decision ? "done" : "waiting"}><span>03</span><div><b>{decision ? `Class ${decision.effective_class} · deterministic safeguards` : "Rulebook & Gatekeeper"}</b><p>{decision ? `${decision.gate_checks.filter(c => c.passed).length}/${decision.gate_checks.length} checks passed. ${decision.triage_rationale}` : "Waiting for a verified failure. No recovery action is running."}</p></div></li>
    </ol>
    <section className={`cloud-card ${advice?.status === "fresh" ? "cloud-ready" : ""}`} aria-label="Ollama Cloud analysis">
      <div className="cloud-heading"><span className="cloud-symbol" aria-hidden="true">✦</span><div><b>Ollama Cloud</b><small>{advice?.model ?? "Cloud-only advisor"} · ADVISORY, NOT ACTION AUTHORITY</small></div></div>
      {advice?.status === "fresh" && advice.result ? <>
        <p className="cloud-explanation">{advice.result.explanation}</p>
        <div className="cloud-note"><b>Operator note</b><p>{advice.result.operator_note}</p></div>
        <div className="cloud-meta"><span>Shadow class {advice.result.suggested_class} · {advice.result.confidence} confidence</span><span>{((advice.elapsed_ms ?? 0)/1000).toFixed(1)}s</span></div>
        <p className="cloud-provenance">Saved cloud generation · {advice.generated_at ? new Date(advice.generated_at).toLocaleString() : ""} · {advice.input_tokens ?? "—"} input / {advice.output_tokens ?? "—"} output tokens</p>
      </> : advice?.status === "unavailable" || advice?.status === "invalid_response" ? <p role="status">AI unavailable. {errors[advice.error_code ?? ""] ?? "The cloud request could not complete."} The deterministic decision is still valid. No local AI or fixture was substituted.</p> : <p>{decision ? "Requesting a fresh explanation from Ollama Cloud…" : "Cloud analysis begins after the deterministic failure decision is saved."}</p>}
    </section>
    {decision ? <div className="connected-audit"><span>{run.ledger_valid ? "✓ Audit chain verified" : "! Audit check failed"}</span><span>{decision.effect_state ? "Recovery intent: dry-run only" : "No recovery effect created"}</span></div> : null}
    {run.error_code ? <p role="alert" className="playground-error">{run.error_code.replaceAll("_", " ")}. No order creation retry is automatic; inspect your Test Mode dashboard.</p> : null}
    <details className="connected-details"><summary>Inspect saved evidence</summary><p>Run: {run.run_id}</p>{run.payment_id ? <p>Payment: {run.payment_id}</p> : null}{decision ? <><p>Decision: {decision.decision_id}</p><code>{decision.decision_hash}</code>{decision.gate_checks.map(check => <p key={check.name}>{check.passed ? "✓" : "×"} {check.name.replaceAll("_", " ")} — {check.explanation}</p>)}</> : null}<p>AI output cannot change amounts, class, timing, or execution. Recovery remains dry-run.</p></details>
  </div>;
}

export default function Simulator() {
  const [state, setState] = useState<SimulatorState | null>(null);
  const [run, setRun] = useState<SimulatorRun | null>(null);
  const [source, setSource] = useState<SimulatorInput["source"]>("synthetic");
  const [scenario, setScenario] = useState<NonNullable<SimulatorInput["scenario"]>>("gateway_timeout");
  const [amount, setAmount] = useState("1250.00");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [attempt, setAttempt] = useState(0);
  const [selectedId, setSelectedId] = useState<string | null>(() => {
    const id = new URLSearchParams(location.search).get("run");
    return id && /^[a-f0-9-]{36}$/i.test(id) ? id : null;
  });
  const pending = useRef<SimulatorInput | null>(null);
  const inFlight = useRef(false);
  const selection = useRef(selectedId);
  selection.current = selectedId;

  useEffect(() => {
    let active = true;
    loadSimulator().then(value => { if (active) { setState(value); setError(""); } }).catch(() => {
      if (active) setError("The connected simulator is unavailable. Check that the local backend is running and configured.");
    });
    return () => { active = false; };
  }, [attempt]);

  useEffect(() => {
    if (!selectedId) return;
    let active = true;
    let fetching = false;
    const refresh = async () => {
      if (fetching) return;
      fetching = true;
      try {
        const value = await loadSimulatorRun(selectedId);
        if (active) {
          setRun(value);
          setError(current => current === refreshError ? "" : current);
        }
      } catch { if (active) setError(refreshError); }
      finally { fetching = false; }
    };
    void refresh();
    const interval = window.setInterval(() => { if (!document.hidden) void refresh(); }, 2000);
    return () => { active = false; window.clearInterval(interval); };
  }, [selectedId]);

  function select(value: SimulatorRun) {
    setRun(value); setSelectedId(value.run_id); setError("");
    history.replaceState(null, "", `?run=${value.run_id}#playground`);
  }

  async function create(event: FormEvent) {
    event.preventDefault();
    if (inFlight.current) return;
    if (!/^\d+(\.\d{1,2})?$/.test(amount)) { setError("Enter a rupee amount with at most two decimal places."); return; }
    const [whole, fraction = ""] = amount.split(".");
    const minor = Number(whole)*100 + Number(fraction.padEnd(2, "0"));
    if (!Number.isSafeInteger(minor) || minor < 100 || minor > 1_000_000) { setError("Use a test amount between ₹1 and ₹10,000."); return; }
    const request = pending.current ?? { run_id: crypto.randomUUID(), source, scenario, amount_minor: minor, method: "card" as const };
    pending.current = request;
    inFlight.current = true; setBusy(true); setError(""); setNotice("");
    try {
      const value = await createSimulatorRun(request);
      select(value); pending.current = null;
      setState(await loadSimulator());
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Could not create the test. Retry safely with the same ID."); }
    finally { inFlight.current = false; setBusy(false); }
  }

  async function checkProvider() {
    if (!run || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    const id = run.run_id;
    try { const value = await syncSimulatorRun(id); if (selection.current === id) select(value); }
    catch (caught) { setError(caught instanceof Error ? caught.message : "Provider check failed."); }
    finally { inFlight.current = false; setBusy(false); }
  }

  async function replay() {
    if (!run || inFlight.current) return;
    inFlight.current = true; setBusy(true); setError("");
    try {
      const value = await createSimulatorRun({ run_id: run.run_id, source: run.source as SimulatorInput["source"], scenario: run.scenario as SimulatorInput["scenario"], amount_minor: run.amount_minor, method: run.method as SimulatorInput["method"] });
      select(value); setNotice("Same run replayed. No new order, generation, or recovery effect was created.");
    } catch (caught) { setError(caught instanceof Error ? caught.message : "Replay failed."); }
    finally { inFlight.current = false; setBusy(false); }
  }

  return <section className="connected" id="playground" aria-labelledby="connected-title">
    <div className="connected-header"><div><p className="eyebrow">The connected recovery lab</p><h2 id="connected-title">Real signals. Clear decisions.</h2><p>Razorpay Test Mode × Ollama Cloud. See the evidence behind every response.</p></div><span className="sandbox-label">TEST ENVIRONMENT</span></div>
    <div className="connection-strip" aria-label="Connection configuration">
      <div><span className={state?.cloud_configured ? "status-dot configured" : "status-dot"} /><b>Ollama Cloud</b><small>{state?.cloud_configured ? `${state.cloud_model} · key configured` : "Not configured"}</small></div>
      <div><span className={state?.razorpay_configured ? "status-dot configured" : "status-dot"} /><b>Razorpay</b><small>{state?.razorpay_configured ? "Test credentials configured" : "Not configured"}</small></div>
      <div><span className={state?.webhook_received || run?.webhook_received ? "status-dot configured" : "status-dot"} /><b>Webhook</b><small>{state?.webhook_received || run?.webhook_received ? "Signed delivery recorded" : "Awaiting first delivery"}</small></div>
    </div>
    {!state ? <div className="connected-unavailable"><p role="status">{error || "Connecting to the local simulator…"}</p><button onClick={() => setAttempt(v => v+1)}>Reconnect simulator</button><p>No canned response or local AI will replace the cloud integration.</p></div> : <div className="connected-grid">
      <div className="connected-controls">
        <div className="lab-tabs" role="group" aria-label="Simulator mode"><button type="button" aria-pressed={source === "synthetic"} onClick={() => { setSource("synthetic"); pending.current = null; }} disabled={busy}>Cloud failure lab</button><button type="button" aria-pressed={source === "razorpay_test"} onClick={() => { setSource("razorpay_test"); pending.current = null; }} disabled={busy}>Razorpay Checkout</button></div>
        <form onSubmit={create}>
          <fieldset disabled={busy}><legend>{source === "synthetic" ? "Choose a failure to investigate" : "Create a genuine Test Mode order"}</legend>
            {source === "synthetic" ? <div className="scenario-options">{state.scenarios.map(option => <label className={`scenario-option ${scenario === option.id ? "chosen" : ""}`} key={option.id}><input type="radio" name="connected-scenario" checked={scenario === option.id} onChange={() => { setScenario(option.id); pending.current = null; }} /><span><b>{option.label}</b><small>{option.description}</small></span></label>)}</div> : <div className="checkout-instructions"><b>Use Razorpay’s test bank page</b><p>Create an order below, open Checkout, and choose a test payment method. Select <strong>Failure</strong> on the mock bank page to send a failed-payment event.</p><p>Use test details only. Razorpay controls the failure reason; this is not the preset scenario generator.</p><a href="https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/?preferred-country=IN" target="_blank" rel="noreferrer">Official test-payment instructions ↗</a></div>}
            <label className="connected-amount">Test amount (INR)<input aria-label="Connected test amount in rupees" inputMode="decimal" value={amount} maxLength={10} onChange={event => { setAmount(event.target.value); pending.current = null; }} /></label>
            <button className="run-button" disabled={state.remaining_runs === 0 || (source === "razorpay_test" && (!state.razorpay_configured || state.remaining_orders === 0))} type="submit">{busy ? "Saving your test…" : pending.current ? "Retry same request safely →" : source === "synthetic" ? "Run with Ollama Cloud →" : "Create Razorpay test order →"}</button>
          </fieldset>
        </form>
        <p className="playground-fineprint">{source === "synthetic" ? "Synthetic event. Fresh cloud call. No Razorpay payment is created." : "Real Razorpay API call using test keys. No real money moves."} Recovery retries, links, and customer messages remain dry-run.</p>
        <details className="webhook-setup"><summary>Connect signed webhook deliveries</summary><p>In Razorpay’s Test Mode dashboard, add a webhook for <code>payment.failed</code>.</p>{state.public_webhook_url ? <code>{state.public_webhook_url}</code> : <p>A public HTTPS webhook address is not configured yet. The dedicated receiver is ready; it needs a tunnel or staging host.</p>}<p>Use the separate webhook secret from your private server settings. Never use the API secret as the webhook secret.</p><p>Until then, Check Razorpay status verifies payments through the API and labels them as API evidence—not webhooks.</p></details>
        {error ? <p role="alert" className="playground-error">{error}</p> : null}
        {notice ? <p role="status" className="connected-notice">{notice}</p> : null}
        {run ? <div className="connected-actions">{run.order_id && run.stage !== "payment_succeeded" ? <><button type="button" disabled={busy} onClick={() => { void openTestCheckout(run, setNotice).catch(caught => setError(caught instanceof Error ? caught.message : "Checkout could not open.")); }}>Open Razorpay test checkout ↗</button><button type="button" disabled={busy} onClick={() => void checkProvider()}>Check Razorpay status</button></> : null}<button type="button" disabled={busy} onClick={() => void replay()}>Replay saved run</button><a href={`/simulator/v1/runs/${run.run_id}/receipt`} download>Download evidence ↓</a></div> : null}
      </div>
      {run ? <Evidence run={run} /> : <div className="connected-empty"><div className="signal-glyph" aria-hidden="true">↗</div><p className="eyebrow">From failure to understanding</p><h3>A real cloud answer.<br />A decision you can inspect.</h3><p>Start with the Cloud failure lab, or create a Razorpay test payment. The timeline will show what actually happened.</p><div className="empty-flow"><span>Event</span><span>Policy</span><span>Cloud advice</span><span>Evidence</span></div></div>}
    </div>}
    {state?.recent.length ? <div className="connected-history"><div><b>Saved investigations</b><small>Opening a result never reruns AI or creates another order.</small></div><div className="investigation-list">{state.recent.map(item => <button key={item.run_id} disabled={busy} onClick={() => select(item)} aria-pressed={selectedId === item.run_id}><span className="history-source">{item.source === "synthetic" ? "CLOUD LAB" : "RAZORPAY TEST"}</span><b>{item.source === "synthetic" ? state.scenarios.find(s => s.id === item.scenario)?.label : item.order_id ?? "Order pending"}</b><small>{money(item.amount_minor)} · {new Date(item.created_at).toLocaleTimeString([], {hour:"2-digit",minute:"2-digit"})}</small></button>)}</div></div> : null}
  </section>;
}
