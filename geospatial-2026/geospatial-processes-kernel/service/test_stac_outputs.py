"""Regression tests for workflow STAC Items and kernel catalog navigation."""

from __future__ import annotations

import importlib.util
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ["OSPD_API_TOKEN"] = "test-token"

import jsonschema
from fastapi.testclient import TestClient

import app as service


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class StacNavigationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.directory = tempfile.TemporaryDirectory()
        self.root = Path(self.directory.name)
        self.root_patch = patch.object(service, "JOB_ROOT", self.root)
        self.root_patch.start()
        self.addCleanup(self.directory.cleanup)
        self.addCleanup(self.root_patch.stop)
        self.client = TestClient(service.app)
        self.auth = {"Authorization": "Bearer test-token"}

    def create_job(self, process_id: str, names: list[str]) -> tuple[str, Path]:
        job = service.JOB_STORE.create(process_id, "cwltool", {})
        job_id = job["jobID"]
        output = self.root / job_id / "outputs"
        output.mkdir(parents=True)
        service.JOB_STORE.update(job_id, status="successful", returnCode=0, results={
            name: {
                "href": f"/jobs/{job_id}/artifacts/{name}",
                "type": "application/geo+json",
            }
            for name in names
        })
        for name in names:
            (output / name).write_text(json.dumps({
                "type": "Feature", "stac_version": "1.0.0", "id": job_id,
                "geometry": None, "properties": {"datetime": "2026-10-12T10:00:00Z"},
                "links": [
                    {"rel": "self", "href": name},
                    {"rel": "root", "href": "https://example.org/stale-catalog"},
                    {"rel": "derived_from", "href": "https://example.org/source"},
                ],
                "assets": {},
            }), encoding="utf-8")
        return job_id, output

    def test_all_served_item_types_have_resolvable_self_and_catalog_root(self) -> None:
        cases = {
            "sentinel2-hsi-pilot": ["stac_item.json"],
            "trash-hotspot-publish": ["cop_item.json"],
            "sentinel2-dji-imagery-harmonization": [
                "sentinel2_stac_item.json", "dji_stac_item.json",
            ],
        }
        for process, names in cases.items():
            if process not in service.PROCESSES:
                continue
            with self.subTest(process=process):
                job_id, output = self.create_job(process, names)
                for name in names:
                    original = (output / name).read_bytes()
                    response = self.client.get(f"/jobs/{job_id}/artifacts/{name}", headers=self.auth)
                    self.assertEqual(response.status_code, 200)
                    self.assertEqual(response.headers["content-type"], "application/geo+json")
                    item = response.json()
                    links = {link["rel"]: link["href"] for link in item["links"]}
                    self.assertEqual(len(item["links"]), 3)
                    self.assertEqual(links["derived_from"], "https://example.org/source")
                    self.assertEqual(
                        self.client.get(links["self"], headers=self.auth).json(), item,
                    )
                    catalog_response = self.client.get(links["root"], headers=self.auth)
                    self.assertEqual(catalog_response.status_code, 200)
                    catalog = catalog_response.json()
                    self.assertEqual(catalog["type"], "Catalog")
                    self.assertEqual(catalog["stac_version"], "1.0.0")
                    item_links = [link for link in catalog["links"] if link["rel"] == "item"]
                    self.assertEqual(len(item_links), len(names))
                    self.assertIn(links["self"], [link["href"] for link in item_links])
                    self.assertEqual((output / name).read_bytes(), original)
                    self.assertEqual(self.client.get(links["root"]).status_code, 401)
                    self.assertEqual(self.client.get(links["self"]).status_code, 401)

    def test_legacy_item_without_links_is_served_with_navigation(self) -> None:
        job_id, output = self.create_job("sentinel2-hsi-pilot", ["stac_item.json"])
        path = output / "stac_item.json"
        item = json.loads(path.read_text())
        del item["links"]
        path.write_text(json.dumps(item))
        response = self.client.get(f"/jobs/{job_id}/artifacts/stac_item.json", headers=self.auth)
        self.assertEqual(response.status_code, 200)
        self.assertEqual({link["rel"] for link in response.json()["links"]}, {"self", "root"})

    def test_catalog_checks_job_and_terminal_status(self) -> None:
        self.assertEqual(self.client.get("/jobs/missing/catalog", headers=self.auth).status_code, 404)
        job = service.JOB_STORE.create("sentinel2-hsi-pilot", "cwltool", {})
        url = f"/jobs/{job['jobID']}/catalog"
        for status in ("accepted", "running", "failed"):
            service.JOB_STORE.update(job["jobID"], status=status)
            self.assertEqual(self.client.get(url, headers=self.auth).status_code, 409)

    def test_invalid_stac_artifacts_fail_explicitly(self) -> None:
        job_id, output = self.create_job("sentinel2-hsi-pilot", ["stac_item.json"])
        for content in (
            "{",
            "{}",
            json.dumps({"type": "Feature", "stac_version": "1.0.0", "links": {}}),
            json.dumps({"type": "Feature", "stac_version": "1.0.0", "links": [{}]}),
        ):
            with self.subTest(content=content):
                (output / "stac_item.json").write_text(content)
                response = self.client.get(
                    f"/jobs/{job_id}/artifacts/stac_item.json", headers=self.auth,
                )
                self.assertEqual(response.status_code, 500)
                self.assertIn("detail", response.json())

    def test_non_stac_downloads_are_unchanged(self) -> None:
        job_id, output = self.create_job("sentinel2-hsi-pilot", [])
        content = b'{"type":"FeatureCollection","features":[]}'
        (output / "hsi_classification.geojson").write_bytes(content)
        response = self.client.get(
            f"/jobs/{job_id}/artifacts/hsi_classification.geojson", headers=self.auth,
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, content)
        self.assertIn("attachment", response.headers["content-disposition"])


