import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import demo from "../public/demo-data.json";
import Simulator from "./Simulator";
import { createSimulatorRun, loadSimulator, loadSimulatorRun, type SimulatorRun, type SimulatorState } from "./api/client";
import { openTestCheckout } from "./checkout";

vi.mock("./api/client", () => ({ createSimulatorRun: vi.fn(), loadSimulator: vi.fn(), loadSimulatorRun: vi.fn(), syncSimulatorRun: vi.fn() }));

const run: SimulatorRun = {
  run_id: "803ae802-0978-47a3-a515-f10d54dc7a2b", source: "synthetic", scenario: "gateway_timeout",
  amount_minor: 125000, method: "card", stage: "complete", created_at: "2026-08-31T00:00:00Z",
  order_id: null, payment_id: "pay_fixture001", event_source: "synthetic", error_code: null,
  checkout_key_id: null, decision: demo.decisions.items.find(d => d.effective_class === "A")!,
  advice: { status: "fresh", provider: "ollama_cloud", actor: "local_operator", cost_note: "Not reported", model: "gpt-oss:20b", prompt_version: "operator-explanation-v2", generation_id: "803ae802-0978-47a3-a515-f10d54dc7a2b",
    generated_at: "2026-08-31T00:00:00Z", elapsed_ms: 3200, input_tokens: 100, output_tokens: 80,
    result: { suggested_class: "A", confidence: "high", explanation: "A real cloud explanation for this recorded test.", operator_note: "No active retry has been scheduled." } },
  webhook_received: false, webhook_deliveries: 0, ledger_valid: true, safety_mode: "test_only_dry_run_recovery",
};
const state: SimulatorState = {
  cloud_configured: true, cloud_model: "gpt-oss:20b", razorpay_configured: true,
  public_webhook_url: null, webhook_received: false, remaining_runs: 200, remaining_orders: 30,
  scenarios: [{ id: "gateway_timeout", label: "Gateway timeout", description: "Provider timed out." }], recent: [],
};

describe("Connected simulator", () => {
  beforeEach(() => {
    history.replaceState(null, "", "/"); vi.clearAllMocks();
    vi.mocked(loadSimulator).mockResolvedValue(state);
    vi.mocked(loadSimulatorRun).mockResolvedValue(run);
    vi.mocked(createSimulatorRun).mockResolvedValue(run);
  });

  it("submits a cloud test and shows saved provider provenance", async () => {
    const user = userEvent.setup(); render(<Simulator />);
    await user.click(await screen.findByRole("button", { name: "Run with Ollama Cloud →" }));
    expect(await screen.findByText("A real cloud explanation for this recorded test.")).toBeInTheDocument();
    expect(vi.mocked(createSimulatorRun).mock.calls[0][0]).toMatchObject({ source: "synthetic", amount_minor: 125000 });
    expect(screen.getByText(/Saved cloud generation/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /download evidence/i })).toHaveAttribute("href", `/simulator/v1/runs/${run.run_id}/receipt`);
    await user.click(screen.getByRole("button", { name: "Replay saved run" }));
    expect(await screen.findByText(/Same run replayed/)).toBeInTheDocument();
    expect(vi.mocked(createSimulatorRun).mock.calls[1][0].run_id).toBe(run.run_id);
  });

  it("shows cloud failure without a local or canned substitute", async () => {
    const unavailable = { ...run, advice: { ...run.advice!, status: "unavailable" as const, result: null, error_code: "cloud_timeout" } };
    vi.mocked(createSimulatorRun).mockResolvedValue(unavailable); vi.mocked(loadSimulatorRun).mockResolvedValue(unavailable);
    const user = userEvent.setup(); render(<Simulator />);
    await user.click(await screen.findByRole("button", { name: "Run with Ollama Cloud →" }));
    expect(await screen.findByText(/AI unavailable/)).toHaveTextContent("No local AI or fixture was substituted.");
    expect(screen.queryByText("A real cloud explanation for this recorded test.")).not.toBeInTheDocument();
  });

  it("does not label API evidence as a webhook", async () => {
    const apiRun = { ...run, source: "razorpay_test", order_id: "order_fixture001", event_source: "razorpay_api", checkout_key_id: "rzp_test_fixture" };
    vi.mocked(createSimulatorRun).mockResolvedValue(apiRun); vi.mocked(loadSimulatorRun).mockResolvedValue(apiRun);
    const user = userEvent.setup(); render(<Simulator />);
    await user.click(await screen.findByRole("button", { name: "Razorpay Checkout" }));
    await user.click(screen.getByRole("button", { name: "Create Razorpay test order →" }));
    expect(await screen.findByText("Failure verified through Razorpay API")).toBeInTheDocument();
    expect(screen.queryByText("Signed webhook received")).not.toBeInTheDocument();
  });

  it("retains request identity after an uncertain network response", async () => {
    vi.mocked(createSimulatorRun).mockRejectedValueOnce(new Error("Request timed out"));
    const user = userEvent.setup(); render(<Simulator />);
    await user.click(await screen.findByRole("button", { name: "Run with Ollama Cloud →" }));
    await user.click(await screen.findByRole("button", { name: "Retry same request safely →" }));
    expect(vi.mocked(createSimulatorRun).mock.calls[1][0]).toEqual(vi.mocked(createSimulatorRun).mock.calls[0][0]);
  });

  it("clears a transient refresh warning when the backend reconnects", async () => {
    vi.mocked(loadSimulatorRun).mockRejectedValueOnce(new Error("Backend restarting"));
    const user = userEvent.setup(); render(<Simulator />);
    await user.click(await screen.findByRole("button", { name: "Run with Ollama Cloud →" }));
    expect(await screen.findByText(/Could not refresh this test/)).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText(/Could not refresh this test/)).not.toBeInTheDocument(), { timeout: 3500 });
    expect(screen.getByText("A real cloud explanation for this recorded test.")).toBeInTheDocument();
  });

  it("refuses live credentials before loading external Checkout", async () => {
    await expect(openTestCheckout({ ...run, order_id: "order_fixture001", checkout_key_id: "rzp_live_forbidden" }, vi.fn())).rejects.toThrow("Test Mode order");
    expect(document.querySelector('script[src*="checkout.razorpay.com"]')).toBeNull();
  });
});
