# China Candidate Channel Framework Design

## Goal

Add a conservative research and manual-approval path for expanding the China household playlist without changing any existing published playlist or weakening source provenance rules.

## Compatibility contract

- `channels/catalog.json` remains the only source of facts for published channels.
- `news.m3u`, `playlists/news.m3u`, and `playlists/news-cn.m3u` remain byte-for-byte unchanged in this release.
- Existing Global and China profile order and all current `tvg-id` values remain unchanged.
- Candidate data is never read by a playlist, Favorites, or EPG generator.
- A technical PASS never changes candidate status and never publishes a channel.

## Candidate data model

`channels/candidates.json` uses a versioned document with an ordered `candidates` array. Every entry has exactly these fields:

```json
{
  "id": "ExampleNews.xx",
  "name": "Example News",
  "country": "Country",
  "category": "Asia",
  "official_url": "https://broadcaster.example/live",
  "stream_url": "https://media.example/live/master.m3u8",
  "source_notes": "The official player publishes this delivery URL.",
  "status": "candidate"
}
```

IDs must be unique and must not collide with catalog IDs. Both URLs are required HTTPS URLs. Stream URLs cannot contain query parameters, temporary tokens, or fragments. Source notes are mandatory. Status is one of `candidate`, `testing`, `approved`, or `rejected`.

Only channels with a confirmed official page and a concrete official HLS delivery chain enter the candidate file. Names without a reliable HLS URL remain research suggestions in documentation.

## Catalog profiles

The catalog keeps its current top-level ordered profile model and adds:

- `asia`: NHK World-Japan, CNA English, and CGTN English;
- `finance`: Bloomberg TV and Schwab Network;
- `technology`: initially empty.

These profiles are classification sets for formal catalog records. This release does not publish new category M3Us from them. Channel objects do not gain a `profiles` property.

## Candidate lifecycle

```text
confirmed official page + official HLS
  -> candidate record
  -> automated technical check
  -> manual China household test
  -> manually set status to approved
  -> human review and explicit catalog/profile promotion
  -> existing catalog generators publish the channel
```

`approved` means eligible for manual promotion. It does not create a playlist entry. Promotion requires adding one reviewed channel fact to `catalog.json` and explicitly adding its ID to a formal profile in a later change.

## Candidate checker

`scripts/check_candidates.py` validates the candidate document and then calls the existing HLS validation implementation. It checks URL structure, HTTP status, Content-Type, HTML rejection, `#EXTM3U`, master variants, a selected media variant, and the first segment. It accepts the same timeout and User-Agent behavior as the formal checker.

The script produces a Markdown technical report and exits nonzero for invalid metadata or a failed stream. It never rewrites `candidates.json`, changes status, edits the catalog, or generates an M3U.

## Manual China testing

`reports/china-candidate-testing.md` is a tracked manual record, separate from automated candidate checks and Global Health. It provides fields for channel, test date, test environment, PASS/FAIL, first-frame time, resolution, stability, and notes.

Unknown measurements remain explicitly unrecorded. Automated latency and resolution are not copied into manual fields and no household result is inferred from the development or Actions network.

## Initial research

Research starts with KBS World, Arirang TV, ABC Australia, SBS Australia, NASA TV, and TRT World, then considers the remaining requested finance, technology, and Asia directions. Existing catalog channels are not duplicated in the candidate pool.

A candidate is seeded only after its official page-to-HLS relationship is confirmed and the strict checker passes. A broadcaster name alone is not a candidate record.

## Tests

Tests lock down:

- exact candidate schema, statuses, HTTPS/no-query policy, unique IDs, and catalog non-collision;
- correct `asia`, `finance`, and `technology` membership and order;
- unchanged Global and China playlist bytes and approved Global SHA-256;
- no candidate, including an `approved` candidate, entering a generated playlist;
- only exact catalog/profile IDs generating formal M3Us;
- candidate checker reuse of the strict HLS validation function;
- HTTP, HTML, non-HLS, missing-variant, segment, and timeout failures;
- an identity-only EPG and unchanged scheduled Global Health behavior.
