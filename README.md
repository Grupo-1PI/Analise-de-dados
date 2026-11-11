# Analise-de-dados

## Pipeline de dados

Execute os scripts na ordem abaixo, a partir da raiz do projeto:

```powershell
.\.venv\Scripts\python.exe scripts\bronze.py
.\.venv\Scripts\python.exe scripts\silver.py
.\.venv\Scripts\python.exe scripts\gold.py
```

O Gold cruza a população de São Caetano do Sul com a prevalência de dor crônica observada na amostra da PNS para São Paulo, usando faixas etárias compatíveis. Ele gera um único arquivo em `dados/gold/censo-pns_gold.csv`, contendo as faixas a partir de `15-19` e os campos `faixa_etaria`, `populacao_sao_caetano`, `prevalencia_dor_cronica_sp_pct` e `estimativa_pessoas_com_dor`.

A prevalência é ponderada pelos pesos amostrais da PNS. A estimativa de pessoas com dor é calculada aplicando essa prevalência à população de São Caetano da mesma faixa etária; é uma projeção de referência, não uma contagem observada de pessoas com dor no município.