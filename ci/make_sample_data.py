#!/usr/bin/env python3
"""Build a SYNTHETIC sample database for CI and local smoke tests.

This is NOT real TLC data. It mimics the raw table layout (raw.yellow_trips_raw and
raw.taxi_zone_lookup) so the whole dbt project can run on DuckDB without Snowflake or a
multi-gigabyte download. Zone IDs/names loosely resemble the TLC lookup.

Known bad records are planted for every data-quality rule, and the expected number of
rows each rule should catch is written to ci/expected_dq_counts.json so
ci/verify_dq_counts.py can prove the rules work.

    python ci/make_sample_data.py
"""
import json
from pathlib import Path

import duckdb
import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
DB_PATH = HERE / "sample.duckdb"
EXPECTED_PATH = HERE / "expected_dq_counts.json"

RNG = np.random.default_rng(42)
N_GOOD = 20_000

ZONES = [
    (1, "EWR", "Newark Airport", "EWR"),
    (3, "Bronx", "Allerton/Pelham Gardens", "Boro Zone"),
    (4, "Manhattan", "Alphabet City", "Yellow Zone"),
    (7, "Queens", "Astoria", "Boro Zone"),
    (12, "Manhattan", "Battery Park", "Yellow Zone"),
    (17, "Brooklyn", "Bedford", "Boro Zone"),
    (33, "Brooklyn", "Brooklyn Heights", "Boro Zone"),
    (43, "Manhattan", "Central Park", "Yellow Zone"),
    (68, "Manhattan", "East Chelsea", "Yellow Zone"),
    (79, "Manhattan", "East Village", "Yellow Zone"),
    (100, "Manhattan", "Garment District", "Yellow Zone"),
    (132, "Queens", "JFK Airport", "Airports"),
    (138, "Queens", "LaGuardia Airport", "Airports"),
    (161, "Manhattan", "Midtown Center", "Yellow Zone"),
    (162, "Manhattan", "Midtown East", "Yellow Zone"),
    (181, "Brooklyn", "Park Slope", "Boro Zone"),
    (230, "Manhattan", "Times Sq/Theatre District", "Yellow Zone"),
    (236, "Manhattan", "Upper East Side North", "Yellow Zone"),
    (237, "Manhattan", "Upper East Side South", "Yellow Zone"),
    (264, "Unknown", "N/A", "N/A"),
    (265, "N/A", "Outside of NYC", "N/A"),
]
ZONE_IDS = np.array([z[0] for z in ZONES])
ZONE_WEIGHTS = np.array([2, 1, 3, 2, 3, 2, 1, 3, 4, 4, 5, 3, 3, 7, 6, 1, 8, 5, 6, 0.3, 0.3], dtype=float)
ZONE_WEIGHTS /= ZONE_WEIGHTS.sum()
AIRPORTS = {1, 132, 138}

HOUR_WEIGHTS = np.array(
    [3, 2, 1.5, 1, 1, 1.5, 3, 5, 6, 5, 4.5, 4.5, 5, 5, 5, 5.5, 6, 7.5, 8, 7.5, 6.5, 6, 5.5, 4.5], dtype=float
)
HOUR_WEIGHTS /= HOUR_WEIGHTS.sum()

COLUMNS = [
    "vendorid", "tpep_pickup_datetime", "tpep_dropoff_datetime", "passenger_count", "trip_distance",
    "ratecodeid", "store_and_fwd_flag", "pulocationid", "dolocationid", "payment_type", "fare_amount",
    "extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "total_amount",
    "congestion_surcharge", "airport_fee", "cbd_congestion_fee", "source_file",
]


