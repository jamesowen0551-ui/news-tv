#!/usr/bin/env python3
"""Generate the identity-only XMLTV framework from the channel catalog."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from xml.sax.saxutils import escape, quoteattr

if __package__:
    from .channel_catalog import load_catalog_text, sync_text
else:
    from channel_catalog import load_catalog_text, sync_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CATALOG = ROOT / "channels/catalog.json"
DEFAULT_OUTPUT = ROOT / "epg/epg.xml"


def render_epg(catalog) -> str:
    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<tv generator-info-name="News TV" generator-info-url="https://github.com/jamesowen0551-ui/news-tv">',
    ]
    for channel in catalog.channels:
        lines.extend(
            [
                f"  <channel id={quoteattr(channel.tvg_id)}>",
                f'    <display-name lang="en">{escape(channel.tvg_name)}</display-name>',
                "  </channel>",
            ]
        )
    lines.append("</tv>")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        catalog = load_catalog_text(args.catalog.read_text(encoding="utf-8"))
        sync_text(args.output, render_epg(catalog), check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL EPG generation: {error}", file=sys.stderr)
        return 1

    action = "PASS EPG is current" if args.check else "Wrote"
    print(f"{action}: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
