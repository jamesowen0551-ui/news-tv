# News TV

A small, conservative IPTV playlist of free, official English-language news streams for Sony Android TV and other IPTV players.

The project optimizes for provenance and stability, not channel count. A stream is published only when its public availability can be tied to the broadcaster or its delivery infrastructure and the live HLS check succeeds.

## Playlist URLs

Recommended television address (GitHub Raw, primary):

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/news.m3u
```

Backup television address (jsDelivr CDN):

```text
https://cdn.jsdelivr.net/gh/jamesowen0551-ui/news-tv@main/news.m3u
```

Use GitHub Raw normally. Use jsDelivr only as a fallback when GitHub Raw is
temporarily slow or unreachable from the television. Daily automation downloads
both public entry points and requires their exact bytes and SHA-256 digests to match.

Canonical combined playlist:

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/news.m3u
```

EPG (XMLTV identity framework):

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml
```

Favorites playlist:

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/favorites.m3u
```

Legacy combined playlist (fully supported for existing installations):

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/news.m3u
```

Category playlists:

```text
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/finance.m3u
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/us-news.m3u
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/world-news.m3u
```

Root `news.m3u` is kept byte-for-byte identical to `playlists/news.m3u`. Existing
television configurations do not need to migrate; all new setup examples use the
canonical path.

## Channels

| Category | Channels |
|---|---|
| Finance | Bloomberg TV, Schwab Network |
| US News | CBS News 24/7, NBC News NOW, Scripps News |
| World News | Sky News, DW English, NHK World-Japan, Euronews English, Al Jazeera English |

See [docs/sources.md](docs/sources.md) for first-party availability evidence, delivery decisions, and candidates withheld from this release.

## Sony Android TV setup

Install one IPTV player from Google Play on the television, then import these URLs.
App labels can vary slightly between versions.

```text
M3U URL:
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/news.m3u

EPG URL:
https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml
```

The M3U header already includes the EPG URL. If the player does not import it
automatically, add the XMLTV URL manually using the app's EPG settings.

### TiviMate

1. Open **Add playlist**.
2. Choose **M3U playlist** and then **Enter URL**.
3. Enter the combined raw URL.
4. If prompted for an EPG source, enter the EPG URL; otherwise add it later in the playlist's EPG settings.
5. Name the playlist `News TV`, complete setup, and open **TV**.

### Televizo

1. Open **Playlists** and select **Create playlist**.
2. Choose **New M3U playlist**.
3. Enter `News TV` as the name and paste the combined raw URL as the playlist link.
4. Add the EPG URL when Televizo offers an EPG source, then save.
5. Open the playlist and refresh it if the channels do not appear immediately.

### Sparkle TV

1. Open **Sources** and select **Add new source**.
2. Choose **Playlist** as the source type.
3. Paste the combined raw URL and name the source `News TV`.
4. Add the EPG URL as an XMLTV source if it was not detected from the playlist header.
5. Finish setup and allow Sparkle TV to synchronize the source.

### OTT Navigator

1. Open **Settings**, then **Provider** (or **Providers**).
2. Select **Add provider** and choose a generic **Playlist/M3U** provider.
3. Paste the combined raw URL into the playlist URL field.
4. If necessary, open **Settings → Provider → News TV → Parameters → EPG** and enter the EPG URL.
5. Save the provider and run a provider/EPG update.

For category-only viewing, use one of the category URLs instead. Every published
playlist carries the same EPG URL and preserves the Finance, US News, and World
News groups.

## Favorites and EPG behavior

`playlists/favorites.m3u` contains Bloomberg TV, Sky News, NHK World-Japan,
DW English, and CBS News 24/7 in priority order. It is a separate quick-access
playlist and does not change the categories in the full playlist.

Favorites are generated rather than maintained by hand. Edit
`config/favorites.yaml` using exact full `tvg-id` values already present in
`playlists/news.m3u`, then run:

```bash
python3 scripts/generate_favorites.py
python3 scripts/generate_favorites.py --check
```

The generator preserves configuration order and copies only existing main-playlist
entries. Unknown IDs, duplicates, aliases, URLs, and extra YAML keys fail. It
cannot introduce a new stream URL.

`epg/epg.xml` is intentionally conservative. It currently maps the ten stable
`tvg-id` values to their channel names but contains no programme entries. No show
title or broadcast time is invented. Programme data will be added only when an
official public source with suitable reuse terms is confirmed.

`scripts/discover_epg.py` is a read-only future interface. It accepts exact full
IDs and prints reviewed candidates as JSON:

```bash
python3 scripts/discover_epg.py BloombergTV.us SkyNews.uk
```

The current candidate registry is empty, so it reports `no-confirmed-source`.
The script does not use the network, modify `epg/epg.xml`, or create programme data.

## Repository layout

```text
news.m3u                    # legacy-compatible mirror
playlists/news.m3u          # canonical combined playlist
playlists/finance.m3u
playlists/us-news.m3u
playlists/world-news.m3u
playlists/favorites.m3u
playlists/events.m3u
config/favorites.yaml
epg/epg.xml
scripts/check_streams.py
scripts/check_mirrors.py
scripts/generate_favorites.py
scripts/discover_epg.py
reports/                    # generated health reports (not committed)
```

## Inclusion policy

Allowed:

- Official public live broadcasts.
- Broadcaster-controlled or identifiable official CDN delivery.
- Exact HLS delivery endpoints exposed by an official web player.
- Stable URLs without expiring query tokens.

Not allowed:

- Third-party restreams or unexplained proxy servers.
- Temporary signed URLs or session tokens.
- DRM bypasses or access-control circumvention.
- Sources whose association with the broadcaster cannot be confirmed.
- Unauthorized CNN, CNBC, BBC News, or Fox News cable streams.

Passing a network test does not establish permission or provenance. For that reason, technically working candidates may still be withheld. Logos are also omitted until stable first-party usage permission can be established.

## Stream checker

The checker uses only the Python standard library:

```bash
python3 scripts/check_streams.py playlists/news.m3u \
  --timeout 15 \
  --report reports/health-report.md
