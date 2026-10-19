{#
  Grain: pickup zone x month. revenue_per_mile = sum(revenue) / sum(miles), never an average of ratios.
#}
select
    f.pickup_zone_key                                   as zone_key,
    z.borough                                           as pickup_borough,
    z.zone_name                                         as pickup_zone,
    cast(date_trunc('month', f.pickup_datetime) as date) as month_start,
    count(*)                                            as trips,
    sum(f.trip_revenue)                                 as revenue,
    sum(f.trip_distance)                                as miles,
    sum(f.trip_revenue) / nullif(sum(f.trip_distance), 0) as revenue_per_mile
from {{ ref('fct_trips') }} as f
inner join {{ ref('dim_zone') }} as z on f.pickup_zone_key = z.zone_key
group by
    f.pickup_zone_key,
    z.borough,
    z.zone_name,
    cast(date_trunc('month', f.pickup_datetime) as date)
