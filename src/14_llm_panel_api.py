#!/usr/bin/env python3
"""
14_llm_panel_api.py — 可复现的"多模型独立标注小组"(API 版)
=====================================================================
攻击点3：两位编码者就是两位作者，没有独立第三方人工编码。在"不能加人"的约束下，
最强的替代是把你 11_llm_annotation.py 的网页版 LLM 校验，升级成【API + 温度0 +
固定 seed + 多个不同厂商模型】的独立标注小组——任何人按公开 prompt 与参数就能逐位
复跑。这既堵住"第三方是不是真的/能不能复现"，本身也是一个小的方法贡献：
"a reproducible multi-model LLM annotation panel as an independent reliability
instrument for computational content analysis."

本脚本做四件事：
  1) 用同一份 prompt（与 Appendix A 一致）在温度0下调用多个模型标注 300 句金标准；
  2) 每个模型 vs 人工金标准：四类 Cohen κ 与逐框架 F1；
  3) 模型之间：Fleiss' κ（多评分者一致性）；
  4) 多数表决集成(majority vote) vs 金标准：κ 与准确率。
并把"温度0下两次独立运行完全一致"作为可复现性证据(run-to-run)。

输入：output/tables/coding_sample.csv（列：sent_id,text,coder_1_blind,
      coder_2_blind,adjudicated,auto_label,...），金标准口径与 06/09/13 一致。
输出：output/tables/llm_panel_api.csv（逐句各模型标签）
      output/tables/llm_panel_metrics.csv（每模型 κ/F1 + Fleiss + 集成）

★ 铁律：所有调用过的模型都要如实报告，不许只留好看的。换/加模型是为了【增加】
        独立证据。prompt 与所有参数(模型名、版本、temperature、seed、日期)写进论文
        与公开仓库，确保可复现。

依赖：仅需 `requests`。API key 从环境变量读：
      ANTHROPIC_API_KEY / OPENAI_API_KEY / 以及任意 OpenAI 兼容端点(见 MODELS)。
用法：
  python 14_llm_panel_api.py --run 1          # 第一轮，跑通 MODELS 里启用的所有模型
  python 14_llm_panel_api.py --run 2          # 第二轮(复现性)，与第一轮逐句比对
  python 14_llm_panel_api.py --summary        # 汇总 κ/F1/Fleiss/集成
"""
from __future__ import annotations
import os, re, sys, json, time, argparse
import pandas as pd

try:
    import requests
except Exception:
    requests = None

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
TABLES = os.path.join(ROOT, "output", "tables")
SAMPLE = os.path.join(TABLES, "coding_sample.csv")
PANEL_CSV = os.path.join(TABLES, "llm_panel_api.csv")

VALID = ["cap", "con", "both", "neither"]
ALIAS = {"cap": "cap", "capability": "cap", "con": "con", "consequence": "con",
         "both": "both", "neither": "neither", "none": "neither", "na": "neither"}

# ── 把 Appendix A 的定义压成评注指令（与论文/仓库公开的一致）────────────────────
SYSTEM = ("You are an independent annotator applying a fixed codebook to sentences "
          "from official AI-governance documents. Reply with ONLY the label.")
CODEBOOK = """Labels:
- cap: the sentence foregrounds what AI can do (capacities, performance, deployment, innovation).
- con: the sentence foregrounds AI's effects/risks/harms/impacts, OR obligations/responsibilities arising from them.
- both: distinct elements of cap AND con are present.
- neither: neither is foregrounded (procedural provisions, definitions, institutional/cross-reference text).
Decision rule ("about-what"): code by what the sentence is primarily about.
A procedural obligation (filing, registration, reporting deadlines with shall/must) is 'neither'
unless the mandated action is itself substantively about addressing AI consequences."""

