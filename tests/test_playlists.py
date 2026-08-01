import unittest
from pathlib import Path

from scripts.check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]


class PublishedPlaylistTests(unittest.TestCase):
    def _channels(self, relative_path: str):
        path = ROOT / relative_path
        return parse_m3u_text(path.read_text(encoding="utf-8"), source=relative_path)

    def test_combined_playlist_matches_category_union(self):
        combined = self._channels("news.m3u")
        category_channels = []
        for path in (
            "playlists/finance.m3u",
            "playlists/us-news.m3u",
            "playlists/world-news.m3u",
        ):
            category_channels.extend(self._channels(path))

        combined_entries = {(channel.name, channel.url, channel.group) for channel in combined}
        category_entries = {
            (channel.name, channel.url, channel.group) for channel in category_channels
        }
        self.assertEqual(combined_entries, category_entries)
        self.assertEqual(len(combined), len(combined_entries), "combined playlist has duplicates")

    def test_categories_and_urls_follow_release_policy(self):
        expected_groups = {"Finance", "US News", "World News"}
        channels = self._channels("news.m3u")

        self.assertEqual({channel.group for channel in channels}, expected_groups)
        for channel in channels:
            with self.subTest(channel=channel.name):
                self.assertTrue(channel.url.startswith("https://"))
                self.assertNotIn("?", channel.url, "temporary or tracking query parameters are forbidden")

    def test_forbidden_pay_tv_channels_are_absent(self):
        names = {channel.name.casefold() for channel in self._channels("news.m3u")}
        for forbidden in ("CNN", "CNBC", "BBC News", "Fox News"):
            self.assertNotIn(forbidden.casefold(), names)

    def test_events_playlist_is_reserved_and_empty(self):
        self.assertEqual(self._channels("playlists/events.m3u"), [])


if __name__ == "__main__":
    unittest.main()
