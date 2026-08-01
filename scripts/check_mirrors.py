#!/usr/bin/env python3
"""Verify that the public GitHub Raw and jsDelivr playlists are identical."""

from __future__ import annotations

import argparse
import hashlib
import sys
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


PRIMARY_URL = "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/news.m3u"
CDN_URL = "https://cdn.jsdelivr.net/gh/jamesowen0551-ui/news-tv@main/news.m3u"
USER_AGENT = "news-tv-mirror-checker/1.0 (+https://github.com/jamesowen0551-ui/news-tv)"
MAX_PLAYLIST_BYTES = 5 * 1024 * 1024


class MirrorMismatchError(ValueError):
    """Raised when the two public playlist payloads differ."""


@dataclass(frozen=True)
class MirrorResult:
    primary_sha256: str
    cdn_sha256: str
    byte_count: int
    equal: bool = True


def _fetch(url: str, timeout: float) -> bytes:
    request = Request(url, headers={"Accept": "*/*", "User-Agent": USER_AGENT})
    with urlopen(request, timeout=timeout) as response:
        if response.status != 200:
            raise ValueError(f"{url}: HTTP {response.status}")
        body = response.read(MAX_PLAYLIST_BYTES + 1)
    if len(body) > MAX_PLAYLIST_BYTES:
        raise ValueError(f"{url}: playlist exceeds {MAX_PLAYLIST_BYTES} bytes")
    return body


def check_mirrors(
    primary_url: str = PRIMARY_URL,
    cdn_url: str = CDN_URL,
    timeout: float = 15,
) -> MirrorResult:
    primary = _fetch(primary_url, timeout)
    cdn = _fetch(cdn_url, timeout)
    primary_sha = hashlib.sha256(primary).hexdigest()
    cdn_sha = hashlib.sha256(cdn).hexdigest()
    if primary_sha != cdn_sha:
        raise MirrorMismatchError(
            f"SHA-256 mismatch: primary={primary_sha}, cdn={cdn_sha}"
        )
    return MirrorResult(primary_sha, cdn_sha, len(primary))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--primary-url", default=PRIMARY_URL)
    parser.add_argument("--cdn-url", default=CDN_URL)
    parser.add_argument("--timeout", type=float, default=15)
    args = parser.parse_args(argv)

    try:
        result = check_mirrors(args.primary_url, args.cdn_url, args.timeout)
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        if isinstance(error, HTTPError):
            error.close()
        print(f"FAIL mirror check: {error}", file=sys.stderr)
        return 1

    print(f"Primary SHA-256: {result.primary_sha256}")
    print(f"CDN SHA-256:     {result.cdn_sha256}")
    print(f"Bytes: {result.byte_count}")
    print("Status: MATCH")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
