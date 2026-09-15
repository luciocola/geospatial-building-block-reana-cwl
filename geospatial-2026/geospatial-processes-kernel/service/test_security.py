#!/usr/bin/env python3
"""Security regression tests for operational API boundaries."""

from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

os.environ["OSPD_API_TOKEN"] = "test-token"

from fastapi.testclient import TestClient

import app as service


class SecurityBoundaryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.client = TestClient(service.app)
        cls.headers = {"Authorization": "Bearer test-token"}

    def setUp(self) -> None:
        self.temporary_directory = tempfile.TemporaryDirectory()
        service.PROVENANCE_ROOT = Path(self.temporary_directory.name)

    def tearDown(self) -> None:
        self.temporary_directory.cleanup()

    def test_discovery_is_public_but_jobs_require_authentication(self) -> None:
        self.assertEqual(self.client.get("/processes").status_code, 200)
        self.assertEqual(self.client.get("/jobs/missing").status_code, 401)
        self.assertEqual(
            self.client.get("/jobs/missing", headers=self.headers).status_code,
            404,
        )

    def test_execution_rejects_files_outside_workspace(self) -> None:
        response = self.client.post(
            "/processes/sentinel2-hsi-pilot/execution",
            headers=self.headers,
            json={"inputs": {"aoi_geojson": {"href": "/etc/passwd"}}},
        )
        self.assertEqual(response.status_code, 422)

    def test_provenance_requires_shape_and_hides_storage_path(self) -> None:
        self.assertEqual(
            self.client.post("/kernel/provenance", headers=self.headers, json={}).status_code,
            422,
        )
        response = self.client.post(
            "/kernel/provenance",
            headers=self.headers,
            json={"bundle": {"entity": {}}},
        )
        self.assertEqual(response.status_code, 202)
        self.assertNotIn("storedAt", response.json())
        stored_files = list(service.PROVENANCE_ROOT.glob("*.json"))
        self.assertEqual(len(stored_files), 1)
        self.assertEqual(stored_files[0].stat().st_mode & 0o777, 0o600)

    def test_results_do_not_disclose_process_logs(self) -> None:
        job = service.JOB_STORE.create("sentinel2-hsi-pilot", "cwltool", {})
        service.JOB_STORE.update(
            job["jobID"],
            status="failed",
            returnCode=2,
            stdout="sensitive stdout",
            stderr="sensitive stderr",
        )
        response = self.client.get(f"/jobs/{job['jobID']}/results", headers=self.headers)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertNotIn("stdout", result)
        self.assertNotIn("stderr", result)
        self.assertTrue(result["logsAvailable"])

    def test_collected_results_use_api_references(self) -> None:
        with tempfile.TemporaryDirectory() as temporary_directory:
            output_dir = Path(temporary_directory) / "outputs"
            output_dir.mkdir()
            (output_dir / "stac_item.json").write_text("{}", encoding="utf-8")
            results = service._collect_local_results("job-123", Path(temporary_directory))
        self.assertEqual(
            results["stac_item.json"]["href"],
            "/jobs/job-123/artifacts/stac_item.json",
        )
        self.assertNotIn(temporary_directory, str(results))


if __name__ == "__main__":
    unittest.main()