#!/usr/bin/env python3
"""Generate every published non-Favorites playlist from the channel catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from .channel_catalog import (
        load_catalog_text,
        render_global_group,
        render_profile,
        sync_text,
    )
else:
    from channel_catalog import (
        load_catalog_text,
        render_global_group,
        render_profile,
        sync_text,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "channels/catalog.json"


def expected_outputs(catalog) -> dict[str, str]:
    global_playlist = render_profile(catalog, "global")
    events_playlist = (
        f'#EXTM3U x-tvg-url="{catalog.epg_url}"\n'
        "# Reserved for verified, time-bounded official event streams only.\n"
        "# Possible future coverage: FOMC, ECB, IMF, World Bank, NASA TV,\n"
        "# Apple Keynote, Google I/O, NVIDIA GTC, and OpenAI Event.\n"
    )
    return {
        "news.m3u": global_playlist,
        "playlists/news.m3u": global_playlist,
        "playlists/finance.m3u": render_global_group(catalog, "Finance"),
        "playlists/us-news.m3u": render_global_group(catalog, "US News"),
        "playlists/world-news.m3u": render_global_group(catalog, "World News"),
        "playlists/news-cn.m3u": render_profile(
            catalog, "china_optimized", group_override="China Recommended"
        ),
        "playlists/events.m3u": events_playlist,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        catalog = load_catalog_text(args.catalog.read_text(encoding="utf-8"))
        outputs = expected_outputs(catalog)
        for relative_path, text in outputs.items():
            sync_text(args.root / relative_path, text, check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL playlist generation: {error}", file=sys.stderr)
        return 1

    action = "PASS playlists are current" if args.check else "Generated playlists"
    print(f"{action}: {args.root}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
