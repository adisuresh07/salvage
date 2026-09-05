import { useEffect, useMemo, useState } from "react";
import { loadConsoleBundle, type ConsoleBundle } from "./api/client";
import Simulator from "./Simulator";

const actionLabels: Record<string, string> = {
  schedule_retry: "Schedule bounded retry",
  schedule_later_retry: "Wait, then retry",
  create_payment_link: "Create a fresh payment path",
  queue_customer_message: "Queue one message",
  escalate_review: "Stop & escalate",
  stop: "Stop automatically",
};

const policyLabels: Record<string, string> = {
  salvage: "Salvage",
  retry_all_3x: "Retry everything",
  never_retry: "Never retry",
};

function DotIcon({ label }: { label: string }) {
  return <span className="dot-icon" aria-hidden="true">{label}</span>;
}

function money(minorUnits: number, compact = false) {
  const rupees = minorUnits / 100;
  if (compact && rupees >= 100_000) return `₹${(rupees / 100_000).toFixed(2)}L`;
  return new Intl.NumberFormat("en-IN", {
    style: "currency",
    currency: "INR",
    maximumFractionDigits: 0,
  }).format(rupees);
}

function shortHash(value: string | null | undefined) {
  if (!value) return "not available";
  return `${value.slice(0, 6)}…${value.slice(-4)}`;
}

function formatAction(action: string) {
  return actionLabels[action] ?? action.replaceAll("_", " ");
}

function LoadingScreen() {
  return (
    <div className="loading-screen" role="status">
      <span className="brand-mark">S</span>
      <div><b>Reading the decision ledger</b><p>Loading deterministic evidence…</p></div>
    </div>
  );
}

