#!/usr/bin/env python3
"""Generate the Favorites playlist from exact tvg-id values in a strict YAML subset."""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

if __package__:
    from .channel_catalog import load_catalog_text, render_channels, sync_text
else:
    from channel_catalog import load_catalog_text, render_channels, sync_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/favorites.yaml"
DEFAULT_CATALOG = ROOT / "channels/catalog.json"
DEFAULT_OUTPUT = ROOT / "playlists/favorites.m3u"
TVG_ID_PATTERN = re.compile(r"[A-Za-z0-9._-]+")


def parse_favorites_config(text: str) -> list[str]:
    favorites: list[str] = []
    header_seen = False
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if not header_seen:
            if raw_line == "favorites:":
                header_seen = True
                continue
            raise ValueError(f"unsupported YAML at line {line_number}")
        if not stripped.startswith("- "):
            raise ValueError(f"unsupported YAML key or value at line {line_number}")
        tvg_id = stripped[2:].strip()
        if "://" in tvg_id:
            raise ValueError(f"URL values are forbidden at line {line_number}")
        if not TVG_ID_PATTERN.fullmatch(tvg_id):
            raise ValueError(f"invalid full tvg-id at line {line_number}: {tvg_id}")
        if tvg_id in favorites:
            raise ValueError(f"duplicate favorite tvg-id: {tvg_id}")
        favorites.append(tvg_id)
    if not header_seen:
        raise ValueError("missing favorites YAML key")
    if not favorites:
        raise ValueError("favorites list is empty")
    return favorites


def generate_favorites_text(
    config_text: str,
    catalog_text: str,
    *,
    group_override: str | None = None,
) -> str:
    favorite_ids = parse_favorites_config(config_text)
    catalog = load_catalog_text(catalog_text)
    for tvg_id in favorite_ids:
        try:
            catalog.channel_by_id(tvg_id)
        except ValueError as error:
            raise ValueError(
                f"favorite tvg-id not found in channel catalog: {tvg_id}"
            ) from error
    return render_channels(catalog, favorite_ids, group_override=group_override)


def run(
    argv: list[str] | None,
    *,
    default_config: Path,
    default_output: Path,
    group_override: str | None = None,
) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=default_config)
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument("--output", type=Path, default=default_output)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        expected = generate_favorites_text(
            args.config.read_text(encoding="utf-8"),
            args.catalog.read_text(encoding="utf-8"),
            group_override=group_override,
        )
        sync_text(args.output, expected, check=args.check)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL favorites generation: {error}", file=sys.stderr)
        return 1

    action = "PASS favorites are current" if args.check else "Wrote"
    print(f"{action}: {args.output}")
    return 0


def main(argv: list[str] | None = None) -> int:
    return run(
        argv,
        default_config=DEFAULT_CONFIG,
        default_output=DEFAULT_OUTPUT,
    )


if __name__ == "__main__":
    raise SystemExit(main())
