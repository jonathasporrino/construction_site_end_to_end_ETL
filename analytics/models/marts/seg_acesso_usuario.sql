-- Row-level security map for Power BI (user e-mail -> business units). '*' = all units.
-- Fictitious e-mails: replace the seed with the real list (the original project never received it).
select 
    a.email, 
    o.unidade_negocio
from {{ ref('acesso_usuario') }} as a
join 
    (select distinct unidade_negocio 
    from {{ ref('dim_obra') }} 
    where unidade_negocio is not null) as o
  on a.unidade_negocio in ('*', o.unidade_negocio)
