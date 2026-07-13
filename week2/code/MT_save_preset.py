"""Save an MT MATLAB-optimized active-port voltage vector as an MT preset."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import List, Optional, Sequence

from MT_presets import save_preset


PORT_NUM = 16


def read_numbers(path: str | Path) -> List[float]:
    text = Path(path).read_text(encoding="utf-8")
    return [float(part) for part in text.split()]


def make_full_voltage(active_ports: Sequence[int], active_values: Sequence[float]) -> List[float]:
    if len(active_ports) != len(active_values):
        raise ValueError("active port count and voltage count do not match")
    voltage = [0.0 for _ in range(PORT_NUM)]
    for port, value in zip(active_ports, active_values):
        if port < 1 or port > PORT_NUM:
            raise ValueError(f"port must be 1..16, got {port}")
        voltage[port - 1] = float(value)
    return voltage


def read_summary_limit(voltage_file: Path) -> Optional[float]:
    summary_path = voltage_file.parent / "MT_optimization_summary.txt"
    if not summary_path.exists():
        return None
    for line in summary_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        if line.startswith("max_total_abs_voltage="):
            return float(line.split("=", 1)[1].strip())
    return None


def write_final_report(
    name: str,
    preset_path: Path,
    voltage_file: Path,
    active_ports: Sequence[int],
    voltage: Sequence[float],
    max_total_abs_voltage: Optional[float],
) -> Path:
    report_dir = Path("MT_outputs") / "final_presets"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"{stamp}_{name}.json"
    payload = {
        "name": name,
        "preset_path": str(preset_path),
        "source_voltage_file": str(voltage_file),
        "active_ports": list(active_ports),
        "voltage": list(voltage),
        "max_total_abs_voltage": max_total_abs_voltage,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    shutil.copy2(preset_path, report_dir / f"{stamp}_{name}_preset.json")
    return report_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save MT optimized voltage as an MT preset.")
    parser.add_argument("name", help="Preset name, for example center_bump_strong")
    parser.add_argument("--active-ports", type=int, nargs="+", required=True)
    parser.add_argument("--voltage-file", default="TargetTerrainBestVoltage.dat")
    parser.add_argument("--notes", default="MT optimized preset from MATLAB patternsearch.")
    args = parser.parse_args(argv)

    voltage_file = Path(args.voltage_file)
    active_values = read_numbers(voltage_file)
    voltage = make_full_voltage(args.active_ports, active_values)
    max_total_abs_voltage = read_summary_limit(voltage_file)
    path = save_preset(
        args.name,
        voltage,
        max_total_abs_voltage=max_total_abs_voltage,
        notes=args.notes,
    )
    report_path = write_final_report(
        args.name,
        path,
        voltage_file,
        args.active_ports,
        voltage,
        max_total_abs_voltage,
    )
    print(f"saved {args.name}: {path}")
    print(f"final report: {report_path}")
    print("max_total_abs_voltage:", max_total_abs_voltage)
    print("voltage:", voltage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
