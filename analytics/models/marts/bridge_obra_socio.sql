-- Partners of each work with SCD Type 2 validity (from the snapshot). Filter is_current for today's shares.
select
    {{ dbt_utils.generate_surrogate_key(['numero_obra', 'socio_seq', 'dbt_valid_from']) }} as obra_socio_key,
    numero_obra as obra_key,
    empresa_id as empresa_key,
    socio_seq,
    pct_participacao,
    pct_tac,
    dbt_valid_from as valido_de,
    dbt_valid_to as valido_ate,
    dbt_valid_to is null as is_current
from {{ ref('snap_obra_socio') }}