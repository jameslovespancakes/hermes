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
        for file in (
            "index.html",
            "benchmarks/index.html",
            "methodology/index.html",
            "dashboard/index.html",
            "assets/app.js",
            "licenses/icons.txt",
        ):
            (dist / file).parent.mkdir(parents=True, exist_ok=True)
            (dist / file).write_text(file, encoding="utf-8")
        app = FastAPI()
        app.get("/health")(lambda: {"status": "ok"})
        mount_frontend(app, dist)
        self.client = TestClient(app)

    def test_pages(self):
        for route, file in (
            ("/", "index.html"),
            ("/benchmarks", "benchmarks/index.html"),
            ("/methodology", "methodology/index.html"),
            ("/dashboard", "dashboard/index.html"),
        ):
            self.assertEqual(self.client.get(route).text, file)

    def test_assets(self):
        self.assertEqual(self.client.get("/assets/app.js").status_code, 200)
        self.assertEqual(self.client.get("/licenses/icons.txt").status_code, 200)

    def test_api_untouched(self):
        self.assertEqual(self.client.get("/health").json(), {"status": "ok"})
        self.assertEqual(self.client.get("/unknown").status_code, 404)


class ContractTests(unittest.TestCase):
    """The dashboard's TypeScript types must match the API's response models field for field."""

    def test_dashboard_types_match_api(self):
        import re

        from server.api.schemas import CourierPosition, DataHealth, Overview, ParcelStatus, Route

        source = (Path(__file__).resolve().parents[2] / "app/src/pages/dashboard/api.ts").read_text(encoding="utf-8")
        interfaces = {name: body for name, body in re.findall(r"export interface (\w+) \{(.*?)\n\}", source, re.S)}
        for name, model in (("Parcel", ParcelStatus), ("Courier", CourierPosition), ("Overview", Overview), ("Route", Route)):
            fields = set(re.findall(r"^\s+(\w+):", interfaces[name], re.M))
            self.assertEqual(fields, set(model.model_fields), name)
        self.assertLessEqual(set(re.findall(r"^\s+(\w+):", interfaces["DataHealth"], re.M)), set(DataHealth.model_fields))


if __name__ == "__main__":
    unittest.main()
