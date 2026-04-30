# -*- coding: utf-8 -*-
"""
Last Digit Test - HLTV Rating 3.0 Forensic Analysis
=====================================================
H0: ZywOo's rating last-digit distribution is not significantly different
    from other top players.
H1: A systematic bias exists (possible indicator of data manipulation).

Methods:
  1. Extract last digit of each rating (round(r*100) mod 10)
  2. Chi-square goodness-of-fit test vs uniform distribution
  3. Chi-square independence test: ZywOo vs all others combined
  4. KL divergence (information-theoretic distance from uniform)
  5. Visualisations
"""

import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

import json
import os
import numpy as np
from scipy.stats import chisquare, chi2_contingency
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import Counter

# ── Configuration ──────────────────────────────────────────────
DATA_DIR   = "data"
OUTPUT_DIR = "output"
os.makedirs(OUTPUT_DIR, exist_ok=True)

plt.rcParams.update({
    "figure.facecolor": "#0d1117",
    "axes.facecolor":   "#161b22",
    "axes.edgecolor":   "#30363d",
    "axes.labelcolor":  "#c9d1d9",
    "xtick.color":      "#c9d1d9",
    "ytick.color":      "#c9d1d9",
    "text.color":       "#c9d1d9",
    "grid.color":       "#21262d",
    "grid.alpha":       0.6,
    "font.family":      "DejaVu Sans",
    "font.size":        10,
})

ZYWOO_COLOR   = "#f78166"
OTHERS_COLOR  = "#58a6ff"
UNIFORM_COLOR = "#3fb950"
GRID_ALPHA    = 0.5


# ── Core functions ─────────────────────────────────────────────

def extract_last_digit(r: float) -> int:
    return int(round(r * 100)) % 10


def load_data() -> dict[str, list[float]]:
    data = {}
    for fname in sorted(os.listdir(DATA_DIR)):
        if fname.endswith("_ratings.json"):
            player = fname.replace("_ratings.json", "")
            with open(os.path.join(DATA_DIR, fname)) as f:
                ratings = json.load(f)
            if ratings:
                data[player] = ratings
                print(f"  Loaded {player}: {len(ratings)} entries")
    return data


def digit_counts(ratings: list[float]) -> np.ndarray:
    c = np.zeros(10, dtype=int)
    for r in ratings:
        c[extract_last_digit(r)] += 1
    return c


def chi_uniform_test(counts: np.ndarray, player: str) -> dict:
    n = counts.sum()
    expected = np.full(10, n / 10.0)
    chi2, p = chisquare(counts, expected)
    return dict(player=player, n=int(n), chi2=float(chi2), p_value=float(p),
                significant=(p < 0.05), counts=counts)


def kl_div(counts: np.ndarray) -> float:
    probs = counts / counts.sum()
    probs = np.where(probs == 0, 1e-10, probs)
    return float(np.sum(probs * np.log(probs / 0.1)))


def independence_test(cz: np.ndarray, co: np.ndarray) -> dict:
    chi2, p, dof, _ = chi2_contingency(np.vstack([cz, co]))
    return dict(chi2=float(chi2), p_value=float(p), dof=int(dof),
                significant=(p < 0.05))


# ── Plots ──────────────────────────────────────────────────────

