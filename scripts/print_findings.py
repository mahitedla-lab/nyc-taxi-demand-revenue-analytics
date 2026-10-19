#!/usr/bin/env python3
"""Query the ANALYTICS schema in Snowflake and write docs/findings.md with the real numbers
from YOUR run (top revenue windows, revenue per mile by borough, airport share, exclusions).

    python scripts/print_findings.py
"""
from pathlib import Path

from snowflake_conn import connect

QUERIES = {
    "Data-quality exclusions (staging.dq_exclusion_summary)": """
        select rule_code, rule_name, rows_failing_rule, pct_of_raw_rows
        from nyc_taxi.staging.dq_exclusion_summary
        order by rows_failing_rule desc
    """,
    "Top 10 day/hour windows by revenue per trip hour": """
        select day_name, hour_of_day, trips, round(revenue_per_trip_hour, 2) as revenue_per_trip_hour,
               round(revenue_per_trip, 2) as revenue_per_trip
        from nyc_taxi.analytics.agg_revenue_per_trip_hour
        order by revenue_per_trip_hour_rank
        limit 10
    """,
    "Revenue per mile by pickup borough": """
        select pickup_borough, sum(trips) as trips,
               round(sum(revenue) / nullif(sum(miles), 0), 2) as revenue_per_mile
        from nyc_taxi.analytics.agg_revenue_per_mile
        group by pickup_borough
        order by trips desc
    """,
    "Airport trip share by pickup borough": """
        select pickup_borough, sum(trips) as trips, sum(airport_trips) as airport_trips,
               round(100.0 * sum(airport_trips) / nullif(sum(trips), 0), 2) as airport_trip_share_pct
        from nyc_taxi.analytics.agg_airport_share_by_borough
        group by pickup_borough
        order by trips desc
    """,
    "Row counts": """
        select (select count(*) from nyc_taxi.raw.yellow_trips_raw) as raw_trips,
               (select count(*) from nyc_taxi.marts.fct_trips) as valid_trips
    """,
}


def to_markdown(columns, rows) -> str:
    out = ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for row in rows:
        out.append("| " + " | ".join(f"{v:,}" if isinstance(v, int) else str(v) for v in row) + " |")
    return "\n".join(out)


def main() -> None:
    conn = connect("ANALYTICS")
    cur = conn.cursor()
    sections = ["# Findings (generated from the Snowflake run)\n"]
    try:
        for title, sql in QUERIES.items():
            cur.execute(sql)
            cols = [c[0].lower() for c in cur.description]
            sections.append(f"## {title}\n\n{to_markdown(cols, cur.fetchall())}\n")
    finally:
        cur.close()
        conn.close()

    out = Path("docs/findings.md")
    out.parent.mkdir(exist_ok=True)
    out.write_text("\n".join(sections))
    print("\n".join(sections))
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