# ── 模型清单：把要用的取消注释/补好；endpoint 走 OpenAI 兼容协议 ────────────────
# provider: "anthropic" 或 "openai_compatible"
MODELS = {
    "claude": dict(provider="anthropic",
                   model="claude-opus-4-8",                 # 按需改成你实际用的版本
                   key_env="ANTHROPIC_API_KEY"),
    "gpt":    dict(provider="openai_compatible",
                   model="gpt-5.5",                          # 占位，改成你账号可用模型
                   base="https://api.openai.com/v1",
                   key_env="OPENAI_API_KEY"),
    # 再加 2 个不同厂商可显著增强"独立"说服力，例如：
    # "gemini": dict(provider="openai_compatible", model="...",
    #                base="https://generativelanguage.googleapis.com/v1beta/openai",
    #                key_env="GEMINI_API_KEY"),
    # "qwen":   dict(provider="openai_compatible", model="...",
    #                base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    #                key_env="DASHSCOPE_API_KEY"),
}
SEED = 99
TEMPERATURE = 0.0


def parse_label(txt: str):
    if not txt:
        return None
    w = re.findall(r"[a-zA-Z]+", txt.lower())
    for t in w:
        if t in ALIAS:
            return ALIAS[t]
    return None


def call_anthropic(cfg, sentence):
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        raise RuntimeError(f"缺少环境变量 {cfg['key_env']}")
    r = requests.post(
        "https://api.anthropic.com/v1/messages",
        headers={"x-api-key": key, "anthropic-version": "2023-06-01",
                 "content-type": "application/json"},
        json={"model": cfg["model"], "max_tokens": 8, "temperature": TEMPERATURE,
              "system": SYSTEM + "\n" + CODEBOOK,
              "messages": [{"role": "user",
                            "content": f'Sentence: "{sentence}"\nLabel (cap/con/both/neither):'}]},
        timeout=60)
    r.raise_for_status()
    data = r.json()
    return "".join(b.get("text", "") for b in data.get("content", []))


def call_openai_compatible(cfg, sentence):
    key = os.environ.get(cfg["key_env"], "")
    if not key:
        raise RuntimeError(f"缺少环境变量 {cfg['key_env']}")
    body = {"model": cfg["model"], "temperature": TEMPERATURE, "max_tokens": 8,
            "seed": SEED,
            "messages": [{"role": "system", "content": SYSTEM + "\n" + CODEBOOK},
                         {"role": "user",
                          "content": f'Sentence: "{sentence}"\nLabel (cap/con/both/neither):'}]}
    r = requests.post(cfg["base"].rstrip("/") + "/chat/completions",
                      headers={"Authorization": f"Bearer {key}",
                               "Content-Type": "application/json"},
                      json=body, timeout=60)
    r.raise_for_status()
    return r.json()["choices"][0]["message"]["content"]


def annotate(run: int):
    if requests is None:
        sys.exit("[!] 需要 requests：pip install requests")
    if not os.path.exists(SAMPLE):
        sys.exit(f"[!] 找不到 {SAMPLE}")
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")
    if os.path.exists(PANEL_CSV):
        panel = pd.read_csv(PANEL_CSV, dtype=str).fillna("")
    else:
        panel = df[["sent_id", "text"]].copy()

    for name, cfg in MODELS.items():
        col = f"{name}_run{run}"
        if col in panel.columns and panel[col].isin(VALID).all():
            print(f"[skip] {col} 已存在"); continue
        labels = []
        caller = call_anthropic if cfg["provider"] == "anthropic" else call_openai_compatible
        print(f"[run] 模型 {name} (run {run}) ...")
        for i, row in df.iterrows():
            for attempt in range(4):
                try:
                    lab = parse_label(caller(cfg, row["text"]))
                    break
                except Exception as e:
                    if attempt == 3:
                        print(f"   句 {i} 失败: {e}"); lab = None
                    time.sleep(2 * (attempt + 1))
            labels.append(lab if lab in VALID else "neither")
            if (i + 1) % 25 == 0:
                print(f"   {i+1}/{len(df)}")
        panel[col] = labels
        panel.to_csv(PANEL_CSV, index=False)
        print(f"[saved] {col} -> {PANEL_CSV}")


