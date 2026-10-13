"""CSV logger for Py5cheSim simulation runs."""
import csv
import os
from datetime import datetime

class CSVLogger:
    def __init__(self, log_dir="Logs"):
        os.makedirs(log_dir, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.filepath = os.path.join(log_dir, f"slice_log_{timestamp}.csv")

        self.file = open(self.filepath, "w", newline="", encoding="utf-8")
        self.writer = csv.writer(self.file)
        self.writer.writerow([
            "wall_time", "sim_time_ms", "slice", "num_ues",
            "prbs_allocated", "sent_packets", "lost_packets", "plr_pct",
            "rcvd_bytes", "throughput_mbps", "buffer_packets",
            "avg_sinr_db", "avg_mcs", "numerology_khz",
        ])
        self.file.flush()
        self.prev_rcvd = {}
        print(f"[CSVLogger] Writing to {self.filepath}")

    def log_row(self, sim_time_ms, slice_label, sch_dl, slice_obj):
        conn_ues = list(sch_dl.ues.keys())
        sent = lost = rcvd = 0
        sinr_sum = mcs_sum = 0.0

        for ue in conn_ues:
            flow = sch_dl.ues[ue].packetFlows[0]
            sent += flow.sentPackets
            lost += flow.lostPackets
            rcvd += flow.rcvdBytes
            sinr_sum += sch_dl.ues[ue].radioLinks.linkQuality
            mcs_sum += sch_dl.ues[ue].MCS

        n = max(len(conn_ues), 1)
        avg_sinr = sinr_sum / n
        avg_mcs = mcs_sum / n
        plr = 100.0 * lost / sent if sent > 0 else 0.0
        buffer_pkts = sch_dl.updSumPcks()

        prev = self.prev_rcvd.get(slice_label, 0)
        delta_bytes = rcvd - prev
        throughput = delta_bytes * 8 / 1000 / max(slice_obj.ttiBms, 1)
        self.prev_rcvd[slice_label] = rcvd

        self.writer.writerow([
            datetime.now().strftime("%H:%M:%S"),
            int(sim_time_ms), slice_label, len(conn_ues),
            slice_obj.PRBs, sent, lost, round(plr, 3),
            rcvd, round(throughput, 4), buffer_pkts,
            round(avg_sinr, 2), round(avg_mcs, 2),
            int(slice_obj.ttiBms * 15),
        ])
        self.file.flush()

    def close(self):
        self.file.close()
        print(f"[CSVLogger] Closed {self.filepath}")