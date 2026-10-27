"""Test the trained slice classifier on the held-out test split.

SHAP-free version — produces metrics, confusion matrix, per-class
accuracy, and a detailed predictions CSV.
"""
import os
import joblib
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score, f1_score
)

DATA_DIR = "data/split"
MODEL_DIR = "models"
FIG_DIR = "Figures"
OUT_DIR = "data/test_results"

FEATURE_COLS = [
    "num_packets", "duration_s", "total_bytes", "throughput_mbps",
    "packet_rate_pps", "pkt_size_mean", "pkt_size_std",
    "pkt_size_min", "pkt_size_max",
    "iat_mean_ms", "iat_std_ms", "iat_min_ms", "iat_max_ms",
    "protocol",
]


def main():
    os.makedirs(FIG_DIR, exist_ok=True)
    os.makedirs(OUT_DIR, exist_ok=True)

    print("Loading model...")
    model = joblib.load(os.path.join(MODEL_DIR, "slice_classifier_xgb.pkl"))
    le    = joblib.load(os.path.join(MODEL_DIR, "label_encoder.pkl"))
    print(f"Classes: {list(le.classes_)}")

    test_df = pd.read_csv(os.path.join(DATA_DIR, "test.csv"))
    print(f"Test rows: {len(test_df)}")
    print(f"Label distribution:\n{test_df['slice_label'].value_counts()}")

    X_test = test_df[FEATURE_COLS].values
    y_test = test_df["slice_label"].values
    y_test_enc = le.transform(y_test)

    print("\nRunning predictions...")
    y_pred_enc = model.predict(X_test)
    y_pred = le.inverse_transform(y_pred_enc)

    acc = accuracy_score(y_test_enc, y_pred_enc)
    f1_macro = f1_score(y_test_enc, y_pred_enc, average="macro")
    f1_weighted = f1_score(y_test_enc, y_pred_enc, average="weighted")

    print(f"\n=== Overall Metrics ===")
    print(f"Accuracy:        {acc:.4f}")
    print(f"Macro F1:        {f1_macro:.4f}")
    print(f"Weighted F1:     {f1_weighted:.4f}")

    print(f"\n=== Classification Report ===")
    print(classification_report(y_test_enc, y_pred_enc,
                                target_names=le.classes_, digits=4))

    print("=== Per-Class Accuracy ===")
    per_class = {}
    for cls in le.classes_:
        mask = y_test == cls
        if mask.sum() == 0:
            continue
        class_acc = (y_pred[mask] == cls).mean()
        per_class[cls] = (mask.sum(), class_acc)
        print(f"  {cls:8s}: {class_acc*100:.2f}%  ({mask.sum()} samples)")

    cm = confusion_matrix(y_test_enc, y_pred_enc, labels=range(len(le.classes_)))
    plt.figure(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=le.classes_, yticklabels=le.classes_)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(f"Test Set Confusion Matrix (acc={acc:.3f})")
    plt.tight_layout()
    out1 = os.path.join(FIG_DIR, "test_confusion_matrix.png")
    plt.savefig(out1, dpi=120)
    plt.close()
    print(f"\nSaved {out1}")

    labels = list(per_class.keys())
    counts = [per_class[l][0] for l in labels]
    accs   = [per_class[l][1] * 100 for l in labels]

    plt.figure(figsize=(8, 5))
    bars = plt.bar(labels, accs, color=["#1f77b4", "#2ca02c", "#ff7f0e"][:len(labels)])
    for bar, n, a in zip(bars, counts, accs):
        plt.text(bar.get_x() + bar.get_width()/2, bar.get_height() + 1,
                 f"{a:.1f}%\n(n={n})", ha="center", va="bottom", fontsize=11)
    plt.ylim(0, 110)
    plt.ylabel("Recall (%)")
    plt.title("Per-Class Test Recall")
    plt.grid(axis="y", alpha=0.3)
    plt.tight_layout()
    out2 = os.path.join(FIG_DIR, "test_per_class_accuracy.png")
    plt.savefig(out2, dpi=120)
    plt.close()
    print(f"Saved {out2}")

    out_df = test_df.copy()
    out_df["predicted"] = y_pred
    out_df["correct"] = (out_df["predicted"] == out_df["slice_label"])
    out3 = os.path.join(OUT_DIR, "test_predictions.csv")
    out_df.to_csv(out3, index=False)
    print(f"Saved detailed predictions → {out3}")

    misclassified = out_df[~out_df["correct"]]
    n_wrong = len(misclassified)
    print(f"\n=== Misclassified flows: {n_wrong} of {len(out_df)} ===")

    if n_wrong > 0:
        print(f"\nAll {n_wrong} misclassifications:")
        for i, (_, row) in enumerate(misclassified.iterrows(), 1):
            print(f"\n  [{i}] true={row['slice_label']:8s}  pred={row['predicted']:8s}")
            print(f"      pkt_size_mean={row['pkt_size_mean']:.1f}  "
                  f"pkt_size_std={row['pkt_size_std']:.1f}  "
                  f"iat_mean_ms={row['iat_mean_ms']:.2f}  "
                  f"throughput_mbps={row['throughput_mbps']:.4f}  "
                  f"protocol={int(row['protocol'])}")
    else:
        print("No misclassifications — perfect test accuracy.")


if __name__ == "__main__":
    main()