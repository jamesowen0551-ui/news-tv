import threading
import time
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from scripts.check_streams import (
    Channel,
    parse_master_manifest,
    parse_media_manifest,
    parse_m3u_text,
    render_markdown,
    validate_channel,
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


class _HlsHandler(BaseHTTPRequestHandler):
    seen_user_agents: list[str] = []
    routes: dict[str, tuple[int, str, bytes, dict[str, str]]] = {}

    def do_GET(self):
        type(self).seen_user_agents.append(self.headers.get("User-Agent", ""))
        status, content_type, body, headers = type(self).routes.get(
            self.path, (404, "text/plain", b"not found", {})
        )
        delay = headers.pop("X-Test-Delay", None)
        if delay:
            time.sleep(float(delay))
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in headers.items():
            self.send_header(name, value)
        self.end_headers()
        try:
            self.wfile.write(body)
        except BrokenPipeError:
            pass

    def log_message(self, format, *args):
        pass


class NetworkValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _HlsHandler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def setUp(self):
        _HlsHandler.seen_user_agents = []
        _HlsHandler.routes = {
            "/start.m3u8": (302, "text/plain", b"", {"Location": "/master.m3u8"}),
            "/master.m3u8": (
                200,
                "application/vnd.apple.mpegurl",
                b'''#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360
/low/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=4500000,RESOLUTION=1920x1080
/high/index.m3u8
''',
                {},
            ),
            "/fallback.m3u8": (
                200,
                "application/vnd.apple.mpegurl",
                b'''#EXTM3U
#EXT-X-STREAM-INF:BANDWIDTH=4500000,RESOLUTION=1920x1080
/missing/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=4500000,RESOLUTION=1920x1080
/high/index.m3u8
#EXT-X-STREAM-INF:BANDWIDTH=900000,RESOLUTION=640x360
/low/index.m3u8
''',
                {},
            ),
            "/high/index.m3u8": (
                200,
                "application/vnd.apple.mpegurl",
                b"#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nfirst.ts\n",
                {},
            ),
            "/high/first.ts": (200, "video/mp2t", b"video-segment", {}),
            "/html": (200, "text/html", b"<!doctype html><html>player</html>", {}),
            "/direct.m3u8": (
                200,
                "application/vnd.apple.mpegurl",
                b"#EXTM3U\n#EXTINF:6,\nfirst.ts\n",
                {},
            ),
            "/slow.m3u8": (
                200,
                "application/vnd.apple.mpegurl",
                b"#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000000\nvariant.m3u8\n",
                {"X-Test-Delay": "0.2"},
            ),
        }

    def test_follows_redirect_and_probes_highest_variant_first_segment(self):
        channel = Channel("Example News", f"{self.base_url}/start.m3u8", "World News")

        result = validate_channel(channel, timeout=2)

        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.redirects, 1)
        self.assertEqual(result.variant_count, 2)
        self.assertEqual(result.resolution, "1920x1080")
        self.assertEqual(result.bandwidth, 4_500_000)
        self.assertEqual(result.segment_url, f"{self.base_url}/high/first.ts")
        self.assertEqual(result.score, 5)
        self.assertTrue(all("news-tv-stream-checker" in ua for ua in _HlsHandler.seen_user_agents))

    def test_rejects_html_even_when_status_is_200(self):
        result = validate_channel(Channel("Fake", f"{self.base_url}/html"), timeout=2)

        self.assertFalse(result.ok)
        self.assertIn("HTML", result.error)

    def test_falls_back_when_the_first_highest_bitrate_variant_is_broken(self):
        result = validate_channel(
            Channel("Redundant", f"{self.base_url}/fallback.m3u8"), timeout=2
        )

        self.assertTrue(result.ok, result.error)
        self.assertEqual(result.variant_count, 3)
        self.assertEqual(result.bandwidth, 4_500_000)
        self.assertEqual(result.segment_url, f"{self.base_url}/high/first.ts")

    def test_requires_a_variant_playlist(self):
        result = validate_channel(
            Channel("Direct Media", f"{self.base_url}/direct.m3u8"), timeout=2
        )

        self.assertFalse(result.ok)
        self.assertIn("STREAM-INF", result.error)

    def test_reports_request_timeout(self):
        result = validate_channel(
            Channel("Slow", f"{self.base_url}/slow.m3u8"), timeout=0.05
        )

        self.assertFalse(result.ok)
        self.assertIn("timed out", result.error.lower())

    def test_markdown_report_contains_metrics_and_failure_reason(self):
        good = validate_channel(
            Channel("Good | News", f"{self.base_url}/start.m3u8", "US News"), timeout=2
        )
        bad = validate_channel(Channel("Bad", f"{self.base_url}/html", "World News"), timeout=2)

        report = render_markdown([good, bad], generated_at="2026-08-01T00:00:00Z")

        self.assertIn("# Stream Health Report", report)
        self.assertIn("Good \\| News", report)
        self.assertIn("1920x1080", report)
        self.assertIn("4.50 Mbps", report)
        self.assertIn("| HTTP | Content-Type |", report)
        self.assertIn("application/vnd.apple.mpegurl", report)
        self.assertIn("★★★★★", report)
        self.assertIn("HTML", report)
        self.assertIn("1 passed, 1 failed", report)


if __name__ == "__main__":
    unittest.main()
