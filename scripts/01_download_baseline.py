"""
Step 1 of the pipeline: download regular-season Statcast data.

Downloads each season in month-sized chunks with pybaseball and saves one
parquet file per chunk to data/raw/. Files already on disk are reused
unless they look truncated. A manifest of every chunk is written to
data/raw/download_manifest.csv.

The script stops with an error if any date range could not be downloaded,
so 02_build_chase_dataset.py is never run on a dataset with holes in it.
"""

import time
from pathlib import Path

import pandas as pd
from pybaseball import statcast


# --------------------------------------------------
# SETTINGS
# --------------------------------------------------

# Paths are anchored to the project folder (the parent of scripts/), not
# to the directory the script is run from.
PROJECT_DIR = Path(__file__).resolve().parent

if not (PROJECT_DIR / "data").exists():
    PROJECT_DIR = PROJECT_DIR.parent

RAW_DIR = PROJECT_DIR / "data" / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

MANIFEST_FILE = RAW_DIR / "download_manifest.csv"

# 2025 opened with the Tokyo Series on March 18 (regular season), so the
# 2024 and 2025 windows start on March 15.
SEASONS = {
    2024: ("2024-03-15", "2024-11-03"),
    2025: ("2025-03-15", "2025-11-03"),
    2026: ("2026-03-20", "2026-11-03"),
}

# A complete April-September month has well over 100,000 pitches. A full
# month that comes back with fewer than this is almost certainly a
# truncated response from Savant.
MINIMUM_PITCHES_FULL_MONTH = 60000

FULL_MONTHS = [4, 5, 6, 7, 8, 9]

MAX_ATTEMPTS = 3


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def month_ranges(start_date, end_date):
    """Yield (start, end) timestamps, one calendar month at a time."""

    start = pd.Timestamp(start_date)
    end = pd.Timestamp(end_date)

    current = start

    while current <= end:

        month_end = current + pd.offsets.MonthEnd(0)

        if month_end > end:
            month_end = end

        yield current, month_end

        current = month_end + pd.Timedelta(days=1)


def is_a_full_month(start, end):
    """
    True only when this chunk covers a whole April-September month that
    has already finished.

    The "already finished" part matters during a season in progress: the
    current month cannot reach a full month's pitch count yet, so it should
    not be retried for being short or labelled full_month=True in the
    manifest.
    """

    if start.month not in FULL_MONTHS:
        return False

    if start.day != 1:
        return False

    last_day_of_month = start + pd.offsets.MonthEnd(0)

    if end != last_day_of_month:
        return False

    if end >= pd.Timestamp.today().normalize():
        return False

    return True


def count_rows_in_file(path):
    """Count rows by reading one column only. Returns -1 if unreadable."""

    try:
        small = pd.read_parquet(path, columns=["game_pk"])
        return len(small)

    except Exception as error:
        print(f"Could not read {path.name}: {error}")
        return -1


def manifest_row(season, start_string, end_string, full_month, pitches, source):
    """One row of the download manifest."""

    return {
        "season": season,
        "start_date": start_string,
        "end_date": end_string,
        "full_month": full_month,
        "pitches": pitches,
        "source": source
    }


def download_range(start_string, end_string, filename, full_month):
    """
    Download one date range with retries and save it to filename.

    Returns the number of pitches saved, or None if every attempt failed.
    A full month that is still short after the last attempt is saved
    anyway; the caller flags it as suspicious.
    """

    for attempt in range(1, MAX_ATTEMPTS + 1):

        try:

            df = statcast(
                start_dt=start_string,
                end_dt=end_string
            )

            print(f"Downloaded {len(df):,} pitches")

            if full_month and len(df) < MINIMUM_PITCHES_FULL_MONTH:

                print(
                    f"That is too few pitches for a full month "
                    f"(expected at least "
                    f"{MINIMUM_PITCHES_FULL_MONTH:,}). Retrying."
                )

                if attempt < MAX_ATTEMPTS:
                    time.sleep(15)
                    continue

            df.to_parquet(filename, index=False)

            print(f"Saved: {filename}")

            return len(df)

        except Exception as error:

            print(f"Attempt {attempt} failed:")
            print(error)

            if attempt < MAX_ATTEMPTS:
                print("Waiting 10 seconds before retrying...")
                time.sleep(10)

    return None


