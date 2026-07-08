"""Apply an optimized terrain preset and run one measurement."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Optional, Sequence

from MT1_terrain_presets import load_voltage_for_terrain, write_current_voltage


def apply_terrain(
    name: str,
    membrane_id: Optional[str] = None,
    measure: bool = True,
    python_exe: str = sys.executable,
) -> None:
    voltage = load_voltage_for_terrain(name, membrane_id=membrane_id)
    write_current_voltage(voltage)
    print(f"wrote CurrentVoltage.dat for terrain={name} membrane={membrane_id or 'default'}")

    if measure:
        cmd = [python_exe, "MT1_SinglePort_wrapped.py"]
        print("running:", " ".join(cmd))
        subprocess.check_call(cmd)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Apply one terrain preset.")
    parser.add_argument("terrain")
    parser.add_argument("--membrane", default=None)
    parser.add_argument("--no-measure", action="store_true", help="Only write CurrentVoltage.dat.")
    parser.add_argument("--python", default=sys.executable, help="Python executable for MT1_SinglePort_wrapped.py.")
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    apply_terrain(
        args.terrain,
        membrane_id=args.membrane,
        measure=not args.no_measure,
        python_exe=args.python,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
