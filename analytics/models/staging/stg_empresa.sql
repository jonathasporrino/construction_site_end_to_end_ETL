select
    empresa_id,
    trim(razao_social) as razao_social,
    cnpj,
    tipo as tipo_empresa,
from {{ source('erp', 'empresa')}}