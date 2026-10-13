"""Plot PRB allocation and PLR over time from InterSlice stats."""
import matplotlib.pyplot as plt
import pandas as pd
import os

stats_file = "Statistics/dlStsts_InterSlice.txt"

# ---- Load: skip header, assign columns manually ----
# Header claims 8 columns but code writes 9 (adds pfSliceMetric at end)
col_names = ["time", "Slice", "Connections", "ResourceUse",
             "sntPackets", "lstPackets", "rcvdBytes", "bufferSize", "pfMetric"]

df = pd.read_csv(
    stats_file,
    sep=r"\s+",
    engine="python",
    skiprows=1,          # skip the header line
    names=col_names,
    header=None
)

# Convert to numeric where needed
for col in ["time", "Connections", "ResourceUse", "sntPackets",
            "lstPackets", "rcvdBytes", "bufferSize"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

df = df.dropna(subset=["time", "Slice"])
df = df.drop_duplicates()

# ---- Aggregate in case of duplicates ----
prb = df.groupby(["time", "Slice"], as_index=False)["ResourceUse"].mean()

# ---- Plot ----
fig, axes = plt.subplots(2, 1, figsize=(14, 10), sharex=True)

# Top: PRB allocation
for slice_name in prb["Slice"].unique():
    sub = prb[prb["Slice"] == slice_name].sort_values("time")
    axes[0].plot(sub["time"], sub["ResourceUse"],
                 label=slice_name, linewidth=1.5)
axes[0].set_ylabel("PRBs Allocated")
axes[0].set_title("Inter-Slice PRB Allocation Over Time")
axes[0].legend()
axes[0].grid(True, alpha=0.3)

# Bottom: PLR per interval
for slice_name in df["Slice"].unique():
    sub = df[df["Slice"] == slice_name].groupby("time", as_index=False).agg(
        {"sntPackets": "max", "lstPackets": "max"}
    ).sort_values("time")
    sub["delta_sent"] = sub["sntPackets"].diff().fillna(0)
    sub["delta_lost"] = sub["lstPackets"].diff().fillna(0)
    sub["plr"] = (sub["delta_lost"] / sub["delta_sent"].replace(0, 1)) * 100
    sub["plr"] = sub["plr"].clip(lower=0, upper=100)   # sanity clamp
    axes[1].plot(sub["time"], sub["plr"], label=slice_name, linewidth=1.5)

axes[1].set_xlabel("Time (ms)")
axes[1].set_ylabel("PLR (%)")
axes[1].set_title("Per-Interval Packet Loss Rate")
axes[1].legend()
axes[1].grid(True, alpha=0.3)

plt.tight_layout()
os.makedirs("Figures", exist_ok=True)
plt.savefig("Figures/prb_plr_timeline.png", dpi=120)
print("Saved: Figures/prb_plr_timeline.png")
plt.show()