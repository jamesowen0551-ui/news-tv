# China-Optimized Playlist Design

## Goal and compatibility boundary

Add a manually curated China-optimized playlist for mainland residential
broadband and Sony Android TV without changing the published global playlist.
The root `news.m3u` and `playlists/news.m3u` must retain their current exact
bytes and SHA-256 digest:

`cdeabf21790e726bfb2e5cd85916a88432b86d53a53331acabe2249726aa0662`

All existing global channel IDs remain unchanged. Global health measurements
continue to come from GitHub Actions. China compatibility remains a separate,
manually maintained observation and never removes or substitutes a channel.

## Single source of truth

`channels/catalog.json` becomes the sole source of channel facts. Each channel
appears exactly once and owns its stable `tvg-id`, display name, HLS URL, normal
global category when applicable, official public page, delivery evidence, and
profile memberships.

The catalog also stores ordered profile ID lists:

- `global`: the existing ten-channel order.
- `china_optimized`: NHK World-Japan, CNA English, CGTN English, and Schwab
  Network.

Favorites YAML files remain selection policy only: they contain exact complete
IDs and no names, metadata, or URLs. Every generated M3U resolves those IDs
through the catalog. A missing, duplicate, or unknown ID is a hard failure.

## Generated playlists

A shared catalog library validates the JSON and renders deterministic Extended
M3U. A global playlist generator produces the combined root and canonical files
plus Finance, US News, and World News category files. A China generator produces
`playlists/news-cn.m3u` using `group-title="China Recommended"` for all entries.

The existing `scripts/generate_favorites.py` is refactored to resolve its exact
IDs from the catalog rather than copying URLs from another playlist. The new
`scripts/generate_favorites_cn.py` reads `config/favorites-cn.yaml` and produces
`playlists/favorites-cn.m3u`. Both support deterministic generation and
read-only `--check` mode. Generated files use the existing EPG header and no
unconfirmed logos.

The root and canonical global outputs are compared with their pre-change digest
before any commit. Generation is accepted only if their bytes remain identical.

## Source acceptance

NHK World-Japan and Schwab Network reuse their already reviewed catalog URLs.

CGTN English uses the first token-free HLS endpoint returned by the official
`https://news.cgtn.com/tv/channel-en.json`. The official `cgtn.com/tv` page loads
a CGTN JavaScript bundle which reads that JSON and passes the URL directly to
JW Player. The stream must pass master, variant, and first-segment validation.

CNA English uses the public source returned by the official CNA Brightcove
embed: account `6057994443001`, player `jC4rfpFdV4`, video
`6379472319112`. The resulting Mediacorp-branded Akamai HLS contains a signed
path mapping but no expiry claim or time-bound query string. This path is
accepted as an official public, non-temporary source. The older unbranded
CloudFront candidate remains rejected.

If either source fails strict live validation before release, it is omitted and
the corresponding exact-ID configuration check must be resolved rather than
silently replaced.

## China compatibility record

`reports/china-compatibility.md` is a tracked human record, exempted from the
general generated-report ignore rule. It records channel, test environment,
status, startup experience, resolution, and notes. Only facts supplied by the
manual tester are recorded. Unmeasured startup time or resolution is written as
`Not recorded`; GitHub Actions metrics are not copied into this report.

## EPG and checker behavior

The XMLTV framework adds identity-only mappings for `CNAEnglish.sg` and
`CGTNEnglish.cn`, with no fabricated programme elements. The M3U metadata
validator accepts `China Recommended` while retaining all existing strict HLS,
HTML, Content-Type, timeout, redirect, and first-segment checks.

The scheduled global health job continues to validate only
`playlists/news.m3u`. It does not calculate a China score or automatically edit
either profile. Generation consistency is verified without changing the
workflow schedule, manual trigger, report names, artifact name, or public URLs.

## Tests

Tests cover:

- catalog schema, unique IDs, HTTPS URLs, official evidence, and profile IDs;
- exact rendering of all global and category playlists from the catalog;
- immutable global SHA-256 and byte equality of both global entry points;
- complete China metadata and the exact `China Recommended` group;
- China entries and URLs resolving only from catalog records;
- strict Favorites and Favorites-CN ordering and unknown-ID failure;
- EPG identity coverage without programme data;
- independence of global health reporting and China compatibility records;
- strict live HLS validation of all four China entries before release.
