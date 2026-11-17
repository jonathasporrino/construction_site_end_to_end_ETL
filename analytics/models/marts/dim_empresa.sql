-- Role-playing dimension: counterpart, receiving/paying company and partner all use it.
select
    empresa_id as empresa_key,
    razao_social,
    cnpj,
    tipo_empresa
from {{ ref('stg_empresa')}}

union all

select 
    -1, 
    'NÃO INFORMADA', 
    null, 
    null