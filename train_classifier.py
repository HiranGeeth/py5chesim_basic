"""Train XGBoost slice classifier on the prepared dataset.

Loads train/val/test from data/split/, trains XGBoost,
evaluates on validation and test, saves model + label encoder.
"""
import os
import joblib
import pandas as pd
import numpy as np
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix, accuracy_score, f1_score
)
import matplotlib.pyplot as plt
import seaborn as sns
import xgboost as xgb

DATA_DIR = "data/split"
MODEL_DIR = "models"
FEATURE_COLS = [
    "num_packets", "duration_s", "total_bytes", "throughput_mbps",
    "packet_rate_pps", "pkt_size_mean", "pkt_size_std",
    "pkt_size_min", "pkt_size_max",
    "iat_mean_ms", "iat_std_ms", "iat_min_ms", "iat_max_ms",
    "protocol",
]


def load_split(name):
    df = pd.read_csv(os.path.join(DATA_DIR, f"{name}.csv"))
    X = df[FEATURE_COLS].values
    y = df["slice_label"].values
    return X, y, df


def main():
    os.makedirs(MODEL_DIR, exist_ok=True)
    os.makedirs("Figures", exist_ok=True)

    print("Loading data...")
    X_train, y_train, _ = load_split("train")
    X_val, y_val, _ = load_split("val")
    X_test, y_test, test_df = load_split("test")

    print(f"Train: {X_train.shape}, Val: {X_val.shape}, Test: {X_test.shape}")

    # Encode labels to integers
    le = LabelEncoder()
    y_train_enc = le.fit_transform(y_train)
    y_val_enc = le.transform(y_val)
    y_test_enc = le.transform(y_test)
    print(f"Classes: {list(le.classes_)}")

    # --- Build and train XGBoost ---
    print("\nTraining XGBoost...")
    model = xgb.XGBClassifier(
        n_estimators=200,
        max_depth=5,
        learning_rate=0.1,
        objective="multi:softprob",
        num_class=len(le.classes_),
        subsample=0.9,
        colsample_bytree=0.9,
        eval_metric="mlogloss",
        random_state=42,
        use_label_encoder=False,
    )
    from sklearn.utils.class_weight import compute_class_weight


    # Compute class weights (inverse frequency)
    classes = np.unique(y_train_enc)
    weights = compute_class_weight("balanced", classes=classes, y=y_train_enc)
    class_weight = dict(zip(classes, weights))
    print(f"\nClass weights (higher = rarer):")
    for c, w in class_weight.items():
        print(f"  {le.classes_[c]}: {w:.3f}")

    # Apply to each training sample
    sample_weights = np.array([class_weight[c] for c in y_train_enc])

    model.fit(
        X_train, y_train_enc,
        sample_weight=sample_weights,
        eval_set=[(X_train, y_train_enc), (X_val, y_val_enc)],
        verbose=False,
    )
    # --- Validation metrics ---
    y_val_pred = model.predict(X_val)
    val_acc = accuracy_score(y_val_enc, y_val_pred)
    val_f1 = f1_score(y_val_enc, y_val_pred, average="macro")
    print(f"\nValidation accuracy: {val_acc:.4f}")
    print(f"Validation macro-F1: {val_f1:.4f}")

    # --- Test metrics ---
    y_test_pred = model.predict(X_test)
    test_acc = accuracy_score(y_test_enc, y_test_pred)
    test_f1 = f1_score(y_test_enc, y_test_pred, average="macro")
    print(f"\nTest accuracy: {test_acc:.4f}")
    print(f"Test macro-F1: {test_f1:.4f}")

    print("\n=== Test Classification Report ===")
    print(classification_report(y_test_enc, y_test_pred,
                                target_names=le.classes_))

    # --- Confusion matrix ---
    cm = confusion_matrix(y_test_enc, y_test_pred)
    plt.figure(figsize=(7, 5))
    sns.heatmap(cm, annot=True, fmt="d", cmap="Blues",
                xticklabels=le.classes_, yticklabels=le.classes_)
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.title(f"XGBoost Test Confusion Matrix (acc={test_acc:.3f})")
    plt.tight_layout()
    plt.savefig("Figures/confusion_matrix.png", dpi=120)
    print("Saved Figures/confusion_matrix.png")

    # --- Feature importance ---
    importances = model.feature_importances_
    order = np.argsort(importances)[::-1]
    plt.figure(figsize=(10, 6))
    plt.barh(
        [FEATURE_COLS[i] for i in order][::-1],
        importances[order][::-1],
    )
    plt.xlabel("Importance")
    plt.title("XGBoost Feature Importance")
    plt.tight_layout()
    plt.savefig("Figures/feature_importance.png", dpi=120)
    print("Saved Figures/feature_importance.png")

    # --- Save model + encoder ---
    joblib.dump(model, os.path.join(MODEL_DIR, "slice_classifier_xgb.pkl"))
    joblib.dump(le, os.path.join(MODEL_DIR, "label_encoder.pkl"))
    joblib.dump(FEATURE_COLS, os.path.join(MODEL_DIR, "feature_cols.pkl"))
    print(f"\nSaved model → {MODEL_DIR}/slice_classifier_xgb.pkl")
    print(f"Saved encoder → {MODEL_DIR}/label_encoder.pkl")


if __name__ == "__main__":
    main()