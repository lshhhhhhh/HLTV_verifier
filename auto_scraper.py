# -*- coding: utf-8 -*-
"""
auto_scraper.py — Automatic HLTV Rating 3.0 scraper using DrissionPage.

DrissionPage takes over your real Chrome browser, so Cloudflare sees a
normal human user. You may be asked to solve a CAPTCHA once on first run;
after that the session is reused.

Usage:
    .venv\Scripts\python.exe auto_scraper.py

The script will:
  1. Open Chrome (you'll see the window)
  2. Visit each player's stats page, paginating automatically
  3. Skip ratings marked with * (pre-3.0)
  4. Save <Player>_ratings.json to data/ after each player
  5. When done, print a summary

Add/remove players from the PLAYERS dict below.
"""

import sys, io, os, json, time, re
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")

from DrissionPage import ChromiumPage, ChromiumOptions

# ── Player list ────────────────────────────────────────────────
# Format:  "DisplayName": (player_id, url_slug)
# To find IDs: visit hltv.org/player/XXXX/name and copy XXXX
PLAYERS = {
    # Original 10
    "ZywOo":   (11893, "zywoo"),
    "NiKo":    (3741,  "niko"),
    "donk":    (21167, "donk"),
    "malbsMd": (11617, "malbsmd"),
    "sh1ro":   (16920, "sh1ro"),
    "Ax1Le":   (16555, "ax1le"),
    "b1t":     (18987, "b1t"),
    "Jame":    (13776, "jame"),
    "device":  (7592,  "device"),
    "s1mple":  (7998,  "s1mple"),
    
    # New 10 (Expanding to 20)
    "m0NESY":  (19230, "m0nesy"),
    "ropz":    (11816, "ropz"),
    "Twistzz": (10394, "twistzz"),
    "karrigan":(429,   "karrigan"),
    "apEX":    (7322,  "apex"),
    "Spinx":   (18221, "spinx"),
    "EliGE":   (8738,  "elige"),
    "NAF":     (8520,  "naf"),
    "Magisk":  (9032,  "magisk"),
    "Snappi":  (922,   "snappi"),
}

RANKING_FILTER = "Top50"   # Top5 / Top10 / Top20 / Top30 / Top50 / (blank=All)
START_DATE     = "2024-01-01"  # Rating 3.0 was introduced in Jan 2024.
                               # All matches from this date onward use Rating 3.0.
                               # This prevents HLTV from showing the Rating 2.0 column.
PAGE_SIZE      = 100       # HLTV shows 100 rows per page
MAX_PAGES      = 20        # safety cap (20 × 100 = 2000 rows per player)
PAGE_DELAY     = 3.0       # seconds between page requests (be polite)
CF_WAIT        = 30        # seconds to wait for Cloudflare to clear

# Set to True to skip players that already have a data file in DATA_DIR.
# Existing data is preserved and the player is not re-scraped.
# Set to False to always overwrite.
SKIP_IF_EXISTS = True

DATA_DIR = "data"
os.makedirs(DATA_DIR, exist_ok=True)


def build_url(player_id: int, slug: str, offset: int = 0) -> str:
    base = f"https://www.hltv.org/stats/players/matches/{player_id}/{slug}"
    params = []
    if START_DATE:
        params.append(f"startDate={START_DATE}")
    if offset:
        params.append(f"offset={offset}")
    if RANKING_FILTER:
        params.append(f"rankingFilter={RANKING_FILTER}")
    return base + ("?" + "&".join(params) if params else "")


def wait_for_table(page, timeout: int = CF_WAIT) -> bool:
    """Wait until the HLTV stats table appears (Cloudflare clears).
    Uses the specific class so CF challenge pages don't fool us.
    """
    for i in range(timeout):
        try:
            # Must be the actual stats table, not a CF layout table
            if page.ele("css:table.stats-matches-table", timeout=1):
                return True
        except Exception:
            pass
        if i % 5 == 4:
            print(f"    Waiting for stats table... ({timeout-i}s left)")
        time.sleep(1)
    return False



# Unix timestamp (ms) for 2023-07-01 — safely before CS2 / Rating 3.0 launch
# (CS2 launched 2023-09-27; using an earlier date ensures no 3.0 data is missed)
RATING30_CUTOFF_MS = 1_688_169_600_000


