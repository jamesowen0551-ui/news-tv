import importlib
import importlib.util
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer


class _MirrorHandler(BaseHTTPRequestHandler):
    routes: dict[str, tuple[int, bytes]] = {}

    def do_GET(self):
        status, body = type(self).routes.get(self.path, (404, b"not found"))
        self.send_response(status)
        self.send_header("Content-Type", "application/vnd.apple.mpegurl")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):
        pass


class MirrorCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), _MirrorHandler)
        cls.base_url = f"http://127.0.0.1:{cls.server.server_port}"
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def _module(self):
        spec = importlib.util.find_spec("scripts.check_mirrors")
        self.assertIsNotNone(spec, "mirror checker module is missing")
        return importlib.import_module("scripts.check_mirrors")

    def test_identical_mirrors_return_matching_sha256(self):
        module = self._module()
        body = b"#EXTM3U\n# test playlist\n"
        _MirrorHandler.routes = {"/primary": (200, body), "/cdn": (200, body)}

        result = module.check_mirrors(
            f"{self.base_url}/primary", f"{self.base_url}/cdn", timeout=2
        )

        self.assertTrue(result.equal)
        self.assertEqual(result.primary_sha256, result.cdn_sha256)
        self.assertEqual(result.byte_count, len(body))

    def test_mismatched_mirrors_raise_a_clear_error(self):
        module = self._module()
        _MirrorHandler.routes = {
            "/primary": (200, b"primary"),
            "/cdn": (200, b"different"),
        }

        with self.assertRaisesRegex(module.MirrorMismatchError, "SHA-256 mismatch"):
            module.check_mirrors(
                f"{self.base_url}/primary", f"{self.base_url}/cdn", timeout=2
            )

    def test_cli_returns_nonzero_for_http_failure(self):
        module = self._module()
        _MirrorHandler.routes = {"/primary": (200, b"playlist")}

        exit_code = module.main(
            [
                "--primary-url",
                f"{self.base_url}/primary",
                "--cdn-url",
                f"{self.base_url}/missing",
                "--timeout",
                "2",
            ]
        )

        self.assertEqual(exit_code, 1)


if __name__ == "__main__":
    unittest.main()
