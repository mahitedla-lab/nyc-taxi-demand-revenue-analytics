{#
  Audit trail: how many raw trips each data-quality rule catches.
    rows_failing_rule        - trips matching the rule (a trip can match several rules)
    rows_excluded_first_match - trips whose FIRST matching rule is this one (sums to total excluded)
#}
{% set rules = dq_rules() %}

with agg as (

    select
        count(*) as total_rows,
        sum(is_valid) as valid_rows,
        {% for r in rules %}
        sum({{ r.flag }}) as {{ r.flag }}_n,
        sum(case when primary_rejection_rule = '{{ r.code }}_{{ r.name }}' then 1 else 0 end) as {{ r.flag }}_first_n{{ "," if not loop.last }}
        {% endfor %}
    from {{ ref('int_trips_dq_flagged') }}

)

{% for r in rules %}
select
    '{{ r.code }}' as rule_code,
    '{{ r.name }}' as rule_name,
    '{{ r.description }}' as rule_description,
    {{ r.flag }}_n as rows_failing_rule,
    {{ r.flag }}_first_n as rows_excluded_first_match,
    round(100.0 * {{ r.flag }}_n / nullif(total_rows, 0), 4) as pct_of_raw_rows,
    total_rows,
    valid_rows
from agg
{% if not loop.last %}union all{% endif %}
{% endfor %}
