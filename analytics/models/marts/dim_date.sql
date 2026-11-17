with spine as(
    {{ dbt_utils.date_spine(datepart="day",
                            start_date="cast('2022-01-01' as date)",
                            end_date="cast('2031-01-01' as date)")}}
)
select
    {{ date_key('date_day') }} as date_key,
    date_key::date as data,
    extract(year from date_day)::int as ano,
    extract(month from date_day)::int as mes_num,
    case month(date_day) 
        when 1 then 'Jan' 
        when 2 then 'Fev' 
        when 3 then 'Mar' 
        when 4 then 'Abr' 
        when 5 then 'Mai' 
        when 6 then 'Jun'
        when 7 then 'Jul' 
        when 8 then 'Ago' 
        when 9 then 'Set' 
        when 10 then 'Out' 
        when 11 then 'Nov' 
        else 'Dez' 
    end as mes_nome,
    extract(quarter from date_day)::int as trimestre,
    (extract(year from date_day) * 100 + extract(month from date_day))::int as ano_mes,
    strftime(date_day, '%m/%Y') as mes_ano,
    isodow(date_day) as dia_semana,
    case isodow(date_day) 
        when 1 then 'Segunda' 
        when 2 then 'Terça' 
        when 3 then 'Quarta' 
        when 4 then 'Quinta'
        when 5 then 'Sexta' 
        when 6 then 'Sábado' 
        else 'Domingo' 
    end as nome_dia,
    date_trunc('month', date_day)::date as inicio_mes
from spine