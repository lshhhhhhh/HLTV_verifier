import os
import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path

# Paths
DATA_DIR = "data"
OUTPUT_DIR = "output"

def load_data():
    all_ratings = {}
    if not os.path.exists(DATA_DIR):
        return all_ratings
        
    for file in os.listdir(DATA_DIR):
        if file.endswith("_ratings.json"):
            player = file.replace("_ratings.json", "")
            with open(os.path.join(DATA_DIR, file), "r", encoding="utf-8") as f:
                data = json.load(f)
                
            # Extract valid rating values
            ratings = []
            for item in data:
                if isinstance(item, dict):
                    r = item.get("rating_3")
                else:
                    r = item
                if r is not None and str(r).replace(".", "").replace("*", "").isdigit():
                    ratings.append(float(str(r).replace("*", "")))
            
            if len(ratings) > 0:
                all_ratings[player] = np.array(ratings)
                print(f"  Loaded {player}: {len(ratings)} entries")
                
    return all_ratings

def plot_kde_cliffs(all_ratings):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    players = sorted(list(all_ratings.keys()))
    n_players = len(players)
    
    # Calculate grid size
    cols = 4
    rows = (n_players + cols - 1) // cols
    
    # Set style
    plt.style.use('dark_background')
    sns.set_context("paper")
    
    fig, axes = plt.subplots(rows, cols, figsize=(cols * 4.5, rows * 3.5))
    axes = axes.flatten()
    
    for i, player in enumerate(players):
        ax = axes[i]
        ratings = all_ratings[player]
        
        # Plot precise histogram (bin width = 0.05 to smooth out the 0.01 granularity while showing cliffs)
        bins = np.arange(0.3, 2.5, 0.05)
        
        # Use seaborn for KDE and hist
        sns.histplot(ratings, bins=bins, kde=False, stat="density", 
                     color="#30363d", edgecolor="#8b949e", ax=ax, alpha=0.7)
        
        sns.kdeplot(ratings, color="#3fb950" if player != "ZywOo" else "#f78166", 
                    linewidth=2, ax=ax, bw_adjust=0.5) # bw_adjust < 1 makes it more sensitive to sharp cliffs
        
        # Mean line
        mean_val = np.mean(ratings)
        ax.axvline(mean_val, color="white", linestyle="--", alpha=0.5, linewidth=1)
        
        # Annotate
        ax.set_title(f"{player} (n={len(ratings)})", color="white", fontweight="bold")
        ax.set_xlim(0.5, 2.2)
        ax.set_xlabel("Rating 3.0" if i >= len(players) - cols else "")
        ax.set_ylabel("Density" if i % cols == 0 else "")
        
        # Turn off spines
        for spine in ax.spines.values():
            spine.set_color('#30363d')
            
    # Hide empty subplots
    for i in range(n_players, len(axes)):
        axes[i].axis("off")
        
    plt.suptitle("KDE & Histogram 'Cliff' Analysis — HLTV Rating 3.0", 
                 fontsize=18, fontweight="bold", y=0.98, color="white")
    
    plt.tight_layout(rect=[0, 0, 1, 0.96])
    
    out_path = os.path.join(OUTPUT_DIR, "kde_cliffs_all.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"\n  Saved All Players KDE plot: {out_path}")
    plt.close()

def plot_zywoo_vs_others(all_ratings):
    """Deep dive comparison of ZywOo vs a few key players on a single plot"""
    plt.figure(figsize=(10, 6), facecolor="#0d1117")
    ax = plt.gca()
    ax.set_facecolor("#0d1117")
    
    compare_players = ["ZywOo", "NiKo", "donk", "m0NESY", "Jame"]
    colors = {
        "ZywOo": "#f78166",  # Red/Orange
        "NiKo": "#58a6ff",   # Blue
        "donk": "#3fb950",   # Green
        "m0NESY": "#d2a8ff", # Purple
        "Jame": "#e3b341"    # Yellow
    }
    
    for player in compare_players:
        if player in all_ratings:
            ratings = all_ratings[player]
            sns.kdeplot(ratings, label=f"{player} (Mean: {np.mean(ratings):.2f})", 
                        color=colors[player], linewidth=2.5 if player == "ZywOo" else 1.5,
                        ax=ax, bw_adjust=0.6)
            
    # Styling
    ax.set_title("Distribution Shape Comparison (KDE)\nAre there unnatural cliffs or bumps?", 
                 color="white", fontsize=14, pad=15)
    ax.set_xlim(0.6, 2.0)
    ax.set_xlabel("Rating 3.0", color="white", fontsize=12)
    ax.set_ylabel("Density", color="white", fontsize=12)
    
    ax.tick_params(colors="white")
    for spine in ax.spines.values():
        spine.set_color('#30363d')
        
    plt.legend(facecolor="#161b22", edgecolor="#30363d", labelcolor="white")
    
    out_path = os.path.join(OUTPUT_DIR, "kde_zywoo_vs_key_players.png")
    plt.savefig(out_path, dpi=150, bbox_inches="tight")
    print(f"  Saved Comparison KDE plot: {out_path}")
    plt.close()

if __name__ == "__main__":
    print("============================================================")
    print("  Running KDE & Histogram Cliff Analysis")
    print("============================================================")
    ratings = load_data()
    if ratings:
        plot_kde_cliffs(ratings)
        plot_zywoo_vs_others(ratings)
        print("Done!")
    else:
        print("No data found!")
