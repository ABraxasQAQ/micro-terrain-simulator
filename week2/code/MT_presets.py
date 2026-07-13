"""JSON helpers for optimized terrain voltage presets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List, Optional


PORT_NUM = 16
ROOT_DIR = Path(__file__).resolve().parent
PRESETS_DIR = ROOT_DIR / "MT_presets"
CALIBRATIONS_DIR = ROOT_DIR / "MT_calibrations"


def ensure_dirs() -> None:
    PRESETS_DIR.mkdir(exist_ok=True)
    CALIBRATIONS_DIR.mkdir(exist_ok=True)


def preset_path(name: str) -> Path:
    return PRESETS_DIR / f"{name}.json"


def calibration_path(membrane_id: str) -> Path:
    return CALIBRATIONS_DIR / f"{membrane_id}.json"


def load_json(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def save_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, sort_keys=True)


def validate_voltage(voltage: List[float], field_name: str = "voltage") -> List[float]:
    if len(voltage) != PORT_NUM:
        raise ValueError(f"{field_name} must contain {PORT_NUM} values, got {len(voltage)}")
    return [float(value) for value in voltage]


def load_preset(name: str) -> dict:
    path = preset_path(name)
    if not path.exists():
        raise FileNotFoundError(f"missing preset: {path}")
    payload = load_json(path)
    payload["voltage"] = validate_voltage(payload["voltage"])
    return payload


def load_voltage_for_terrain(name: str, membrane_id: Optional[str] = None) -> List[float]:
    preset = load_preset(name)
    voltage = preset["voltage"]

    if membrane_id:
        cpath = calibration_path(membrane_id)
        if cpath.exists():
            calibration = load_json(cpath)
            terrains = calibration.get("terrains", {})
            if name in terrains and "voltage" in terrains[name]:
                voltage = terrains[name]["voltage"]

    return validate_voltage(voltage)


def write_current_voltage(voltage: List[float], path: str | Path = "CurrentVoltage.dat") -> None:
    voltage = validate_voltage(voltage)
    with Path(path).open("w", encoding="utf-8") as handle:
        for value in voltage:
            handle.write(f"{value:25.15f}\n")


def create_preset_payload(
    name: str,
    voltage: List[float],
    target_z: Optional[List[float]] = None,
    measured_z: Optional[List[float]] = None,
    error: Optional[float] = None,
    max_total_abs_voltage: Optional[float] = None,
    notes: str = "",
) -> dict:
    payload = {
        "name": name,
        "voltage": validate_voltage(voltage),
        "target_z": target_z or [],
        "measured_z": measured_z or [],
        "error": error,
        "max_total_abs_voltage": max_total_abs_voltage,
        "notes": notes,
    }
    return payload


def save_preset(
    name: str,
    voltage: List[float],
    target_z: Optional[List[float]] = None,
    measured_z: Optional[List[float]] = None,
    error: Optional[float] = None,
    max_total_abs_voltage: Optional[float] = None,
    notes: str = "",
) -> Path:
    ensure_dirs()
    payload = create_preset_payload(
        name,
        voltage,
        target_z,
        measured_z,
        error,
        max_total_abs_voltage,
        notes,
    )
    path = preset_path(name)
    save_json(path, payload)
    return path


def list_presets() -> List[str]:
    ensure_dirs()
    return sorted(path.stem for path in PRESETS_DIR.glob("*.json"))
