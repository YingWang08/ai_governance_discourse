#!/usr/bin/env python3
"""
03_frame_coding.py  —  逐句框架编码 (v3 优化版)
v3 关键修复 [M1]：份额型指标成分闭合 -> 同时输出独立频率 rate（不闭合，可独立升降）。
下游 05 的滞后分析改用 rate。保留 [#7] pandas 兼容修复。
"""
from __future__ import annotations
import os, re, yaml
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
CONF = os.path.join(ROOT, "config"); PROC = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "output", "tables")

def load_lexicon():
    path = os.path.join(CONF, "lexicon_expanded.yaml")
    if not os.path.exists(path):
        path = os.path.join(CONF, "lexicon.yaml"); print("[warn] 用 lexicon.yaml")
    with open(path, "r", encoding="utf-8") as f: return yaml.safe_load(f)

def build_matchers(terms):
    esc = sorted([re.escape(t.lower()) for t in terms], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(esc) + r")\b", flags=re.I)

def count_hits(text, m): return len(m.findall(text))

def salience_fn(group):
    cap=(group.frame=="capability").sum(); con=(group.frame=="consequence").sum()
    both=(group.frame=="both").sum(); framed=cap+con+both; n=len(group)
    cap_share=cap/framed if framed else 0.0; con_share=con/framed if framed else 0.0
    both_share=both/framed if framed else 0.0
    cap_rate=(cap+both)/n if n else 0.0; con_rate=(con+both)/n if n else 0.0
    return pd.Series({"n_sentences":n,"capability":cap,"consequence":con,"both":both,
        "framed":framed,"framed_ratio":round(framed/n,4) if n else 0.0,
        "capability_share":round(cap_share,4),"consequence_share":round(con_share,4),
        "both_share":round(both_share,4),"net_consequence":round(con_share-cap_share,4),
        "capability_rate":round(cap_rate,4),"consequence_rate":round(con_rate,4)})

def safe_apply(grouped, fn):
    try: return grouped.apply(fn, include_groups=False).reset_index()
    except TypeError: return grouped.apply(fn).reset_index()

def main():
    lex=load_lexicon(); cap_re=build_matchers(lex["capability"]); con_re=build_matchers(lex["consequence"])
    df=pd.read_csv(os.path.join(PROC,"sentences.csv"))
    df["cap_hits"]=df.text.astype(str).apply(lambda t: count_hits(t,cap_re))
    df["con_hits"]=df.text.astype(str).apply(lambda t: count_hits(t,con_re))
    def label(r):
        c,k=r.cap_hits,r.con_hits
        return "both" if c>0 and k>0 else "capability" if c>0 else "consequence" if k>0 else "neither"
    df["frame"]=df.apply(label,axis=1)
    os.makedirs(PROC,exist_ok=True); os.makedirs(TABLES,exist_ok=True)
    df.to_csv(os.path.join(PROC,"coded_sentences.csv"),index=False)
    by_doc=safe_apply(df.groupby(["doc_id","body","year"]),salience_fn)
    by_year=safe_apply(df.groupby("year"),salience_fn)
    by_body=safe_apply(df.groupby("body"),salience_fn)
    by_doc.to_csv(os.path.join(TABLES,"salience_by_document.csv"),index=False)
    by_year.to_csv(os.path.join(TABLES,"salience_by_year.csv"),index=False)
    by_body.to_csv(os.path.join(TABLES,"salience_by_body.csv"),index=False)
    print("===== 框架分布 ====="); print(df.frame.value_counts().to_string())
    print("\n===== 按年份：份额(描述)+独立频率(趋势用) =====")
    print(by_year[["year","n_sentences","capability_share","consequence_share",
                   "net_consequence","capability_rate","consequence_rate"]].to_string(index=False))
    print("\n[提示] 滞后/交叉相关请用 *_rate 列；*_share 三者恒和为1，做交叉相关会得 ≈ -1 的假象。")
    print(f"[saved] salience_by_*.csv -> {TABLES}/")

if __name__=="__main__": main()
