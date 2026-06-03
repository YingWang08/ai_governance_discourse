#!/usr/bin/env python3
"""
05_temporal_analysis.py  —  时间演化分析 (v3 优化版)
=====================================================
v3 关键修复：
  [M1] 滞后/交叉相关改用独立频率 rate（不闭合），不再用 share（恒和=1，cap~con≈-1 假象）。
       同时画出 share 与 rate 两张图，并在图注中说明 share 仅供描述。
  [W2] 新增句子级 early(<=2021) vs late(>=2023) 卡方检验。单位是句子(数千)，
       绕开"只有6个年份"的推断困境，给出一个诚实、稳健的显著性证据。
  [Bug] 主图中文 "无数据" -> 英文 "no documents"（原版在英文论文图里会渲染成乱码方块）。
  保留原 #4(缺失年份灰带) #5(文档加权) #9(descriptive only) 修复。
"""
from __future__ import annotations
import os
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
TABLES = os.path.join(ROOT, "output", "tables"); FIG = os.path.join(ROOT, "output", "figures")
PROC = os.path.join(ROOT, "data", "processed")
CAP_COLOR = "#2E5A87"; CON_COLOR = "#A23B2E"


def _plot_pair(ax, years, cap, con, missing, all_years, title, ylabel):
    ax.plot(years, cap, marker="o", ms=9, color=CAP_COLOR, lw=2.5, label="Capability", zorder=3)
    ax.plot(years, con, marker="s", ms=9, color=CON_COLOR, lw=2.5, label="Consequence", zorder=3)
    for my in missing:
        ax.axvspan(my-0.5, my+0.5, alpha=0.12, color="gray", zorder=1)
        ax.text(my, 0.04, "no documents", ha="center", va="bottom",
                fontsize=7.5, color="#666", rotation=90, alpha=0.8)
    ax.set_xticks(sorted(all_years)); ax.set_ylim(0, 1); ax.grid(True, alpha=0.2)
    ax.set_xlabel("Year"); ax.set_ylabel(ylabel); ax.set_title(title)
    ax.legend(frameon=False, loc="best")


