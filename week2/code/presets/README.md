# Terrain Presets

Each terrain preset is a JSON file named `<terrain>.json`.

Required field:

- `voltage`: 16 numbers in the same channel order used by `CurrentVoltage.dat`.

Recommended fields:

- `name`: terrain id, for example `center_bump`.
- `target_z`: 16 target z values.
- `measured_z`: 16 measured z values from the optimization result.
- `error`: final optimization error.
- `notes`: short human notes.

Example:

```json
{
  "name": "center_bump",
  "voltage": [0, 0, 0, 0, 0, 0.1, 0.1, 0, 0, 0.1, 0.1, 0, 0, 0, 0, 0],
  "target_z": [],
  "measured_z": [],
  "error": null,
  "notes": "Replace with MATLAB optimized voltage before hardware test."
}
```
