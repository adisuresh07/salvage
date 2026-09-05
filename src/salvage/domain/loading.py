from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import yaml

from salvage.domain.models import ActionClass, ActionType, ClassPolicy, RecoveryPolicy


def canonical_json(value: object) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def fingerprint(value: object) -> str:
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def load_yaml(path: Path) -> dict[str, Any]:
    parsed = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(parsed, dict):
        raise ValueError(f"{path.name} must contain a mapping")
    return parsed


def load_reason_map(path: Path) -> tuple[dict[str, dict[str, str]], str, str]:
    data = load_yaml(path)
    raw_reasons = data.get("reasons")
    if not isinstance(raw_reasons, dict) or not raw_reasons:
        raise ValueError("Reason map must contain at least one reason")
    reasons: dict[str, dict[str, str]] = {}
    for reason, entry in raw_reasons.items():
        if not isinstance(reason, str) or not isinstance(entry, dict):
            raise ValueError("Reason map entries must be mappings")
        action_class = ActionClass(str(entry.get("class")))
        review_state = str(entry.get("review_state", ""))
        if review_state != "approved":
            continue
        reasons[reason] = {
            "class": action_class.value,
            "rationale": str(entry.get("rationale", "")),
            "source_reference": str(entry.get("source_reference", "")),
        }
    normalized = {"version": str(data.get("version")), "reasons": reasons}
    return reasons, str(data.get("version")), fingerprint(normalized)


def load_policy(path: Path) -> RecoveryPolicy:
    data = load_yaml(path)
    raw_classes = data.get("classes")
    if not isinstance(raw_classes, dict):
        raise ValueError("Recovery policy must define action classes")
    classes: dict[ActionClass, ClassPolicy] = {}
    for class_name in ActionClass:
        raw = raw_classes.get(class_name.value)
        if not isinstance(raw, dict):
            raise ValueError(f"Missing Class {class_name.value} policy")
        classes[class_name] = ClassPolicy(
            attempt_cap=int(raw["attempt_cap"]),
            cooldown_seconds=int(raw["cooldown_seconds"]),
            contact_cap=int(raw["contact_cap"]),
        )
    raw_global = data.get("global", {})
    if not isinstance(raw_global, dict):
        raise ValueError("Policy global section must be a mapping")
    capabilities = frozenset(
        ActionType(str(action)) for action in raw_global.get("adapter_capabilities", [])
    )
    normalized = {
        "version": str(data.get("version")),
        "classes": raw_classes,
        "global": raw_global,
    }
    return RecoveryPolicy(
        version=str(data.get("version")),
        fingerprint=fingerprint(normalized),
        classes=classes,
        customer_contact_window_cap=int(raw_global["customer_contact_window_cap"]),
        adapter_capabilities=capabilities,
    )
