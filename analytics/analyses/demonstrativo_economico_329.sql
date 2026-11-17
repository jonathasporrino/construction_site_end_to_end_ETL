-- Reproduces the layout of the ERP report "3.29 - Demonstrativo Sintético Econômico do Período" for one work:
-- one line per account level (1, 2, 3 and analytic), Comp. / Efetuado / Total, % of the revenue or expense total,
-- then Saldo (A - B) and % Resultado = Saldo / Total Receitas.
-- dbt compile -s demonstrativo_economico_329 --vars '{obra: 9070, de: "2023-01-01", ate: "2025-10-05"}'
{% set obra = var('obra', 9070) %}
{% set de = var('de', '2000-01-01') %}
{% set ate = var('ate', '2100-12-31') %}

with base as (
    select c.natureza, 
           c.nivel1_codigo, 
           c.nivel1_descricao, 
           c.nivel2_codigo, 
           c.nivel2_descricao,
           c.nivel3_codigo, 
           c.nivel3_descricao, 
           c.codigo_conta, 
           c.descricao_conta,
           f.valor_compromissado, 
           f.valor_efetuado, 
           f.valor_total
    from {{ ref('fct_lancamento') }} f
    join {{ ref('dim_conta') }} c using (conta_key)
    where f.obra_key = {{ obra }} 
        and f.is_dre
        and f.data_competencia_key between {{ de | replace('-', '') }} 
        and {{ ate | replace('-', '') }}
),
linhas as (
    select 
        natureza, 
        nivel1_codigo as codigo, 
        nivel1_descricao as descricao, 
        sum(valor_compromissado) comp, 
        sum(valor_efetuado) efet, 
        sum(valor_total) total 
    from base 
    group by 1, 2, 3
    
union all 
    select 
        natureza, 
        nivel2_codigo, 
        nivel2_descricao, 
        sum(valor_compromissado), 
        sum(valor_efetuado), 
        sum(valor_total) 
    from base 
    group by 1, 2, 3
    
union all 
    select 
        natureza, 
        nivel3_codigo, 
        nivel3_descricao, 
        sum(valor_compromissado), 
        sum(valor_efetuado), 
        sum(valor_total) 
    from base 
    group by 1, 2, 3

union all 
    select 
        natureza, 
        codigo_conta, 
        descricao_conta, 
        sum(valor_compromissado), 
        sum(valor_efetuado), 
        sum(valor_total) 
    from base 
    group by 1, 2, 3
),
totais as (
    select natureza, 
    sum(valor_total) as total 
    from base 
    group by 1
)
select 
    l.codigo, 
    l.descricao, 
    l.comp, 
    l.efet, 
    l.total, 
    round(100 * l.total / nullif(t.total, 0), 4) as pct
from linhas l 
join totais t using (natureza)

union all
    select 'Saldo (A - B)', 
    null,
   sum(case natureza when 'RECEITA' then valor_compromissado else -valor_compromissado end),
   sum(case natureza when 'RECEITA' then valor_efetuado else -valor_efetuado end),
   sum(case natureza when 'RECEITA' then valor_total else -valor_total end),
   round(100 * sum(
       case natureza 
            when 'RECEITA' then valor_total 
            else -valor_total 
        end)
             / nullif(sum(
                case natureza 
                    when 'RECEITA' then valor_total 
                end), 0), 2)  -- % Resultado
from base
order by 1
