# AI Governance Discourse — Capability vs Consequence (2019–2026)

A reproducible, **CPU-only**, ethics-clearance-free pipeline for the paper:

> *The Shifting Balance of Capability and Consequence in Global AI
> Governance Discourse, 2019–2026: A Computational Text Analysis through
> Günther Anders' Lens*

The pipeline codes governance-document sentences into a **capability** frame
("what AI can do") and a **consequence** frame ("what it does to us"), then
tracks how their balance shifts over time and aligns the lag with Anders'
notion of the *Promethean gap*.

Every step runs on the **CPU** in minutes — no GPU, no paid API, no human
subjects, and no personal data, so **no ethics approval is required**. All
sources are official, public governance documents.

---

## 1. Install

```bash
python -m venv .venv
# Windows:        .venv\Scripts\activate
# macOS / Linux:  source .venv/bin/activate
pip install -r requirements.txt
```

The first run that tokenizes text downloads NLTK's sentence tokenizer
(~13 MB, one time). If the machine is offline at run time, fetch it once
beforehand:

```python
import nltk; nltk.download('punkt'); nltk.download('punkt_tab')
```

---

## 2. Get the data (manual, one time, ~30 min)

Open `config/corpus_manifest.yaml`. For each document, download the official
PDF from its `url` into `data/raw/`, saving it under the exact `file` name
listed (e.g. `oecd_2019.pdf`). Manual download keeps the corpus auditable and
avoids fragile scrapers.

- Can't get a clean PDF? Save the official text as `data/raw/<id>.txt` instead;
  the pipeline auto-detects it.
- Add or remove documents freely by editing the manifest — keep the `id`,
  `year`, and `file` fields.
- **Raw PDFs are not redistributed in this repo** (copyright). The manifest
  tells anyone exactly which public documents to fetch.

---

## 3. The pipeline

Scripts are numbered in run order. Place them under `src/` (or run from the
repo root — each script resolves paths either way).

| Step | Script | What it does |
|---|---|---|
| 0 | `00_auto_cleaning.py` | Fully automatic, zero-touch sentence cleaning of dirty governance PDFs; logs every removed sentence for audit |
| 2 | `02_expand_lexicon.py` | Normalises the seed lexicon (`--method none`, default) or optionally grows it from the corpus itself (`--method sbert`) |
| 3 | `03_frame_coding.py` | Labels every sentence; outputs salience by year / body / document, plus an **independent rate** (not share-closed) for the lag analysis |
| 4 | `04_cooccurrence_network.py` | Keyword co-occurrence network + centrality table; boundary terms (e.g. *trustworthy*) included as bridging nodes |
| 5 | `05_temporal_analysis.py` | **Centerpiece**: temporal trajectory, cross-correlation lag, and a sentence-level early-vs-late χ² test |
| 7 | `07_robustness.py` | Lexicon perturbation, leave-one-document-out, time-granularity, and polysemy checks |

Inter-coder reliability and validation (run as needed):

| Step | Script | What it does |
|---|---|---|
| 6 | `06_interactive_kappa.py` | Interactive per-sentence double-coding + Cohen's κ |
| 8 | `08_batch_coding.py` | Faster alternative to 06: export an Excel sheet with dropdowns, two coders fill it, import back (same `coding_sample.csv`, same labels) |
| 9 | `09_classification_metrics.py` | Lexicon vs human Precision / Recall / F1 (explains the κ as "high recall, low precision") |
| 10 | `10_supervised_baseline.py` | TF-IDF + Logistic Regression baseline, stratified CV, fixed seed — apples-to-apples vs the lexicon |
| 11 | `11_llm_annotation.py` | Uses **web-chat LLM outputs** (no paid API) as an independent third annotator; multi-model cross-validation |

Coders read **`CODEBOOK_template.md`** before labelling — a κ is only
credible with a written manual. The finalised codebook goes in the appendix.

Typical minimal run after `data/raw/` is populated:

```bash
cd src
python 00_auto_cleaning.py
python 02_expand_lexicon.py --method none
python 03_frame_coding.py
python 04_cooccurrence_network.py
python 05_temporal_analysis.py
python 07_robustness.py
```

---

## 4. Files you must add before the repo runs

These are imported or read by the scripts but are **not** committed here (they
are environment- or content-specific). Add them under the paths shown:

- **`utils_audit.py`** — provides `AuditLog` and `fingerprint_corpus`,
  imported by `00` and `06`. Required.
- **`config/lexicon.yaml`** — the seed lexicon (capability / consequence /
  boundary terms). This is the single most important knob; edit it, re-run,
  and report any change — that *is* the robustness story.
- **`config/corpus_manifest.yaml`** — `id`, `year`, `file`, `url` for every
  source document.
- **`config/lexicon_expanded.yaml`** — produced by `02`; you don't write it by
  hand.

(The pipeline also expects an ingest step that turns `data/raw/` PDFs/txt into
`sentences.csv` before `00` cleans them. If you keep that as a separate
`01_*` script, add it too.)

---

## 5. Outputs and where they appear in the paper

| File | Paper element |
|---|---|
| `output/figures/temporal_salience.png` | **Centerpiece figure** (RQ2) |
| `output/figures/net_consequence_trend.png` | Net balance over time |
| `output/figures/cooccurrence_network.png` | Semantic structure (RQ1) |
| `output/tables/salience_by_year.csv` | Temporal salience numbers |
| `output/tables/salience_by_document.csv` / `_by_body.csv` | Distribution (RQ1) |
| `output/tables/network_centrality.csv` | Bridging terms |
| `output/tables/temporal_crosscorr.csv` | Descriptive lag (RQ2) |
| `output/tables/reliability_report.txt` | Cohen's κ (Methods) |
| `output/tables/metrics_lexicon_4class.csv` | P/R/F1 vs human (validation) |
| `output/tables/robustness_*.csv` | Robustness checks |

---

## 6. How the code answers the predictable reviewer objections

- **"Corpus too small / document-level counting."** The unit of analysis is the
  **sentence**; report sample size in sentences/tokens, not documents.
- **"It's just word frequency."** The main result (`05`) is a **temporal
  trajectory with a lag**, not a static count.
- **"Researcher bias in the lexicon."** The lexicon is external
  (`config/lexicon.yaml`), optionally data-expanded (`02`), and validated by
  **two human coders with Cohen's κ** (`06`/`08`), a supervised baseline
  (`10`), and an independent LLM annotator (`11`).
- **"Driven by one long document (the EU AI Act)."** Leave-one-document-out is
  built into `07`.
- **"Reading the lag."** The lag *number* from `05` is meaningless until aligned
  with the governance timeline (GPT-4 release, G7 Hiroshima Process, EU AI Act
  trilogue) in the Discussion. Only then does Anders' Promethean gap attach.
  This is the author's job, not the code's.
- **"Anders is dubious / I don't know Anders."** The theory is **detachable** —
  every figure and table stands on its own; Anders enters only in
  interpretation.

---

## 7. Reproducibility notes

- No network calls at analysis time except the one-time NLTK download and the
  optional SBERT model fetch.
- Random seeds are fixed (`42`).
- Cleaning is auditable: every removed sentence is logged
  (`output/tables/cleaning_decisions.csv`) so you can tell a reviewer exactly
  what was excluded and why.

---

## 8. Citation

If you use this code or data, please cite the software (see `CITATION.cff`) and
the accompanying paper once published.

## 9. License

Released under the [MIT License](LICENSE). The MIT license covers the **code**.
If you also want to license the figures, codebook, or any released derived data,
a content license such as CC-BY 4.0 is the conventional companion — add a note
in this section if you adopt one.
