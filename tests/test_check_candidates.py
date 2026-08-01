import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from scripts import check_streams
from scripts.candidate_catalog import load_candidate_pool_text
from scripts.channel_catalog import load_catalog_text


ROOT = Path(__file__).resolve().parents[1]


class CandidateCheckerTests(unittest.TestCase):
    def _catalog(self):
        return load_catalog_text(
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8")
        )

    def _pool(self):
        return load_candidate_pool_text(
            (ROOT / "channels/candidates.json").read_text(encoding="utf-8"),
            self._catalog(),
        )

    def test_checker_imports_the_existing_strict_validator(self):
        from scripts import check_candidates

        self.assertIs(check_candidates.validate_channel, check_streams.validate_channel)
        self.assertIs(check_candidates.render_markdown, check_streams.render_markdown)

    def test_candidates_are_adapted_to_existing_channel_model_in_order(self):
        from scripts.check_candidates import candidate_channels

        channels = candidate_channels(self._pool())

        self.assertEqual([channel.tvg_id for channel in channels], ["ArirangTV.kr"])
        self.assertEqual(channels[0].name, "Arirang TV")
        self.assertEqual(channels[0].tvg_name, "Arirang TV")
        self.assertEqual(channels[0].group, "Asia")
        self.assertEqual(channels[0].source, "https://www.arirang.com/live")

    def test_run_checks_calls_shared_validator_and_propagates_timeout(self):
        from scripts import check_candidates

        calls = []

        def fake_validator(channel, timeout):
            calls.append((channel.tvg_id, timeout))
            return check_streams.ValidationResult(channel=channel, ok=True)

        with patch.object(check_candidates, "validate_channel", fake_validator):
            results = check_candidates.run_checks(self._pool(), timeout=7.5)

        self.assertEqual(calls, [("ArirangTV.kr", 7.5)])
        self.assertEqual([result.channel.tvg_id for result in results], ["ArirangTV.kr"])

    def test_cli_writes_candidate_markdown_without_modifying_inputs_or_playlists(self):
        from scripts import check_candidates

        protected = [
            ROOT / "news.m3u",
            ROOT / "playlists/news.m3u",
            ROOT / "playlists/news-cn.m3u",
            ROOT / "channels/catalog.json",
            ROOT / "channels/candidates.json",
        ]
        before = {path: path.read_bytes() for path in protected}

        def fake_validator(channel, timeout):
            return check_streams.ValidationResult(
                channel=channel,
                ok=True,
                http_status=200,
                content_type="application/vnd.apple.mpegurl",
                manifest_ok=True,
                variant_ok=True,
                segment_ok=True,
                variant_count=3,
                resolution="1280x720",
                bandwidth=2_000_000,
                latency_ms=500,
                score=5,
            )

        with TemporaryDirectory() as directory:
            report = Path(directory) / "candidate-report.md"
            with patch.object(check_candidates, "validate_channel", fake_validator):
                exit_code = check_candidates.main(
                    ["--timeout", "4", "--report", str(report)]
                )
            text = report.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 0)
        self.assertIn("# Candidate Technical Report", text)
        self.assertIn("Arirang TV", text)
        self.assertIn("technical PASS does not approve", text)
        self.assertEqual({path: path.read_bytes() for path in protected}, before)

    def test_cli_returns_nonzero_when_the_shared_validator_fails(self):
        from scripts import check_candidates

        def fake_validator(channel, timeout):
            return check_streams.ValidationResult(
                channel=channel,
                ok=False,
                error="HLS manifest has no #EXT-X-STREAM-INF variant playlist",
            )

        with TemporaryDirectory() as directory:
            report = Path(directory) / "candidate-report.md"
            with patch.object(check_candidates, "validate_channel", fake_validator):
                exit_code = check_candidates.main(["--report", str(report)])
            text = report.read_text(encoding="utf-8")

        self.assertEqual(exit_code, 1)
        self.assertIn("FAIL", text)
        self.assertIn("no #EXT-X-STREAM-INF", text)


if __name__ == "__main__":
    unittest.main()