# --------------------------------------------------
# DOWNLOAD
# --------------------------------------------------

manifest_rows = []
failed_ranges = []
suspicious_files = []

for season, (season_start, season_end) in SEASONS.items():

    print()
    print("=" * 60)
    print(f"DOWNLOADING {season}")
    print("=" * 60)

    for start, end in month_ranges(season_start, season_end):

        start_string = start.strftime("%Y-%m-%d")
        end_string = end.strftime("%Y-%m-%d")

        filename = (
            RAW_DIR
            / f"statcast_{start_string}_{end_string}.parquet"
        )

        full_month = is_a_full_month(start, end)

        # ------------------------------------------
        # Reuse a file from a previous run unless it
        # looks truncated
        # ------------------------------------------

        if filename.exists():

            existing_rows = count_rows_in_file(filename)

            looks_truncated = (
                full_month
                and existing_rows < MINIMUM_PITCHES_FULL_MONTH
            )

            # Zero rows is a legitimate, already-fetched answer for a
            # chunk that is not a full month (an off-season sliver, or a
            # month not played yet). Without this, an empty range would be
            # deleted and re-requested on every run.
            looks_legitimately_empty = (
                not full_month
                and existing_rows == 0
            )

            if (
                (not looks_truncated and existing_rows > 0)
                or looks_legitimately_empty
            ):

                print(
                    f"Already have {filename.name} "
                    f"({existing_rows:,} pitches)"
                )

                manifest_rows.append(
                    manifest_row(
                        season,
                        start_string,
                        end_string,
                        full_month,
                        existing_rows,
                        "cached"
                    )
                )

                continue

            print()
            print(
                f"{filename.name} only has {existing_rows:,} pitches "
                f"for a full month. Deleting and downloading again."
            )

            filename.unlink()

        # ------------------------------------------
        # Download with retries
        # ------------------------------------------

        print()
        print(f"Downloading {start_string} through {end_string}...")

        downloaded_rows = download_range(
            start_string,
            end_string,
            filename,
            full_month
        )

        if downloaded_rows is None:

            print(
                f"FAILED permanently: "
                f"{start_string} through {end_string}"
            )

            failed_ranges.append((start_string, end_string))

        else:

            if full_month and downloaded_rows < MINIMUM_PITCHES_FULL_MONTH:
                suspicious_files.append(
                    (filename.name, downloaded_rows)
                )

            manifest_rows.append(
                manifest_row(
                    season,
                    start_string,
                    end_string,
                    full_month,
                    downloaded_rows,
                    "downloaded"
                )
            )

        # Be polite to Baseball Savant
        time.sleep(2)


# --------------------------------------------------
# MANIFEST
# --------------------------------------------------

manifest = pd.DataFrame(manifest_rows)

manifest = manifest.sort_values("start_date")

manifest.to_csv(MANIFEST_FILE, index=False)

print()
print("=" * 60)
print("DOWNLOAD MANIFEST")
print("=" * 60)
print(manifest.to_string(index=False))

print()
print("Pitches per season:")
print(manifest.groupby("season")["pitches"].sum())

# Rough expectation: a full regular season is around 700,000 pitches once
# postseason and spring training are filtered out in script 03.


# --------------------------------------------------
# STOP LOUDLY IF THE DATASET HAS HOLES
# --------------------------------------------------

if suspicious_files:

    print()
    print("These full months look short:")

    for name, rows in suspicious_files:
        print(f"  {name}: {rows:,} pitches")

if failed_ranges:

    print()
    print("These date ranges never downloaded:")

    for start_string, end_string in failed_ranges:
        print(f"  {start_string} through {end_string}")

    raise RuntimeError(
        "Download is incomplete. Do not run 03 until every range "
        "above has been downloaded, or the cleaned dataset will "
        "silently be missing games."
    )

print()
print("Baseline download complete.")
