# IPTV Metadata, Favorites, and EPG Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Publish fully identified IPTV playlists, a five-channel favorites list, and an honest XMLTV framework while preserving every existing URL and live-stream validation behavior.

**Architecture:** `playlists/news.m3u` is the canonical combined playlist and root `news.m3u` is an exact compatibility mirror protected by tests. The checker parses and validates IPTV metadata before reusing the existing network probe. `epg/epg.xml` maps channel identities only and contains no fabricated programme data.

**Tech Stack:** Extended M3U, XMLTV, Python 3.12 standard library, `unittest`, GitHub Actions.

---

### Task 1: Lock the published playlist contract with failing tests

**Files:**
- Modify: `tests/test_playlists.py`

**Step 1: Write failing tests**

Add tests that assert:

```python
EPG_URL = "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml"

def test_canonical_and_compatibility_playlists_are_identical(self):
    self.assertEqual(
        (ROOT / "news.m3u").read_bytes(),
        (ROOT / "playlists/news.m3u").read_bytes(),
    )

def test_published_channels_have_complete_unique_metadata(self):
    channels = self._channels("playlists/news.m3u")
    self.assertEqual(len({channel.tvg_id for channel in channels}), len(channels))
    for channel in channels:
        self.assertTrue(channel.tvg_id)
        self.assertEqual(channel.tvg_name, channel.name)

def test_favorites_have_the_required_order(self):
    self.assertEqual(
        [channel.name for channel in self._channels("playlists/favorites.m3u")],
        ["Bloomberg TV", "Sky News", "NHK World-Japan", "DW English", "CBS News 24/7"],
    )
```

Also assert every published `#EXTM3U` header contains the exact EPG URL and all
category entries equal their canonical subsets.

**Step 2: Run tests to verify RED**

Run: `python3 -m unittest tests.test_playlists -v`

Expected: FAIL because `playlists/news.m3u`, `playlists/favorites.m3u`, header
metadata, and `Channel.tvg_name` do not exist.

### Task 2: Add metadata parsing and validation

**Files:**
- Modify: `tests/test_check_streams.py`
- Modify: `scripts/check_streams.py`

**Step 1: Write failing parser and validation tests**

Add assertions that a complete entry preserves `tvg-name`, and that published
metadata validation rejects missing `tvg-id`, missing/mismatched `tvg-name`,
missing/invalid `group-title`, duplicate IDs, missing/wrong `x-tvg-url`, and
non-HTTPS logo URLs when a logo is present.

**Step 2: Run the focused tests to verify RED**

Run: `python3 -m unittest tests.test_check_streams.PlaylistParsingTests -v`

Expected: FAIL because header metadata, `tvg_name`, and playlist validation are absent.

**Step 3: Implement the minimal parser model**

Extend `Channel` with `tvg_name`, introduce a parsed playlist container carrying
header attributes and channels, and keep `parse_m3u_text()` as a compatibility
wrapper returning only channels.

**Step 4: Implement metadata validation**

Require the exact raw EPG URL, unique non-empty IDs, `tvg-name == display name`,
approved groups, HTTPS stream URLs without query tokens, and HTTPS logos only
when `tvg-logo` exists. Raise a clear `ValueError` before any network check.

**Step 5: Run focused and full tests**

Run:

```bash
python3 -m unittest tests.test_check_streams.PlaylistParsingTests -v
python3 -m unittest discover -s tests -v
```

Expected: new parser tests pass; playlist contract tests remain RED until files are updated.

### Task 3: Publish canonical, compatibility, category, and favorites playlists

**Files:**
- Create: `playlists/news.m3u`
- Create: `playlists/favorites.m3u`
- Modify: `news.m3u`
- Modify: `playlists/finance.m3u`
- Modify: `playlists/us-news.m3u`
- Modify: `playlists/world-news.m3u`
- Modify: `playlists/events.m3u`

**Step 1: Add the common playlist header**

Use exactly:

```text
#EXTM3U x-tvg-url="https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml"
```

**Step 2: Add complete channel metadata**

For each existing entry add `tvg-name` and retain its existing `tvg-id`,
`group-title`, display name, and unchanged stream URL. Do not add `tvg-logo`.

