# China-Optimized Playlist Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make one validated channel catalog the sole URL/metadata source and generate unchanged global playlists plus a four-channel China-optimized profile and exact-ID Favorites.

**Architecture:** `channels/catalog.json` stores each channel exactly once and defines ordered profiles. A standard-library catalog module renders deterministic M3U/XMLTV, thin CLIs generate or check every published artifact, and Favorites YAML files contain selection IDs only. Global live health remains separate from the tracked manual China compatibility record.

**Tech Stack:** Python 3.12 standard library, JSON, constrained YAML, Extended M3U, XMLTV, `unittest`, GitHub Actions.

---

### Task 1: Define and validate the single channel catalog

**Files:**
- Create: `tests/test_channel_catalog.py`
- Create: `channels/catalog.json`
- Create: `scripts/channel_catalog.py`

**Step 1: Write failing catalog tests**

Require `load_catalog_text()` to accept `schema_version`, `epg_url`, ordered
`profiles`, and a unique list of channel facts. Assert that the global profile
contains the current ten exact IDs, the China profile contains
`NHKWorldJapan.jp`, `CNAEnglish.sg`, `CGTNEnglish.cn`, and
`SchwabNetwork.us` in that order, and every referenced ID exists.

Add negative tests for duplicate IDs, duplicate profile entries, unknown profile
IDs, missing metadata, non-HTTPS URLs, query strings, and sources without an
official page or delivery evidence.

**Step 2: Run tests to verify RED**

Run: `python3 -m unittest tests.test_channel_catalog -v`

Expected: import failure because `scripts.channel_catalog` does not exist.

**Step 3: Implement the catalog parser**

Create immutable `CatalogChannel` and `Catalog` dataclasses. Parse JSON using
`json.loads`, reject unexpected or missing fields, validate the exact-ID pattern,
unique IDs, HTTPS/no-query stream policy, group names, profile membership, and
official evidence. Provide exact lookup only; never normalize or fuzzy-match IDs.

Populate the existing ten facts byte-for-byte from `playlists/news.m3u`, then add
the reviewed CNA Brightcove/Akamai and CGTN official-JSON HLS records once.

**Step 4: Run focused tests to verify GREEN**

Run: `python3 -m unittest tests.test_channel_catalog -v`

Expected: PASS.

### Task 2: Generate every non-Favorites playlist from catalog

**Files:**
- Modify: `tests/test_channel_catalog.py`
- Create: `scripts/generate_playlists.py`
- Create: `scripts/generate_china_playlist.py`
- Create: `playlists/news-cn.m3u`
- Regenerate without byte changes: `news.m3u`
- Regenerate without byte changes: `playlists/news.m3u`
- Regenerate without byte changes: `playlists/finance.m3u`
- Regenerate without byte changes: `playlists/us-news.m3u`
- Regenerate without byte changes: `playlists/world-news.m3u`
- Regenerate without byte changes: `playlists/events.m3u`

**Step 1: Write failing deterministic-render tests**

Assert `render_profile("global")` exactly equals the committed global bytes and
SHA-256
`cdeabf21790e726bfb2e5cd85916a88432b86d53a53331acabe2249726aa0662`.
Assert category rendering exactly equals the current category files. Assert the
China output has four channels in approved order, complete metadata, the common
`China Recommended` group, and URLs equal to exact catalog records.

Test normal generation, atomic `0644` writes, and `--check` detecting stale files
without modifying them.

**Step 2: Run focused tests to verify RED**

Run: `python3 -m unittest tests.test_channel_catalog.PlaylistGenerationTests -v`

Expected: failure because renderer/generator entry points do not exist.

**Step 3: Implement deterministic rendering and CLIs**

In `channel_catalog.py`, render the unchanged EPG header and attributes in the
existing order: `tvg-id`, `tvg-name`, optional confirmed `tvg-logo`, then
`group-title`. Add reusable atomic write/check helpers.

`generate_playlists.py` owns all profile/category/root output mappings.
`generate_china_playlist.py` is a thin China-only wrapper. Neither script accepts
a URL argument or obtains channel facts from an M3U.

**Step 4: Run generation and verify immutable global bytes**

Run:

```bash
python3 scripts/generate_playlists.py
python3 scripts/generate_playlists.py --check
shasum -a 256 news.m3u playlists/news.m3u
```

Expected: both global digests remain the approved value and tests pass.

### Task 3: Generate both Favorites profiles from catalog exact IDs

**Files:**
- Modify: `tests/test_generate_favorites.py`
- Create: `tests/test_generate_favorites_cn.py`
- Modify: `scripts/generate_favorites.py`
- Create: `scripts/generate_favorites_cn.py`
- Create: `config/favorites-cn.yaml`
- Regenerate: `playlists/favorites.m3u`
- Create: `playlists/favorites-cn.m3u`

**Step 1: Write failing exact-ID tests**

Change the global generator contract so its second fact input is catalog JSON,
not playlist text. Assert both configs preserve order, resolve URLs and metadata
only from catalog, reject aliases/unknown IDs/duplicates/URLs/extra YAML keys,
and fail when an exact ID is absent.

Assert Favorites-CN contains the four requested IDs in order with
`China Recommended`. Assert no generated Favorites URL exists outside the
catalog.

**Step 2: Run tests to verify RED**

Run:

```bash
python3 -m unittest tests.test_generate_favorites -v
python3 -m unittest tests.test_generate_favorites_cn -v
```

