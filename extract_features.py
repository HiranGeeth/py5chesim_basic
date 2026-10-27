"""Extract per-flow features from pcapng files for slice classification.

Reads data/<slice>/*.pcapng, groups packets by 5-tuple flow,
computes statistical features, writes data/features_<slice>.csv
"""
import os
import glob
import numpy as np
import pandas as pd
from scapy.all import rdpcap, IP, TCP, UDP, ICMP

DATA_ROOT = "data"
SLICES = ["embb", "urllc", "mmtc"]

# Minimum packets per flow to be considered a real flow
MIN_PACKETS = 3

# Max flows per pcapng (to keep data balanced)
MAX_FLOWS_PER_FILE = 500


def extract_flow_features(packets):
    """Given a list of packets from ONE flow, return a dict of features."""
    sizes = np.array([len(p) for p in packets], dtype=float)
    times = np.array(sorted(float(p.time) for p in packets))
    iats = np.diff(times) * 1000.0  # convert to ms

    duration = times[-1] - times[0] if len(times) > 1 else 0.0
    total_bytes = sizes.sum()

    throughput_mbps = (total_bytes * 8 / 1e6 / duration) if duration > 0 else 0.0
    packet_rate_pps = len(packets) / duration if duration > 0 else 0.0

    return {
        "num_packets": len(packets),
        "duration_s": round(duration, 3),
        "total_bytes": int(total_bytes),
        "throughput_mbps": round(throughput_mbps, 4),
        "packet_rate_pps": round(packet_rate_pps, 3),
        "pkt_size_mean": round(sizes.mean(), 2),
        "pkt_size_std": round(sizes.std(), 2),
        "pkt_size_min": int(sizes.min()),
        "pkt_size_max": int(sizes.max()),
        "iat_mean_ms": round(iats.mean(), 3) if len(iats) > 0 else 0.0,
        "iat_std_ms": round(iats.std(), 3) if len(iats) > 0 else 0.0,
        "iat_min_ms": round(iats.min(), 3) if len(iats) > 0 else 0.0,
        "iat_max_ms": round(iats.max(), 3) if len(iats) > 0 else 0.0,
    }


def process_pcap(pcap_path):
    """Read a pcapng, group into flows, return list of feature dicts."""
    print(f"  Reading {os.path.basename(pcap_path)}...")
    try:
        packets = rdpcap(pcap_path)
    except Exception as e:
        print(f"    ERROR reading: {e}")
        return []

    # Group by 5-tuple, handling all protocol types safely
    flows = {}
    for pkt in packets:
        if IP not in pkt:
            continue

        src = pkt[IP].src
        dst = pkt[IP].dst
        proto = pkt[IP].proto  # 6=TCP, 17=UDP, 1=ICMP, etc.

        # Default port values for non-TCP/UDP
        sport = 0
        dport = 0

        try:
            if TCP in pkt:
                sport = pkt[TCP].sport
                dport = pkt[TCP].dport
            elif UDP in pkt:
                sport = pkt[UDP].sport
                dport = pkt[UDP].dport
            # ICMP or others: keep sport=dport=0, keep proto distinguishing
        except Exception:
            # Malformed packet — skip it entirely
            continue

        key = (src, dst, sport, dport, proto)
        flows.setdefault(key, []).append(pkt)

    # Compute features per flow
    rows = []
    for key, pkts in flows.items():
        if len(pkts) < MIN_PACKETS:
            continue
        try:
            feats = extract_flow_features(pkts)
        except Exception as e:
            print(f"    WARN: could not compute features for {key}: {e}")
            continue
        feats["src"] = key[0]
        feats["dst"] = key[1]
        feats["sport"] = key[2]
        feats["dport"] = key[3]
        feats["protocol"] = key[4]
        feats["pcap_file"] = os.path.basename(pcap_path)
        rows.append(feats)

    # Cap to MAX_FLOWS_PER_FILE
    if len(rows) > MAX_FLOWS_PER_FILE:
        rows = sorted(rows, key=lambda r: r["num_packets"], reverse=True)[:MAX_FLOWS_PER_FILE]

    print(f"    {len(rows)} flows extracted (from {len(flows)} total 5-tuple groups)")
    return rows

def main():
    for slice_name in SLICES:
        folder = os.path.join(DATA_ROOT, slice_name)
        if not os.path.isdir(folder):
            print(f"[{slice_name}] Folder not found: {folder}, skipping.")
            continue

        pcaps = glob.glob(os.path.join(folder, "*.pcapng"))
        if not pcaps:
            print(f"[{slice_name}] No .pcapng files in {folder}, skipping.")
            continue

        print(f"\n[{slice_name.upper()}] Processing {len(pcaps)} files...")
        all_rows = []
        for pcap in pcaps:
            rows = process_pcap(pcap)
            for r in rows:
                r["slice_label"] = slice_name
            all_rows.extend(rows)

        if not all_rows:
            print(f"[{slice_name}] No usable flows, skipping CSV.")
            continue

        df = pd.DataFrame(all_rows)
        out_path = os.path.join(DATA_ROOT, f"features_{slice_name}.csv")
        df.to_csv(out_path, index=False)
        print(f"[{slice_name}] Wrote {len(df)} flows → {out_path}")

    print("\nDone. Check data/ for features_*.csv files.")


if __name__ == "__main__":
    main()