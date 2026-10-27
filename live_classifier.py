"""Live traffic classifier. Run in ml_env as Administrator."""
import time
import threading
import joblib
import numpy as np
from collections import defaultdict
from scapy.all import sniff, IP, TCP, UDP, get_if_list, conf
from shared_bus import update_section

MODEL_PATH = "models/slice_classifier_xgb.pkl"
ENCODER_PATH = "models/label_encoder.pkl"

# --- INTERFACE CONFIG ---
# Set to None to let Scapy auto-select the primary active Wi-Fi/Ethernet interface
INTERFACE = None

WINDOW_SECONDS = 2.0

FEATURE_COLS = [
    "num_packets", "duration_s", "total_bytes", "throughput_mbps",
    "packet_rate_pps", "pkt_size_mean", "pkt_size_std",
    "pkt_size_min", "pkt_size_max",
    "iat_mean_ms", "iat_std_ms", "iat_min_ms", "iat_max_ms",
    "protocol",
]

# --- Load model ---
print("[ML] Loading model...")
model = joblib.load(MODEL_PATH)
le = joblib.load(ENCODER_PATH)
print(f"[ML] Classes: {list(le.classes_)}")

# --- State ---
flow_buffers = defaultdict(list)
lock = threading.Lock()
packet_counter = {"total": 0, "ip": 0, "stored": 0}


def packet_handler(pkt):
    packet_counter["total"] += 1
    if IP not in pkt:
        return
        
    packet_counter["ip"] += 1
    try:
        src, dst, proto = pkt[IP].src, pkt[IP].dst, pkt[IP].proto
        sport = dport = 0
        if TCP in pkt:
            sport, dport = pkt[TCP].sport, pkt[TCP].dport
        elif UDP in pkt:
            sport, dport = pkt[UDP].sport, pkt[UDP].dport
    except Exception:
        return
    
    key = (src, dst, sport, dport, proto)
    with lock:
        flow_buffers[key].append((float(pkt.time), len(pkt)))
        packet_counter["stored"] += 1


def extract_features(pkts, protocol):
    sizes = np.array([p[1] for p in pkts], dtype=float)
    times = np.array(sorted(p[0] for p in pkts))
    iats = np.diff(times) * 1000.0
    duration = times[-1] - times[0] if len(times) > 1 else 0.0
    return {
        "num_packets": len(pkts),
        "duration_s": round(duration, 3),
        "total_bytes": int(sizes.sum()),
        "throughput_mbps": round((sizes.sum() * 8 / 1e6 / duration) if duration > 0 else 0, 4),
        "packet_rate_pps": round(len(pkts) / duration if duration > 0 else 0, 3),
        "pkt_size_mean": round(sizes.mean(), 2),
        "pkt_size_std": round(sizes.std(), 2),
        "pkt_size_min": int(sizes.min()),
        "pkt_size_max": int(sizes.max()),
        "iat_mean_ms": round(iats.mean(), 3) if len(iats) > 0 else 0.0,
        "iat_std_ms": round(iats.std(), 3) if len(iats) > 0 else 0.0,
        "iat_min_ms": round(iats.min(), 3) if len(iats) > 0 else 0.0,
        "iat_max_ms": round(iats.max(), 3) if len(iats) > 0 else 0.0,
        "protocol": int(protocol),
    }


def classifier_loop():
    while True:
        time.sleep(WINDOW_SECONDS)
        with lock:
            snapshot = dict(flow_buffers)
            flow_buffers.clear()
            stats = dict(packet_counter)

        predictions = []
        for key, pkts in snapshot.items():
            if len(pkts) < 3:
                continue
            feats = extract_features(pkts, key[4])
            X = np.array([[feats[c] for c in FEATURE_COLS]])
            pred_enc = model.predict(X)[0]
            pred_label = le.inverse_transform([pred_enc])[0]
            predictions.append({
                "src": f"{key[0]}:{key[2]}",
                "dst": f"{key[1]}:{key[3]}",
                "protocol": key[4],
                "predicted_slice": pred_label,
                "pkt_size_mean": feats["pkt_size_mean"],
                "iat_mean_ms": feats["iat_mean_ms"],
                "throughput_mbps": feats["throughput_mbps"],
            })

        update_section("classifier", {
            "timestamp": time.time(),
            "window_seconds": WINDOW_SECONDS,
            "num_flows": len(predictions),
            "predictions": predictions,
            "diagnostics": {
                "total_packets": stats["total"],
                "ip_packets": stats["ip"],
                "stored_packets": stats["stored"],
            },
        })
        print(f"[ML] Classified {len(predictions)} flows | "
              f"packets: total={stats['total']}, ip={stats['ip']}, stored={stats['stored']}")
        
        # Reset counters for the next window
        packet_counter["total"] = 0
        packet_counter["ip"] = 0
        packet_counter["stored"] = 0


def start_sniffing(iface):
    print(f"[ML] Sniffing on interface: {iface}")
    try:
        # Note: We use promisc=True so it sees all passing traffic
        sniff(iface=iface, prn=packet_handler, store=False, promisc=True)
    except Exception as e:
        print(f"[ML] Sniff error: {e}")
        print("[ML] Run this script as Administrator!")


if __name__ == "__main__":
    print("\n=== Available interfaces ===")
    for i, name in enumerate(get_if_list()):
        print(f"  [{i}] {name}")
    print(f"\nDefault interface (Scapy): {conf.iface}")

    iface = INTERFACE if INTERFACE else conf.iface
    print(f"\nUsing interface: {iface}\n")

    t = threading.Thread(target=start_sniffing, args=(iface,), daemon=True)
    t.start()

    try:
        classifier_loop()
    except KeyboardInterrupt:
        print("\n[ML] Stopped.")