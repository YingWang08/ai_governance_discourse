#!/usr/bin/env python3
"""
10_supervised_baseline.py  —  TF-IDF + Logistic Regression 监督基线
==================================================================
给审稿人一个"lexicon vs supervised baseline"的对照。设计要点（针对
小样本、类别不均衡）：
  • 主对比放在逐框架二元任务（能力是否出现 / 后果是否出现）——样本充足、
    与词典的二元指示器同口径，结论最稳。
  • 四类任务作为附带结果，仅在每类样本足够分层时给出。
  • 一律分层交叉验证 + 固定随机种子，纯 CPU，保持论文的可复现卖点。
  • 同一份折上同时评估词典法，做到苹果对苹果。

金标准口径与 06 / 09 一致。
输出 output/tables/baseline_vs_lexicon.csv，并打印两种写法模板。
"""
from __future__ import annotations
import os, sys
from collections import Counter
import pandas as pd
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
TABLES = os.path.join(ROOT, "output", "tables")
SAMPLE = os.path.join(TABLES, "coding_sample.csv")

VALID = ["cap", "con", "both", "neither"]
SEED = 42


def gold_label(r):
    adj = r.get("adjudicated", "")
    if adj in VALID:
        return adj
    c1, c2 = r.get("coder_1_blind", ""), r.get("coder_2_blind", "")
    if c1 in VALID and c2 in VALID and c1 == c2:
        return c1
    return None


def load_gold():
    if not os.path.exists(SAMPLE):
        sys.exit(f"[!] 找不到 {SAMPLE}")
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")
    df["gold"] = df.apply(gold_label, axis=1)
    use = df[df["gold"].isin(VALID) & df["auto_label"].isin(VALID)].copy()
    if len(use) < 20:
        sys.exit(f"[!] 可用金标准仅 {len(use)} 条，监督基线意义有限，"
                 f"建议先把样本扩到 \u2265200（06 --make-sample --n 300）。")
    return use.reset_index(drop=True)


def make_clf():
    from sklearn.pipeline import Pipeline
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.linear_model import LogisticRegression
    return Pipeline([
        ("tfidf", TfidfVectorizer(lowercase=True, ngram_range=(1, 2),
                                  min_df=2, sublinear_tf=True)),
        ("clf", LogisticRegression(max_iter=2000, class_weight="balanced",
                                   random_state=SEED)),
    ])


def cv_predict(X, y):
    """分层交叉验证 out-of-fold 预测；折数随最小类自适应。"""
    from sklearn.model_selection import StratifiedKFold, cross_val_predict
    min_class = min(Counter(y).values())
    k = max(2, min(5, min_class))
    if min_class < 2:
        return None, k  # 无法分层交叉验证
    skf = StratifiedKFold(n_splits=k, shuffle=True, random_state=SEED)
    pred = cross_val_predict(make_clf(), X, y, cv=skf)
    return pred, k


def prf(y_true, y_pred, average, pos_label=None):
    from sklearn.metrics import precision_recall_fscore_support
    p, r, f, _ = precision_recall_fscore_support(
        y_true, y_pred, average=average, pos_label=pos_label, zero_division=0)
    return round(p, 3), round(r, 3), round(f, 3)


def main():
    use = load_gold()
    X = use["text"].astype(str).tolist()
    gold4 = use["gold"].tolist()
    auto4 = use["auto_label"].tolist()
    os.makedirs(TABLES, exist_ok=True)
    rows = []

    print(f"\n===== 监督基线 vs 词典（金标准 n = {len(use)}）=====")
    print(f"金标准类别分布: {dict(Counter(gold4))}\n")

    # ── 逐框架二元（主对比）────────────────────────────────────────────
    def present(series, frame):
        pos = {"cap", "both"} if frame == "capability" else {"con", "both"}
        return np.array([1 if x in pos else 0 for x in series])

    for frame in ("capability", "consequence"):
        yg = present(gold4, frame)
        ya = present(auto4, frame)                      # 词典预测
        lp, lr, lf = prf(yg, ya, "binary", pos_label=1)  # lexicon
        pred, k = cv_predict(X, yg)
        if pred is None:
            print(f"[{frame}] 正例过少，跳过监督交叉验证。")
            rows.append({"task": f"{frame} (binary)", "method": "lexicon",
                         "precision": lp, "recall": lr, "f1": lf, "cv_folds": "-"})
            continue
        sp, sr, sf = prf(yg, pred, "binary", pos_label=1)  # supervised
        print(f"[{frame} 二元]  lexicon F1={lf:.3f} (P={lp:.3f} R={lr:.3f}) | "
              f"LogReg F1={sf:.3f} (P={sp:.3f} R={sr:.3f}, {k}-fold)")
        rows += [
            {"task": f"{frame} (binary)", "method": "lexicon",
             "precision": lp, "recall": lr, "f1": lf, "cv_folds": "-"},
            {"task": f"{frame} (binary)", "method": "tfidf+logreg",
             "precision": sp, "recall": sr, "f1": sf, "cv_folds": k},
        ]

    # ── 四类（附带，仅在可分层时）──────────────────────────────────────
    lex_macro = prf(gold4, auto4, "macro")[2]
    pred4, k4 = cv_predict(X, gold4)
    if pred4 is not None:
        sup_macro = prf(gold4, pred4, "macro")[2]
        print(f"\n[四类 macro-F1]  lexicon={lex_macro:.3f} | "
              f"LogReg={sup_macro:.3f} ({k4}-fold)")
        rows += [
            {"task": "4-class (macro)", "method": "lexicon",
             "precision": "", "recall": "", "f1": lex_macro, "cv_folds": "-"},
            {"task": "4-class (macro)", "method": "tfidf+logreg",
             "precision": "", "recall": "", "f1": sup_macro, "cv_folds": k4},
        ]
    else:
        sup_macro = None
        print(f"\n[四类] 最小类样本不足，未做四类交叉验证；"
              f"lexicon macro-F1={lex_macro:.3f}（仅供参考）。")

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(TABLES, "baseline_vs_lexicon.csv"), index=False)

    # ── 两种写法模板（按真实数字二选一）─────────────────────────────────
    print("\n===== 论文可用写法（按你的真实数字二选一）=====")
    print("• 若监督基线略高：")
    print("  The supervised TF-IDF + logistic-regression baseline achieves a "
          "slightly higher cross-validated F1 than the lexicon, whereas the "
          "lexicon-based instrument offers superior interpretability, temporal "
          "stability, and reproducibility, and\u2014unlike the supervised "
          "model\u2014requires no labelled data to extend to new documents or years.")
    print("• 若两者相当（或词典不低）：")
    print("  Despite its simplicity and its requirement of no training labels, "
          "the lexicon-based instrument performs comparably to a supervised "
          "TF-IDF + logistic-regression baseline under cross-validation, "
          "supporting its use as a transparent, drift-free measurement "
          "instrument for longitudinal analysis.")
    print(f"\n[saved] baseline_vs_lexicon.csv -> {TABLES}/")


if __name__ == "__main__":
    main()
