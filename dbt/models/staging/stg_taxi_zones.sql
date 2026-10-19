select
    cast(locationid as integer)  as location_id,
    trim(borough)                as borough,
    trim(zone)                   as zone_name,
    trim(service_zone)           as service_zone
from {{ source('raw', 'taxi_zone_lookup') }}
