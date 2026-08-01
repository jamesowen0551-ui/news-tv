#!/usr/bin/env python3
"""Validate IPTV HLS streams and produce a Markdown health report."""

from __future__ import annotations

import re
import shlex
from dataclasses import dataclass
from urllib.parse import urljoin


@dataclass(frozen=True)
class Channel:
    name: str
    url: str
    group: str = ""
    logo: str = ""
    tvg_id: str = ""
    source: str = ""


@dataclass(frozen=True)
class Variant:
    url: str
    bandwidth: int | None = None
    average_bandwidth: int | None = None
    resolution: str = ""


def _reject_html(text: str) -> None:
    sample = text.lstrip().lower()[:512]
    if sample.startswith("<!doctype html") or "<html" in sample:
        raise ValueError("response is HTML, not an HLS manifest")


def _require_hls(text: str) -> list[str]:
    _reject_html(text)
    lines = [line.strip() for line in text.lstrip("\ufeff").splitlines()]
    if not lines or lines[0] != "#EXTM3U":
        raise ValueError("response is not an HLS manifest (#EXTM3U missing)")
    return lines


def parse_m3u_text(text: str, source: str = "") -> list[Channel]:
    lines = _require_hls(text)
    channels: list[Channel] = []
    pending: tuple[str, dict[str, str]] | None = None
    for line in lines[1:]:
        if line.startswith("#EXTINF:"):
            metadata, separator, name = line.partition(",")
            if not separator or not name.strip():
                raise ValueError("EXTINF entry has no channel name")
            attributes: dict[str, str] = {}
            tokens = shlex.split(metadata[len("#EXTINF:") :])
            for token in tokens[1:]:
                key, equals, value = token.partition("=")
                if equals:
                    attributes[key] = value
            pending = (name.strip(), attributes)
        elif line and not line.startswith("#") and pending:
            name, attributes = pending
            channels.append(
                Channel(
                    name=name,
                    url=line,
                    group=attributes.get("group-title", ""),
                    logo=attributes.get("tvg-logo", ""),
                    tvg_id=attributes.get("tvg-id", ""),
                    source=source,
                )
            )
            pending = None
    return channels


def _attribute_map(value: str) -> dict[str, str]:
    return {
        key: raw.strip('"')
        for key, raw in re.findall(r"([A-Z0-9-]+)=((?:\"[^\"]*\")|[^,]*)", value)
    }


def parse_master_manifest(text: str, base_url: str) -> list[Variant]:
    lines = _require_hls(text)
    variants: list[Variant] = []
    for index, line in enumerate(lines):
        if not line.startswith("#EXT-X-STREAM-INF:"):
            continue
        attributes = _attribute_map(line.partition(":")[2])
        uri = next(
            (candidate for candidate in lines[index + 1 :] if candidate and not candidate.startswith("#")),
            "",
        )
        if not uri:
            raise ValueError("variant playlist URI is missing")
        variants.append(
            Variant(
                url=urljoin(base_url, uri),
                bandwidth=int(attributes["BANDWIDTH"]) if attributes.get("BANDWIDTH", "").isdigit() else None,
                average_bandwidth=int(attributes["AVERAGE-BANDWIDTH"])
                if attributes.get("AVERAGE-BANDWIDTH", "").isdigit()
                else None,
                resolution=attributes.get("RESOLUTION", ""),
            )
        )
    if not variants:
        raise ValueError("HLS manifest has no #EXT-X-STREAM-INF variant playlist")
    return variants


def parse_media_manifest(text: str, base_url: str) -> list[str]:
    lines = _require_hls(text)
    segments = [urljoin(base_url, line) for line in lines if line and not line.startswith("#")]
    if not segments:
        raise ValueError("HLS media playlist contains no segment")
    return segments
