"""Merge per-slice feature CSVs, split 80/10/10 stratified, save train/val/test."""
import os
import pandas as pd
from sklearn.model_selection import train_test_split

DATA_ROOT = "data"
OUT_DIR = "data/split"

FEATURE_COLS = [
    "num_packets", "duration_s", "total_bytes", "throughput_mbps",
    "packet_rate_pps", "pkt_size_mean", "pkt_size_std",
    "pkt_size_min", "pkt_size_max",
    "iat_mean_ms", "iat_std_ms", "iat_min_ms", "iat_max_ms",
    "protocol",
]


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    # --- Load all slice CSVs ---
    dfs = []
    for name in ["embb", "urllc", "mmtc"]:
        path = os.path.join(DATA_ROOT, f"features_{name}.csv")
        if not os.path.exists(path):
            print(f"Warning: {path} not found, skipping.")
            continue
        df = pd.read_csv(path)
        print(f"Loaded {len(df)} rows from {name}")
        dfs.append(df)

    if not dfs:
        print("No feature CSVs found. Run extract_features.py first.")
        return

    data = pd.concat(dfs, ignore_index=True)
    print(f"\nTotal rows: {len(data)}")
    print(f"Label distribution:\n{data['slice_label'].value_counts()}")

    # --- Drop rows with NaNs in key features ---
    data = data.dropna(subset=FEATURE_COLS)
    print(f"Rows after dropna: {len(data)}")

    # --- Sanity: need at least 3 rows per class for stratified split ---
    counts = data["slice_label"].value_counts()
    if (counts < 3).any():
        print("\nERROR: Some classes have fewer than 3 samples. Collect more data.")
        print(counts)
        return

    # --- Shuffle for reproducibility ---
    data = data.sample(frac=1, random_state=42).reset_index(drop=True)

    # --- Stratified 80/10/10 split ---
    train_df, temp_df = train_test_split(
        data, test_size=0.20, stratify=data["slice_label"], random_state=42
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.50, stratify=temp_df["slice_label"], random_state=42
    )

    print(f"\nSplit sizes:")
    print(f"  Train:      {len(train_df)} ({len(train_df)/len(data)*100:.1f}%)")
    print(f"  Validation: {len(val_df)} ({len(val_df)/len(data)*100:.1f}%)")
    print(f"  Test:       {len(test_df)} ({len(test_df)/len(data)*100:.1f}%)")

    print(f"\nTrain label distribution:\n{train_df['slice_label'].value_counts()}")
    print(f"\nVal label distribution:\n{val_df['slice_label'].value_counts()}")
    print(f"\nTest label distribution:\n{test_df['slice_label'].value_counts()}")

    train_df.to_csv(os.path.join(OUT_DIR, "train.csv"), index=False)
    val_df.to_csv(os.path.join(OUT_DIR, "val.csv"), index=False)
    test_df.to_csv(os.path.join(OUT_DIR, "test.csv"), index=False)

    print(f"\nSaved:")
    print(f"  {OUT_DIR}/train.csv")
    print(f"  {OUT_DIR}/val.csv")
    print(f"  {OUT_DIR}/test.csv")


if __name__ == "__main__":
    main()