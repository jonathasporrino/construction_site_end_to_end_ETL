-- Every work's current partner shares must add up to 100%.
select 
    obra_key, 
    sum(pct_participacao) as total
from {{ ref('bridge_obra_socio') }}
where is_current
group by obra_key
having abs(sum(pct_participacao) - 1) > 0.0001