def good_trips(n: int) -> pd.DataFrame:
    days = RNG.integers(0, 365, n)
    hours = RNG.choice(24, n, p=HOUR_WEIGHTS)
    pickup = (
        pd.Timestamp("2023-01-01")
        + pd.to_timedelta(days, unit="D")
        + pd.to_timedelta(hours, unit="h")
        + pd.to_timedelta(RNG.integers(0, 3600, n), unit="s")
    )
    duration_min = np.clip(RNG.lognormal(2.5, 0.55, n), 2, 120).round(2)
    speed = RNG.uniform(6, 28, n)
    distance = np.clip(speed * duration_min / 60, 0.2, 60).round(2)
    pu = RNG.choice(ZONE_IDS, n, p=ZONE_WEIGHTS)
    do = RNG.choice(ZONE_IDS, n, p=ZONE_WEIGHTS)
    airport_pu = np.isin(pu, list(AIRPORTS))
    airport_do = np.isin(do, list(AIRPORTS))

    fare = (3.0 + 2.5 * distance + 0.5 * duration_min).round(2)
    jfk = (pu == 132) | (do == 132)
    fare = np.where(jfk & (distance > 8), 70.0, fare)
    extra = np.where(np.isin(hours, [20, 21, 22, 23, 0, 1, 2, 3, 4, 5]), 1.0, 0.0)
    extra = np.where((hours >= 16) & (hours < 20), 2.5, extra)
    card = RNG.random(n) < 0.7
    tip = np.where(card, (fare * RNG.uniform(0.1, 0.25, n)).round(2), 0.0)
    tolls = np.where(RNG.random(n) < 0.08, 6.94, 0.0)
    airport_fee = np.where(airport_pu & ((pu == 132) | (pu == 138)), 1.75, 0.0)
    congestion = 2.5
    total = (fare + extra + 0.5 + tip + tolls + 1.0 + congestion + airport_fee).round(2)

    passenger = RNG.choice([1, 1, 1, 1, 2, 2, 3, 4, 5, 6], n).astype(float)
    passenger[RNG.random(n) < 0.04] = np.nan      # missing passenger counts are legitimate

    return pd.DataFrame(
        {
            "vendorid": RNG.choice([1, 2], n),
            "tpep_pickup_datetime": pickup,
            "tpep_dropoff_datetime": pickup + pd.to_timedelta(duration_min, unit="m"),
            "passenger_count": passenger,
            "trip_distance": distance,
            "ratecodeid": np.where(jfk, 2.0, 1.0),
            "store_and_fwd_flag": "N",
            "pulocationid": pu,
            "dolocationid": do,
            "payment_type": np.where(card, 1.0, 2.0),
            "fare_amount": fare,
            "extra": extra,
            "mta_tax": 0.5,
            "tip_amount": tip,
            "tolls_amount": tolls,
            "improvement_surcharge": 1.0,
            "total_amount": total,
            "congestion_surcharge": congestion,
            "airport_fee": airport_fee,
            "cbd_congestion_fee": np.nan,
            "source_file": "yellow_tripdata_2023-synthetic.parquet",
        }
    )


def plant(template: pd.DataFrame, n: int, **overrides) -> pd.DataFrame:
    rows = template.sample(n, random_state=int(RNG.integers(0, 10_000))).copy().reset_index(drop=True)
    for col, value in overrides.items():
        rows[col] = value
    return rows


