-- SCD Type 1: attributes always reflect the current ERP state. Key -1 = unknown member.
select
    numero_obra as obra_key,
    numero_obra,
    descricao_obra,
    tipo_obra,
    tipo_cliente,
    grupo,
    unidade_negocio,
    controle,
    gerente,
    uf,
    cliente,
    pct_empresa_parceira,
    valor_contrato,
    pct_fisico_executado,
    credito_inss,
    contas_inss,
    dt_inicio,
    dt_fim,
    is_ativa,
    tipo_obra = 'ADMINISTRATIVO' as is_centro_administrativo  -- hypothesis for the original NÚMERO 1/100-179 filter
from {{ ref('stg_obra') }}

union all

select 
    -1, 
    -1, 
    'NÃO INFORMADA', 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    null, 
    false, 
    false
