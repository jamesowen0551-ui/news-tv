import json
import hashlib
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]
GLOBAL_IDS = [
    "BloombergTV.us",
    "SchwabNetwork.us",
    "CBSNews247.us",
    "NBCNewsNOW.us",
    "ScrippsNews.us",
    "SkyNews.uk",
    "DWEnglish.de",
    "NHKWorldJapan.jp",
    "EuronewsEnglish.fr",
    "AlJazeeraEnglish.qa",
]
CHINA_IDS = [
    "NHKWorldJapan.jp",
    "CNAEnglish.sg",
    "CGTNEnglish.cn",
    "SchwabNetwork.us",
]
CNA_OFFICIAL_HLS = (
    "https://mediacorp-nca-prod-videos-bclive.akamaized.net/6379472319112/"
    "ap-southeast-1/6057994443001/"
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJob3N0IjoicGE2ODB1LmVncmVzcy5wcHRpOHciLCJhY2NvdW50X2lkIjoiNjA1Nzk5NDQ0MzAwMSIsImVobiI6Im1lZGlhY29ycC1uY2EtcHJvZC12aWRlb3MtYmNsaXZlLmFrYW1haXplZC5uZXQiLCJpc3MiOiJibGl2ZS1wbGF5YmFjay1zb3VyY2UtYXBpIiwic3ViIjoicGF0aG1hcHRva2VuIiwiYXVkIjpbIjYwNTc5OTQ0NDMwMDEiXSwianRpIjoiNjM3OTQ3MjMxOTExMiJ9."
    "Cw77amOc6efNO32Sw9nD0SOhjQUc5ewKN8ZWJOPt15Y/playlist-hls.m3u8"
)


class CatalogValidationTests(unittest.TestCase):
    def _module(self):
        from scripts import channel_catalog

        return channel_catalog

    def _valid_document(self):
        return {
            "schema_version": 1,
            "epg_url": "https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml",
            "profiles": {
                "global": ["Example.us"],
                "china_optimized": ["Example.us"],
                "asia": ["Example.us"],
                "finance": [],
                "technology": [],
            },
            "channels": [
                {
                    "tvg_id": "Example.us",
                    "tvg_name": "Example News",
                    "url": "https://media.example/live/master.m3u8",
                    "global_group": "World News",
                    "official_page": "https://example.com/live",
                    "delivery_evidence": "Official player publishes media.example HLS.",
                }
            ],
        }

    def test_committed_catalog_has_unique_complete_profiles(self):
        module = self._module()
        path = ROOT / "channels/catalog.json"
        self.assertTrue(path.exists(), "channel catalog is missing")

        catalog = module.load_catalog_text(path.read_text(encoding="utf-8"))

        self.assertEqual(list(catalog.profiles["global"]), GLOBAL_IDS)
        self.assertEqual(list(catalog.profiles["china_optimized"]), CHINA_IDS)
        self.assertEqual(
            list(catalog.profiles["asia"]),
            ["NHKWorldJapan.jp", "CNAEnglish.sg", "CGTNEnglish.cn"],
        )
        self.assertEqual(
            list(catalog.profiles["finance"]),
            ["BloombergTV.us", "SchwabNetwork.us"],
        )
        self.assertEqual(list(catalog.profiles["technology"]), [])
        self.assertEqual(len(catalog.channels), 12)
        self.assertEqual(len({channel.tvg_id for channel in catalog.channels}), 12)
        self.assertEqual(catalog.channel_by_id("CNAEnglish.sg").tvg_name, "CNA English")
        self.assertEqual(catalog.channel_by_id("CNAEnglish.sg").url, CNA_OFFICIAL_HLS)
        self.assertEqual(catalog.channel_by_id("CGTNEnglish.cn").tvg_name, "CGTN English")
        raw_catalog = json.loads(path.read_text(encoding="utf-8"))
        self.assertTrue(
            all("profiles" not in channel for channel in raw_catalog["channels"])
        )

    def test_unknown_lookup_uses_exact_id_only(self):
        module = self._module()
        catalog = module.load_catalog_text(json.dumps(self._valid_document()))

        with self.assertRaisesRegex(ValueError, "unknown tvg-id.*Example"):
            catalog.channel_by_id("Example")

    def test_rejects_invalid_catalog_documents(self):
        module = self._module()
        cases = {}

        duplicate_id = self._valid_document()
        duplicate_id["channels"].append(dict(duplicate_id["channels"][0]))
        cases["duplicate tvg-id"] = duplicate_id

        duplicate_profile = self._valid_document()
        duplicate_profile["profiles"]["global"] = ["Example.us", "Example.us"]
        cases["duplicate profile tvg-id"] = duplicate_profile

        unknown_profile = self._valid_document()
        unknown_profile["profiles"]["global"] = ["Missing.us"]
        cases["unknown profile tvg-id"] = unknown_profile

        missing_name = self._valid_document()
        del missing_name["channels"][0]["tvg_name"]
        cases["missing channel field"] = missing_name

        http_url = self._valid_document()
        http_url["channels"][0]["url"] = "http://media.example/master.m3u8"
        cases["HTTPS"] = http_url

        query_url = self._valid_document()
        query_url["channels"][0]["url"] += "?token=temporary"
        cases["query parameters"] = query_url

        missing_evidence = self._valid_document()
        missing_evidence["channels"][0]["delivery_evidence"] = ""
        cases["delivery evidence"] = missing_evidence

        extra_field = self._valid_document()
        extra_field["channels"][0]["stream_backup"] = "https://unknown.example/live.m3u8"
        cases["unexpected channel field"] = extra_field

        for expected, document in cases.items():
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ValueError, expected
            ):
                module.load_catalog_text(json.dumps(document))


