import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class CandidateCatalogTests(unittest.TestCase):
    def _catalog(self):
        from scripts.channel_catalog import load_catalog_text

        return load_catalog_text(
            (ROOT / "channels/catalog.json").read_text(encoding="utf-8")
        )

    @staticmethod
    def _valid_document():
        return {
            "schema_version": 1,
            "candidates": [
                {
                    "id": "ExampleNews.xx",
                    "name": "Example News",
                    "country": "Exampleland",
                    "category": "Asia",
                    "official_url": "https://example.com/live",
                    "stream_url": "https://media.example.com/live/master.m3u8",
                    "source_notes": "The official player publishes this HLS URL.",
                    "status": "candidate",
                }
            ],
        }

    def test_committed_pool_contains_only_complete_release_gated_records(self):
        from scripts.candidate_catalog import load_candidate_pool_text

        path = ROOT / "channels/candidates.json"
        self.assertTrue(path.exists(), "candidate pool is missing")
        pool = load_candidate_pool_text(
            path.read_text(encoding="utf-8"), self._catalog()
        )

        self.assertEqual([candidate.id for candidate in pool.candidates], ["ArirangTV.kr"])
        candidate = pool.candidate_by_id("ArirangTV.kr")
        self.assertEqual(candidate.name, "Arirang TV")
        self.assertEqual(candidate.status, "candidate")
        self.assertEqual(candidate.category, "Asia")
        self.assertNotIn("?", candidate.stream_url)
        self.assertNotIn("#", candidate.stream_url)

    def test_approved_candidates_are_the_only_promotion_eligible_records(self):
        from scripts.candidate_catalog import load_candidate_pool_text

        document = self._valid_document()
        records = []
        for status in ("candidate", "testing", "approved", "rejected"):
            record = dict(document["candidates"][0])
            record["id"] = f"Example{status.title()}.xx"
            record["name"] = f"Example {status.title()}"
            record["stream_url"] = f"https://media.example.com/{status}/master.m3u8"
            record["status"] = status
            records.append(record)
        document["candidates"] = records

        pool = load_candidate_pool_text(json.dumps(document), self._catalog())

        self.assertEqual(
            [candidate.id for candidate in pool.approved_candidates()],
            ["ExampleApproved.xx"],
        )

    def test_unknown_lookup_uses_exact_id_only(self):
        from scripts.candidate_catalog import load_candidate_pool_text

        pool = load_candidate_pool_text(
            json.dumps(self._valid_document()), self._catalog()
        )

        with self.assertRaisesRegex(ValueError, "unknown candidate id.*ExampleNews"):
            pool.candidate_by_id("ExampleNews")

    def test_invalid_candidate_documents_are_rejected(self):
        from scripts.candidate_catalog import load_candidate_pool_text

        cases = {}

        wrong_schema = self._valid_document()
        wrong_schema["schema_version"] = 2
        cases["schema_version"] = wrong_schema

        duplicate = self._valid_document()
        duplicate["candidates"].append(dict(duplicate["candidates"][0]))
        cases["duplicate candidate id"] = duplicate

        catalog_collision = self._valid_document()
        catalog_collision["candidates"][0]["id"] = "NHKWorldJapan.jp"
        cases["collides with catalog"] = catalog_collision

        missing_field = self._valid_document()
        del missing_field["candidates"][0]["source_notes"]
        cases["missing candidate field"] = missing_field

        extra_field = self._valid_document()
        extra_field["candidates"][0]["logo"] = "https://example.com/logo.png"
        cases["unexpected candidate field"] = extra_field

        empty_stream = self._valid_document()
        empty_stream["candidates"][0]["stream_url"] = ""
        cases["stream URL"] = empty_stream

        http_official = self._valid_document()
        http_official["candidates"][0]["official_url"] = "http://example.com/live"
        cases["official URL must use HTTPS"] = http_official

        query_stream = self._valid_document()
        query_stream["candidates"][0]["stream_url"] += "?token=temporary"
        cases["query parameters"] = query_stream

        fragment_stream = self._valid_document()
        fragment_stream["candidates"][0]["stream_url"] += "#fragment"
        cases["fragment"] = fragment_stream

        bad_status = self._valid_document()
        bad_status["candidates"][0]["status"] = "published"
        cases["invalid candidate status"] = bad_status

        bad_root = self._valid_document()
        bad_root["channels"] = []
        cases["unexpected candidate pool field"] = bad_root

        for expected, document in cases.items():
            with self.subTest(expected=expected), self.assertRaisesRegex(
                ValueError, expected
            ):
                load_candidate_pool_text(json.dumps(document), self._catalog())


if __name__ == "__main__":
    unittest.main()
