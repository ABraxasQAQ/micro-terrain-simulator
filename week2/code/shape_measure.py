"""Measurement wrapper for the existing micro-terrain hardware pipeline.

This module keeps the old MATLAB/Python file protocol:

MATLAB writes CurrentVoltage.dat -> Python measures -> Python writes AveragePos.txt

It intentionally does not change opencv_wrapper or the C++ build.  The public
entry point for MATLAB is SinglePort_wrapped.py.
"""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
import time
import traceback
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Sequence, Tuple

POINT_GRID_N = 4
DEFAULT_PORT_NUM = 16
DEFAULT_VFS = 10.0
DEFAULT_ACTUATION_TIME = 5.0
DEFAULT_ACTUATION_WAIT_TIME = 5
DEFAULT_SKIP_FRAMES = 500
DEFAULT_MAX_TOTAL_ABS_VOLTAGE = 0.51


@dataclass
class VoltageProgram:
    port_num: int
    time_points: List[float]
    voltages: List[List[float]]
    source_format: str

    @property
    def point_num(self) -> int:
        return POINT_GRID_N * POINT_GRID_N

    @property
    def last_voltage(self) -> List[float]:
        return list(self.voltages[-1])

    @property
    def total_time(self) -> int:
        if not self.time_points:
            return int(DEFAULT_ACTUATION_TIME)
        return max(1, int(round(max(self.time_points))))


def calculate_packet(port_id: int, input_voltage: float, vfs: float = DEFAULT_VFS) -> bytes:
    voltage = max(-vfs, min(vfs, float(input_voltage)))
    dac12 = int(round((voltage + vfs) / (2.0 * vfs) * 4095.0))
    dac12 = max(0, min(4095, dac12))
    packet = (port_id << 12) | dac12
    return struct.pack(">H", packet)


