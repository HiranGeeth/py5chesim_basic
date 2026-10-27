"""Live state emitter for dashboard visualization."""
import json
import os
import time
from shared_bus import update_section

STATE_FILE = "Statistics/live_state.json"
EVENT_LOG = "Statistics/events.jsonl"
def emit_state(time_ms, slices_data, extra=None):
    """Write current simulation state to JSON file for live dashboard."""
    state = {
        "time_ms": time_ms,
        "wall_time": time.time(),
        "slices": slices_data,
        "extra": extra or {},
    }
    os.makedirs("Statistics", exist_ok=True)

    tmp = STATE_FILE + ".tmp"
    for attempt in range(5):
        try:
            with open(tmp, "w") as f:
                json.dump(state, f)
            os.replace(tmp, STATE_FILE)
            return
        except PermissionError:
            time.sleep(0.05 * (attempt + 1))
        except Exception as e:
            print(f"[emit_state] error: {e}")
            return

    # Last-ditch fallback: write directly (dashboard may read partial file)
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"[emit_state] fallback failed: {e}")
    update_section("allocator", {
        "time_ms": time_ms,
        "slices": slices_data,
    })
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