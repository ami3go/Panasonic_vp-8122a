"""Offline validation for source-traced native command HIL qualification."""
from __future__ import annotations

import copy
import csv
import json
from pathlib import Path
from xml.etree import ElementTree as ET

import pytest

from tests.hil_reporting import (
    FAMILIES, MatrixError, SAFE_CASES, build_report, load_matrix,
    load_talker_observations, measurement_comparison, write_reports,
)


def test_matrix_covers_each_documented_family_and_variants():
    matrix = load_matrix()
    assert set(matrix["families"]) == FAMILIES
    assert len(matrix["cases"]) >= 45
    assert SAFE_CASES == set(matrix["default_executable_hil_case_ids"])
    assert len({x["case_id"] for x in matrix["cases"]}) == len(matrix["cases"])


def test_status_only_variants_have_no_transmission_bytes():
    matrix = load_matrix()
    for case in matrix["cases"]:
        if case["example_word"] is None:
            assert case["expected_host_tx_hex"] is None
            assert case["required_phase"] == "SOURCE_UNVERIFIED"
        if case["side_effect_risk"] == "RF_ENABLE":
            assert case["required_phase"] == "DEDICATED_APPROVAL"
        if case["case_id"] not in SAFE_CASES:
            assert case["required_phase"] != "TALKER_ONLY"


@pytest.mark.parametrize("mutation", [
    lambda m: m["default_executable_hil_case_ids"].append("AP.ON"),
    lambda m: m["cases"][0].update(physical_hil_status="PASS"),
    lambda m: m["cases"][0]["expected_host_tx_hex"].update(EOI="2a49444e3f"),
    lambda m: m["cases"][0].update(required_phase="TALKER_ONLY"),
    lambda m: m["cases"].append(copy.deepcopy(m["cases"][0])),
    lambda m: m["cases"][-1].update(example_word="P200"),
    lambda m: m["bus_operations"][0].update(default_allowed=True),
])
def test_matrix_rejects_unsafe_or_forged_qualification(tmp_path, mutation):
    modified = copy.deepcopy(load_matrix())
    mutation(modified)
    path = tmp_path / "matrix.json"
    path.write_text(json.dumps(modified), encoding="utf-8")
    with pytest.raises(MatrixError):
        load_matrix(path)


@pytest.mark.parametrize("requested,measured,uncertainty,tolerance,calibrated,want", [
    (100, 100.5, 0.2, 1, True, "WITHIN_LIMIT"),
    (100, 103, 0.2, 1, True, "OUTSIDE_LIMIT"),
    (100, 100.9, 0.2, 1, True, "INDETERMINATE"),
    (100, 100, 0.1, 1, False, "INDETERMINATE"),
    (100, float("nan"), 0.1, 1, True, "INDETERMINATE"),
    (100, 100, -1, 1, True, "INDETERMINATE"),
    (100, 100, 0, 0, True, "INDETERMINATE"),
    (100, True, 0.1, 1, True, "INDETERMINATE"),
])
def test_measurement_guardband_is_not_a_hil_pass(
    requested, measured, uncertainty, tolerance, calibrated, want
):
    assert measurement_comparison(
        requested=requested, measured=measured,
        expanded_uncertainty=uncertainty, tolerance=tolerance,
        calibration_valid=calibrated
    ) == want


def test_observation_is_never_lifted_to_physical_pass(tmp_path):
    evidence = {
        "schema_version": 1, "result": "OBSERVED", "talker_mode": 0,
        "requested_tx_hex": ["544d300a"], "raw_rx_hex": "4652314d5a0a",
        "ordered_tm0_fields": [{"index": 0, "prefix": "FR", "value": "1MZ"}],
        "eoi_verified_by_bus_analyzer": False, "rf_output_measured": False
    }
    (tmp_path / "vp8122a_local_tm0_test.json").write_text(
        json.dumps(evidence), encoding="utf-8"
    )
    observations = load_talker_observations(tmp_path)
    report = build_report(load_matrix(), observations, run_id="local")
    row = next(c for c in report["cases"] if c["case_id"] == "TM.0")
    assert row["physical_hil_status"] == "INCONCLUSIVE"
    assert row["observation_count"] == 1
    assert report["physical_qualified_families"] == []
    assert report["talker_observations"][0]["raw"] == evidence
    output = write_reports(report, tmp_path)
    assert set(output) == {"json", "csv", "md", "xml"}
    assert all(p.is_file() for p in output.values())
    loaded = json.loads(output["json"].read_text(encoding="utf-8"))
    assert loaded["talker_observations"][0]["raw"]["raw_rx_hex"] == "4652314d5a0a"
    assert loaded["driver_version"] == "0.2.7"
    assert loaded["matrix_source_baseline"] == "0.2.6"
    with output["csv"].open(encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.DictReader(stream))
    assert len(csv_rows) == 45
    tree = ET.parse(output["xml"])
    assert tree.getroot().attrib["tests"] == "45"
    assert len(tree.findall(".//testcase")) == 45
    assert not tree.findall(".//failure")
    with pytest.raises(MatrixError, match="already exist"):
        write_reports(report, tmp_path)


def test_invalid_run_id_and_outside_case_cannot_enter_report():
    with pytest.raises(MatrixError, match="run ID"):
        build_report(load_matrix(), [], run_id="../../injection")
    with pytest.raises(MatrixError, match="unknown command case"):
        build_report(load_matrix(), [{"case_id": "GT.L"}], run_id="safe")


def test_malformed_or_unknown_talker_evidence_is_rejected(tmp_path):
    path = tmp_path / "vp8122a_x_tm0_bad.json"
    path.write_text(json.dumps({"talker_mode": 99, "result": "OBSERVED",
                                "requested_tx_hex": ["544d30"]}), encoding="utf-8")
    with pytest.raises(MatrixError, match="unknown talker"):
        load_talker_observations(tmp_path)
