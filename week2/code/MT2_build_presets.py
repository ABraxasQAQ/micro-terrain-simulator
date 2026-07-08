"""Build usable terrain presets from MT2 scan outputs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from MT1_terrain_presets import save_preset


PORT_NUM = 16
DEFAULT_CENTER_POINTS = [6, 7, 10, 11]


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
        return [0.0 for _ in range(PORT_NUM)]
    result = []
    for idx in range(PORT_NUM):
        result.append(mean([float(row["z_values"][idx]) for row in good]))
    return result


def center_delta(row: dict, baseline_z: List[float]) -> float:
    indices = [point - 1 for point in DEFAULT_CENTER_POINTS]
    current = mean([float(row["z_values"][idx]) for idx in indices])
    baseline = mean([baseline_z[idx] for idx in indices])
    return current - baseline


def choose_pattern(rows: List[dict], pattern: str, baseline_z: List[float], target_delta: float, max_delta: float) -> Optional[dict]:
    candidates = [
        row for row in rows
        if row.get("success") and row.get("scan_type") == "pattern_scan" and row.get("pattern") == pattern
    ]
    if not candidates:
        return None

    for row in candidates:
        row["center_delta"] = center_delta(row, baseline_z)

    in_range = [
        row for row in candidates
        if abs(float(row["center_delta"])) >= target_delta and abs(float(row["center_delta"])) <= max_delta
    ]
    pool = in_range if in_range else candidates
    return sorted(pool, key=lambda row: abs(abs(float(row["center_delta"])) - target_delta))[0]


def build_presets(
    summary_path: str,
    target_delta: float,
    max_delta: float,
    baseline_summary_path: Optional[str] = None,
) -> dict:
    rows = load_jsonl(summary_path)
    if baseline_summary_path:
        rows.extend(load_jsonl(baseline_summary_path))
    baseline_rows = [row for row in rows if row.get("scan_type") == "baseline"]
    baseline_z = average_z(baseline_rows)

    report = {
        "summary_path": summary_path,
        "baseline_summary_path": baseline_summary_path,
        "baseline_count": len(baseline_rows),
        "baseline_z": baseline_z,
        "generated": [],
        "warnings": [],
    }

    flat_voltage = [0.0 for _ in range(PORT_NUM)]
    save_preset(
        "flat",
        flat_voltage,
        target_z=baseline_z,
        measured_z=baseline_z,
        error=0.0,
        notes="MT2 generated flat baseline preset.",
    )
    report["generated"].append({"name": "flat", "voltage": flat_voltage})

    for pattern in ["center_bump", "one_side_slope"]:
        chosen = choose_pattern(rows, pattern, baseline_z, target_delta, max_delta)
        if not chosen:
            report["warnings"].append(f"no successful pattern scan found for {pattern}")
            continue

        target_z = list(baseline_z)
        for point in DEFAULT_CENTER_POINTS:
            target_z[point - 1] = baseline_z[point - 1] + target_delta

        save_preset(
            pattern,
            [float(value) for value in chosen["voltage"]],
            target_z=target_z,
            measured_z=[float(value) for value in chosen["z_values"]],
            error=abs(float(chosen.get("center_delta", 0.0)) - target_delta),
            notes=(
                "MT2 generated from pattern scan. "
                f"source_case={chosen.get('case_id')} center_delta={chosen.get('center_delta')}"
            ),
        )
        report["generated"].append(
            {
                "name": pattern,
                "source_case": chosen.get("case_id"),
                "level": chosen.get("level"),
                "ports": chosen.get("ports"),
                "center_delta": chosen.get("center_delta"),
                "voltage": chosen.get("voltage"),
            }
        )

    with Path("MT2_preset_report.json").open("w", encoding="utf-8") as handle:
        json.dump(report, handle, ensure_ascii=False, indent=2, sort_keys=True)

    return report


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Generate MT1_presets from an MT2 scan summary.")
    parser.add_argument("summary_jsonl", help="Path to MT2_summary.jsonl from a pattern scan session.")
    parser.add_argument("--baseline-summary", default=None, help="Optional MT2_summary.jsonl from the baseline session.")
    parser.add_argument("--target-delta", type=float, default=0.2)
    parser.add_argument("--max-delta", type=float, default=0.35)
    args = parser.parse_args(argv)

    report = build_presets(
        args.summary_jsonl,
        args.target_delta,
        args.max_delta,
        baseline_summary_path=args.baseline_summary,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
