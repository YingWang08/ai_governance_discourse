#!/usr/bin/env bash
# run_all.sh — v3：与 MASTER_GUIDE v2/v3 流水线一致的端到端运行
# 前提：data/raw/ 已放入11份原始文件（见 config/corpus_manifest.yaml）
set -e
cd "$(dirname "$0")"
echo "==> 00 全自动清洗 (提取+清洗+空提取检测)"; python src/00_auto_cleaning.py
echo "==> 02 词典定型 (none, 最可复现)";          python src/02_expand_lexicon.py --method none
echo "==> 03 框架编码 (share + 独立rate)";         python src/03_frame_coding.py
echo "==> 04 共现网络 (含boundary桥接词节点)";      python src/04_cooccurrence_network.py
echo "==> 05 时间分析 (rate趋势+句子级卡方检验)";    python src/05_temporal_analysis.py
echo "==> 07 稳健性 (词典/留一/时段/多义/文档加权/体裁)"; python src/07_robustness.py
echo ""
echo "完成。图 -> output/figures/，表 -> output/tables/"
echo "评分者间信度(人工一次性，见README §5):"
echo "  python src/06_interactive_kappa.py --make-sample --n 300"
echo "  python src/06_interactive_kappa.py --code --coder 1   # 两人独立"
echo "  python src/06_interactive_kappa.py --code --coder 2"
echo "  python src/06_interactive_kappa.py --score"
echo "  python src/06_interactive_kappa.py --adjudicate"