```

It verifies:

- Required `x-tvg-url`, `tvg-id`, `tvg-name`, and `group-title` metadata.
- Unique channel IDs, allowed categories, HTTPS URLs, and optional logo URL format.
- HTTP status and redirect handling.
- Content-Type and explicit HTML rejection.
- A real `#EXTM3U` HLS manifest.
- At least one `#EXT-X-STREAM-INF` variant.
- Highest-quality playable variant, with fallback across redundant variants.
- Resolution and advertised bandwidth.
- Accessibility of the first media segment using a bounded byte request.
- Per-request timeout, browser-compatible User-Agent, and total request latency.

The command always writes the requested Markdown report and exits nonzero when any
channel fails. Strict PASS/FAIL behavior is unchanged. The existing five-star
rating remains, and a separate 0–100 health score uses these weights:

| Dimension | Points |
|---|---:|
| Initial HTTP access | 15 |
| Master manifest | 15 |
| Variant playlist | 15 |
| First segment | 20 |
| Resolution | 15 |
| Total response time | 15 |
| Redirect count | 5 |

Passed channels scoring 90 or above are `Healthy`; passed channels scoring 75–89
are `Degraded`. Failed channels and scores below 75 are `Unhealthy`. Scores are
reporting metadata only: they never delete, replace, or reorder a channel.

Run the deterministic test suite with:

```bash
python3 -m unittest discover -s tests -v
```

## Automated monitoring

GitHub Actions runs the live check every day at 04:00 Beijing time (`20:00 UTC`)
and can also be started manually exactly as before. It checks generated Favorites,
validates all live streams, compares GitHub Raw with jsDelivr, and uploads both
`reports/stream-report.md` and `reports/health-report.md` in the existing
`stream-health-report` artifact. The legacy report path remains supported.

Automation never edits playlists, replaces URLs, or adds an unreviewed source.

## Maintenance principles

- Prefer official public HLS and broadcaster-controlled delivery.
- Keep the catalog small when provenance or stability is uncertain.
- Treat health scores as observations, never as automatic removal instructions.
- Keep Favorites derived from the canonical playlist and exact stable IDs.
- Require GitHub Raw and CDN bytes to match; never use the CDN as a different source.
- Keep EPG discovery read-only until an official reusable schedule is confirmed.
- Never auto-replace a failed channel with an unreviewed URL.

## Future event playlist

[`playlists/events.m3u`](playlists/events.m3u) is intentionally empty. It is reserved for time-bounded, official streams such as FOMC, ECB, IMF, World Bank, NASA TV, Apple Keynote, Google I/O, NVIDIA GTC, and OpenAI events. Event entries will be added only after the same provenance and live checks, then removed when the official event ends.

## Disclaimer

This repository contains links, not retransmitted video. Broadcasters and delivery providers can change availability, geographic restrictions, or URLs at any time. Users are responsible for complying with applicable terms and local law.
