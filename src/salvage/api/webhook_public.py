"""Dedicated tunnel target. Exposes no UI, secrets, simulator controls, or read API."""

from fastapi import FastAPI

from salvage.api.simulator import create_webhook_router
from salvage.config import settings
from salvage.persistence.db import migrate
from salvage.simulator.service import Simulator

settings.assert_safe()
if not settings.simulator_enabled:
    raise RuntimeError("Enable the connected simulator before starting its ingress")
migrate(settings.simulator_database_path)
app = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
app.include_router(create_webhook_router(Simulator(settings)))
