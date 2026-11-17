select
    p.codigo_conta::bigint as conta_key,
    p.codigo_conta,
    p.descricao_conta,
    -- rules doc: revenue = accounts starting with 1, expense = starting with 2 (replaces the hard-coded M list)
    case left(p.codigo_conta, 1)
        when '1' then 'RECEITA'
        when '2' then 'DESPESA'
        else 'FORA_DRE'
    end as natureza,
    g1.codigo_grupo as nivel1_codigo, 
    g1.descricao_grupo as nivel1_descricao,
    g2.codigo_grupo as nivel2_codigo,
    g2.descricao_grupo as nivel2_descricao,
    g3.codigo_grupo as nivel3_codigo, 
    g3.descricao_grupo as nivel3_descricao
from 
    {{ ref('stg_plano_contas')}} as p
left join
    {{ ref('plano_contas_grupo') }} as g1 on g1.codigo_grupo = left(p.codigo_conta,1)
left join
    {{ ref('plano_contas_grupo') }} as g2 
        on g2.codigo_grupo = left(p.codigo_conta,4)
left join
    {{ ref('plano_contas_grupo') }} as g3 
        on g3.codigo_grupo = left(p.codigo_conta,6)

union all
        
select
    -1,
    '-1',
    'NÃO INFORMADA', 
    'FORA_DRE',
    null,
    null,
    null,
    null,
    null,
    null