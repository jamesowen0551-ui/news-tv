#!/usr/bin/env python3
"""Strictly test unpublished channel candidates without promoting them."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__:
    from .candidate_catalog import CandidatePool, load_candidate_pool_text
    from .channel_catalog import load_catalog_text
    from .check_streams import (
        Channel,
        ValidationResult,
        render_markdown,
        validate_channel,
    )
else:
    from candidate_catalog import CandidatePool, load_candidate_pool_text
    from channel_catalog import load_catalog_text
    from check_streams import (
        Channel,
        ValidationResult,
        render_markdown,
        validate_channel,
    )


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CANDIDATES = ROOT / "channels/candidates.json"
DEFAULT_CATALOG = ROOT / "channels/catalog.json"


def candidate_channels(pool: CandidatePool) -> list[Channel]:
    return [
        Channel(
            name=candidate.name,
            url=candidate.stream_url,
            group=candidate.category,
            tvg_id=candidate.id,
            tvg_name=candidate.name,
            source=candidate.official_url,
        )
        for candidate in pool.candidates
    ]


def run_checks(
    pool: CandidatePool, timeout: float = 10
) -> list[ValidationResult]:
    return [
        validate_channel(channel, timeout=timeout)
        for channel in candidate_channels(pool)
    ]


def render_candidate_report(results: list[ValidationResult]) -> str:
    report = render_markdown(results).replace(
        "# Stream Health Report", "# Candidate Technical Report", 1
    )
    return report + (
        "> A technical PASS does not approve or publish a candidate. Status changes "
        "and catalog promotion require manual review.\n"
    )


def _emit_report(
    results: list[ValidationResult], report_path: Path | None
) -> None:
    report = render_candidate_report(results)
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(report, encoding="utf-8")
        print(f"Wrote {report_path}")
    else:
        print(report)


def _input_failure(message: str, report_path: Path | None) -> int:
    result = ValidationResult(
        channel=Channel(name="Candidate input", url=""),
        ok=False,
        error=message,
    )
    _emit_report([result], report_path)
    print(f"FAIL Candidate input: {message}", file=sys.stderr)
    return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--candidates", type=Path, default=DEFAULT_CANDIDATES
    )
    parser.add_argument("--catalog", type=Path, default=DEFAULT_CATALOG)
    parser.add_argument(
        "--timeout", type=float, default=10, help="per-request timeout in seconds"
    )
    parser.add_argument(
        "--report", type=Path, help="write the Markdown technical report"
    )
    args = parser.parse_args(argv)

    try:
        catalog = load_catalog_text(args.catalog.read_text(encoding="utf-8"))
        pool = load_candidate_pool_text(
            args.candidates.read_text(encoding="utf-8"), catalog
        )
    except (OSError, UnicodeError, ValueError) as error:
        return _input_failure(f"candidate load failed: {error}", args.report)
    if not pool.candidates:
        return _input_failure("no candidates found", args.report)

    results = run_checks(pool, timeout=args.timeout)
    _emit_report(results, args.report)
    for result in results:
        outcome = "PASS" if result.ok else "FAIL"
        if result.ok:
            detail = result.resolution or "HLS validated"
        else:
            detail = result.error
        print(f"{outcome:4} {result.channel.name}: {detail}", file=sys.stderr)
    return 0 if all(result.ok for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
