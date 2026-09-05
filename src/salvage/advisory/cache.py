from __future__ import annotations

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from salvage.domain.loading import fingerprint
from salvage.domain.models import ActionClass


class SuggestionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suggested_class: ActionClass
    confidence: Literal["low", "medium", "high"]
    rationale: str = Field(min_length=1, max_length=240)


class ShadowSuggestion(SuggestionPayload):
    provider: str
    model: str
    prompt_version: str
    cache_key: str


class CacheFile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: str
    provider: str
    model: str
    prompt_version: str
    entries: dict[str, SuggestionPayload]


def advisory_cache_key(
    *, reason: str, schema_version: str, prompt_version: str, provider: str, model: str
) -> str:
    return fingerprint(
        {
            "task": "suggest_class",
            "schema_version": schema_version,
            "prompt_version": prompt_version,
            "semantic_input": {"reason": reason},
            "provider": provider,
            "model": model,
        }
    )


def get_shadow_suggestion(reason: str, mode: str, cache_path: Path) -> ShadowSuggestion | None:
    if mode != "cache-only" or not cache_path.exists():
        return None
    cache = CacheFile.model_validate_json(cache_path.read_text(encoding="utf-8"))
    payload = cache.entries.get(reason)
    if payload is None:
        return None
    return ShadowSuggestion(
        **payload.model_dump(),
        provider=cache.provider,
        model=cache.model,
        prompt_version=cache.prompt_version,
        cache_key=advisory_cache_key(
            reason=reason,
            schema_version=cache.schema_version,
            prompt_version=cache.prompt_version,
            provider=cache.provider,
            model=cache.model,
        ),
    )
