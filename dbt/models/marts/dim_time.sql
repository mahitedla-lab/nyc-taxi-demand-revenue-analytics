{#
  One row per clock hour in [data_start_date, data_end_date). Used as a role-playing
  dimension for pickup and dropoff time.
  day_of_week_num: 0 = Sunday ... 6 = Saturday.
#}
with hours as (

    {{ dbt_utils.date_spine(
        datepart="hour",
        start_date="cast('" ~ var('data_start_date') ~ "' as timestamp)",
        end_date="cast('" ~ var('data_end_date') ~ "' as timestamp)"
    ) }}

),

parts as (

    select
        cast(date_hour as timestamp)                    as time_key,
        cast(date_hour as date)                         as date_day,
        extract(hour from date_hour)        as hour_of_day,
        extract(dow from date_hour)         as day_of_week_num
    from hours

)

select
    time_key,
    date_day,
    cast(date_trunc('month', date_day) as date) as month_start,
    hour_of_day,
    day_of_week_num,
    case day_of_week_num
        when 0 then 'Sunday'    when 1 then 'Monday'   when 2 then 'Tuesday'
        when 3 then 'Wednesday' when 4 then 'Thursday' when 5 then 'Friday'
        else 'Saturday'
    end                                         as day_name,
    case when day_of_week_num in (0, 6) then 1 else 0 end as is_weekend,
    case
        when hour_of_day between 0  and 4  then '1 Overnight (12a-5a)'
        when hour_of_day between 5  and 9  then '2 Morning (5a-10a)'
        when hour_of_day between 10 and 15 then '3 Midday (10a-4p)'
        when hour_of_day between 16 and 19 then '4 Evening peak (4p-8p)'
        else                                    '5 Night (8p-12a)'
    end                                         as day_part
from parts
