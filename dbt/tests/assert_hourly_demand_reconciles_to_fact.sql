-- The hourly demand aggregate must neither lose nor invent trips or revenue versus fct_trips.
with agg as (
    select sum(trips) as trips, sum(revenue) as revenue
    from {{ ref('agg_hourly_demand') }}
),
fct as (
    select count(*) as trips, sum(trip_revenue) as revenue
    from {{ ref('fct_trips') }}
)
select
    agg.trips    as agg_trips,
    fct.trips    as fct_trips,
    agg.revenue  as agg_revenue,
    fct.revenue  as fct_revenue
from agg, fct
where agg.trips <> fct.trips
   or abs(agg.revenue - fct.revenue) > 0.01