export default function App() {
  const [bundle, setBundle] = useState<ConsoleBundle | null>(null);
  const [loadError, setLoadError] = useState(false);
  const [filter, setFilter] = useState<"all" | "acting" | "stopped">("all");
  const [selectedId, setSelectedId] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    loadConsoleBundle()
      .then((data) => {
        if (!active) return;
        setBundle(data);
        const hardStop = data.decisions.items.find((item) => item.effective_class === "D");
        setSelectedId(hardStop?.decision_id ?? data.decisions.items[0]?.decision_id ?? null);
      })
      .catch(() => active && setLoadError(true));
    return () => { active = false; };
  }, []);

  const filtered = useMemo(() => {
    if (!bundle) return [];
    if (filter === "acting") return bundle.decisions.items.filter((item) => item.effect_state);
    if (filter === "stopped") return bundle.decisions.items.filter((item) => item.review_required || !item.effect_state);
    return bundle.decisions.items;
  }, [bundle, filter]);

  if (loadError) {
    return <div className="error-screen" role="alert"><b>The evidence bundle could not be loaded.</b><button onClick={() => location.reload()}>Try again</button></div>;
  }
  if (!bundle) return <LoadingScreen />;

  const salvage = bundle.result.policies.find((policy) => policy.policy === "salvage")!;
  const retryAll = bundle.result.policies.find((policy) => policy.policy === "retry_all_3x")!;
  const selected = bundle.decisions.items.find((item) => item.decision_id === selectedId) ?? bundle.decisions.items[0];
  const recoveryDelta = salvage.recovery_rate - retryAll.recovery_rate;
  const wasteAvoided = retryAll.wasted_attempts
    ? Math.round((1 - salvage.wasted_attempts / retryAll.wasted_attempts) * 100)
    : 0;
  const passedChecks = selected?.gate_checks.filter((check) => check.passed).length ?? 0;
  const maximumRecovery = Math.max(...bundle.result.policies.map((policy) => policy.recovery_rate), 1);
  const sensitivity = (bundle.result.sensitivity ?? []).map((item) => ({
    label: item.label,
    salvage: item.policies.find((policy) => policy.policy === "salvage")!,
  }));

  return (
    <div className="shell">
      <aside className="sidebar">
        <a className="brand" href="#top" aria-label="Salvage home"><span className="brand-mark">S</span><span>SALVAGE</span></a>
        <nav aria-label="Primary navigation">
          <a className="nav-link active" href="#playground"><DotIcon label="↗" />Try a failure</a>
          <a className="nav-link" href="#overview"><DotIcon label="01" />Overview</a>
          <a className="nav-link" href="#decisions"><DotIcon label="02" />Decisions<span className="nav-count">{bundle.decisions.items.length}</span></a>
          <a className="nav-link" href="#evaluation"><DotIcon label="03" />Evaluation</a>
          <a className="nav-link" href="#ledger"><DotIcon label="04" />Audit ledger</a>
        </nav>
        <div className="sidebar-foot">
          <div className="system-state"><span className="pulse" />{bundle.ledger.valid ? "Decision ledger verified" : "Ledger check failed"}</div>
          <p>{bundle.source === "live_api" ? "Local deterministic pipeline" : "Portable static evidence"}</p>
          <a href="https://github.com/rajpaladitiya/salvage">View source ↗</a>
        </div>
      </aside>

      <main id="top">
        <header className="topbar">
          <div><p className="eyebrow">Recovery command center</p><h1>Good recovery knows<br />when to <em>stop.</em></h1></div>
          <div className="top-actions">
            <div className="mode-chip"><span />{bundle.source === "live_api" ? "LOCAL PIPELINE" : "STATIC DEMO"}</div>
            <a className="icon-button" href="#disclosure" aria-label="Read evaluation disclosure">?</a>
            <div className="avatar" aria-label="Merchant operator">AR</div>
          </div>
        </header>

        <Simulator />

        <section className="metrics" id="overview" aria-label="Evaluation highlights">
          <article className="metric-card feature-card">
            <p className="metric-label">Synthetic recovery rate <span>ⓘ</span></p>
            <div className="metric-row"><strong>{salvage.recovery_rate.toFixed(1)}%</strong><span className="trend">↑ {recoveryDelta.toFixed(1)} pts</span></div>
            <p>vs. blind retries on the same seeded batch</p>
            <div className="sparkline" aria-hidden="true"><i /><i /><i /><i /><i /><i /><i /></div>
          </article>
          <article className="metric-card">
            <p className="metric-label">Wasted attempts avoided</p><strong>{wasteAvoided}%</strong>
            <p>{(retryAll.wasted_attempts - salvage.wasted_attempts).toLocaleString("en-IN")} attempts never made</p>
            <div className="mini-rule"><span style={{ width: `${wasteAvoided}%` }} /></div>
          </article>
          <article className="metric-card safe-card">
            <p className="metric-label">Salvage Class D violations</p><strong>{salvage.class_d_violations}</strong>
            <p>No retry. No contact. By design.</p><span className="safety-stamp">HARD STOP PROVEN</span>
          </article>
          <article className="metric-card">
            <p className="metric-label">Decision replay</p><strong className="hash-score">{bundle.ledger.valid ? "100%" : "FAILED"}</strong>
            <p>{bundle.ledger.entry_count} entries in a verified chain</p><code>{shortHash(bundle.ledger.final_hash)}</code>
          </article>
        </section>

        <section className="content-grid">
          <article className="panel performance" id="evaluation">
            <div className="panel-head"><div><p className="eyebrow">Same batch. Different policy.</p><h2>Recovery efficiency</h2></div><span className="batch-tag">n={bundle.result.scenario_count} · seed {bundle.result.seed}</span></div>
            <div className="policy-list">
              {bundle.result.policies.slice().reverse().map((policy) => (
                <div className="policy" key={policy.policy}>
                  <div className="policy-meta"><strong>{policyLabels[policy.policy] ?? policy.policy}</strong><span>{money(policy.recovered_minor_units, true)} recovered</span></div>
                  <div className="bar-track" aria-label={`${policy.recovery_rate}% synthetic recovery rate`}><span className={policy.policy === "salvage" ? "mint" : policy.policy === "retry_all_3x" ? "amber" : "slate"} style={{ width: `${Math.max((policy.recovery_rate / maximumRecovery) * 100, 2)}%` }} /></div>
                  <b>{policy.recovery_rate}%</b>
                </div>
              ))}
            </div>
            <div className="disclosure" id="disclosure"><b>What’s real?</b> {bundle.result.real_vs_simulated}</div>
            {sensitivity.length > 0 ? <div className="sensitivity-strip" aria-label="Sensitivity sweep">
              <div><span>Assumption sweep</span><b>±{bundle.result.assumptions.sensitivity_range_percent}%</b></div>
              {sensitivity.map((item) => <div key={item.label}><span>{item.label}</span><b>{item.salvage.recovery_rate}%</b></div>)}
            </div> : null}
          </article>

          {selected && <article className="panel chain-panel" id="ledger">
            <div className="panel-head"><div><p className="eyebrow">Selected decision</p><h2>{selected.review_required ? "Why Salvage stopped" : "Why Salvage acted"}</h2></div><span className={`class-badge class-${selected.effective_class}`}>{selected.effective_class}</span></div>
            <div className="reason-title"><span>{selected.reason}</span><small>{selected.payment_id}</small></div>
            {selected.advisory_class ? <div className="advisory-note">
              <span>RECORDED FIXTURE · NO AUTHORITY</span>
              <p>Suggested Class {selected.advisory_class} ({selected.advisory_confidence} confidence): {selected.advisory_rationale}</p>
              <b>Effective class remains {selected.effective_class}</b>
            </div> : null}
            <ol className="decision-chain">
              <li><span className="chain-node">1</span><div><b>Triage</b><p>{selected.triage_rationale}</p></div><strong>{selected.known_reason ? "KNOWN" : "UNKNOWN"}</strong></li>
              <li><span className="chain-node">2</span><div><b>Rulebook</b><p>Allowed: {selected.allowed_actions.map(formatAction).join(" · ")}</p></div><strong>LOCKED</strong></li>
              <li><span className="chain-node">3</span><div><b>Gatekeeper</b><p>{passedChecks} of {selected.gate_checks.length} deterministic checks passed.</p></div><strong>{passedChecks === selected.gate_checks.length ? "PASS" : "BLOCK"}</strong></li>
              <li><span className={`chain-node ${selected.review_required ? "stop" : ""}`}>{selected.review_required ? "×" : "✓"}</span><div><b>Effect</b><p>{selected.effect_state ? `${formatAction(selected.effect_action ?? selected.selected_action)} · ${selected.effect_state}` : "No retry and no customer contact created."}</p></div><strong className={selected.review_required ? "stopped" : ""}>{selected.review_required ? "STOPPED" : "DRY RUN"}</strong></li>
            </ol>
            <div className="ledger-proof"><span>✓</span><div><b>Decision hash recorded</b><code>{shortHash(selected.decision_hash)}</code></div></div>
            <details className="gate-details">
              <summary>Inspect all {selected.gate_checks.length} Gatekeeper checks</summary>
              <ul>{selected.gate_checks.map((check) => <li key={check.name}><span>{check.passed ? "✓" : "×"}</span><div><b>{check.name.replaceAll("_", " ")}</b><p>{check.explanation}</p></div></li>)}</ul>
            </details>
          </article>}
        </section>

        <section className="panel decision-table" id="decisions">
          <div className="panel-head">
            <div><p className="eyebrow">Recent activity</p><h2>Every failure gets a reasoned response</h2></div>
            <div className="filters" aria-label="Filter decisions">
              {(["all", "acting", "stopped"] as const).map((value) => <button key={value} className={`filter ${filter === value ? "active" : ""}`} aria-pressed={filter === value} onClick={() => setFilter(value)}>{value[0].toUpperCase() + value.slice(1)}</button>)}
            </div>
          </div>
          <div className="table-wrap">
            <table>
              <thead><tr><th>Effective class</th><th>Payment</th><th>Failure reason</th><th>Amount</th><th>Deterministic action</th><th>Status</th></tr></thead>
              <tbody>{filtered.map((decision) => (
                <tr key={decision.decision_id} className={selectedId === decision.decision_id ? "selected-row" : ""}>
                  <td><span className={`class-badge class-${decision.effective_class}`}>{decision.effective_class}</span></td>
                  <td><button className="row-select" onClick={() => setSelectedId(decision.decision_id)} aria-label={`Inspect ${decision.payment_id}`}>{decision.payment_id}</button></td>
                  <td>{decision.reason}</td><td>{money(decision.amount_minor)}</td><td><strong>{formatAction(decision.selected_action)}</strong></td>
                  <td><span className={`status ${decision.review_required ? "stopped" : ""}`}>{decision.review_required ? "Review required" : decision.effect_state ? "Dry-run recorded" : "Stopped safely"}</span></td>
                </tr>
              ))}</tbody>
            </table>
          </div>
        </section>
        <footer><span>Salvage / Buildathon prototype</span><span>{bundle.result.map_coverage_rate}% deterministic map coverage · {bundle.result.fallback_rate}% failed closed</span></footer>
      </main>
    </div>
  );
}
