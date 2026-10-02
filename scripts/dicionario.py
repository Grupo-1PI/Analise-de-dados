from __future__ import annotations

import csv
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'dados'
DICTIONARY_DIR = DATA_DIR / 'dicionarios'

DATASETS = {
    'censo_bronze': {
        'camada': 'bronze',
        'descricao': 'Dados de população por idade capturados da API do Censo 2022.',
        'granularidade': 'Uma linha por faixa de idade retornada para o município.',
        'campos': [
            ('Codigo_idade', 'código (texto)', 'Código da categoria de idade do IBGE.', 'Código preservado da API.'),
            ('Idade', 'texto', 'Rótulo da categoria de idade.', 'Valor conforme retornado pela API.'),
            ('Populacao_2022', 'inteiro', 'População contabilizada na categoria em 2022.', 'Valor numérico inteiro ou vazio na origem.'),
            ('Codigo_municipio', 'código (texto)', 'Código IBGE do município.', 'Identificador municipal preservado da API.'),
            ('Municipio', 'texto', 'Nome do município informado pela API.', 'Valor conforme retornado pela API.'),
        ],
    },
    'pns_bronze': {
        'camada': 'bronze',
        'descricao': 'Variáveis selecionadas dos microdados da Pesquisa Nacional de Saúde 2019.',
        'granularidade': 'Uma linha por registro individual dos microdados.',
        'campos': [
            ('V0001', 'código (texto)', 'Código da unidade da federação.', 'Código IBGE de UF com dois dígitos.'),
            ('V0024', 'código (texto)', 'Código do estrato amostral da PNS.', 'Código preservado dos microdados.'),
            ('UPA_PNS', 'código (texto)', 'Código da unidade primária de amostragem.', 'Identificador preservado dos microdados.'),
            ('C008', 'inteiro (texto na origem)', 'Idade da pessoa em anos.', 'Campo numérico conforme código original da PNS.'),
            ('Q084', 'código (texto)', 'Resposta original à pergunta usada para identificar dor crônica.', '1 = sim; 2 = não; vazio = sem resposta.'),
            ('V00291', 'decimal (texto na origem)', 'Peso amostral da pessoa na PNS.', 'Valor numérico conforme fornecido nos microdados.'),
        ],
    },
    'censo_silver': {
        'camada': 'silver',
        'descricao': 'População do Censo 2022 tratada e organizada por faixa etária.',
        'granularidade': 'Uma linha por faixa etária de São Caetano do Sul.',
        'campos': [
            ('faixa_etaria', 'texto', 'Faixa etária normalizada.', 'Rótulo padronizado em minúsculas e com sublinhados.'),
            ('qtd_amostra', 'inteiro', 'Quantidade de pessoas na faixa etária.', 'Inteiro maior ou igual a zero.'),
            ('municipio', 'texto', 'Município ao qual os dados se referem.', 'Valor fixo SCS-SP.'),
        ],
    },
    'pns_silver': {
        'camada': 'silver',
        'descricao': 'Registros da PNS 2019 tratados para análise de dor crônica.',
        'granularidade': 'Uma linha por pessoa com resposta válida à pergunta de dor crônica.',
        'campos': [
            ('uf', 'texto', 'Sigla da unidade da federação da pessoa.', 'Sigla válida de UF brasileira.'),
            ('codigo_upa', 'código (texto)', 'Código da unidade primária de amostragem.', 'Identificador preservado como texto.'),
            ('idade', 'inteiro (texto)', 'Idade da pessoa em anos.', 'Inteiro não negativo; zeros à esquerda removidos.'),
            ('dor_cronica', 'binário (texto)', 'Indica se a pessoa declarou dor crônica.', '1 = sim; 0 = não; sem valores vazios.'),
            ('peso_amostral_pns', 'inteiro (texto)', 'Peso amostral arredondado da pessoa.', 'Inteiro não negativo, arredondado para o inteiro mais próximo.'),
        ],
    },
}


def write_dictionary(name: str, dataset: dict[str, object]) -> Path:
    layer = str(dataset['camada'])
    csv_path = DATA_DIR / layer / f'{name}.csv'
    fields = dataset['campos']

    with csv_path.open(encoding='utf-8-sig', newline='') as source:
        actual_fields = next(csv.reader(source))

    expected_fields = [field[0] for field in fields]
    if actual_fields != expected_fields:
        raise ValueError(
            f'Esquema inesperado em {csv_path}: '
            f'esperado {expected_fields}, encontrado {actual_fields}.'
        )

    dictionary = {
        'base': name,
        'camada': layer,
        'arquivo': str(csv_path.relative_to(ROOT)).replace('\\', '/'),
        'descricao': dataset['descricao'],
        'granularidade': dataset['granularidade'],
        'campos': [
            {
                'campo': field_name,
                'tipo': field_type,
                'descricao': description,
                'regra': rule,
            }
            for field_name, field_type, description, rule in fields
        ],
    }

    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DICTIONARY_DIR / f'{name}_dicionario.json'
    with output_path.open('w', encoding='utf-8') as output:
        json.dump(dictionary, output, ensure_ascii=False, indent=2)
        output.write('\n')
    return output_path


def main() -> None:
    for name, dataset in DATASETS.items():
        output_path = write_dictionary(name, dataset)
        print(f'Dicionário salvo: {output_path}')


if __name__ == '__main__':
    main()