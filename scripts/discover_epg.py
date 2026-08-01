#!/usr/bin/env python3
"""List reviewed EPG source candidates without network access or file changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__:
    from .check_streams import parse_m3u_text
else:
    from check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PLAYLIST = ROOT / "playlists/news.m3u"
EPG_CANDIDATES: dict[str, list[dict[str, str]]] = {}
NO_SOURCE_NOTE = (
    "No official public EPG source with confirmed reuse terms is registered. "
    "No programme data was generated."
)


def discover_candidates(
    tvg_ids: list[str], playlist_text: str
) -> list[dict[str, object]]:
    channels = parse_m3u_text(playlist_text, source="canonical playlist")
    by_id = {channel.tvg_id: channel for channel in channels}
    results: list[dict[str, object]] = []
    seen: set[str] = set()
    for tvg_id in tvg_ids:
        if tvg_id in seen:
            raise ValueError(f"duplicate tvg-id input: {tvg_id}")
        seen.add(tvg_id)
        channel = by_id.get(tvg_id)
        if channel is None:
            raise ValueError(f"unknown tvg-id (exact matching only): {tvg_id}")
        candidates = EPG_CANDIDATES.get(tvg_id, [])
        results.append(
            {
                "tvg_id": tvg_id,
                "channel": channel.name,
                "status": "candidates-reviewed" if candidates else "no-confirmed-source",
                "candidates": candidates,
                "note": NO_SOURCE_NOTE if not candidates else "Candidates require manual review.",
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tvg_ids", nargs="+", help="exact full tvg-id values")
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    args = parser.parse_args(argv)

    try:
        results = discover_candidates(
            args.tvg_ids, args.playlist.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL EPG discovery: {error}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
