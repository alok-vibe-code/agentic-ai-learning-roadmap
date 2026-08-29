"""Load and validate the framework comparison dataset."""

from __future__ import annotations

import json
from pathlib import Path

from models import FrameworkProfile


DEFAULT_DATA_PATH = Path(__file__).resolve().parent / "data" / "frameworks.json"


def load_profiles(path: str | Path | None = None) -> list[FrameworkProfile]:
    source = Path(path) if path else DEFAULT_DATA_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))

    if not isinstance(payload, list) or not payload:
        raise ValueError("Framework data must be a non-empty JSON list.")

    profiles = [FrameworkProfile.from_dict(item) for item in payload]
    ids = [profile.id for profile in profiles]

    if len(ids) != len(set(ids)):
        raise ValueError("Framework IDs must be unique.")

    for profile in profiles:
        if not profile.docs_url.startswith("https://"):
            raise ValueError(
                f"{profile.id} must use an HTTPS documentation URL."
            )
        if not profile.verified_date:
            raise ValueError(
                f"{profile.id} is missing verified_date."
            )

    return profiles


def get_profile(
    framework_id: str,
    profiles: list[FrameworkProfile] | None = None,
) -> FrameworkProfile:
    available = profiles or load_profiles()
    for profile in available:
        if profile.id == framework_id:
            return profile
    raise KeyError(f"Unknown framework: {framework_id}")
