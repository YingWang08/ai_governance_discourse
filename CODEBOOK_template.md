# Coding Manual (Codebook) — Capability vs Consequence Framing
# 编码手册 — 能力 vs 后果框架

> **Purpose / 目的.** This codebook governs the human double-coding used to
> validate the automatic lexicon labels (Methods §3.2). The *finalised*
> version goes in the paper's appendix. Inter-coder reliability (Cohen's
> kappa) is only credible if the coders worked from a written manual — this is it.
>
> 本手册指导人工双盲编码以验证自动词典标注。最终版放入论文附录。
>
> **How to use / 使用方式.** Two coders read this manual together once, code
> the sample sheet independently, then run `--score`.
>
> 两位编码者先一起读完本手册，再各自独立编码，最后运行 `--score` 计算 Kappa。

---

## 1. Unit of analysis / 分析单元

The **sentence**, as segmented by the pipeline. Code the sentence on its
own terms; do not import context from neighbouring sentences unless the
sentence is grammatically incomplete on its own (rare; flag these).

以流水线分割的**句子**为单位。就句子本身编码，不引入上下文（除非句子本身语法不完整，标记之）。

---

## 2. The two frames / 两个框架

### Capability frame (`cap`) / 能力框架

The sentence foregrounds AI's **productive power, promise, or
advancement** — what AI can do, enable, accelerate, or deliver.

句子重心在 AI 的**生产力、前景或进步**——AI 能做什么、促成什么、加速什么。

*Indicative content / 典型内容:* innovation, competitiveness,
economic growth, productivity, deployment, adoption, efficiency,
investment, scientific progress, opportunity, technological leadership.

*Examples / 示例:*

| 句子 | 标签 | 理由 |
|------|------|------|
| "AI offers considerable benefits in healthcare and productivity." | **cap** | 核心论述 AI 的益处 |
| "States should promote AI research and development." | **cap** | 推动 AI 能力建设 |
| "AI can enhance efficiency in public services." | **cap** | 强调 AI 带来的效率提升 |

---

### Consequence frame (`con`) / 后果框架

The sentence foregrounds the **risks, harms, duties, or protective
measures** associated with AI — what AI does to people/society and what
must be done about it.

句子重心在 AI 相关的**风险、危害、义务或保护措施**——AI 对人/社会的影响及应对。

*Indicative content / 典型内容:* safety, risk, harm, accountability, human oversight,
fundamental/human rights, transparency obligations, responsibility,
liability, bias, discrimination, misuse, mitigation, redress.

*Examples / 示例:*

| 句子 | 标签 | 理由 |
|------|------|------|
| "Providers shall ensure human oversight to minimise risks to fundamental rights." | **con** | 核心是"降低对基本权利的风险" |
| "AI systems may cause harm through biased decisions." | **con** | 核心论述 AI 的危害 |
| "Effective redress mechanisms must be available to affected persons." | **con** | 核心是受影响者的权利保护 |

---

### Both (`both`) / 兼有

The sentence gives **substantive weight to BOTH** frames — not a passing
mention of one. The classic governance sentence balancing promise and
protection.

句子对两个框架都给予**实质性权重**——不是一笔带过，而是并重。

*Examples / 示例:*

| 句子 | 标签 | 理由 |
|------|------|------|
| "Foster innovation while ensuring safety and fundamental rights." | **both** | 创新(cap) + 安全与权利(con) 并重 |
| "Harness AI's potential while mitigating risks to society." | **both** | 潜力(cap) + 风险缓解(con) 并重 |

---

### Neither (`neither`) / 均无

Procedural, definitional, scoping, or administrative sentences with no
substantive capability or consequence content.

程序性、定义性、范围界定或行政性句子，没有实质性的能力或后果立场。

*Examples / 示例:*

