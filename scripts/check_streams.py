#!/usr/bin/env python3
"""Validate IPTV HLS streams and produce a Markdown health report."""

from __future__ import annotations

import argparse
import re
import shlex
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin
from urllib.request import HTTPRedirectHandler, Request, build_opener


USER_AGENT = "news-tv-stream-checker/1.0 (+https://github.com/jamesowen0551-ui/news-tv)"
MANIFEST_CONTENT_TYPES = {
    "application/mpegurl",
    "application/octet-stream",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "audio/mpegurl",
    "audio/x-mpegurl",
    "binary/octet-stream",
    "text/plain",
}


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


@dataclass(frozen=True)
class ValidationResult:
    channel: Channel
    ok: bool
    http_status: int | None = None
    content_type: str = ""
    final_url: str = ""
    redirects: int = 0
    latency_ms: int | None = None
    variant_count: int = 0
    resolution: str = ""
    bandwidth: int | None = None
    segment_url: str = ""
    score: int = 0
    error: str = ""


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


class _TrackingRedirectHandler(HTTPRedirectHandler):
    def __init__(self) -> None:
        super().__init__()
        self.count = 0

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        self.count += 1
        return super().redirect_request(req, fp, code, msg, headers, newurl)


@dataclass(frozen=True)
class _Response:
    status: int
    content_type: str
    body: bytes
    final_url: str
    redirects: int
    latency_ms: int


def _fetch(url: str, timeout: float, *, segment: bool = False) -> _Response:
    redirect_handler = _TrackingRedirectHandler()
    opener = build_opener(redirect_handler)
    headers = {
        "Accept": "*/*" if segment else "application/vnd.apple.mpegurl, application/x-mpegURL, */*;q=0.8",
        "User-Agent": USER_AGENT,
    }
    if segment:
        headers["Range"] = "bytes=0-1023"
    request = Request(url, headers=headers)
    started = time.monotonic()
    with opener.open(request, timeout=timeout) as response:
        body = response.read(1024 if segment else 2 * 1024 * 1024)
        elapsed = round((time.monotonic() - started) * 1000)
        content_type = response.headers.get_content_type().lower()
        return _Response(
            status=response.status,
            content_type=content_type,
            body=body,
            final_url=response.geturl(),
            redirects=redirect_handler.count,
            latency_ms=elapsed,
        )


def _decode_manifest(response: _Response) -> str:
    if response.status != 200:
        raise ValueError(f"HTTP {response.status}")
    if response.content_type == "text/html":
        raise ValueError("response is HTML, not an HLS manifest")
    try:
        text = response.body.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise ValueError("manifest is not valid UTF-8 text") from error
    _require_hls(text)
    if response.content_type not in MANIFEST_CONTENT_TYPES:
        raise ValueError(f"unexpected manifest Content-Type: {response.content_type}")
    return text


def _score(resolution: str, bandwidth: int | None, latency_ms: int, redirects: int) -> int:
    score = 5
    height = 0
    if "x" in resolution:
        try:
            height = int(resolution.lower().split("x", 1)[1])
        except ValueError:
            height = 0
    if height < 720:
        score -= 1
    if bandwidth is None or bandwidth < 1_000_000:
        score -= 1
    if latency_ms > 3_000:
        score -= 1
    if redirects > 2:
        score -= 1
    return max(1, score)


def validate_channel(channel: Channel, timeout: float = 10) -> ValidationResult:
    total_redirects = 0
    total_latency = 0
    initial: _Response | None = None
    try:
        initial = _fetch(channel.url, timeout)
        total_redirects += initial.redirects
        total_latency += initial.latency_ms
        master_text = _decode_manifest(initial)
        variants = parse_master_manifest(master_text, initial.final_url)
        selected: Variant | None = None
        segment_url = ""
        variant_errors: list[str] = []
        for candidate in sorted(
            variants, key=lambda item: item.bandwidth or 0, reverse=True
        ):
            try:
                media = _fetch(candidate.url, timeout)
                media_text = _decode_manifest(media)
                candidate_segment_url = parse_media_manifest(media_text, media.final_url)[0]
                segment = _fetch(candidate_segment_url, timeout, segment=True)
                if segment.status not in (200, 206) or not segment.body:
                    raise ValueError(
                        f"first segment returned HTTP {segment.status} or no data"
                    )
            except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
                if isinstance(error, HTTPError):
                    error.close()
                variant_errors.append(f"{candidate.url}: {error}")
                continue
            selected = candidate
            segment_url = candidate_segment_url
            total_redirects += media.redirects + segment.redirects
            total_latency += media.latency_ms + segment.latency_ms
            break
        if selected is None:
            details = "; ".join(variant_errors[:3])
            raise ValueError(f"no playable HLS variant ({details})")

        bandwidth = selected.average_bandwidth or selected.bandwidth
        return ValidationResult(
            channel=channel,
            ok=True,
            http_status=initial.status,
            content_type=initial.content_type,
            final_url=initial.final_url,
            redirects=total_redirects,
            latency_ms=total_latency,
            variant_count=len(variants),
            resolution=selected.resolution,
            bandwidth=bandwidth,
            segment_url=segment_url,
            score=_score(selected.resolution, bandwidth, total_latency, total_redirects),
        )
    except (HTTPError, URLError, TimeoutError, OSError, ValueError) as error:
        error_status = initial.status if initial else None
        error_content_type = initial.content_type if initial else ""
        error_url = initial.final_url if initial else ""
        if isinstance(error, HTTPError):
            error_status = error.code
            error_content_type = error.headers.get_content_type().lower()
            error_url = error.geturl()
            error.close()
        return ValidationResult(
            channel=channel,
            ok=False,
            http_status=error_status,
            content_type=error_content_type,
            final_url=error_url,
            redirects=total_redirects,
            latency_ms=total_latency or None,
            error=str(error),
        )


