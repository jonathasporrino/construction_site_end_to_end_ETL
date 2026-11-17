-- P&L by work and month: use it to check Power BI totals against SQL.
select 
    o.descricao_obra, 
    d.ano_mes, 
    c.natureza, 
    sum(f.valor_efetuado) as efetuado, 
    sum(f.valor_compromissado) as compromissado, 
    sum(f.valor_total) as total
from {{ ref('fct_lancamento') }} f
join {{ ref('dim_obra') }} o using (obra_key)
join {{ ref('dim_conta') }} c using (conta_key)
join {{ ref('dim_date') }} d on d.date_key = f.data_competencia_key
where f.is_dre
group by 1, 2, 3
order by 1, 2, 3
