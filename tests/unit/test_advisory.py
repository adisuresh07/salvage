from __future__ import annotations

from salvage.advisory.cache import advisory_cache_key, get_shadow_suggestion
from salvage.config import ROOT
from salvage.domain.models import ActionClass

CACHE = ROOT / "fixtures" / "advisory-cache" / "suggestions.json"


def test_cache_only_suggestion_is_locally_validated() -> None:
    suggestion = get_shadow_suggestion("processor_code_z91", "cache-only", CACHE)
    assert suggestion is not None
    assert suggestion.suggested_class is ActionClass.A
    assert suggestion.confidence == "low"
    assert len(suggestion.cache_key) == 64


def test_off_mode_never_reads_advice() -> None:
    assert get_shadow_suggestion("processor_code_z91", "off", CACHE) is None


def test_cache_key_covers_semantic_input_and_versions() -> None:
    base = advisory_cache_key(
        reason="processor_code_z91",
        schema_version="1",
        prompt_version="v1",
        provider="fixture",
        model="cache-only",
    )
    changed = advisory_cache_key(
        reason="another_reason",
        schema_version="1",
        prompt_version="v1",
        provider="fixture",
        model="cache-only",
    )
    assert base != changed
