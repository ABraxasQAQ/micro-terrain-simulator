"""Apply an optimized terrain preset and run one measurement."""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from MT_runtime import ensure_project_root
from MT_presets import load_preset, load_voltage_for_terrain, write_current_voltage

ensure_project_root()


DEFAULT_MAX_TOTAL_ABS_VOLTAGE = 0.51


def apply_terrain(
    name: str,
    membrane_id: Optional[str] = None,
    measure: bool = True,
    python_exe: str = sys.executable,
    max_total_abs_voltage: Optional[float] = None,
) -> None:
    voltage = load_voltage_for_terrain(name, membrane_id=membrane_id)
    if max_total_abs_voltage is None:
        preset = load_preset(name)
        max_total_abs_voltage = preset.get("max_total_abs_voltage")
    if max_total_abs_voltage is None:
        max_total_abs_voltage = max(DEFAULT_MAX_TOTAL_ABS_VOLTAGE, sum(abs(v) for v in voltage) + 0.01)

    write_current_voltage(voltage)
    print(f"wrote CurrentVoltage.dat for terrain={name} membrane={membrane_id or 'default'}")

    if measure:
        cmd = [
            python_exe,
            str(Path(__file__).with_name("MT_single_port.py")),
            "--max-total-abs-voltage",
            str(max_total_abs_voltage),
        ]
        print("running:", " ".join(cmd))
        subprocess.check_call(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply one terrain preset.")
    parser.add_argument("terrain")
    parser.add_argument("--membrane", default=None)
    parser.add_argument("--no-measure", action="store_true", help="Only write CurrentVoltage.dat.")
    parser.add_argument("--python", default=sys.executable, help="Python executable for MT_single_port.py.")
    parser.add_argument("--max-total-abs-voltage", type=float, default=None)
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    apply_terrain(
        args.terrain,
        membrane_id=args.membrane,
        measure=not args.no_measure,
        python_exe=args.python,
        max_total_abs_voltage=args.max_total_abs_voltage,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
