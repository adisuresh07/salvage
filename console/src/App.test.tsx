import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import demoBundle from "../public/demo-data.json";
import App from "./App";


function jsonResponse(value: object) {
  return Promise.resolve(new Response(JSON.stringify(value), { status: 200 }));
}


describe("Salvage operator console", () => {
  beforeEach(() => {
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        const url = String(input);
        if (url === "/demo-data.json") return jsonResponse(demoBundle);
        return Promise.reject(new Error("API unavailable in portable demo test"));
      }),
    );
  });

  it("shows the honest evaluation and hard-stop evidence", async () => {
    render(<App />);
    expect(await screen.findByRole("heading", { name: /good recovery knows/i })).toBeInTheDocument();
    const salvage = demoBundle.result.policies.find((policy) => policy.policy === "salvage")!;
    expect(screen.getAllByText(`${salvage.recovery_rate}%`).length).toBeGreaterThanOrEqual(2);
    expect(screen.getByText(/simulated: batch volume/i)).toBeInTheDocument();
    expect(screen.getByText("HARD STOP PROVEN")).toBeInTheDocument();
    expect(within(screen.getByLabelText("Sensitivity sweep")).getByText("upper")).toBeInTheDocument();
  });

  it("labels model advice as a powerless shadow annotation", async () => {
    const user = userEvent.setup();
    render(<App />);
    const advisoryDecision = await screen.findByRole("button", { name: "Inspect pay_SALVAGE007" });
    await user.click(advisoryDecision);
    expect(advisoryDecision.closest("tr")).toHaveClass("selected-row");
    await waitFor(() => expect(screen.getByText("RECORDED FIXTURE · NO AUTHORITY")).toBeInTheDocument());
    expect(screen.getByText("Effective class remains D")).toBeInTheDocument();
    expect(screen.getByText(/no retry and no customer contact created/i)).toBeInTheDocument();
  });

  it("degrades gracefully when a rolling backend still serves an older evaluation", async () => {
    const legacyBundle = JSON.parse(JSON.stringify(demoBundle));
    delete legacyBundle.result.sensitivity;
    vi.stubGlobal(
      "fetch",
      vi.fn((input: string | URL | Request) => {
        if (String(input) === "/demo-data.json") return jsonResponse(legacyBundle);
        return Promise.reject(new Error("API unavailable in compatibility test"));
      }),
    );
    render(<App />);
    expect(await screen.findByRole("heading", { name: /good recovery knows/i })).toBeInTheDocument();
    expect(screen.queryByLabelText("Sensitivity sweep")).not.toBeInTheDocument();
  });

  it("filters to stopped decisions without a mutation request", async () => {
    const user = userEvent.setup();
    render(<App />);
    await screen.findByRole("heading", { name: /every failure gets/i });
    await user.click(screen.getByRole("button", { name: "Stopped" }));
    await waitFor(() => expect(screen.getAllByText("Review required").length).toBeGreaterThan(0));
    expect(screen.queryByText("Dry-run recorded")).not.toBeInTheDocument();
    const fetchMock = vi.mocked(fetch);
    expect(fetchMock.mock.calls.every(([, init]) => !init?.method || init.method === "GET")).toBe(true);
  });
});
