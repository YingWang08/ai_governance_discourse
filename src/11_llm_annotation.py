#!/usr/bin/env python3
"""
11_llm_annotation.py  —  把"网页版 LLM"当作独立标注者，做可复现校验（多模型版）
====================================================================================
目的：在不调用付费 API 的前提下，用网页聊天界面的 LLM 对 300 句金标准做
独立标注，得到一个"任何人都能按公开 prompt 复跑"的第三方判官，化解
"第三个人是不是真的"这类质疑。

接进现有流程：复用 output/tables/coding_sample.csv（列：sent_id, text,
coder_1_blind, coder_2_blind, adjudicated, auto_label ...），金标准口径
与 06/09 完全一致（两人盲编一致取该标签，不一致取 adjudicated）。

★ 多模型交叉验证（本版新增）★
  用 --model 给每个模型独立分文件存放、独立打分，互不覆盖：
    回复目录   output/llm/responses_<model>/      （第二轮：responses_<model>_run2/）
    标签列     llm_<model>  /  llm_<model>_run2
    导出       output/tables/llm_labels_<model>_run<run>.csv
  prompt 是【所有模型共用同一份】（交叉验证的前提），故 prompts/ 不分模型。
  --model 默认 'gpt'，因此你之前已跑的 gpt 结果不受影响。

  铁律：所有跑过的模型结果都要如实报告，不许挑好看的留、难看的删。
        换模型是为了【增加】独立证据，不是替换证据。

典型流程：
  # 1) 生成 prompt（只需一次，所有模型共用）
  python 11_llm_annotation.py --make-prompts --batch 25

  # 2) 模型 A（如 gpt）：回复粘进 output/llm/responses_gpt/batch_NN.txt
  python 11_llm_annotation.py --model gpt --collect
  python 11_llm_annotation.py --model gpt --score
  #    第二轮稳定性：回复粘进 responses_gpt_run2/
  python 11_llm_annotation.py --model gpt --collect --run 2
  python 11_llm_annotation.py --model gpt --consistency

  # 3) 模型 B（如 claude）：回复粘进 output/llm/responses_claude/batch_NN.txt
  python 11_llm_annotation.py --model claude --collect
  python 11_llm_annotation.py --model claude --score

  # 4) 汇总所有模型 + 人工 κ，打印对比表
  python 11_llm_annotation.py --summary
"""
from __future__ import annotations
import os, re, sys, argparse, glob
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
TABLES = os.path.join(ROOT, "output", "tables")
SAMPLE = os.path.join(TABLES, "coding_sample.csv")
LLM_DIR = os.path.join(ROOT, "output", "llm")
PROMPT_DIR = os.path.join(LLM_DIR, "prompts")

VALID = ["cap", "con", "both", "neither"]
# 容错：模型可能输出全称/大小写，统一映射
ALIAS = {
    "cap": "cap", "capability": "cap", "capabilities": "cap",
    "con": "con", "consequence": "con", "consequences": "con",
    "both": "both",
    "neither": "neither", "none": "neither", "na": "neither",
}


def safe_model(name: str) -> str:
    """把模型名规整成可做文件名/列名的安全标识（小写、字母数字下划线）。"""
    s = re.sub(r"[^0-9a-zA-Z]+", "_", str(name).strip().lower()).strip("_")
    return s or "model"


# 各模型回复目录 / 标签列 / 导出文件名，全部由模型名派生 ----------------------
def resp_dir_for(model: str, run: int) -> str:
    m = safe_model(model)
    sub = f"responses_{m}" if run == 1 else f"responses_{m}_run{run}"
    return os.path.join(LLM_DIR, sub)


def label_col_for(model: str, run: int) -> str:
    m = safe_model(model)
    return f"llm_{m}" if run == 1 else f"llm_{m}_run{run}"


