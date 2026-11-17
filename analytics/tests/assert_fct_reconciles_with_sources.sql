-- Fails if row count or any amount differs between the ERP source and the fact table.
with src as (
    select 
        count(*) as n, 
        sum(valor_previsto) as prev, 
        sum(valor_compromissado) as comp, 
        sum(valor_efetuado) as efet
    from {{ source('erp', 'lancamento') }}
), fct as (
    select count(*) as n, 
        sum(valor_previsto) as prev, 
        sum(valor_compromissado) as comp, 
        sum(valor_efetuado) as efet
    from {{ ref('fct_lancamento') }}
)
select * 
from 
src, fct
where src.n <> fct.n 
    or src.prev <> fct.prev 
    or src.comp <> fct.comp 
    or src.efet <> fct.efet