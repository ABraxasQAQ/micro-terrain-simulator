"""Save an MT5 MATLAB-optimized active-port voltage vector as an MT1 preset."""

from __future__ import annotations

import argparse
import json
import shutil
import time
from pathlib import Path
from typing import List, Sequence

from MT1_terrain_presets import save_preset


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


def write_final_report(name: str, preset_path: Path, voltage_file: Path, active_ports: Sequence[int], voltage: Sequence[float]) -> Path:
    report_dir = Path("MT5_outputs") / "final_presets"
    report_dir.mkdir(parents=True, exist_ok=True)
    stamp = time.strftime("%Y%m%d_%H%M%S")
    report_path = report_dir / f"{stamp}_{name}.json"
    payload = {
        "name": name,
        "preset_path": str(preset_path),
        "source_voltage_file": str(voltage_file),
        "active_ports": list(active_ports),
        "voltage": list(voltage),
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True), encoding="utf-8")
    shutil.copy2(preset_path, report_dir / f"{stamp}_{name}_preset.json")
    return report_path


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Save MT5 optimized voltage as MT1 preset.")
    parser.add_argument("name", help="Preset name, for example center_bump_strong")
    parser.add_argument("--active-ports", type=int, nargs="+", required=True)
    parser.add_argument("--voltage-file", default="TargetTerrainBestVoltage.dat")
    parser.add_argument("--notes", default="MT5 optimized preset from MATLAB patternsearch.")
    args = parser.parse_args(argv)

    voltage_file = Path(args.voltage_file)
    active_values = read_numbers(voltage_file)
    voltage = make_full_voltage(args.active_ports, active_values)
    path = save_preset(args.name, voltage, notes=args.notes)
    report_path = write_final_report(args.name, path, voltage_file, args.active_ports, voltage)
    print(f"saved {args.name}: {path}")
    print(f"final report: {report_path}")
    print("voltage:", voltage)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
