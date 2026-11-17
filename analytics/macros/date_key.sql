{# Integer yyyymmdd key for dim_date joins; null stays null (e.g. open items without a bank date). #}
{%  macro date_key(column) -%}
      cast(strftime({{ column }}, '%Y%m%d') as integer)

{% endmacro %}