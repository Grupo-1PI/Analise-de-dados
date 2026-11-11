from __future__ import annotations

import math
import re
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
SILVER_DIR = ROOT / 'dados' / 'silver'
GOLD_DIR = ROOT / 'dados' / 'gold'
MINIMUM_SAMPLE_SIZE = 30
AGE_BANDS = [
    '0-9',
    '10-14',
    '15-19',
    '20-29',
    '30-39',
    '40-49',
    '50-59',
    '60-69',
    '70-79',
    '80-89',
    '90+',
]
def create_age_band(age: int) -> str:
    if age < 0:
        raise ValueError(f'Idade inválida: {age}')
    if age < 10:
        return '0-9'
    if age < 15:
        return '10-14'
    if age < 20:
        return '15-19'
    if age >= 90:
        return '90+'
    lower_bound = age // 10 * 10
    return f'{lower_bound}-{lower_bound + 9}'


def census_label_to_age(label: str) -> int:
    if label == 'menos_de_1_mes':
        return 0
    if label == '100_ano_ou_mais':
        return 100
    match = re.fullmatch(r'(\d+)_(?:mes|ano)', label)
    if not match:
        raise ValueError(f'Categoria etária do Censo não reconhecida: {label!r}')
    value = int(match.group(1))
    return 0 if label.endswith('_mes') else value


def load_pns_sp() -> pd.DataFrame:
    source_path = SILVER_DIR / 'pns_silver.csv'
    pns = pd.read_csv(
        source_path,
        dtype=str,
        keep_default_na=False,
        encoding='utf-8-sig',
        usecols=[
            'uf',
            'codigo_upa',
            'idade',
            'dor_cronica',
            'peso_amostral_pns',
        ],
    )
    pns = pns.loc[pns['uf'].str.strip().eq('SP')].copy()
    if pns.empty:
        raise ValueError(f'A base Silver da PNS não contém respostas de SP: {source_path}')

    pns['idade'] = pd.to_numeric(pns['idade'], errors='raise')
    if (pns['idade'] % 1 != 0).any():
        raise ValueError('A base Silver contém idades que não são números inteiros.')
    pns['idade'] = pns['idade'].astype(int)
    if (pns['idade'] < 15).any():
        raise ValueError('A base Silver da PNS contém idades abaixo de 15 anos.')
    pns['faixa_etaria'] = pns['idade'].map(create_age_band)

    pns['dor_cronica'] = pd.to_numeric(pns['dor_cronica'], errors='raise')
    if not pns['dor_cronica'].isin([0, 1]).all():
        raise ValueError('A base Silver contém respostas de dor crônica inválidas.')

    pns['peso_amostral_pns'] = pd.to_numeric(
        pns['peso_amostral_pns'], errors='raise'
    )
    if (
        not pns['peso_amostral_pns'].notna().all()
        or (pns['peso_amostral_pns'] <= 0).any()
    ):
        raise ValueError('A base Silver contém pesos amostrais inválidos.')
    return pns


def load_census_sao_caetano() -> pd.DataFrame:
    source_path = SILVER_DIR / 'censo_silver.csv'
    census = pd.read_csv(
        source_path,
        dtype=str,
        keep_default_na=False,
        encoding='utf-8-sig',
        usecols=['faixa_etaria', 'qtd_amostra', 'municipio'],
    )
    if census.empty:
        raise ValueError(f'A base Silver do Censo está vazia: {source_path}')
    if set(census['municipio']) != {'SCS-SP'}:
        raise ValueError('A base Silver do Censo não corresponde apenas a SCS-SP.')

    census['idade_base'] = census['faixa_etaria'].map(census_label_to_age)
    census['faixa_etaria'] = census['idade_base'].map(create_age_band)
    census['qtd_amostra'] = pd.to_numeric(census['qtd_amostra'], errors='raise')
    if (census['qtd_amostra'] < 0).any():
        raise ValueError('A base Silver do Censo contém populações negativas.')
    population = (
        census.groupby('faixa_etaria', as_index=False, sort=False)
        .agg(populacao_sao_caetano=('qtd_amostra', 'sum'))
    )
    population['faixa_etaria'] = pd.Categorical(
        population['faixa_etaria'],
        categories=AGE_BANDS,
        ordered=True,
    )
    return population.sort_values('faixa_etaria').reset_index(drop=True)


def aggregate_sp_prevalence(pns: pd.DataFrame) -> pd.DataFrame:
    pns = pns.assign(
        peso_com_dor_ponderado=pns['peso_amostral_pns'] * pns['dor_cronica']
    )
    prevalence = (
        pns.groupby('faixa_etaria', as_index=False, sort=False)
        .agg(
            respondentes_pns_sp=('dor_cronica', 'size'),
            respondentes_com_dor_pns_sp=('dor_cronica', 'sum'),
            upas_amostra_pns_sp=('codigo_upa', 'nunique'),
            peso_total_ponderado=('peso_amostral_pns', 'sum'),
            peso_com_dor_ponderado=('peso_com_dor_ponderado', 'sum'),
        )
    )
    prevalence['prevalencia_dor_cronica_sp_pct'] = (
        100
        * prevalence['peso_com_dor_ponderado']
        / prevalence['peso_total_ponderado']
    ).round(2)
    prevalence['faixa_etaria'] = pd.Categorical(
        prevalence['faixa_etaria'],
        categories=AGE_BANDS,
        ordered=True,
    )
    prevalence['status_estimativa'] = 'OK'
    prevalence.loc[
        prevalence['respondentes_pns_sp'] < MINIMUM_SAMPLE_SIZE,
        'status_estimativa',
    ] = 'AMOSTRA_PEQUENA_SP'
    return prevalence.sort_values('faixa_etaria').reset_index(drop=True)


def combine_population_and_prevalence(
    population: pd.DataFrame,
    prevalence: pd.DataFrame,
) -> pd.DataFrame:
    gold = population.merge(
        prevalence,
        on='faixa_etaria',
        how='left',
        validate='one_to_one',
    )
    gold['faixa_etaria'] = gold['faixa_etaria'].astype(str)
    gold['status_estimativa'] = gold['status_estimativa'].fillna(
        'SEM_DADO_PNS_PARA_FAIXA'
    )
    gold['status_estimativa'] = gold['status_estimativa'].replace(
        'nan', 'SEM_DADO_PNS_PARA_FAIXA'
    )
    usable = gold['status_estimativa'].eq('OK')
    gold['estimativa_pessoas_com_dor'] = pd.NA
    gold.loc[usable, 'estimativa_pessoas_com_dor'] = gold.loc[
        usable
    ].apply(
        lambda row: math.floor(
            row['populacao_sao_caetano']
            * row['prevalencia_dor_cronica_sp_pct']
            / 100
            + 0.5
        ),
        axis=1,
    )
    gold['estimativa_pessoas_com_dor'] = gold[
        'estimativa_pessoas_com_dor'
    ].astype('Int64')
    return gold.loc[~gold['faixa_etaria'].isin(['0-9', '10-14']), [
        'faixa_etaria',
        'populacao_sao_caetano',
        'prevalencia_dor_cronica_sp_pct',
        'estimativa_pessoas_com_dor',
    ]].copy()


def main() -> None:
    GOLD_DIR.mkdir(parents=True, exist_ok=True)
    pns = load_pns_sp()
    population = load_census_sao_caetano()
    prevalence = aggregate_sp_prevalence(pns)
    gold = combine_population_and_prevalence(population, prevalence)
    output_path = GOLD_DIR / 'censo-pns_gold.csv'
    gold.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f'Arquivo Gold salvo: {output_path}')


if __name__ == '__main__':
    main()
