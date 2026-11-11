select
    op_codigo,
    descricao as descricao_operacao
from {{ source('erp', 'operacao')}}