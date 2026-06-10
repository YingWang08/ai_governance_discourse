# Sentence-Level Information Extraction from AI Governance Texts

A reproducible, **CPU-only** pipeline for the paper:

> **Sentence-Level Information Extraction from AI Governance Texts: A Reproducible
> Pipeline with Lexicon Validation, Benchmarking, and Semantic-Network Analysis**

The pipeline classifies every sentence of an AI governance document into one of four
frames — **capability** ("what AI can do"), **consequence** ("what it does / what it
obliges"), **both**, or **neither** — using a validated lexicon and codebook. It then
(i) validates the extraction against a human gold standard, a supervised baseline, and
two independent large-language-model annotators used as auxiliary triangulation;
(ii) characterises the corpus through a term co-occurrence network; and (iii) tracks
how the frame balance shifts across the 2019–2025 observation window.

Everything runs on an ordinary CPU. No GPU, no specialised hardware, no ethics-committee
approval (the corpus is public official documents only; no human subjects, no personal data).

---

## Reproducibility & data

- **All code, the lexicon and codebook, the derived sentence-level dataset, the
  inter-coder reliability sample (both coders' labels + adjudication), and the full
  LLM prompt and complete raw model outputs** are archived on Figshare:
  **DOI [10.6084/m9.figshare.32568747](https://doi.org/10.6084/m9.figshare.32568747)**.
- This repository holds the analysis code.
- Random seeds are fixed (reliability sample `seed = 99`; supervised baseline `seed = 42`)
  for full reproducibility.

---

## 1. Install

```bash
python -m venv .venv
# Windows:      .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

The cleaning step uses NLTK's Punkt sentence tokenizer (~13 MB, downloaded once). If the
run-time machine has no internet, fetch it beforehand:

```python
import nltk; nltk.download('punkt'); nltk.download('punkt_tab')
```

---

## 2. Get the data (manual, one time)

The eleven flagship governance documents are listed in Table 1 of the paper. Download the
official PDF (or official HTML/text) of each from its source body into the raw-data folder,
keeping a stable filename per document. Manual download keeps the corpus auditable and avoids
fragile scrapers. All sources are official and public, so **no ethics approval is required**.

---

## 3. Pipeline — run order

The scripts are numbered in execution order. Steps 00–07 produce the corpus, the labels, and
the three analytical results; steps 08–15 are the benchmarking and robustness layer that the
paper's Section 3.5 and Sections 4.1–4.5 report.

| Script | Does | Paper element |
|---|---|---|
| `00_auto_cleaning.py` | Ingest PDF/HTML, strip boilerplate (page numbers, article markers, watermarks, tables-as-text), split into sentences, drop < 5-token segments, log every removed segment | §3.1 Corpus construction (Tables 1–2) |
| `02_expand_lexicon.py` | Build / audit the capability & consequence lexicon (`--method none` for the audited list used in the paper; `--method sbert` optional, CPU-OK) | §3.2.1, Appendix A |
| `03_frame_coding.py` | Label every sentence (cap / con / both / neither) from the lexicon; per-year / per-body / per-document salience | §3.2, §4.2 (Table 6) |
| `04_cooccurrence_network.py` | Build the term co-occurrence network; compute betweenness centrality (bridging terms) | §4.3 (Figure 2, Table 7) |
| `05_temporal_analysis.py` | Per-sentence frame **rates** by year; net-consequence index; descriptive lag cross-correlation | §4.4 (Figure 3, Table 8) |
| `06_interactive_kappa.py` | Inter-coder reliability: draw the blind sample, score Cohen's κ / Krippendorff's α, per-category κ | §3.2.3 (κ = 0.91) |
| `07_robustness.py` | Six robustness checks: lexical / polysemy perturbation, leave-one-document-out, coarse-period, document- vs. sentence-weighting, genre stratification | §3.4, §4.5 (Table 9, Appendix B) |
| `08_batch_coding.py` | Apply the validated coding across the full corpus, writing `coded_sentences.csv` for the downstream benchmarking and inference scripts | feeds §4.1, §4.4, §4.5 |
| `09_classification_metrics.py` | Lexicon vs. human gold standard: per-frame & per-class precision / recall / F1 + four-class confusion matrix (decomposes the single auto-vs-human κ into "high recall, lower precision") | §4.1 (Table 3) |
| `10_supervised_baseline.py` | TF-IDF + logistic-regression baseline (balanced class weights, stratified 5-fold CV, `seed = 42`); lexicon scored on the identical folds | §4.1 (Table 4) |
| `11_llm_annotation.py` | Generate the shared annotation prompt and score two LLMs (web-interface workflow) against the gold standard; per-frame F1, four-class κ, run-to-run κ | §4.1 (Table 5) |
| `12_clustered_inference.py` | Clustering-aware inference: document-level Spearman / Kendall / Mann–Kendall (n = 11), GEE (exchangeable, clustered on document), cluster-robust logit, document cluster bootstrap, and a genre-adjusted model | §4.4 |
| `13_procedural_filter.py` | Implement the codebook's "about-what" procedural-obligation exclusion in code; reclassify pure administrative `shall`/`must` sentences to *neither*; re-score precision/recall/F1 | §4.5 |
| `14_llm_panel_api.py` | API-based alternative to `11`, for users who prefer scripted LLM annotation over the web interface | §4.1 (alternative path) |
| `15_lexicon_validity.py` | Lexicon-composition bootstrap (drop a random 30 % of each frame's terms, B = 1000) + per-term influence audit | §4.5 |
| `generate_pipeline_figure.py` | Render the end-to-end pipeline diagram | Figure 1 |
| `make_genre_template.py` | Helper to build the hard-law / soft-law genre stratification table | §4.5 genre check |

There is no `01_…`; ingestion is handled entirely by `00_auto_cleaning.py`.

---

## 4. Clean before you trust (the PDF pitfall)

Real governance PDFs are dirty (page numbers, `Article 5(1)(c)`, watermarks, tables-as-text).
`00_auto_cleaning.py` strips the common cases automatically and logs **everything removed** to a
dropped-sentences file, so cleaning stays auditable. Always skim the cleaning output on your own
files before trusting downstream counts; add a rule, or hand-clean a document as a `.txt`, if
anything is still broken. Re-run until clean.

---

## 5. Reliability + codebook (the kappa pitfall)

A kappa is only credible with a written manual. Two coders read the codebook (reproduced in
Appendix A of the paper and included in the Figshare archive), then **independently** label the
blind sample; `06_interactive_kappa.py` scores agreement. Report the human–human κ, the per-category
κ, and the human-vs-automatic agreement (the latter decomposed into precision/recall by
`09_classification_metrics.py`). The finalised codebook lives in the appendix and the archive.

---

## 6. The benchmarking layer (what reviewers asked for)

The paper's validity case rests on **four reference points**, all reproducible here:

1. **Human gold standard** — blind two-coder reliability, κ = 0.91 (`06`).
2. **Transparent rule-based classifier** — the lexicon itself, scored per-frame (`09`).
3. **Supervised baseline** — TF-IDF + logistic regression, 5-fold CV (`10`).
4. **Auxiliary LLM triangulation** — two models from different developers, codebook-only,
   prompt and raw outputs released (`11` / `14`).

The human-coded gold standard is the **sole reference** for all classification metrics; the LLM
outputs are reported only as auxiliary external triangulation, never as ground truth.

Two further scripts probe the construction of the measure directly: the procedural-obligation
filter (`13`) bounds over-coding of administrative language, and the lexicon bootstrap +
term-influence audit (`15`) shows the temporal direction is not carried by any single term.

---

## 7. Reading the temporal result (the interpretation pitfall)

The unit of temporal inference is **eleven documents, not 5,527 sentences**. `12` runs the
clustering-aware models that keep the inference honest; the sentence-level chi-square is a
**heuristic only**, because it treats clustered sentences as independent. Report the document-level
trend as the primary result, treat the trend as **exploratory and modest in strength** at this
sample size, and keep the cross-sectional network finding (`04`) as an independent result that does
not depend on the trajectory. Any broader interpretive reading is the author's job in the
Discussion, not the code's, and the empirical results stand on their own without it.

---

## 8. How the code answers the predictable reviewer objections

- **"Corpus too small / document-level counting."** The unit of analysis is the **sentence**
  (5,527 sentences, 207,777 tokens); `00` prints these. For *inference*, the unit is the document,
  and `12` does document-level and clustering-aware estimation — no pseudoreplication.
- **"It's just word frequency."** The headline is a **temporal trajectory** plus a **bridging-term
  network structure**, not a static count (`04`, `05`).
- **"The lexicon is arbitrary / researcher bias."** The lexicon is external and audited (`02`),
  validated by two human coders with Cohen's κ (`06`), benchmarked against a supervised model (`10`)
  and two independent LLMs (`11`/`14`), and shown robust to dropping 30 % of its terms (`15`).
- **"Over-coding of `shall`/`must` procedural text."** Quantified and bounded by the explicit
  procedural-obligation filter (`13`): reclassifies only ~0.8 % of sentences, consequence F1 unchanged.
- **"Driven by one long document (the EU AI Act)."** Leave-one-document-out is in `07`.
- **"Soft-to-hard-law confound."** Genre stratification (`07`) and a genre-adjusted model (`12`).

---

## 9. Notes

- No `localStorage`, no network calls at analysis time (except the one-time NLTK download and the
  optional SBERT model fetch).
- The lexicon files are the single most important knob. Edit them, re-run, and report any change —
  that *is* the robustness story (`15`).
- Random seeds are fixed (`99` for the reliability sample, `42` for the supervised baseline).
