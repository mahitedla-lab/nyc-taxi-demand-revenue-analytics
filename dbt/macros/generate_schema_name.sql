{#
  Use the custom schema exactly as written (staging / marts / analytics) instead of
  dbt's default "<target_schema>_<custom_schema>" so Power BI sees clean schema names.
#}
{% macro generate_schema_name(custom_schema_name, node) -%}
    {%- if custom_schema_name is none -%}
        {{ target.schema }}
    {%- else -%}
        {{ custom_schema_name | trim }}
    {%- endif -%}
{%- endmacro %}