Expected: contract/new-module failures.

**Step 3: Refactor and implement minimal generators**

Reuse strict YAML parsing. Resolve every exact ID through `Catalog.channel_by_id`.
Keep global Favorites original groups; force the China profile group for
Favorites-CN. Share the CLI implementation while retaining the existing
`scripts/generate_favorites.py --check` entry point.

**Step 4: Generate and verify GREEN**

Run both generators and their `--check` modes, then run both focused test modules.

Expected: PASS and the original global Favorites bytes remain unchanged.

### Task 4: Extend identity-only EPG and manual China record

**Files:**
- Create: `tests/test_generate_epg.py`
- Create: `scripts/generate_epg.py`
- Modify: `epg/epg.xml`
- Modify: `.gitignore`
- Create: `reports/china-compatibility.md`
- Modify: `tests/test_playlists.py`

**Step 1: Write failing EPG/report tests**

Require XMLTV channel IDs/names to come from all catalog records and require zero
`programme` elements. Test `generate_epg.py --check` stale detection. Require the
tracked China report to have separate environment, status, startup, resolution,
and notes fields for all four channels and to explicitly state that it is manual,
not Global Health Score data.

**Step 2: Run focused tests to verify RED**

Run: `python3 -m unittest tests.test_generate_epg tests.test_playlists -v`

Expected: failures for missing CNA/CGTN mappings and China report.

**Step 3: Implement identity generation and report**

Render deterministic XML with channel/display-name only. Add the two new IDs and
no programme rows. Exempt only `reports/china-compatibility.md` from the generated
report ignore rule. Record user-reported mainland residential broadband + Sony
Android TV PASS status; use `Not recorded` for unsupplied startup/resolution
facts rather than inventing measurements.

**Step 4: Run focused tests to verify GREEN**

Run the EPG generator/check and focused tests. Expected: PASS.

### Task 5: Keep Global Health and China compatibility independent

**Files:**
- Modify: `tests/test_check_streams.py`
- Modify: `scripts/check_streams.py`
- Modify: `tests/test_playlists.py`
- Modify: `.github/workflows/check-streams.yml`

**Step 1: Write failing compatibility tests**

Require the metadata validator to accept `China Recommended` without relaxing
any other check. Lock the workflow's existing name, cron, manual trigger, global
HLS input, report paths, artifact name, and mirror command. Require deterministic
catalog/China/Favorites-CN/EPG `--check` commands, but forbid live validation of
`playlists/news-cn.m3u` in the Global Health job.

**Step 2: Run focused tests to verify RED**

Run: `python3 -m unittest tests.test_check_streams tests.test_playlists -v`

Expected: failures only for the new group and generation checks.

**Step 3: Make minimal checker/workflow changes**

Add `China Recommended` to accepted metadata groups. Add read-only generation
consistency steps to the existing workflow while keeping the live command pointed
only at `playlists/news.m3u`. Preserve all existing workflow usage and outputs.

**Step 4: Run focused tests to verify GREEN**

Expected: PASS.

### Task 6: Document profiles, sources, and imports

**Files:**
- Modify: `README.md`
- Modify: `docs/sources.md`
- Modify: `tests/test_playlists.py`

**Step 1: Write failing documentation assertions**

Require the China Raw URL, Global-versus-China explanation, catalog SSOT policy,
manual compatibility-report link, generation/check commands, Favorites-CN URL,
and official CNA/CGTN provenance descriptions. Keep all existing Raw/CDN URLs.

**Step 2: Run tests to verify RED**

Run: `python3 -m unittest tests.test_playlists -v`

Expected: README/source documentation failures.

**Step 3: Update documentation**

Explain that global is optimized for overseas reachability and China is a small
manual residential-broadband profile. Document the exact Raw URL, Favorites-CN,
manual record limitations, single-source generation, and no automatic deletion.
Move CNA from the rejected historical CloudFront candidate to the included
official Brightcove delivery section; document CGTN's official JSON chain.

**Step 4: Run focused tests to verify GREEN**

Expected: PASS.

### Task 7: Verify live sources, amend, push, and validate remotely

**Files:**
- Verify: all modified files
- Do not track: `task_plan.md`, `findings.md`, `progress.md`

**Step 1: Run complete deterministic verification**

```bash
python3 -W error::ResourceWarning -m unittest discover -s tests -v
python3 scripts/generate_playlists.py --check
python3 scripts/generate_favorites.py --check
python3 scripts/generate_favorites_cn.py --check
python3 scripts/generate_epg.py --check
git diff --check
```

Expected: all pass with no warnings.

**Step 2: Prove backward compatibility**

Compare both global SHA-256 values with the approved digest and verify the old
Raw/CDN mirror still matches.

**Step 3: Run strict live validation for China release**

Run `scripts/check_streams.py playlists/news-cn.m3u --timeout 15` and require all
four channels to pass Master/Variant/first-segment checks. This is a release gate,
not a China experience score and is not added to the scheduled Global Health job.

**Step 4: Review the complete diff**

Use the requesting-code-review and verification-before-completion skills. Fix
every critical/important finding with a regression test.

**Step 5: Remove scratch planning files and amend**

Amend the design commit so the final commit message is exactly:

`Add China optimized news playlist`

**Step 6: Push and remotely verify**

Push `main`, confirm the remote SHA, manually run the unchanged workflow, inspect
its artifact, and verify public global Raw/CDN equality plus the new China Raw
playlist.
