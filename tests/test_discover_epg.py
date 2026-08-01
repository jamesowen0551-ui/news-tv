import contextlib
import importlib
import importlib.util
import io
import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class EpgDiscoveryTests(unittest.TestCase):
    def _module(self):
        spec = importlib.util.find_spec("scripts.discover_epg")
        self.assertIsNotNone(spec, "EPG discovery module is missing")
        return importlib.import_module("scripts.discover_epg")

    def test_known_ids_return_empty_confirmed_candidate_lists_in_input_order(self):
        module = self._module()
        results = module.discover_candidates(
            ["SkyNews.uk", "CNAEnglish.sg", "CGTNEnglish.cn"],
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8"),
        )

        self.assertEqual(
            [result["tvg_id"] for result in results],
            ["SkyNews.uk", "CNAEnglish.sg", "CGTNEnglish.cn"],
        )
        for result in results:
            self.assertEqual(result["status"], "no-confirmed-source")
            self.assertEqual(result["candidates"], [])

    def test_unknown_id_is_rejected_without_alias_matching(self):
        module = self._module()
        with self.assertRaisesRegex(ValueError, "unknown tvg-id.*SkyNews"):
            module.discover_candidates(
                ["SkyNews"],
                (ROOT / "channels/catalog.json").read_text(encoding="utf-8"),
            )

    def test_cli_outputs_json_and_does_not_modify_epg(self):
        module = self._module()
        epg_path = ROOT / "epg/epg.xml"
        before = epg_path.read_bytes()
        output = io.StringIO()

        with contextlib.redirect_stdout(output):
            exit_code = module.main(
                [
                    "SkyNews.uk",
                    "NHKWorldJapan.jp",
                    "--catalog",
                    str(ROOT / "channels/catalog.json"),
                ]
            )

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            [item["tvg_id"] for item in json.loads(output.getvalue())],
            ["SkyNews.uk", "NHKWorldJapan.jp"],
        )
        self.assertEqual(epg_path.read_bytes(), before)


if __name__ == "__main__":
    unittest.main()
