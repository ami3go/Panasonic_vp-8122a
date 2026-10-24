"""Offline-only VP-8122A native command matrix and evidence reporting.

Never opens VISA, executes program words, or infers physical RF qualification.
A documented example is a golden *host serialization* fixture, not permission
to send that command to a physical VP-8122A.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import re
from typing import Any
from xml.etree import ElementTree as ET

from panasonic_vp8122a.native import encode_program_word

FAMILIES = frozenset((
    "FR", "AP", "LE", "EM", "CO", "AM", "FM", "MS", "PL", "FT", "PR",
    "SC", "LV", "NP", "RC", "ST", "TM", "DR", "AS", "NT", "P1", "P2",
))
STATUSES = frozenset(("PASS", "FAIL", "INCONCLUSIVE", "NOT_TESTED", "UNSUPPORTED"))
PHASES = frozenset(("TALKER_ONLY", "ACTIVE_RF_MEASURED", "DEDICATED_APPROVAL",
                     "SOURCE_UNVERIFIED"))
SAFE_CASES = frozenset(("TM.0", "TM.1", "TM.2"))
TERMINATIONS = {"EOI": "", "LF": "\n", "CRLF": "\r\n"}
RUN_ID = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
MATRIX_PATH = Path(__file__).parent / "hil" / "command_matrix.json"


class MatrixError(ValueError):
    """An offline fixture is malformed or overstates safety/qualification."""


def load_matrix(path: Path = MATRIX_PATH) -> dict[str, Any]:
    """Strictly validate documentation fixtures; do not touch instruments."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema_version") != 1:
        raise MatrixError("unsupported command-matrix schema")
    if set(data.get("families", ())) != FAMILIES:
        raise MatrixError("native command families are incomplete")
    if data.get("default_executable_hil_case_ids") != ["TM.0", "TM.1", "TM.2"]:
        raise MatrixError("physical HIL default allowlist may contain only TM0/1/2")
    if not isinstance(data.get("cases"), list):
        raise MatrixError("expected a case array")
    ids = set()
    observed = set()
    for case in data["cases"]:
        if not isinstance(case, dict):
            raise MatrixError("invalid case record")
        cid = case.get("case_id")
        family = case.get("family")
        variant = case.get("variant")
        if not isinstance(cid, str) or not isinstance(variant, str) or cid != f"{family}.{variant}" or cid in ids:
            raise MatrixError("duplicate or invalid case ID")
        if family not in FAMILIES:
            raise MatrixError(f"unknown native family: {family}")
        ids.add(cid)
        observed.add(family)
        if case.get("required_phase") not in PHASES:
            raise MatrixError(f"invalid required authorization for {cid}")
        if case.get("physical_hil_status") not in ("NOT_TESTED", "UNSUPPORTED"):
            raise MatrixError(f"unverified fixture claims physical qualification: {cid}")
        if not case.get("manual_image") or not case.get("manual_reference"):
            raise MatrixError(f"missing command provenance: {cid}")
        word = case.get("example_word")
        wire = case.get("expected_host_tx_hex")
        if word is None:
            if wire is not None or case["required_phase"] != "SOURCE_UNVERIFIED":
                raise MatrixError(f"status-only/unverified case must have no TX vector: {cid}")
        else:
            if not isinstance(word, str) or not isinstance(wire, dict):
                raise MatrixError(f"missing golden bytes: {cid}")
            for term, suffix in TERMINATIONS.items():
                try:
                    expected = encode_program_word(word, suffix).hex()
                except Exception as exc:
                    raise MatrixError(f"invalid native golden vector: {cid}") from exc
                if wire.get(term) != expected:
                    raise MatrixError(f"golden bytes do not match encoder: {cid}:{term}")
        if cid in SAFE_CASES:
            if case["required_phase"] != "TALKER_ONLY" or word != cid.replace(".", ""):
                raise MatrixError(f"unsafe talker test definition: {cid}")
        elif case["required_phase"] == "TALKER_ONLY":
            raise MatrixError(f"unexpected physical HIL permission: {cid}")
        if case.get("side_effect_risk") == "RF_ENABLE" and case["required_phase"] != "DEDICATED_APPROVAL":
            raise MatrixError(f"RF enable must require separate dedicated approval: {cid}")
    if observed != FAMILIES or not SAFE_CASES.issubset(ids):
        raise MatrixError("incomplete source inventory or missing talker modes")
    for op in data.get("bus_operations", []):
        if op.get("type") != "IEEE488_BUS" or op.get("default_allowed") is not False:
            raise MatrixError("IEEE-488 bus operations cannot be ASCII HIL tests")
    return data


