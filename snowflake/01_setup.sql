-- ============================================================================
-- Snowflake setup for the NYC taxi project.
-- Run once, as a role that can create warehouses/databases (SYSADMIN is fine
-- on a personal trial account).
-- ============================================================================

use role sysadmin;

create warehouse if not exists taxi_wh
    warehouse_size = 'SMALL'
    auto_suspend   = 60
    auto_resume    = true
    initially_suspended = true;

create database if not exists nyc_taxi;

create schema if not exists nyc_taxi.raw;        -- loaded as-is from TLC files
create schema if not exists nyc_taxi.staging;    -- dbt: staging + intermediate models
create schema if not exists nyc_taxi.marts;      -- dbt: star schema (fct_trips, dim_zone, dim_time)
create schema if not exists nyc_taxi.analytics;  -- dbt: aggregates consumed by Power BI

use warehouse taxi_wh;
use schema nyc_taxi.raw;

-- File formats ---------------------------------------------------------------
-- USE_LOGICAL_TYPE makes Snowflake read Parquet timestamps as real timestamps.
create file format if not exists tlc_parquet
    type = parquet
    use_logical_type = true;

create file format if not exists zone_csv
    type = csv
    skip_header = 1
    field_optionally_enclosed_by = '"';

-- Internal stages --------------------------------------------------------------
create stage if not exists tlc_stage  file_format = tlc_parquet;
create stage if not exists zone_stage file_format = zone_csv;

-- Raw trips ---------------------------------------------------------------------
-- Column names must match the Parquet field names (case-insensitive) because the
-- load uses MATCH_BY_COLUMN_NAME. Columns missing from older/newer files load as NULL.
-- Numeric columns that TLC has shipped as both INT and DOUBLE are FLOAT here and
-- are cast to proper types in dbt (stg_yellow_trips).
create table if not exists raw.yellow_trips_raw (
    vendorid              number(38, 0),
    tpep_pickup_datetime  timestamp_ntz,
    tpep_dropoff_datetime timestamp_ntz,
    passenger_count       float,
    trip_distance         float,
    ratecodeid            float,
    store_and_fwd_flag    varchar(1),
    pulocationid          number(38, 0),
    dolocationid          number(38, 0),
    payment_type          float,
    fare_amount           float,
    extra                 float,
    mta_tax               float,
    tip_amount            float,
    tolls_amount          float,
    improvement_surcharge float,
    total_amount          float,
    congestion_surcharge  float,
    airport_fee           float,
    cbd_congestion_fee    float,           -- only present in 2025+ files
    source_file           varchar          -- added at load time (METADATA$FILENAME)
);

-- Zone lookup (265 rows) ---------------------------------------------------------
create table if not exists raw.taxi_zone_lookup (
    locationid   number(38, 0),
    borough      varchar,
    zone         varchar,
    service_zone varchar
);
