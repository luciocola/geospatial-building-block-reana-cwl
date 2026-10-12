#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright 2026 4113 Engineering
"""Abstract test suite for the GBB core conformance class (gbb-core/description.md)."""

from __future__ import annotations

import importlib.util
import json
import os
import unittest
from pathlib import Path

os.environ["OSPD_API_TOKEN"] = "test-token"

from fastapi.testclient import TestClient

import app as service

GBB_ROOT = Path(__file__).resolve().parents[2]
EVIDENCE_SCHEMA = GBB_ROOT / "gbb-core" / "schema" / "job-evidence.schema.json"
CORE = "https://luciocola.github.io/geospatial-building-block/1.0/conf/core"
IMPLEMENTED_OGC_CLASSES = {
    "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/core",
    "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/json",
    "http://www.opengis.net/spec/ogcapi-processes-1/1.0/conf/oas30",
}
JSON = {"Accept": "application/json"}


def _load_register_app():
    spec = importlib.util.spec_from_file_location(
        "process_type_register_app", GBB_ROOT / "process-type-register" / "service" / "app.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.app


def assert_valid_link(case: unittest.TestCase, link: dict) -> None:
    """Structural check of ogc.ogc-utils.json-link (href and rel are required strings)."""
    case.assertIsInstance(link.get("href"), str)
    case.assertIsInstance(link.get("rel"), str)
    for optional in ("type", "title", "hreflang"):
        if optional in link:
            case.assertIsInstance(link[optional], str)


def assert_landing(case: unittest.TestCase, client: TestClient) -> None:
    response = client.get("/", headers=JSON)
    case.assertEqual(response.status_code, 200)
    body = response.json()
    case.assertIsInstance(body.get("links"), list)
    for link in body["links"]:
        assert_valid_link(case, link)
    rels = {link["rel"] for link in body["links"]}
    case.assertTrue({"self", "conformance", "service-desc", "service-doc"} <= rels, rels)
    targets = {link["rel"]: link["href"] for link in body["links"]}
    case.assertEqual(client.get(targets["service-desc"]).status_code, 200)
    case.assertEqual(client.get(targets["conformance"]).status_code, 200)
    browser = client.get("/", headers={"Accept": "text/html"}, follow_redirects=False)
    case.assertIn(browser.status_code, (200, 307))


class GbbCoreConformanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(service.app)
        cls.auth = {"Authorization": "Bearer test-token"}

    def test_req_core_landing(self) -> None:
        assert_landing(self, self.client)

    def test_req_core_conformance(self) -> None:
        conforms_to = self.client.get("/conformance").json()["conformsTo"]
        self.assertIsInstance(conforms_to, list)
        self.assertIn(CORE, conforms_to)
        undeclared = set(conforms_to) - IMPLEMENTED_OGC_CLASSES - {CORE}
        self.assertFalse(undeclared, f"conformance classes without an implementation: {undeclared}")

    def test_req_core_conformance_matches_kernel_descriptor(self) -> None:
        kernel = json.loads(service.KERNEL_FILE.read_text(encoding="utf-8"))
        core = next(c for c in kernel["functionalContract"]["conformanceClasses"] if c["id"] == "functional-core")
        self.assertEqual(core["uri"], CORE)
        declared = {
            cls["uri"]
            for bb in kernel["buildingBlocks"]
            if bb["id"] == "geospatial-processes-facade"
            for standard in bb.get("standards", [])
            for cls in standard.get("conformanceClasses", [])
        }
        self.assertEqual(declared, IMPLEMENTED_OGC_CLASSES)

    def test_req_core_process_declaration(self) -> None:
        processes = self.client.get("/processes").json()["processes"]
        self.assertTrue(processes)
        for process in processes:
            for key in ("id", "title", "version"):
                self.assertTrue(process.get(key), f"{process.get('id')} lacks {key}")
            description = self.client.get(f"/processes/{process['id']}").json()
            self.assertIsInstance(description.get("inputs"), dict)
            self.assertIsInstance(description.get("outputs"), dict)
            self.assertTrue(description["outputs"], f"{process['id']} declares no outputs")

    def test_req_core_structured_failure(self) -> None:
        missing = self.client.get("/processes/does-not-exist")
        self.assertEqual(missing.status_code, 404)
        self.assertIsInstance(missing.json(), dict)
        missing_job = self.client.get("/jobs/does-not-exist", headers=self.auth)
        self.assertEqual(missing_job.status_code, 404)
        self.assertIsInstance(missing_job.json(), dict)
        invalid = self.client.post(
            "/processes/sentinel2-hsi-pilot/execution",
            headers=self.auth,
            json={"backend": "unsupported"},
        )
        self.assertGreaterEqual(invalid.status_code, 400)
        self.assertLess(invalid.status_code, 500)
        self.assertIsInstance(invalid.json(), dict)

    def test_req_core_evidence(self) -> None:
        inputs = {"aoi_geojson": {"href": "workflows/sentinel2_hsi_pilot/examples/aoi.geojson"}}
        job = service.JOB_STORE.create("sentinel2-hsi-pilot", "cwltool", {"inputs": inputs})
        job_id = job["jobID"]
        service.JOB_STORE.update(
            job_id,
            status="successful",
            returnCode=0,
            results={"stac_item.json": {"href": f"/jobs/{job_id}/artifacts/stac_item.json", "type": "application/geo+json"}},
        )
        evidence = self.client.get(f"/jobs/{job_id}/results", headers=self.auth).json()
        self.assertEqual(evidence["jobID"], job_id)
        self.assertEqual(evidence["processID"], "sentinel2-hsi-pilot")
        self.assertEqual(evidence["status"], "successful")
        self.assertEqual(evidence["inputs"], inputs)
        self.assertTrue(all("href" in ref for ref in evidence["results"].values()))
        self.assertIs(evidence["validation"]["passed"], True)
        try:
            import jsonschema
        except ImportError:
            return
        jsonschema.validate(evidence, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))

    def test_req_core_evidence_reports_failed_validation(self) -> None:
        job = service.JOB_STORE.create("sentinel2-hsi-pilot", "cwltool", {})
        service.JOB_STORE.update(job["jobID"], status="failed", returnCode=2)
        evidence = self.client.get(f"/jobs/{job['jobID']}/results", headers=self.auth).json()
        self.assertIs(evidence["validation"]["passed"], False)
        self.assertEqual(evidence["inputs"], {})

    def test_req_core_discovery_is_public(self) -> None:
        for path in ("/", "/conformance", "/processes"):
            self.assertEqual(self.client.get(path, headers=JSON).status_code, 200, path)

    def test_example_matches_evidence_schema(self) -> None:
        try:
            import jsonschema
        except ImportError:
            self.skipTest("jsonschema not installed")
        example = json.loads((GBB_ROOT / "gbb-core" / "examples" / "job-evidence.json").read_text(encoding="utf-8"))
        jsonschema.validate(example, json.loads(EVIDENCE_SCHEMA.read_text(encoding="utf-8")))


class RegisterMinimumAlignmentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(_load_register_app())

    def test_landing(self) -> None:
        assert_landing(self, self.client)

    def test_unsupported_filters_are_rejected_not_ignored(self) -> None:
        for query in ("bbox=0,0,1,1", "datetime=2026-01-01T00:00:00Z"):
            response = self.client.get(f"/collections/process-types/items?{query}")
            self.assertEqual(response.status_code, 400, query)
            self.assertIsInstance(response.json(), dict)
        self.assertEqual(self.client.get("/collections/process-types/items?limit=5").status_code, 200)


if __name__ == "__main__":
    unittest.main()
