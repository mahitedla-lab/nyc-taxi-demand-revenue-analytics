#!/usr/bin/env python3
"""Download NYC TLC yellow taxi trip files (Parquet) and the taxi zone lookup.

Usage:
    python scripts/download_tlc.py --year 2023 --out data/raw

Files are skipped if they already exist, so the script is safe to re-run.
"""
import argparse
import sys
import time
from pathlib import Path

import requests

BASE = "https://d37ci6vzurychx.cloudfront.net"
TRIP_URL = BASE + "/trip-data/yellow_tripdata_{year}-{month:02d}.parquet"
ZONE_URL = BASE + "/misc/taxi_zone_lookup.csv"


def download(url: str, dest: Path, retries: int = 3) -> bool:
    if dest.exists() and dest.stat().st_size > 0:
        print(f"skip      {dest.name} (already downloaded)")
        return True

    tmp = dest.with_suffix(dest.suffix + ".part")
    for attempt in range(1, retries + 1):
        try:
            with requests.get(url, stream=True, timeout=60) as resp:
                resp.raise_for_status()
                with open(tmp, "wb") as fh:
                    for chunk in resp.iter_content(chunk_size=1 << 20):
                        fh.write(chunk)
            tmp.rename(dest)
            size_mb = dest.stat().st_size / 1e6
            print(f"download  {dest.name} ({size_mb:,.1f} MB)")
            return True
        except requests.RequestException as exc:
            print(f"retry {attempt}/{retries}  {dest.name}: {exc}", file=sys.stderr)
            time.sleep(2 * attempt)

    print(f"FAILED    {dest.name}", file=sys.stderr)
    return False


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=2023, help="calendar year of trips (default: 2023)")
    parser.add_argument("--out", type=Path, default=Path("data/raw"), help="output directory")
    args = parser.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)

    ok = download(ZONE_URL, args.out / "taxi_zone_lookup.csv")
    for month in range(1, 13):
        url = TRIP_URL.format(year=args.year, month=month)
        ok &= download(url, args.out / f"yellow_tripdata_{args.year}-{month:02d}.parquet")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
