#!/usr/bin/env python3
"""Generate only the China-optimized playlist from the channel catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from .channel_catalog import load_catalog_text, render_profile, sync_text
else:
    from channel_catalog import load_catalog_text, render_profile, sync_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "channels/catalog.json"
DEFAULT_OUTPUT = ROOT / "playlists/news-cn.m3u"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    try:
        catalog = load_catalog_text(args.catalog.read_text(encoding="utf-8"))
        text = render_profile(
            catalog, "china_optimized", group_override="China Recommended"
        )
        sync_text(args.output, text, check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL China playlist generation: {error}", file=sys.stderr)
        return 1
    action = "PASS China playlist is current" if args.check else "Generated"
    print(f"{action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
