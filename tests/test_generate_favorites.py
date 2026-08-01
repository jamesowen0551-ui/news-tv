import importlib
import importlib.util
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from scripts.check_streams import parse_m3u_text


ROOT = Path(__file__).resolve().parents[1]


class FavoritesGeneratorTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.find_spec("scripts.generate_favorites")
        self.assertIsNotNone(spec, "favorites generator module is missing")
        return importlib.import_module("scripts.generate_favorites")

    def test_yaml_order_is_preserved_in_generated_playlist(self):
        module = self._module()
        config = """favorites:
  - SkyNews.uk
  - BloombergTV.us
"""
        catalog = (ROOT / "channels/catalog.json").read_text(encoding="utf-8")

        generated = module.generate_favorites_text(config, catalog)
        channels = parse_m3u_text(generated)

        self.assertEqual(
            [channel.tvg_id for channel in channels],
            ["SkyNews.uk", "BloombergTV.us"],
        )

    def test_unknown_id_is_rejected_without_fuzzy_matching(self):
        module = self._module()
        catalog = (ROOT / "channels/catalog.json").read_text(encoding="utf-8")

        with self.assertRaisesRegex(ValueError, "not found.*BloombergTV"):
            module.generate_favorites_text(
                "favorites:\n  - BloombergTV\n", catalog
            )

    def test_duplicate_ids_urls_and_extra_keys_are_rejected(self):
        module = self._module()
        invalid_configs = {
            "duplicate": "favorites:\n  - SkyNews.uk\n  - SkyNews.uk\n",
            "URL": "favorites:\n  - https://example.com/live.m3u8\n",
            "unsupported": "favorites:\n  - SkyNews.uk\nstreams:\n  - anything\n",
        }
        for expected, config in invalid_configs.items():
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ValueError, expected
            ):
                module.parse_favorites_config(config)

    def test_check_mode_detects_a_stale_output_without_writing(self):
        module = self._module()
        with TemporaryDirectory() as directory:
            root = Path(directory)
            config = root / "favorites.yaml"
            catalog = root / "catalog.json"
            output = root / "favorites.m3u"
            config.write_text("favorites:\n  - BloombergTV.us\n", encoding="utf-8")
            catalog.write_bytes((ROOT / "channels/catalog.json").read_bytes())

            self.assertEqual(
                module.main(
                    [
                        "--config",
                        str(config),
                        "--catalog",
                        str(catalog),
                        "--output",
                        str(output),
                    ]
                ),
                0,
            )
            expected = output.read_bytes()
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(
                module.main(
                    [
                        "--config",
                        str(config),
                        "--catalog",
                        str(catalog),
                        "--output",
                        str(output),
                        "--check",
                    ]
                ),
                0,
            )
            output.write_text("stale\n", encoding="utf-8")
            self.assertEqual(
                module.main(
                    [
                        "--config",
                        str(config),
                        "--catalog",
                        str(catalog),
                        "--output",
                        str(output),
                        "--check",
                    ]
                ),
                1,
            )
            self.assertEqual(output.read_text(encoding="utf-8"), "stale\n")
            self.assertNotEqual(output.read_bytes(), expected)

    def test_committed_config_generates_the_committed_playlist(self):
        module = self._module()
        config = ROOT / "config/favorites.yaml"
        self.assertTrue(config.exists(), "favorites config is missing")

        generated = module.generate_favorites_text(
            config.read_text(encoding="utf-8"),
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8"),
        )

        self.assertEqual(
            generated.encode("utf-8"),
            (ROOT / "playlists/favorites.m3u").read_bytes(),
        )

    def test_generated_urls_come_only_from_catalog(self):
        module = self._module()
        from scripts.channel_catalog import load_catalog_text

        catalog_text = (ROOT / "channels/catalog.json").read_text(encoding="utf-8")
        catalog = load_catalog_text(catalog_text)
        generated = module.generate_favorites_text(
            (ROOT / "config/favorites.yaml").read_text(encoding="utf-8"),
            catalog_text,
        )

        for channel in parse_m3u_text(generated):
            self.assertEqual(channel.url, catalog.channel_by_id(channel.tvg_id).url)


if __name__ == "__main__":
    unittest.main()
