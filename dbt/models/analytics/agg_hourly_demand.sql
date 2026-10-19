{#
  Grain: pickup hour x pickup borough. Additive measures only (sum them, then divide in BI).
#}
select
    f.pickup_time_key                    as time_key,
    t.date_day,
    t.hour_of_day,
    t.day_of_week_num,
    t.day_name,
    t.is_weekend,
    t.day_part,
    z.borough                            as pickup_borough,
    count(*)                             as trips,
    sum(f.trip_revenue)                  as revenue,
    sum(f.trip_distance)                 as miles,
    sum(f.trip_duration_minutes) / 60.0  as trip_hours
from {{ ref('fct_trips') }} as f
inner join {{ ref('dim_time') }} as t on f.pickup_time_key = t.time_key
inner join {{ ref('dim_zone') }} as z on f.pickup_zone_key = z.zone_key
group by
    f.pickup_time_key,
    t.date_day,
    t.hour_of_day,
    t.day_of_week_num,
    t.day_name,
    t.is_weekend,
    t.day_part,
    z.borough
