"""MT4 response scan helper.

This is not the final controller.  It only measures baseline and single-port
responses so we can choose active ports, initial voltages, and MATLAB bounds.
"""

from __future__ import annotations

import argparse
import csv
import json
import shutil
import time
from pathlib import Path
from typing import Dict, List, Optional, Sequence

from MT1_shape_measure import load_average_pos, run_once_from_current_voltage
from MT1_terrain_presets import write_current_voltage


PORT_NUM = 16
SUMMARY_JSONL = "MT4_summary.jsonl"
SUMMARY_CSV = "MT4_summary.csv"


def now_id() -> str:
    return time.strftime("%Y%m%d_%H%M%S")


def mean(values: Sequence[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def voltage_vector(port_levels: Dict[int, float]) -> List[float]:
    values = [0.0 for _ in range(PORT_NUM)]
    for port, level in port_levels.items():
        if port < 1 or port > PORT_NUM:
            raise ValueError(f"port must be 1..16, got {port}")
        values[port - 1] = float(level)
    return values


def read_z_values(path: str | Path = "AveragePos.txt") -> List[float]:
    shape = load_average_pos(path)
    return [float(row[2]) for row in shape]


def copy_if_exists(src: str | Path, dst_dir: Path) -> None:
    src = Path(src)
    if src.exists():
        shutil.copy2(src, dst_dir / src.name)


def append_jsonl(path: Path, payload: dict) -> None:
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, ensure_ascii=False, sort_keys=True))
        handle.write("\n")


def append_csv(path: Path, payload: dict) -> None:
    fields = [
        "case_id",
        "scan_type",
        "ports",
        "level",
        "repeat",
        "success",
        "z_mean",
        "z_min",
        "z_max",
        "center_z_mean",
        "case_dir",
    ]
    exists = path.exists()
    with path.open("a", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        if not exists:
            writer.writeheader()
        writer.writerow({field: payload.get(field, "") for field in fields})


def make_session_dir(root: str | Path, label: str) -> Path:
    session_dir = Path(root) / f"{now_id()}_{label}"
    session_dir.mkdir(parents=True, exist_ok=True)
    return session_dir


def save_case(
    session_dir: Path,
    case_id: str,
    scan_type: str,
    ports: Sequence[int],
    level: float,
    repeat: int,
    skip_frames: int,
    max_total_abs_voltage: float,
    mock_average_pos: Optional[str] = None,
) -> dict:
    case_dir = session_dir / case_id
    case_dir.mkdir(parents=True, exist_ok=True)

    voltage = voltage_vector({port: level for port in ports})
    write_current_voltage(voltage, "CurrentVoltage.dat")

    payload = {
        "case_id": case_id,
        "scan_type": scan_type,
        "ports": list(ports),
        "level": float(level),
        "repeat": int(repeat),
        "voltage": voltage,
        "case_dir": str(case_dir),
        "success": False,
    }

    try:
        run_once_from_current_voltage(
            current_voltage_path="CurrentVoltage.dat",
            average_pos_path="AveragePos.txt",
            measure_log_path="measure_log.json",
            skip_frames=skip_frames,
            max_total_abs_voltage=max_total_abs_voltage,
            mock_average_pos=mock_average_pos,
        )
        z_values = read_z_values("AveragePos.txt")
        center_indices = [5, 6, 9, 10]
        payload.update(
            {
                "success": True,
                "z_values": z_values,
                "z_mean": mean(z_values),
                "z_min": min(z_values),
                "z_max": max(z_values),
                "center_z_mean": mean([z_values[idx] for idx in center_indices]),
            }
        )
    except Exception as exc:
        payload.update({"success": False, "error": str(exc)})

    for filename in [
        "CurrentVoltage.dat",
        "CurrentPortVoltages.txt",
        "AveragePos.txt",
        "measure_log.json",
        "ResultPath.dat",
    ]:
        copy_if_exists(filename, case_dir)

    with (case_dir / "MT4_case_meta.json").open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2, sort_keys=True)

    append_jsonl(session_dir / SUMMARY_JSONL, payload)
    append_csv(session_dir / SUMMARY_CSV, payload)
    print(
        f"{case_id}: success={payload['success']} "
        f"level={level:.3f} ports={list(ports)} dir={case_dir}"
    )
    return payload


def run_baseline(args: argparse.Namespace) -> Path:
    session_dir = make_session_dir(args.output_root, "baseline")
    for repeat in range(1, args.repeats + 1):
        save_case(
            session_dir,
            f"baseline_r{repeat:02d}",
            "baseline",
            [],
            0.0,
            repeat,
            args.skip_frames,
            args.max_total_abs_voltage,
            args.mock_average_pos,
        )
    print(f"baseline session saved: {session_dir}")
    return session_dir


def run_port_scan(args: argparse.Namespace) -> Path:
    session_dir = make_session_dir(args.output_root, "port_scan")
    for port in args.ports:
        for level in args.levels:
            for repeat in range(1, args.repeats + 1):
                save_case(
                    session_dir,
                    f"port{port:02d}_v{level:.3f}_r{repeat:02d}".replace(".", "p"),
                    "port_scan",
                    [port],
                    level,
                    repeat,
                    args.skip_frames,
                    args.max_total_abs_voltage,
                    args.mock_average_pos,
                )
    print(f"port scan session saved: {session_dir}")
    return session_dir


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="MT4 baseline and port response scan.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    def add_common(subparser: argparse.ArgumentParser) -> None:
        subparser.add_argument("--output-root", default="MT4_runs")
        subparser.add_argument("--skip-frames", type=int, default=500)
        subparser.add_argument("--max-total-abs-voltage", type=float, default=0.51)
        subparser.add_argument("--mock-average-pos", default=None)

    baseline = subparsers.add_parser("baseline")
    add_common(baseline)
    baseline.add_argument("--repeats", type=int, default=5)
    baseline.set_defaults(func=run_baseline)

    port_scan = subparsers.add_parser("port-scan")
    add_common(port_scan)
    port_scan.add_argument("--ports", type=int, nargs="+", default=[2, 6, 7, 10, 11])
    port_scan.add_argument("--levels", type=float, nargs="+", default=[0.0, 0.1, 0.2, 0.3])
    port_scan.add_argument("--repeats", type=int, default=1)
    port_scan.set_defaults(func=run_port_scan)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
