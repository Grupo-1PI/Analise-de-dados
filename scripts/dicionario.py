from __future__ import annotations

import csv
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
            ('Codigo_idade', 'string', 'Identificador da categoria etária usado pelo IBGE para distinguir cada faixa ou totalização.', 'Código obrigatório e único para cada categoria etária.'),
            ('Idade', 'string', 'Faixa ou categoria etária associada ao total populacional, como idade em anos ou grupo de idades.', 'Rótulo da classificação do Censo 2022; pode incluir categorias agregadas além das idades detalhadas.'),
            ('Populacao_2022', 'int', 'Número de habitantes contabilizados na categoria etária para o município em 2022.', 'Número inteiro maior ou igual a zero; pode ficar vazio se não houver valor na fonte.'),
            ('Codigo_municipio', 'string', 'Código geográfico de sete dígitos que identifica o município na divisão territorial do IBGE.', 'Código IBGE de sete dígitos, mantido como texto para preservar zeros à esquerda.'),
            ('Municipio', 'string', 'Nome do município ao qual pertencem as contagens populacionais.', 'Deve estar preenchido e corresponder ao código do município.'),
        ],
    },
    'pns_bronze': {
        'camada': 'bronze',
        'descricao': 'Variáveis selecionadas dos microdados da Pesquisa Nacional de Saúde 2019.',
        'granularidade': 'Uma linha por registro individual dos microdados.',
        'campos': [
            ('V0001', 'string', 'Código numérico da unidade da federação onde a entrevista foi realizada.', 'Código composto por dois dígitos; na base tratada é convertido para a sigla da UF.'),
            ('V0024', 'string', 'Identificador do estrato amostral ao qual a observação da pesquisa pertence.', 'Código obrigatório, preservado como texto.'),
            ('UPA_PNS', 'string', 'Identificador da unidade primária de amostragem (UPA) da entrevista.', 'Código obrigatório, preservado como texto para manter zeros à esquerda.'),
            ('C008', 'int', 'Idade declarada pelo participante, em anos.', 'Valor numérico inteiro; na base tratada são removidos zeros à esquerda.'),
            ('Q084', 'string', 'Resposta do participante à pergunta da PNS sobre dor crônica.', 'Aceita 1 (sim), 2 (não) ou vazio; na base tratada vazio é excluído e 2 é recodificado para 0.'),
            ('V00291', 'dec', 'Peso amostral associado ao participante, usado para representar a população no desenho da pesquisa.', 'Valor numérico decimal não negativo; na base tratada é arredondado para o inteiro mais próximo.'),
        ],
    },
    'censo_silver': {
        'camada': 'silver',
        'descricao': 'População do Censo 2022 tratada e organizada por faixa etária.',
        'granularidade': 'Uma linha por faixa etária de São Caetano do Sul.',
        'campos': [
            ('faixa_etaria', 'string', 'Grupo etário detalhado usado para organizar a população, expresso em meses ou anos completos.', 'Uma linha por faixa etária detalhada, rótulos em minúsculas, sem acentos e com sublinhados.'),
            ('qtd_amostra', 'int', 'Quantidade de habitantes do município que pertence à faixa etária indicada.', 'Número inteiro maior ou igual a zero.'),
            ('municipio', 'string', 'Município ao qual todas as contagens da tabela se referem: São Caetano do Sul, SP.', 'Usar a sigla da cidade, hífen e sigla do estado. Neste conjunto, SCS-SP.'),
        ],
    },
    'pns_silver': {
        'camada': 'silver',
        'descricao': 'Registros da PNS 2019 tratados para análise de dor crônica.',
        'granularidade': 'Uma linha por pessoa com resposta válida à pergunta de dor crônica.',
        'campos': [
            ('uf', 'string', 'Sigla da unidade da federação onde foi realizada a entrevista.', 'Deve conter uma sigla válida de UF brasileira.'),
            ('codigo_upa', 'string', 'Código da Unidade Primária de Amostragem (UPA) da PNS, unidade do desenho amostral identificada nos microdados; não se refere a uma Unidade de Pronto Atendimento.', 'Código obrigatório, preservado como texto.'),
            ('idade', 'int', 'Idade do participante em anos, conforme registrada na pesquisa.', 'Número inteiro maior ou igual a zero; zeros à esquerda são removidos.'),
            ('dor_cronica', 'int', 'Indica se o participante respondeu afirmativamente à pergunta sobre dor crônica.', 'Aceita somente 1 (sim) ou 0 (não); respostas sem valor são excluídas.'),
            ('peso_amostral_pns', 'int', 'Peso amostral do participante após arredondamento, que permite ponderar sua representação na população.', 'Número inteiro não negativo, arredondado para o inteiro mais próximo.'),
        ],
    },
}

DICTIONARY_COLUMNS = [
    'regra_campo', 'tipo', 'descricao_campo', 'campo',
]


def write_dictionary(name: str, dataset: dict[str, object]) -> Path:
    layer = str(dataset['camada'])
    data_path = DATA_DIR / layer / f'{name}.csv'
    with data_path.open(encoding='utf-8-sig', newline='') as source:
        actual_fields = next(csv.reader(source))

    fields = dataset['campos']
    expected_fields = [field[0] for field in fields]
    if actual_fields != expected_fields:
        raise ValueError(
            f'Esquema inesperado em {data_path}: '
            f'esperado {expected_fields}, encontrado {actual_fields}.'
        )

    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DICTIONARY_DIR / f'{name}_dicionario.csv'
    columns = DICTIONARY_COLUMNS if layer == 'silver' else [
        column for column in DICTIONARY_COLUMNS if column != 'regra_campo'
    ]
    with output_path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.DictWriter(output, fieldnames=columns, delimiter=';')
        writer.writeheader()
        for field_name, field_type, description, rule in fields:
            row = {
                'regra_campo': rule if layer == 'silver' else '',
                'tipo': field_type,
                'descricao_campo': description,
                'campo': field_name,
            }
            row = {
                column: value.replace(';', ',') if isinstance(value, str) else value
                for column, value in row.items()
            }
            writer.writerow({column: row[column] for column in columns})
    return output_path


def main() -> None:
    for name, dataset in DATASETS.items():
        output_path = write_dictionary(name, dataset)
        print(f'Dicionário salvo: {output_path}')


if __name__ == '__main__':
    main()