def main() -> None:
    good = good_trips(N_GOOD)

    # A clean template: moderate trips, no airports, normal fares.
    clean = good[(~good["pulocationid"].isin(list(AIRPORTS))) & (~good["dolocationid"].isin(list(AIRPORTS)))
                 & (good["trip_distance"].between(1, 10)) & (good["passenger_count"].notna())]
    clean = clean[clean["pulocationid"].isin(ZONE_IDS) & clean["dolocationid"].isin(ZONE_IDS)]

    planted = []
    expected = {}

    def add(rule_code: str, df: pd.DataFrame, also: tuple = ()):
        planted.append(df)
        for code in (rule_code, *also):
            expected[code] = expected.get(code, 0) + len(df)

    # DQ01 missing timestamp (null dropoff)
    add("DQ01", plant(clean, 7, tpep_dropoff_datetime=pd.NaT))
    # DQ02 outside analysis window (2009)
    p = plant(clean, 5)
    p["tpep_pickup_datetime"] = pd.Timestamp("2009-01-01 08:00:00")
    p["tpep_dropoff_datetime"] = pd.Timestamp("2009-01-01 08:20:00")
    add("DQ02", p)
    # DQ03 dropoff at/before pickup: 3 equal, 3 earlier
    p = plant(clean, 6)
    p["tpep_dropoff_datetime"] = p["tpep_pickup_datetime"]
    p.loc[3:, "tpep_dropoff_datetime"] = p.loc[3:, "tpep_pickup_datetime"] - pd.Timedelta(minutes=15)
    add("DQ03", p)
    # DQ04 > 24h duration (but plausible speed)
    p = plant(clean, 4)
    p["tpep_dropoff_datetime"] = p["tpep_pickup_datetime"] + pd.Timedelta(minutes=1500)
    p["trip_distance"] = 10.0
    add("DQ04", p)
    # DQ05 impossible speed (80 miles in 4 minutes), distance still under the max distance
    p = plant(clean, 3)
    p["tpep_dropoff_datetime"] = p["tpep_pickup_datetime"] + pd.Timedelta(minutes=4)
    p["trip_distance"] = 80.0
    add("DQ05", p)
    # DQ06 zero / negative distance
    p = plant(clean, 8)
    p["trip_distance"] = 0.0
    p.loc[:1, "trip_distance"] = -1.5
    add("DQ06", p)
    # DQ07 distance over the maximum (150 miles in 10 hours = plausible speed)
    p = plant(clean, 4)
    p["tpep_dropoff_datetime"] = p["tpep_pickup_datetime"] + pd.Timedelta(minutes=600)
    p["trip_distance"] = 150.0
    add("DQ07", p)
    # DQ08 negative fare (total also negative, so DQ09 fires too)
    p = plant(clean, 9)
    p["fare_amount"] = -10.0
    p["total_amount"] = -10.0
    p[["extra", "mta_tax", "tip_amount", "tolls_amount", "improvement_surcharge", "congestion_surcharge", "airport_fee"]] = 0.0
    add("DQ08", p, also=("DQ09",))
    # DQ09 zero total with a normal fare
    p = plant(clean, 3)
    p["total_amount"] = 0.0
    add("DQ09", p)
    # DQ10 negative tip
    p = plant(clean, 3)
    p["tip_amount"] = -5.0
    add("DQ10", p)
    # DQ11 fare above the maximum
    p = plant(clean, 4)
    p["fare_amount"] = 900.0
    p["total_amount"] = 905.0
    add("DQ11", p)
    # DQ12 unknown location (3 bad pickup IDs, 3 bad dropoff IDs)
    p = plant(clean, 6)
    p.loc[:2, "pulocationid"] = 999
    p.loc[3:, "dolocationid"] = 0
    add("DQ12", p)
    # DQ13 impossible passenger count
    add("DQ13", plant(clean, 3, passenger_count=12.0))
    # DQ14 exact duplicates of good trips (the originals stay valid)
    add("DQ14", good.sample(10, random_state=7).copy())

    sample = pd.concat([good] + planted, ignore_index=True)[COLUMNS]
    expected_valid = N_GOOD
    expected["_raw_rows"] = len(sample)
    expected["_valid_rows"] = expected_valid
    expected["_rejected_rows"] = len(sample) - expected_valid

    if DB_PATH.exists():
        DB_PATH.unlink()
    con = duckdb.connect(str(DB_PATH))
    con.execute("create schema raw")
    con.register("trips_df", sample)
    con.execute("create table raw.yellow_trips_raw as select * from trips_df")
    zones_df = pd.DataFrame(ZONES, columns=["locationid", "borough", "zone", "service_zone"])
    con.register("zones_df", zones_df)
    con.execute("create table raw.taxi_zone_lookup as select * from zones_df")
    con.close()

    EXPECTED_PATH.write_text(json.dumps(expected, indent=2, sort_keys=True))
    print(f"Wrote {DB_PATH.name}: {len(sample):,} synthetic raw trips "
          f"({N_GOOD:,} good + {len(sample) - N_GOOD} planted bad/duplicate rows)")


if __name__ == "__main__":
    main()
