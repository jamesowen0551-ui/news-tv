import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]
CHINA_IDS = [
    "NHKWorldJapan.jp",
    "CNAEnglish.sg",
    "CGTNEnglish.cn",
    "SchwabNetwork.us",
]


class ChinaFavoritesGeneratorTests(unittest.TestCase):
    def test_committed_config_generates_exact_catalog_entries_in_order(self):
        from scripts.generate_favorites import generate_favorites_text

        config = ROOT / "config/favorites-cn.yaml"
        self.assertTrue(config.exists(), "China Favorites config is missing")
        generated = generate_favorites_text(
            config.read_text(encoding="utf-8"),
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8"),
            group_override="China Recommended",
        )
        channels = parse_m3u_text(generated)

        self.assertEqual([channel.tvg_id for channel in channels], CHINA_IDS)
        self.assertTrue(all(channel.group == "China Recommended" for channel in channels))
        self.assertEqual(
            generated.encode("utf-8"),
            (ROOT / "playlists/favorites-cn.m3u").read_bytes(),
        )

    def test_cli_generates_and_checks_without_fuzzy_matching(self):
        from scripts import generate_favorites_cn

        with TemporaryDirectory() as directory:
            output = Path(directory) / "favorites-cn.m3u"
            args = [
                "--config",
                str(ROOT / "config/favorites-cn.yaml"),
                "--catalog",
                str(ROOT / "channels/catalog.json"),
                "--output",
                str(output),
            ]
            self.assertEqual(generate_favorites_cn.main(args), 0)
            self.assertEqual(
                [channel.tvg_id for channel in parse_m3u_text(output.read_text())],
                CHINA_IDS,
            )
            self.assertEqual(generate_favorites_cn.main([*args, "--check"]), 0)

            bad_config = Path(directory) / "bad.yaml"
            bad_config.write_text("favorites:\n  - CNAEnglish\n", encoding="utf-8")
            self.assertEqual(
                generate_favorites_cn.main(
                    [
                        "--config",
                        str(bad_config),
                        "--catalog",
                        str(ROOT / "channels/catalog.json"),
                        "--output",
                        str(output),
                    ]
                ),
                1,
            )


if __name__ == "__main__":
    unittest.main()