| 句子 | 标签 | 理由 |
|------|------|------|
| "This Regulation shall apply from 2 August 2026." | **neither** | 纯程序性生效日期 |
| "'Provider' means a natural or legal person that develops an AI system." | **neither** | 纯定义 |
| "The Commission shall adopt implementing acts." | **neither** | 行政程序 |
| "Providers shall register high-risk systems in the EU database before placing them on the market." | **neither** | 行政操作（登记备案），无实质性风险/危害/权利主张 |
| "The provider shall draw up the technical documentation." | **neither** | 行政操作（编写文件） |

---

## 3. Decision rules / 判决规则

### Rule 1 — Dominant emphasis wins / 主导优先
If one frame is clearly primary and the other is a glancing mention,
code the dominant one — not `both`.

一方明显主导、另一方仅一笔带过 → 选主导框架，不选 `both`。

### Rule 2 — `both` requires genuine balance / `both` 需真正并重
`both` is for genuine balance, not for any sentence that happens to
contain one word from each list.

`both` 要求两个框架都有实质性权重，不是"碰巧各含一个词"。

### Rule 3 — Boundary terms don't count / 边界词不计入
*trustworthy, ethical, governance, trust, compliance, standard* are NOT,
by themselves, evidence of either frame. Code on the rest of the sentence.

边界词不单独构成编码依据，看句子其余部分。

---

### ★ Rule 4 — The "shall" rule: SUBSTANCE, not verb / "shall" 规则：看实质，不看动词

**This is the most important rule. 80% of round-1 disagreements came from this boundary.**

**这是最重要的规则。第一轮 80% 的分歧来自这个边界。**

The verb *shall / must / require* does NOT automatically make a sentence `con`.
Ask: **"What is the sentence ABOUT?"** — not what verb it uses.

动词 shall/must/require **不自动**构成 `con`。要问：**"这个句子在讲什么？"**——不是看它用什么动词。

#### Test: The "about-what" test / 检验法："关于什么"检验

Read the sentence and ask: is it **about** any of these substantive consequence topics?
读句子后问：它是否**实质性地关于**以下后果主题？

- 风险 / 危害 / 安全 (risk, harm, safety)
- 人权 / 基本权利 (human rights, fundamental rights)
- 歧视 / 偏见 (discrimination, bias)
- 监督 / 问责 / 救济 (oversight, accountability, redress)
- 透明度与可解释性的**实质性理由** (transparency **for protection**, not just "submit a form")

**YES → `con`** / **NO → `neither`**

#### Worked examples / 判例练习

| 句子 | 标签 | 推理 |
|------|------|------|
| "Providers **shall** ensure human oversight to minimise **risks** to **fundamental rights**." | **con** | About: 风险 + 基本权利 → 实质性后果 |
| "Providers **shall** draw up the technical documentation referred to in Annex IV." | **neither** | About: 编写文件 → 行政操作，无风险/权利/危害 |
| "Providers **shall** register the system in the EU database." | **neither** | About: 登记备案 → 行政程序 |
| "Member States **shall** designate a national competent authority." | **neither** | About: 指定主管机关 → 行政安排 |
| "Providers **shall** implement a quality management system." | **neither** | About: 建立管理体系 → 组织操作 |
| "Providers **shall** take corrective action to address **non-compliance** that poses a **risk** to health or safety." | **con** | About: 纠正不合规 + 风险 → 实质性后果 |
| "The AI system **shall** not be placed on the market if it presents a **risk** to safety." | **con** | About: 安全风险 → 实质性后果 |
| "This Regulation **shall** apply from 2 August 2026." | **neither** | About: 生效日期 → 纯程序 |
| "Deployers **shall** monitor the operation of the high-risk AI system on the basis of the instructions for use." | **neither** | About: 按说明书监测运行 → 操作性要求 |
| "Deployers **shall** inform workers that they will be subject to **AI oversight**." | **con** | About: 告知受 AI 监督 → 涉及权利/监控 |
| "**Obligations** of providers of high-risk AI systems." | **neither** | 这是标题/目录项，无实质性内容 |
| "Providers **shall** ensure AI systems allow for effective **human oversight** to prevent or minimise **risks** to health, safety or **fundamental rights**." | **con** | About: 人工监督 + 风险 + 基本权利 → 核心后果语言 |

