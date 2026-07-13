"""Quickly apply a hand-picked high-voltage terrain candidate.

This is only for fast amplitude probing.  Final presets should still come from
MT MATLAB optimization.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Sequence

from MT_runtime import ensure_project_root
from MT_presets import save_preset, write_current_voltage

ensure_project_root()


PORT_NUM = 16
DEFAULT_LABEL = "center_up_rim_positive_probe"
DEFAULT_PORTS = [14, 12, 11, 13, 9, 16, 10, 7]
DEFAULT_VALUES = [0.55, 0.50, 0.35, 0.30, 0.16, 0.14, 0.10, 0.08]
DEFAULT_MAX_TOTAL_ABS_VOLTAGE = 2.20
ARCHIVE_FILES = [
    "CurrentVoltage.dat",
    "CurrentPortVoltages.txt",
    "AveragePos.txt",
    "measure_log.json",
    "ResultPath.dat",
]


def make_run_dir(label: str) -> Path:
    root = Path("MT_outputs") / "quick_tests"
    root.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    run_dir = root / f"{stamp}_{label}"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


def make_voltage(ports: Sequence[int], values: Sequence[float]) -> List[float]:
    if len(ports) != len(values):
        raise ValueError("ports and values must have the same length")
    voltage = [0.0 for _ in range(PORT_NUM)]
    for port, value in zip(ports, values):
        if port < 1 or port > PORT_NUM:
            raise ValueError(f"port must be 1..16, got {port}")
        voltage[port - 1] = float(value)
    return voltage


def archive_files(run_dir: Path, suffix: str) -> None:
    suffix_part = f"_{suffix}" if suffix else ""
    for filename in ARCHIVE_FILES:
        path = Path(filename)
        if path.exists():
            target = run_dir / f"{path.stem}{suffix_part}{path.suffix}"
            shutil.copy2(path, target)


def run_measurement(python_exe: str, max_total_abs_voltage: float) -> None:
    cmd = [
        python_exe,
        str(Path(__file__).with_name("MT_single_port.py")),
        "--max-total-abs-voltage",
        str(max_total_abs_voltage),
    ]
    print("running:", " ".join(cmd))
    subprocess.check_call(cmd)


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Quickly apply a direct voltage candidate.")
    parser.add_argument("--label", default=DEFAULT_LABEL)
    parser.add_argument("--ports", type=int, nargs="+", default=DEFAULT_PORTS)
    parser.add_argument("--values", type=float, nargs="+", default=DEFAULT_VALUES)
    parser.add_argument("--max-total-abs-voltage", type=float, default=DEFAULT_MAX_TOTAL_ABS_VOLTAGE)
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--save-preset", default=None, help="Optional preset name to save before measuring.")
    parser.add_argument("--no-measure", action="store_true")
    parser.add_argument("--skip-baseline", action="store_true")
    args = parser.parse_args(argv)

    voltage = make_voltage(args.ports, args.values)
    total = sum(abs(value) for value in voltage)
    if total > args.max_total_abs_voltage:
        raise ValueError(
            f"total voltage {total:.6f} exceeds --max-total-abs-voltage {args.max_total_abs_voltage:.6f}"
        )

    print("label:", args.label)
    print("ports:", args.ports)
    print("values:", args.values)
    print("total_abs_voltage:", total)
    print("max_total_abs_voltage:", args.max_total_abs_voltage)

    if args.save_preset:
        path = save_preset(
            args.save_preset,
            voltage,
            max_total_abs_voltage=args.max_total_abs_voltage,
            notes="MT quick high-voltage candidate; not MATLAB optimized.",
        )
        print(f"saved preset: {path}")

    if not args.no_measure:
        run_dir = make_run_dir(args.label)

        if not args.skip_baseline:
            print("step 1/2: measuring zero-voltage baseline")
            write_current_voltage([0.0 for _ in range(PORT_NUM)])
            run_measurement(args.python, args.max_total_abs_voltage)
            archive_files(run_dir, "baseline")

        print("measuring quick-test voltage")
        write_current_voltage(voltage)
        run_measurement(args.python, args.max_total_abs_voltage)
        archive_files(run_dir, "quicktest")

        print(f"archived quick-test files to: {run_dir}")
    else:
        write_current_voltage(voltage)
        print("wrote CurrentVoltage.dat")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
