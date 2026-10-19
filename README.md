# NYC Taxi Demand & Revenue Analytics

One year of NYC TLC **yellow taxi** trip records (tens of millions of rows) loaded into **Snowflake**, modeled in **dbt** as a star schema (trip, zone, time) with tests on fares, distances and timestamps, cleaned with documented SQL data-quality rules, and reported in **Power BI** (hourly demand, revenue per mile, airport trip share by borough, and the time windows earning the most revenue per trip hour).

```
TLC Parquet -> scripts/download_tlc.py -> Snowflake RAW (scripts/load_to_snowflake.py)
   -> dbt staging/intermediate (type, flag 14 DQ rules) -> marts (fct_trips, dim_zone, dim_time)
   -> analytics aggregates -> Power BI
```

## What is verified, and what is not
- **Verified:** the full dbt project (70 models/tests) builds on a *synthetic* 20k-row sample using DuckDB (`ci/`), and a check script proves each of the 14 DQ rules catches exactly the bad rows planted for it. GitHub Actions runs this on every push.
- **Not verified here:** the Snowflake load and a full-year run. They need your Snowflake account and the TLC download, so **no real row counts or findings are claimed in this repo**. `scripts/print_findings.py` writes `docs/findings.md` from your actual run.
- The Power BI `.pbix` is binary and must be authored in Power BI Desktop; `powerbi/` has the connection, DAX measures and page layouts.

## Star schema
| Table | Grain |
|---|---|
| `marts.fct_trips` | one valid trip (fare, distance, duration, speed, `trip_revenue`, airport flags) |
| `marts.dim_zone` | TLC taxi zone (borough, `is_airport`, `is_unknown_zone`) |
| `marts.dim_time` | clock hour (hour, day of week, weekend, `day_part`), used for pickup and dropoff |

`analytics.agg_*` tables feed the dashboard; `staging.dq_exclusion_summary` is the audit trail of every exclusion. `trip_revenue` = fare + surcharges + fees + tolls, **excluding tips** (cash tips are not recorded).

## Data quality
Fourteen rules (`dbt/macros/dq_rules.sql`) remove zero-distance trips, negative fares, impossible durations and speeds, stray dates, duplicates and more. Every rule is documented in [docs/DATA_QUALITY_RULES.md](docs/DATA_QUALITY_RULES.md), counted in `dq_exclusion_summary`, and reconciled by tests (raw = kept + rejected). Thresholds are dbt vars in `dbt/dbt_project.yml`.

## Run it
```bash
pip install -r requirements.txt
python scripts/download_tlc.py                 # 12 monthly Parquet files + zone lookup
# run snowflake/01_setup.sql in Snowflake, set SNOWFLAKE_* env vars, then:
python scripts/load_to_snowflake.py
cd dbt && cp profiles.yml.example ~/.dbt/profiles.yml
dbt deps && dbt build
python ../scripts/print_findings.py            # writes docs/findings.md from your run
```
Smoke test without Snowflake: `pip install -r requirements-ci.txt && python ci/make_sample_data.py && cd dbt && dbt deps && dbt build --profiles-dir ../ci --target ci && cd .. && python ci/verify_dq_counts.py`
