#!/usr/bin/env python3
"""Pure-Python tests for the QGIS EDI contract boundary."""

import unittest

from contract_adapter import QGISLayerContext, ServiceEndpoints, build_contract


class ContractAdapterTests(unittest.TestCase):
    def setUp(self) -> None:
        self.context = QGISLayerContext(
            layer_id="sentinel-reference",
            source_href="/approved/staging/sentinel.tif",
            profile="raster",
            crs="EPSG:32632",
            extent=(500000.0, 4510000.0, 505000.0, 4515000.0),
            resolution_m=10.0,
            bands=("red", "green", "blue"),
            masks=("cloud", "nodata"),
            metadata={"processingLevel": "L2A"},
        )

    def test_contract_preserves_context_and_shared_semantics(self) -> None:
        contract = build_contract(
            self.context,
            "sentinel2-dji-imagery-harmonization",
            {"target_resolution_m": 2.5},
            ServiceEndpoints(kernel="http://kernel:8016"),
        )
        self.assertEqual(contract["input"]["contextMetadata"]["processingLevel"], "L2A")
        self.assertEqual(contract["process"]["id"], "sentinel2-dji-imagery-harmonization")
        self.assertIn("validation result", contract["outputs"]["requiredEvidence"])
        self.assertEqual(contract["services"]["kernel"], "http://kernel:8016")

    def test_rejects_unknown_profiles_and_invalid_extent(self) -> None:
        with self.assertRaises(ValueError):
            build_contract(self.context.__class__(**{**self.context.__dict__, "profile": "video"}), "p", {})
        with self.assertRaises(ValueError):
            build_contract(self.context.__class__(**{**self.context.__dict__, "extent": (1, 2, 0, 3)}), "p", {})


if __name__ == "__main__":
    unittest.main()