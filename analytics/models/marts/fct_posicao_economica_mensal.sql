{{
    config(
        materialized='incremental',
        unique_key=['mes_referencia', 'obra_key', 'conta_key'],
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}
{#-
  Periodic snapshot of the economic position (rules doc: "a versão dos dados da posição econômica deve ser
  salva mensalmente"). Grain: closing month x work x P&L account, as known at the month's last day.
  Full refresh = backfill every month from the first document (point-in-time from the ERP dates).
  Incremental run = (re)saves only the closing month, so closed months are never rewritten by later ERP edits.
-#}
{%- set fechamento = var('mes_fechamento') -%}
{%- set ultimo_mes -%}
    {% if fechamento %}date '{{ fechamento }}'{% else %}
        cast(date_trunc('month', current_date) - interval '1 month' as date)
        {% endif %}
{%- endset -%}
-- months come from dim_date (no array/series functions, so the SQL stays portable)
with meses as (
    select distinct inicio_mes as mes_referencia
    from {{ ref('dim_date') }}
    where inicio_mes <= {{ ultimo_mes }}
    {% if is_incremental() -%}
      and inicio_mes >= {{ ultimo_mes }}
    {%- else -%}
      and inicio_mes >= (select d.inicio_mes from {{ ref('dim_date') }} d
                         where d.date_key = (select min(data_documento_key) from {{ ref('fct_lancamento') }}))
    {%- endif %}
),
cortes as (
    select mes_referencia, 
    {{ date_key("(mes_referencia + interval '1 month' - interval '1 day')") }} as corte_key
    from meses
)
select
    c.mes_referencia,
    {{ date_key('c.mes_referencia') }} as mes_referencia_key,
    f.obra_key,
    f.conta_key,
    -- paid by the cut date -> efetuado (cumulative); documented by the cut but not yet paid -> compromissado
    sum(case when f.data_movimento_bancario_key <= c.corte_key then f.valor_previsto else 0 end)::numeric(16,2)
        as valor_efetuado_acumulado,
    sum(case 
        when f.data_movimento_bancario_key <= c.corte_key 
        then 0 else f.valor_previsto end)::numeric(16,2)
        as valor_compromissado,
    sum(f.valor_previsto)::numeric(16,2) as valor_total,
    current_timestamp::timestamp as salvo_em
from cortes as c
join {{ ref('fct_lancamento') }} as f
    on f.data_documento_key <= c.corte_key
   and f.is_dre
group by 1, 2, 3, 4