def measurement_comparison(
    *, requested: float, measured: float, expanded_uncertainty: float,
    tolerance: float, calibration_valid: bool
) -> str:
    """Guard-band a *numeric comparison*, not a physical HIL verdict.

    Results are WITHIN_LIMIT, OUTSIDE_LIMIT, or INDETERMINATE. Caller must
    separately authenticate reference identity, calibration and actual samples;
    this function alone cannot grant a physical qualification PASS.
    """
    nums = (requested, measured, expanded_uncertainty, tolerance)
    if (any(type(n) not in (int, float) or not math.isfinite(n) for n in nums)
            or expanded_uncertainty < 0 or tolerance <= 0
            or calibration_valid is not True):
        return "INDETERMINATE"
    error = abs(measured - requested)
    if error + expanded_uncertainty <= tolerance:
        return "WITHIN_LIMIT"
    if error - expanded_uncertainty > tolerance:
        return "OUTSIDE_LIMIT"
    return "INDETERMINATE"


def load_talker_observations(folder: Path, *, run_id: str | None = None) -> list[dict[str, Any]]:
    """Load pre-existing JSON evidence only; no RF/GPIB backend calls."""
    if not folder.is_dir():
        raise MatrixError("evidence directory does not exist")
    if run_id is not None and RUN_ID.fullmatch(run_id) is None:
        raise MatrixError("unsafe run ID")
    results: list[dict[str, Any]] = []
    pattern = f"vp8122a_{run_id}_tm*.json" if run_id else "vp8122a_*_tm*.json"
    for path in sorted(folder.glob(pattern)):
        if path.stat().st_size > 2_000_000:
            raise MatrixError(f"oversized evidence: {path.name}")
        try:
            item = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, UnicodeError) as exc:
            raise MatrixError(f"malformed evidence: {path.name}") from exc
        if not isinstance(item, dict) or type(item.get("talker_mode")) is not int:
            raise MatrixError(f"invalid talker evidence: {path.name}")
        mode = item["talker_mode"]
        if mode not in (0, 1, 2):
            raise MatrixError(f"unknown talker mode in {path.name}")
        if item.get("result") not in ("OBSERVED", "INCONCLUSIVE"):
            raise MatrixError(f"invalid raw observation status in {path.name}")
        requested = item.get("requested_tx_hex")
        if not isinstance(requested, list) or any(type(v) is not str for v in requested):
            raise MatrixError(f"missing host TX trace in {path.name}")
        # Readback OBSERVED is explicitly NOT physical RF/EOI qualification.
        results.append({"case_id": f"TM.{mode}", "file": path.name, "raw": item,
                        "qualification_status": "INCONCLUSIVE",
                        "reason": "EOI and external RF state lack verified independent evidence"})
    return results


