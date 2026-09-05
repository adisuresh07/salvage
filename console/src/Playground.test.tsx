import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import demoBundle from "../public/demo-data.json";
import Playground from "./Playground";
import type { PlaygroundRequest } from "./api/client";

const state = {
  scenarios: [
    { id: "gateway_timeout", label: "Gateway timeout", description: "Provider did not respond." },
    { id: "processor_code_z91", label: "Unknown reason", description: "Unmapped code." },
  ],
  recent: [], remaining_runs: 200,
};
let requests: PlaygroundRequest[];

function json(value: unknown, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(value), { status }));
}

function mockFetch(input: string | URL | Request, init?: RequestInit) {
  if (String(input) === "/demo/v1/playground") return json(state);
  const request = JSON.parse(String(init?.body)) as PlaygroundRequest;
  const duplicate = requests.some((previous) => previous.run_id === request.run_id);
  requests.push(request);
  const decision = demoBundle.decisions.items.find((item) => item.reason === request.scenario)!;
  return json({ request, duplicate, decision, ingress_verified: true, ledger_valid: true,
    event_count: 1, decision_count: 1, effect_count: decision.effect_state ? 1 : 0,
    ledger_entry_count: 1, elapsed_ms: 15, safety_mode: "dry_run" });
}

describe("Local recovery playground", () => {
  beforeEach(() => { requests = []; vi.stubGlobal("fetch", vi.fn(mockFetch)); });

  it("submits integer minor units and replays the same event", async () => {
    const user = userEvent.setup();
    render(<Playground />);
    await screen.findByRole("radio", { name: /gateway timeout/i });
    await user.clear(screen.getByLabelText("Test amount in rupees"));
    await user.type(screen.getByLabelText("Test amount in rupees"), "1250.25");
    await user.click(screen.getByRole("button", { name: /run recovery test/i }));
    expect(await screen.findByText("A bounded retry is allowed.")).toBeInTheDocument();
    expect(requests[0].amount_minor).toBe(125025);
    expect(screen.getByRole("link", { name: /download evidence/i })).toHaveAttribute(
      "href", `/demo/v1/runs/${requests[0].run_id}/receipt`,
    );
    await user.click(screen.getByRole("button", { name: "Replay same event" }));
    expect(await screen.findByText("DUPLICATE EVENT · NO EXTRA EFFECT")).toBeInTheDocument();
    expect(requests[1]).toEqual(requests[0]);
    expect(vi.mocked(fetch).mock.calls.some(([, init]) => new Headers(init?.headers).get("X-Salvage-Playground") === "1")).toBe(true);
  });

  it("shows the hard stop and powerless shadow advice for unknown reasons", async () => {
    const user = userEvent.setup(); render(<Playground />);
    await user.click(await screen.findByRole("radio", { name: /unknown reason/i }));
    await user.click(screen.getByRole("button", { name: /run recovery test/i }));
    expect(await screen.findByText("Stop. This needs human review.")).toBeInTheDocument();
    expect(screen.getByText("AI shadow suggested A. Effective class stays D.")).toBeInTheDocument();
    expect(screen.getByText("No retry, payment link, or customer contact was created.")).toBeInTheDocument();
  });

  it("validates amounts before sending a request", async () => {
    const user = userEvent.setup(); render(<Playground />);
    await screen.findByRole("radio", { name: /gateway timeout/i });
    await user.clear(screen.getByLabelText("Test amount in rupees"));
    await user.type(screen.getByLabelText("Test amount in rupees"), "1.001");
    await user.click(screen.getByRole("button", { name: /run recovery test/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("two decimal places");
    expect(requests).toHaveLength(0);
  });

  it("retains the event identity after an uncertain response", async () => {
    const user = userEvent.setup(); let fail = true;
    vi.stubGlobal("fetch", vi.fn((input: string | URL | Request, init?: RequestInit) => {
      if (String(input) === "/demo/v1/runs" && fail) {
        fail = false; requests.push(JSON.parse(String(init?.body)));
        return Promise.reject(new Error("Connection interrupted"));
      }
      return mockFetch(input, init);
    }));
    render(<Playground />);
    await screen.findByRole("radio", { name: /gateway timeout/i });
    await user.click(screen.getByRole("button", { name: /run recovery test/i }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Connection interrupted");
    await user.click(screen.getByRole("button", { name: /retry this test safely/i }));
    await waitFor(() => expect(requests).toHaveLength(2));
    expect(requests[1].run_id).toBe(requests[0].run_id);
  });

  it("does not fake successful tests when the backend is absent", async () => {
    vi.stubGlobal("fetch", vi.fn(() => Promise.reject(new Error("offline"))));
    render(<Playground />);
    expect(await screen.findByRole("status")).toHaveTextContent("need the local Salvage backend");
    expect(screen.queryByRole("button", { name: /run recovery test/i })).not.toBeInTheDocument();
  });
});
