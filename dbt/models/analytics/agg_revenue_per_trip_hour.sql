{#
  Grain: day of week x hour of day (168 time windows).
  revenue_per_trip_hour = revenue earned per hour of metered trip time
                        = sum(trip_revenue) / (sum(trip_duration_minutes) / 60).
  Rank 1 = the window that earns the most per trip hour. is_top_decile flags the top 10% of windows.
#}
with windows as (

    select
        t.day_of_week_num,
        t.day_name,
        t.is_weekend,
        t.hour_of_day,
        count(*)                             as trips,
        sum(f.trip_revenue)                  as revenue,
        sum(f.trip_distance)                 as miles,
        sum(f.trip_duration_minutes) / 60.0  as trip_hours
    from {{ ref('fct_trips') }} as f
    inner join {{ ref('dim_time') }} as t on f.pickup_time_key = t.time_key
    group by
        t.day_of_week_num,
        t.day_name,
        t.is_weekend,
        t.hour_of_day

),

scored as (

    select
        windows.*,
        revenue / nullif(trip_hours, 0) as revenue_per_trip_hour,
        revenue / nullif(trips, 0)      as revenue_per_trip,
        revenue / nullif(miles, 0)      as revenue_per_mile
    from windows

)

select
    scored.*,
    rank() over (order by revenue_per_trip_hour desc) as revenue_per_trip_hour_rank,
    case when ntile(10) over (order by revenue_per_trip_hour desc) = 1 then 1 else 0 end as is_top_decile
from scored
