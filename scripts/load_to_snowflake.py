#!/usr/bin/env python3
"""Load downloaded TLC files into Snowflake RAW tables.

    python scripts/load_to_snowflake.py --year 2023 --data-dir data/raw

Steps: PUT parquet files to an internal stage -> COPY INTO raw.yellow_trips_raw
(MATCH_BY_COLUMN_NAME, with the source file name recorded) -> reload the zone lookup.

Re-running is safe: COPY INTO skips files it has already loaded (Snowflake keeps
load history for 64 days), so trips are not duplicated.
"""
import argparse
import sys
from pathlib import Path

from snowflake_conn import connect


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2023)
    parser.add_argument("--data-dir", type=Path, default=Path("data/raw"))
    args = parser.parse_args()

    trip_files = sorted(args.data_dir.glob(f"yellow_tripdata_{args.year}-*.parquet"))
    zone_file = args.data_dir / "taxi_zone_lookup.csv"
    if not trip_files:
        print(f"No parquet files for {args.year} in {args.data_dir}. Run scripts/download_tlc.py first.", file=sys.stderr)
        return 1
    if not zone_file.exists():
        print(f"{zone_file} not found. Run scripts/download_tlc.py first.", file=sys.stderr)
        return 1

    conn = connect("RAW")
    cur = conn.cursor()
    try:
        stage_path = f"@raw.tlc_stage/yellow/{args.year}/"

        for path in trip_files:
            print(f"PUT {path.name}")
            cur.execute(
                f"PUT 'file://{path.resolve().as_posix()}' {stage_path} "
                "AUTO_COMPRESS=FALSE OVERWRITE=TRUE PARALLEL=8"
            )

        print("COPY INTO raw.yellow_trips_raw ...")
        cur.execute(
            f"""
            COPY INTO raw.yellow_trips_raw
            FROM {stage_path}
            FILE_FORMAT = (FORMAT_NAME = 'raw.tlc_parquet')
            MATCH_BY_COLUMN_NAME = CASE_INSENSITIVE
            INCLUDE_METADATA = (source_file = METADATA$FILENAME)
            ON_ERROR = ABORT_STATEMENT
            """
        )
        for row in cur.fetchall():
            print("  ", row[0], row[1], "rows" if len(row) > 3 else "")

        print("Reloading raw.taxi_zone_lookup ...")
        cur.execute(
            f"PUT 'file://{zone_file.resolve().as_posix()}' @raw.zone_stage AUTO_COMPRESS=FALSE OVERWRITE=TRUE"
        )
        cur.execute("TRUNCATE TABLE raw.taxi_zone_lookup")
        cur.execute(
            """
            COPY INTO raw.taxi_zone_lookup
            FROM @raw.zone_stage
            FILE_FORMAT = (FORMAT_NAME = 'raw.zone_csv')
            FORCE = TRUE
            """
        )

        print("\nRows loaded per source file:")
        cur.execute(
            "SELECT source_file, COUNT(*) FROM raw.yellow_trips_raw GROUP BY 1 ORDER BY 1"
        )
        total = 0
        for source_file, n in cur.fetchall():
            print(f"  {source_file}: {n:,}")
            total += n
        print(f"TOTAL raw trips: {total:,}")

        cur.execute("SELECT COUNT(*) FROM raw.taxi_zone_lookup")
        print(f"Zone lookup rows: {cur.fetchone()[0]}")
    finally:
        cur.close()
        conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
