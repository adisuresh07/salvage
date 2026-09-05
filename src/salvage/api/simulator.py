from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Request, Response

from salvage.api.playground import LOCAL_ORIGINS
from salvage.simulator.service import RunInput, RunOut, Simulator, SimulatorState


def local_only(request: Request, response: Response) -> None:
    response.headers["Cache-Control"] = "no-store"
    host = request.headers.get("host", "").split(":")[0]
    origin = request.headers.get("origin")
    if host not in {"localhost", "127.0.0.1"} or (origin and origin not in LOCAL_ORIGINS):
        raise HTTPException(403, "Use the simulator from the local console")
    if request.headers.get("sec-fetch-site") == "cross-site":
        raise HTTPException(403, "Cross-site simulator requests are disabled")
    if request.method == "POST" and (
        origin not in LOCAL_ORIGINS or request.headers.get("x-salvage-playground") != "1"
    ):
        raise HTTPException(403, "Local simulator authorization required")


def create_simulator_router(simulator: Simulator) -> APIRouter:
    router = APIRouter(
        prefix="/simulator/v1",
        tags=["connected test simulator"],
        dependencies=[Depends(local_only)],
    )

    @router.get("/status", response_model=SimulatorState)
    def state() -> SimulatorState:
        return simulator.state()

    @router.post("/runs", response_model=RunOut)
    def create(run: RunInput) -> RunOut:
        return simulator.create(run)

    @router.get("/runs/{run_id}", response_model=RunOut)
    def detail(run_id: UUID) -> RunOut:
        return simulator.result(str(run_id))

    @router.get("/runs/{run_id}/receipt", response_model=RunOut)
    def receipt(run_id: UUID, response: Response) -> RunOut:
        response.headers["Content-Disposition"] = (
            f'attachment; filename="salvage-connected-{run_id}.json"'
        )
        return simulator.result(str(run_id))

    @router.post("/runs/{run_id}/sync", response_model=RunOut)
    def sync(run_id: UUID) -> RunOut:
        return simulator.sync(str(run_id))

    return router


def create_webhook_router(simulator: Simulator) -> APIRouter:
    router = APIRouter()

    @router.post("/webhooks/razorpay/test", status_code=202, tags=["connected test webhook"])
    async def webhook(request: Request) -> dict[str, bool | str]:
        signature = request.headers.get("x-razorpay-signature", "")
        event_id = request.headers.get("x-razorpay-event-id", "")
        if not signature or not event_id or len(event_id) > 160:
            raise HTTPException(401, "Missing or invalid webhook authentication")
        raw = bytearray()
        async for chunk in request.stream():
            raw.extend(chunk)
            if len(raw) > simulator.settings.max_body_bytes:
                raise HTTPException(413, "Webhook body too large")
        return simulator.webhook(bytes(raw), signature, event_id)

    return router