def build_report(matrix: dict[str, Any], observations: list[dict[str, Any]],
                 *, run_id: str) -> dict[str, Any]:
    """Keep offline implementation and actual physical HIL coverage separate."""
    if not isinstance(run_id, str) or RUN_ID.fullmatch(run_id) is None:
        raise MatrixError("unsafe run ID")
    case_ids = {c["case_id"] for c in matrix["cases"]}
    if any(o.get("case_id") not in case_ids for o in observations):
        raise MatrixError("observation references unknown command case")
    obs_by_case: dict[str, list[dict[str, Any]]] = {}
    for observation in observations:
        obs_by_case.setdefault(observation["case_id"], []).append(observation)
    rows = []
    for case in matrix["cases"]:
        cid = case["case_id"]
        found = obs_by_case.get(cid, [])
        status = ("UNSUPPORTED" if case["example_word"] is None
                  else "INCONCLUSIVE" if found else "NOT_TESTED")
        rows.append({
            "case_id": cid, "family": case["family"],
            "risk": case["side_effect_risk"],
            "required_phase": case["required_phase"],
            "offline_golden_vector": case["example_word"] is not None,
            "source": f"{case['manual_image']} ({case['manual_reference']})",
            "physical_hil_status": status,
            "observation_count": len(found),
            "requested_host_bytes_hex": case["expected_host_tx_hex"],
            "notes": case["syntax_and_limits"],
        })
    return {
        "schema_version": 1, "run_id": run_id,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "driver_baseline": matrix["driver_baseline"],
        "source_reference": matrix["source"],
        "physical_qualified_families": [],
        "qualification_warning": "OFFLINE FIXTURES/OBSERVATIONS; NO PHYSICAL HIL PASS. RF, EOI and interlocks not independently qualified.",
        "cases": rows, "talker_observations": observations,
        "bus_operations": matrix["bus_operations"],
    }


def write_reports(report: dict[str, Any], output_dir: Path) -> dict[str, Path]:
    """Atomically refuse overwrites; generate four synchronized offline artifacts."""
    if not output_dir.is_dir():
        raise MatrixError("report directory must already exist")
    stem = f"vp8122a_qualification_{report['run_id']}"
    paths = {ext: output_dir / f"{stem}.{ext}" for ext in ("json", "csv", "md", "xml")}
    if any(p.exists() for p in paths.values()):
        raise MatrixError("run reports already exist; choose another run ID")
    # Pre-render all formats before creating files to minimize partial output.
    j = json.dumps(report, indent=2, sort_keys=True) + "\n"
    import io
    buf = io.StringIO()
    fields = ("case_id", "family", "risk", "required_phase",
              "offline_golden_vector", "physical_hil_status",
              "observation_count", "source", "notes")
    writer = csv.DictWriter(buf, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(report["cases"])
    md = ["# Panasonic VP-8122A native GPIB qualification",
          "", f"Run: {report['run_id']}", "",
          "**No physical RF/EOI qualification recorded.**", "",
          "| Case | Offline vector | Physical HIL | Observations |",
          "|---|---|---|---|"]
    for row in report["cases"]:
        md.append(f"| {row['case_id']} | {'YES' if row['offline_golden_vector'] else 'NO'} | "
                  f"{row['physical_hil_status']} | {row['observation_count']} |")
    root = ET.Element("testsuite", name="vp8122a_native_hil",
                      tests=str(len(report["cases"])),
                      failures=str(sum(r["physical_hil_status"] == "FAIL" for r in report["cases"])),
                      skipped=str(sum(r["physical_hil_status"] in
                                      ("INCONCLUSIVE", "NOT_TESTED", "UNSUPPORTED")
                                      for r in report["cases"])))
    for row in report["cases"]:
        test = ET.SubElement(root, "testcase", classname="native_gpib."+row["family"],
                             name=row["case_id"])
        status = row["physical_hil_status"]
        if status == "FAIL":
            ET.SubElement(test, "failure", message="physical HIL acceptance failed")
        elif status != "PASS":
            ET.SubElement(test, "skipped", message=status)
    payloads = {"json": j, "csv": buf.getvalue(), "md": "\n".join(md)+"\n",
                "xml": ET.tostring(root, encoding="unicode", xml_declaration=False)+"\n"}
    created = []
    try:
        for ext, path in paths.items():
            with path.open("x", encoding="utf-8", newline="") as out:
                created.append(path)
                out.write(payloads[ext])
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return paths


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline-only native GPIB qualification report")
    parser.add_argument("--evidence-dir", required=True, type=Path)
    parser.add_argument("--output-dir", required=True, type=Path)
    parser.add_argument("--run-id", required=True)
    ns = parser.parse_args()
    report = build_report(load_matrix(), load_talker_observations(ns.evidence_dir, run_id=ns.run_id),
                          run_id=ns.run_id)
    for name, path in write_reports(report, ns.output_dir).items():
        print(f"{name}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
