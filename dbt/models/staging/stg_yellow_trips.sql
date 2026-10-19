{#
  Types and renames the raw TLC columns. NO rows are filtered here - exclusions happen in
  int_trips_dq_flagged so every removed trip stays auditable.
  trip_key hashes every trip field, so exact duplicate records share a key (rule DQ14).
#}
select
    {{ dbt_utils.generate_surrogate_key([
        'vendorid', 'tpep_pickup_datetime', 'tpep_dropoff_datetime', 'passenger_count', 'trip_distance',
        'ratecodeid', 'pulocationid', 'dolocationid', 'payment_type', 'fare_amount', 'extra', 'mta_tax',
        'tip_amount', 'tolls_amount', 'improvement_surcharge', 'total_amount', 'congestion_surcharge',
        'airport_fee'
    ]) }}                                          as trip_key,
    cast(vendorid as integer)                      as vendor_id,
    cast(tpep_pickup_datetime as timestamp)        as pickup_datetime,
    cast(tpep_dropoff_datetime as timestamp)       as dropoff_datetime,
    cast(passenger_count as integer)               as passenger_count,
    cast(trip_distance as double)                  as trip_distance,
    cast(ratecodeid as integer)                    as rate_code_id,
    cast(pulocationid as integer)                  as pickup_location_id,
    cast(dolocationid as integer)                  as dropoff_location_id,
    cast(payment_type as integer)                  as payment_type,
    cast(fare_amount as double)                    as fare_amount,
    cast(extra as double)                          as extra,
    cast(mta_tax as double)                        as mta_tax,
    cast(tip_amount as double)                     as tip_amount,
    cast(tolls_amount as double)                   as tolls_amount,
    cast(improvement_surcharge as double)          as improvement_surcharge,
    cast(total_amount as double)                   as total_amount,
    cast(congestion_surcharge as double)           as congestion_surcharge,
    cast(airport_fee as double)                    as airport_fee,
    cast(cbd_congestion_fee as double)             as cbd_congestion_fee,
    source_file
from {{ source('raw', 'yellow_trips_raw') }}
