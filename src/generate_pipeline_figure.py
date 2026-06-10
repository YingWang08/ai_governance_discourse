"""
Figure 1 — End-to-end extraction and analysis pipeline.
Publication-quality, Applied Sciences (MDPI), 300 dpi.
"""
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
import numpy as np

DPI = 300
FIG_W, FIG_H = 12.0, 7.4

# Colors (muted, print-safe)
C_BLUE = '#4472C4';  C_BLUE_BG = '#D6E4F0';  C_BLUE_T = '#1B3A5C'
C_ORNG = '#C55A11';  C_ORNG_BG = '#FDE8D0';  C_ORNG_T = '#7A3B12'
C_PURP = '#7B57A0';  C_PURP_BG = '#E8DDF0';  C_PURP_T = '#3F2062'
C_GRN  = '#548235';  C_GRN_BG  = '#DEE8D1';  C_GRN_T  = '#2D5016'
C_GREY = '#404040';  C_LGREY   = '#F2F2F2';  C_WHITE  = '#FFFFFF'

FS_BOX = 9;  FS_SUB = 7.5;  FS_TINY = 6.5;  FS_LBL = 8.5

# ─── Helpers ─────────────────────────────────────────────────────
def rbox(ax, cx, cy, w, h, l1, l2=None,
         fc=C_WHITE, ec=C_GREY, lw=1.1, tc=C_GREY, pad=0.12):
    b = FancyBboxPatch((cx-w/2, cy-h/2), w, h,
            boxstyle=f"round,pad={pad}", fc=fc, ec=ec, lw=lw, zorder=3)
    ax.add_patch(b)
    if l2:
        ax.text(cx, cy+0.14, l1, ha='center', va='center',
                fontsize=FS_BOX, fontweight='bold', color=tc, zorder=4)
        ax.text(cx, cy-0.13, l2, ha='center', va='center',
                fontsize=FS_SUB, color=tc, style='italic', zorder=4)
    else:
        ax.text(cx, cy, l1, ha='center', va='center',
                fontsize=FS_BOX, fontweight='bold', color=tc, zorder=4)

def gbox(ax, x, y, w, h, label, fc, ec, lc, dash=False):
    b = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12",
            fc=fc, ec=ec, lw=0.8, ls='--' if dash else '-', zorder=1)
    ax.add_patch(b)
    # Label with white background for readability
    t = ax.text(x+0.18, y+h-0.05, label, ha='left', va='top',
                fontsize=FS_LBL, fontweight='bold', color=lc, zorder=6)
    t.set_bbox(dict(facecolor=fc, edgecolor='none', alpha=0.9, pad=1.5))

def harr(ax, x1, y, x2, c=C_GREY, lw=1.4):
    ax.annotate('', xy=(x2,y), xytext=(x1,y),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw), zorder=5)

def varr(ax, x, y1, y2, c=C_GREY, lw=1.4, dash=False):
    ax.annotate('', xy=(x,y2), xytext=(x,y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                                linestyle='--' if dash else '-'), zorder=5)

def darr(ax, x1, y1, x2, y2, c=C_GREY, lw=1.0, dash=False):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=lw,
                                linestyle='--' if dash else '-'), zorder=5)

# ─── Figure ──────────────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(FIG_W, FIG_H), dpi=DPI)
ax.set_xlim(-0.1, 11.6)
ax.set_ylim(-0.6, 7.1)
ax.set_aspect('equal')
ax.axis('off')

# Shared x-centers
XL, XC, XR = 2.0, 5.65, 9.3

# ════════════════════════════════════════════════════════════════
# ROW 1 — Data Preparation
# ════════════════════════════════════════════════════════════════
y1 = 6.1
bw, bh = 2.5, 0.72
gbox(ax, 0.2, y1-0.65, 11.1, 1.3, 'Data Preparation  (§3.1–3.2)',
     C_BLUE_BG, C_BLUE, C_BLUE)

rbox(ax, XL, y1, bw, bh, 'Corpus Construction',
     '11 documents, 2019–2025', ec=C_BLUE, tc=C_BLUE_T)
rbox(ax, XC, y1, bw, bh, 'Sentence Splitting',
     'Punkt tokeniser → 5,527 sent.', ec=C_BLUE, tc=C_BLUE_T)
rbox(ax, XR, y1, bw, bh, 'Lexicon-Based Frame Coding',
     '4-class: cap / con / both / neither', ec=C_BLUE, tc=C_BLUE_T)

harr(ax, XL+bw/2, y1, XC-bw/2, c=C_BLUE)
harr(ax, XC+bw/2, y1, XR-bw/2, c=C_BLUE)

# ════════════════════════════════════════════════════════════════
# Gold Standard badge
# ════════════════════════════════════════════════════════════════
yg = 4.95
rbox(ax, XC, yg, 3.3, 0.36,
     'Labelled Sentences → Gold Standard (n = 300)',
     fc='#FFF7ED', ec=C_ORNG, tc=C_ORNG_T, lw=0.9, pad=0.08)

darr(ax, XR, y1-bh/2, XC+1.3, yg+0.18, c=C_ORNG, lw=1.0, dash=True)

