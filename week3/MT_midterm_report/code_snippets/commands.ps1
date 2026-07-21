# Hold one terrain preset
python .\MT_hold_preset.py left_down_corner --seconds 20

# Cycle two terrains with flat states and collect ant trajectory
python .\MT_cycle_terrain_track.py left_down_corner right_down_corner --hold-seconds 20 --flat-seconds 20 --cycles 1 --cameras 0 1 --plot-camera auto --debug-every 20

# Re-render an existing session
python .\MT_cycle_terrain_track.py --render-only .\MT_outputs\terrain_ant_tracks\session_YYYYMMDD_HHMMSS --plot-camera auto
