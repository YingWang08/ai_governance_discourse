#!/usr/bin/env bash
# ============================================================
# download_corpus.sh
# 一键下载全部11份语料库原始文件到 data/raw/
# 用法：在项目根目录执行  bash download_corpus.sh
# ============================================================
set -e
mkdir -p data/raw
cd data/raw

UA="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
DL="curl -L --max-time 60 -A \"$UA\" --retry 3 --retry-delay 5"

ok=0
fail=0
skip=0

download() {
  local filename="$1"
  local url="$2"
  local note="$3"

  if [ -f "$filename" ] && [ $(wc -c < "$filename") -gt 10000 ]; then
    echo "[skip] $filename 已存在，跳过"
    skip=$((skip+1))
    return
  fi

  echo ""
  echo ">>> 下载: $filename"
  echo "    $url"
  if [ -n "$note" ]; then echo "    注意: $note"; fi

  curl -L --max-time 60 -A "$UA" --retry 3 --retry-delay 5 \
       -o "$filename" "$url"

  size=$(wc -c < "$filename" 2>/dev/null || echo 0)
  if [ "$size" -gt 10000 ]; then
    echo "[ok] $filename  ($(du -h "$filename" | cut -f1))"
    ok=$((ok+1))
  else
    echo "[FAIL] $filename 下载失败或文件过小 (${size} bytes)"
    echo "       请手动访问: $url"
    rm -f "$filename"
    fail=$((fail+1))
  fi
}

# ---- 1. OECD 2019 ----
download "oecd_2019.pdf" \
  "https://legalinstruments.oecd.org/api/download/?uri=/instruments/OECD-LEGAL-0449" \
  "若下载失败，访问 https://oecd.ai/en/ai-principles 找 PDF 链接"

# ---- 2. G20 2019 ----
download "g20_2019.pdf" \
  "https://www.mofa.go.jp/files/000486596.pdf" \
  ""

# ---- 3. UNESCO 2021 ----
download "unesco_2021.pdf" \
  "https://unesdoc.unesco.org/ark:/48223/pf0000381137.locale=en" \
  "若失败可在 https://unesdoc.unesco.org 搜索 '381137'"

# ---- 4. EU AI Act Commission Proposal 2021 ----
# EUR-Lex 直链
download "eu_aiact_proposal_2021.pdf" \
  "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:52021PC0206" \
  "较大文件（~120页），需耐心等待"

# ---- 5. NIST RMF 2023 ----
download "nist_rmf_2023.pdf" \
  "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf" \
  ""

# ---- 6. G7 Hiroshima 2023 ----
# 欧盟数字战略网站有该文件
download "g7_hiroshima_2023.pdf" \
  "https://digital-strategy.ec.europa.eu/en/library/hiroshima-process-international-guiding-principles-advanced-ai-system" \
  "这个页面可能是HTML，见下方备注"

# G7 Hiroshima 备用：白宫直链
echo ""
echo "    [备注] G7 Hiroshima 如上链接为HTML页面，请改用以下任一备用链接手动下载："
echo "    白宫存档: https://www.whitehouse.gov/briefing-room/statements-releases/2023/10/30/g7-hiroshima-process-international-guiding-principles-for-advanced-ai-systems/"
echo "    然后将页面内容保存为 data/raw/g7_hiroshima_2023.txt"

# ---- 7. US Executive Order 14110 (2023) ----
download "us_eo_14110_2023.pdf" \
  "https://www.federalregister.gov/documents/full_text/pdf/2023-24283.pdf" \
  ""

# ---- 8. OECD 2024 (更新版) ----
download "oecd_2024.pdf" \
  "https://legalinstruments.oecd.org/api/download/?uri=/instruments/OECD-LEGAL-0449" \
  "重要：与oecd_2019同一URL。请手动确认下载的是2024年更新文本，否则去 https://oecd.ai/en/ai-principles 找历史版本"

# ---- 9. EU AI Act Final 2024 ----
download "eu_aiact_final_2024.pdf" \
  "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=OJ:L_202401689" \
  "最大文件（~458页），耐心等待"

# ---- 10. Council of Europe Convention 2024 ----
download "coe_convention_2024.pdf" \
  "https://rm.coe.int/1680afae3c" \
  "CoE直链PDF，若失败访问 https://www.coe.int/en/web/artificial-intelligence/the-framework-convention-on-artificial-intelligence"

# ---- 11. EU GPAI Code of Practice 2025 ----
download "eu_gpai_code_2025.pdf" \
  "https://digital-strategy.ec.europa.eu/en/policies/contents-code-gpai" \
  "2025年文件，若链接为HTML，手动下载PDF并存为 eu_gpai_code_2025.pdf"

# ============================================================
echo ""
echo "============================================"
echo "下载完成统计"
echo "  成功: $ok"
echo "  跳过(已存在): $skip"
echo "  失败(需手动): $fail"
echo "============================================"
echo ""
echo "下一步："
echo "  1. 检查 data/raw/ 中的文件是否完整"
echo "  2. 对于失败的文件，按上方提示手动下载"
echo "  3. 如某PDF文本提取困难，另存为同名.txt文件即可"
echo "  4. 然后运行: python src/01_ingest.py"
