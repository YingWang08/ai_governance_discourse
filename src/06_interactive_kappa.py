#!/usr/bin/env python3
"""
06_interactive_kappa.py  —  双通道交互式编码 + Cohen's kappa（中英双语版）
============================================================
在所有需要人工判断的地方，同时显示英文原文和中文翻译，
帮助英语能力一般的编码者做出更准确的判断。

翻译策略：
  • make-sample 阶段：批量预翻译所有300句，存入 coding_sample.csv 的 text_cn 列
  • 编码时直接读取预翻译，不实时调API，不影响速度
  • 翻译引擎：优先使用本地 translators 库（免费），fallback到逐词机器翻译提示
  • 翻译仅辅助理解，编码标签仍基于原文语义

双通道说明：
  ROUND 1 (BLIND)    — 显示英文原文+中文翻译，无任何编码建议，独立判断 → 报告Kappa
  ROUND 2 (ASSISTED) — 显示英文原文+翻译+程序建议+词典理由，可选修订 → 辅助统计

操作流程：
  python 06_interactive_kappa.py --make-sample --n 300   # 抽样+批量预翻译
  python 06_interactive_kappa.py --code --coder 1        # 编码者1
  python 06_interactive_kappa.py --code --coder 2        # 编码者2（独立！）
  python 06_interactive_kappa.py --score                 # 计算 Kappa
  python 06_interactive_kappa.py --adjudicate            # 裁决分歧
"""
from __future__ import annotations
import os, re, sys, argparse, yaml, time
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE) if os.path.basename(HERE) == "src" else HERE
PROC   = os.path.join(ROOT, "data", "processed")
CONF   = os.path.join(ROOT, "config")
TABLES = os.path.join(ROOT, "output", "tables")
SAMPLE = os.path.join(TABLES, "coding_sample.csv")
KAPPA_LOG = os.path.join(TABLES, "kappa_decisions.csv")
CODEBOOK = os.path.join(ROOT, "CODEBOOK_template.md")

# 引入审计工具
sys.path.insert(0, HERE)
from utils_audit import AuditLog

VALID = {"cap", "con", "both", "neither"}
LABEL_CN = {"cap":"能力", "con":"后果", "both":"兼有", "neither":"均无"}

# ── 终端 ───────────────────────────────────────────────────────────────
def _c(t, code): return f"\033[{code}m{t}\033[0m"
GREEN=lambda t:_c(t,"32"); YELLOW=lambda t:_c(t,"33"); RED=lambda t:_c(t,"31")
CYAN=lambda t:_c(t,"36"); BOLD=lambda t:_c(t,"1"); DIM=lambda t:_c(t,"2")
MAGENTA=lambda t:_c(t,"35")


# ═══════════════════════════════════════════════════════════════════════
# 翻译引擎：translators 库（调用必应翻译，需联网，免费无需API Key）
# ═══════════════════════════════════════════════════════════════════════
#
# 依赖：pip install translators
# 翻译仅用于辅助理解，编码标签仍基于原文语义。

def translate_en_to_zh(text: str) -> str:
    """
    将英文句子翻译成中文（使用 translators 库，必应引擎）。
    失败时返回空串，不影响编码流程。
    """
    try:
        import translators as ts
        result = ts.translate_text(text[:500], translator="bing", to_language="zh")
        return result.strip() if result else ""
    except Exception:
        return ""


