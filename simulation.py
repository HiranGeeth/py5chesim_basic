"""
Live Resource Allocator
-----------------------
Runs continuously in real-time.
Reads live classifier predictions from the shared bus.
Computes PRB allocations based on observed traffic weights.
Writes allocation state back to the shared bus.
"""
import time
import os
from shared_bus import read_state, update_section

# -----------------------------------------------------------------
# Allocator Configuration
# -----------------------------------------------------------------
TOTAL_PRBS = 160          # 30 MHz at 15 kHz SCS = 160 PRBs
MIN_WEIGHT = 0.10         # Give every slice at least 10% to prevent starvation
UPDATE_INTERVAL = 0.5     # Seconds between allocation updates
LABEL_MAP = {
    "embb":  "embb-0",
    "urllc": "urllc-0",
    "mmtc":  "mmtc-0",
}

# -----------------------------------------------------------------
# Main Loop
# -----------------------------------------------------------------
def main():
    print("="*60)
    print("🚀 LIVE RESOURCE ALLOCATOR STARTED")
    print(f"Total PRBs available: {TOTAL_PRBS}")
    print(f"Update interval: {UPDATE_INTERVAL}s")
    print("="*60)

    # Keep track of our own internal state so the dashboard has data 
    # even before the first classifier window finishes.
    current_allocations = {
        "embb-0": TOTAL_PRBS // 3,
        "urllc-0": TOTAL_PRBS // 3,
        "mmtc-0": TOTAL_PRBS // 3,
    }

    try:
        while True:
            time.sleep(UPDATE_INTERVAL)
            
            # 1. Read live data from the ML classifier
            state = read_state()
            cls = state.get("classifier", {})
            predictions = cls.get("predictions", [])

            if not predictions:
                # If ML hasn't reported yet, just keep the previous allocation 
                # but push it to the dashboard so the UI isn't blank.
                pass
            else:
                # 2. Count the predicted slices
                counts = {"embb-0": 0, "urllc-0": 0, "mmtc-0": 0}
                for p in predictions:
                    label = p.get("predicted_slice", "").lower()
                    slice_name = LABEL_MAP.get(label)
                    if slice_name:
                        counts[slice_name] += 1

                total_preds = sum(counts.values())
                
                if total_preds > 0:
                    # 3. Compute weights (with a minimum floor to avoid starvation)
                    weights = {}
                    for k, v in counts.items():
                        raw_weight = v / total_preds
                        weights[k] = max(raw_weight, MIN_WEIGHT)
                    
                    # Re-normalize so weights sum exactly to 1.0
                    weight_sum = sum(weights.values())
                    weights = {k: v / weight_sum for k, v in weights.items()}

                    # 4. Calculate PRB allocations
                    for slice_name, weight in weights.items():
                        current_allocations[slice_name] = int(TOTAL_PRBS * weight)

                    # Print to terminal
                    print(f"[Allocator] Live flows: {total_preds} | "
                          f"eMBB: {current_allocations['embb-0']} PRBs | "
                          f"URLLC: {current_allocations['urllc-0']} PRBs | "
                          f"mMTC: {current_allocations['mmtc-0']} PRBs")

            # 5. Push the finalized allocation to the shared bus for the dashboard
            # We include some dummy PLR and Throughput to keep the UI happy.
            slices_data = {}
            for slice_name, prbs in current_allocations.items():
                slices_data[slice_name] = {
                    "prbs": prbs,
                    "plr": 0.0,
                    "throughput": (prbs / TOTAL_PRBS) * 100, # Fake throughput for UI visual
                    "buffer": 0
                }

            update_section("allocator", {
                "time_ms": int(time.time() * 1000) % 100000, # Just a rolling counter for UI
                "slices": slices_data
            })

    except KeyboardInterrupt:
        print("\n[Allocator] Stopped by user.")

if __name__ == "__main__":
    main()