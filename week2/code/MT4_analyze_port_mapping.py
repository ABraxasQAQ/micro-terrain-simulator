"""Analyze port-to-terrain direction from MT4 response scans.

Input:
  - baseline MT4_summary.jsonl
  - port-scan MT4_summary.jsonl

Output:
  - MT4_outputs/port_mapping/MT4_port_mapping_summary.csv
  - MT4_outputs/port_mapping/MT4_port_mapping_summary.json

This does not know the physical electrode layout by itself.  It maps each port
to measured coordinate-side response: x-small, x-large, y-small, y-large, center.
After matching x/y sides to the live camera view, use the strongest ports as
MATLAB active-port candidates.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from collections import defaultdict
from pathlib import Path
from typing import Dict, Iterable, List, Sequence


PORT_NUM = 16
GROUPS = {
    "x_small": [0, 1, 2, 3],
    "x_large": [12, 13, 14, 15],
    "y_small": [0, 4, 8, 12],
    "y_large": [3, 7, 11, 15],
    "center": [5, 6, 9, 10],
}


def load_jsonl(path: str | Path) -> List[dict]:
    rows: List[dict] = []
    with Path(path).open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def mean(values: Sequence[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def average_z(rows: Sequence[dict]) -> List[float]:
    good = [row for row in rows if row.get("success") and row.get("z_values")]
    if not good:
        raise ValueError("no successful baseline rows with z_values")
    return [mean([float(row["z_values"][idx]) for row in good]) for idx in range(PORT_NUM)]


def group_mean(values: Sequence[float], group_name: str) -> float:
    return mean([float(values[idx]) for idx in GROUPS[group_name]])


def dominant_response(delta: Sequence[float]) -> tuple[str, float]:
    group_values = {
        "x_small": group_mean(delta, "x_small"),
        "x_large": group_mean(delta, "x_large"),
        "y_small": group_mean(delta, "y_small"),
        "y_large": group_mean(delta, "y_large"),
        "center": group_mean(delta, "center"),
    }
    name = max(group_values, key=lambda key: abs(group_values[key]))
    return name, group_values[name]


def point_list(indices: Iterable[int]) -> str:
    return " ".join(str(idx + 1) for idx in indices)


def analyze(baseline_path: str | Path, port_scan_path: str | Path) -> dict:
    baseline_rows = load_jsonl(baseline_path)
    port_rows = [
        row for row in load_jsonl(port_scan_path)
        if row.get("success") and row.get("scan_type") == "port_scan" and row.get("z_values")
    ]
    baseline_z = average_z(baseline_rows)

    by_port: Dict[int, List[dict]] = defaultdict(list)
    for row in port_rows:
        ports = row.get("ports") or []
        if len(ports) == 1:
            by_port[int(ports[0])].append(row)

    summaries = []
    for port, rows in sorted(by_port.items()):
        rows = sorted(rows, key=lambda row: float(row.get("level", 0.0)))
        for row in rows:
            level = float(row.get("level", 0.0))
            z_values = [float(value) for value in row["z_values"]]
            delta = [z_values[idx] - baseline_z[idx] for idx in range(PORT_NUM)]
            strongest_point = max(range(PORT_NUM), key=lambda idx: abs(delta[idx])) + 1
            dominant_group, dominant_value = dominant_response(delta)
            x_gradient = group_mean(delta, "x_large") - group_mean(delta, "x_small")
            y_gradient = group_mean(delta, "y_large") - group_mean(delta, "y_small")
            summaries.append(
                {
                    "port": port,
                    "level": level,
                    "dominant_group": dominant_group,
                    "dominant_value": dominant_value,
                    "center_delta": group_mean(delta, "center"),
                    "x_small_delta": group_mean(delta, "x_small"),
                    "x_large_delta": group_mean(delta, "x_large"),
                    "y_small_delta": group_mean(delta, "y_small"),
                    "y_large_delta": group_mean(delta, "y_large"),
                    "x_gradient_xlarge_minus_xsmall": x_gradient,
                    "y_gradient_ylarge_minus_ysmall": y_gradient,
                    "strongest_point": strongest_point,
                    "strongest_point_delta": delta[strongest_point - 1],
                    "case_id": row.get("case_id", ""),
                }
            )

    recommendations = {
        "center_up_candidates": sorted(
            summaries,
            key=lambda row: row["center_delta"],
            reverse=True,
        )[:5],
        "x_large_up_candidates": sorted(
            summaries,
            key=lambda row: row["x_gradient_xlarge_minus_xsmall"],
            reverse=True,
        )[:5],
        "x_small_up_candidates": sorted(
            summaries,
            key=lambda row: row["x_gradient_xlarge_minus_xsmall"],
        )[:5],
        "y_large_up_candidates": sorted(
            summaries,
            key=lambda row: row["y_gradient_ylarge_minus_ysmall"],
            reverse=True,
        )[:5],
        "y_small_up_candidates": sorted(
            summaries,
            key=lambda row: row["y_gradient_ylarge_minus_ysmall"],
        )[:5],
    }

    return {
        "baseline_path": str(baseline_path),
        "port_scan_path": str(port_scan_path),
        "point_groups": {name: point_list(indices) for name, indices in GROUPS.items()},
        "summaries": summaries,
        "recommendations": recommendations,
    }


def write_outputs(report: dict, output_dir: str | Path) -> None:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"{stamp}_MT4_port_mapping_summary.json"
    csv_path = output_dir / f"{stamp}_MT4_port_mapping_summary.csv"

    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")

    fields = [
        "port",
        "level",
        "dominant_group",
        "dominant_value",
        "center_delta",
        "x_small_delta",
        "x_large_delta",
        "y_small_delta",
        "y_large_delta",
        "x_gradient_xlarge_minus_xsmall",
        "y_gradient_ylarge_minus_ysmall",
        "strongest_point",
        "strongest_point_delta",
        "case_id",
    ]
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in report["summaries"]:
            writer.writerow({field: row.get(field, "") for field in fields})

    print(f"written: {json_path}")
    print(f"written: {csv_path}")


def print_recommendations(report: dict) -> None:
    print("Point groups:")
    for name, points in report["point_groups"].items():
        print(f"  {name}: {points}")

    print("\nTop candidates:")
    for name, rows in report["recommendations"].items():
        print(f"  {name}:")
        for row in rows[:3]:
            print(
                "    port={port:2d} level={level:.3f} "
                "center={center_delta:+.3f} xgrad={x_gradient_xlarge_minus_xsmall:+.3f} "
                "ygrad={y_gradient_ylarge_minus_ysmall:+.3f} dominant={dominant_group}:{dominant_value:+.3f}".format(**row)
            )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Analyze MT4 port direction mapping.")
    parser.add_argument("--baseline", required=True, help="MT4 baseline summary jsonl")
    parser.add_argument("--port-scan", required=True, help="MT4 port-scan summary jsonl")
    parser.add_argument("--output-dir", default="MT4_outputs/port_mapping")
    args = parser.parse_args(argv)

    report = analyze(args.baseline, args.port_scan)
    write_outputs(report, args.output_dir)
    print_recommendations(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