def plot_per_player(all_counts: dict[str, np.ndarray], results: dict):
    players = list(all_counts.keys())
    n = len(players)
    n_cols = 3
    n_rows = (n + n_cols - 1) // n_cols

    fig, axes = plt.subplots(n_rows, n_cols,
                             figsize=(16, 4.5 * n_rows),
                             facecolor="#0d1117")
    fig.suptitle("HLTV Rating 3.0 — Last Digit Distribution\n"
                 "Last Digit Test for Data Manipulation",
                 fontsize=15, fontweight="bold", color="#f0f6fc", y=0.99)

    flat = axes.flatten() if hasattr(axes, "flatten") else [axes]

    digits = np.arange(10)
    uniform = np.full(10, 10.0)

    for i, player in enumerate(players):
        ax = flat[i]
        counts = all_counts[player]
        pct    = counts / counts.sum() * 100
        res    = results.get(player, {})
        is_z   = (player == "ZywOo")
        color  = ZYWOO_COLOR if is_z else OTHERS_COLOR

        bars = ax.bar(digits, pct, color=color, alpha=0.85,
                      edgecolor="#ffffff22", linewidth=0.5, zorder=3)
        ax.step(np.append(digits - 0.5, 9.5),
                np.append(uniform, uniform[-1]),
                where="post", color=UNIFORM_COLOR,
                linewidth=1.5, linestyle="--", label="Uniform 10%", zorder=4)

        for bar, val in zip(bars, pct):
            ax.text(bar.get_x() + bar.get_width() / 2,
                    bar.get_height() + 0.3,
                    f"{val:.1f}%", ha="center", va="bottom",
                    fontsize=7, color="#c9d1d9")

        p_val  = res.get("p_value", 1.0)
        kl     = res.get("kl", 0.0)
        nn     = res.get("n", 0)
        sig    = "[p<0.05 ANOMALOUS]" if p_val < 0.05 else "[Normal]"
        prefix = "*** " if is_z else ""
        ax.set_title(f"{prefix}{player}  n={nn}\n"
                     f"chi2={res.get('chi2',0):.2f}  p={p_val:.4f}  "
                     f"KL={kl:.4f}  {sig}",
                     color=ZYWOO_COLOR if is_z else "#c9d1d9",
                     fontsize=9, fontweight="bold" if is_z else "normal")

        ax.set_xlabel("Last digit (hundredths place)", fontsize=8)
        ax.set_ylabel("Frequency (%)", fontsize=8)
        ax.set_xticks(digits)
        ax.set_ylim(0, max(float(pct.max()) * 1.3, 17))
        ax.grid(axis="y", alpha=GRID_ALPHA)
        ax.legend(fontsize=7, loc="upper right")
        ax.set_facecolor("#161b22")

    for i in range(n, len(flat)):
        flat[i].set_visible(False)

    plt.tight_layout(rect=[0, 0, 1, 0.97])
    out = os.path.join(OUTPUT_DIR, "last_digit_per_player.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Saved: {out}")
    plt.close()


def plot_zywoo_vs_others(cz: np.ndarray, co: np.ndarray, indep: dict):
    digits = np.arange(10)
    pz = cz / cz.sum() * 100
    po = co / co.sum() * 100

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(16, 6), facecolor="#0d1117")
    fig.suptitle("ZywOo vs Other Top Players — Last Digit Comparison",
                 fontsize=14, fontweight="bold", color="#f0f6fc")

    w = 0.38
    ax1.bar(digits - w/2, pz, w, color=ZYWOO_COLOR, alpha=0.85,
            label=f"ZywOo (n={cz.sum()})", zorder=3)
    ax1.bar(digits + w/2, po, w, color=OTHERS_COLOR, alpha=0.85,
            label=f"Others (n={co.sum()})", zorder=3)
    ax1.axhline(10, color=UNIFORM_COLOR, linestyle="--",
                linewidth=1.5, label="Uniform 10%", zorder=4)

    p = indep["p_value"]
    verdict = "[SIGNIFICANT DIFFERENCE p<0.05]" if p < 0.05 \
              else "[No significant difference]"
    ax1.set_title(f"Side-by-Side\nIndependence chi2={indep['chi2']:.3f}  "
                  f"df={indep['dof']}  p={p:.4f}\n{verdict}",
                  fontsize=10, color="#f0f6fc")
    ax1.set_xlabel("Last Digit"); ax1.set_ylabel("Frequency (%)")
    ax1.set_xticks(digits); ax1.legend()
    ax1.grid(axis="y", alpha=GRID_ALPHA); ax1.set_facecolor("#161b22")

    diff = pz - po
    colors = [ZYWOO_COLOR if d > 0 else OTHERS_COLOR for d in diff]
    bars = ax2.bar(digits, diff, color=colors, alpha=0.85,
                   edgecolor="#ffffff22", zorder=3)
    ax2.axhline(0, color="#c9d1d9", linewidth=1)
    for bar, val in zip(bars, diff):
        ax2.text(bar.get_x() + bar.get_width() / 2,
                 val + (0.15 if val >= 0 else -0.4),
                 f"{val:+.1f}%", ha="center",
                 va="bottom" if val >= 0 else "top",
                 fontsize=8, color="#c9d1d9")

    ax2.set_title("Difference: ZywOo% - Others%\n"
                  "(red = ZywOo higher, blue = ZywOo lower)",
                  fontsize=10, color="#f0f6fc")
    ax2.set_xlabel("Last Digit"); ax2.set_ylabel("Delta (%)")
    ax2.set_xticks(digits)
    ax2.grid(axis="y", alpha=GRID_ALPHA); ax2.set_facecolor("#161b22")

    plt.tight_layout(rect=[0, 0, 1, 0.93])
    out = os.path.join(OUTPUT_DIR, "zywoo_vs_others.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Saved: {out}")
    plt.close()


