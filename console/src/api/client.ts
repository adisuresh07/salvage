import type { components } from "./schema";

export type Decision = components["schemas"]["DecisionOut"];
export type DecisionList = components["schemas"]["DecisionListOut"];
export type BatchList = components["schemas"]["BatchListOut"];
export type BatchResult = components["schemas"]["BatchResultOut"];
export type Ledger = components["schemas"]["LedgerOut"];
export type PlaygroundRequest = components["schemas"]["PlaygroundInput"];
export type PlaygroundReceipt = components["schemas"]["PlaygroundReceipt"];
export type PlaygroundState = components["schemas"]["PlaygroundState"];
export type SimulatorState = components["schemas"]["SimulatorState"];
export type SimulatorRun = components["schemas"]["RunOut"];
export type SimulatorInput = components["schemas"]["RunInput"];

export function loadSimulator(): Promise<SimulatorState> {
  return getJson<SimulatorState>("/simulator/v1/status");
}

export function loadSimulatorRun(id: string): Promise<SimulatorRun> {
  return getJson<SimulatorRun>(`/simulator/v1/runs/${encodeURIComponent(id)}`);
}

async function simulatorPost(path: string, body?: SimulatorInput): Promise<SimulatorRun> {
  const response = await fetch(`/simulator/v1/${path}`, {
    method: "POST", cache: "no-store",
    headers: { "Content-Type": "application/json", "X-Salvage-Playground": "1" },
    body: body ? JSON.stringify(body) : undefined, signal: AbortSignal.timeout(25_000),
  });
  if (!response.ok) {
    const data = await response.json().catch(() => null);
    throw new Error(typeof data?.detail === "string" ? data.detail : "The simulator request failed. Your saved test can be reopened safely.");
  }
  return response.json() as Promise<SimulatorRun>;
}

export const createSimulatorRun = (body: SimulatorInput) => simulatorPost("runs", body);
export const syncSimulatorRun = (id: string) => simulatorPost(`runs/${encodeURIComponent(id)}/sync`);

export function loadPlayground(): Promise<PlaygroundState> {
  return getJson<PlaygroundState>("/demo/v1/playground");
}

export async function runPlayground(request: PlaygroundRequest): Promise<PlaygroundReceipt> {
  const response = await fetch("/demo/v1/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-Salvage-Playground": "1" },
    body: JSON.stringify(request),
    signal: AbortSignal.timeout(15_000),
  });
  if (!response.ok) {
    const error = await response.json().catch(() => null);
    throw new Error(typeof error?.detail === "string" ? error.detail : "The test could not finish. Retry the same event safely.");
  }
  return response.json() as Promise<PlaygroundReceipt>;
}

export interface ConsoleBundle {
  decisions: DecisionList;
  batches: BatchList;
  result: BatchResult;
  ledger: Ledger;
  source: "live_api" | "static_demo";
}

async function getJson<T>(url: string): Promise<T> {
  const response = await fetch(url, { cache: "no-store", headers: { Accept: "application/json" } });
  if (!response.ok) throw new Error(`Request failed with status ${response.status}`);
  return (await response.json()) as T;
}

export async function loadConsoleBundle(): Promise<ConsoleBundle> {
  try {
    const [decisions, batches, ledger] = await Promise.all([
      getJson<DecisionList>("/api/v1/decisions"),
      getJson<BatchList>("/api/v1/batches"),
      getJson<Ledger>("/api/v1/ledger/status"),
    ]);
    const batch = batches.items[0];
    if (!batch) throw new Error("No evaluation batch is available");
    const result = await getJson<BatchResult>(`/api/v1/batches/${encodeURIComponent(batch.batch_id)}/results`);
    return { decisions, batches, ledger, result, source: "live_api" };
  } catch {
    return getJson<ConsoleBundle>("/demo-data.json");
  }
}
