# News TV Playlist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish a conservative set of verified first-party English news HLS streams with reusable health checks, Android TV documentation, and daily reporting.

**Architecture:** A dependency-free Python checker parses M3U playlists, validates master and media HLS manifests, probes the first media segment, and emits a Markdown report with quality metadata and an operational score. Static category playlists and the combined playlist contain only candidates that pass both provenance review and a live check; automation reports failures without mutating them.

**Tech Stack:** Python 3.11+ standard library, `unittest`, extended M3U, GitHub Actions, broadcaster/CDN HLS endpoints.

---

### Task 1: Stream checker parsing contract

**Files:**
- Create: `tests/test_check_streams.py`
- Create: `scripts/check_streams.py`

1. Write failing tests for parsing channel metadata from extended M3U, rejecting HTML, recognizing master playlists with `#EXT-X-STREAM-INF`, parsing bandwidth/resolution, and recognizing media playlists with segment URIs.
2. Run `python3 -m unittest -v`; expect import or assertion failures because the checker does not exist.
3. Implement dataclasses plus `parse_m3u`, `parse_master_manifest`, and `parse_media_manifest` using `urllib.parse.urljoin` for relative URIs.
4. Run `python3 -m unittest -v`; expect all parser tests to pass.
5. Commit the parser and tests.

### Task 2: Network validation and reporting

**Files:**
- Modify: `tests/test_check_streams.py`
- Modify: `scripts/check_streams.py`

1. Add failing integration tests backed by an in-process local HTTP server for redirects, User-Agent propagation, master-to-variant traversal, first-segment probing, HTML rejection, timeout/error reporting, and Markdown escaping/output.
2. Run the focused tests and confirm each new behavior fails for the expected missing implementation.
3. Implement a bounded `urllib.request` client, content-type/body checks, redirect history recording, highest-bandwidth variant selection, byte-range segment probe support, metrics collection, and deterministic five-star scoring.
4. Add a CLI accepting one or more playlists, `--timeout`, and `--report`; it must always write the report and exit nonzero when any channel fails.
5. Run `python3 -m unittest -v` and `python3 scripts/check_streams.py --help`; expect success.
6. Commit the completed checker.

### Task 3: Source provenance and live qualification

**Files:**
- Create: `docs/sources.md`
- Create temporarily and then finalize: `news.m3u`
- Create: `playlists/finance.m3u`
- Create: `playlists/us-news.m3u`
- Create: `playlists/world-news.m3u`
- Create: `playlists/events.m3u`

1. Research each requested broadcaster from its official live page and document the official page, delivery host, and inclusion decision without treating third-party playlist repositories as authorization evidence.
2. Build a candidate M3U outside the published paths and run the checker against every candidate.
3. Remove every candidate that fails provenance review, returns HTML, requires an expiring token, lacks a real HLS media path, times out, or has an inaccessible first segment.
4. Generate the four category playlists and combined playlist from the identical accepted entry set; include stable official logo URLs only when verified.
5. Leave `events.m3u` empty except for its M3U header and comments describing the future official-event policy.
6. Run the checker against all published playlists and compare channel sets to prevent drift or duplication.
7. Commit sources and playlists.

### Task 4: Documentation and automation

**Files:**
- Create: `README.md`
- Create: `.github/workflows/check-streams.yml`
- Create: `.gitignore`

1. Document the raw combined URL and category URLs, Sony Android TV setup, and import steps for TiviMate, Televizo, Sparkle TV, and OTT Navigator.
2. Document inclusion/exclusion policy, checker usage, score interpretation, limitations, and the planned event categories.
3. Add a GitHub Actions workflow scheduled at `0 20 * * *` (04:00 Beijing), with manual dispatch, `contents: read`, Python setup, checker execution that preserves its exit code, report artifact upload with `if: always()`, and final failure propagation.
4. Validate YAML structure and run local tests/checks.
5. Commit documentation and automation.

### Task 5: Final verification and release

**Files:**
- Generate: `reports/stream-report.md`

1. Run `python3 -m unittest -v` from a clean working tree context.
2. Run `python3 scripts/check_streams.py news.m3u --timeout 15 --report reports/stream-report.md` and inspect the complete report.
3. Run a playlist consistency check and inspect `git diff --check`, `git status`, and the complete staged diff.
4. Configure the remote `https://github.com/jamesowen0551-ui/news-tv.git`, confirm the target repository, commit the verified release state, and push `main`.
5. Confirm the remote `main` commit and report accepted channels, rejected candidates with reasons, README URL, and raw playlist URL.
