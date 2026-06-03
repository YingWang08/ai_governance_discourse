#!/usr/bin/env python3
"""
utils_audit.py  —  审计工具（append-only日志 + 文件指纹）
========================================================
被 00_interactive_cleaning 和 06_interactive_kappa 共用。

提供两个核心能力：
  1. AuditLog: 仅追加的决策日志，永不覆盖。每条决策带时间戳。
                 同一条记录的多次修订都保留，最终决策由"最近一条"决定。
  2. fingerprint_corpus(): 对 data/raw/ 下所有文件计算 SHA-256，
                            存入 corpus_fingerprints.csv 供审稿验证。

这两个东西是审稿人质疑"你是不是改过数据"时唯一能拿出来的客观证据。
"""
from __future__ import annotations
import os
import hashlib
import csv
from datetime import datetime
from pathlib import Path


# ═══════════════════════════════════════════════════════════════════════
# 1. Append-only 决策日志
# ═══════════════════════════════════════════════════════════════════════
class AuditLog:
    """
    仅追加的CSV日志。每次调用 record() 都在文件末尾添加一行，从不覆盖。
    
    使用方式:
        log = AuditLog("output/tables/cleaning_decisions.csv")
        log.record(sent_id="abc_001", action="keep", reason="人工确认",
                   suggestion="keep", coder="auto")
    
    所有记录都带时间戳。重复 sent_id 表示该条被修订过（最后一条为准）。
    """

    FIELDS = [
        "timestamp",       # ISO 8601
        "sent_id",         # 句子ID
        "action",          # 操作（keep/drop/cap/con/both/neither/...）
        "suggestion",      # 程序建议
        "agreed",          # 是否与建议一致 (yes/no)
        "coder",           # 决策来源 (auto/human/coder1/coder2/replay)
        "reason",          # 自由文本说明
        "text_preview",    # 句子前100字符（便于核对）
    ]

    def __init__(self, path: str):
        self.path = path
        os.makedirs(os.path.dirname(path), exist_ok=True)
        if not os.path.exists(path):
            with open(path, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(self.FIELDS)

    def record(self, sent_id: str, action: str, suggestion: str = "",
               coder: str = "human", reason: str = "", text_preview: str = ""):
        agreed = "yes" if (suggestion and action == suggestion) else \
                 "no"  if suggestion else ""
        row = [
            datetime.now().isoformat(timespec="seconds"),
            str(sent_id), str(action), str(suggestion), agreed,
            str(coder), str(reason)[:200],
            str(text_preview)[:100].replace("\n", " "),
        ]
        with open(self.path, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)

    def load_latest(self) -> dict:
        """
        读取日志，返回 {sent_id: latest_action}。
        如果同一 sent_id 出现多次，以最后一次为准。
        """
        if not os.path.exists(self.path):
            return {}
        latest = {}
        with open(self.path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                latest[row["sent_id"]] = row["action"]
        return latest

    def count_revisions(self) -> dict:
        """返回 {sent_id: 修订次数}，用于审计是否有反复修改。"""
        if not os.path.exists(self.path):
            return {}
        counts = {}
        with open(self.path, "r", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                counts[row["sent_id"]] = counts.get(row["sent_id"], 0) + 1
        return counts


# ═══════════════════════════════════════════════════════════════════════
# 2. 文档指纹
# ═══════════════════════════════════════════════════════════════════════
def file_sha256(path: str, chunk_size: int = 65536) -> str:
    """计算文件的SHA-256哈希值。"""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while True:
            chunk = f.read(chunk_size)
            if not chunk:
                break
            h.update(chunk)
    return h.hexdigest()


def fingerprint_corpus(raw_dir: str, output_csv: str,
                       expected_files: list = None) -> dict:
    """
    对 raw_dir 下所有文件计算SHA-256，写入CSV。
    返回 {filename: sha256}。
    
    expected_files: 若给出，会检查这些文件是否存在并记录缺失。
    
    这个CSV应该提交到代码仓库，作为"我用的就是这个版本"的证明。
    """
    raw = Path(raw_dir)
    fingerprints = {}
    missing = []

    if expected_files:
        for fname in expected_files:
            fpath = raw / fname
            if not fpath.exists():
                # 尝试 .txt 后备
                alt = raw / (Path(fname).stem + ".txt")
                if alt.exists():
                    fpath = alt
                else:
                    missing.append(fname)
                    continue
            fingerprints[fpath.name] = file_sha256(str(fpath))
    else:
        for fpath in sorted(raw.iterdir()):
            if fpath.is_file():
                fingerprints[fpath.name] = file_sha256(str(fpath))

    # 写入CSV
    os.makedirs(os.path.dirname(output_csv), exist_ok=True)
    with open(output_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["filename", "sha256", "size_bytes", "recorded_at"])
        for fname, h in fingerprints.items():
            size = (raw / fname).stat().st_size
            w.writerow([fname, h, size,
                        datetime.now().isoformat(timespec="seconds")])

    return {"fingerprints": fingerprints, "missing": missing,
            "output": output_csv}


# ═══════════════════════════════════════════════════════════════════════
# 3. 验证指纹（用于复现性检查）
# ═══════════════════════════════════════════════════════════════════════
def verify_fingerprints(raw_dir: str, fingerprints_csv: str) -> dict:
    """
    比对当前文件 vs 历史记录的SHA-256。
    返回 {match: [...], changed: [...], missing: [...]}。
    """
    if not os.path.exists(fingerprints_csv):
        return {"error": f"找不到 {fingerprints_csv}"}

    expected = {}
    with open(fingerprints_csv, "r", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            expected[row["filename"]] = row["sha256"]

    raw = Path(raw_dir)
    match, changed, missing = [], [], []
    for fname, exp_hash in expected.items():
        fpath = raw / fname
        if not fpath.exists():
            missing.append(fname)
        else:
            actual = file_sha256(str(fpath))
            if actual == exp_hash:
                match.append(fname)
            else:
                changed.append({"filename": fname,
                                "expected": exp_hash[:16],
                                "actual": actual[:16]})

    return {"match": match, "changed": changed, "missing": missing}


# ═══════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    # 自测
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        log = AuditLog(os.path.join(td, "test.csv"))
        log.record("s001", "keep", "keep", "auto", "正常", "AI must be safe.")
        log.record("s001", "drop", "keep", "human", "改主意", "AI must be safe.")
        latest = log.load_latest()
        assert latest["s001"] == "drop", "append-only failed"
        revs = log.count_revisions()
        assert revs["s001"] == 2, "revision count failed"
        print("✓ AuditLog 测试通过")
        print(f"  最新决策: {latest}")
        print(f"  修订次数: {revs}")
