{# Post-hook for marts: on the prod target, writes the table to <export_path>/<model>.<format> for Power BI.
   Power BI reads the files, never the .duckdb, so a dbt run never fights Power BI for the database lock.
   export_format: 'parquet' (default) or 'csv' (for a DuckDB driver without the Parquet extension). #}
{% macro export_parquet() -%}
    {%- set fmt = var('export_format', 'parquet') -%}
    {%- if target.name == 'prod' -%}
        copy {{ this }} to '{{ var("export_path") }}/{{ this.identifier }}.{{ fmt }}'
        ({% if fmt == 'csv' %}format csv, header true{% else %}format parquet{% endif %})
    {%- else -%}
        select 1
    {%- endif -%}
{%- endmacro %}
