{#
  Applies every rule from macros/dq_rules.sql to every trip and keeps ALL rows:
    - one 0/1 flag column per rule (dqNN_<name>)
    - dq_failed_rule_count, primary_rejection_rule (first rule that matched), is_valid
  fct_trips keeps only is_valid = 1. Rejected trips stay queryable here for audits.
#}
{{ config(materialized='table') }}

{% set rules = dq_rules() %}

with trips as (

    select
        t.*,
        {{ dbt.datediff('t.pickup_datetime', 't.dropoff_datetime', 'second') }} / 60.0 as trip_duration_minutes,
        case when pz.location_id is null then 0 else 1 end as pickup_zone_found,
        case when dz.location_id is null then 0 else 1 end as dropoff_zone_found,
        row_number() over (partition by t.trip_key order by t.source_file) as dup_rank
    from {{ ref('stg_yellow_trips') }} as t
    left join {{ ref('stg_taxi_zones') }} as pz on t.pickup_location_id = pz.location_id
    left join {{ ref('stg_taxi_zones') }} as dz on t.dropoff_location_id = dz.location_id

),

flagged as (

    select
        trips.*,
        {% for r in rules %}
        case when ({{ r.condition }}) then 1 else 0 end as {{ r.flag }}{{ "," if not loop.last }}
        {% endfor %}
    from trips

),

scored as (

    select
        flagged.*,
        {% for r in rules %}flagged.{{ r.flag }}{{ " + " if not loop.last }}{% endfor %} as dq_failed_rule_count,
        case
            {% for r in rules %}
            when flagged.{{ r.flag }} = 1 then '{{ r.code }}_{{ r.name }}'
            {% endfor %}
        end as primary_rejection_rule
    from flagged

)

select
    scored.*,
    case when dq_failed_rule_count = 0 then 1 else 0 end as is_valid
from scored