def _escape_cell(value: object) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


def _quality(result: ValidationResult) -> str:
    if not result.ok:
        return "—"
    resolution = result.resolution or "not advertised"
    bitrate = f"{result.bandwidth / 1_000_000:.2f} Mbps" if result.bandwidth else "not advertised"
    return f"{resolution}; {bitrate}"


def render_markdown(
    results: list[ValidationResult], generated_at: str | None = None
) -> str:
    timestamp = generated_at or datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    passed = sum(result.ok for result in results)
    failed = len(results) - passed
    lines = [
        "# Stream Health Report",
        "",
        f"Generated: `{timestamp}`",
        "",
        f"Summary: **{passed} passed, {failed} failed**.",
        "",
        "| Status | Channel | Category | Score | Quality | HTTP | Content-Type | Latency | Redirects | Details |",
        "|---|---|---|---:|---|---:|---|---:|---:|---|",
    ]
    for result in results:
        status = "PASS" if result.ok else "FAIL"
        stars = "★" * result.score + "☆" * (5 - result.score) if result.ok else "☆☆☆☆☆"
        latency = f"{result.latency_ms} ms" if result.latency_ms is not None else "—"
        details = (
            f"{result.variant_count} variants; first segment accessible"
            if result.ok
            else result.error or "unknown error"
        )
        lines.append(
            "| "
            + " | ".join(
                _escape_cell(value)
                for value in (
                    status,
                    result.channel.name,
                    result.channel.group or "—",
                    stars,
                    _quality(result),
                    result.http_status if result.http_status is not None else "—",
                    result.content_type or "—",
                    latency,
                    result.redirects,
                    details,
                )
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "> Scores reflect current stream structure, advertised quality, redirects, and request latency—not editorial quality.",
            "",
        ]
    )
    return "\n".join(lines)


def _load_channels(paths: list[Path]) -> list[Channel]:
    channels: list[Channel] = []
    seen: set[tuple[str, str]] = set()
    for path in paths:
        for channel in parse_m3u_text(path.read_text(encoding="utf-8"), source=str(path)):
            key = (channel.name, channel.url)
            if key not in seen:
                channels.append(channel)
                seen.add(key)
    return channels


def _emit_report(results: list[ValidationResult], report_path: Path | None) -> None:
    report = render_markdown(results)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"Wrote {report_path}")
    else:
        print(report)


def _input_failure(message: str, paths: list[Path], report_path: Path | None) -> int:
    result = ValidationResult(
        channel=Channel(
            name="Playlist input",
            url="",
            source=", ".join(str(path) for path in paths),
        ),
        ok=False,
        error=message,
    )
    _emit_report([result], report_path)
    print(f"FAIL Playlist input: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("playlists", nargs="+", type=Path, help="M3U playlists to validate")
    parser.add_argument("--timeout", type=float, default=10, help="per-request timeout in seconds")
    parser.add_argument("--report", type=Path, help="write the Markdown report to this path")
    args = parser.parse_args(argv)

    try:
        channels = _load_channels(args.playlists)
    except (OSError, UnicodeError, ValueError) as error:
        return _input_failure(
            f"playlist load failed: {error}", args.playlists, args.report
        )
    if not channels:
        return _input_failure("no channels found", args.playlists, args.report)

    results = [validate_channel(channel, timeout=args.timeout) for channel in channels]
    _emit_report(results, args.report)
    for result in results:
        outcome = "PASS" if result.ok else "FAIL"
        detail = _quality(result) if result.ok else result.error
        print(f"{outcome:4} {result.channel.name}: {detail}", file=sys.stderr)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
