select
    lancamento_id,
    numero_obra,
    plano_conta as codigo_conta,
    contraparte_id,
    trim(empresa) as empresa,
    trim(empresa_recbto_pagto) as empresa_recbto_pagto,
    numdoc,
    dt_doc,
    dt_venc,
    dt_vencorig,
    dt_movbanc,
    -- competence rule kept from the original model: paid -> bank date, open -> original due date
    case when status = 'REALIZADO' 
            then dt_movbanc 
        else dt_vencorig 
    end as dt_competencia,
    historico,
    op_codigo,
    ri,
    valor_previsto,
    valor_compromissado,
    valor_efetuado,
    tx_adm_prev,
    tx_adm_comp,
    tx_adm_efetu,
    aprec as tipo_titulo,
    apconta,
    status,
    created_at,
    updated_at
from {{ source( 'erp', 'lancamento')}}