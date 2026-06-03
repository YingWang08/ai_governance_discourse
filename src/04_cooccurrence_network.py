#!/usr/bin/env python3
"""
04_cooccurrence_network.py  —  关键词共现网络 (v3 优化版)
=========================================================
v3 关键修复：
  [M3] 原版只把 capability + consequence 词加入网络，boundary 词
       (trustworthy, trust, ethical, governance, compliance, standard) 从未成为节点。
       但论文 §4.2 的核心论述是"'trustworthy' 介数中心性最高、桥接两个框架"——
       原版代码根本无法产出该结果，作者要么写不出该节，要么被迫编造。
       修复：把 boundary 词作为第三类节点(灰色)纳入网络与中心性计算，
             "桥接词"的介数中心性现在是真实算出来的。
  [Bug] ROOT 路径与其它脚本不一致(原版无条件 dirname)，改为统一的条件式，
        避免扁平目录布局下找不到 config/data。
"""
from __future__ import annotations
import os, re, itertools, yaml
import pandas as pd, networkx as nx
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
CONF = os.path.join(ROOT, "config"); PROC = os.path.join(ROOT, "data", "processed")
FIG = os.path.join(ROOT, "output", "figures"); TABLES = os.path.join(ROOT, "output", "tables")
CAP_COLOR = "#2E5A87"; CON_COLOR = "#A23B2E"; BND_COLOR = "#6E6E6E"


def load_lexicon():
    p = os.path.join(CONF, "lexicon_expanded.yaml")
    if not os.path.exists(p): p = os.path.join(CONF, "lexicon.yaml")
    with open(p, "r", encoding="utf-8") as f: return yaml.safe_load(f)


def main(min_edge_weight=2, top_n_terms=45):
    lex = load_lexicon()
    frame_of = {}
    for t in lex["capability"]:  frame_of[t.lower()] = "capability"
    for t in lex["consequence"]: frame_of[t.lower()] = "consequence"
    # [M3] 关键修复：把 boundary 词也纳入
    for t in lex.get("boundary", []): frame_of[t.lower()] = "boundary"

    all_terms = sorted(frame_of.keys(), key=len, reverse=True)
    term_re = re.compile(r"\b(?:" + "|".join(re.escape(t) for t in all_terms) + r")\b", re.I)

    df = pd.read_csv(os.path.join(PROC, "sentences.csv"))
    co = {}; node_freq = {}
    for text in df.text.astype(str):
        found = sorted(set(m.lower() for m in term_re.findall(text)))
        for t in found: node_freq[t] = node_freq.get(t, 0) + 1
        for a, b in itertools.combinations(found, 2):
            key = tuple(sorted((a, b))); co[key] = co.get(key, 0) + 1

    keep = set(t for t, _ in sorted(node_freq.items(), key=lambda x: -x[1])[:top_n_terms])
    G = nx.Graph()
    for t in keep: G.add_node(t, frame=frame_of.get(t, "boundary"), freq=node_freq[t])
    for (a, b), w in co.items():
        if w >= min_edge_weight and a in keep and b in keep: G.add_edge(a, b, weight=w)
    G.remove_nodes_from([n for n in list(G.nodes()) if G.degree(n) == 0])
    if G.number_of_nodes() == 0:
        print("[warn] empty network; lower min_edge_weight or add data."); return

    deg = nx.degree_centrality(G); btw = nx.betweenness_centrality(G, weight="weight")
    cen = pd.DataFrame({
        "term": list(G.nodes()),
        "frame": [G.nodes[n]["frame"] for n in G.nodes()],
        "frequency": [G.nodes[n]["freq"] for n in G.nodes()],
        "degree_centrality": [round(deg[n], 4) for n in G.nodes()],
        "betweenness_centrality": [round(btw[n], 4) for n in G.nodes()],
    }).sort_values("betweenness_centrality", ascending=False)
    os.makedirs(TABLES, exist_ok=True)
    cen.to_csv(os.path.join(TABLES, "network_centrality.csv"), index=False)

    os.makedirs(FIG, exist_ok=True)
    plt.figure(figsize=(11, 9))
    pos = nx.spring_layout(G, k=0.6, seed=42, weight="weight")
    colors = {"capability": CAP_COLOR, "consequence": CON_COLOR, "boundary": BND_COLOR}
    node_colors = [colors[G.nodes[n]["frame"]] for n in G.nodes()]
    node_sizes = [200 + 40*G.nodes[n]["freq"] for n in G.nodes()]
    edge_widths = [0.3 + 0.25*G[u][v]["weight"] for u, v in G.edges()]
    nx.draw_networkx_edges(G, pos, width=edge_widths, alpha=0.25, edge_color="#888888")
    nx.draw_networkx_nodes(G, pos, node_color=node_colors, node_size=node_sizes,
                           alpha=0.9, linewidths=0.5, edgecolors="white")
    nx.draw_networkx_labels(G, pos, font_size=8, font_color="#1a1a1a")
    legend = [Line2D([0],[0], marker="o", color="w", label="Capability frame", markerfacecolor=CAP_COLOR, markersize=11),
              Line2D([0],[0], marker="o", color="w", label="Consequence frame", markerfacecolor=CON_COLOR, markersize=11),
              Line2D([0],[0], marker="o", color="w", label="Boundary / bridging", markerfacecolor=BND_COLOR, markersize=11)]
    plt.legend(handles=legend, loc="upper right", frameon=False, fontsize=10)
    plt.title("Co-occurrence network of capability, consequence and boundary terms\n"
              "in global AI governance discourse (2019-2026)", fontsize=12)
    plt.axis("off"); plt.tight_layout()
    out = os.path.join(FIG, "cooccurrence_network.png")
    plt.savefig(out, dpi=300, bbox_inches="tight"); plt.close()

    print(f"[ok] nodes={G.number_of_nodes()} edges={G.number_of_edges()}")
    print("Top bridging terms by betweenness (boundary terms now included):")
    print(cen.head(10).to_string(index=False))
    print(f"[saved] {out}")
    print(f"[saved] {TABLES}/network_centrality.csv")


if __name__ == "__main__":
    main()
