#!/usr/bin/env python3
"""
15_lexicon_validity.py — 词典稳健性自助 + 词条影响力审计（★文档级版★）
=====================================================================
软攻击点5："字典法是手搭的、武断的，换几个词结论就变了"。

本版相对旧版的关键改动（与主分析口径对齐）：
  • 旧版按【年份】聚合（groupby year，约 5 个点，ρ 易顶 ±1 上限、且与主分析口径
    不一致）；
  • 本版按【文档】聚合（groupby doc_id，n=11），直接为论文主推的文档级趋势
    （Spearman ρ≈+0.62, p≈0.042）做稳健性背书。单位统一，审稿人无从挑"换口径"。

做三件事：
  1) 文档级词典自助：每次随机丢弃每个框架词表里 drop_frac 比例的词，重判、按文档
     重算净后果(con_rate−cap_rate)，看"文档年份 vs 文档净后果"的 Spearman 方向是否
     仍为正。报告 B 次里方向保持(ρ>0)的比例与 ρ 分布。
  2) 逐词影响力（绝对水平）：逐个去掉单个 consequence 词，看它对【全语料】consequence
     命中率的边际贡献，排序导出。──诚实呈现：'risk' 这类核心词贡献大是正常的。
  3) 留一词的文档级趋势（方向）：把影响力最大的词单独拿掉，重算文档级 ρ，回答
     "趋势是不是靠某一个词撑着"。──这才是稳健性该讲的"方向不依赖单一词条"。

★铁律（交接说明第9条）：所有数如实报告，显著与不显著一并写；
  ★不得套用旧模板句 "no single term accounts for more than a few points"——你的真实
   数据里 'risk' 对绝对命中率贡献约 11 个百分点，那句是错的。正确写法是把"绝对水平"
   与"趋势方向"分开讲（见第 3 件事与脚本结尾自适应话术）。

★注意（口径说明）：本脚本必须用【词典命中】(regex 是否含某框架词) 来判定 cap/con，
  因为它要"扰动词典"；这与主分析里基于 frame 标签的 net_consequence 略有差别，故
  base ρ 不一定恰好等于 0.62。这是词典扰动检验的固有性质，正常且可解释——它考查的是
  "基于词典的测量对词条选择是否稳健"，base ρ 是这套检验自身的参照点。

输入：data/processed/coded_sentences.csv（需含 text, doc_id, year）+ config/lexicon*.yaml
输出（output/tables/）：lexicon_bootstrap_doclevel.csv, term_influence_consequence.csv
依赖：pandas, numpy, scipy, pyyaml。
"""
from __future__ import annotations
import os, re, sys, yaml
import numpy as np
import pandas as pd
from scipy.stats import spearmanr

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
CONF = os.path.join(ROOT, "config")
PROC = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "output", "tables")


def load_lexicon():
    for name in ("lexicon_expanded.yaml", "lexicon.yaml"):
        p = os.path.join(CONF, name)
        if os.path.exists(p):
            return yaml.safe_load(open(p, encoding="utf-8"))
    sys.exit("[!] 找不到 config/lexicon*.yaml")


def matcher(terms):
    if not terms:
        return re.compile(r"(?!x)x")  # 永不匹配
    esc = sorted([re.escape(t.lower()) for t in terms], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(esc) + r")\b", re.I)


def document_net(df, cap_terms, con_terms):
    """★文档级★：每个文档一行，net = con_rate − cap_rate，并带上该文档的年份。
    返回 DataFrame，index=doc_id，列 [year, cap, con, net]。
    观测单位是文档（n=11），与主分析一致，而非年份。"""
    cre, kre = matcher(cap_terms), matcher(con_terms)
    cap = df["text"].astype(str).str.contains(cre)
    con = df["text"].astype(str).str.contains(kre)
    tmp = pd.DataFrame({"doc_id": df["doc_id"], "year": df["year"],
                        "cap": cap.astype(int), "con": con.astype(int)})
    g = tmp.groupby("doc_id").agg(year=("year", "first"),
                                  cap=("cap", "mean"),
                                  con=("con", "mean"))
    g["net"] = g["con"] - g["cap"]
    return g