def plot_summary_table(results: list[dict], indep: dict):
    sorted_res = sorted(results, key=lambda x: x["p_value"])
    rows = []
    for r in sorted_res:
        verdict = "[ANOMALOUS p<0.05]" if r["p_value"] < 0.05 else "[Normal]"
        rows.append([r["player"], str(r["n"]),
                     f"{r['chi2']:.3f}", f"{r['p_value']:.4f}",
                     f"{r['kl']:.5f}", verdict])

    fig, ax = plt.subplots(figsize=(14, len(results) * 0.75 + 2.5),
                           facecolor="#0d1117")
    ax.set_facecolor("#0d1117"); ax.axis("off")

    col_labels = ["Player", "N", "chi2 vs Uniform", "p-value", "KL Div.", "Verdict"]
    tbl = ax.table(cellText=rows, colLabels=col_labels,
                   loc="center", cellLoc="center")
    tbl.auto_set_font_size(False); tbl.set_fontsize(10); tbl.scale(1.2, 2.2)

    for (row, col), cell in tbl.get_celld().items():
        cell.set_edgecolor("#30363d")
        if row == 0:
            cell.set_facecolor("#21262d")
            cell.set_text_props(color="#f0f6fc", fontweight="bold")
        else:
            player_name = rows[row - 1][0]
            if player_name == "ZywOo":
                cell.set_facecolor("#3d1f1f")
                cell.set_text_props(color=ZYWOO_COLOR)
            else:
                cell.set_facecolor("#161b22" if row % 2 == 0 else "#1c2128")
                cell.set_text_props(color="#c9d1d9")

    p_ind = indep["p_value"]
    footer = (f"ZywOo vs Others Independence Test:  "
              f"chi2={indep['chi2']:.3f}  df={indep['dof']}  p={p_ind:.4f}  "
              + ("[SIGNIFICANT p<0.05]" if p_ind < 0.05 else "[Not Significant]"))
    ax.text(0.5, 0.02, footer, transform=ax.transAxes,
            ha="center", va="bottom", fontsize=9,
            color=ZYWOO_COLOR if p_ind < 0.05 else UNIFORM_COLOR)

    ax.set_title("Last Digit Test — Summary\n"
                 "(Chi-square test vs uniform distribution; Rating 3.0 only)",
                 fontsize=13, fontweight="bold", color="#f0f6fc", pad=20)

    plt.tight_layout()
    out = os.path.join(OUTPUT_DIR, "summary_table.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Saved: {out}")
    plt.close()


def plot_digit_heatmap(all_counts: dict[str, np.ndarray], results: list[dict]):
    """
    Heatmap table: rows = last digit 0-9, columns = players.
    Cell colour encodes deviation from uniform 10%.
    Green = above average, Red = below average.
    """
    players = list(all_counts.keys())
    n_players = len(players)

    # Build percentage matrix  shape (10, n_players)
    mat = np.zeros((10, n_players))
    for j, player in enumerate(players):
        counts = all_counts[player]
        mat[:, j] = counts / counts.sum() * 100

    fig, ax = plt.subplots(figsize=(3 + 1.6 * n_players, 7), facecolor="#0d1117")
    ax.set_facecolor("#0d1117")

    # Colour map: centre at 10% (uniform), red=low, green=high
    import matplotlib.colors as mcolors
    cmap = mcolors.LinearSegmentedColormap.from_list(
        "rg", ["#f78166", "#161b22", "#3fb950"]
    )
    norm = mcolors.TwoSlopeNorm(vmin=4, vcenter=10, vmax=17)

    # Draw cells
    for j, player in enumerate(players):
        for i in range(10):
            val = mat[i, j]
            color = cmap(norm(val))
            rect = plt.Rectangle([j, 9 - i], 1, 1,
                                  facecolor=color, edgecolor="#0d1117", linewidth=1.5)
            ax.add_patch(rect)

            delta = val - 10.0
            delta_str = f"{delta:+.1f}%" if abs(delta) >= 0.5 else ""
            ax.text(j + 0.5, 9 - i + 0.62, f"{val:.1f}%",
                    ha="center", va="center", fontsize=9.5,
                    color="#f0f6fc", fontweight="bold")
            ax.text(j + 0.5, 9 - i + 0.28, delta_str,
                    ha="center", va="center", fontsize=7.5,
                    color="#f0f6fc" if abs(delta) < 2 else "#ffa657")

    # Column headers (player names + stats)
    result_map = {r["player"]: r for r in results}
    for j, player in enumerate(players):
        res = result_map.get(player, {})
        p_val = res.get("p_value", 1.0)
        sig = "*" if p_val < 0.05 else ""
        color = ZYWOO_COLOR if player == "ZywOo" else (
            "#ffa657" if p_val < 0.05 else "#c9d1d9")
        ax.text(j + 0.5, 10.5, f"{player}{sig}",
                ha="center", va="center", fontsize=10,
                fontweight="bold", color=color)
        ax.text(j + 0.5, 10.1, f"n={res.get('n',0)}  p={p_val:.3f}",
                ha="center", va="center", fontsize=7.5, color="#8b949e")

    # Row labels (digits)
    for i in range(10):
        ax.text(-0.15, 9 - i + 0.5, str(i),
                ha="right", va="center", fontsize=11,
                fontweight="bold", color="#c9d1d9")

    # Uniform reference line annotation
    ax.axvline(x=0, color="#30363d", linewidth=0)
    ax.set_xlim(-0.3, n_players)
    ax.set_ylim(-0.5, 11.2)
    ax.axis("off")

    # Colour bar
    sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
    sm.set_array([])
    cbar = fig.colorbar(sm, ax=ax, orientation="vertical",
                        fraction=0.025, pad=0.02, aspect=30)
    cbar.set_label("Frequency %  (uniform = 10%)", color="#c9d1d9", fontsize=9)
    cbar.ax.yaxis.set_tick_params(color="#c9d1d9")
    plt.setp(cbar.ax.yaxis.get_ticklabels(), color="#c9d1d9", fontsize=8)

    fig.suptitle("Last Digit Probability Table — HLTV Rating 3.0\n"
                 "(*) = anomalous p<0.05  |  delta vs uniform 10% shown below each cell",
                 fontsize=12, fontweight="bold", color="#f0f6fc", y=0.98)

    plt.tight_layout(rect=[0, 0, 1, 0.95])
    out = os.path.join(OUTPUT_DIR, "digit_heatmap_table.png")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"  Saved: {out}")
    plt.close()


