# Data quality rules

Every exclusion applied to the raw TLC trips is defined **once**, in [`dbt/macros/dq_rules.sql`](../dbt/macros/dq_rules.sql).
That macro drives:

| Artifact | What it gives you |
|---|---|
| `staging.int_trips_dq_flagged` | every raw trip with one 0/1 flag per rule, `dq_failed_rule_count`, `primary_rejection_rule`, `is_valid` |
| `staging.dq_exclusion_summary` | one row per rule: trips failing it, trips attributed to it as first match, % of raw rows |
| `marts.fct_trips` | only `is_valid = 1` trips |

Nothing is deleted. Rejected trips stay in `int_trips_dq_flagged`, so any exclusion can be inspected:

```sql
select * from staging.int_trips_dq_flagged where primary_rejection_rule = 'DQ05_impossible_speed' limit 100;
select rule_code, rule_name, rows_failing_rule, pct_of_raw_rows from staging.dq_exclusion_summary order by rows_failing_rule desc;
```

## Rules

A trip is excluded if it matches **any** rule. Thresholds are dbt vars in `dbt/dbt_project.yml`.

| Code | Rule | Condition | Why |
|---|---|---|---|
| DQ01 | missing_timestamp | pickup or dropoff timestamp is null | cannot be placed in time or measured |
| DQ02 | outside_period | pickup outside `data_start_date` … `data_end_date` | TLC files contain stray dates (e.g. 2002, 2009) |
| DQ03 | nonpositive_duration | dropoff ≤ pickup | zero or negative duration is impossible |
| DQ04 | excessive_duration | duration > `max_trip_duration_minutes` (1,440 = 24 h) | meter left running / bad timestamps |
| DQ05 | impossible_speed | distance ÷ duration > `max_avg_speed_mph` (100) | distance and duration cannot both be right |
| DQ06 | nonpositive_distance | distance is null, 0 or negative | zero-distance trips carry no mileage information |
| DQ07 | excessive_distance | distance > `max_trip_distance_miles` (100) | implausible for NYC yellow taxis |
| DQ08 | nonpositive_fare | fare_amount is null, 0 or negative | refunds, disputes, test trips |
| DQ09 | nonpositive_total | total_amount is null, 0 or negative | same, at the total level |
| DQ10 | negative_charge | any of extra, mta_tax, tip, tolls, improvement/congestion surcharge, airport fee < 0 | adjustments, not real trip charges |
| DQ11 | excessive_fare | fare_amount > `max_fare_amount` (500) | extreme outliers distort revenue per mile / per hour |
| DQ12 | unknown_location | pickup or dropoff zone ID is null or not in the zone lookup | cannot be assigned to a borough |
| DQ13 | invalid_passenger_count | passenger_count < 0 or > `max_passenger_count` (8) | impossible values (nulls are allowed) |
| DQ14 | duplicate_trip | identical on every trip field to an earlier record | double-loaded rows (first occurrence kept) |

## Deliberate decisions

- **Zero-passenger and null passenger counts are kept.** They are driver-entry noise, not a fare problem, and passenger count is not used in the revenue metrics.
- **Zones 264 (Unknown) and 265 (Outside of NYC) are kept** and flagged `is_unknown_zone` in `dim_zone`, because the trip itself is valid; filter them in BI if you only want in-borough analysis.
- **Revenue excludes tips and tolls.** `trip_revenue = total_amount − tip_amount − tolls_amount`. Tips are only recorded for card payments and tolls are pass-through, so this keeps cash and card trips comparable.
- **Thresholds are judgment calls.** They are intentionally loose (only physically/economically implausible trips are removed). Tighten or loosen them with dbt vars, e.g. `dbt build --vars '{max_fare_amount: 300}'`.

## Tests that enforce the rules downstream

`fct_trips` carries dbt tests on fares (`> 0`, `<= max`), distances (`> 0`, `<= max`), timestamps (`dropoff > pickup`, pickup inside the window), duration, speed and passenger count, plus uniqueness of `trip_id` and foreign keys to `dim_zone` / `dim_time`.
Singular tests in `dbt/tests/` check that:

1. raw rows = `fct_trips` rows + rejected rows (nothing silently lost),
2. the exclusion summary adds up to the rejected row count,
3. `agg_hourly_demand` reconciles to `fct_trips` (trips and revenue).
