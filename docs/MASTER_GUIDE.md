# 完整实验与写作指南
## 全球AI治理话语2019-2026：经京特·安德斯视角的计算文本分析

> **投稿目标：** MDPI *Information*（常规投稿）  
> **作者署名：** 第一作者（马原博士，需满足毕业要求） + 第二作者（计算机硕士）  
> **预计时间：** 准备1天 + 清洗1天 + 分析0.5天 + 双重编码1天 + 写作2-4周 + 审稿2-4月

---

# 目录

- [第一部分：项目准备（Part A）](#第一部分项目准备)
- [第二部分：实验执行（Part B）](#第二部分实验执行)
- [第三部分：论文写作（Part C）](#第三部分论文写作)
- [第四部分：投稿与审稿（Part D）](#第四部分投稿与审稿)
- [附录A：故障排除](#附录a故障排除)
- [附录B：论文素材即取即用](#附录b论文素材即取即用)

---

# 第一部分：项目准备

## A1. 环境与目录搭建（30分钟）

### A1.1 创建项目目录

在你打算放项目的位置：

```bash
mkdir AI_governance_paper
cd AI_governance_paper
mkdir -p data/raw data/processed
mkdir -p output/tables output/figures
mkdir -p config src docs
```

最终结构应该是：
```
AI_governance_paper/
├── config/                  # 配置文件
├── data/
│   ├── raw/                 # 原始PDF/TXT（11份文件）
│   └── processed/           # 清洗后的中间数据
├── output/
│   ├── tables/              # 所有CSV结果表
│   └── figures/             # 所有PNG图片
├── src/                     # Python脚本
└── docs/                    # 文档
```

### A1.2 放置脚本和配置

把交付包中的文件放到对应位置：

| 文件 | 目标位置 |
|------|---------|
| `utils_audit.py` | `src/utils_audit.py` |
| `00_interactive_cleaning.py` | `src/00_interactive_cleaning.py` |
| `02_expand_lexicon.py`（原版） | `src/02_expand_lexicon.py` |
| `03_frame_coding.py`（修复版） | `src/03_frame_coding.py` |
| `04_cooccurrence_network.py`（原版） | `src/04_cooccurrence_network.py` |
| `05_temporal_analysis.py`（修复版） | `src/05_temporal_analysis.py` |
| `06_interactive_kappa.py`（v2加固版） | `src/06_interactive_kappa.py` |
| `07_robustness.py`（修复版） | `src/07_robustness.py` |
| `lexicon.yaml`（原版） | `config/lexicon.yaml` |
| `corpus_manifest.yaml`（修复版） | `config/corpus_manifest.yaml` |
| `CODEBOOK_template.md`（原版） | 项目根目录 |
| `requirements.txt` | 项目根目录 |

### A1.3 安装Python环境

```bash
# 创建虚拟环境
python -m venv .venv

# 激活（Windows）
.venv\Scripts\activate
# 激活（macOS/Linux）
source .venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install scikit-learn   # 用于Cohen's kappa
```

### A1.4 预下载NLTK分词器

```bash
python -c "import nltk; nltk.download('punkt'); nltk.download('punkt_tab')"
```

如果国内网络下载失败：
```bash
# 设置代理或下载离线包
python -c "import nltk; nltk.set_proxy('http://your.proxy:port'); nltk.download('punkt')"
```

### A1.5 验证基础设施

```bash
python src/utils_audit.py
```

期望输出：
```
✓ AuditLog 测试通过
  最新决策: {'s001': 'drop'}
  修订次数: {'s001': 2}
```

如果失败，检查Python版本（需要3.9+）。

---

## A2. 下载11份原始文件（30分钟，最费时）

### A2.1 在 `corpus_manifest.yaml` 中列出的文件

| ID | 文件名 | 大小预估 | 关键提醒 |
|----|--------|---------|---------|
| oecd_2019 | oecd_2019.pdf | ~500KB | ⚠ 必须找2019原版，不是2024更新版 |
| g20_2019 | g20_2019.pdf | ~200KB | 日本外务省直链 |
| unesco_2021 | unesco_2021.pdf | ~2MB | UNESCO官方 |
| eu_aiact_proposal_2021 | eu_aiact_proposal_2021.pdf | ~5MB | EUR-Lex需接受cookies |
| nist_rmf_2023 | nist_rmf_2023.pdf | ~3MB | NIST直链 |
| g7_hiroshima_2023 | g7_hiroshima_2023.txt | ~50KB | ⚠ 只有HTML，需手存为txt |
| us_eo_14110_2023 | us_eo_14110_2023.pdf | ~3MB | 联邦公报 |
| oecd_2024 | oecd_2024.pdf | ~500KB | ⚠ 必须与2019不同 |
| eu_aiact_final_2024 | eu_aiact_final_2024.pdf | ~15MB | ⚠ 最大，~458页 |
| coe_convention_2024 | coe_convention_2024.pdf | ~1MB | 欧委会（非欧盟） |
| eu_gpai_code_2025 | eu_gpai_code_2025.pdf | ~2MB | 取最新Final版 |

### A2.2 OECD 2019 vs 2024 的特殊处理

这是整个项目最容易出问题的地方。**两份文件用同一个URL**，但内容应该不同。

**正确做法：**

1. **下载 oecd_2024.pdf**：直接访问 https://legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449 ，下载当前PDF
2. **下载 oecd_2019.pdf**：
   - 访问 https://web.archive.org
   - 在搜索框输入：`legalinstruments.oecd.org/en/instruments/OECD-LEGAL-0449`
   - 在日历视图选择 2020-2023 间的任一日期（不要选2024之后）
   - 在该快照页面找到PDF下载链接，下载并重命名为 `oecd_2019.pdf`
3. **核查**：用 PDF 阅读器分别打开两份，搜索"2024"。oecd_2019.pdf 不应包含 2024 年的修订标记。

### A2.3 G7 Hiroshima 的特殊处理

它没有独立PDF，是HTML网页：

1. 浏览器打开 https://digital-strategy.ec.europa.eu/en/library/hiroshima-process-international-guiding-principles-advanced-ai-system
2. 找到正文部分（"International Guiding Principles..."的标题之后）
3. 全选正文（不要复制页眉/页脚/菜单），复制
4. 打开记事本，粘贴
5. 另存为 `data/raw/g7_hiroshima_2023.txt`，编码选择 **UTF-8**

### A2.4 EU AI Act Final 2024 下载技巧

文件很大（~15MB），可能下载失败：

- 直链：https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689
- 如果点击后没有下载，等30秒，浏览器会跳到PDF查看器
- 用浏览器的"另存为"保存
- 如果反复失败，用迅雷/IDM等下载工具

### A2.5 验证下载

```bash
ls -lh data/raw/
```

应该看到11个文件，每个大小都符合预估。如果某个文件 < 50KB，肯定下载失败（可能是HTML错误页）。

---

# 第二部分：实验执行

## B1. 第一阶段：文本清洗（半天）

### B1.1 启动交互式清洗

```bash
python src/00_auto_cleaning.py
```

### B1.2 程序会自动做的事

1. 计算所有文件的 SHA-256 指纹 → `output/tables/corpus_fingerprints.csv`
2. 提取PDF/TXT文本
3. 用正则规则去除页码、条款号、目录残留等明显噪音
4. 句子分割（NLTK Punkt）
5. 对每个句子三级分类：
   - **ok**（≥10词+有终止标点）→ 自动保留
   - **noise**（纯数字/全大写标题/<3词）→ 自动丢弃
   - **suspect**（灰色地带）→ 暂停问你

### B1.3 程序会问你的事

#### 🔴 暂停1：文档健康检查

每份文档处理完后会展示前15句预览：

```
── 文档 5/11：nist_rmf_2023  (2023) ─────────────
  提取 487 句: 正常=412  噪音=58  需确认=17
  
  前15句预览:
   1. The NIST AI Risk Management Framework provides...
   2. This document offers guidance on how...
   3. L 206/1 [自动丢弃: EU官报水印]
   ...
   
  >>> 文档整体质量？ [g=继续 / r=需重新处理 / s=跳过] (默认=g):
```

**如何决定：**
- 大多数情况按回车（默认 `g`）即可
- 如果看到大量乱码、表格碎片混入正文、英文单词被切碎，输入 `r`，然后：
  - 退出脚本
  - 手动整理该PDF的文本（用Word复制粘贴重新整理）
  - 保存为 `data/raw/<id>.txt`（覆盖原PDF的处理）
  - 重新运行脚本

#### 🔴 暂停2：每条可疑句的决定

```
[3/17] 仅4词
  AI must be safe.
  程序建议: 保留 (信心 70%) — 虽短但有终止标点，可能是正常短句
>>> 决定？ [回车=接受(保留) / k=保留 / d=丢弃 / K=剩余全保留 / D=剩余全丢弃] (默认=):
```

**如何决定：**
- 句子有完整意义 → 保留（回车或 `k`）
- 看起来是标题/碎片 → 丢弃（`d`）
- 后面句子大多类似 → `K` 或 `D` 批量处理（慎用）

#### 🔴 暂停3：最终确认

所有文档处理完后会展示统计：

```
═══ 最终统计 ═══
  文档数: 11
  保留句子: 8,234
  丢弃句子: 1,567
  总词元: 245,891
  按年份: ...
  
>>> 确认保存？ [Y/n] (默认=Y):
```

回车确认保存。

### B1.4 完成后的文件

```
data/processed/
├── sentences.csv              ← 最终保留的句子
├── sentences.parquet
└── dropped_sentences.csv      ← 丢弃的句子（审计用）

output/tables/
├── cleaning_decisions.csv     ← append-only决策日志（关键证据）
├── corpus_fingerprints.csv    ← 文件指纹（版本证明）
└── cleaning_methods_paragraph.txt  ← 论文Methods草稿
```

### B1.5 关键数字记下来

终端会打印：
```
  文档数: 11
  保留句子数: ____
  丢弃句子数: ____
  总词元数: ____
  人工推翻率: ____%
```

把这四个数字记下来，会写进论文Methods §3.1。

### B1.6 第二次运行（如有需要）

如果你重新下载了某个PDF：
```bash
python src/00_auto_cleaning.py --replay
```

- 已记录的决策自动复用
- 新增的句子（之前没问过的）会单独询问

---

## B2. 第二阶段：词典定型（5分钟）

```bash
python src/02_expand_lexicon.py --method none
```

输出 `config/lexicon_expanded.yaml`。这一步只是把种子词规范化，不做机器扩展。

**🔴 不要用 `--method sbert`**。机器扩展会引入争议，让审稿人怀疑词典是"被优化过的"，反而失分。

---

## B3. 第三阶段：自动框架编码（2分钟）

```bash
python src/03_frame_coding.py
```

终端输出：
```
===== 框架分布 =====
neither       3245
capability    2156
consequence   2433
both          400

===== 按年份显著度 =====
 year  n_sentences  capability_share  consequence_share  net_consequence
 2019         812            0.5234            0.4234          -0.1000
 ...
```

记下这些数字。

输出文件：
- `data/processed/coded_sentences.csv`
- `output/tables/salience_by_year.csv`
- `output/tables/salience_by_document.csv`
- `output/tables/salience_by_body.csv`

---

## B4. 第四阶段：生成图表（3分钟）

### B4.1 共现网络图

```bash
python src/04_cooccurrence_network.py
```

输出 `output/figures/cooccurrence_network.png` + `output/tables/network_centrality.csv`。

### B4.2 时间趋势图（核心图）

```bash
python src/05_temporal_analysis.py
```

输出：
- `output/figures/temporal_salience.png` ← **论文主图**
- `output/figures/temporal_salience_doc_weighted.png` ← 文档加权对比图
- `output/figures/net_consequence_trend.png`
- `output/tables/temporal_crosscorr.csv`

### B4.3 稳健性检验

```bash
python src/07_robustness.py
```

输出5张稳健性表：
- `robustness_lexicon.csv`（去掉最频繁词）
- `robustness_leave_one_out.csv`（留一文档）
- `robustness_periods.csv`（粗粒度时段）
- `robustness_polysemy.csv`（多义词扰动）
- `robustness_doc_weighted.csv`（文档加权）

### B4.4 内化"四个数"

在开始编码或写作前，背出这四个数：

1. 最早年份（2019）的 `capability_share` ≈ ____
2. 最晚年份的 `consequence_share` ≈ ____
3. 两条线的交叉年份 ≈ ____
4. 交叉相关峰值的lag ≈ ____

**记不住这四个数，不要写论文。**

---

## B5. 第五阶段：人工双重编码 + Kappa（1天，最关键的方法论步骤）

### B5.1 准备工作（30分钟）

**你（博士）和合作者（硕士）一起**做：

1. 找一个无干扰的环境（咖啡厅、会议室）
2. 两人各自打开 `CODEBOOK_template.md`
3. 逐条读规则，讨论每个例子
4. 确保两人对"both"边界的理解一致
5. **从这一步之后到完成编码前，禁止再讨论具体句子**

### B5.2 抽取300句样本

```bash
python src/06_interactive_kappa.py --make-sample --n 300
```

**🟢 如果想做"黄金方案"（推荐）**：

```bash
# 同时为第三编码者标记50句子样本
python src/06_interactive_kappa.py --make-sample --n 300 --sample-third 50
```

需要找一位独立的第三编码者（建议：同实验室博士生 / 你的导师 / 国外合作者）只编码这50句。

输出 `output/tables/coding_sample.csv`。

### B5.3 ROUND 1 盲编（关键步骤）

#### B5.3.1 编码者1（博士）独立完成

**在你自己的电脑上**：
```bash
python src/06_interactive_kappa.py --code --coder 1
```

首次运行会显示编码规则提醒，确认已读后开始。

每句话长这样：
```
═══ 42/300  [eu_aiact_final_2024, 2024] ═══════════════════

  Providers shall ensure human oversight to minimise risks 
  to fundamental rights.

>>> 你的编码？ [1=cap 2=con 3=both 4=neither / q / ?]:
```

**关键设计：完全没有任何建议、词典提示、对方编码。** 这是为了保证盲编独立性。

- 输入 `1/2/3/4` 选择标签
- 输入 `q` 暂停（下次自动从断点继续）
- 输入 `?` 复习编码规则
- 每20句自动保存

完成300句大约需要1-2小时。

#### B5.3.2 编码者2（硕士）独立完成

**在另一台电脑、或另一个时间段**：

```bash
# 必须把 coding_sample.csv 拷贝过去
python src/06_interactive_kappa.py --code --coder 2
```

**🔴 严禁两人一起编码、严禁互相讨论某条句子、严禁互看对方答案。**

如果不放心，第二位编码者可以在不同物理空间或不同时间完成。

#### B5.3.3 第三编码者（可选，但推荐）

第三编码者只看50句子样本：
```bash
python src/06_interactive_kappa.py --code --coder 3
```

### B5.4 计算 Kappa

两位（或三位）都完成 ROUND 1 后：

```bash
python src/06_interactive_kappa.py --score
```

终端会展示完整报告：

```
═══ Cohen's Kappa 报告 (论文报告值) ═══
  ★ ROUND 1 (盲编) — 这是论文报告的 Kappa
  样本量              : 300
  
  整体 Kappa (主指标):
    Cohen's kappa     : 0.683  实质性一致 (substantial) ✓
    95% Bootstrap CI  : [0.621, 0.738]  (SE=0.030)
    Krippendorff α    : 0.681  (现代指标)
  
  与自动标注的一致性:
    Coder1-Auto kappa : 0.712   (准确率 0.781)
    Coder2-Auto kappa : 0.695   (准确率 0.764)
  
  逐类别 Kappa (one-vs-rest):
    cap     (能力): 0.758  良好 (n=189)
    con     (后果): 0.733  良好 (n=217)
    both    (兼有): 0.370  ⚠ 偏弱 (n=67)
    neither (均无): 0.712  良好 (n=127)
  
  分歧数: 73 (24.3%)
  分歧类型分布:
    con-vs-both     28
    cap-vs-both     19
    ...
```

**判定**：
- Cohen's kappa ≥ 0.61 + CI下限 > 0.50 → ✓ 通过
- 0.41 ≤ kappa < 0.61 → △ 中等，需在Methods讨论 `both` 的固有模糊性
- < 0.41 → ✗ 不通过，**修订CODEBOOK后重做 ROUND 1**

### B5.5 ROUND 2 反馈复审（可选）

如果想增加方法论亮点：

```bash
python src/06_interactive_kappa.py --review --coder 1
python src/06_interactive_kappa.py --review --coder 2
```

这一轮会展示程序建议+词典理由，编码者**可以**修订自己ROUND 1的答案。修订率作为辅助统计。

### B5.6 裁决分歧

两位编码者**一起**审查所有分歧：

```bash
python src/06_interactive_kappa.py --adjudicate
```

每条分歧句：
- 显示两人各自的标签
- 显示程序的裁决建议（基于词典和谁与auto一致）
- 两人讨论后输入最终裁决

裁决后的最终CODEBOOK放入论文附录A。

### B5.7 关键数字记下来

```
Kappa样本量: 300
盲编 Cohen's kappa: ____
95% CI: [____, ____]
Krippendorff alpha: ____
逐类别 kappa: cap=____ con=____ both=____ neither=____
分歧数: ____
```

---

## B6. 实验执行检查清单

完成上述所有步骤后，逐项打钩：

```
准备阶段
☐ 11份PDF/TXT文件已下载到 data/raw/
☐ OECD 2019 和 2024 内容确认不同
☐ G7 Hiroshima 已保存为 .txt
☐ Python环境就绪，依赖已安装

清洗阶段
☐ 00_interactive_cleaning.py 已运行
☐ corpus_fingerprints.csv 已生成
☐ cleaning_decisions.csv 已生成（append-only）
☐ sentences.csv 中句数符合预期

分析阶段
☐ 02_expand_lexicon.py --method none 已运行
☐ 03_frame_coding.py 已运行，按年份显著度表已查看
☐ 04_cooccurrence_network.py 已运行
☐ 05_temporal_analysis.py 已运行，主图已查看
☐ 07_robustness.py 已运行，5张表已查看

Kappa 阶段
☐ 两位编码者共同阅读了 CODEBOOK
☐ ROUND 1 抽样 300 句
☐ 编码者1独立完成 ROUND 1 盲编
☐ 编码者2独立完成 ROUND 1 盲编
☐ 计算 Cohen's kappa ≥ 0.61
☐ Bootstrap 95% CI 计算完成
☐ 逐类别 kappa 计算完成
☐ 分歧裁决完成
☐ 最终 CODEBOOK 准备好放入附录

可选加固
☐ 第三编码者完成50句子样本
☐ ROUND 2 反馈复审完成
```

所有项打钩后，进入第三部分。

---

# 第三部分：论文写作

## C1. 写作总体策略

### C1.1 期刊定位

**MDPI Information** 是计算机科学领域的中等水平期刊：
- Scopus收录，Q3-Q2
- 关注 information science 跨学科应用
- 审稿周期 2-6 周
- 接受跨学科稿件（计算+人文）
- 文章长度灵活，但建议 8000-10000 词

**审稿人画像**：
- 大概率：NLP/计算社会科学背景
- 小概率：科技哲学/STS背景
- 两类审稿人都要能看懂

### C1.2 写作的根本策略

**经验防御层与理论层必须可分离**。

审稿人逻辑：
- 如果他相信你的经验结果 → 即使不接受安德斯解读，论文也成立
- 如果他不相信安德斯 → 经验部分仍然是合格的话语分析

因此整篇论文要让人感觉：**"即使把第5.2节(安德斯)删掉，这仍然是一篇完整的实证论文。"**

这句话本身就要写进Methods §3.5。

### C1.3 写作顺序（不要按目录顺序写）

```
1. Methods（最熟悉，最先写）
2. Results（图表已就绪）
3. Discussion（含安德斯解读）
4. Related Work（写完前三节才知道要怎么定位自己）
5. Introduction（最后写引言）
6. Conclusion
7. Abstract（最后写）
8. Title（最后再检查一遍）
```

**禁忌：先写引言**。这会让你写一个"未来论文的引言"，最终引言和实际内容对不上，全文会显得拼凑。

---

## C2. MDPI Information 的格式要求

摘要应该是一个单独段落，遵循结构化摘要的风格但不使用标题：1) Background；2) Methods；3) Results；4) Conclusion。

研究文章结构应包括 Abstract, Keywords, Introduction, Materials and Methods, Results, Discussion, Conclusions。

**总体规格**：
- 模板：MDPI Word/LaTeX template（官网下载）
- 参考文献：MDPI numerical style（[1], [2]...）
- 图分辨率：300 dpi，半页缩小后仍清晰
- 摘要：200词以内（推荐150-200）
- 关键词：3-10个

---

## C3. 各章节详细写作指南

### C3.1 标题（Title）

候选：
- "The Shifting Balance of Capability and Consequence in Global AI Governance Discourse, 2019–2026: A Computational Text Analysis through Günther Anders' Lens"

**修订建议**：
1. 副标题里的"安德斯"位置考虑往后挪：
   - 原版：副标题中"通过安德斯之镜"  
   - 备选：副标题为"A Sentence-Level Computational Discourse Analysis"，安德斯只在摘要后半段出现

2. 把哲学家姓氏放进标题有风险——可能让计算背景审稿人觉得"这不是我能审的"，建议保留但放在副标题末端

**最终推荐**：
> "The Shifting Balance of Capability and Consequence in Global AI Governance Discourse (2019–2026): A Sentence-Level Computational Frame Analysis, with a Reading through Günther Anders' Promethean Gap"

### C3.2 摘要（Abstract，200词）

按 MDPI 结构化摘要要求，必须包含 Background / Methods / Results / Conclusion 但不要写出小标题。

模板：

> **[Background]** Global AI governance has produced an increasing body of regulatory and ethical texts since 2019, but the discursive dynamics within these texts remain understudied. We examine how the relative salience of capability-oriented versus consequence-oriented framing has shifted across eleven authoritative AI governance documents issued between 2019 and 2026. **[Methods]** Using a sentence-level dictionary-based frame analysis (n = X,XXX sentences, Y,YYY tokens), validated by two-coder blind labelling of a 300-sentence sample (Cohen's κ = 0.XX, 95% bootstrap CI [0.XX, 0.XX]; Krippendorff's α = 0.XX), we track per-year and per-document distributions of the two framings, examine their semantic co-occurrence structure, and assess the temporal lag between capability and consequence trajectories. Robustness is verified via five checks including lexicon perturbation, leave-one-document-out, and a polysemy-aware re-analysis. **[Results]** We find that capability framing dominates in early documents (2019–2021) while consequence framing becomes increasingly salient in the post-2023 period, with consequence salience adjusting in an asymmetric, delayed manner relative to capability. The substantive direction survives all robustness checks. **[Conclusion]** This temporal asymmetry can be productively read through Günther Anders' notion of the Promethean gap, providing a vocabulary for naming the structural lag between productive capacity and the construction of responsibility frameworks. **The empirical findings stand independently of the theoretical lens.**

**关键句必须保留**：
> "The empirical findings stand independently of the theoretical lens."

这句话是给审稿人的明确信号：可以不接受安德斯但接受经验贡献。

### C3.3 关键词（Keywords）

3-10个，建议：

```
AI governance; frame analysis; computational discourse analysis; 
Cohen's kappa; temporal text analysis; Günther Anders; 
Promethean gap; technology policy; policy discourse
```

### C3.4 第1节：Introduction（1000-1500词）

**目标**：让读者明白做了什么、为什么重要，不涉及方法细节。

**结构（4段）**：

**段1（背景，~300词）**：
AI治理文本爆炸式增长，从2019年OECD原则到2024年EU AI Act。这些文本不仅是政策的载体，也是技术与社会关系的话语建构。但系统的话语分析仍稀少。

**段2（研究空白，~300词）**：
已有文献(citation 1-5)关注单一文档/事件/国家，缺乏跨文档、跨时间的话语动力学分析。特别是，AI能力快速演进与治理回应之间的时间关系尚未被系统量化。

**段3（理论框架的轻引入，~300词）**：
京特·安德斯在《人之过时》中提出"普罗米修斯差距"（Promethean gap），描述人类生产能力与对这种能力进行道德判断能力之间的结构性裂隙。这一概念在近期AI伦理文献中重新引起关注 (citations)。我们**不**用安德斯做假设检验——我们用它作为一个**解释性词汇**，帮助命名我们在数据中观察到的时间不对称。

**段4（贡献+三个RQ，~300词）**：

> Our paper makes three contributions:
> 1. We construct and openly release a sentence-level frame analysis pipeline for AI governance discourse, comprising 11 documents and X,XXX sentences (2019–2026).
> 2. We document an empirically robust temporal asymmetry between capability- and consequence-oriented framings.
> 3. We offer a theoretically informed reading of this asymmetry through Anders' Promethean gap. **The empirical findings (Contributions 1 and 2) stand independently of the theoretical interpretation (Contribution 3).**

> Three research questions guide the analysis:
> - **RQ1**: How is the relative salience of capability- vs consequence-oriented framing distributed across documents and issuing bodies?
> - **RQ2 (main)**: How does this balance shift over time, and is consequence framing's adjustment synchronous with or lagged behind capability framing?
> - **RQ3**: To what extent can this temporal pattern be productively read through Anders' Promethean gap?

### C3.5 第2节：Related Work（600-900词）

**结构（3小节）**：

#### 2.1 Computational discourse analysis of AI policy texts (~300词)

引用：
- Schiff et al. (各种关于AI伦理文本的内容分析)
- Jobin et al. (2019) 的AI ethics guidelines review
- 任何使用 LIWC、词典法、主题模型分析政策文本的研究

#### 2.2 Frame analysis as a method (~250词)

引用：
- Entman (1993) 的框架理论奠基
- Matthes & Kohring (2008) 的框架内容分析方法
- 近期computational frame analysis (e.g., Card et al. 2015 Media Frames Corpus)

#### 2.3 Anders' technology critique in AI ethics literature (~200词)

引用：
- Anders, G. *Die Antiquiertheit des Menschen, Bd. 1* (1956)
- Liessmann (2002) 等关于安德斯的二手文献
- 近期复兴：Müller, Fuchs，以及其他将安德斯应用于AI的论文

**关键句子**：
> "While Anders has received limited engagement in mainstream technology studies, recent works (citations) have re-examined his framework in the context of generative AI, suggesting that its conceptual vocabulary remains productive for naming structural features of contemporary AI development."

### C3.6 第3节：Materials and Methods（1500-2000词，最重要的章节）

#### 3.1 Corpus（~400词）

直接用 `cleaning_methods_paragraph.txt` 的内容稍作扩展。

**关键要素**：
1. **入选标准**（4条，明确列出）：
   - Issued by government, IGO, or official standards body
   - AI governance/regulation/ethics as central topic
   - Published 2019-01-01 to 2026-05-31
   - Official English text or official English translation
   
2. **排除内容**：one sentence acknowledging industry-association statements, NGO reports were considered and excluded

3. **文档清单**：用一个表格列出11份文档（id, body, year, sentences, tokens）

4. **指纹**：明确写明"SHA-256 fingerprints of all source files are recorded in corpus_fingerprints.csv (project repository) for reproducibility"

#### 3.2 Frame coding（~500词，方法论核心）

**子节1：词典构建**
- 两个框架（capability, consequence）+ 边界类别（boundary，excluded from scoring）
- 种子词来自 codebook，可在附录或仓库中查阅
- 不做语义扩展（`--method none`），最大化可复现性

**子节2：自动编码**
- Sentence-level matching using compiled regex with word boundaries
- 标签规则：cap (only capability hits), con (only consequence hits), both, neither

**子节3：人工双重编码 + Kappa**

这是关键。用以下模板（v2加固版）：

> "Inter-coder reliability was assessed on a random sample of 300 sentences (seed = 42, drawn uniformly from all coded sentences) using a dual-pass design. In the blind round (Round 1), two coders independently labelled each sentence as cap, con, both, or neither, following the codebook (Appendix A). During this round, coders saw neither the lexicon-derived automatic label nor each other's labels, ensuring methodological independence. 
> 
> Cohen's kappa on the blind round was **0.XX** (95% bootstrap CI [0.XX, 0.XX], 1000 resamples; Krippendorff's α = 0.XX). Coder-versus-automatic-label kappa was 0.XX and 0.XX for Coder 1 and Coder 2 respectively. 
> 
> Per-category one-vs-rest kappa values are reported in Table X. The both category showed weaker agreement (κ = 0.XX), consistent with the inherent boundary ambiguity acknowledged in §3.5; this is treated transparently rather than smoothed away. 
> 
> In an optional Round 2, coders viewed the lexicon-derived suggestion and reasoning, with the option to revise their Round 1 labels; revision rates of XX% and XX% are reported as descriptive aids. **The blind-round kappa (Round 1) is the primary reliability statistic.**
> 
> Disagreements were adjudicated jointly by the two coders; the adjudicated labels and the disagreement-type distribution are reported in Table Y. The codebook was updated only after Round 1 completion based on adjudication insights, ensuring the reported kappa is not inflated by post-hoc revision."

**🔴 关键防御句子**：
- "blind round" / "ensuring methodological independence"
- "95% bootstrap CI" + "Krippendorff's α"
- "Per-category one-vs-rest kappa"
- "The blind-round kappa is the primary reliability statistic"
- "Codebook updated only after Round 1 completion"

#### 3.3 Analyses（~300词）

三个子节：
1. **Salience computation**: capability_share, consequence_share, net_consequence
2. **Semantic co-occurrence network**: NetworkX, degree and betweenness centrality
3. **Temporal evolution**: yearly trajectories + descriptive cross-correlation at lags 0-2

**关键句**：
> "Given the limited number of observation years (n = 6), cross-correlation values are reported as descriptive, not inferential. We do not claim statistical significance for the observed lag."

#### 3.4 Robustness（~250词）

五个检验（用一个表格列出）：

| Check | What | Outcome |
|-------|------|---------|
| 1 | Lexicon perturbation: drop top-3 frequent terms per frame | Direction stable |
| 2 | Leave-one-document-out (esp. EU AI Act 2024) | Direction stable |
| 3 | Coarse periods (early ≤2021 vs late ≥2023) | Direction stable |
| 4 | Polysemy perturbation: drop risk/scale/potential | Direction stable |
| 5 | Document-weighted re-aggregation | Direction stable |

**关键句**：
> "The substantive direction of our findings survives all five checks."

#### 3.5 Role of theory in the analysis（~150词）

**这是整个Methods最关键的一段，必须独立成段**：

> "We use Anders' Promethean gap concept as an interpretive lens for the temporal pattern we observe (§5.2), not as a hypothesis to be tested. The empirical results stand independently: §4.1-4.4 contain claims about the corpus that can be evaluated without reference to Anders. A reader who does not engage with the theoretical reading in §5.2 can still assess the validity of the empirical contributions in §4. We make this separation explicit because we believe Anders' framework is one productive lens among several (e.g., Habermasian, Beckian, STS readings), not the only available one."

### C3.7 第4节：Results（1200-1800词）

**目标**：描述数字，不解释。解释留给Discussion。

#### 4.1 Distribution across the corpus (~300词)

- 报告 capability_share, consequence_share by issuing body
- 一张小表格 + 一段文字
- 关键点：**每个文档都有非零的capability和consequence**（预防"政府文件天然都是consequence framing"的反对意见）

> "Importantly, capability framing is non-trivially present in every document (minimum capability_share = X.XX in [doc_id]), indicating that the capability/consequence distinction reflects internal discursive competition, not a feature of certain document types."

#### 4.2 Semantic structure (~400词)

- 展示共现网络图（Figure 2）
- 描述高介数中心性的"桥接词"：trustworthy, governance, ethical
- **关键点**：把trustworthy作为"试图通过语言融合来弥合普罗米修斯差距"的话语装置（但不点名安德斯）

> "The term 'trustworthy' occupies a position of high betweenness centrality (X.XX), bridging capability and consequence subgraphs. This bridging position is itself analytically informative: it suggests a discursive strategy of conceptual fusion, attempting to subsume both productive promise and protective obligation under a single legitimating term."

#### 4.3 Temporal evolution (centerpiece) (~500词)

- 展示主图（Figure 3 = temporal_salience.png）
- 描述两条轨迹
- 报告交叉相关（描述性）
- 提到2020和2022的数据空缺（已在图中用灰色带标注）

**关键句**：
> "We emphasise that cross-correlation values are reported descriptively. With only six observation years, formal inferential testing of lag structure is not feasible. The qualitative pattern—consequence framing rising in the latter half of the observation window, lagging the establishment of capability framing—is the empirical finding."

#### 4.4 Robustness (~300词)

- 摘要式报告5个检验，指向附录的完整表格
- 关键句：**所有5个检验都保持了核心方向**

### C3.8 第5节：Discussion（1500-2000词）

#### 5.1 Summary of empirical findings (~400词)

用平白英语总结4.3的发现，并把它**对齐到治理时间线**：

> "The trajectory documented in §4.3 maps onto a recognisable policy timeline:
> - 2019-2021: soft, non-binding consensus documents (OECD, G20, early UNESCO) under capability-oriented framing
> - 2022 Nov: ChatGPT release; public discourse inflection
> - 2023: rapid proliferation of risk-focused frameworks (G7 Hiroshima Process, US EO 14110, NIST RMF)
> - 2024-2025: binding legal instruments (EU AI Act, CoE Convention) with strong consequence framing
> 
> The temporal asymmetry our analysis surfaces is consistent with a sequence in which capability claims precede, and consequence frameworks follow."

#### 5.2 Reading through Anders' Promethean gap (~600词)

**这是论文的理论贡献，必须谨慎写**：

要点：
1. 引用安德斯原始文本（Anders, G. *Die Antiquiertheit des Menschen, Bd. 1*, 1956）
2. 描述普罗米修斯差距的核心概念
3. 论述为什么这个概念能命名我们观察到的时间模式
4. **明确说不是在"证明"差距存在**，只是提供一个解释性词汇

**关键句子**：
> "Our analysis does not 'prove' the existence of the Promethean gap. Rather, we argue that Anders' framework supplies a productive vocabulary for naming a structural feature of contemporary AI governance discourse: that the language of responsibility is constructed behind the language of capacity, rather than alongside it."

> "Other theoretical frameworks—Habermasian public sphere theory, Beck's risk society, STS-influenced governance studies—offer complementary readings of the same empirical pattern. We adopt the Andersian framing because it foregrounds the temporal asymmetry that our data make most visible."

#### 5.3 Limitations (~400词)

诚实列出4个限制：

1. **少时间点**: cross-correlation仅描述性
2. **英文语料**: 其他语言版本可能不同
3. **词典编码**: 多义词扰动已部分缓解但仍是限制
4. **解释性理论**: 安德斯解读是诸多可能解读之一

#### 5.4 Implications (~300词)

简短，紧贴经验结果，不延伸到安德斯：

> "Three implications follow from our findings, independent of the theoretical reading:
> 1. AI governance discourse exhibits internal competition between capability and consequence framings, not a monotonic 'precautionary' stance.
> 2. The semantic centrality of bridging terms like 'trustworthy' suggests these terms function as contested zones rather than settled categories.
> 3. The temporal asymmetry suggests responsibility frameworks should not be assumed to keep pace with capability deployment automatically."

### C3.9 第6节：Conclusion（300-500词）

简短，重述：
1. 经验贡献
2. 理论贡献
3. **明示两者可独立评估**
4. 一句话指向未来工作

模板：
> "We have presented a sentence-level computational frame analysis of global AI governance discourse from 2019 to 2026, documenting a temporal asymmetry between capability- and consequence-oriented framings. We have offered an Andersian reading of this asymmetry through the Promethean gap concept. **The empirical contributions stand independently of the theoretical interpretation, and either may be assessed on its own terms.** Future work could extend this analysis to non-English-language governance documents, to industry self-regulation texts, or to public-facing AI discourse, to test whether the temporal pattern we document is specific to formal governance or generalisable."

---

## C4. 图表规范

### C4.1 图

| 图号 | 内容 | 文件 | 必备元素 |
|------|------|------|---------|
| Fig. 1 | 流水线示意图 | 自制 | 表明11文档 → 句子 → 编码 → 分析 |
| Fig. 2 | 共现网络 | cooccurrence_network.png | 颜色编码、图例、桥接词高亮 |
| Fig. 3 | **核心图**：时间轨迹 | temporal_salience.png | 灰色带标注缺失年份 |
| Fig. 4 | 净后果柱状图 | net_consequence_trend.png | 0线明确 |
| Fig. 5 (附录) | 文档加权对比 | temporal_salience_doc_weighted.png | 稳健性 |

**MDPI图要求**：
- 300 dpi
- 半页缩小后仍清晰
- caption自包含（无需读正文也能懂）
- 颜色对色盲友好（我们的脚本已用蓝/红，符合）

### C4.2 表

| 表号 | 内容 |
|------|------|
| Table 1 | 11份文档元信息（id, body, year, sentences, tokens） |
| Table 2 | 按机构的salience分布 |
| Table 3 | 网络中心性top-10术语 |
| Table 4 | 5个稳健性检验汇总 |
| Table 5 | Kappa报告（整体 + per-category） |
| Appendix A | 完整CODEBOOK |
| Appendix B | 完整词典 |

---

## C5. 引用文献

按 MDPI数值引用风格 [1], [2]...。

**必引文献清单**：

理论：
- Anders, G. *Die Antiquiertheit des Menschen, Band 1*, 1956
- 至少1篇近期安德斯研究（Liessmann, Müller, Fuchs等）

方法：
- Cohen, J. *Educational and Psychological Measurement*, 1960（kappa原始论文）
- Landis & Koch, *Biometrics*, 1977（kappa解读标准）
- Krippendorff (alpha 的教材)
- Entman, *Journal of Communication*, 1993（框架理论）

经验：
- Jobin, Ienca & Vayena, *Nature Machine Intelligence*, 2019（AI伦理guidelines综述）
- Schiff et al.（如有相关）
- Card et al. 2015 Media Frames Corpus

技术工具：
- NLTK, pdfplumber, scikit-learn等的官方引用

总数建议：30-50篇。MDPI Information 不要求特别多。

---

# 第四部分：投稿与审稿

## D1. 投稿包准备清单

### D1.1 必备文件

```
☐ 主稿件（MDPI Word模板）
☐ Cover letter（一页）
☐ Highlights（3-5条，每条<85字符）
☐ Author contributions（CRediT标准）
☐ Data availability statement
☐ Conflict of interest statement
☐ Funding statement（即使无资助也要写）
☐ Suggested reviewers（3-5人）
☐ Supplementary materials（如有）
```

### D1.2 Cover letter模板

```
[Date]

To the Editors of Information,

We submit for your consideration our manuscript "The Shifting Balance 
of Capability and Consequence in Global AI Governance Discourse, 
2019–2026" for publication as a research article.

The paper contributes a computational frame analysis of eleven 
authoritative AI governance documents (2019–2026), documenting a 
temporal asymmetry between capability- and consequence-oriented 
framings, and offering a theoretically informed reading via Anders' 
Promethean gap. The empirical contribution stands independently of 
the theoretical interpretation.

This work fits Information's interdisciplinary scope: it combines 
computational text analysis with critical theory and policy 
analysis, addressing the information-and-society nexus the journal 
foregrounds. Recent issues of Information have published adjacent 
work on [cite 1-2 recent papers].

We confirm: (1) this manuscript has not been published elsewhere 
and is not under consideration by another journal; (2) all authors 
have approved the submission; (3) the research did not involve 
human subjects or personal data, and no ethics approval was 
required; (4) all source documents are publicly available 
governmental and intergovernmental texts; (5) full pipeline 
code and intermediate data are deposited at [Zenodo DOI] under 
an open license.

We have no conflicts of interest to declare.

[Suggested reviewers list — optional]
We respectfully suggest that the following scholars, who have 
not collaborated with us in the past five years, may be 
appropriate reviewers:
- [Name], [Affiliation], [Email] — expertise in computational 
  policy text analysis
- [Name], [Affiliation], [Email] — expertise in AI ethics
- [Name], [Affiliation], [Email] — expertise in technology 
  philosophy / critical theory

Sincerely,
[Corresponding Author Name]
[Affiliation]
[Email]
```

### D1.3 Author contributions

按 CRediT 分类：

```
Conceptualization: [Author 1]
Methodology: [Author 1, Author 2]
Software: [Author 2]
Validation: [Author 1, Author 2]
Formal analysis: [Author 1]
Investigation: [Author 1, Author 2]
Data curation: [Author 2]
Writing—original draft: [Author 1]
Writing—review & editing: [Author 1, Author 2]
Visualization: [Author 2]
Supervision: [Author 1's supervisor if appropriate]
Project administration: [Author 1]

Both authors have read and agreed to the published version of the manuscript.
```

### D1.4 Data Availability Statement

```
All source documents are publicly available from the issuing bodies; 
URLs and SHA-256 fingerprints are provided in corpus_manifest.yaml 
and corpus_fingerprints.csv in the project repository. Processed 
sentence-level data, the lexicon, the codebook, append-only decision 
logs (cleaning_decisions.csv, kappa_decisions.csv), and all analysis 
scripts are openly available at [Zenodo DOI] under [CC-BY 4.0 / MIT] 
license. No personal data were collected; no ethics approval was 
required.
```

### D1.5 代码仓库准备

提交Zenodo前的检查清单：

```
仓库根目录:
☐ README.md（如何复现每个图表）
☐ requirements.txt
☐ CODEBOOK.md（最终版）
☐ LICENSE（CC-BY 4.0 / MIT）
☐ run_all.sh

config/:
☐ corpus_manifest.yaml
☐ lexicon.yaml
☐ lexicon_expanded.yaml

src/:
☐ 所有.py脚本（不含注释掉的代码）

output/tables/:
☐ corpus_fingerprints.csv ← 必须有
☐ cleaning_decisions.csv ← 必须有（append-only）
☐ kappa_decisions.csv ← 必须有（append-only）
☐ reliability_report.txt
☐ 其他salience和robustness表

不提交:
✗ data/raw/ 下的PDF（公开可下载）
✗ .venv/、__pycache__/、.DS_Store
✗ 任何TODO/FIXME注释
```

获取 Zenodo DOI：
1. GitHub仓库 → Settings → Integrations → Zenodo
2. 在Zenodo关联仓库
3. 在GitHub创建一个release（如v1.0）
4. Zenodo自动生成DOI

把这个DOI写进 Data Availability Statement。

---

## D2. 审稿应对策略

### D2.1 时间线预期

| 阶段 | 预期时间 |
|------|---------|
| 初步编辑筛查 | 1-7天 |
| 外审返回 | 2-6周 |
| 第一轮决定 | 通常 minor 或 major revision |
| 修订窗口 | minor 10天 / major 30天 |
| 第二轮决定 | 1-4周 |
| **总时间到接收** | 2-4个月（顺利）/ 6+个月（major revisions） |

### D2.2 预防式应对：常见审稿意见与回应

| 审稿意见 | 你的回应 |
|---------|---------|
| "语料太小" | 单位是句子不是文档，共X,XXX句Y,YYY词；引用稳健性检验 |
| "这就是关键词计数" | 引用 (a) kappa验证 (b) 时间动态分析 (c) 桥接词处理 |
| "词典embeds作者偏见" | 是，所以词典外置、可审计、Kappa验证、扰动测试 |
| "安德斯是边缘人物" | 承认主流接受有限，引用近期复兴文献，强调经验结果独立 |
| "结果被EU AI Act长文档驱动" | 引用 leave-one-document-out + document-weighted稳健性 |
| "为何不用BERTopic/LLM" | 11份文档样本太小；可复现性；透明性；引用词典法在小语料的地位 |
| "都是法律文档，体裁混淆" | 承认+主动选择；within-corpus竞争是设计目的而非缺陷 |
| "lag分析时间点太少" | 同意；明确报告为描述性而非推断性 |
| "两人Kappa不够" | 引用 (a) Cohen kappa本为两人设计 (b) Bootstrap CI (c) Krippendorff alpha (d) per-category breakdown (e) 可选第三编码者 |

### D2.3 收到Major Revisions的处理

1. **读三遍审稿意见，然后冷静24小时再开始回复**
2. **建立回复文档**：每条意见 → 引用原文 → 你的回应 → 修改位置
3. **每条意见都回应**：即使你不同意也要回应，不能沉默
4. **修改用track changes**（MDPI支持），让reviewer看到具体变化
5. **按时提交**（迟交会被当作新投稿）

回复模板：

```
Reviewer 1, Comment 1:
> [完整引用审稿意见]

Response:
We thank the reviewer for this insightful comment. We agree that 
[acknowledgement]. In response, we have [specific action taken], 
which is reflected in the manuscript at [section/line numbers].

Specifically:
- [Change 1 with line reference]
- [Change 2 with line reference]
```

### D2.4 收到Rejection的处理

不要立即重投。先复盘：

1. **方法论问题** → 修复后投同等期刊（不要直接重投 Information）
2. **贡献不明确** → 重写introduction + abstract
3. **范围不匹配** → 考虑下面的备选期刊

**备选期刊清单**（按降序优先）：

| 期刊 | IF/分区 | 适合度 |
|------|---------|--------|
| AI & Society | Q2 | 跨学科，理论友好 |
| Policy & Internet | Q2 | 政策导向 |
| Big Data & Society | Q1 | 批判+计算 |
| Discourse, Context & Media | Q2 | 话语分析 |
| New Media & Society | Q1 | 媒体/社会 |

---

## D3. 最后的检查（投稿前24小时）

```
内容检查:
☐ 标题准确描述论文
☐ 摘要符合MDPI结构化要求且≤200词
☐ Methods §3.5"理论的角色"段落保留
☐ 摘要中"empirical findings stand independently"句子保留
☐ 引言不超过1500词
☐ 总长度8000-10000词
☐ 4个核心数字与图表一致

格式检查:
☐ 使用MDPI Word/LaTeX模板
☐ 引用按MDPI数值风格
☐ 所有图300dpi
☐ 所有图表caption自包含
☐ 关键词3-10个

代码仓库:
☐ Zenodo DOI已获取
☐ README充分描述如何复现
☐ corpus_fingerprints.csv存在
☐ cleaning_decisions.csv存在（append-only格式）
☐ kappa_decisions.csv存在（append-only格式）
☐ 所有审计日志带时间戳
☐ 仓库无TODO/FIXME

法律/伦理:
☐ Data availability statement明确说明无伦理问题
☐ 利益冲突声明
☐ Funding statement（即使"no external funding"）
☐ 所有作者已批准最终版

最关键的自检:
☐ 如果删掉§5.2（安德斯解读），论文仍然是完整的实证研究 ← 必须是Yes
```

如果最后一项是No，回到§3.5重写直到是Yes为止。

---

# 附录A：故障排除

## A1. PDF提取后大量乱码

**症状**：清洗报告里看到 "Th e provider s sh all..." 这种被空格切碎的单词。

**原因**：pdfplumber对某些PDF的字体编码处理不好。

**解决**：
1. 用Adobe Acrobat或Foxit打开PDF → 另存为TXT
2. 把TXT放到 `data/raw/<id>.txt`
3. 删除对应PDF或重命名（避免冲突）
4. 重新运行 `00_interactive_cleaning.py`

## A2. NLTK下载失败

**症状**：`LookupError: Resource punkt not found`

**解决**：
```bash
# 方法1：设置环境变量
export NLTK_DATA=~/nltk_data
python -c "import nltk; nltk.download('punkt', download_dir='~/nltk_data')"

# 方法2：手动下载
# 访问 https://www.nltk.org/nltk_data/
# 下载 punkt.zip，解压到 ~/nltk_data/tokenizers/
```

## A3. Kappa < 0.41

**症状**：盲编后kappa不达标。

**诊断步骤**：
1. 看 per-category kappa，找出哪一类最低
2. 通常是 `both` 类
3. 查看分歧类型分布，看是 con-vs-both 还是 cap-vs-both

**修复**：
1. 重新讨论CODEBOOK的"主导优先"规则
2. 添加3-5条来自实际语料的边界例子
3. 把改进版CODEBOOK保存为新文件
4. 重新抽样（用不同seed）重做ROUND 1
5. 论文中诚实报告"the codebook was revised once after a pilot round of n=300 sentences yielded κ=0.XX, leading to additional decision rules for the both category. Reported κ is from the second round."

## A4. 运行到一半电脑死机

所有交互脚本都是**断点续传**的。重新启动后再运行同一命令，自动从上次进度继续。

## A5. 第三编码者拒绝/无法找到

完全可接受。回到基础方案：仅2人 + bootstrap CI + per-category + Krippendorff alpha。脚本会自动跳过第三编码者部分。

---

# 附录B：论文素材即取即用

## B1. 自动生成的文本素材清单

完成实验后，以下文件包含可直接复制到论文的现成文字：

| 文件 | 用于论文哪部分 |
|------|---------------|
| `output/tables/cleaning_methods_paragraph.txt` | Methods §3.1 |
| `output/tables/reliability_report.txt` | Methods §3.2 + Results §4.x |
| 终端打印的"Methods paragraph (paste into paper §3.2)" | Methods §3.2 |
| 终端打印的"按年份显著度"表 | Results §4.3 |
| 终端打印的5个稳健性表 | Methods §3.4 / Results §4.4 |

## B2. 关键防御句子库

需要时直接复制到论文：

**关于2人Kappa**：
> "Cohen's kappa was originally developed for two raters; our use of two coders is consistent with standard practice in computational content analysis. We augment the basic kappa with (i) 95% bootstrap confidence intervals, (ii) Krippendorff's alpha as a parallel reliability measure, (iii) per-category one-vs-rest kappas, and (iv) [if used] a third independent coder on a robustness subsample."

**关于词典偏见**：
> "The lexicon is treated as a methodological choice subject to scrutiny, not a neutral instrument. It is openly published (config/lexicon.yaml), validated by inter-coder kappa, and tested via lexicon perturbation including polysemy-aware perturbation (§3.4)."

**关于体裁混淆**：
> "All eleven documents share the genre of formal governance text. Cross-genre comparison (e.g., to industry self-regulation or news media) was considered and rejected: the within-corpus competition between capability and consequence framings—visible precisely because all documents share the same broad genre—is what makes our temporal analysis interpretable."

**关于安德斯**：
> "Anders' framework is used here as one productive interpretive lens, not as a tested hypothesis. The empirical patterns reported in §4 can be interrogated independently of the theoretical reading in §5.2. Alternative theoretical framings (Habermasian, Beckian, STS) would offer different vocabularies for the same observations."

---

# 一句话总结

完成所有步骤的最终自检：

> **如果我把§5.2(安德斯)删掉，§4(经验结果)还能独立成立吗？**

如果Yes → 投稿。  
如果No → 回到§3.5和§5.2重写。

这是整个项目的方法论生命线。
