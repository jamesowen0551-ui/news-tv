import unittest
import xml.etree.ElementTree as ET
from pathlib import Path
from tempfile import TemporaryDirectory


ROOT = Path(__file__).resolve().parents[1]


class EpgGeneratorTests(unittest.TestCase):
    def _catalog(self):
        from scripts.channel_catalog import load_catalog_text

        return load_catalog_text(
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8")
        )

    def test_render_maps_every_catalog_channel_without_programmes(self):
        from scripts.generate_epg import render_epg

        catalog = self._catalog()
        document = ET.fromstring(render_epg(catalog))
        channels = document.findall("channel")

        self.assertEqual(
            [channel.attrib["id"] for channel in channels],
            [channel.tvg_id for channel in catalog.channels],
        )
        self.assertEqual(
            [channel.findtext("display-name") for channel in channels],
            [channel.tvg_name for channel in catalog.channels],
        )
        self.assertEqual(document.findall("programme"), [])

    def test_committed_epg_is_generated_from_catalog(self):
        from scripts.generate_epg import render_epg

        self.assertEqual(
            render_epg(self._catalog()).encode("utf-8"),
            (ROOT / "epg/epg.xml").read_bytes(),
        )

    def test_check_mode_detects_stale_output_without_writing(self):
        from scripts import generate_epg

        with TemporaryDirectory() as directory:
            output = Path(directory) / "epg.xml"
            args = [
                "--catalog",
                str(ROOT / "channels/catalog.json"),
                "--output",
                str(output),
            ]
            self.assertEqual(generate_epg.main(args), 0)
            self.assertEqual(output.stat().st_mode & 0o777, 0o644)
            self.assertEqual(generate_epg.main([*args, "--check"]), 0)

            output.write_text("stale\n", encoding="utf-8")
            self.assertEqual(generate_epg.main([*args, "--check"]), 1)
            self.assertEqual(output.read_text(encoding="utf-8"), "stale\n")


if __name__ == "__main__":
    unittest.main()
