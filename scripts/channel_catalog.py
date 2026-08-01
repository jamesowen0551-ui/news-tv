#!/usr/bin/env python3
"""Load and validate the single source of truth for news channel facts."""

from __future__ import annotations

import json
import re
import tempfile
from dataclasses import dataclass
from pathlib import Path


TVG_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")
ALLOWED_GLOBAL_GROUPS = {"", "Finance", "US News", "World News"}
TOP_LEVEL_FIELDS = {"schema_version", "epg_url", "profiles", "channels"}
CHANNEL_FIELDS = {
    "tvg_id",
    "tvg_name",
    "url",
    "global_group",
    "official_page",
    "delivery_evidence",
}


@dataclass(frozen=True)
class CatalogChannel:
    tvg_id: str
    tvg_name: str
    url: str
    global_group: str
    official_page: str
    delivery_evidence: str


@dataclass(frozen=True)
class Catalog:
    schema_version: int
    epg_url: str
    profiles: dict[str, tuple[str, ...]]
    channels: tuple[CatalogChannel, ...]

    def channel_by_id(self, tvg_id: str) -> CatalogChannel:
        for channel in self.channels:
            if channel.tvg_id == tvg_id:
                return channel
        raise ValueError(f"unknown tvg-id (exact matching only): {tvg_id}")


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


def load_catalog_text(text: str) -> Catalog:
    try:
        document = json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(f"invalid catalog JSON: {error}") from error
    if not isinstance(document, dict):
        raise ValueError("catalog root must be an object")
    _require_exact_fields(document, TOP_LEVEL_FIELDS, "catalog")
    if document["schema_version"] != 1:
        raise ValueError("unsupported catalog schema_version")

    epg_url = _required_text(document["epg_url"], "EPG URL")
    if not epg_url.startswith("https://"):
        raise ValueError("EPG URL must use HTTPS")

    raw_channels = document["channels"]
    if not isinstance(raw_channels, list) or not raw_channels:
        raise ValueError("channels must be a non-empty list")
    channels: list[CatalogChannel] = []
    seen_ids: set[str] = set()
    for index, raw_channel in enumerate(raw_channels):
        if not isinstance(raw_channel, dict):
            raise ValueError(f"channel {index} must be an object")
        _require_exact_fields(raw_channel, CHANNEL_FIELDS, "channel")
        tvg_id = _required_text(raw_channel["tvg_id"], "channel tvg-id")
        if not TVG_ID_PATTERN.fullmatch(tvg_id):
            raise ValueError(f"invalid channel tvg-id: {tvg_id}")
        if tvg_id in seen_ids:
            raise ValueError(f"duplicate tvg-id: {tvg_id}")
        seen_ids.add(tvg_id)

        tvg_name = _required_text(raw_channel["tvg_name"], "channel tvg-name")
        url = _required_text(raw_channel["url"], "channel URL")
        if not url.startswith("https://"):
            raise ValueError(f"channel URL must use HTTPS: {tvg_id}")
        if "?" in url:
            raise ValueError(f"channel URL contains query parameters: {tvg_id}")
        global_group = raw_channel["global_group"]
        if not isinstance(global_group, str) or global_group not in ALLOWED_GLOBAL_GROUPS:
            raise ValueError(f"invalid global group: {tvg_id}")
        official_page = _required_text(
            raw_channel["official_page"], "official page"
        )
        if not official_page.startswith("https://"):
            raise ValueError(f"official page must use HTTPS: {tvg_id}")
        delivery_evidence = _required_text(
            raw_channel["delivery_evidence"], "delivery evidence"
        )
        channels.append(
            CatalogChannel(
                tvg_id=tvg_id,
                tvg_name=tvg_name,
                url=url,
                global_group=global_group,
                official_page=official_page,
                delivery_evidence=delivery_evidence,
            )
        )

    raw_profiles = document["profiles"]
    if not isinstance(raw_profiles, dict):
        raise ValueError("profiles must be an object")
    for required_profile in (
        "global",
        "china_optimized",
        "asia",
        "finance",
        "technology",
    ):
        if required_profile not in raw_profiles:
            raise ValueError(f"missing profile: {required_profile}")
    profiles: dict[str, tuple[str, ...]] = {}
    for name, raw_ids in raw_profiles.items():
        if not isinstance(name, str) or not TVG_ID_PATTERN.fullmatch(name):
            raise ValueError(f"invalid profile name: {name}")
        if not isinstance(raw_ids, list):
            raise ValueError(f"profile must be a list: {name}")
        ids: list[str] = []
        for tvg_id in raw_ids:
            if not isinstance(tvg_id, str):
                raise ValueError(f"profile tvg-id must be text: {name}")
            if tvg_id in ids:
                raise ValueError(f"duplicate profile tvg-id: {name}: {tvg_id}")
            if tvg_id not in seen_ids:
                raise ValueError(f"unknown profile tvg-id: {name}: {tvg_id}")
            ids.append(tvg_id)
        profiles[name] = tuple(ids)

    return Catalog(1, epg_url, profiles, tuple(channels))


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def render_channels(
    catalog: Catalog,
    tvg_ids: tuple[str, ...] | list[str],
    *,
    group_override: str | None = None,
) -> str:
    lines = [f'#EXTM3U x-tvg-url="{_quote(catalog.epg_url)}"']
    for tvg_id in tvg_ids:
        channel = catalog.channel_by_id(tvg_id)
        group = group_override if group_override is not None else channel.global_group
        if not group:
            raise ValueError(f"channel has no group for this playlist: {tvg_id}")
        name = _quote(channel.tvg_name)
        lines.extend(
            [
                f'#EXTINF:-1 tvg-id="{_quote(channel.tvg_id)}" tvg-name="{name}" group-title="{_quote(group)}",{channel.tvg_name}',
                channel.url,
            ]
        )
    return "\n".join(lines) + "\n"


def render_profile(
    catalog: Catalog, profile: str, *, group_override: str | None = None
) -> str:
    try:
        tvg_ids = catalog.profiles[profile]
    except KeyError as error:
        raise ValueError(f"unknown profile: {profile}") from error
    return render_channels(catalog, tvg_ids, group_override=group_override)


def render_global_group(catalog: Catalog, group: str) -> str:
    if group not in ALLOWED_GLOBAL_GROUPS - {""}:
        raise ValueError(f"invalid global group: {group}")
    tvg_ids = tuple(
        tvg_id
        for tvg_id in catalog.profiles["global"]
        if catalog.channel_by_id(tvg_id).global_group == group
    )
    return render_channels(catalog, tvg_ids)


def sync_text(path: Path, text: str, *, check: bool) -> None:
    expected = text.encode("utf-8")
    if check:
        if not path.exists() or path.read_bytes() != expected:
            raise ValueError(f"generated file is stale: {path}")
        return

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, delete=False
        ) as handle:
            handle.write(expected)
            temporary_path = Path(handle.name)
        temporary_path.chmod(0o644)
        temporary_path.replace(path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()
