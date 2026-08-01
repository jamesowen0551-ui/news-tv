#!/usr/bin/env python3
"""Generate China Favorites from exact catalog IDs."""

from __future__ import annotations

from pathlib import Path

if __package__:
    from .generate_favorites import ROOT, run
else:
    from generate_favorites import ROOT, run


DEFAULT_CONFIG = ROOT / "config/favorites-cn.yaml"
DEFAULT_OUTPUT = ROOT / "playlists/favorites-cn.m3u"


def main(argv: list[str] | None = None) -> int:
    return run(
        argv,
        default_config=DEFAULT_CONFIG,
        default_output=DEFAULT_OUTPUT,
        group_override="China Recommended",
    )


if __name__ == "__main__":
    raise SystemExit(main())
