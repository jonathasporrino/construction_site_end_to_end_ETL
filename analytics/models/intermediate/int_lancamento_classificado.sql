-- Adds business classification used by the marts: P&L scope and movement category.
select
    l.*,
    left(l.codigo_conta, 1) in('1', '2') as is_dre,
    coalesce(c.categoria, 'NAO_CLASSIFICADA') as categoria_operacao,
    case
        when c.categoria = 'APORTE' and l.codigo_conta = '300101002'
            then 'DEVOLUCAO_APORTE'
        when c.categoria = 'APORTE'
            then 'APORTE'
        else c.categoria
    end as tipo_movimento_socio,
    -- INSS offset: SCP work paying through one of its INSS accounts (was a hard-coded APCONTA list in DAX)
    coalesce(o.tipo_obra = 'SCP' and 
            ('|'|| o.contas_inss || '|')
            like ('%|' ||  l.apconta || '|%'), false) as is_inss_compensado
from {{ ref('stg_lancamento')}} as l
left join {{ ref('categoria_operacao') }} as c on c.op_codigo = l.op_codigo
left join {{ ref('stg_obra') }} as o on o.numero_obra = l.numero_obra
     
