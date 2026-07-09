"""Check the 4x4 measured point order and coordinate directions.

This script is a dry mapping helper.  It does not optimize terrain.  By default
it reads AveragePos.txt and prints the point grid inferred from x/y coordinates.
Use --measure-flat if you want it to first run a zero-voltage measurement.
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import List, Sequence

from MT1_shape_measure import load_average_pos, run_once_from_current_voltage
from MT1_terrain_presets import write_current_voltage


PORT_NUM = 16


def mean(values: Sequence[float]) -> float:
    return sum(values) / float(len(values)) if values else 0.0


def measure_flat(skip_frames: int, max_total_abs_voltage: float) -> None:
    write_current_voltage([0.0 for _ in range(PORT_NUM)], "CurrentVoltage.dat")
    run_once_from_current_voltage(
        current_voltage_path="CurrentVoltage.dat",
        average_pos_path="AveragePos.txt",
        measure_log_path="measure_log.json",
        skip_frames=skip_frames,
        max_total_abs_voltage=max_total_abs_voltage,
    )


def load_points(path: str | Path) -> List[List[float]]:
    points = load_average_pos(path)
    if len(points) != PORT_NUM:
        raise ValueError(f"Expected {PORT_NUM} points, got {len(points)}")
    return points


def print_grid(points: Sequence[Sequence[float]]) -> None:
    print("Point grid by file order:")
    for row in range(4):
        ids = [row * 4 + col + 1 for col in range(4)]
        print("  " + "  ".join(f"{point_id:2d}" for point_id in ids))

    print("\nCoordinates by point id:")
    print("  id          x          y          z")
    for idx, point in enumerate(points, start=1):
        print(f"  {idx:2d} {point[0]:10.3f} {point[1]:10.3f} {point[2]:10.3f}")

    rows = [[row * 4 + col for col in range(4)] for row in range(4)]
    cols = [[row * 4 + col for row in range(4)] for col in range(4)]
    row_x = [mean([points[idx][0] for idx in row]) for row in rows]
    row_y = [mean([points[idx][1] for idx in row]) for row in rows]
    col_x = [mean([points[idx][0] for idx in col]) for col in cols]
    col_y = [mean([points[idx][1] for idx in col]) for col in cols]

    print("\nRow means by file-order rows:")
    for row_id, (x_value, y_value) in enumerate(zip(row_x, row_y), start=1):
        print(f"  row {row_id}: mean_x={x_value:10.3f}, mean_y={y_value:10.3f}")

    print("\nColumn means by file-order columns:")
    for col_id, (x_value, y_value) in enumerate(zip(col_x, col_y), start=1):
        print(f"  col {col_id}: mean_x={x_value:10.3f}, mean_y={y_value:10.3f}")

    print("\nCurrent coordinate-side groups:")
    print("  x-small side: points 1, 2, 3, 4")
    print("  x-large side: points 13, 14, 15, 16")
    print("  y-small side: points 1, 5, 9, 13")
    print("  y-large side: points 4, 8, 12, 16")
    print("  center:       points 6, 7, 10, 11")
    print("\nName left/right/front/back only after matching x/y sides to the live camera view.")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check MT4 measured point mapping.")
    parser.add_argument("--average-pos", default="AveragePos.txt")
    parser.add_argument("--measure-flat", action="store_true", help="Measure zero-voltage shape before reading AveragePos.")
    parser.add_argument("--skip-frames", type=int, default=500)
    parser.add_argument("--max-total-abs-voltage", type=float, default=0.51)
    args = parser.parse_args(argv)

    if args.measure_flat:
        measure_flat(args.skip_frames, args.max_total_abs_voltage)

    points = load_points(args.average_pos)
    print_grid(points)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
