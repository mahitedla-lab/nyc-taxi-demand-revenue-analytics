{#
  Single source of truth for every data-quality exclusion.

  Each rule is a SQL condition evaluated per trip; a trip that matches ANY rule is
  excluded from fct_trips. The rules drive three things:
    * int_trips_dq_flagged   - one 0/1 flag column per rule + the first matching rule
    * dq_exclusion_summary   - how many trips each rule catches (the audit trail)
    * docs/DATA_QUALITY_RULES.md - human-readable explanation (keep in sync)

  Thresholds come from vars in dbt_project.yml. Conditions may reference columns of the
  trips CTE in int_trips_dq_flagged. A NULL condition counts as "rule not triggered",
  so rules that must treat NULL as bad use coalesce(..., true).
  Descriptions must not contain single quotes (they are emitted as SQL string literals).
#}
{% macro dq_rules() %}
  {% set start_ts = "cast('" ~ var('data_start_date') ~ "' as timestamp)" %}
  {% set end_ts = "cast('" ~ var('data_end_date') ~ "' as timestamp)" %}

  {% set rules = [
    {
      'code': 'DQ01', 'name': 'missing_timestamp',
      'description': 'Pickup or dropoff timestamp is missing',
      'condition': "pickup_datetime is null or dropoff_datetime is null"
    },
    {
      'code': 'DQ02', 'name': 'outside_period',
      'description': 'Pickup falls outside the analysis window (stray dates such as 2002 or 2009 appear in TLC files)',
      'condition': "pickup_datetime < " ~ start_ts ~ " or pickup_datetime >= " ~ end_ts
    },
    {
      'code': 'DQ03', 'name': 'nonpositive_duration',
      'description': 'Dropoff is at or before pickup (zero or negative duration)',
      'condition': "dropoff_datetime <= pickup_datetime"
    },
    {
      'code': 'DQ04', 'name': 'excessive_duration',
      'description': 'Trip lasts longer than the maximum plausible duration',
      'condition': "trip_duration_minutes > " ~ var('max_trip_duration_minutes')
    },
    {
      'code': 'DQ05', 'name': 'impossible_speed',
      'description': 'Implied average speed (distance / duration) exceeds the maximum plausible speed',
      'condition': "trip_distance / nullif(trip_duration_minutes / 60.0, 0) > " ~ var('max_avg_speed_mph')
    },
    {
      'code': 'DQ06', 'name': 'nonpositive_distance',
      'description': 'Trip distance is missing, zero or negative',
      'condition': "coalesce(trip_distance <= 0, true)"
    },
    {
      'code': 'DQ07', 'name': 'excessive_distance',
      'description': 'Trip distance exceeds the maximum plausible distance',
      'condition': "trip_distance > " ~ var('max_trip_distance_miles')
    },
    {
      'code': 'DQ08', 'name': 'nonpositive_fare',
      'description': 'Metered fare is missing, zero or negative (refunds, disputes, test trips)',
      'condition': "coalesce(fare_amount <= 0, true)"
    },
    {
      'code': 'DQ09', 'name': 'nonpositive_total',
      'description': 'Total amount charged is missing, zero or negative',
      'condition': "coalesce(total_amount <= 0, true)"
    },
    {
      'code': 'DQ10', 'name': 'negative_charge',
      'description': 'Any individual surcharge, tax, tip or toll is negative',
      'condition': "coalesce(extra, 0) < 0 or coalesce(mta_tax, 0) < 0 or coalesce(tip_amount, 0) < 0 or coalesce(tolls_amount, 0) < 0 or coalesce(improvement_surcharge, 0) < 0 or coalesce(congestion_surcharge, 0) < 0 or coalesce(airport_fee, 0) < 0"
    },
    {
      'code': 'DQ11', 'name': 'excessive_fare',
      'description': 'Metered fare exceeds the maximum plausible fare',
      'condition': "fare_amount > " ~ var('max_fare_amount')
    },
    {
      'code': 'DQ12', 'name': 'unknown_location',
      'description': 'Pickup or dropoff location ID is missing or not in the taxi zone lookup',
      'condition': "pickup_zone_found = 0 or dropoff_zone_found = 0"
    },
    {
      'code': 'DQ13', 'name': 'invalid_passenger_count',
      'description': 'Passenger count is negative or above the vehicle maximum (missing counts are allowed)',
      'condition': "passenger_count < 0 or passenger_count > " ~ var('max_passenger_count')
    },
    {
      'code': 'DQ14', 'name': 'duplicate_trip',
      'description': 'Exact duplicate of another trip record (the first occurrence is kept)',
      'condition': "dup_rank > 1"
    }
  ] %}

  {% set out = [] %}
  {% for r in rules %}
    {% do out.append({
      'code': r['code'],
      'name': r['name'],
      'description': r['description'],
      'condition': r['condition'],
      'flag': (r['code'] | lower) ~ '_' ~ r['name']
    }) %}
  {% endfor %}
  {{ return(out) }}
{% endmacro %}
