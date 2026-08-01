# IPTV Metadata, Favorites, and EPG Design

Date: 2026-08-01

## Objective

Upgrade News TV with richer IPTV metadata, a high-priority favorites playlist,
and a truthful EPG framework while preserving all ten verified streams and every
existing public entry point.

## Compatibility contract

- `playlists/news.m3u` becomes the canonical combined playlist.
- Root `news.m3u` remains published as an exact content mirror.
- README keeps the existing root Raw URL and adds the new canonical URL.
- GitHub Actions retains both its daily schedule and `workflow_dispatch` entry.
- Category playlist paths and the checker CLI remain available.
- No existing stream URL, category, source policy, or HLS validation is weakened.

## Playlist metadata

Every published playlist starts with an `#EXTM3U` header whose `x-tvg-url`
points to the repository's raw `epg/epg.xml`. Every channel entry has a unique,
non-empty `tvg-id`, a `tvg-name` equal to its display name, and one of the three
approved `group-title` values: Finance, US News, or World News.

No `tvg-logo` value is added in this iteration. The project has not established
a stable official logo URL with suitable hotlink or redistribution permission,
and an omitted logo is preferable to an uncertain source.

## Favorites

`playlists/favorites.m3u` contains exactly five existing channels, in this order:
Bloomberg TV, Sky News, NHK World-Japan, DW English, and CBS News 24/7. Entries
are copied from the canonical playlist so metadata and stream URLs cannot diverge.

## EPG framework

`epg/epg.xml` is a valid XMLTV document. It defines a `<channel>` element for
each published `tvg-id` and a matching `<display-name>`. It intentionally contains
no `<programme>` elements until an official, redistributable schedule source is
confirmed. This provides correct identity mapping without inventing programme
names or times.

## Validation and data flow

The existing parser is extended to retain `tvg-name` and playlist-header
attributes. Metadata validation runs before network probing and rejects missing,
duplicate, or inconsistent IDs/names/groups and an incorrect or missing EPG URL.
After metadata passes, the current HTTP, redirect, Content-Type, HTML rejection,
master manifest, variant, media manifest, segment, timeout, quality, and report
logic runs unchanged.

The scheduled workflow validates `playlists/news.m3u`, uploads its Markdown
report on every run, and propagates failures after upload. It never edits or
replaces a playlist.

## Testing

Tests first establish the new contract and must fail against the current release.
They then cover:

- canonical and compatibility playlists are identical;
- all required metadata is present, valid, and unique;
- all category playlists match their canonical subsets;
- favorites contain the exact five-channel order;
- XMLTV channel IDs equal M3U IDs and no programme entries are fabricated;
- the workflow uses the canonical path while retaining schedule and manual entry;
- all pre-existing network and parser behavior remains green.

Final verification includes the complete deterministic suite, a real ten-channel
stream check, a clean Git worktree, remote commit equality, and Raw URL checks for
both old and new playlist paths plus the EPG path.