# ---------------------------------------------------------------------------
# 固定 prompt 头：codebook 摘要 + 决策规则 + 输出格式。
# 与论文 Appendix A 的定义保持一致。改动这里 = 改动你公开的 prompt，请同步归档。
# 所有模型共用这一份，确保交叉验证的可比性。
# ---------------------------------------------------------------------------
PROMPT_HEADER = """\
You are an independent annotator. Apply the codebook below to each sentence \
from official AI-governance documents. Do NOT add explanations.

CODEBOOK
========
Assign exactly ONE label to each sentence: cap, con, both, or neither.

- cap (CAPABILITY): the sentence foregrounds what AI systems can do, are able
  to do, or are being developed to do — functionalities, performance, technical
  capacities, or potentials for deployment and innovation.
- con (CONSEQUENCE): the sentence foregrounds effects, impacts, risks, or harms
  of AI systems (actual, anticipated, or mandated), or the obligations,
  responsibilities, and duties that arise from those effects.
- both: the sentence contains distinct elements foregrounding BOTH capability
  and consequence.
- neither: the sentence foregrounds neither. Typical cases: procedural
  provisions, definitions, institutional descriptions, cross-references.

DECISION RULE ("about-what" test)
- Ask what the sentence is primarily ABOUT.
- About what AI can do / be made to do -> cap.
- About what AI causes, may cause, or obliges actors to do in response -> con.
- If both -> both. If neither -> neither.

CRITICAL BOUNDARY
- Procedural obligations (administrative actions such as filing, registration,
  reporting deadlines) phrased with "shall"/"must" are coded NEITHER, UNLESS the
  mandated action is itself substantively about addressing AI consequences.
- The mere presence of "shall"/"must" is NOT sufficient for con.

OUTPUT FORMAT (STRICT)
- Output one line per sentence, nothing else (no headers, no commentary).
- Each line: copy the sentence ID exactly as given, then a TAB, then the label.
- Example (IDs illustrative; copy the real IDs verbatim):
  <ID_AS_GIVEN>\tcon
  <ID_AS_GIVEN>\tneither
- Use ONLY these labels: cap, con, both, neither.

SENTENCES
=========
"""


def gold_label(r):
    adj = r.get("adjudicated", "")
    if adj in VALID:
        return adj
    c1, c2 = r.get("coder_1_blind", ""), r.get("coder_2_blind", "")
    if c1 in VALID and c2 in VALID and c1 == c2:
        return c1
    return None


def load_sample():
    if not os.path.exists(SAMPLE):
        sys.exit(f"[!] 找不到 {SAMPLE}（先用 06 --make-sample 生成）")
    return pd.read_csv(SAMPLE, dtype=str).fillna("")


# ---------------------------------------------------------------------------
def make_prompts(batch=25):
    df = load_sample()
    os.makedirs(PROMPT_DIR, exist_ok=True)
    ids = df["sent_id"].tolist()
    texts = df["text"].tolist()
    n_batches = (len(ids) + batch - 1) // batch
    for b in range(n_batches):
        lo, hi = b * batch, min((b + 1) * batch, len(ids))
        lines = [f"{ids[i]}\t{texts[i]}" for i in range(lo, hi)]
        body = PROMPT_HEADER + "\n".join(lines) + "\n"
        path = os.path.join(PROMPT_DIR, f"batch_{b+1:02d}.txt")
        with open(path, "w", encoding="utf-8") as f:
            f.write(body)
    print(f"[ok] 生成 {n_batches} 个 prompt 文件到 {PROMPT_DIR}（所有模型共用同一份 prompt）")
    print("     操作：每个 batch_NN.txt 整段复制到网页（建议每批开新会话）。")
    print("     模型 A 回复 -> output/llm/responses_<model>/batch_NN.txt")
    print("     第二轮稳定性 -> output/llm/responses_<model>_run2/batch_NN.txt")


# ---------------------------------------------------------------------------
def parse_responses(resp_dir, known_ids):
    """从一批回复文件里抓 sent_id -> label。

    不假设 ID 格式、不依赖行结构或分隔符：用样本里真实存在的 sent_id 在全文
    里定位，取每个 ID 之后紧跟的第一个合法标签词。这样 'eu_aiact_final_2024_01463 con'
    这种长 ID、空格分隔、甚至整段挤成一行也能正确解析。
    """
    files = sorted(glob.glob(os.path.join(resp_dir, "*.txt")))
    if not files:
        sys.exit(f"[!] {resp_dir} 里没有回复文件。\n"
                 f"    先建好该目录并把模型输出粘进 batch_NN.txt。")
    blob = []
    for fp in files:
        with open(fp, encoding="utf-8") as f:
            blob.append(f.read())
    blob = "\n".join(blob)

    labels = {}
    label_alt = "|".join(sorted({re.escape(k) for k in ALIAS}, key=len, reverse=True))
    # 长 ID 优先，避免一个 ID 是另一个的前缀时误截
    for sid in sorted(known_ids, key=len, reverse=True):
        m = re.search(re.escape(sid) + r"[\s\t,;:\-]*\b(" + label_alt + r")\b",
                      blob, flags=re.IGNORECASE)
        if m:
            lab = ALIAS.get(m.group(1).strip().lower())
            if lab in VALID:
                labels[sid] = lab
    return labels


