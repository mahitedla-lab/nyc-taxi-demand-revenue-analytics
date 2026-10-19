{#
  Star-schema fact: one row per VALID trip (is_valid = 1 in int_trips_dq_flagged).
  trip_revenue = fare + surcharges + fees + tolls, EXCLUDING tips (cash tips are not recorded,
  so including tips would overstate card trips). It is positive for every kept trip because
  rules DQ08 and DQ10 reject non-positive fares and negative charges.
#}
select
    v.trip_key                                                     as trip_id,
    cast({{ dbt.date_trunc('hour', 'v.pickup_datetime') }} as timestamp)  as pickup_time_key,
    cast({{ dbt.date_trunc('hour', 'v.dropoff_datetime') }} as timestamp) as dropoff_time_key,
    v.pickup_location_id                                           as pickup_zone_key,
    v.dropoff_location_id                                          as dropoff_zone_key,
    v.vendor_id,
    v.payment_type,
    v.pickup_datetime,
    v.dropoff_datetime,
    v.passenger_count,
    v.trip_distance,
    v.trip_duration_minutes,
    v.trip_distance / (v.trip_duration_minutes / 60.0)             as avg_speed_mph,
    v.fare_amount,
    v.extra,
    v.mta_tax,
    v.tip_amount,
    v.tolls_amount,
    v.improvement_surcharge,
    v.congestion_surcharge,
    v.airport_fee,
    v.total_amount,
    v.fare_amount + coalesce(v.extra, 0) + coalesce(v.mta_tax, 0) + coalesce(v.tolls_amount, 0)
      + coalesce(v.improvement_surcharge, 0) + coalesce(v.congestion_surcharge, 0)
      + coalesce(v.airport_fee, 0) + coalesce(v.cbd_congestion_fee, 0) as trip_revenue,
    pz.is_airport                                                  as is_airport_pickup,
    dz.is_airport                                                  as is_airport_dropoff,
    case when pz.is_airport = 1 or dz.is_airport = 1 then 1 else 0 end as is_airport_trip
from {{ ref('int_trips_dq_flagged') }} as v
inner join {{ ref('dim_zone') }} as pz on v.pickup_location_id  = pz.zone_key
inner join {{ ref('dim_zone') }} as dz on v.dropoff_location_id = dz.zone_key
where v.is_valid = 1
