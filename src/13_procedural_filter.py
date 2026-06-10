#!/usr/bin/env python3
"""
13_procedural_filter.py — 把 codebook 的"about-what 程序性排除"写进代码
=====================================================================
攻击点2：词典法把"shall/must + 报送/登记/期限"这类纯程序性义务句过度判给
consequence，导致精确率低、自动-人工 κ 只有 0.097/0.152、capability F1=0.67。
你的 Appendix A 里"程序性义务→neither(除非实质上关乎 AI 后果)"这条规则，目前
只活在【人工 codebook】里，没进【自动管线】。本脚本把它实现出来。

做法：对每个句子，若它当前因某个 consequence/capability 词被判为 con/cap，
而该词只出现在【程序性-行政】语境(义务情态 + 行政动作)且句中没有实质后果对象
(risk/harm/safety/rights/...)，则把该句降级为 neither。保守起见只动"明显程序句"，
宁可少改、不要过改。

输出（output/tables/）：
  coded_sentences_filtered.csv   增加 frame_filtered 列（不覆盖原 frame）
  salience_by_year_filtered.csv  过滤后的逐年 rate/share/net（用于复核趋势不变）
  metrics_filtered_vs_gold.csv   过滤后 auto_label 对金标准的 P/R/F1（应当上升）
  procedural_examples.csv        被降级的句子样例（供你人工抽查，确保没误伤）

★ 两种用法，自己选，但都要如实报告：★
  (推荐) 作为"改进变体 + 稳健性"：正文主结果仍用原词典，另报一段
         "加入程序性过滤后，consequence 精确率从 0.97→…、capability F1 从
          0.67→…，而时间方向不变(净后果逐年仍上升)"。既补强又不必重做全部表。
  (更彻底) 把 frame_filtered 当作主标签：那就要把 03→05→07→09 全链路用过滤后的
          标签重跑，Table 3/6/8 等所有数字按真实结果更新。方向应当不变，但量级会变。

依赖：pyyaml（读你的 lexicon）+ sklearn（算指标，与 09 一致）。
"""
from __future__ import annotations
import os, re, sys, yaml
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
CONF = os.path.join(ROOT, "config")
PROC = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "output", "tables")

# ── 程序性-行政 触发词（可按需扩充；保持保守）────────────────────────────────
OBLIGATION = r"(?:shall|must|is required to|are required to|shall be required to)"
ADMIN_ACTION = (r"(?:submit|file|filing|filed|register|registration|registered|"
                r"report|reporting|notify|notification|record|records|log|"
                r"keep|maintain|retain|publish|publication|disclose to the|"
                r"designate|appoint|provide to the|deadline|"
                r"within \d+\s+(?:day|days|month|months|working days))")
# 句中若出现"实质后果对象"，则【不】判为纯程序（保护真正的后果义务句）
SUBSTANTIVE_OBJ = (r"(?:risk|risks|harm|harms|harmful|safety|safe|security|"
                   r"fundamental rights|human rights|health|discrimination|bias|"
                   r"privacy|damage|injury|threat|misuse|impact|adverse|"
                   r"protection of|safeguard against|mitigat)")

ob_re = re.compile(OBLIGATION, re.I)
admin_re = re.compile(ADMIN_ACTION, re.I)
subst_re = re.compile(SUBSTANTIVE_OBJ, re.I)

CON_LABELS = {"con", "consequence"}
CAP_LABELS = {"cap", "capability"}


def load_lexicon():
    for name in ("lexicon_expanded.yaml", "lexicon.yaml"):
        p = os.path.join(CONF, name)
        if os.path.exists(p):
            with open(p, encoding="utf-8") as f:
                return yaml.safe_load(f)
    sys.exit("[!] 找不到 config/lexicon*.yaml")


def build_re(terms):
    esc = sorted([re.escape(t.lower()) for t in terms], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(esc) + r")\b", re.I)


def is_procedural(text: str) -> bool:
    """明显的程序性-行政义务句：有义务情态 + 行政动作，且无实质后果对象。"""
    t = str(text)
    return bool(ob_re.search(t) and admin_re.search(t) and not subst_re.search(t))


def relabel(frame: str, text: str) -> str:
    """只在'明显程序句'上，把 con-only / cap-only 降级为 neither。both 不动(信息更丰富)。"""
    f = str(frame).lower()
    if f in CON_LABELS or f in CAP_LABELS:
        if is_procedural(text):
            return "neither"
    return frame


