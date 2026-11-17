select
    o.op_codigo as operacao_key,
    o.op_codigo,
    o.descricao_operacao,
    coalesce(c.categoria, 'NAO_CLASSIFICADA') as categoria_operacao
from 
    {{ ref('stg_operacao') }} as o
left join
    {{ ref('categoria_operacao')}} as c
        on c.op_codigo = o.op_codigo

union all

select
    -1,
    -1,
    'NÃO INFORMADA',
    'NAO_CLASSIFICADA'