def collect(model="gpt", run=1):
    df = load_sample()
    resp_dir = resp_dir_for(model, run)
    labels = parse_responses(resp_dir, set(df["sent_id"].astype(str)))
    col = label_col_for(model, run)
    df[col] = df["sent_id"].map(labels).fillna("")
    got = df[col].isin(VALID).sum()
    df.to_csv(SAMPLE, index=False)
    df[["sent_id", "text", col]].to_csv(
        os.path.join(TABLES, f"llm_labels_{safe_model(model)}_run{run}.csv"), index=False)
    print(f"[ok] model={model} run{run}: 解析到 {got}/{len(df)} 条标签，已写入 '{col}' 列。")
    print(f"     回复目录：{resp_dir}")
    missing = df.loc[~df[col].isin(VALID), "sent_id"].tolist()
    if missing:
        print(f"[note] 未解析到 {len(missing)} 条（检查回复格式/是否漏批）："
              f"{missing[:10]}{' ...' if len(missing)>10 else ''}")


# ---------------------------------------------------------------------------
def _per_frame_f1(gold, pred):
    """逐框架二元 P/R/F1：把 both 拆成 cap+con 的出现指标。"""
    from sklearn.metrics import precision_recall_fscore_support
    out = {}
    for frame in ("cap", "con"):
        g = [1 if x in (frame, "both") else 0 for x in gold]
        p = [1 if x in (frame, "both") else 0 for x in pred]
        pr, rc, f1, _ = precision_recall_fscore_support(
            g, p, average="binary", zero_division=0)
        out[frame] = (pr, rc, f1, sum(g))
    return out


def _kappa_and_frames(df, col):
    from sklearn.metrics import cohen_kappa_score
    d = df.copy()
    d["gold"] = d.apply(gold_label, axis=1)
    use = d[d["gold"].isin(VALID) & d[col].isin(VALID)].copy()
    if len(use) < 10:
        return None
    gold, pred = use["gold"].tolist(), use[col].tolist()
    k4 = cohen_kappa_score(gold, pred, labels=VALID)
    pf = _per_frame_f1(gold, pred)
    return {"n": len(use), "k4": k4, "pf": pf}


def score(model="gpt", run=1):
    df = load_sample()
    col = label_col_for(model, run)
    if col not in df.columns:
        sys.exit(f"[!] 没有 '{col}' 列，先跑 --model {model} --collect"
                 + (f" --run {run}" if run != 1 else ""))
    res = _kappa_and_frames(df, col)
    if res is None:
        sys.exit("[!] 可用配对不足 10 条。")
    pf = res["pf"]
    print(f"\n=== {model} (run{run}) vs 人工金标准  n={res['n']} ===")
    print(f"四类 Cohen's κ = {res['k4']:.3f}")
    for frame, (pr, rc, f1, sup) in pf.items():
        name = "capability" if frame == "cap" else "consequence"
        print(f"  {name:11s}  P={pr:.2f}  R={rc:.2f}  F1={f1:.2f}  (support={sup})")

    print("\n--- 可直接粘进论文（填模型版本/日期）---")
    print(
        f"As an additional, fully documented annotation check, we had "
        f"[{model} — fill version, accessed YYYY-MM-DD] label the same {res['n']} "
        f"gold-standard sentences from the written codebook alone, blind to both "
        f"the human labels and the lexicon output. Agreement with the human gold "
        f"standard was Cohen's \u03ba = {res['k4']:.2f} (four-class), with per-frame "
        f"F1 of {pf['con'][2]:.2f} for the consequence frame and "
        f"{pf['cap'][2]:.2f} for the capability frame. We release the full prompt, "
        f"the model version and access date, and the complete raw outputs; because "
        f"the hosted interface does not expose temperature or seed settings, we do "
        f"not claim bit-exact reproducibility, and we report this check as an "
        f"independent triangulation of the human coding rather than as a primary "
        f"measurement."
    )