def main():
    from sklearn.metrics import precision_recall_fscore_support

    # ---- 1) 对全语料应用过滤，产出 frame_filtered，并复核趋势 ----
    coded_p = os.path.join(PROC, "coded_sentences.csv")
    if not os.path.exists(coded_p):
        sys.exit(f"[!] 找不到 {coded_p}")
    df = pd.read_csv(coded_p)
    df["frame_filtered"] = [relabel(fr, tx) for fr, tx in zip(df["frame"], df["text"])]
    n_demoted = int((df["frame"] != df["frame_filtered"]).sum())
    df.to_csv(os.path.join(PROC, "coded_sentences_filtered.csv"), index=False)

    # 逐年 rate（过滤后），用于"方向不变"的复核
    def year_rates(frame_col):
        g = df.groupby("year")
        cap = g.apply(lambda x: (x[frame_col].isin(["cap", "capability", "both"])).mean())
        con = g.apply(lambda x: (x[frame_col].isin(["con", "consequence", "both"])).mean())
        out = pd.DataFrame({"capability_rate": cap, "consequence_rate": con})
        out["net_rate"] = out["consequence_rate"] - out["capability_rate"]
        return out.reset_index()
    before = year_rates("frame").rename(columns=lambda c: c + "_orig" if c != "year" else c)
    after = year_rates("frame_filtered")
    comp = before.merge(after, on="year")
    comp.to_csv(os.path.join(TABLES, "salience_by_year_filtered.csv"), index=False)

    print(f"被降级为 neither 的句子数: {n_demoted} / {len(df)} "
          f"({100*n_demoted/len(df):.1f}%)")
    print("\n逐年 net（过滤前后对比；方向应当一致）：")
    print(comp[["year", "net_rate_orig", "net_rate"]].to_string(index=False))

    # 抽样导出被降级的句子，供人工抽查（防止误伤真正的后果句）
    demoted = df[df["frame"] != df["frame_filtered"]][["text", "frame", "frame_filtered"]]
    demoted.head(60).to_csv(os.path.join(TABLES, "procedural_examples.csv"), index=False)
    print(f"[saved] 降级样例 60 条 -> {TABLES}/procedural_examples.csv （请务必人工抽查）")

    # ---- 2) 在 300 句金标准上，对比过滤前后对人工的 P/R/F1（核心证据）----
    sample_p = os.path.join(TABLES, "coding_sample.csv")
    if not os.path.exists(sample_p):
        print(f"\n[note] 没有 {sample_p}，跳过金标准复评。")
        return
    s = pd.read_csv(sample_p, dtype=str).fillna("")
    VALID = {"cap", "con", "both", "neither"}

    def gold(r):
        if r.get("adjudicated", "") in VALID:
            return r["adjudicated"]
        a, b = r.get("coder_1_blind", ""), r.get("coder_2_blind", "")
        return a if (a in VALID and a == b) else None
    s["gold"] = s.apply(gold, axis=1)
    s = s[s["gold"].isin(VALID) & s["auto_label"].isin(VALID)].copy()
    # 对自动标签也施加同一过滤
    s["auto_filtered"] = [relabel(a, t) for a, t in zip(s["auto_label"], s["text"])]

    def perframe(gold_list, pred_list, frame):
        pos = {"cap", "both"} if frame == "capability" else {"con", "both"}
        g = [1 if x in pos else 0 for x in gold_list]
        p = [1 if x in pos else 0 for x in pred_list]
        pr, rc, f1, _ = precision_recall_fscore_support(
            g, p, average="binary", zero_division=0)
        return round(pr, 3), round(rc, 3), round(f1, 3)

    rows = []
    for frame in ["capability", "consequence"]:
        pr0, rc0, f10 = perframe(s["gold"], s["auto_label"], frame)
        pr1, rc1, f11 = perframe(s["gold"], s["auto_filtered"], frame)
        rows.append(dict(frame=frame,
                         P_before=pr0, R_before=rc0, F1_before=f10,
                         P_after=pr1, R_after=rc1, F1_after=f11))
        print(f"\n[{frame}] 过滤前 P/R/F1 = {pr0}/{rc0}/{f10}  →  "
              f"过滤后 = {pr1}/{rc1}/{f11}")
    pd.DataFrame(rows).to_csv(os.path.join(TABLES, "metrics_filtered_vs_gold.csv"),
                             index=False)
    print(f"\n[saved] metrics_filtered_vs_gold.csv -> {TABLES}/")
    print("\n预期：consequence 精确率(本就 0.97)基本持平或微升，capability F1 上升，")
    print("      整体 macro-F1 上升。把这组数字写进 §4.1/§5.3，攻击点2 即被堵住。")
    print("注意：若你选择把 frame_filtered 当主标签，请把 03→05→07→09 全链路重跑，")
    print("      Table 3/6/8 全部按真实新数字更新（方向应当不变，量级会变）。")


if __name__ == "__main__":
    main()
