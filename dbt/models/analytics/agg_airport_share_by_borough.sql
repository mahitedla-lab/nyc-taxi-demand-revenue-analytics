{#
  Grain: pickup borough x month.
  An "airport trip" starts or ends in an airport zone (EWR, JFK, LaGuardia).
  Borough is the PICKUP borough, so JFK/LaGuardia departures count toward Queens and
  Newark departures toward EWR.
#}
select
    z.borough                                                            as pickup_borough,
    cast(date_trunc('month', f.pickup_datetime) as date)                 as month_start,
    count(*)                                                             as trips,
    sum(f.is_airport_trip)                                               as airport_trips,
    sum(f.is_airport_pickup)                                             as airport_pickups,
    sum(f.is_airport_dropoff)                                            as airport_dropoffs,
    sum(f.trip_revenue)                                                  as revenue,
    sum(case when f.is_airport_trip = 1 then f.trip_revenue else 0 end)  as airport_revenue,
    sum(f.is_airport_trip) * 1.0 / nullif(count(*), 0)                   as airport_trip_share,
    sum(case when f.is_airport_trip = 1 then f.trip_revenue else 0 end)
        / nullif(sum(f.trip_revenue), 0)                                 as airport_revenue_share
from {{ ref('fct_trips') }} as f
inner join {{ ref('dim_zone') }} as z on f.pickup_zone_key = z.zone_key
group by
    z.borough,
    cast(date_trunc('month', f.pickup_datetime) as date)
