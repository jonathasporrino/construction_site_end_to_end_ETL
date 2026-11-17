{{
    config(
        materialized='incremental',
        unique_key='lancamento_id',
        incremental_strategy='merge',
        on_schema_change='append_new_columns'
    )
}}
-- Grain: one financial document installment. Amounts are positive; dim_conta.natureza gives the sign.
-- valor_compromissado = still to receive/pay (TOTCOMP); valor_efetuado = received/paid (TOTEFETU).
select
    l.lancamento_id,
    coalesce(o.obra_key, -1) as obra_key,
    coalesce(c.conta_key, -1) as conta_key,
    coalesce(cp.empresa_key, -1) as contraparte_key,
    coalesce(rp.empresa_key,-1) as empresa_recbto_pagto_key,
    coalesce(op.operacao_key,-1) as operacao_key,
    {{ date_key('l.dt_competencia') }} as data_competencia_key,
    {{ date_key('l.dt_doc') }} as data_documento_key,
    {{ date_key('l.dt_venc') }} as data_vencimento_key,
    {{ date_key('l.dt_vencorig') }} as data_vencimento_original_key,
    {{ date_key('l.dt_movbanc') }} as data_movimento_bancario_key,
    l.numdoc,
    l.historico,
    l.tipo_titulo,
    l.status,
    l.is_dre,
    l.tipo_movimento_socio,
    l.is_inss_compensado,
    l.apconta,
    l.valor_previsto,
    l.valor_compromissado,
    l.valor_efetuado,
    (l.valor_compromissado + l.valor_efetuado)::numeric(16,2) as valor_total,
    l.tx_adm_prev,
    l.tx_adm_comp,
    l.tx_adm_efetu,
    l.updated_at,
    current_timestamp::timestamp as dbt_loaded_at
from
    {{ ref('int_lancamento_classificado') }} as l
left join 
    {{ ref('dim_obra') }} as o 
        on o.obra_key = l.numero_obra
left join 
    {{ ref('dim_conta') }} as c 
        on c.codigo_conta = l.codigo_conta
left join 
{{ ref('dim_empresa') }} as cp 
    on cp.empresa_key = l.contraparte_id
left join 
    {{ ref('dim_empresa') }} as rp 
        on rp.razao_social = l.empresa_recbto_pagto
left join 
    {{ ref('dim_operacao') }} as op 
        on op.op_codigo = l.op_codigo

{% if is_incremental() %}
where l.updated_at > (select 
                        max(updated_at) - interval 
                        '{{ var("incremental_lookback_days") }} days'
                        from {{ this }})
  {%  if var('reprocess_from_month') %}
  or l.dt_competencia >= date '{{ var("reprocess_from_month") }}'
  {% endif %}
{% endif %}