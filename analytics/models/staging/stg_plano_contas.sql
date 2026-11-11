select
    codigo as codigo_conta,
    descricao as descricao_conta,
    regra_classificacao,
    natureza
from {{ source('erp', 'plano_contas')}}