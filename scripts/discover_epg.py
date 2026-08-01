#!/usr/bin/env python3
"""List reviewed EPG source candidates without network access or file changes."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__:
    from .channel_catalog import load_catalog_text
else:
    from channel_catalog import load_catalog_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "channels/catalog.json"
EPG_CANDIDATES: dict[str, list[dict[str, str]]] = {}
NO_SOURCE_NOTE = (
    "No official public EPG source with confirmed reuse terms is registered. "
    "No programme data was generated."
)


def discover_candidates(
    tvg_ids: list[str], catalog_text: str
) -> list[dict[str, object]]:
    catalog = load_catalog_text(catalog_text)
    results: list[dict[str, object]] = []
    seen: set[str] = set()
    for tvg_id in tvg_ids:
        if tvg_id in seen:
            raise ValueError(f"duplicate tvg-id input: {tvg_id}")
        seen.add(tvg_id)
        channel = catalog.channel_by_id(tvg_id)
        candidates = EPG_CANDIDATES.get(tvg_id, [])
        results.append(
            {
                "tvg_id": tvg_id,
                "channel": channel.tvg_name,
                "status": "candidates-reviewed" if candidates else "no-confirmed-source",
                "candidates": candidates,
                "note": NO_SOURCE_NOTE if not candidates else "Candidates require manual review.",
            }
        )
    return results


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("tvg_ids", nargs="+", help="exact full tvg-id values")
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    args = parser.parse_args(argv)

    try:
        results = discover_candidates(
            args.tvg_ids, args.catalog.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL EPG discovery: {error}", file=sys.stderr)
        return 1
    print(json.dumps(results, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
