import unittest

from scripts.check_streams import (
    parse_master_manifest,
    parse_media_manifest,
    parse_m3u_text,
)


class PlaylistParsingTests(unittest.TestCase):
    def test_parses_extended_m3u_channel_metadata(self):
        playlist = '''#EXTM3U
#EXTINF:-1 tvg-id="example" tvg-logo="https://img.example/logo.png" group-title="World News",Example News
https://media.example/live/master.m3u8
'''

        channels = parse_m3u_text(playlist, source="fixture.m3u")

        self.assertEqual(len(channels), 1)
        self.assertEqual(channels[0].name, "Example News")
        self.assertEqual(channels[0].group, "World News")
        self.assertEqual(channels[0].logo, "https://img.example/logo.png")
        self.assertEqual(channels[0].url, "https://media.example/live/master.m3u8")

    def test_master_manifest_requires_stream_inf_and_parses_quality(self):
        manifest = '''#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=2500000,AVERAGE-BANDWIDTH=2200000,RESOLUTION=1920x1080
1080/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=1200000,RESOLUTION=1280x720
720/index.m3u8
'''

        variants = parse_master_manifest(
            manifest, "https://media.example/live/master.m3u8"
        )

        self.assertEqual(len(variants), 2)
        self.assertEqual(variants[0].url, "https://media.example/live/1080/index.m3u8")
        self.assertEqual(variants[0].bandwidth, 2_500_000)
        self.assertEqual(variants[0].resolution, "1920x1080")

    def test_html_is_not_a_master_manifest(self):
        with self.assertRaisesRegex(ValueError, "HTML"):
            parse_master_manifest(
                "<!doctype html><html><body>player</body></html>",
                "https://example.com/live",
            )

    def test_media_manifest_resolves_first_segment(self):
        manifest = '''#EXTM3U
#EXT-X-TARGETDURATION:6
#EXTINF:6.0,
segments/first.ts
#EXTINF:6.0,
segments/second.ts
'''

        segments = parse_media_manifest(
            manifest, "https://media.example/live/720/index.m3u8"
        )

        self.assertEqual(segments[0], "https://media.example/live/720/segments/first.ts")

    def test_media_manifest_without_segments_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "segment"):
            parse_media_manifest(
                "#EXTM3U\n#EXT-X-TARGETDURATION:6\n",
                "https://media.example/live/index.m3u8",
            )


if __name__ == "__main__":
    unittest.main()