# ════════════════════════════════════════════════════════════════
# ROW 2 — Validation & Benchmarking
# ════════════════════════════════════════════════════════════════
y2 = 3.90
vw, vh = 2.9, 0.72
gbox(ax, 0.2, y2-0.65, 11.1, 1.3,
     'Validation & Benchmarking  (§3.5)',
     C_ORNG_BG, C_ORNG, C_ORNG, dash=True)

rbox(ax, XL, y2, vw, vh, 'Human Inter-Coder Reliability',
     "Cohen's κ = 0.91  (n = 300)", ec=C_ORNG, tc=C_ORNG_T)
rbox(ax, XC, y2, vw, vh, 'Supervised Baseline',
     'TF-IDF + LogReg  (macro-F1 = 0.53)', ec=C_ORNG, tc=C_ORNG_T)
rbox(ax, XR, y2, vw, vh, 'LLM Triangulation (auxiliary)',
     '2 models  (con F1 = 0.69–0.71)', ec=C_ORNG, tc=C_ORNG_T)

# Arrows from Gold Standard → three validation boxes
darr(ax, XC-0.9, yg-0.18, XL, y2+vh/2, c=C_ORNG, lw=0.9, dash=True)
varr(ax, XC, yg-0.18, y2+vh/2, c=C_ORNG, lw=0.9, dash=True)
darr(ax, XC+0.9, yg-0.18, XR, y2+vh/2, c=C_ORNG, lw=0.9, dash=True)

# ════════════════════════════════════════════════════════════════
# Validated Labels badge
# ════════════════════════════════════════════════════════════════
yv = 2.78
rbox(ax, XC, yv, 3.0, 0.34,
     'Validated Frame Labels  (5,527 sent.)',
     fc=C_LGREY, ec=C_GREY, tc=C_GREY, lw=0.8, pad=0.08)
varr(ax, XC, y2-vh/2, yv+0.17, c=C_GREY, lw=1.4)

# ════════════════════════════════════════════════════════════════
# ROW 3 — Downstream Analyses
# ════════════════════════════════════════════════════════════════
y3 = 1.70
aw, ah = 2.3, 0.68
gbox(ax, 0.2, y3-0.65, 11.1, 1.3, 'Downstream Analyses  (§4.2–4.5)',
     C_PURP_BG, C_PURP, C_PURP)

xs3 = [1.55, 4.2, 6.85, 9.5]
for x, (l1, l2) in zip(xs3,
    [('Frame', 'Distribution'),
     ('Semantic-Network', 'Analysis'),
     ('Temporal', 'Analysis'),
     ('Robustness &', 'Ablation')]):
    rbox(ax, x, y3, aw, ah, l1, l2, ec=C_PURP, tc=C_PURP_T)

# Fan-out: center arrow first, then diagonal branches
varr(ax, XC, yv-0.17, y3+ah/2+0.06, c=C_GREY, lw=1.2)
# Branch lines (no arrowhead, just connector + arrowhead boxes)
branch_y = y3 + ah/2 + 0.04
for x in xs3:
    if abs(x - XC) > 0.5:
        darr(ax, XC, branch_y, x, y3+ah/2, c=C_GREY, lw=0.8)

# ════════════════════════════════════════════════════════════════
# ROW 4 — Open Release
# ════════════════════════════════════════════════════════════════
y4 = 0.25
gbox(ax, 0.2, y4-0.40, 11.1, 0.80, '', C_GRN_BG, C_GRN, C_GRN)
ax.text(0.42, y4+0.05, 'Open\nRelease', ha='left', va='center',
        fontsize=FS_LBL, fontweight='bold', color=C_GRN,
        zorder=4, linespacing=1.1)

for i, item in enumerate(
    ['Code &\nScripts', 'Lexicon &\nCodebook', 'Human\nLabels',
     'LLM\nOutputs', 'Derived\nDataset']):
    xi = 2.7 + i * 1.80
    rbox(ax, xi, y4, 1.5, 0.48, item,
         fc=C_WHITE, ec=C_GRN, tc=C_GRN_T, lw=0.8, pad=0.06)

varr(ax, XC, y3-ah/2, y4+0.40, c=C_GREY, lw=1.2)

# ════════════════════════════════════════════════════════════════
# Legend
# ════════════════════════════════════════════════════════════════
ly = -0.35
ax.annotate('', xy=(0.7,ly), xytext=(0.2,ly),
            arrowprops=dict(arrowstyle='->', color=C_GREY, lw=1.2))
ax.text(0.8, ly, 'Main processing flow', fontsize=FS_TINY,
        va='center', color=C_GREY)
ax.annotate('', xy=(4.0,ly), xytext=(3.5,ly),
            arrowprops=dict(arrowstyle='->', color=C_ORNG, lw=1.0, ls='--'))
ax.text(4.1, ly, 'Validation / benchmarking', fontsize=FS_TINY,
        va='center', color=C_ORNG)

# ─── Save ─────────────────────────────────────────────────────
fig.tight_layout(pad=0.2)
for ext in ('png', 'pdf'):
    fig.savefig(f'D:/ai_governance_discourse/output/figures/Figure1_pipeline.{ext}',
                dpi=DPI if ext=='png' else None,
                bbox_inches='tight', facecolor='white', edgecolor='none')
print("✓ Saved: Figure1_pipeline.png (300 dpi) + .pdf")
print(f"  Canvas: {FIG_W}×{FIG_H} in = {FIG_W*2.54:.1f}×{FIG_H*2.54:.1f} cm")