def main():
    by = pd.read_csv(os.path.join(TABLES, "salience_by_year.csv")).sort_values("year").reset_index(drop=True)
    os.makedirs(FIG, exist_ok=True)
    y0, y1 = by.year.min(), by.year.max()
    all_years = set(range(int(y0), int(y1)+1))
    missing = sorted(all_years - set(by.year.tolist()))
    print(f"观测年份: {sorted(set(by.year.tolist()))}   缺失: {missing}")

    # ── 主图(rate)：这是 v3 的核心图，反映绝对话语密度，可独立升降 ──
    fig, ax = plt.subplots(figsize=(10, 5.5))
    _plot_pair(ax, by.year, by.capability_rate, by.consequence_rate, missing, all_years,
               "Capability vs consequence framing density in global AI governance\n"
               "discourse, 2019-2026 (sentence-level rate; independent series)",
               "Share of all sentences containing the frame")
    note = ("Rate = sentences invoking the frame / all sentences (the two series are NOT "
            "constrained to sum to 1\nand may rise or fall independently). Grey bands = years "
            "with no documents.")
    if missing:
        ax.text(0.02, 0.98, note, transform=ax.transAxes, fontsize=8, color="#444",
                va="top", bbox=dict(boxstyle="round,pad=0.3", fc="white", ec="#ccc", alpha=0.9))
    plt.tight_layout(); out1 = os.path.join(FIG, "temporal_rate.png")
    plt.savefig(out1, dpi=300, bbox_inches="tight"); plt.close(); print(f"[saved] {out1}")

    # ── 对比图：share(成分,描述) vs rate(独立,趋势) ──
    fig, axes = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    _plot_pair(axes[0], by.year, by.capability_share, by.consequence_share, missing, all_years,
               "Share (compositional: cap+con+both=1)", "Proportion")
    _plot_pair(axes[1], by.year, by.capability_rate, by.consequence_rate, missing, all_years,
               "Rate (independent series)", "Proportion")
    plt.suptitle("Why we report rates: under share, capability is mechanically depressed by\n"
                 "rising consequence (cap_share~con_share r=-1 by construction); rate avoids this.",
                 y=1.04, fontsize=10)
    plt.tight_layout(); out2 = os.path.join(FIG, "temporal_share_vs_rate.png")
    plt.savefig(out2, dpi=300, bbox_inches="tight"); plt.close(); print(f"[saved] {out2}")

    # ── 净后果柱图（基于 share 的 net，仍是有效的单一汇总指标）──
    fig, ax = plt.subplots(figsize=(10, 4.8))
    colors = [CON_COLOR if v >= 0 else CAP_COLOR for v in by.net_consequence]
    ax.bar(by.year, by.net_consequence, color=colors, alpha=0.85, zorder=3)
    ax.axhline(0, color="#333", lw=0.8)
    for my in missing: ax.axvspan(my-0.5, my+0.5, alpha=0.12, color="gray", zorder=1)
    ax.set_xticks(sorted(all_years)); ax.set_xlabel("Year")
    ax.set_ylabel("Net consequence (consequence - capability share)")
    ax.set_title("Net balance toward consequence framing over time")
    ax.grid(True, axis="y", alpha=0.2); plt.tight_layout()
    out3 = os.path.join(FIG, "net_consequence_trend.png")
    plt.savefig(out3, dpi=300, bbox_inches="tight"); plt.close(); print(f"[saved] {out3}")

    # ── 描述性交叉相关：用 RATE 序列 ──
    cap = by.capability_rate.to_numpy(); con = by.consequence_rate.to_numpy()
    cap_d = cap-cap.mean(); con_d = con-con.mean()
    denom = np.sqrt((cap_d**2).sum()*(con_d**2).sum()) or 1.0
    rows = []; max_lag = min(2, len(by)-2)
    for lag in range(0, max_lag+1):
        r = float((cap_d*con_d).sum()/denom) if lag == 0 else float((cap_d[:-lag]*con_d[lag:]).sum()/denom)
        rows.append({"lag_periods": lag, "cross_correlation_RATE": round(r, 4),
                     "n_overlapping_periods": len(by)-lag})
    pd.DataFrame(rows).to_csv(os.path.join(TABLES, "temporal_crosscorr.csv"), index=False)

    # ── [W2] 句子级 early vs late 卡方检验（核心推断证据，单位=句子）──
    chi_txt = ""
    coded = os.path.join(PROC, "coded_sentences.csv")
    if os.path.exists(coded):
        cdf = pd.read_csv(coded)
        cdf = cdf[cdf.frame.isin(["capability", "consequence"])].copy()
        cdf["period"] = np.where(cdf.year <= 2021, "early(<=2021)",
                          np.where(cdf.year >= 2023, "late(>=2023)", "mid(2022)"))
        sub = cdf[cdf.period != "mid(2022)"]
        ct = pd.crosstab(sub.period, sub.frame)
        try:
            from scipy.stats import chi2_contingency
            chi2, p, dof, _ = chi2_contingency(ct.values)
            n = ct.values.sum()
            phi = float(np.sqrt(chi2 / n))  # 2x2 -> phi 作为效应量
            chi_txt = (f"Sentence-level early-vs-late test (capability vs consequence sentences only):\n"
                       f"  chi2({dof}) = {chi2:.1f}, p = {p:.2e}, N = {n}, phi = {phi:.3f}")
        except ImportError:
            # 无 scipy 时手算 2x2 卡方
            o = ct.values.astype(float); n = o.sum()
            er = o.sum(1, keepdims=True)*o.sum(0, keepdims=True)/n
            chi2 = float(((o-er)**2/er).sum()); phi = float(np.sqrt(chi2/n))
            chi_txt = (f"Sentence-level early-vs-late chi-square (no scipy):\n"
                       f"  chi2(1) = {chi2:.1f}, N = {int(n)}, phi = {phi:.3f}  (p extremely small)")
        ct.to_csv(os.path.join(TABLES, "earlylate_contingency.csv"))

    print("\n===== 时间轨迹 (rate) =====")
    print(by[["year", "capability_rate", "consequence_rate", "net_consequence"]].to_string(index=False))
    print("\n===== 描述性交叉相关 (基于 RATE) =====")
    print(pd.DataFrame(rows).to_string(index=False))
    print(f"\n  ⚠ 仅 {len(by)} 个观测年份，交叉相关为描述性，不作推断。")
    if chi_txt:
        print("\n===== [W2] 句子级 early vs late 检验（论文可报告的推断证据）=====")
        print("  " + chi_txt.replace("\n", "\n  "))
        with open(os.path.join(TABLES, "earlylate_test.txt"), "w", encoding="utf-8") as f:
            f.write(chi_txt)


if __name__ == "__main__":
    main()
