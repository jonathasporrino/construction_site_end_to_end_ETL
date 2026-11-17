-- The month saved by the latest run must match the fact at that cut. Older saved months may differ on purpose:
-- they are frozen versions, and later ERP edits must not change them.
with ultimo as (
    select max(mes_referencia) as mes 
    from {{ ref('fct_posicao_economica_mensal') }}
    where salvo_em = (
        select max(salvo_em) 
        from {{ ref('fct_posicao_economica_mensal') }})
),
corte as (
    select 
        {{ date_key("(mes + interval '1 month' - interval '1 day')") }} as k, 
        mes 
    from ultimo),
pos as (
    select 
        sum(valor_efetuado_acumulado) as v 
    from {{ ref('fct_posicao_economica_mensal') }}
    where mes_referencia = (
        select mes 
        from ultimo)
),
fct as (
    select 
        sum(valor_previsto) as v 
    from {{ ref('fct_lancamento') }}
    where is_dre 
        and data_movimento_bancario_key <= (select k from corte)
        and data_documento_key <= (select k from corte)
)
select 
    pos.v as posicao, 
    fct.v as fato 
from 
    pos, 
    fct 
where pos.v is distinct from fct.v
