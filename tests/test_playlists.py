import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

from scripts.check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]
EPG_URL = "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml"
FAVORITES = [
    "Bloomberg TV",
    "Sky News",
    "NHK World-Japan",
    "DW English",
    "CBS News 24/7",
]
EXPECTED_TVG_IDS = {
    "Bloomberg TV": "BloombergTV.us",
    "Schwab Network": "SchwabNetwork.us",
    "CBS News 24/7": "CBSNews247.us",
    "NBC News NOW": "NBCNewsNOW.us",
    "Scripps News": "ScrippsNews.us",
    "Sky News": "SkyNews.uk",
    "DW English": "DWEnglish.de",
    "NHK World-Japan": "NHKWorldJapan.jp",
    "Euronews English": "EuronewsEnglish.fr",
    "Al Jazeera English": "AlJazeeraEnglish.qa",
}


class PublishedPlaylistTests(unittest.TestCase):
    @staticmethod
    def _entry(channel):
        return (
            channel.name,
            channel.url,
            channel.group,
            channel.tvg_id,
            channel.tvg_name,
            channel.logo,
        )

    def _channels(self, relative_path: str):
        path = ROOT / relative_path
        self.assertTrue(path.exists(), f"missing playlist: {relative_path}")
        return parse_m3u_text(path.read_text(encoding="utf-8"), source=relative_path)

    def _header(self, relative_path: str):
        path = ROOT / relative_path
        self.assertTrue(path.exists(), f"missing playlist: {relative_path}")
        return path.read_text(encoding="utf-8").splitlines()[0]

    def test_canonical_and_compatibility_playlists_are_identical(self):
        canonical = ROOT / "playlists/news.m3u"
        self.assertTrue(canonical.exists(), "missing canonical playlist")
        self.assertEqual((ROOT / "news.m3u").read_bytes(), canonical.read_bytes())

    def test_combined_playlist_matches_category_union(self):
        combined = self._channels("playlists/news.m3u")
        category_channels = []
        for path in (
            "playlists/finance.m3u",
            "playlists/us-news.m3u",
            "playlists/world-news.m3u",
        ):
            category_channels.extend(self._channels(path))

        combined_entries = {self._entry(channel) for channel in combined}
        category_entries = {self._entry(channel) for channel in category_channels}
        self.assertEqual(combined_entries, category_entries)
        self.assertEqual(len(combined), len(combined_entries), "combined playlist has duplicates")

    def test_categories_and_urls_follow_release_policy(self):
        expected_groups = {"Finance", "US News", "World News"}
        channels = self._channels("playlists/news.m3u")

        self.assertEqual({channel.group for channel in channels}, expected_groups)
        for channel in channels:
            with self.subTest(channel=channel.name):
                self.assertTrue(channel.url.startswith("https://"))
                self.assertNotIn("?", channel.url, "temporary or tracking query parameters are forbidden")

    def test_published_channels_have_complete_unique_metadata(self):
        channels = self._channels("playlists/news.m3u")

        self.assertEqual(len({channel.tvg_id for channel in channels}), len(channels))
        for channel in channels:
            with self.subTest(channel=channel.name):
                self.assertTrue(channel.tvg_id)
                self.assertEqual(getattr(channel, "tvg_name", None), channel.name)
                self.assertIn(channel.group, {"Finance", "US News", "World News"})
                self.assertEqual(channel.logo, "", "logos require confirmed usage permission")
        self.assertEqual(
            {channel.name: channel.tvg_id for channel in channels}, EXPECTED_TVG_IDS
        )

    def test_published_playlists_reference_the_epg(self):
        paths = (
            "news.m3u",
            "playlists/news.m3u",
            "playlists/finance.m3u",
            "playlists/us-news.m3u",
            "playlists/world-news.m3u",
            "playlists/favorites.m3u",
            "playlists/events.m3u",
        )
        for path in paths:
            with self.subTest(path=path):
                self.assertEqual(self._header(path), f'#EXTM3U x-tvg-url="{EPG_URL}"')

    def test_favorites_have_the_required_order(self):
        combined = {
            channel.name: self._entry(channel)
            for channel in self._channels("playlists/news.m3u")
        }
        favorites = self._channels("playlists/favorites.m3u")

        self.assertEqual([channel.name for channel in favorites], FAVORITES)
        self.assertEqual(
            [self._entry(channel) for channel in favorites],
            [combined[name] for name in FAVORITES],
        )

    def test_epg_maps_all_channels_without_fake_programmes(self):
        epg_path = ROOT / "epg/epg.xml"
        self.assertTrue(epg_path.exists(), "missing XMLTV EPG framework")
        epg_root = ET.parse(epg_path).getroot()
        channels = self._channels("playlists/news.m3u")
        expected = {channel.tvg_id: channel.name for channel in channels}
        actual = {
            element.attrib["id"]: element.findtext("display-name")
            for element in epg_root.findall("channel")
        }

        self.assertEqual(epg_root.tag, "tv")
        self.assertEqual(actual, expected)
        self.assertEqual(epg_root.findall("programme"), [])

    def test_workflow_keeps_entries_and_checks_canonical_playlist(self):
        workflow = (ROOT / ".github/workflows/check-streams.yml").read_text(
            encoding="utf-8"
        )

        self.assertIn("schedule:", workflow)
        self.assertIn("name: Check news streams", workflow)
        self.assertIn('cron: "0 20 * * *"', workflow)
        self.assertIn("workflow_dispatch:", workflow)
        self.assertIn("scripts/check_streams.py playlists/news.m3u", workflow)
        self.assertIn("upload-artifact@v4", workflow)
        self.assertIn("python3 scripts/generate_favorites.py --check", workflow)
        self.assertIn("python3 scripts/check_mirrors.py", workflow)
        self.assertIn("reports/health-report.md", workflow)
        self.assertIn("reports/stream-report.md", workflow)
        self.assertIn("name: stream-health-report", workflow)
        self.assertIn(
            "- name: Check GitHub Raw and jsDelivr mirror\n"
            "        if: always()",
            workflow,
        )
        self.assertIn(
            "if: always() && (steps.stream_check.outcome == 'failure'",
            workflow,
        )

    def test_readme_documents_new_and_legacy_urls(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        urls = (
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/news.m3u",
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/news.m3u",
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/favorites.m3u",
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/finance.m3u",
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/us-news.m3u",
            "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/playlists/world-news.m3u",
            EPG_URL,
        )
        for url in urls:
            with self.subTest(url=url):
                self.assertIn(url, readme)
        for player in (
            "Sony Android TV",
            "TiviMate",
            "Televizo",
            "Sparkle TV",
            "OTT Navigator",
        ):
            with self.subTest(player=player):
                self.assertIn(player, readme)
        for maintenance_item in (
            "https://cdn.jsdelivr.net/gh/jamesowen0551-ui/news-tv@main/news.m3u",
            "config/favorites.yaml",
            "scripts/generate_favorites.py",
            "scripts/discover_epg.py",
            "reports/health-report.md",
            "GitHub Raw",
            "jsDelivr",
        ):
            with self.subTest(maintenance_item=maintenance_item):
                self.assertIn(maintenance_item, readme)

    def test_reports_directory_is_preserved_without_tracking_reports(self):
        self.assertTrue(
            (ROOT / "reports/.gitkeep").is_file(),
            "reports directory must survive a fresh clone",
        )

    def test_forbidden_pay_tv_channels_are_absent(self):
        names = {
            channel.name.casefold()
            for channel in self._channels("playlists/news.m3u")
        }
        for forbidden in ("CNN", "CNBC", "BBC News", "Fox News"):
            self.assertNotIn(forbidden.casefold(), names)

    def test_events_playlist_is_reserved_and_empty(self):
        self.assertEqual(self._channels("playlists/events.m3u"), [])


if __name__ == "__main__":
    unittest.main()
