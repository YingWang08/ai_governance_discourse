#!/usr/bin/env python3
"""
make_genre_template.py — 用你真实数据自动生成 config/genre.csv
=====================================================================
解决"手动填 doc_id 总对不上"的问题：本脚本直接读 coded_sentences.csv，列出你
真实的 11 个文档(doc_id, body, year)，按 Table 1 的关键词+年份给每个文档猜一个
hard/soft，写进 config/genre.csv。doc_id 一定与数据一致，不会再合并成空。

★ 这只是"猜"，你必须打开 config/genre.csv 用肉眼核对、改正每一行，再去跑 12。★
按你论文 Table 1，hard law 应为这 4 个：
  EU AI Act proposal (2021) / US EO 14110 (2023) /
  EU AI Act final (2024)    / CoE Framework Convention (2024)
其余 7 个为 soft law。

输入：data/processed/coded_sentences.csv（需含 doc_id, body, year）
输出：config/genre.csv（doc_id, genre, body, year；后两列仅供你核对）
"""
from __future__ import annotations
import os, re, sys
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
PROC = os.path.join(ROOT, "data", "processed")
CONF = os.path.join(ROOT, "config")


def guess_genre(body: str, year) -> str:
    """按 Table 1 的关键词+年份猜 hard/soft。猜不准没关系，留给人工核对。"""
    b = str(body).lower()
    try:
        y = int(year)
    except Exception:
        y = None
    # 4 个 hard-law：欧盟AI法案(提案2021/终版2024)、美国EO 14110(2023)、欧委会公约(2024)
    if "council of europe" in b or re.search(r"\bcoe\b", b):
        return "hard"
    if ("executive order" in b or "14110" in b or "white house" in b
            or (("united states" in b or re.search(r"\bus\b|\bu\.s\.", b)
                 or "government" in b) and y == 2023)):
        return "hard"
    if y == 2021 and ("commission" in b or "european" in b or re.search(r"\bec\b|\beu\b", b)):
        return "hard"   # EU AI Act 提案 2021
    if y == 2024 and ("european union" in b or "parliament" in b or "regulation" in b
                      or re.search(r"\beu\b", b)):
        return "hard"   # EU AI Act 终版 2024
    return "soft"


def main():
    p = os.path.join(PROC, "coded_sentences.csv")
    if not os.path.exists(p):
        sys.exit(f"[!] 找不到 {p}")
    df = pd.read_csv(p)
    need = {"doc_id", "year"}
    if not need.issubset(df.columns):
        sys.exit(f"[!] coded_sentences.csv 需要列 {need}，当前列: {list(df.columns)}")
    body_col = "body" if "body" in df.columns else None
    cols = ["doc_id", "year"] + ([body_col] if body_col else [])
    docs = df[cols].drop_duplicates().sort_values("year").reset_index(drop=True)
    docs["doc_id"] = docs["doc_id"].astype(str)
    docs["genre"] = [guess_genre(r[body_col] if body_col else "", r["year"])
                     for _, r in docs.iterrows()]

    os.makedirs(CONF, exist_ok=True)
    out = os.path.join(CONF, "genre.csv")
    keep = ["doc_id", "genre"] + (["body"] if body_col else []) + ["year"]
    docs[keep].to_csv(out, index=False)

    print(f"共 {len(docs)} 个文档。已写出猜测版 -> {out}")
    print("（doc_id 与数据完全一致；body/year 仅供你核对，12 只读 doc_id 与 genre）\n")
    print(docs[keep].to_string(index=False))
    n_hard = (docs["genre"] == "hard").sum()
    print(f"\n猜测 hard={n_hard}, soft={len(docs)-n_hard}。"
          f"按 Table 1 应当 hard=4, soft=7。")
    if n_hard != 4:
        print("⚠ 与预期(4 个 hard)不一致，请务必打开 genre.csv 手动核对改正！")
    print("\n下一步：打开 config/genre.csv 核对每行的 hard/soft，改正后重跑 12_clustered_inference.py")


if __name__ == "__main__":
    main()