def doc_trend(g):
    """对文档级聚合表算 Spearman(文档年份, 文档净后果)。返回 (rho, p)。
    点太少或 net 全相等时返回 (nan, nan)。"""
    if g["net"].notna().sum() < 3 or g["net"].nunique() < 2:
        return float("nan"), float("nan")
    rho, p = spearmanr(g["year"].values, g["net"].values)
    return rho, p


def main():
    coded_p = os.path.join(PROC, "coded_sentences.csv")
    if not os.path.exists(coded_p):
        sys.exit(f"[!] 找不到 {coded_p}")
    df = pd.read_csv(coded_p)
    for need in ("text", "doc_id", "year"):
        if need not in df.columns:
            sys.exit(f"[!] coded_sentences.csv 缺列 '{need}'（文档级口径必需 doc_id 与 year）")
    lex = load_lexicon()
    cap0, con0 = list(lex["capability"]), list(lex["consequence"])
    os.makedirs(TABLES, exist_ok=True)
    n_docs = df["doc_id"].nunique()

    # ── 0) 基准：文档级（主口径）+（仅供对照）旧的年份聚合口径 ──────────────
    base_doc = document_net(df, cap0, con0)
    rho_doc, p_doc = doc_trend(base_doc)
    print(f"★ 文档级（主口径, n_docs={n_docs}）：净后果 vs 年份 "
          f"Spearman ρ = {rho_doc:+.3f} (p={p_doc:.4f})   ← 这是要报告的口径")
    # 仅作对照，不写进论文：帮助理解旧版为何偏高（点更少、易顶上限）
    yr = (df.assign(
            _cap=df["text"].astype(str).str.contains(matcher(cap0)).astype(int),
            _con=df["text"].astype(str).str.contains(matcher(con0)).astype(int))
          .groupby("year")[["_cap", "_con"]].mean())
    yr_net = yr["_con"] - yr["_cap"]
    if yr_net.notna().sum() >= 3 and yr_net.nunique() >= 2:
        rho_yr, p_yr = spearmanr(yr_net.index, yr_net.values)
        print(f"  （仅对照，不报告）年份聚合 n_years={yr_net.notna().sum()}："
              f"ρ = {rho_yr:+.3f} (p={p_yr:.4f}) — 点少易顶上限，故弃用")

    # ── 1) 文档级词典自助稳定性 ─────────────────────────────────────────
    rng = np.random.default_rng(99)
    B, drop_frac = 1000, 0.30
    rhos, preserved = [], 0
    for _ in range(B):
        cap = [t for t in cap0 if rng.random() > drop_frac] or cap0[:1]
        con = [t for t in con0 if rng.random() > drop_frac] or con0[:1]
        rr, _ = doc_trend(document_net(df, cap, con))
        if np.isfinite(rr):
            rhos.append(rr); preserved += int(rr > 0)
    rhos = np.array(rhos)
    frac = preserved / len(rhos) if len(rhos) else float("nan")
    print(f"\n文档级词典自助 (B={B}, 每次随机丢弃 {int(drop_frac*100)}% 词条)：")
    print(f"  有效重抽样 = {len(rhos)}/{B}")
    print(f"  方向保持(ρ>0)的比例 = {frac:.3f}")
    if len(rhos):
        print(f"  ρ 分布: 中位 {np.median(rhos):+.3f}, "
              f"95% 区间 [{np.percentile(rhos,2.5):+.3f}, {np.percentile(rhos,97.5):+.3f}]")
    pd.DataFrame({"bootstrap_rho_doclevel": rhos}).to_csv(
        os.path.join(TABLES, "lexicon_bootstrap_doclevel.csv"), index=False)

    # ── 2) 逐词影响力（绝对水平，全语料 consequence 命中率）─────────────
    full_con_rate = df["text"].astype(str).str.contains(matcher(con0)).mean()
    rows = []
    for t in con0:
        reduced = [x for x in con0 if x != t]
        rate = df["text"].astype(str).str.contains(matcher(reduced)).mean()
        rows.append(dict(term=t,
                         drop_delta_consequence_rate=round(full_con_rate - rate, 5)))
    infl = (pd.DataFrame(rows)
            .sort_values("drop_delta_consequence_rate", ascending=False)
            .reset_index(drop=True))

    # ── 3) 留一词的文档级趋势（方向是否依赖单一词条）──────────────────
    #    对影响力最大的前 K 个 consequence 词，逐个单独剔除，重算文档级 ρ。
    K = min(8, len(infl))
    loo_rows = []
    for t in infl["term"].head(K):
        rr, _ = doc_trend(document_net(df, cap0, [x for x in con0 if x != t]))
        loo_rows.append(dict(term=t,
                             doc_rho_without_term=round(rr, 3) if np.isfinite(rr) else np.nan,
                             still_positive=bool(np.isfinite(rr) and rr > 0)))
    loo = pd.DataFrame(loo_rows)
    infl_out = infl.merge(loo, on="term", how="left")
    infl_out.to_csv(os.path.join(TABLES, "term_influence_consequence.csv"), index=False)

    print(f"\n影响力最大的 {K} 个 consequence 词"
          f"（drop_delta=去掉后全语料命中率下降；doc_rho=单独去掉它后的文档级趋势）：")
    print(infl_out.head(K).to_string(index=False))

    # 关键单点：影响力最大的词（你的数据里多半是 'risk'）单独拿掉后趋势是否还在
    top_term = infl["term"].iloc[0]
    top_delta = infl["drop_delta_consequence_rate"].iloc[0]
    rho_top, _ = doc_trend(document_net(df, cap0, [x for x in con0 if x != top_term]))
    n_pos_topK = int(loo["still_positive"].sum())

    # ── 自适应、诚实的论文话术（绝不套用"no single term > a few points"）──
    print("\n" + "=" * 70)
    print("§4.5 稳健性话术（按真实数字自适应生成，已规避错误模板句）：")
    print("=" * 70)
    s1 = (f"Under a document-level lexicon bootstrap that randomly drops 30% of "
          f"each frame's terms (B={B}, resampling the term lists), the positive "
          f"year-net-consequence association at the document level (n={n_docs}) is "
          f"preserved in {frac*100:.0f}% of resamples")
    if len(rhos):
        s1 += (f" (median rho = {np.median(rhos):+.2f}, "
               f"95% interval [{np.percentile(rhos,2.5):+.2f}, "
               f"{np.percentile(rhos,97.5):+.2f}]).")
    else:
        s1 += "."
    print(s1)
    if np.isfinite(rho_top) and rho_top > 0:
        print(f"Although the single most influential consequence term ('{top_term}') "
              f"contributes about {top_delta*100:.1f} percentage points to the "
              f"corpus-wide consequence rate, the document-level trend remains "
              f"positive when this term alone is removed (rho = {rho_top:+.2f}); "
              f"across the {K} most influential terms, {n_pos_topK}/{K} leave the "
              f"trend positive, indicating the temporal pattern does not hinge on "
              f"any single term.")
    else:
        print(f"The single most influential consequence term ('{top_term}') "
              f"contributes about {top_delta*100:.1f} percentage points to the "
              f"corpus-wide consequence rate; when it is removed the document-level "
              f"trend is rho = {rho_top:+.2f}. We therefore report the absolute "
              f"consequence level as partly carried by core risk vocabulary, while "
              f"the {frac*100:.0f}% direction-preservation in the bootstrap speaks to "
              f"the robustness of the trend's sign rather than its magnitude.")

    print(f"\n[saved] lexicon_bootstrap_doclevel.csv / term_influence_consequence.csv "
          f"-> {TABLES}/")
    print("（把上面真实数字贴回对话，我据此把这段定成与证据强度一致的终稿。）")


if __name__ == "__main__":
    main()