def summary():
    from sklearn.metrics import cohen_kappa_score, precision_recall_fscore_support
    if not os.path.exists(PANEL_CSV):
        sys.exit("[!] 先跑 --run 1 生成标注")
    s = pd.read_csv(SAMPLE, dtype=str).fillna("")
    panel = pd.read_csv(PANEL_CSV, dtype=str).fillna("")

    def gold(r):
        if r.get("adjudicated", "") in VALID:
            return r["adjudicated"]
        a, b = r.get("coder_1_blind", ""), r.get("coder_2_blind", "")
        return a if (a in VALID and a == b) else None
    s["gold"] = s.apply(gold, axis=1)
    g = s[["sent_id", "gold"]]
    panel = panel.merge(g, on="sent_id", how="left")
    use = panel[panel["gold"].isin(VALID)].copy()

    def perframe_f1(gold_list, pred_list, frame):
        pos = {"cap", "both"} if frame == "capability" else {"con", "both"}
        gg = [1 if x in pos else 0 for x in gold_list]
        pp = [1 if x in pos else 0 for x in pred_list]
        _, _, f1, _ = precision_recall_fscore_support(gg, pp, average="binary",
                                                      zero_division=0)
        return round(f1, 3)

    model_run1_cols = [c for c in use.columns if c.endswith("_run1")]
    rows = []
    for col in model_run1_cols:
        d = use[use[col].isin(VALID)]
        kappa = cohen_kappa_score(d["gold"], d[col])
        rows.append(dict(annotator=col,
                         four_class_kappa=round(kappa, 3),
                         capability_F1=perframe_f1(d["gold"], d[col], "capability"),
                         consequence_F1=perframe_f1(d["gold"], d[col], "consequence"),
                         n=len(d)))
        # run-to-run 复现性
        run2 = col.replace("_run1", "_run2")
        if run2 in use.columns:
            dd = use[use[col].isin(VALID) & use[run2].isin(VALID)]
            rr = cohen_kappa_score(dd[col], dd[run2])
            rows[-1]["run_to_run_kappa"] = round(rr, 3)

    # Fleiss' κ（模型之间，多评分者一致性）
    def fleiss(matrix):
        # matrix: N x k 计数表（每句每类被多少模型选中）
        N, k = matrix.shape
        n = matrix.sum(1)[0]
        p_j = matrix.sum(0) / (N * n)
        P_i = ((matrix ** 2).sum(1) - n) / (n * (n - 1))
        Pbar = P_i.mean(); Pe = (p_j ** 2).sum()
        return (Pbar - Pe) / (1 - Pe) if (1 - Pe) else float("nan")

    import numpy as np
    cats = VALID
    M = []
    sub = use.dropna(subset=model_run1_cols)
    sub = sub[(sub[model_run1_cols].isin(VALID)).all(axis=1)]
    for _, r in sub.iterrows():
        counts = [sum(r[c] == cat for c in model_run1_cols) for cat in cats]
        M.append(counts)
    fk = fleiss(np.array(M)) if M else float("nan")

    # 多数表决集成 vs 金标准
    def majority(r):
        votes = [r[c] for c in model_run1_cols if r[c] in VALID]
        return max(set(votes), key=votes.count) if votes else None
    use["ensemble"] = use.apply(majority, axis=1)
    de = use[use["ensemble"].isin(VALID)]
    ens_kappa = cohen_kappa_score(de["gold"], de["ensemble"])
    ens_acc = (de["gold"] == de["ensemble"]).mean()

    out = pd.DataFrame(rows)
    out.to_csv(os.path.join(TABLES, "llm_panel_metrics.csv"), index=False)
    print("\n===== 多模型独立标注小组：对人工金标准 =====")
    print(out.to_string(index=False))
    print(f"\n模型间一致性 Fleiss' κ = {fk:.3f}  (n_models={len(model_run1_cols)})")
    print(f"多数表决集成 vs 金标准: κ = {ens_kappa:.3f}, accuracy = {ens_acc:.3f}")
    print(f"\n[saved] llm_panel_metrics.csv -> {TABLES}/")
    print("\n论文写法：把 §4.1 的 LLM 校验重述为'an independent, reproducible")
    print("multi-model annotation panel (temperature 0, fixed seed, run-to-run κ=…)';")
    print("报告每个模型的 κ/F1、模型间 Fleiss' κ、以及集成与金标准的一致，强调")
    print("这是在无法增加人工编码者时，对作者编码的独立、可复现校验。")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", type=int, default=0)
    ap.add_argument("--summary", action="store_true")
    a = ap.parse_args()
    if a.summary:
        summary()
    elif a.run:
        annotate(a.run)
    else:
        ap.print_help()
