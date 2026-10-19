# Power BI dashboard: build guide

A `.pbix` file can only be authored in Power BI Desktop, so this folder gives you everything needed to build it in ~30 minutes:
the connection, the data model, every DAX measure ([`measures.dax`](measures.dax)) and the page layouts.

## 1. Connect to Snowflake

Power BI Desktop → **Get data → Snowflake**
- Server: `<your-account>.snowflakecomputing.com`
- Warehouse: `TAXI_WH`
- Advanced → SQL is not needed; navigate to **NYC_TAXI → ANALYTICS** and import:
  `AGG_HOURLY_DEMAND`, `AGG_REVENUE_PER_MILE`, `AGG_AIRPORT_SHARE_BY_BOROUGH`, `AGG_REVENUE_PER_TRIP_HOUR`

Or paste this in **Advanced Editor** for each table (change the table name):

```m
let
    Source    = Snowflake.Databases("<your-account>.snowflakecomputing.com", "TAXI_WH", [Role = "SYSADMIN"]),
    Database  = Source{[Name = "NYC_TAXI", Kind = "Database"]}[Data],
    Analytics = Database{[Name = "ANALYTICS", Kind = "Schema"]}[Data],
    Table     = Analytics{[Name = "AGG_HOURLY_DEMAND", Kind = "Table"]}[Data]
in
    Table
```

Import mode is fine: the four tables are small (the largest, hourly demand, is ~8,760 hours × 7 boroughs).
Rename the columns to lower-case names if Power BI shows them in upper case so the DAX in `measures.dax` resolves (or find/replace the names).

## 2. Model

The tables are independent aggregates; relate nothing except through shared slicer fields. Add a shared **Borough** slicer by syncing
`pickup_borough` across pages (View → Sync slicers). Mark `agg_hourly_demand[date_day]` as a date column.

Sort `day_name` by `day_of_week_num`, and `day_part` by `hour_of_day` (Column tools → Sort by column).

## 3. Pages

**Page 1: Hourly demand**
- KPI cards: `Trips`, `Revenue`, `Avg Revenue per Trip`
- Line chart: axis `hour_of_day`, legend `is_weekend` (Weekday / Weekend), value `Avg Trips per Hour Slot`
- Matrix (heatmap): rows `day_name`, columns `hour_of_day`, values `Trips`; background colour scale
- Slicers: month (`date_day` hierarchy), `pickup_borough`

**Page 2: Revenue per mile**
- Bar chart: `pickup_borough` × `Zone Revenue per Mile`
- Table / map: `pickup_zone` × `Zone Revenue per Mile`, `Zone Trips` (filter `Zone Trips` ≥ 500 to avoid noisy low-volume zones)
- Line chart: `month_start` × `Zone Revenue per Mile`

**Page 3: Airport trip share by borough**
- Clustered column: `pickup_borough` × `Airport Trip Share`
- Line chart: `month_start` × `Airport Trip Share`, legend `pickup_borough`
- Cards: `Airport Trips`, `Airport Revenue Share`
- Tooltip note: borough is the *pickup* borough, so JFK/LaGuardia departures count toward Queens and Newark toward EWR.

**Page 4: Best revenue windows (revenue per trip hour)**
- Matrix: rows `day_name`, columns `hour_of_day`, values `Window Revenue per Trip Hour`; conditional formatting on `Is Top Window`
- Table: top 10 by `Window Rank` with `Window Revenue per Trip Hour`, `Window Trips`
- Card: `Window Label` filtered to rank 1 (the single best window)

## 4. Publish

File → Publish → choose a workspace. Add a screenshot of each page to `docs/images/` and reference it from the README.
