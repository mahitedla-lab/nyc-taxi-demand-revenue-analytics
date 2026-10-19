select
    location_id                                            as zone_key,
    zone_name,
    borough,
    service_zone,
    case when lower(zone_name) like '%airport%'
           or service_zone in ('Airports', 'EWR') then 1 else 0 end as is_airport,
    -- TLC zones 264 (Unknown) and 265 (Outside of NYC): valid trips, flagged so BI can filter them
    case when location_id in (264, 265) then 1 else 0 end            as is_unknown_zone
from {{ ref('stg_taxi_zones') }}
