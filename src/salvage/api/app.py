from __future__ import annotations

import json
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager

from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from salvage import __version__
from salvage.api.playground import create_playground_router
from salvage.api.schemas import (
    BatchListOut,
    BatchOut,
    BatchResultOut,
    DecisionListOut,
    DecisionOut,
    HealthOut,
    LedgerOut,
)
from salvage.api.simulator import create_simulator_router, create_webhook_router
from salvage.audit.ledger import verify_ledger
from salvage.config import Settings
from salvage.config import settings as default_settings
from salvage.demo import ensure_demo
from salvage.domain.loading import load_policy, load_reason_map
from salvage.ingress.webhook import project_event, verify_signature
from salvage.persistence.db import connect, schema_current
from salvage.persistence.repository import list_decision_rows, store_event_and_job
from salvage.simulator.service import Simulator

SECURITY_HEADERS = {
    "Content-Security-Policy": (
        "default-src 'self'; connect-src 'self'; img-src 'self' data:; "
        "style-src 'self'; script-src 'self'; object-src 'none'; "
        "base-uri 'none'; frame-ancestors 'none'"
    ),
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
    "Permissions-Policy": "camera=(), microphone=(), geolocation=(), payment=()",
}


def create_app(app_settings: Settings | None = None) -> FastAPI:
    active = app_settings or default_settings
    simulator = Simulator(active) if active.simulator_enabled else None

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        active.assert_safe()
        if active.mode == "demo":
            ensure_demo(active)
        else:
            schema_current(active.database_path)
        if simulator:
            simulator.start()
        try:
            yield
        finally:
            if simulator:
                simulator.close()

    application = FastAPI(
        title="Salvage read-only API",
        version=__version__,
        description="Deterministic payment-recovery evidence and read-only operator views.",
        lifespan=lifespan,
    )
    application.state.settings = active
    application.state.simulator = simulator
    if active.mode == "demo":
        application.include_router(create_playground_router(active))
    if simulator:
        application.include_router(create_simulator_router(simulator))
        application.include_router(create_webhook_router(simulator))

    @application.middleware("http")
    async def secure_headers(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        response = await call_next(request)
        for name, value in SECURITY_HEADERS.items():
            response.headers[name] = value
        if simulator:
            response.headers["Content-Security-Policy"] = (
                "default-src 'self'; connect-src 'self' https://api.razorpay.com; "
                "img-src 'self' data: https://*.razorpay.com; style-src 'self' 'unsafe-inline'; "
                "script-src 'self' https://checkout.razorpay.com; "
                "frame-src https://api.razorpay.com https://checkout.razorpay.com; "
                "object-src 'none'; base-uri 'none'; frame-ancestors 'none'"
            )
        return response

    @application.get("/health/live", response_model=HealthOut, tags=["health"])
    def health_live() -> HealthOut:
        return HealthOut(status="live")

    @application.get("/health/ready", response_model=HealthOut, tags=["health"])
    def health_ready() -> HealthOut:
        try:
            schema_current(active.database_path)
            load_reason_map(active.policy_dir / "reason-map.yaml")
            load_policy(active.policy_dir / "recovery-policy.yaml")
        except Exception as exc:
            raise HTTPException(status_code=503, detail="Readiness checks failed") from exc
        return HealthOut(status="ready", details={"mode": active.mode, "llm": active.llm})

    @application.post("/webhooks/razorpay", status_code=status.HTTP_202_ACCEPTED, tags=["webhooks"])
    async def razorpay_webhook(
        request: Request,
        x_razorpay_signature: str | None = Header(default=None),
        x_razorpay_event_id: str | None = Header(default=None),
    ) -> dict[str, str | bool]:
        if not x_razorpay_signature or not x_razorpay_event_id:
            raise HTTPException(status_code=401, detail="Missing webhook authentication")
        raw = await request.body()
        if len(raw) > active.max_body_bytes:
            raise HTTPException(status_code=413, detail="Webhook body is too large")
        if not verify_signature(raw, x_razorpay_signature, active.webhook_secret):
            raise HTTPException(status_code=401, detail="Invalid webhook signature")
        try:
            projection = project_event(raw, x_razorpay_event_id)
        except (ValueError, json.JSONDecodeError) as exc:
            raise HTTPException(
                status_code=422, detail="Invalid payment.failed projection"
            ) from exc
        inserted = store_event_and_job(active.database_path, projection)
        return {"status": "accepted", "duplicate": not inserted}

    @application.get("/api/v1/decisions", response_model=DecisionListOut, tags=["console"])
    def decisions(limit: int = 100) -> DecisionListOut:
        safe_limit = max(1, min(limit, 250))
        return DecisionListOut(
            items=[
                DecisionOut.model_validate(row)
                for row in list_decision_rows(active.database_path, safe_limit)
            ]
        )

    @application.get(
        "/api/v1/decisions/{decision_id}", response_model=DecisionOut, tags=["console"]
    )
    def decision_detail(decision_id: str) -> DecisionOut:
        match = next(
            (
                row
                for row in list_decision_rows(active.database_path, 250)
                if row["decision_id"] == decision_id
            ),
            None,
        )
        if match is None:
            raise HTTPException(status_code=404, detail="Decision not found")
        return DecisionOut.model_validate(match)

    @application.get("/api/v1/escalations", response_model=DecisionListOut, tags=["console"])
    def escalations() -> DecisionListOut:
        items = [
            DecisionOut.model_validate(row)
            for row in list_decision_rows(active.database_path, 250)
            if row["review_required"]
        ]
        return DecisionListOut(items=items)

    @application.get("/api/v1/batches", response_model=BatchListOut, tags=["console"])
    def batches() -> BatchListOut:
        with connect(active.database_path) as connection:
            rows = connection.execute(
                "SELECT batch_id, seed, scenario_count, batch_digest, created_at "
                "FROM eval_batches ORDER BY created_at DESC"
            ).fetchall()
        return BatchListOut(items=[BatchOut.model_validate(dict(row)) for row in rows])

    @application.get(
        "/api/v1/batches/{batch_id}/results", response_model=BatchResultOut, tags=["console"]
    )
    def batch_results(batch_id: str) -> BatchResultOut:
        with connect(active.database_path) as connection:
            row = connection.execute(
                "SELECT result_json FROM eval_batches WHERE batch_id = ?", (batch_id,)
            ).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Batch not found")
        return BatchResultOut.model_validate_json(row["result_json"])

    @application.get("/api/v1/ledger/status", response_model=LedgerOut, tags=["console"])
    def ledger_status() -> LedgerOut:
        return LedgerOut.model_validate(verify_ledger(active.database_path), from_attributes=True)

    @application.get("/api/v1/meta/versions", tags=["console"])
    def versions() -> dict[str, str]:
        _, map_version, map_fingerprint = load_reason_map(active.policy_dir / "reason-map.yaml")
        policy = load_policy(active.policy_dir / "recovery-policy.yaml")
        return {
            "application": __version__,
            "reason_map": map_version,
            "reason_map_fingerprint": map_fingerprint,
            "policy": policy.version,
            "policy_fingerprint": policy.fingerprint,
            "llm": active.llm,
        }

    if active.console_dist.exists():
        assets = active.console_dist / "assets"
        if assets.exists():
            application.mount("/assets", StaticFiles(directory=assets), name="assets")

        @application.get("/", include_in_schema=False)
        def console_index() -> FileResponse:
            return FileResponse(active.console_dist / "index.html")

        @application.get("/{path:path}", include_in_schema=False)
        def console_fallback(path: str) -> FileResponse:
            if path.split("/", 1)[0] in {"api", "demo", "simulator", "health", "webhooks"}:
                raise HTTPException(status_code=404, detail="Endpoint not found")
            candidate = (active.console_dist / path).resolve()
            if candidate.is_relative_to(active.console_dist.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(active.console_dist / "index.html")

    return application


app = create_app()
