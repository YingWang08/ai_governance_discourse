#!/usr/bin/env python3
"""
02_expand_lexicon.py  —  Optional semantic expansion of seed lexicon
====================================================================
Methods 3.2, layer 1->2. Takes the seed terms in config/lexicon.yaml and
optionally grows each frame with nearest-neighbour terms found in the
CORPUS ITSELF (data-driven, not hand-picked -> reduces researcher bias).

Two modes:
  --method none   (default) : just normalises & saves the seed lexicon.
                              Fully reproducible, zero ML, defensible.
  --method sbert            : expand using sentence-transformers word
                              embeddings (needs internet once to fetch a
                              small model; runs fine on CPU; GTX1650
                              optional). Adds candidate neighbours that a
                              human coder then keeps/drops.

Output : config/lexicon_expanded.yaml  (the audited list used for scoring)
         output/tables/lexicon_expansion_audit.csv  (for the appendix)

Even if you never run sbert, run this once with --method none so the rest
of the pipeline has lexicon_expanded.yaml to read.

Dependencies (only for sbert mode): sentence-transformers scikit-learn
  pip install sentence-transformers
"""
from __future__ import annotations
import os
import argparse
import yaml
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CONF = os.path.join(ROOT, "config")
PROC = os.path.join(ROOT, "data", "processed")
TABLES = os.path.join(ROOT, "output", "tables")


def load_seed():
    with open(os.path.join(CONF, "lexicon.yaml"), "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def expand_sbert(seed, top_k=8, threshold=0.55):
    """For each seed term, propose corpus vocabulary neighbours by cosine
    similarity of SBERT embeddings. Returns dict frame->set, plus an audit
    table of (frame, seed, candidate, similarity)."""
    from sentence_transformers import SentenceTransformer
    from sklearn.metrics.pairwise import cosine_similarity
    import numpy as np
    import re
    from collections import Counter

    df = pd.read_csv(os.path.join(PROC, "sentences.csv"))
    # build corpus vocabulary (lowercased unigrams, min frequency)
    words = re.findall(r"[a-z][a-z\-']{2,}", " ".join(df.text).lower())
    freq = Counter(words)
    vocab = [w for w, c in freq.items() if c >= 5]
    print(f"[sbert] corpus vocabulary size (freq>=5): {len(vocab)}")

    model = SentenceTransformer("all-MiniLM-L6-v2")  # small, CPU-friendly
    vocab_emb = model.encode(vocab, batch_size=64, show_progress_bar=True,
                             normalize_embeddings=True)

    audit_rows = []
    expanded = {}
    for frame in ("capability", "consequence"):
        seeds = seed[frame]
        seed_emb = model.encode(seeds, normalize_embeddings=True)
        sims = cosine_similarity(seed_emb, vocab_emb)
        keep = set(s.lower() for s in seeds)
        for i, s in enumerate(seeds):
            order = np.argsort(-sims[i])[:top_k]
            for j in order:
                cand, sim = vocab[j], float(sims[i][j])
                if sim >= threshold and cand not in keep:
                    keep.add(cand)
                    audit_rows.append({"frame": frame, "seed": s,
                                       "candidate": cand,
                                       "similarity": round(sim, 3)})
        expanded[frame] = sorted(keep)
    expanded["boundary"] = seed.get("boundary", [])
    audit = pd.DataFrame(audit_rows).sort_values(
        ["frame", "similarity"], ascending=[True, False])
    return expanded, audit


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--method", choices=["none", "sbert"], default="none")
    ap.add_argument("--top_k", type=int, default=8)
    ap.add_argument("--threshold", type=float, default=0.55)
    args = ap.parse_args()

    seed = load_seed()
    os.makedirs(TABLES, exist_ok=True)

    if args.method == "none":
        expanded = {k: sorted(set(x.lower() for x in v))
                    for k, v in seed.items()}
        audit = pd.DataFrame(columns=["frame", "seed", "candidate", "similarity"])
        print("[mode] none — using seed lexicon as-is (most reproducible).")
    else:
        expanded, audit = expand_sbert(seed, args.top_k, args.threshold)
        print(f"[mode] sbert — proposed {len(audit)} candidate expansions.")
        print("       >>> REVIEW output/tables/lexicon_expansion_audit.csv and")
        print("       >>> hand-prune before trusting. This is the human step.")

    with open(os.path.join(CONF, "lexicon_expanded.yaml"), "w",
              encoding="utf-8") as f:
        yaml.safe_dump(expanded, f, allow_unicode=True, sort_keys=False)
    audit.to_csv(os.path.join(TABLES, "lexicon_expansion_audit.csv"),
                 index=False)

    for frame in ("capability", "consequence", "boundary"):
        print(f"  {frame:<12}: {len(expanded.get(frame, []))} terms")
    print(f"[saved] {os.path.join(CONF, 'lexicon_expanded.yaml')}")


if __name__ == "__main__":
    main()