class StacProducerTests(unittest.TestCase):
    def test_pilot_writer_emits_self_link(self) -> None:
        script = service.WORKFLOW_DIR / "scripts" / "classify_hsi.py"
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            manifest = root / "manifest.json"
            manifest.write_text('{"hsi_cube":{}}')
            subprocess.run([
                sys.executable, str(script), "--hsi-cube-manifest", str(manifest),
                "--classifier-model", "test", "--run-id", "test", "--output-dir", str(root),
            ], check=True, capture_output=True, text=True)
            item = json.loads((root / "stac_item.json").read_text())
            self.assertEqual(item["links"], [{
                "rel": "self", "href": "stac_item.json", "type": "application/geo+json",
            }])

    def test_imagery_writer_uses_declared_output_filename(self) -> None:
        from rasterio.crs import CRS
        from rasterio.transform import from_origin

        contracts = load_module(
            "stac_raster_contracts",
            service.WORKSPACE_ROOT / "workflows/imagery_harmonization/scripts/raster_contracts.py",
        )
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            raster = root / "image.tif"
            raster.write_bytes(b"fixture")
            for name in ("sentinel2_stac_item.json", "dji_stac_item.json"):
                item = contracts.stac_item(
                    "fixture", raster, root / "quality.json", CRS.from_epsg(4326),
                    from_origin(12, 42, 0.01, 0.01), 4, 4, {},
                    item_path=root / name,
                )
                self.assertEqual(item["links"][0]["href"], name)
                self.assertEqual(item["links"][0]["rel"], "self")


class ProvenanceDraftTests(unittest.TestCase):
    def test_existing_profile_example_validates_with_formats(self) -> None:
        profile = service.BASE_DIR.parent / "provenance-profile"
        schema = json.loads((profile / "schema/provenance-profile.schema.json").read_text())
        example = json.loads((profile / "examples/workflow-provenance-example.json").read_text())
        validator = jsonschema.Draft7Validator(schema, format_checker=jsonschema.FormatChecker())
        validator.validate(example)
        activity = next(iter(example["activity"].values()))
        activity["prov:startTime"] = "invalid timestamp"
        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(example)

    def test_draft_is_not_advertised_as_implemented(self) -> None:
        client = TestClient(service.app)
        self.assertNotIn(
            "https://luciocola.github.io/geospatial-building-block/1.0/conf/provenance",
            client.get("/conformance").json()["conformsTo"],
        )


if __name__ == "__main__":
    unittest.main()
