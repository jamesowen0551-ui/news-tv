#!/usr/bin/env python3
"""Load and validate unpublished candidate channel records."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from urllib.parse import urlsplit

if __package__:
    from .channel_catalog import Catalog
else:
    from channel_catalog import Catalog


ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
POOL_FIELDS = {"schema_version", "candidates"}
CANDIDATE_FIELDS = {
    "id",
    "name",
    "country",
    "category",
    "official_url",
    "stream_url",
    "source_notes",
    "status",
}
ALLOWED_STATUSES = {"candidate", "testing", "approved", "rejected"}


@dataclass(frozen=True)
class CandidateChannel:
    id: str
    name: str
    country: str
    category: str
    official_url: str
    stream_url: str
    source_notes: str
    status: str


@dataclass(frozen=True)
class CandidatePool:
    schema_version: int
    candidates: tuple[CandidateChannel, ...]

    def candidate_by_id(self, candidate_id: str) -> CandidateChannel:
        for candidate in self.candidates:
            if candidate.id == candidate_id:
                return candidate
        raise ValueError(
            f"unknown candidate id (exact matching only): {candidate_id}"
        )

    def approved_candidates(self) -> tuple[CandidateChannel, ...]:
        return tuple(
            candidate
            for candidate in self.candidates
            if candidate.status == "approved"
        )


def _require_exact_fields(
    value: dict[str, object], expected: set[str], label: str
) -> None:
    missing = expected - value.keys()
    extra = value.keys() - expected
    if missing:
        raise ValueError(f"missing {label} field: {sorted(missing)[0]}")
    if extra:
        raise ValueError(f"unexpected {label} field: {sorted(extra)[0]}")


def _required_text(value: object, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"missing {label}")
    return value


def _https_url(value: object, label: str, *, stream: bool = False) -> str:
    url = _required_text(value, label)
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.netloc:
        raise ValueError(f"{label} must use HTTPS")
    if parsed.username or parsed.password:
        raise ValueError(f"{label} must not contain credentials")
    if stream and parsed.query:
        raise ValueError(f"{label} contains query parameters")
    if stream and parsed.fragment:
        raise ValueError(f"{label} contains fragment")
    return url


def load_candidate_pool_text(text: str, catalog: Catalog) -> CandidatePool:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid candidate pool JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("candidate pool root must be an object")
    _require_exact_fields(document, POOL_FIELDS, "candidate pool")
    if document["schema_version"] != 1:
        raise ValueError("unsupported candidate pool schema_version")

    raw_candidates = document["candidates"]
    if not isinstance(raw_candidates, list):
        raise ValueError("candidates must be a list")

    catalog_ids = {channel.tvg_id for channel in catalog.channels}
    seen_ids: set[str] = set()
    candidates: list[CandidateChannel] = []
    for index, raw_candidate in enumerate(raw_candidates):
        if not isinstance(raw_candidate, dict):
            raise ValueError(f"candidate {index} must be an object")
        _require_exact_fields(raw_candidate, CANDIDATE_FIELDS, "candidate")

        candidate_id = _required_text(raw_candidate["id"], "candidate id")
        if not ID_PATTERN.fullmatch(candidate_id):
            raise ValueError(f"invalid candidate id: {candidate_id}")
        if candidate_id in seen_ids:
            raise ValueError(f"duplicate candidate id: {candidate_id}")
        if candidate_id in catalog_ids:
            raise ValueError(f"candidate id collides with catalog: {candidate_id}")
        seen_ids.add(candidate_id)

        status = _required_text(raw_candidate["status"], "candidate status")
        if status not in ALLOWED_STATUSES:
            raise ValueError(f"invalid candidate status: {status}")

        candidates.append(
            CandidateChannel(
                id=candidate_id,
                name=_required_text(raw_candidate["name"], "candidate name"),
                country=_required_text(
                    raw_candidate["country"], "candidate country"
                ),
                category=_required_text(
                    raw_candidate["category"], "candidate category"
                ),
                official_url=_https_url(
                    raw_candidate["official_url"], "official URL"
                ),
                stream_url=_https_url(
                    raw_candidate["stream_url"], "stream URL", stream=True
                ),
                source_notes=_required_text(
                    raw_candidate["source_notes"], "candidate source notes"
                ),
                status=status,
            )
        )

    return CandidatePool(1, tuple(candidates))