#### Quick shortcut / 快速捷径

If in doubt, try mentally **removing "shall"** and rephrasing:
如有疑问，心里把 "shall" 去掉，改写成陈述句：

- "Providers **draw up** technical documentation." → 有人会说这是"后果框架"吗？→ No → **neither**
- "Providers **ensure** oversight to minimise **risks**." → 有人会说这是"后果框架"吗？→ Yes → **con**

---

### Rule 5 — Modality matters / 情态语气有关
"AI could cause harm" (raising a risk) is `con` even though it mentions
a negative capability.

"AI 可能造成危害"（提出风险）是 `con`。

### Rule 6 — Definitions of risky things / 风险事物的定义
"'High-risk system' means …" is `neither` unless the sentence also
asserts a duty or a harm.

"'高风险系统'指……" 是 `neither`，除非句子同时主张了义务或危害。

### Rule 7 — When genuinely torn / 真正拿不定时
When genuinely torn between a frame and `neither`, prefer the frame
only if a naive reader would say the sentence is *about* capability or
consequence. If a naive reader would say "this is about paperwork /
procedures / dates", it is `neither`.

真正犹豫时，只有在普通读者会说"这句话是关于能力/后果"时才选框架。如果普通读者会说"这是关于行政手续/程序/日期"，则选 `neither`。

---

## 4. Calibration exercise / 校准练习

**Before coding independently**, both coders should sit together and
code 10 practice sentences aloud, applying Rule 4 explicitly. This is
NOT part of the scored sample — it is calibration only.

**独立编码前**，两人应坐在一起，对 10 句练习句子出声编码，明确应用规则 4。
这不计入计分样本——仅作校准。

Procedure:
1. Read the sentence aloud
2. Each coder says their label and one-sentence justification
3. If labels differ, discuss and agree which rule applies
4. Move to next sentence

---

## 5. Disagreement handling / 分歧处理

- Code independently first; compute kappa on the raw, pre-discussion labels
  (this is the number you report).
- Then meet, review every disagreement, and record the **type** of each
  disagreement (e.g. cap-vs-both, con-vs-neither) in a short table.
- Agree an adjudicated label for each, and note any decision rule that the
  disagreement prompted you to add above. Adding rules *after* seeing
  disagreements is normal and should be disclosed.

先独立编码，用原始标签算 Kappa（这是论文报告值）。然后一起审查分歧，
记录分歧类型，裁决最终标签，补充规则。赛后补充规则是正常做法，应在论文中披露。

---

## 6. Sampling note / 抽样说明

State the sample size, seed, kappa (human-human), bootstrap 95% CI,
and human-vs-automatic agreement, with the Landis & Koch interpretation band.

报告样本量、随机种子、人-人 Kappa、bootstrap 95% CI、人-自动一致性及 Landis & Koch 解释等级。

If an iterative process was used (pilot round → codebook revision → final round),
disclose both rounds and report the final round's kappa as the primary result:

如果使用了迭代过程（试编轮→CODEBOOK修订→正式轮），须披露两轮并以最终轮 Kappa 为主结果：

> "An initial pilot round (n = 300, seed = 42) revealed systematic disagreement
> at the consequence/neither boundary (κ = 0.12), attributable to ambiguous
> codebook guidance on obligatory-but-procedural language. Following codebook
> revision — specifically, the addition of the 'about-what' test for sentences
> containing *shall* (Rule 4) — and a joint calibration exercise, a second
> reliability round on a fresh sample (n = 100, seed = 99) yielded κ = X.XX
> (95% CI [X.XX, X.XX]), confirming adequate agreement. This iterative
> calibration process is standard practice in computational content analysis
> (Krippendorff, 2004; Neuendorf, 2017)."

---

*Fill in your own additional examples under each frame as you encounter
them during coding — real examples from your corpus make the appendix
far more convincing than invented ones.*
