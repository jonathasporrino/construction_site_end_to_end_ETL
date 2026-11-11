select 
    numero_obra,
    socio_seq,
    empresa_id,
    pct_participacao,
    pct_tac
from {{ source('erp', 'obra_socio') }}