**Step 3: Create the canonical and compatibility copies**

Make `playlists/news.m3u` canonical, then make root `news.m3u` byte-identical.

**Step 4: Create favorites**

Copy the five canonical entries in the approved priority order without changing
their categories or URLs.

**Step 5: Run playlist tests to verify GREEN**

Run: `python3 -m unittest tests.test_playlists -v`

Expected: PASS.

### Task 4: Add truthful XMLTV structure

**Files:**
- Modify: `tests/test_playlists.py`
- Create: `epg/epg.xml`

**Step 1: Write a failing EPG mapping test**

Parse XML with `xml.etree.ElementTree` and assert:

```python
self.assertEqual(epg_channel_ids, playlist_tvg_ids)
self.assertEqual(root.findall("programme"), [])
```

Also require a display name matching every playlist channel.

**Step 2: Run the focused test to verify RED**

Run: `python3 -m unittest tests.test_playlists.PublishedPlaylistTests.test_epg_maps_all_channels_without_fake_programmes -v`

Expected: FAIL because `epg/epg.xml` does not exist.

**Step 3: Create the minimal XMLTV file**

Create an XML declaration, a `<tv>` root identifying the project generator, and
ten `<channel id="...">` elements with English `<display-name>` children. Add no
`<programme>` elements.

**Step 4: Run playlist tests to verify GREEN**

Run: `python3 -m unittest tests.test_playlists -v`

Expected: PASS.

### Task 5: Preserve and update automation and documentation

**Files:**
- Modify: `tests/test_playlists.py`
- Modify: `.github/workflows/check-streams.yml`
- Modify: `README.md`
- Modify: `docs/sources.md`

**Step 1: Write failing workflow and README compatibility tests**

Assert the workflow still contains `schedule:` and `workflow_dispatch:`, validates
`playlists/news.m3u`, and the README contains all three URLs:

- root compatibility M3U;
- canonical M3U;
- EPG XML.

**Step 2: Run tests to verify RED**

Run: `python3 -m unittest tests.test_playlists -v`

Expected: FAIL because automation and README still reference only root `news.m3u`.

**Step 3: Update the workflow**

Change only the checker input to `playlists/news.m3u`. Preserve cron, manual
dispatch, report upload, failure propagation, permissions, and no-replacement policy.

**Step 4: Update documentation**

Lead with canonical M3U and EPG URLs, retain the legacy root URL as supported,
document Sony Android TV, TiviMate, Televizo, Sparkle TV, and OTT Navigator setup,
explain empty EPG programme data, favorites, metadata requirements, and logo omission.

**Step 5: Run tests to verify GREEN**

Run: `python3 -m unittest discover -s tests -v`

Expected: PASS with all existing HLS tests unchanged.

### Task 6: Final verification and release

**Files:**
- Update: `progress.md` and `task_plan.md` during verification (local working files)
- Amend: current release commit

**Step 1: Run deterministic tests with warnings as errors**

Run: `python3 -W error::ResourceWarning -m unittest discover -s tests -v`

Expected: all tests PASS with no warnings.

**Step 2: Run the real stream checker**

Run:

```bash
SSL_CERT_FILE=/private/etc/ssl/cert.pem python3 scripts/check_streams.py \
  playlists/news.m3u --timeout 15 --report reports/stream-report.md
```

Expected: all ten existing channels PASS. The explicit CA path is local-machine
configuration only and is not committed; GitHub Actions uses Python 3.12 on Ubuntu.

**Step 3: Verify compatibility and syntax**

Run byte comparison for both combined playlists, parse `epg/epg.xml`, run
`git diff --check`, and inspect the workflow.

**Step 4: Amend the release commit**

Remove local planning scratch files, stage all product/test/design/plan changes,
and amend using the required message:

```bash
git commit --amend -m "Add IPTV metadata, favorites playlist and EPG framework"
```

**Step 5: Push and verify remote artifacts**

Run `git push origin main`, verify local and remote SHA equality, and compare
remote Raw bytes for both M3U paths and the EPG path. Confirm the GitHub Actions
workflow remains active.
