import tempfile
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from server.api.frontend import mount_frontend


class FrontendTests(unittest.TestCase):
    def setUp(self):
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        dist = Path(folder.name)
        for file in ("index.html", "benchmarks/index.html", "methodology/index.html", "assets/app.js", "licenses/icons.txt"):
            (dist / file).parent.mkdir(parents=True, exist_ok=True)
            (dist / file).write_text(file, encoding="utf-8")
        app = FastAPI()
        app.get("/health")(lambda: {"status": "ok"})
        mount_frontend(app, dist)
        self.client = TestClient(app)

    def test_pages(self):
        for route, file in (("/", "index.html"), ("/benchmarks", "benchmarks/index.html"), ("/methodology", "methodology/index.html")):
            self.assertEqual(self.client.get(route).text, file)

    def test_assets(self):
        self.assertEqual(self.client.get("/assets/app.js").status_code, 200)
        self.assertEqual(self.client.get("/licenses/icons.txt").status_code, 200)

    def test_api_untouched(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/unknown").status_code, 404)

    def test_without_build(self):
        app = FastAPI()
        mount_frontend(app, Path("missing"))
        self.assertEqual(TestClient(app).get("/").status_code, 404)


if __name__ == "__main__":
    unittest.main()
