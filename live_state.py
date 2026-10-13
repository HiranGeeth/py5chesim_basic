"""Live state emitter for dashboard visualization."""
import json
import os
import time

STATE_FILE = "Statistics/live_state.json"
EVENT_LOG = "Statistics/events.jsonl"

def emit_state(time_ms, slices_data, extra=None):
    """
    Write current simulation state to JSON file for live dashboard.
    
    slices_data: dict mapping slice_label -> {
        'prbs': int,
        'plr': float,
        'throughput': float,
        'buffer': int,
        'sinr': float,
        'mcs': float,
        'numerology': int,
    }
    """
    state = {
        "time_ms": time_ms,
        "wall_time": time.time(),
        "slices": slices_data,
        "extra": extra or {},
    }
    os.makedirs("Statistics", exist_ok=True)
    # Atomic write to avoid dashboard reading half-written file
    tmp = STATE_FILE + ".tmp"
    with open(tmp, "w") as f:
        json.dump(state, f)
    os.replace(tmp, STATE_FILE)

def log_event(time_ms, slice_label, event_type, details=""):
    """Append a structured event for the event timeline."""
    os.makedirs("Statistics", exist_ok=True)
    event = {
        "t": time_ms,
        "slice": slice_label,
        "type": event_type,
        "details": details,
    }
    with open(EVENT_LOG, "a") as f:
        f.write(json.dumps(event) + "\n")