# ── Main ───────────────────────────────────────────────────────

def main():
    print("=" * 60)
    print("  HLTV Rating 3.0 — Last Digit Forensic Test")
    print("=" * 60)

    print("\n[1] Loading data...")
    all_data = load_data()

    if not all_data:
        print("ERROR: No data found in data/ directory.")
        return
    if "ZywOo" not in all_data:
        print("ERROR: ZywOo data missing.")
        return

    print(f"\n  Players with data: {list(all_data.keys())}")

    print("\n[2] Computing last-digit distributions...")
    all_counts = {}
    for player, ratings in all_data.items():
        all_counts[player] = digit_counts(ratings)

    print("\n[3] Chi-square goodness-of-fit (vs uniform)...")
    results = []
    for player, counts in all_counts.items():
        res = chi_uniform_test(counts, player)
        res["kl"] = kl_div(counts)
        results.append(res)
        flag = "[p<0.05 ANOMALOUS]" if res["significant"] else "[Normal]"
        print(f"  {player:15s}: chi2={res['chi2']:7.3f}  p={res['p_value']:.4f}  "
              f"KL={res['kl']:.5f}  {flag}")

    print("\n[4] Chi-square independence test (ZywOo vs all others combined)...")
    cz = all_counts["ZywOo"]
    co = sum(v for k, v in all_counts.items() if k != "ZywOo")
    indep = independence_test(cz, co)
    print(f"  chi2={indep['chi2']:.3f}  df={indep['dof']}  p={indep['p_value']:.4f}")
    if indep["significant"]:
        print("  *** SIGNIFICANT: ZywOo's digit distribution differs from peers! ***")
    else:
        print("  Not significant: no anomaly detected vs peers.")

    print("\n[5] Generating plots...")
    plot_per_player(all_counts, {r["player"]: r for r in results})
    plot_zywoo_vs_others(cz, co, indep)
    plot_summary_table(results, indep)
    plot_digit_heatmap(all_counts, results)

    print("\n" + "=" * 60)
    print("  INTERPRETATION GUIDE")
    print("=" * 60)
    print("""
p < 0.05  -> Statistically anomalous at 95% confidence
p < 0.01  -> Statistically anomalous at 99% confidence
KL div    -> Information distance from perfect uniform (higher = more unusual)

IMPORTANT CAVEATS:
  1. HLTV Rating is computed by formula, NOT entered manually.
     Last-digit non-uniformity can arise from the formula itself,
     not only from human manipulation.
  2. A significant result does NOT prove manipulation.
     It only shows the distribution is unusual.
  3. A non-significant result does NOT prove the data is clean.

EVIDENCE STRENGTH:
  Strong   = ZywOo anomalous + all others normal
  Moderate = ZywOo anomalous + some others also anomalous
  None     = ZywOo not anomalous, OR all players anomalous equally
""")
    print(f"Charts saved to: {os.path.abspath(OUTPUT_DIR)}/")


if __name__ == "__main__":
    main()
