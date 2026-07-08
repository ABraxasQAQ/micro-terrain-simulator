"""Export preset/calibration voltage vectors to MATLAB-friendly .dat files."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Sequence

from MT1_terrain_presets import load_voltage_for_terrain


def export_voltage(terrain: str, output: str, membrane: Optional[str] = None) -> Path:
    voltage = load_voltage_for_terrain(terrain, membrane_id=membrane)
    path = Path(output)
    with path.open("w", encoding="utf-8") as handle:
        for value in voltage:
            handle.write(f"{value:25.15f}\n")
    return path


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Export terrain voltage to a .dat file.")
    parser.add_argument("terrain")
    parser.add_argument("--membrane", default=None)
    parser.add_argument("--output", default=None)
    args = parser.parse_args(argv)

    output = args.output or f"{args.terrain}_voltage.dat"
    path = export_voltage(args.terrain, output, membrane=args.membrane)
    print(f"exported {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
