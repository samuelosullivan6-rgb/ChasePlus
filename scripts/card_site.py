"""
The card site's season folders. Steps 17 and 21 write one page per season
into results/xchase/player_cards/<season>/ and share three small things:

  built_seasons(page)   the seasons that already have that page
  write_seasons_js()    player_cards/seasons.js, the list every season's
                        pages read for their season switcher
  write_redirect(page)  player_cards/<page>, which sends the old address
                        to the newest season's page, keeping the hitter
                        in the URL hash and any query string
"""

import re
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
CARDS_DIR = PROJECT_DIR / "results" / "xchase" / "player_cards"
SEASON_RE = re.compile(r"^\d{4}$")


def built_seasons(page):
    """Seasons with player_cards/<season>/<page> on disk, oldest first."""
    return sorted(int(d.name) for d in CARDS_DIR.iterdir()
                  if d.is_dir() and SEASON_RE.match(d.name) and (d / page).exists())


def write_seasons_js(*extra):
    """Every season with a cards page or a team page, plus any given
    (the one being built, whose page may not be written yet)."""
    seasons = sorted(set(built_seasons("index.html")) | set(built_seasons("teams.html")) | set(extra))
    (CARDS_DIR / "seasons.js").write_text(
        "// Written by steps 17 and 21: the seasons with a page in this folder.\n"
        f"window.CHASE_SEASONS = {seasons};\n")
    return seasons


def write_redirect(page, season, title):
    """player_cards/<page> -> <season>/<page>, hash and query kept."""
    target = f"{season}/{page}"
    (CARDS_DIR / page).write_text(f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="color-scheme" content="light dark">
<meta name="robots" content="noindex">
<title>{title}</title>
<script>location.replace("{target}" + location.search + location.hash);</script>
<meta http-equiv="refresh" content="0; url={target}">
<p style="font-family: system-ui, sans-serif; padding: 24px">One page per season now.
The newest is <a href="{target}">{target}</a>; the season switcher is on the page.</p>
</html>
""")