class PlaylistGenerationTests(unittest.TestCase):
    def _catalog(self):
        from scripts.channel_catalog import load_catalog_text

        return load_catalog_text(
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8")
        )

    def test_global_render_is_byte_identical_to_stable_release(self):
        from scripts.channel_catalog import render_profile

        rendered = render_profile(self._catalog(), "global")

        self.assertEqual(rendered.encode("utf-8"), (ROOT / "news.m3u").read_bytes())
        self.assertEqual(
            hashlib.sha256(rendered.encode("utf-8")).hexdigest(),
            "cdeabf21790e726bfb2e5cd85916a88432b86d53a53331acabe2249726aa0662",
        )

    def test_category_renders_are_byte_identical(self):
        from scripts.channel_catalog import render_global_group
        from scripts.generate_playlists import expected_outputs

        for group, relative_path in (
            ("Finance", "playlists/finance.m3u"),
            ("US News", "playlists/us-news.m3u"),
            ("World News", "playlists/world-news.m3u"),
        ):
            with self.subTest(group=group):
                self.assertEqual(
                    render_global_group(self._catalog(), group).encode("utf-8"),
                    (ROOT / relative_path).read_bytes(),
                )
        self.assertEqual(
            expected_outputs(self._catalog())["playlists/events.m3u"],
            '#EXTM3U x-tvg-url="https://raw.githubusercontent.com/jamesowen0551-ui/news-tv/main/epg/epg.xml"\n'
            "# Reserved for verified, time-bounded official event streams only.\n"
            "# Possible future coverage: FOMC, ECB, IMF, World Bank, NASA TV,\n"
            "# Apple Keynote, Google I/O, NVIDIA GTC, and OpenAI Event.\n",
        )

    def test_china_render_has_exact_order_metadata_and_catalog_urls(self):
        from scripts.channel_catalog import render_profile

        catalog = self._catalog()
        rendered = render_profile(
            catalog, "china_optimized", group_override="China Recommended"
        )
        channels = parse_m3u_text(rendered)

        self.assertEqual([channel.tvg_id for channel in channels], CHINA_IDS)
        for channel in channels:
            with self.subTest(channel=channel.name):
                fact = catalog.channel_by_id(channel.tvg_id)
                self.assertEqual(channel.tvg_name, fact.tvg_name)
                self.assertEqual(channel.name, fact.tvg_name)
                self.assertEqual(channel.url, fact.url)
                self.assertEqual(channel.group, "China Recommended")
                self.assertEqual(channel.logo, "")

        committed = (ROOT / "playlists/news-cn.m3u").read_bytes()
        self.assertEqual(rendered.encode("utf-8"), committed)
        self.assertEqual(
            hashlib.sha256(committed).hexdigest(),
            "80d9aa33f2807cda315e6417bd537f295989161612d5956147861157c6bb4074",
        )

    def test_generator_check_mode_detects_stale_outputs_without_writing(self):
        from scripts import generate_playlists

        with TemporaryDirectory() as directory:
            output_root = Path(directory)
            args = [
                "--catalog",
                str(ROOT / "channels/catalog.json"),
                "--root",
                str(output_root),
            ]
            self.assertEqual(generate_playlists.main(args), 0)
            global_output = output_root / "news.m3u"
            expected = global_output.read_bytes()
            self.assertEqual(global_output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(generate_playlists.main([*args, "--check"]), 0)

            global_output.write_text("stale\n", encoding="utf-8")
            self.assertEqual(generate_playlists.main([*args, "--check"]), 1)
            self.assertEqual(global_output.read_text(encoding="utf-8"), "stale\n")
            self.assertNotEqual(global_output.read_bytes(), expected)

    def test_china_only_generator_uses_the_catalog(self):
        from scripts import generate_china_playlist

        with TemporaryDirectory() as directory:
            output = Path(directory) / "news-cn.m3u"
            args = [
                "--catalog",
                str(ROOT / "channels/catalog.json"),
                "--output",
                str(output),
            ]
            self.assertEqual(generate_china_playlist.main(args), 0)
            channels = parse_m3u_text(output.read_text(encoding="utf-8"))
            self.assertEqual([channel.tvg_id for channel in channels], CHINA_IDS)
            self.assertEqual(generate_china_playlist.main([*args, "--check"]), 0)


if __name__ == "__main__":
    unittest.main()
