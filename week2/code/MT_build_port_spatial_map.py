"""Build a reusable port spatial-response table from an MT mapping CSV.

The mapping CSV describes how each electrical port changes the measured 4x4 point
grid.  This script converts that response table into a compact MT table that
can be used to choose active ports for terrain optimization.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from pathlib import Path
from typing import Dict, List, Sequence


GROUP_FIELDS = [
    "center_delta",
    "x_small_delta",
    "x_large_delta",
    "y_small_delta",
    "y_large_delta",
]


def read_rows(path: str | Path) -> List[dict]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def as_float(row: dict, key: str) -> float:
    return float(row[key])


def group_changes(row: dict, base: dict) -> Dict[str, float]:
    return {field: as_float(row, field) - as_float(base, field) for field in GROUP_FIELDS}


def edge_mean(changes: Dict[str, float]) -> float:
    fields = ["x_small_delta", "x_large_delta", "y_small_delta", "y_large_delta"]
    return sum(changes[field] for field in fields) / float(len(fields))


def strongest_group(changes: Dict[str, float]) -> tuple[str, float]:
    return max(changes.items(), key=lambda item: abs(item[1]))


def choose_best(rows: Sequence[dict], base: dict, score_name: str) -> tuple[dict, Dict[str, float], float]:
    best_row = rows[0]
    best_changes = group_changes(best_row, base)
    best_score = score(best_changes, score_name)
    for row in rows[1:]:
        changes = group_changes(row, base)
        value = score(changes, score_name)
        if value > best_score:
            best_row = row
            best_changes = changes
            best_score = value
    return best_row, best_changes, best_score


def score(changes: Dict[str, float], score_name: str) -> float:
    center = changes["center_delta"]
    edges = edge_mean(changes)
    if score_name == "center_up":
        return center
    if score_name == "rim_down":
        return -edges
    if score_name == "center_contrast":
        return center - edges
    raise ValueError(f"unknown score: {score_name}")


def role_from_scores(center_up: float, rim_down: float, contrast: float) -> str:
    if center_up >= 0.25 and contrast >= 0.15:
        return "center_up_candidate"
    if rim_down >= 0.10 and center_up <= 0.10:
        return "rim_shape_candidate"
    if contrast >= 0.15:
        return "contrast_candidate"
    return "weak_or_mixed"


def build_table(rows: Sequence[dict]) -> List[dict]:
    by_port: Dict[int, List[dict]] = {}
    for row in rows:
        port = int(float(row["port"]))
        by_port.setdefault(port, []).append(row)

    table: List[dict] = []
    for port, port_rows in sorted(by_port.items()):
        port_rows = sorted(port_rows, key=lambda item: as_float(item, "level"))
        base_rows = [row for row in port_rows if abs(as_float(row, "level")) < 1e-12]
        if not base_rows:
            continue
        base = base_rows[0]
        active_rows = [row for row in port_rows if as_float(row, "level") > 0.0]
        if not active_rows:
            continue

        center_row, center_changes, center_score = choose_best(active_rows, base, "center_up")
        rim_row, rim_changes, rim_score = choose_best(active_rows, base, "rim_down")
        contrast_row, contrast_changes, contrast_score = choose_best(active_rows, base, "center_contrast")
        dominant_name, dominant_value = strongest_group(contrast_changes)
        table.append(
            {
                "port": port,
                "role": role_from_scores(center_score, rim_score, contrast_score),
                "best_center_level": as_float(center_row, "level"),
                "best_center_change": center_score,
                "best_rim_down_level": as_float(rim_row, "level"),
                "best_rim_down_score": rim_score,
                "best_contrast_level": as_float(contrast_row, "level"),
                "best_contrast_score": contrast_score,
                "contrast_center_change": contrast_changes["center_delta"],
                "contrast_edge_mean_change": edge_mean(contrast_changes),
                "contrast_x_small_change": contrast_changes["x_small_delta"],
                "contrast_x_large_change": contrast_changes["x_large_delta"],
                "contrast_y_small_change": contrast_changes["y_small_delta"],
                "contrast_y_large_change": contrast_changes["y_large_delta"],
                "dominant_spatial_group": dominant_name.replace("_delta", ""),
                "dominant_spatial_change": dominant_value,
            }
        )
    return table


def write_outputs(table: Sequence[dict], output_dir: str | Path) -> tuple[Path, Path]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    csv_path = output_dir / f"{stamp}_MT_port_spatial_map.csv"
    json_path = output_dir / f"{stamp}_MT_port_spatial_map.json"

    fields = list(table[0].keys()) if table else []
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(table)

    payload = {
        "created_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "meaning": {
            "best_center_change": "largest center group increase relative to this port's level=0 row",
            "best_rim_down_score": "positive means edge groups moved downward on average",
            "best_contrast_score": "center_change - edge_mean_change; larger is better for center bump",
        },
        "table": list(table),
    }
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    return csv_path, json_path


def print_summary(table: Sequence[dict]) -> None:
    center = sorted(table, key=lambda row: row["best_center_change"], reverse=True)[:6]
    rim = sorted(table, key=lambda row: row["best_rim_down_score"], reverse=True)[:6]
    contrast = sorted(table, key=lambda row: row["best_contrast_score"], reverse=True)[:6]

    print("Top center-up ports:")
    for row in center:
        print(
            "  port={port:2d} level={best_center_level:.2f} center={best_center_change:+.3f} role={role}".format(**row)
        )

    print("Top rim-down/edge-shaping ports:")
    for row in rim:
        print(
            "  port={port:2d} level={best_rim_down_level:.2f} rim_down_score={best_rim_down_score:+.3f} role={role}".format(**row)
        )

    print("Top center-vs-rim contrast ports:")
    for row in contrast:
        print(
            "  port={port:2d} level={best_contrast_level:.2f} contrast={best_contrast_score:+.3f} dominant={dominant_spatial_group}:{dominant_spatial_change:+.3f}".format(**row)
        )


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build MT port spatial map from MT port mapping CSV.")
    parser.add_argument("--mt4-csv", required=True)
    parser.add_argument("--output-dir", default="MT_outputs/port_spatial_map")
    args = parser.parse_args(argv)

    table = build_table(read_rows(args.mt4_csv))
    csv_path, json_path = write_outputs(table, args.output_dir)
    print(f"written: {csv_path}")
    print(f"written: {json_path}")
    print_summary(table)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
