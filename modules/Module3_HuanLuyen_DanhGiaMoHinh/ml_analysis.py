# -*- coding: utf-8 -*-
"""
Kiểm chứng NHANH bằng scikit-learn (KHÔNG cần Spark) — chống leakage theo feature_signature.
Mục đích: xác nhận nhanh các con số trong báo cáo trước khi chạy pipeline Spark thật.

Chạy:  python ml_analysis.py
Xuất:  artifacts/metrics/metrics.json  +  artifacts/metrics/confusion_group_aware.csv

===================== MỤC LỤC FILE =====================
[QUAN TRỌNG] Con số chuẩn phải ra khi chạy: rows=1000 · unique_signatures=152 ·
             duplicated=848 · conflicts=0 · train=697/test=303 · overlap=0 ·
             LR acc=1.0 · RF acc=1.0 (khớp báo cáo).
[QUAN TRỌNG] group_aware_split() — cùng quy tắc sha256(signature + seed) với
             src/ml/split.py; kết quả nhạy với quy tắc xếp nhóm nên 2 file PHẢI đồng bộ.
[QUAN TRỌNG] StandardScaler chỉ fit trên TRAIN rồi transform test (không fit trên test);
             chỉ LR cần scale (age lệch thang với chỉ số 1–9), RF không cần.
Phần còn lại: signature() (SHA-256 như schema.py), in kết quả, ghi json/csv.
=========================================================
"""
import os, sys, json, csv, hashlib
import pandas as pd
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import accuracy_score, f1_score, confusion_matrix

sys.path.append(os.path.join(os.path.dirname(__file__), "src"))
from common.schema import FEATURE_COLUMNS, LABELS, LABEL_TO_INDEX  # noqa: E402

CSV = os.path.join("data", "processed", "cancer_patients_ml_ready.csv")
OUT_DIR = os.path.join("artifacts", "metrics")
SEED = 42
TRAIN_RATIO = 0.70


def signature(row) -> str:
    return hashlib.sha256("|".join(str(int(float(row[c]))) for c in FEATURE_COLUMNS).encode()).hexdigest()


def group_aware_split(df):
    """Chia theo GROUP (feature_signature), phân tầng theo level, mỗi lớp có mặt cả 2 phía.
    Thứ tự nhóm deterministic theo sha256(signature + seed) — CÙNG quy tắc với src/ml/split.py,
    tái lập đúng split đã kiểm chứng: train=697, test=303, overlap=0."""
    groups = df[["feature_signature", "level"]].drop_duplicates("feature_signature")
    train_sigs, test_sigs = set(), set()
    for lv in LABELS:
        sigs = sorted(groups[groups["level"] == lv]["feature_signature"].tolist(),
                      key=lambda s: hashlib.sha256(f"{s}{SEED}".encode()).hexdigest())
        n = len(sigs)
        k = max(1, min(n - 1, round(n * TRAIN_RATIO)))  # đảm bảo cả train & test có group
        train_sigs.update(sigs[:k])
        test_sigs.update(sigs[k:])
    assert len(train_sigs & test_sigs) == 0, "signature overlap != 0"
    tr = df[df["feature_signature"].isin(train_sigs)]
    te = df[df["feature_signature"].isin(test_sigs)]
    return tr, te, len(train_sigs & test_sigs)


def main():
    df = pd.read_csv(CSV, encoding="utf-8-sig")
    df["level"] = df["level"].astype(str).str.strip().str.title()
    df["feature_signature"] = df.apply(signature, axis=1)

    # ----- baseline check -----
    uniq = df["feature_signature"].nunique()
    dup_rows = len(df) - uniq
    conflicts = int((df.groupby("feature_signature")["level"].nunique() > 1).sum())
    print(f"[BASELINE CHECK] rows={len(df)} unique_signatures={uniq} "
          f"duplicated_feature_rows={dup_rows} signature_label_conflicts={conflicts}")

    tr, te, overlap = group_aware_split(df)
    print(f"[GROUP SPLIT]    rows_train={len(tr)} rows_test={len(te)} signature_overlap={overlap}")

    Xtr = tr[FEATURE_COLUMNS].astype(float).values
    Xte = te[FEATURE_COLUMNS].astype(float).values
    ytr = tr["level"].map(LABEL_TO_INDEX).astype(int).values
    yte = te["level"].map(LABEL_TO_INDEX).astype(int).values

    scaler = StandardScaler().fit(Xtr)
    results = {}
    confusions = {}
    models = {
        "LogisticRegression": (LogisticRegression(max_iter=300, C=100.0), True),
        "RandomForest": (RandomForestClassifier(n_estimators=100, max_depth=10, random_state=SEED), False),
    }
    for name, (clf, scale) in models.items():
        a_tr, a_te = (scaler.transform(Xtr), scaler.transform(Xte)) if scale else (Xtr, Xte)
        clf.fit(a_tr, ytr)
        pred = clf.predict(a_te)
        acc = accuracy_score(yte, pred)
        mf1 = f1_score(yte, pred, average="macro")
        cm = confusion_matrix(yte, pred, labels=[0, 1, 2])
        results[name] = {"accuracy": round(float(acc), 4), "macro_f1": round(float(mf1), 4)}
        confusions[name] = cm.tolist()
        print(f"{name}: acc={acc:.4g} macroF1={mf1:.4g}")

    os.makedirs(OUT_DIR, exist_ok=True)
    out = {"baseline": {"rows": len(df), "unique_signatures": uniq,
                        "duplicated_feature_rows": dup_rows, "signature_label_conflicts": conflicts},
           "split": {"rows_train": len(tr), "rows_test": len(te), "signature_overlap": overlap},
           "label_order": LABELS, "models": results, "confusion_matrices": confusions,
           "note": "group-aware split theo feature_signature, đánh giá 1 lần trên test"}
    with open(os.path.join(OUT_DIR, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)
    with open(os.path.join(OUT_DIR, "confusion_group_aware.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        for name, cm in confusions.items():
            w.writerow([f"# {name} (rows=Low/Med/High actual, cols=predicted)"])
            for i, r in enumerate(cm):
                w.writerow([LABELS[i]] + r)
    print(f"[OK] wrote {OUT_DIR}/metrics.json + confusion_group_aware.csv")


if __name__ == "__main__":
    main()