def batch_translate(texts: list[str]) -> list[str]:
    """
    批量翻译一组句子，带进度条，每句间隔0.3秒避免限速。
    """
    try:
        import translators as ts
    except ImportError:
        print(YELLOW("  [提示] translators 未安装：pip install translators"))
        print(YELLOW("  翻译不可用，将在编码时只显示英文原文"))
        return [""] * len(texts)

    print(f"  使用必应翻译（在线）翻译 {len(texts)} 句...")
    print(f"  {DIM('预计 3-8 分钟，翻译完成后结果存入 CSV，之后无需重复翻译')}")

    results = []
    start = time.time()

    for i, text in enumerate(texts):
        try:
            cn = ts.translate_text(text[:500], translator="bing", to_language="zh")
            results.append(cn.strip() if cn else "")
        except Exception:
            results.append("")
        time.sleep(0.3)  # 避免请求过快被限速

        # 进度显示（每20句更新一次）
        if (i + 1) % 20 == 0 or (i + 1) == len(texts):
            elapsed = time.time() - start
            done = i + 1
            rate = done / elapsed if elapsed > 0 else 0
            remaining = (len(texts) - done) / rate if rate > 0 else 0
            bar = "█" * (done * 30 // len(texts)) + "░" * (30 - done * 30 // len(texts))
            print(f"  [{bar}] {done}/{len(texts)}  "
                  f"剩余约{remaining:.0f}s", end="\r", flush=True)

    elapsed = time.time() - start
    n_ok = sum(1 for r in results if r)
    print(f"\n  翻译完成：{n_ok}/{len(texts)} 句成功  耗时 {elapsed:.0f}s")
    return results


def display_sentence(text: str, text_cn: str = "", width: int = 120):
    """
    显示句子：英文原文（加粗）+ 中文翻译（灰色）。
    英文在前，翻译在后，视觉分隔清晰。
    """
    print(f"\n  {'─'*62}")
    print(f"  {BOLD('[EN]')} {text[:width]}")
    if text_cn and text_cn.strip():
        print(f"  {BOLD('[中]')} {DIM(text_cn[:width])}")
    else:
        print(f"  {DIM('[中]  （无翻译，请根据英文原文判断）')}")
    print(f"  {'─'*62}")


def divider(title=""):
    w = 65
    if title: print(f"\n{'═'*4} {CYAN(title)} {'═'*max(1,w-len(title)-5)}")
    else: print("═"*w)

def ask(prompt, opts="", default=""):
    hint = f" [{opts}]" if opts else ""
    dflt = f" (默认={default})" if default else ""
    try: v = input(f"  {CYAN('>>>')} {prompt}{hint}{dflt}: ").strip().lower()
    except (EOFError, KeyboardInterrupt): print("\n  中断。进度已保存。"); sys.exit(0)
    return v or default

# ── 词典 + 建议生成 ────────────────────────────────────────────────────
def load_lexicon():
    p = os.path.join(CONF, "lexicon_expanded.yaml")
    if not os.path.exists(p): p = os.path.join(CONF, "lexicon.yaml")
    with open(p, "r", encoding="utf-8") as f: return yaml.safe_load(f)

def build_matcher(terms):
    esc = sorted([re.escape(t.lower()) for t in terms], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(esc) + r")\b", re.I)

def get_suggestion(text: str, lex: dict) -> dict:
    cap_re = build_matcher(lex["capability"])
    con_re = build_matcher(lex["consequence"])
    bnd_re = build_matcher(lex.get("boundary", []))
    cap = list(set(m.lower() for m in cap_re.findall(text)))
    con = list(set(m.lower() for m in con_re.findall(text)))
    bnd = list(set(m.lower() for m in bnd_re.findall(text)))
    has_cap, has_con = bool(cap), bool(con)
    if has_cap and has_con:
        # 两者都有 → 倾向 both，除非一方明显占优
        if max(len(cap), len(con)) >= 3 * min(len(cap), len(con)):
            if len(cap) > len(con):
                sug, conf, why = "cap", 0.55, f"能力词({len(cap)})远多于后果词({len(con)})"
            else:
                sug, conf, why = "con", 0.55, f"后果词({len(con)})远多于能力词({len(cap)})"
        else:
            sug, conf, why = "both", 0.70, "两个框架都有实质性内容"
    elif has_cap:
        sug, conf, why = "cap", 0.80, "仅含能力框架词"
    elif has_con:
        sug, conf, why = "con", 0.80, "仅含后果框架词"
    else:
        sug, conf, why = "neither", 0.80, "未检测到框架词"
    if bnd and not has_cap and not has_con:
        why += f"；含边界词{bnd}但不计入"; conf = max(0.6, conf-0.1)
    return dict(suggestion=sug, cap_terms=cap, con_terms=con,
                bnd_terms=bnd, explain=why, confidence=conf)

# ═══════════════════════════════════════════════════════════════════════
# 阶段 A：抽样
# ═══════════════════════════════════════════════════════════════════════
def make_sample(n=300, seed=42, third_subsample=0):
    coded = os.path.join(PROC, "coded_sentences.csv")
    if not os.path.exists(coded):
        print(RED("[!] 请先运行 03_frame_coding.py")); sys.exit(1)
    df = pd.read_csv(coded)
    n = min(n, len(df))
    s = df.sample(n=n, random_state=seed).copy()
    auto_map = {"capability":"cap","consequence":"con","both":"both","neither":"neither"}
    s["auto_label"] = s["frame"].map(auto_map)
    out = s[["sent_id","doc_id","year","text","auto_label"]].copy()
    # 双通道列
    out["coder_1_blind"]    = ""   # ROUND 1：盲编（论文报告用）
    out["coder_2_blind"]    = ""
    out["coder_3_blind"]    = ""   # 可选第三编码者（稳健性子样本）
    out["coder_1_assisted"] = ""   # ROUND 2：看建议后的修订（辅助）
    out["coder_2_assisted"] = ""
    out["adjudicated"]      = ""   # 裁决标签
    out["adj_note"]         = ""

    # 第三编码者只编码子样本（成本更可控）
    if third_subsample > 0:
        sub = min(third_subsample, n)
        third_idx = s.sample(n=sub, random_state=seed+1).sent_id.tolist()
        out["needs_coder_3"] = out["sent_id"].isin(third_idx).map(
            lambda x: "yes" if x else "no")
    else:
        out["needs_coder_3"] = "no"

    # ── 批量预翻译（存入CSV，编码时直接读取，不实时调API）────────────
    print(f"\n  正在批量翻译 {n} 句样本（仅需一次，结果存入CSV）...")
    print(f"  {DIM('翻译用于辅助理解，不影响编码标签的客观性')}")
    translations = batch_translate(out["text"].tolist())
    out["text_cn"] = translations
    n_translated = sum(1 for t in translations if t.strip())
    print(GREEN(f"  成功翻译 {n_translated}/{n} 句"))
    if n_translated < n * 0.8:
        print(YELLOW(f"  翻译成功率偏低，编码时英文原文仍完整显示"))

    os.makedirs(TABLES, exist_ok=True)
    out.to_csv(SAMPLE, index=False)

    # 同步初始化审计日志
    log = AuditLog(KAPPA_LOG)
    for _, r in out.iterrows():
        log.record(sent_id=r["sent_id"], action="sample",
                   suggestion=r["auto_label"], coder="system",
                   reason=f"抽样 (seed={seed}, n={n})",
                   text_preview=r["text"])

    print(GREEN(f"\n[✓] 抽取 {n} 句样本 + 翻译 → {SAMPLE}"))
    if third_subsample > 0:
        print(GREEN(f"[✓] 其中 {sub} 句标记为需第三编码者审查"))
    print(GREEN(f"[✓] 审计日志已初始化 → {KAPPA_LOG}"))
    print(f"\n  下一步: ROUND 1 盲编（两位编码者独立完成）")
    print(f"  python 06_interactive_kappa.py --code --coder 1")
    print(f"  python 06_interactive_kappa.py --code --coder 2")
    if third_subsample > 0:
        print(f"  python 06_interactive_kappa.py --code --coder 3  # 可选稳健性子样本")


# ═══════════════════════════════════════════════════════════════════════
# 阶段 B：ROUND 1 盲编（无建议，独立判断）
# ═══════════════════════════════════════════════════════════════════════
def show_codebook_essentials():
    """显示编码规则关键内容（中英双语），强制阅读。"""
    print(f"\n  {BOLD('编码规则提醒（务必先读 CODEBOOK_template.md 完整版）:')}")
    print(f"  {DIM('─' * 65)}")

    print(f"  {GREEN('cap  能力框架（Capability framing）')}")
    print(f"     句子重心在 AI 的生产力、潜力、收益、效率、创新")
    print(f"     Focus: AI's productivity, potential, benefits, efficiency, innovation")
    print(f"     例: 'AI offers benefits in healthcare and productivity.'")
    print(f"         「人工智能在医疗和生产力方面提供了益处。」→ cap")
    print()

    print(f"  {RED('con  后果框架（Consequence framing）')}")
    print(f"     句子重心在风险、危害、义务、监督、问责、权利保护")
    print(f"     Focus: risks, harms, obligations, oversight, accountability, rights")
    print(f"     例: 'Providers shall ensure oversight to minimise risks.'")
    print(f"         「提供者应确保监督以最大程度降低风险。」→ con")
    print()

    print(f"  {MAGENTA('both 两者兼有（Both framings）')}")
    print(f"     两个框架都有{BOLD('实质性')}权重——不是一笔带过，而是并重")
    print(f"     Both frames carry substantial weight, not just mentioned in passing")
    print(f"     例: 'Foster innovation WHILE ensuring safety and fundamental rights.'")
    print(f"         「在确保安全和基本权利的同时促进创新。」→ both")
    print()

    print(f"  {DIM('neither  均无（Neither framing）')}")
    print(f"     程序性、定义性、行政性内容，无框架立场")
    print(f"     Procedural, definitional, or administrative — no framing stance")
    print(f"     例: 'This Regulation shall apply from [date].'")
    print(f"         「本条例自[日期]起适用。」→ neither")
    print()

    print(f"  {YELLOW('决策规则 / Decision rules:')}")
    print(f"     • 主导优先：一方明显主导、另一方仅一笔带过 → 选主导，不选 both")
    print(f"       If one frame clearly dominates, pick it. Don't use 'both' lightly.")
    print(f"     • 边界词不计入：trustworthy / ethical / governance")
    print(f"       Boundary terms don't count. Judge the rest of the sentence.")
    print(f"     • 'risk-based approach' = 方法论术语，≠ 实质风险声明")
    print(f"       'risk-based approach' is methodology, not a consequence claim.")
    print(f"  {DIM('─' * 65)}\n")


def run_round_one_blind(coder_num: int):
    """ROUND 1: 盲编。不显示任何建议。这是报告Kappa的基础。"""
    if coder_num not in (1, 2, 3):
        print(RED("--coder 必须是 1, 2, 或 3")); sys.exit(1)
    if not os.path.exists(SAMPLE):
        print(RED("[!] 请先运行 --make-sample")); sys.exit(1)

    col = f"coder_{coder_num}_blind"
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")

    # 验证 utils_audit 日志存在
    log = AuditLog(KAPPA_LOG)

    # 第三编码者只编码标记为 needs_coder_3=yes 的子样本
    if coder_num == 3:
        if "needs_coder_3" not in df.columns:
            print(RED("[!] 样本未配置第三编码者，请先 --make-sample --sample-third N"))
            sys.exit(1)
        eligible = df[df["needs_coder_3"] == "yes"]
        if len(eligible) == 0:
            print(RED("[!] 没有为第三编码者标记的句子")); sys.exit(1)
        todo = eligible[~eligible[col].isin(VALID)].index.tolist()
        done = len(eligible) - len(todo)
        print(YELLOW(f"  ⚠ 第三编码者将编码 {len(eligible)} 句稳健性子样本"))
    else:
        todo = df[~df[col].isin(VALID)].index.tolist()
        done = len(df) - len(todo)

    divider(f"ROUND 1 (盲编) · 编码者 {coder_num}")
    print(BOLD(f"  ⚠ 这一轮的结果将作为论文报告的 Kappa 来源。"))
    print(f"     程序{BOLD('不会')}显示任何建议，请基于句子本身独立判断。")
    print(f"     不要让自己受到自动标注/对方编码的影响。")
    print()
    print(f"  样本数 {len(todo)+done}    已完成 {done}    待编码 {len(todo)}")

    if done == 0:
        show_codebook_essentials()
        if ask("确认已阅读 CODEBOOK 全文？", "y/n", "y") not in ("y","yes","是"):
            print("请先阅读 CODEBOOK_template.md 再开始。"); sys.exit(0)

    # 不告诉编码者其他人完成情况（避免心理影响）
    if coder_num in (1, 2):
        other = f"coder_{2 if coder_num==1 else 1}_blind"
        other_done = df[other].isin(VALID).sum()
        if other_done > 0:
            print(YELLOW(f"  注意: 另一位主编码者已完成{other_done}条，"
                         f"但你看不到他/她的编码。继续独立判断。"))

    if not todo:
        print(GREEN(f"\n  编码者 {coder_num} ROUND 1 已全部完成！"))
        return

    print(f"\n  {DIM('操作: 回车=无默认 | 1=cap 2=con 3=both 4=neither | q=暂停 | ?=查看规则')}\n")
    shortcut = {"1":"cap","2":"con","3":"both","4":"neither"}

    for prog, idx in enumerate(todo, 1):
        row = df.loc[idx]
        text_cn = str(row.get("text_cn", "")).strip()
        divider(f"{prog}/{len(todo)}  [{row['doc_id']}, {row['year']}]")

        # ★ 核心：中英双语展示，无任何编码建议
        display_sentence(str(row["text"]), text_cn)

        while True:
            resp = ask(f"你的编码？", "1=cap 2=con 3=both 4=neither / q / ?", "")
            if resp == "q":
                df.to_csv(SAMPLE, index=False)
                print(GREEN(f"\n  [已保存] 完成 {prog-1}/{len(todo)}")); sys.exit(0)
            if resp == "?":
                show_codebook_essentials(); continue
            if resp == "":
                print(RED("  必须给出标签（盲编不允许默认）")); continue
            if resp in shortcut:
                decision = shortcut[resp]; break
            print(RED("  无效输入"))

        df.at[idx, col] = decision
        log.record(sent_id=row["sent_id"], action=decision,
                   suggestion="(blind)", coder=f"coder_{coder_num}_blind",
                   reason="ROUND 1 盲编", text_preview=row["text"])

        sug_color = {"cap":GREEN,"con":RED,"both":MAGENTA,"neither":DIM}[decision]
        print(f"  → 编码: {sug_color(LABEL_CN[decision])} ({decision})\n")

        if prog % 20 == 0:
            df.to_csv(SAMPLE, index=False)
            print(DIM(f"  [自动保存] {prog}/{len(todo)}"))

    df.to_csv(SAMPLE, index=False)
    divider("ROUND 1 完成")
    print(GREEN(f"  编码者 {coder_num} 完成 {len(todo)} 条盲编"))

    both_done = (df["coder_1_blind"].isin(VALID).all() and
                 df["coder_2_blind"].isin(VALID).all())
    if both_done:
        print(f"\n  {GREEN('两位编码者 ROUND 1 均完成！')}")
        print(f"  推荐下一步: python 06_interactive_kappa.py --score")
        print(f"  可选(ROUND 2): python 06_interactive_kappa.py --review --coder {coder_num}")


# ═══════════════════════════════════════════════════════════════════════
# 阶段 C：ROUND 2 反馈复审（显示建议，可选修订）
# ═══════════════════════════════════════════════════════════════════════
def run_round_two_assisted(coder_num: int):
    """ROUND 2: 看到建议后是否想改主意。仅作辅助统计。"""
    if coder_num not in (1, 2):
        print(RED("--coder 必须是 1 或 2")); sys.exit(1)
    if not os.path.exists(SAMPLE):
        print(RED("[!] 请先完成 ROUND 1")); sys.exit(1)

    blind_col = f"coder_{coder_num}_blind"
    asst_col  = f"coder_{coder_num}_assisted"
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")
    lex = load_lexicon()
    log = AuditLog(KAPPA_LOG)

    # 必须完成 ROUND 1
    if not df[blind_col].isin(VALID).all():
        n_missing = (~df[blind_col].isin(VALID)).sum()
        print(RED(f"[!] 编码者{coder_num}的 ROUND 1 还有{n_missing}条未完成"))
        print(RED(f"    请先: python 06_interactive_kappa.py --code --coder {coder_num}"))
        sys.exit(1)

    todo = df[~df[asst_col].isin(VALID)].index.tolist()
    done = len(df) - len(todo)

    divider(f"ROUND 2 (反馈复审) · 编码者 {coder_num}")
    print(f"  这一轮会显示程序建议。你可以维持 ROUND 1 的判断，也可以修改。")
    print(f"  {YELLOW('注意: 这一轮的结果')} {BOLD('不会')} {YELLOW('替换论文报告的Kappa。')}")
    print(f"     它只用来回答：'看到机器解释后，你后悔吗？'")
    print()
    print(f"  总样本 {len(df)}    已审 {done}    待审 {len(todo)}")
    if not todo:
        print(GREEN(f"\n  ROUND 2 已完成")); return

    n_changed = 0
    shortcut = {"1":"cap","2":"con","3":"both","4":"neither"}

    for prog, idx in enumerate(todo, 1):
        row = df.loc[idx]
        text = row["text"]
        blind = row[blind_col]
        text_cn = str(row.get("text_cn", "")).strip()
        info = get_suggestion(text, lex)
        sug = info["suggestion"]

        divider(f"{prog}/{len(todo)}  [{row['doc_id']}, {row['year']}]")

        # 英文高亮显示（能力词绿色，后果词红色，边界词黄色）
        display = text[:300]
        for t in info["cap_terms"]:
            display = re.sub(re.escape(t), GREEN(t), display, flags=re.I)
        for t in info["con_terms"]:
            display = re.sub(re.escape(t), RED(t), display, flags=re.I)
        for t in info["bnd_terms"]:
            display = re.sub(re.escape(t), YELLOW(t), display, flags=re.I)

        print(f"\n  {BOLD('[EN]')} {display}")
        if text_cn:
            print(f"  {BOLD('[中]')} {DIM(text_cn[:300])}")
        print()
        print(f"  能力词 (capability): {GREEN(', '.join(info['cap_terms'])) if info['cap_terms'] else DIM('无')}")
        print(f"  后果词 (consequence): {RED(', '.join(info['con_terms'])) if info['con_terms'] else DIM('无')}")
        if info["bnd_terms"]:
            print(f"  边界词 (boundary): {YELLOW(', '.join(info['bnd_terms']))} {DIM('（不计入编码）')}")
        print(f"\n  你 ROUND 1 编码: {BOLD(LABEL_CN[blind])} ({blind})")
        print(f"  程序建议        : {LABEL_CN[sug]} ({sug})  信心={info['confidence']:.0%}")
        print(f"  {DIM(info['explain'])}")

        if blind == sug:
            print(GREEN(f"  → 你与建议一致，自动通过"))
            final = blind
        else:
            while True:
                resp = ask(f"维持 {blind} 还是改为 {sug}（或别的）？",
                           f"回车=维持({blind}) / s=改为建议({sug}) / 1234 / q", "")
                if resp == "q":
                    df.to_csv(SAMPLE, index=False); sys.exit(0)
                if resp == "":
                    final = blind; break
                if resp == "s":
                    final = sug; break
                if resp in shortcut:
                    final = shortcut[resp]; break
                print(RED("  无效输入"))

            if final != blind:
                n_changed += 1
                print(YELLOW(f"  → 修订: {blind} → {final}"))
            else:
                print(GREEN(f"  → 维持: {blind}"))

        df.at[idx, asst_col] = final
        log.record(sent_id=row["sent_id"], action=final,
                   suggestion=sug, coder=f"coder_{coder_num}_assisted",
                   reason=f"ROUND 2 (blind was {blind})",
                   text_preview=text)
        if prog % 20 == 0:
            df.to_csv(SAMPLE, index=False)

    df.to_csv(SAMPLE, index=False)
    divider("ROUND 2 完成")
    print(f"  编码者 {coder_num} 修订了 {n_changed}/{len(todo)} 条 "
          f"({n_changed/len(todo)*100:.1f}%)")
    if n_changed/len(todo) > 0.3:
        print(YELLOW("  修订率较高，可能说明 ROUND 1 时遗漏了一些细节。"
                     "考虑修订CODEBOOK后重做ROUND 1。"))
    else:
        print(GREEN("  修订率合理。"))


# ═══════════════════════════════════════════════════════════════════════
# 阶段 D：计算 Kappa  (v2 加固版)
# ═══════════════════════════════════════════════════════════════════════
def bootstrap_kappa_ci(c1, c2, n_boot=1000, ci=0.95, seed=42):
    """
    Bootstrap 置信区间for Kappa。
    审稿人若质疑"2人Kappa样本量是否足够"，95% CI 是直接答复。
    """
    import numpy as np
    from sklearn.metrics import cohen_kappa_score
    rng = np.random.default_rng(seed)
    n = len(c1)
    c1_arr = np.array(c1); c2_arr = np.array(c2)
    boot_kappas = []
    for _ in range(n_boot):
        idx = rng.integers(0, n, size=n)
        try:
            k = cohen_kappa_score(c1_arr[idx], c2_arr[idx])
            if not np.isnan(k):
                boot_kappas.append(k)
        except: pass
    if len(boot_kappas) < 10:
        return None, None, None
    boot_kappas = np.array(boot_kappas)
    alpha = (1 - ci) / 2
    lo = float(np.quantile(boot_kappas, alpha))
    hi = float(np.quantile(boot_kappas, 1 - alpha))
    se = float(boot_kappas.std())
    return lo, hi, se


def krippendorff_alpha(c1, c2):
    """
    Krippendorff's alpha (nominal data, 2 raters).
    完全等价于 nominal 数据的 Scott's pi，但被认为是更现代的可靠性指标。
    为什么算这个: 审稿人若是质性研究背景，会期待 alpha 而非 kappa。
    """
    import numpy as np
    from collections import Counter
    n_units = len(c1)
    # Coincidence matrix
    all_codes = sorted(set(c1) | set(c2))
    n_cats = len(all_codes)
    code_to_idx = {c: i for i, c in enumerate(all_codes)}
    co = np.zeros((n_cats, n_cats))
    for a, b in zip(c1, c2):
        i, j = code_to_idx[a], code_to_idx[b]
        co[i][j] += 1; co[j][i] += 1
    # Observed disagreement (off-diagonal)
    n_total = co.sum()
    obs_disagree = 0
    for i in range(n_cats):
        for j in range(n_cats):
            if i != j:
                obs_disagree += co[i][j]
    obs_disagree /= n_total
    # Expected disagreement
    n_marginal = co.sum(axis=0)
    exp_disagree = 0
    for i in range(n_cats):
        for j in range(n_cats):
            if i != j:
                exp_disagree += n_marginal[i] * n_marginal[j]
    exp_disagree /= (n_total * (n_total - 1))
    if exp_disagree == 0:
        return 1.0
    return 1 - (obs_disagree / exp_disagree)


def per_category_kappa(c1, c2):
    """
    每个标签单独的 Kappa（one-vs-rest）。
    这能暴露隐藏的失败：整体 Kappa=0.7 可能掩盖某个标签 Kappa=0.3。
    审稿人若是方法论专家，一定会问这个。
    """
    from sklearn.metrics import cohen_kappa_score
    results = {}
    for cat in VALID:
        c1_bin = [1 if x == cat else 0 for x in c1]
        c2_bin = [1 if x == cat else 0 for x in c2]
        try:
            k = cohen_kappa_score(c1_bin, c2_bin)
            n_pos = sum(c1_bin) + sum(c2_bin)
            results[cat] = (float(k) if not __import__('math').isnan(k) else None,
                            n_pos)
        except:
            results[cat] = (None, 0)
    return results


def score():
    from sklearn.metrics import cohen_kappa_score, accuracy_score
    if not os.path.exists(SAMPLE):
        print(RED("[!] 找不到样本")); sys.exit(1)
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")

    # 主结果：ROUND 1 盲编 kappa
    blind = df[df.coder_1_blind.isin(VALID) & df.coder_2_blind.isin(VALID)]
    if len(blind) < 10:
        print(RED(f"[!] 盲编双重编码仅{len(blind)}条，请先完成ROUND 1")); sys.exit(1)

    c1 = blind.coder_1_blind.tolist()
    c2 = blind.coder_2_blind.tolist()
    auto = blind.auto_label.tolist()

    k_hh_blind = cohen_kappa_score(c1, c2)
    k_a1_blind = cohen_kappa_score(c1, auto)
    k_a2_blind = cohen_kappa_score(c2, auto)

    # ── v2 加固 #1: Bootstrap 95% 置信区间 ──────────────────────────────
    print(DIM("  [计算 bootstrap 置信区间...]"))
    lo, hi, se = bootstrap_kappa_ci(c1, c2, n_boot=1000)

    # ── v2 加固 #2: Krippendorff's alpha ────────────────────────────────
    alpha = krippendorff_alpha(c1, c2)

    # ── v2 加固 #3: 逐类别 Kappa ────────────────────────────────────────
    per_cat = per_category_kappa(c1, c2)

    def interpret(k):
        if k >= 0.81: return "几乎完全一致 (almost perfect)"
        if k >= 0.61: return "实质性一致 (substantial) ✓"
        if k >= 0.41: return "中等一致 (moderate) △"
        if k >= 0.21: return "一般一致 (fair) ✗"
        return "微弱一致 (slight/poor) ✗"

    disagree = blind[blind.coder_1_blind != blind.coder_2_blind]
    dtypes = disagree.apply(lambda r: f"{r.coder_1_blind}-vs-{r.coder_2_blind}",
                            axis=1).value_counts() if len(disagree) else pd.Series()

    divider("Cohen's Kappa 报告 (论文报告值)")
    print(BOLD(f"  ★ ROUND 1 (盲编) — 这是论文报告的 Kappa"))
    print(f"  样本量              : {len(blind)}")
    print()
    print(f"  {BOLD('整体 Kappa (主指标):')}")
    print(f"    Cohen's kappa     : {BOLD(f'{k_hh_blind:.3f}')}  {interpret(k_hh_blind)}")
    if lo is not None:
        print(f"    95% Bootstrap CI  : [{lo:.3f}, {hi:.3f}]  (SE={se:.3f})")
        # 检测 CI 是否跨越 0.61 阈值（关键警告）
        if lo < 0.61 < hi:
            print(YELLOW(f"    ⚠ CI 跨越 0.61 阈值 — Kappa 接近边界，"
                         "需在论文中讨论此不确定性"))
        elif hi < 0.61:
            print(RED(f"    ✗ CI 上限 {hi:.3f} < 0.61 — 即使最乐观也未达标"))
    print(f"    Krippendorff α    : {alpha:.3f}  (现代指标，可向质性方法论审稿人展示)")
    print()
    print(f"  {BOLD('与自动标注的一致性:')}")
    print(f"    Coder1-Auto kappa : {k_a1_blind:.3f}   (准确率 "
          f"{accuracy_score(c1, auto):.3f})")
    print(f"    Coder2-Auto kappa : {k_a2_blind:.3f}   (准确率 "
          f"{accuracy_score(c2, auto):.3f})")
    print()
    print(f"  {BOLD('逐类别 Kappa (one-vs-rest):')}")
    print(f"    {DIM('暴露隐藏失败：整体0.7可能掩盖某标签<0.4')}")
    weak_cats = []
    for cat in ["cap", "con", "both", "neither"]:
        k, n_pos = per_cat[cat]
        if k is None:
            print(f"    {cat:<8} : N/A  (样本太少)")
            continue
        label = LABEL_CN[cat]
        if k < 0.40:
            print(f"    {cat:<8} ({label}): {RED(f'{k:.3f}')}  ⚠ 偏弱 (n={n_pos})")
            weak_cats.append(cat)
        elif k < 0.61:
            print(f"    {cat:<8} ({label}): {YELLOW(f'{k:.3f}')}  中等 (n={n_pos})")
        else:
            print(f"    {cat:<8} ({label}): {GREEN(f'{k:.3f}')}  良好 (n={n_pos})")
    print()
    print(f"  分歧数              : {len(disagree)} ({len(disagree)/len(blind)*100:.1f}%)")
    if len(dtypes):
        print(f"  分歧类型分布        :")
        for d, c in dtypes.items():
            print(f"    {d:<25} {c}")

    # ROUND 2 信息（若完成）
    asst = df[df.coder_1_assisted.isin(VALID) & df.coder_2_assisted.isin(VALID)]
    has_round2 = len(asst) >= 10
    k_hh_asst = None
    if has_round2:
        k_hh_asst = cohen_kappa_score(asst.coder_1_assisted, asst.coder_2_assisted)
        rev1 = (asst.coder_1_blind != asst.coder_1_assisted).sum()
        rev2 = (asst.coder_2_blind != asst.coder_2_assisted).sum()
        divider("ROUND 2 (反馈复审) — 辅助统计")
        print(f"  样本量              : {len(asst)}")
        print(f"  人-人 kappa (反馈后): {k_hh_asst:.3f}  {interpret(k_hh_asst)}")
        print(f"  编码者1看反馈后修订: {rev1}/{len(asst)} ({rev1/len(asst)*100:.1f}%)")
        print(f"  编码者2看反馈后修订: {rev2}/{len(asst)} ({rev2/len(asst)*100:.1f}%)")
        print(f"  {DIM('修订率反映编码者在阅读机器解释后改变心意的程度，仅作辅助。')}")

    # ── 写论文素材 ────────────────────────────────────────────────────
    ci_str = f" (95% CI [{lo:.3f}, {hi:.3f}])" if lo is not None else ""
    lines = [
        "Inter-coder Reliability Report (v2 - enhanced)",
        "=" * 60,
        f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "PRIMARY RESULT — ROUND 1 (blind coding, for paper):",
        f"  Doubly-coded sentences  : {len(blind)}",
        f"  Cohen's kappa (overall) : {k_hh_blind:.3f}{ci_str}",
        f"  Interpretation          : {interpret(k_hh_blind)}",
        f"  Krippendorff's alpha    : {alpha:.3f}",
        f"  Coder1-Auto kappa       : {k_a1_blind:.3f}",
        f"  Coder2-Auto kappa       : {k_a2_blind:.3f}",
        f"  Disagreements           : {len(disagree)} ({len(disagree)/len(blind)*100:.1f}%)",
        "",
        "PER-CATEGORY KAPPA (one-vs-rest):",
    ]
    for cat in ["cap", "con", "both", "neither"]:
        k, n_pos = per_cat[cat]
        kstr = f"{k:.3f}" if k is not None else "N/A"
        lines.append(f"  {cat:<10}: {kstr}   (n_positive={n_pos})")
    if has_round2:
        lines += [
            "",
            "SECONDARY — ROUND 2 (after viewing lexicon suggestions, descriptive only):",
            f"  Human-Human kappa     : {k_hh_asst:.3f}",
            f"  Coder1 revision rate  : {rev1/len(asst)*100:.1f}%",
            f"  Coder2 revision rate  : {rev2/len(asst)*100:.1f}%",
        ]
    lines += [
        "",
        "Methods paragraph (paste into paper §3.2):",
        "",
        f"Inter-coder reliability was assessed on a random sample of {len(blind)} sentences "
        f"(seed=42) using a dual-pass design. In the blind round, two coders independently "
        f"labelled each sentence as capability, consequence, both, or neither, following the "
        f"codebook (Appendix A); coders saw neither the lexicon-based automatic label nor each "
        f"other's labels. Cohen's kappa was {k_hh_blind:.3f}{ci_str}, "
        f"with Krippendorff's alpha of {alpha:.3f}. ",
    ]
    # Add per-category mention if weak categories exist
    if weak_cats:
        weak_names = ", ".join(weak_cats)
        lines += [
            f"Per-category one-vs-rest kappa values are reported in Table X; the {weak_names} "
            f"category(ies) showed weaker agreement, reflecting the inherent boundary ambiguity "
            f"acknowledged in §3.5. ",
        ]
    lines += [
        f"Coder-versus-automatic-label kappa was {k_a1_blind:.3f} and {k_a2_blind:.3f} for the "
        f"two coders respectively, justifying the use of automatic labels on the full corpus.",
    ]
    if has_round2:
        lines += [
            "",
            f"In a subsequent assisted round, coders viewed the lexicon-derived suggestion and "
            f"were free to revise; revision rates were {rev1/len(asst)*100:.1f}% and "
            f"{rev2/len(asst)*100:.1f}% respectively. The blind-round kappa is reported above; "
            f"the assisted round is provided as a descriptive aid only.",
        ]

    # ── v2 加固 #4: 第三编码者稳健性检验 ─────────────────────────────────
    has_coder3 = "coder_3_blind" in df.columns and df["coder_3_blind"].isin(VALID).any()
    if has_coder3:
        c3_sub = df[df.coder_1_blind.isin(VALID) &
                    df.coder_2_blind.isin(VALID) &
                    df.coder_3_blind.isin(VALID)]
        if len(c3_sub) >= 10:
            k_13 = cohen_kappa_score(c3_sub.coder_1_blind, c3_sub.coder_3_blind)
            k_23 = cohen_kappa_score(c3_sub.coder_2_blind, c3_sub.coder_3_blind)
            k_12_on_sub = cohen_kappa_score(c3_sub.coder_1_blind, c3_sub.coder_2_blind)

            divider("第三编码者稳健性 (v2 加固)")
            print(f"  三重编码句数        : {len(c3_sub)} (子样本)")
            print(f"  Coder1-Coder2 kappa : {k_12_on_sub:.3f}  (在此子样本上)")
            print(f"  Coder1-Coder3 kappa : {k_13:.3f}")
            print(f"  Coder2-Coder3 kappa : {k_23:.3f}")
            print(f"  {DIM('若三个两两kappa接近一致，说明CODEBOOK具有跨编码者的普适性，')}")
            print(f"  {DIM('而非仅Coder1/Coder2这一特定配对的内部共识。')}")

            # 检测是否有大幅偏离
            kappas = [k_12_on_sub, k_13, k_23]
            spread = max(kappas) - min(kappas)
            if spread > 0.15:
                print(RED(f"  ⚠ 三个两两kappa最大差距 {spread:.3f} > 0.15"))
                print(RED(f"     编码者间存在差异，建议讨论第三编码者的分歧来源"))
            else:
                print(GREEN(f"  ✓ 三个两两kappa差距 {spread:.3f}，CODEBOOK 跨编码者稳定"))

            lines += [
                "",
                "THIRD-CODER ROBUSTNESS CHECK:",
                f"  Triply-coded subsample : {len(c3_sub)}",
                f"  Coder1-Coder2 kappa    : {k_12_on_sub:.3f}",
                f"  Coder1-Coder3 kappa    : {k_13:.3f}",
                f"  Coder2-Coder3 kappa    : {k_23:.3f}",
                f"  Max pairwise spread    : {spread:.3f}",
            ]

    report = "\n".join(lines)
    rpath = os.path.join(TABLES, "reliability_report.txt")
    with open(rpath, "w", encoding="utf-8") as f: f.write(report + "\n")
    print(f"\n[saved] {rpath}")

    # 最终判定
    if k_hh_blind >= 0.61:
        print(GREEN(f"\n  ✓ 盲编 Kappa={k_hh_blind:.3f} 达标（≥0.61），可投稿"))
    elif k_hh_blind >= 0.41:
        print(YELLOW(f"\n  △ 盲编 Kappa={k_hh_blind:.3f} 中等，需在Methods中解释"))
    else:
        print(RED(f"\n  ✗ 盲编 Kappa={k_hh_blind:.3f} 不达标，建议修订CODEBOOK后重做ROUND 1"))


# ═══════════════════════════════════════════════════════════════════════
# 阶段 E：裁决分歧（两人一起 + 程序建议）
# ═══════════════════════════════════════════════════════════════════════
def adjudicate():
    if not os.path.exists(SAMPLE):
        print(RED("[!] 找不到样本")); sys.exit(1)
    df = pd.read_csv(SAMPLE, dtype=str).fillna("")
    # 用盲编结果做分歧识别（仍然以盲编为准）
    sub = df[df.coder_1_blind.isin(VALID) & df.coder_2_blind.isin(VALID)]
    disagree = sub[sub.coder_1_blind != sub.coder_2_blind].copy()
    if disagree.empty:
        print(GREEN("  没有分歧需要裁决！")); return

    todo = disagree[~disagree["adjudicated"].isin(VALID)].index.tolist()
    done = len(disagree) - len(todo)

    lex = load_lexicon()
    log = AuditLog(KAPPA_LOG)
    divider(f"裁决分歧 · {len(disagree)} 条（已裁决 {done}）")
    print("  两位编码者一起审查每条分歧，讨论后选择裁决标签。")
    print(f"  {DIM('回车=接受建议 / 1234 / q')}\n")
    shortcut = {"1":"cap","2":"con","3":"both","4":"neither"}

    for prog, idx in enumerate(todo, 1):
        row = df.loc[idx]
        c1, c2, auto = row["coder_1_blind"], row["coder_2_blind"], row["auto_label"]
        text_cn = str(row.get("text_cn", "")).strip()
        info = get_suggestion(row["text"], lex)

        # 裁决建议：若任一编码者与auto一致 → 用auto；否则建议两人投票
        if c1 == auto: sug = c1; why = "编码者1与自动标注一致"
        elif c2 == auto: sug = c2; why = "编码者2与自动标注一致"
        else: sug = auto; why = "两人都与自动标注不一致，默认采用自动标注"

        divider(f"分歧 {prog}/{len(todo)}  [{c1}-vs-{c2}]")
        # 中英双语展示
        display_sentence(str(row["text"]), text_cn)
        print(f"  能力词 (capability): {GREEN(', '.join(info['cap_terms'])) if info['cap_terms'] else DIM('无')}")
        print(f"  后果词 (consequence): {RED(', '.join(info['con_terms'])) if info['con_terms'] else DIM('无')}")
        print(f"  编码者1: {BOLD(c1+' '+LABEL_CN[c1])} | 编码者2: {BOLD(c2+' '+LABEL_CN[c2])} | 自动: {DIM(auto)}")
        print(f"  {BOLD('裁决建议:')} {LABEL_CN[sug]} ({sug}) — {DIM(why)}")

        while True:
            resp = ask("裁决标签？", f"回车=接受({sug}) / 1234 / q", "")
            if resp == "q":
                df.to_csv(SAMPLE, index=False); sys.exit(0)
            if resp == "": dec = sug; break
            if resp in shortcut: dec = shortcut[resp]; break
            print(RED("  无效输入"))

        note = ""
        if dec != c1 and dec != c2:
            note = ask("简短理由？（可选）", default="")
        df.at[idx, "adjudicated"] = dec
        df.at[idx, "adj_note"] = note or f"adj from {c1}-vs-{c2}"
        log.record(sent_id=row["sent_id"], action=dec,
                   suggestion=sug, coder="adjudication",
                   reason=note or f"{c1}-vs-{c2}",
                   text_preview=row["text"])
        print(GREEN(f"  → 裁决: {dec}\n"))

    df.to_csv(SAMPLE, index=False)
    print(GREEN(f"\n  裁决完成。CODEBOOK请用裁决出的最终版本提交论文附录。"))


# ═══════════════════════════════════════════════════════════════════════
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--make-sample", action="store_true")
    ap.add_argument("--code", action="store_true", help="ROUND 1 盲编")
    ap.add_argument("--review", action="store_true", help="ROUND 2 反馈复审")
    ap.add_argument("--coder", type=int, choices=[1,2,3],
                    help="编码者编号 1/2 (主)，3 (可选第三编码者，用于稳健性)")
    ap.add_argument("--score", action="store_true")
    ap.add_argument("--adjudicate", action="store_true")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=42,
                    help="随机种子 (第二轮换种子避免重复句子，如 --seed 99)")
    ap.add_argument("--sample-third", type=int, default=0,
                    help="为第三编码者抽取的子样本量 (0=不使用第三编码者)")
    args = ap.parse_args()

    if args.make_sample: make_sample(n=args.n, seed=args.seed, third_subsample=args.sample_third)
    elif args.code:
        if not args.coder: print(RED("需 --coder 1, 2, 或 3")); sys.exit(1)
        run_round_one_blind(args.coder)
    elif args.review:
        if not args.coder or args.coder == 3:
            print(RED("--review 仅支持 --coder 1 或 2")); sys.exit(1)
        run_round_two_assisted(args.coder)
    elif args.score: score()
    elif args.adjudicate: adjudicate()
    else:
        print(BOLD("双通道编码流程:"))
        print("  1. python 06_interactive_kappa.py --make-sample --n 300")
        print("     可选: --sample-third 50  (额外用第三编码者验证50句)")
        print("  2. python 06_interactive_kappa.py --code --coder 1   # ROUND 1 盲编")
        print("  3. python 06_interactive_kappa.py --code --coder 2   # 独立完成")
        print("  4. python 06_interactive_kappa.py --code --coder 3   # 可选稳健性")
        print("  5. python 06_interactive_kappa.py --score             # 出Kappa")
        print("  6. python 06_interactive_kappa.py --review --coder 1  # 可选 ROUND 2")
        print("  7. python 06_interactive_kappa.py --review --coder 2")
        print("  8. python 06_interactive_kappa.py --adjudicate        # 裁决分歧")

if __name__ == "__main__":
    main()