def _read_numeric_lines(path: Path) -> List[List[float]]:
    rows: List[List[float]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            parts = line.split()
            if parts:
                rows.append([float(item) for item in parts])
    return rows


def load_voltage_from_matlab(path: str | Path = "CurrentVoltage.dat") -> VoltageProgram:
    """Read either the old 16-line static file or the dynamic MATLAB format."""
    path = Path(path)
    rows = _read_numeric_lines(path)
    if not rows:
        raise ValueError(f"{path} is empty")

    first = rows[0]
    if len(first) == 2 and int(first[0]) == first[0] and int(first[1]) == first[1]:
        port_num = int(first[0])
        time_num = int(first[1])
        expected_rows = 1 + 2 * time_num
        if len(rows) < expected_rows:
            raise ValueError(
                f"{path} declares {time_num} time points but has only {len(rows)} numeric rows"
            )

        time_points: List[float] = []
        voltages: List[List[float]] = []
        for idx in range(time_num):
            time_row = rows[1 + 2 * idx]
            voltage_row = rows[2 + 2 * idx]
            if len(time_row) != 1:
                raise ValueError(f"dynamic time row {idx + 1} must contain one value")
            if len(voltage_row) != port_num:
                raise ValueError(
                    f"dynamic voltage row {idx + 1} has {len(voltage_row)} values, expected {port_num}"
                )
            time_points.append(float(time_row[0]))
            voltages.append([float(v) for v in voltage_row])

        if time_points[-1] < DEFAULT_ACTUATION_TIME:
            time_points.append(DEFAULT_ACTUATION_TIME)
            voltages.append(list(voltages[-1]))
        return VoltageProgram(port_num, time_points, voltages, "dynamic")

    flat_values = [row[0] for row in rows]
    if len(flat_values) != DEFAULT_PORT_NUM:
        raise ValueError(
            f"static CurrentVoltage.dat must contain {DEFAULT_PORT_NUM} voltage rows; got {len(flat_values)}"
        )

    return VoltageProgram(
        DEFAULT_PORT_NUM,
        [0.0, DEFAULT_ACTUATION_TIME],
        [list(flat_values), list(flat_values)],
        "static",
    )


def validate_voltage_program(
    program: VoltageProgram,
    max_total_abs_voltage: float = DEFAULT_MAX_TOTAL_ABS_VOLTAGE,
) -> None:
    for idx, voltage_row in enumerate(program.voltages):
        total = sum(abs(float(v)) for v in voltage_row)
        if total > max_total_abs_voltage:
            raise ValueError(
                f"total absolute voltage at step {idx} is {total:.6f}, "
                f"exceeds limit {max_total_abs_voltage:.6f}"
            )


def write_port_voltage_schedule(
    program: VoltageProgram,
    path: str | Path = "CurrentPortVoltages.txt",
    vfs: float = DEFAULT_VFS,
) -> None:
    path = Path(path)
    with path.open("w", encoding="utf-8") as handle:
        for time_point, voltage_row in zip(program.time_points, program.voltages):
            bin_list = []
            for port_id in range(program.port_num):
                data_bytes = calculate_packet(port_id, voltage_row[port_id], vfs)
                packet_value = int.from_bytes(data_bytes, byteorder="big", signed=False)
                bin_list.append(format(packet_value, "016b"))
            handle.write(f"{time_point * 1000.0:.3f} {' '.join(bin_list)}\n")


def run_dynamic_actuation(
    program: VoltageProgram,
    actuation_wait_time: int = DEFAULT_ACTUATION_WAIT_TIME,
    import_normal: bool = True,
    save_image: bool = False,
) -> None:
    import opencv_wrapper  # Imported here so offline parser tests do not need the .pyd.
    import numpy as np

    port_voltages = np.array(program.last_voltage, dtype=np.float32)
    opencv_wrapper.DynamicActuation(
        port_voltages,
        program.port_num,
        actuation_wait_time,
        program.total_time,
        False,  # user_quit
        False,  # voltage_mock
        False,  # LogSwitchOff
        False,  # ActuationInSitu
        False,  # OutputInitialPos
        import_normal,
        save_image,
    )


def read_result_path(path: str | Path = "ResultPath.dat") -> Path:
    path = Path(path)
    with path.open("r", encoding="utf-8") as handle:
        result_path = handle.readline().strip()
    if not result_path:
        raise ValueError(f"{path} does not contain a result path")
    return Path(result_path)


def compute_average_pos(
    result_path: str | Path,
    skip_frames: int = DEFAULT_SKIP_FRAMES,
    point_num: int = POINT_GRID_N * POINT_GRID_N,
    raw_output_path: str | Path = "TestAveragePos.txt",
) -> Tuple[List[List[float]], int]:
    result_path = Path(result_path)
    results_file = result_path / "results.txt"
    if not results_file.exists():
        raise FileNotFoundError(f"missing results file: {results_file}")

    pos_sum = [[0.0, 0.0, 0.0] for _ in range(point_num)]
    point_count = 0
    line_count = 0

    with results_file.open("r", encoding="utf-8") as source, Path(raw_output_path).open(
        "w", encoding="utf-8"
    ) as raw_out:
        for line in source:
            line = line.strip()
            line_count += 1
            if not line:
                break
            if line_count <= 1 + skip_frames:
                continue

            parts = line.split()
            point_count += 1
            frame_values: List[float] = []
            for point_idx in range(point_num):
                base = 45 + 3 * point_idx
                xyz = []
                for offset in range(3):
                    try:
                        xyz.append(float(parts[base + offset]))
                    except Exception:
                        xyz.append(0.0)
                for offset in range(3):
                    pos_sum[point_idx][offset] += xyz[offset]
                frame_values.extend(xyz)

            raw_out.write("".join(f"{value:25.15f}" for value in frame_values))
            raw_out.write("\n")

    if point_count <= 0:
        raise ValueError(
            f"no frames remained after skip_frames={skip_frames} in {results_file}"
        )

    return [
        [value / float(point_count) for value in row]
        for row in pos_sum
    ], point_count


def save_average_pos(shape: Sequence[Sequence[float]], path: str | Path = "AveragePos.txt") -> None:
    if len(shape) != POINT_GRID_N * POINT_GRID_N:
        raise ValueError(f"AveragePos shape must contain 16 rows, got {len(shape)}")
    with Path(path).open("w", encoding="utf-8") as handle:
        for row in shape:
            if len(row) < 3:
                raise ValueError("AveragePos rows must contain at least 3 values")
            handle.write("".join(f"{value:25.15f}" for value in row))
            handle.write("\n")


def load_average_pos(path: str | Path = "AveragePos.txt") -> List[List[float]]:
    rows = _read_numeric_lines(Path(path))
    if len(rows) != POINT_GRID_N * POINT_GRID_N:
        raise ValueError(f"{path} must contain 16 rows, got {len(rows)}")
    shape: List[List[float]] = []
    for row in rows:
        if len(row) < 3:
            raise ValueError(f"{path} must contain at least 3 columns")
        shape.append([float(row[0]), float(row[1]), float(row[2])])
    return shape


def write_measure_log(path: str | Path, payload: dict) -> None:
    with Path(path).open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def run_once_from_current_voltage(
    current_voltage_path: str | Path = "CurrentVoltage.dat",
    average_pos_path: str | Path = "AveragePos.txt",
    measure_log_path: str | Path = "measure_log.json",
    skip_frames: int = DEFAULT_SKIP_FRAMES,
    max_total_abs_voltage: float = DEFAULT_MAX_TOTAL_ABS_VOLTAGE,
    mock_average_pos: Optional[str | Path] = None,
) -> List[List[float]]:
    started_at = time.strftime("%Y-%m-%d %H:%M:%S")
    log = {
        "started_at": started_at,
        "success": False,
        "current_voltage_path": str(current_voltage_path),
        "average_pos_path": str(average_pos_path),
        "skip_frames": skip_frames,
        "error": "",
    }

    try:
        program = load_voltage_from_matlab(current_voltage_path)
        validate_voltage_program(program, max_total_abs_voltage=max_total_abs_voltage)
        write_port_voltage_schedule(program)

        log.update(
            {
                "source_format": program.source_format,
                "port_num": program.port_num,
                "time_points": program.time_points,
                "voltage_last": program.last_voltage,
                "max_total_abs_voltage": max_total_abs_voltage,
            }
        )

        if mock_average_pos:
            shape = load_average_pos(mock_average_pos)
            result_path = ""
            point_count = 0
        else:
            run_dynamic_actuation(program)
            result_path = str(read_result_path())
            shape, point_count = compute_average_pos(result_path, skip_frames=skip_frames)

        save_average_pos(shape, average_pos_path)
        log.update(
            {
                "success": True,
                "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "result_path": result_path,
                "point_count": point_count,
                "point_num": len(shape),
                "z_min": min(row[2] for row in shape),
                "z_max": max(row[2] for row in shape),
                "z_mean": sum(row[2] for row in shape) / float(len(shape)),
            }
        )
        write_measure_log(measure_log_path, log)
        return shape
    except Exception as exc:
        log.update(
            {
                "success": False,
                "finished_at": time.strftime("%Y-%m-%d %H:%M:%S"),
                "error": str(exc),
                "traceback": traceback.format_exc(),
            }
        )
        write_measure_log(measure_log_path, log)
        raise


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run one terrain shape measurement.")
    parser.add_argument("--current-voltage", default="CurrentVoltage.dat")
    parser.add_argument("--average-pos", default="AveragePos.txt")
    parser.add_argument("--log", default="measure_log.json")
    parser.add_argument("--skip-frames", type=int, default=DEFAULT_SKIP_FRAMES)
    parser.add_argument("--max-total-abs-voltage", type=float, default=DEFAULT_MAX_TOTAL_ABS_VOLTAGE)
    parser.add_argument(
        "--mock-average-pos",
        default=None,
        help="Offline mode: copy/validate an existing AveragePos file without hardware.",
    )
    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    run_once_from_current_voltage(
        current_voltage_path=args.current_voltage,
        average_pos_path=args.average_pos,
        measure_log_path=args.log,
        skip_frames=args.skip_frames,
        max_total_abs_voltage=args.max_total_abs_voltage,
        mock_average_pos=args.mock_average_pos,
    )
    print(f"measurement complete: {args.average_pos}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