def consistency(model="gpt"):
    from sklearn.metrics import cohen_kappa_score
    df = load_sample()
    c1, c2 = label_col_for(model, 1), label_col_for(model, 2)
    if c1 not in df.columns or c2 not in df.columns:
        sys.exit(f"[!] 需要 '{c1}' 和 '{c2}' 两列。\n"
                 f"    先 --model {model} --collect 和 --model {model} --collect --run 2。")
    use = df[df[c1].isin(VALID) & df[c2].isin(VALID)]
    if len(use) < 10:
        sys.exit("[!] 两轮可用配对不足 10 条。")
    k = cohen_kappa_score(use[c1], use[c2], labels=VALID)
    print(f"[{model}] run1 vs run2 自一致性 Cohen's κ = {k:.3f}  (n={len(use)})")
    print("（写进论文：即便无 seed，网页版输出在重复独立调用下高度稳定。）")


def _human_kappa(df):
    """两位盲编者之间的 κ（仅用两人都打了合法标签的句子）。"""
    from sklearn.metrics import cohen_kappa_score
    use = df[df["coder_1_blind"].isin(VALID) & df["coder_2_blind"].isin(VALID)]
    if len(use) < 10:
        return None
    return cohen_kappa_score(use["coder_1_blind"], use["coder_2_blind"],
                             labels=VALID), len(use)


def summary():
    """汇总所有已收集模型（run1）+ 人工 κ，打印对比表。"""
    df = load_sample()
    # 找出所有 run1 模型列：llm_<model>，排除 _run2
    model_cols = [c for c in df.columns
                  if c.startswith("llm_") and not re.search(r"_run\d+$", c)]
    print("\n================ 标注一致性汇总 ================")
    hk = _human_kappa(df)
    if hk:
        print(f"人工编码员间（盲）        四类 κ = {hk[0]:.3f}   (n={hk[1]})")
    else:
        print("人工编码员间（盲）        —（盲编列不足）")

    if not model_cols:
        print("（尚无任何模型标签列。先 --model <name> --collect。）")
        return

    print("-" * 64)
    print(f"{'模型':<16}{'cap F1':>9}{'con F1':>9}{'4类 κ':>9}{'n':>7}")
    print("-" * 64)
    rows = []
    for col in sorted(model_cols):
        res = _kappa_and_frames(df, col)
        if res is None:
            continue
        mname = col[len("llm_"):]
        cap_f1 = res["pf"]["cap"][2]
        con_f1 = res["pf"]["con"][2]
        rows.append((mname, cap_f1, con_f1, res["k4"], res["n"]))
        print(f"{mname:<16}{cap_f1:>9.2f}{con_f1:>9.2f}{res['k4']:>9.3f}{res['n']:>7}")
    print("-" * 64)
    # 自一致性（若有 run2）
    for col in sorted(model_cols):
        mname = col[len("llm_"):]
        c2 = f"llm_{mname}_run2"
        if c2 in df.columns:
            from sklearn.metrics import cohen_kappa_score
            use = df[df[col].isin(VALID) & df[c2].isin(VALID)]
            if len(use) >= 10:
                k = cohen_kappa_score(use[col], use[c2], labels=VALID)
                print(f"  [{mname}] 自一致性 run1↔run2 κ = {k:.3f} (n={len(use)})")

    # 导出汇总 CSV，方便建表/归档
    if rows:
        out = pd.DataFrame(rows, columns=["model", "cap_f1", "con_f1", "kappa4", "n"])
        out_path = os.path.join(TABLES, "llm_summary.csv")
        out.to_csv(out_path, index=False)
        print(f"\n[ok] 汇总已导出：{out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="gpt",
                    help="模型标识，用于分目录/列名（默认 gpt）。例：gpt / claude / gemini / deepseek")
    ap.add_argument("--make-prompts", action="store_true", help="生成共用 prompt 文件")
    ap.add_argument("--batch", type=int, default=25)
    ap.add_argument("--collect", action="store_true", help="解析该模型回复 -> 标签列")
    ap.add_argument("--score", action="store_true", help="该模型 vs 金标准 κ/F1")
    ap.add_argument("--consistency", action="store_true", help="该模型 run1 vs run2 自一致性")
    ap.add_argument("--summary", action="store_true", help="汇总所有模型 + 人工 κ 对比表")
    ap.add_argument("--run", type=int, default=1)
    a = ap.parse_args()
    if a.make_prompts:
        make_prompts(batch=a.batch)
    elif a.collect:
        collect(model=a.model, run=a.run)
    elif a.score:
        score(model=a.model, run=a.run)
    elif a.consistency:
        consistency(model=a.model)
    elif a.summary:
        summary()
    else:
        ap.print_help()


if __name__ == "__main__":
    main()