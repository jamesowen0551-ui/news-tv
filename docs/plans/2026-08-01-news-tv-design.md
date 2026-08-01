# News TV Playlist Design

## Goal

Build a conservative, long-lived IPTV playlist for Sony Android TV clients. Stability and verifiable first-party distribution take priority over channel count.

## Source policy

Only streams published by the broadcaster, its documented distribution platform, or its official CDN are eligible. Streams requiring temporary tokens, DRM circumvention, third-party restreaming, or unverifiable provenance are excluded. A preferred channel is omitted whenever its source or current playback cannot be verified.

Official logos are included only when a stable first-party asset URL is available; missing logos never block a valid stream.

## Repository layout

- `news.m3u`: combined playlist containing every accepted channel.
- `playlists/finance.m3u`: Finance channels.
- `playlists/us-news.m3u`: US News channels.
- `playlists/world-news.m3u`: World News channels.
- `playlists/events.m3u`: empty, documented extension point for future official event streams.
- `scripts/check_streams.py`: standard-library stream validator and report generator.
- `tests/test_check_streams.py`: deterministic unit tests using a local HTTP server.
- `.github/workflows/check-streams.yml`: daily health check at 04:00 Asia/Shanghai.
- `reports/`: generated Markdown health reports.

The combined playlist duplicates the accepted entries rather than using nested playlist URLs because Android IPTV clients do not consistently support nested M3U imports.

## Validation model

For each channel the checker follows redirects with a browser-like User-Agent and bounded timeouts. It rejects non-200 responses, HTML responses, non-HLS bodies, malformed master/media playlists, missing variants, and inaccessible first media segments.

When a master playlist is returned, the checker parses `#EXT-X-STREAM-INF`, reports advertised resolution and bandwidth, chooses the highest-bandwidth variant, resolves relative URLs, loads its media playlist, and requests the first segment. A direct media playlist is accepted only when it contains media segments; the report records that it has no advertised variants.

The checker records redirect count, request latency, variant count, maximum resolution, maximum advertised bitrate, segment accessibility, and a five-star operational score. The score is a maintenance signal based on manifest structure, quality metadata, segment access, redirects, and latency; it is not a statement about editorial quality.

## Automation and failure handling

GitHub Actions runs at `20:00 UTC`, equivalent to 04:00 the next day in Beijing year-round. It always writes and uploads a Markdown report. A failed channel makes the job fail after the report is generated. Automation never edits playlists and never substitutes sources.

## Documentation

The README explains import steps for Sony Android TV apps including TiviMate, Televizo, Sparkle TV, and OTT Navigator, states the source policy and exclusions, documents local checker usage and scoring, and lists future event categories without adding speculative streams.

## Release process

Candidate first-party URLs are researched and tested live. Only passing candidates are written to the playlists. Unit tests, playlist validation, and a final live check must pass before committing and pushing `main` to `jamesowen0551-ui/news-tv`.
