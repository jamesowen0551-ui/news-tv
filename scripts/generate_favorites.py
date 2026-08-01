#!/usr/bin/env python3
"""Generate the Favorites playlist from exact tvg-id values in a strict YAML subset."""

from __future__ import annotations

import argparse
import re
import sys
import tempfile
from pathlib import Path

if __package__:
    from .check_streams import Channel, parse_m3u_text
else:
    from check_streams import Channel, parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "config/favorites.yaml"
DEFAULT_PLAYLIST = ROOT / "playlists/news.m3u"
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


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _render_channel(channel: Channel) -> list[str]:
    attributes = [
        f'tvg-id="{_quote(channel.tvg_id)}"',
        f'tvg-name="{_quote(channel.tvg_name)}"',
    ]
    if channel.logo:
        attributes.append(f'tvg-logo="{_quote(channel.logo)}"')
    attributes.append(f'group-title="{_quote(channel.group)}"')
    return [
        f'#EXTINF:-1 {" ".join(attributes)},{channel.name}',
        channel.url,
    ]


def generate_favorites_text(config_text: str, playlist_text: str) -> str:
    favorite_ids = parse_favorites_config(config_text)
    channels = parse_m3u_text(playlist_text, source="canonical playlist")
    by_id: dict[str, Channel] = {}
    for channel in channels:
        if channel.tvg_id in by_id:
            raise ValueError(f"duplicate tvg-id in canonical playlist: {channel.tvg_id}")
        by_id[channel.tvg_id] = channel

    selected: list[Channel] = []
    for tvg_id in favorite_ids:
        channel = by_id.get(tvg_id)
        if channel is None:
            raise ValueError(f"favorite tvg-id not found in canonical playlist: {tvg_id}")
        selected.append(channel)

    header = playlist_text.lstrip("\ufeff").splitlines()[0].strip()
    lines = [header]
    for channel in selected:
        lines.extend(_render_channel(channel))
    return "\n".join(lines) + "\n"


def _write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=path.parent, delete=False
        ) as handle:
            handle.write(text)
            temporary_path = Path(handle.name)
        temporary_path.chmod(0o644)
        temporary_path.replace(path)
    finally:
        if temporary_path and temporary_path.exists():
            temporary_path.unlink()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--playlist", type=Path, default=DEFAULT_PLAYLIST)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)

    try:
        expected = generate_favorites_text(
            args.config.read_text(encoding="utf-8"),
            args.playlist.read_text(encoding="utf-8"),
        )
        if args.check:
            if not args.output.exists() or args.output.read_text(encoding="utf-8") != expected:
                raise ValueError(f"generated favorites playlist is stale: {args.output}")
            print(f"PASS favorites are current: {args.output}")
            return 0
        _write_atomic(args.output, expected)
    except (OSError, UnicodeError, ValueError) as error:
        print(f"FAIL favorites generation: {error}", file=sys.stderr)
        return 1

    print(f"Wrote {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
