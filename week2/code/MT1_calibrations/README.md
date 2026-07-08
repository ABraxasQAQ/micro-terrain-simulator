# Membrane Calibrations

Optional per-membrane voltage overrides live here.

File name: `<membrane_id>.json`

Example:

```json
{
  "membrane_id": "membrane_01",
  "notes": "Optimized on teacher PC.",
  "terrains": {
    "center_bump": {
      "voltage": [0, 0, 0, 0, 0, 0.12, 0.11, 0, 0, 0.10, 0.13, 0, 0, 0, 0, 0],
      "error": 0.0,
      "measured_z": []
    }
  }
}
```

Use:

```bash
python MT1_apply_terrain.py center_bump --membrane membrane_01
```