def extract_ratings_from_page(page) -> tuple[list[float], bool, bool]:
    """
    Returns (ratings, has_more_pages, hit_old_data).

    Uses JavaScript to inspect EACH ROW's date timestamp alongside its rating.
    Rows dated before RATING30_CUTOFF_MS (2024-01-09) are skipped, and
    hit_old_data is set True so the caller stops pagination immediately.

    This is robust against:
      - Asterisked Rating 2.0 values in the Rating 3.0 column
      - A separate Rating 2.0 column (those rows have old timestamps)
    """
    js = """
    return (function() {
        var CUTOFF = """ + str(RATING30_CUTOFF_MS) + """;
        var rows = document.querySelectorAll(
            'table.stats-matches-table tbody tr'
        );
        var ratings = [];
        var hitOld = false;

        for (var i = 0; i < rows.length; i++) {
            var row = rows[i];

            var timeEl = row.querySelector('.time');
            if (!timeEl) continue;
            var unix = parseInt(timeEl.getAttribute('data-unix') || '0', 10);

            var rEl = row.querySelector('td.ratingPositive, td.ratingNegative');
            if (!rEl) continue;
            var txt = rEl.textContent.trim();

            if (txt.indexOf('*') !== -1) { hitOld = true; continue; }

            var val = parseFloat(txt);
            if (isNaN(val) || val < 0.3 || val > 3.5) continue;

            if (unix < CUTOFF) { hitOld = true; continue; }

            ratings.push(val);
        }

        var hasMore = !!document.querySelector('a.pagination-next:not(.inactive)');
        return JSON.stringify({ ratings: ratings, hitOld: hitOld, hasMore: hasMore });
    })();
    """

    try:
        raw = page.run_js(js)
        import json as _json
        data = _json.loads(raw)
        return data["ratings"], data["hasMore"], data["hitOld"]
    except Exception as e:
        # Print page title so we can see if CF blocked us
        try:
            title = page.title
        except Exception:
            title = "unknown"
        print(f"    JS error (page: '{title}'): {e}")
        return [], False, False


def scrape_player(page: ChromiumPage, name: str,
                  player_id: int, slug: str) -> list[float]:
    all_ratings: list[float] = []
    total_skipped = 0

    for page_num in range(MAX_PAGES):
        offset = page_num * PAGE_SIZE
        url = build_url(player_id, slug, offset)
        print(f"  Page {page_num + 1:2d}  offset={offset:5d}  {url}")

        page.get(url)

        if not wait_for_table(page):
            print(f"    ERROR: table never appeared, skipping page")
            break

        ratings, has_more, hit_old = extract_ratings_from_page(page)
        all_ratings.extend(ratings)

        print(f"    Got {len(ratings):3d} ratings  cumulative: {len(all_ratings)}")

        if hit_old:
            print(f"    Pre-2024 data reached — stopping (Rating 3.0 boundary).")
            break

        if not has_more:
            print(f"    Last page reached.")
            break

        time.sleep(PAGE_DELAY)

    return all_ratings


def main():
    print("=" * 60)
    print("  HLTV Auto-Scraper (DrissionPage)")
    print(f"  Players: {list(PLAYERS.keys())}")
    print(f"  Filter:  {RANKING_FILTER or 'All'}")
    print("=" * 60)
    print()
    print("Chrome will open. If you see a Cloudflare challenge,")
    print("solve it manually — the script will continue automatically.")
    print()

    # Launch Chrome (visible window so you can solve CF if needed)
    opts = ChromiumOptions()
    opts.set_argument("--start-maximized")
    # If you want headless (no window), uncomment:
    # opts.headless(True)   # WARNING: headless gets blocked by Cloudflare!

    page = ChromiumPage(addr_or_opts=opts)

    summary = {}
    try:
        for name, (pid, slug) in PLAYERS.items():
            print(f"\n{'='*55}")
            print(f"Player: {name}  (id={pid}, slug={slug})")
            print(f"{'='*55}")

            out_path = os.path.join(DATA_DIR, f"{name}_ratings.json")

            if SKIP_IF_EXISTS and os.path.exists(out_path):
                with open(out_path) as f:
                    existing = json.load(f)
                if existing:   # only skip when there is actual data
                    print(f"  SKIP — already have {len(existing)} entries in {out_path}")
                    summary[name] = len(existing)
                    continue
                print(f"  Found empty file, will re-scrape {name}.")

            ratings = scrape_player(page, name, pid, slug)
            summary[name] = len(ratings)

            # Save immediately after each player
            with open(out_path, "w") as f:
                json.dump(ratings, f)
            print(f"  Saved {len(ratings)} ratings -> {out_path}")

            # Pause between players
            if name != list(PLAYERS.keys())[-1]:
                wait = 5.0
                print(f"  Waiting {wait}s before next player...")
                time.sleep(wait)

    finally:
        page.quit()

    print(f"\n{'='*55}")
    print("DONE — Summary:")
    for name, count in summary.items():
        status = "OK" if count >= 100 else "LOW"
        print(f"  {name:15s}: {count:4d} entries  [{status}]")
    print(f"\nRun:  .venv\\Scripts\\python.exe analyze.py")


if __name__ == "__main__":
    main()
