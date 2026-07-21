"""Write a compact JSON diagnosis of the current MT run state.

Usage:
  python MT_diagnose_state.py
  python MT_diagnose_state.py --preset center_bump_strong --out MT_diagnosis.json

What the JSON means:
  - files: whether key files exist.
  - preset: saved terrain voltage; total_abs_voltage shows whether it is tiny.
  - current_voltage: voltage currently written for hardware input.
  - average_pos: 16 measured points. Many [0,0,0] rows usually mean vision tracking failed.
  - measure_log: hardware/camera wrapper status. success=false or timeout errors mean do not tune terrain.

Quick judgement:
  - If preset total_abs_voltage is near 0.4 V, visible deformation may be very small.
  - If AveragePos has many zero rows, the camera/marker tracking failed.
  - If CurrentVoltage differs from preset voltage, the intended preset was not the last written input.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
PORT_NUM = 16
POINT_NUM = 16


def read_numbers(path: Path) -> list[float]:
    return [float(part) for part in path.read_text(encoding="utf-8", errors="ignore").split()]


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8", errors="ignore"))


def stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "min": min(values),
        "max": max(values),
        "mean": sum(values) / len(values),
        "sum_abs": sum(abs(v) for v in values),
        "nonzero_count": sum(1 for v in values if abs(v) > 1e-9),
    }


def read_average_pos(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    rows = []
    for line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
        parts = line.split()
        if parts:
            rows.append([float(part) for part in parts[:3]])
    zero_rows = [i + 1 for i, row in enumerate(rows) if len(row) >= 3 and all(abs(v) < 1e-12 for v in row)]
    z = [row[2] for row in rows if len(row) >= 3]
    center_ids = [6, 7, 10, 11]
    center_z = [z[i - 1] for i in center_ids if i - 1 < len(z)]
    rim_z = [value for idx, value in enumerate(z, start=1) if idx not in center_ids]
    return {
        "exists": True,
        "row_count": len(rows),
        "zero_row_count": len(zero_rows),
        "zero_rows_1_based": zero_rows,
        "z_stats": stats(z),
        "center_z_mean": sum(center_z) / len(center_z) if center_z else None,
        "rim_z_mean": sum(rim_z) / len(rim_z) if rim_z else None,
        "center_minus_rim": (sum(center_z) / len(center_z) - sum(rim_z) / len(rim_z)) if center_z and rim_z else None,
    }


def read_voltage_file(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"exists": False}
    values = read_numbers(path)
    return {
        "exists": True,
        "count": len(values),
        "values": values,
        "stats": stats(values),
        "looks_like_16_port_static_file": len(values) == PORT_NUM,
    }


def read_preset(name: str) -> dict[str, Any]:
    path = ROOT / "MT_presets" / f"{name}.json"
    if not path.exists():
        return {"exists": False, "path": str(path)}
    payload = read_json(path)
    voltage = [float(v) for v in payload.get("voltage", [])]
    return {
        "exists": True,
        "path": str(path),
        "name": payload.get("name"),
        "notes": payload.get("notes", ""),
        "voltage": voltage,
        "voltage_stats": stats(voltage),
        "warning": "This preset is probably weak/placeholder." if sum(abs(v) for v in voltage) <= 0.5 else "",
    }


def choose_preset(name: str | None) -> str:
    if name:
        return name
    preset_dir = ROOT / "MT_presets"
    names = sorted(path.stem for path in preset_dir.glob("*.json"))
    strong = [item for item in names if "strong" in item.lower()]
    if strong:
        return strong[0]
    return names[0] if names else "center_bump"


def compare_vectors(a: list[float], b: list[float]) -> dict[str, Any]:
    if len(a) != len(b):
        return {"same_length": False, "max_abs_diff": None}
    diffs = [abs(x - y) for x, y in zip(a, b)]
    return {
        "same_length": True,
        "max_abs_diff": max(diffs) if diffs else 0.0,
        "matches": all(diff < 1e-9 for diff in diffs),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Write MT diagnostic JSON for another agent.")
    parser.add_argument("--preset", default=None, help="Preset name. If omitted, prefers a *strong*.json preset.")
    parser.add_argument("--out", default="MT_diagnosis.json")
    args = parser.parse_args()

    preset_name = choose_preset(args.preset)
    preset = read_preset(preset_name)
    current_voltage = read_voltage_file(ROOT / "CurrentVoltage.dat")
    report = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "root": str(ROOT),
        "selected_preset": preset_name,
        "meaning": {
            "AveragePos.txt": "16 rows of measured x y z points from camera tracking.",
            "CurrentVoltage.dat": "16-port voltage input consumed by hardware wrapper.",
            "measure_log.json": "success/error metadata from the measurement wrapper.",
            "center_minus_rim": "positive means center measured higher than rim in the current coordinate sign.",
        },
        "files": {
            name: (ROOT / name).exists()
            for name in ["CurrentVoltage.dat", "AveragePos.txt", "measure_log.json", "ResultPath.dat"]
        },
        "preset": preset,
        "current_voltage": current_voltage,
        "average_pos": read_average_pos(ROOT / "AveragePos.txt"),
        "measure_log": read_json(ROOT / "measure_log.json") if (ROOT / "measure_log.json").exists() else {"exists": False},
    }
    if preset.get("exists") and current_voltage.get("exists"):
        report["preset_vs_current_voltage"] = compare_vectors(preset.get("voltage", []), current_voltage.get("values", []))

    out = ROOT / args.out
    out.write_text(json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
