from __future__ import annotations

import csv
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / 'dados'
DICTIONARY_DIR = DATA_DIR / 'dicionarios'
SQL_SCHEMA_PATH = ROOT / 'script.sql'

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


def _clean_row(values: list[str]) -> list[str]:
    return [value.replace(';', ',') for value in values]


def write_layer_dictionary(
    layer: str,
    datasets: list[tuple[str, dict[str, object]]],
) -> Path:
    """Write one CSV containing all table blocks for a data layer."""
    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DICTIONARY_DIR / f'{layer}.csv'
    with output_path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, delimiter=';')
        for index, (name, dataset) in enumerate(datasets):
            writer.writerow([f'Tabela {name}'])
            if layer == 'silver':
                writer.writerow([
                    'regra_campo', 'tipo', 'descricao_campo', 'campo',
                ])
                for field_name, field_type, description, rule in dataset['campos']:
                    writer.writerow(_clean_row([
                        rule, str(field_type).upper(), description, field_name,
                    ]))
            else:
                writer.writerow(['tipo', 'descricao_campo', 'campo'])
                for field_name, field_type, description, _rule in dataset['campos']:
                    writer.writerow(_clean_row([
                        str(field_type).upper(), description, field_name,
                    ]))
            if index < len(datasets) - 1:
                writer.writerow([])
                writer.writerow([])
    return output_path


SYSTEM_FIELD_DESCRIPTIONS = {
    'id': 'Identificador unico do registro.',
    'nome': 'Nome do registro.',
    'descricao': 'Descricao do registro.',
    'cep': 'Codigo postal do endereco.',
    'logradouro': 'Rua, avenida ou via do endereco.',
    'bairro': 'Bairro do endereco.',
    'cidade': 'Cidade do endereco.',
    'uf': 'Sigla da unidade federativa.',
    'numero': 'Numero do endereco.',
    'complemento': 'Complemento do endereco, quando informado.',
    'telefone': 'Telefone de contato do usuario.',
    'email': 'Endereco de e-mail do usuario.',
    'senha': 'Hash da senha de autenticacao.',
    'data_nascimento': 'Data de nascimento do usuario.',
    'ativo': 'Indica se o usuario esta ativo (1=sim, 0=nao).',
    'data': 'Data da excecao na agenda.',
    'hora_inicio': 'Horario de inicio da disponibilidade ou excecao.',
    'hora_fim': 'Horario de termino da disponibilidade ou excecao.',
    'disponivel': 'Indica se o funcionario esta disponivel (1=sim, 0=nao).',
    'dia_semana': 'Dia da semana (MySQL DAYOFWEEK: 1=domingo a 7=sabado).',
    'observacao': 'Observacoes adicionais relacionadas ao registro.',
    'observacoes': 'Observacoes adicionais do atendimento.',
    'data_hora_inicio': 'Data e hora de inicio do agendamento.',
    'data_hora_fim': 'Data e hora de termino do agendamento.',
    'valor': 'Preco atual do servico.',
    'valor_unitario': 'Valor cobrado pelo servico neste atendimento.',
    'tempomedio': 'Duracao media estimada do servico, em minutos.',
}


def describe_system_field(table: str, field: str, body: str) -> str:
    if field.lower().startswith('fk'):
        reference = re.search(
            rf'FOREIGN KEY\s*\({re.escape(field)}\)\s*REFERENCES\s+(\w+)',
            body,
            re.IGNORECASE | re.DOTALL,
        )
        target = reference.group(1) if reference else field[2:].lower()
        return f'Chave estrangeira que referencia a tabela {target}.'
    if table == 'atendimento_servico' and field == 'descricao':
        return 'Descricao do servico realizado no atendimento.'
    if table == 'especialidade' and field == 'nome':
        return 'Nome da especialidade oferecida.'
    if table == 'status' and field == 'nome':
        return 'Nome do status do agendamento.'
    if table == 'cargo' and field == 'nome':
        return 'Nome do cargo do funcionario.'
    if table == 'servico' and field == 'nome':
        return 'Nome do servico oferecido.'
    return SYSTEM_FIELD_DESCRIPTIONS.get(
        field.lower(), f'Informacao de {field.replace("_", " ").lower()}.',
    )


SYSTEM_TABLES_FALLBACK = [('cargo',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(45)', 'Nome do cargo do funcionario.', 'nome'),
   ('VARCHAR(255)', 'Descricao do cargo ou item.', 'descricao')]),
 ('endereco',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(9)', 'Codigo postal do endereco.', 'cep'),
   ('VARCHAR(120)', 'Rua, avenida ou via do endereco.', 'logradouro'),
   ('VARCHAR(80)', 'Bairro do endereco.', 'bairro'),
   ('VARCHAR(80)', 'Cidade do endereco.', 'cidade'),
   ('VARCHAR(2)', 'Sigla da unidade federativa.', 'uf'),
   ('VARCHAR(10)', 'Numero do endereco.', 'numero'),
   ('VARCHAR(60)', 'Complemento do endereco, quando informado.', 'complemento')]),
 ('usuario',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(120)', 'Nome do registro.', 'nome'),
   ('VARCHAR(20)', 'Telefone de contato do usuario.', 'telefone'),
   ('VARCHAR(120)', 'Endereco de e-mail do usuario.', 'email'),
   ('VARCHAR(255)', 'Hash da senha de autenticacao.', 'senha'),
   ('DATE', 'Data de nascimento do usuario.', 'data_nascimento'),
   ('TINYINT(1)', 'Indica se o usuario esta ativo (1=sim, 0=nao).', 'ativo'),
   ('INT', 'Chave estrangeira que referencia a tabela endereco.', 'fkEndereco')]),
 ('funcionario',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('INT', 'Chave estrangeira que referencia a tabela usuario.', 'fkUsuario'),
   ('INT', 'Chave estrangeira que referencia a tabela cargo.', 'fkCargo')]),
 ('agenda_excecao',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('INT', 'Chave estrangeira que referencia a tabela funcionario.', 'fkFuncionario'),
   ('DATE', 'Data da excecao na agenda.', 'data'),
   ('TIME', 'Horario de inicio da disponibilidade ou excecao.', 'hora_inicio'),
   ('TIME', 'Horario de termino da disponibilidade ou excecao.', 'hora_fim'),
   ('TINYINT(1)',
    'Indica se o funcionario esta disponivel no periodo (1=sim, 0=nao).',
    'disponivel')]),
 ('agenda_funcionario',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('INT', 'Chave estrangeira que referencia a tabela funcionario.', 'fkFuncionario'),
   ('INT', 'Dia da semana (MySQL DAYOFWEEK: 1=domingo a 7=sabado).', 'dia_semana'),
   ('TIME', 'Horario de inicio da disponibilidade ou excecao.', 'hora_inicio'),
   ('TIME', 'Horario de termino da disponibilidade ou excecao.', 'hora_fim')]),
 ('cliente',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('INT', 'Chave estrangeira que referencia a tabela usuario.', 'fkUsuario'),
   ('VARCHAR(255)', 'Observacoes adicionais relacionadas ao registro.', 'observacao')]),
 ('sala',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(255)', 'Descricao do cargo ou item.', 'descricao')]),
 ('status',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(45)', 'Nome do status do agendamento.', 'nome')]),
 ('agendamento',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('DATETIME', 'Data e hora de inicio do agendamento.', 'data_hora_inicio'),
   ('DATETIME', 'Data e hora de termino do agendamento.', 'data_hora_fim'),
   ('VARCHAR(255)', 'Observacoes adicionais relacionadas ao registro.', 'observacao'),
   ('INT', 'Chave estrangeira que referencia a tabela cliente.', 'fkCliente'),
   ('INT', 'Chave estrangeira que referencia a tabela sala.', 'fkSala'),
   ('INT', 'Chave estrangeira que referencia a tabela status.', 'fkStatus')]),
 ('funcionario_agendamento',
  [('INT', 'Chave estrangeira que referencia a tabela funcionario.', 'fkFuncionario'),
   ('INT', 'Chave estrangeira que referencia a tabela agendamento.', 'fkAgendamento')]),
 ('servico',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(100)', 'Nome do servico oferecido.', 'nome'),
   ('DECIMAL(10,2)', 'Preco atual do servico.', 'valor'),
   ('VARCHAR(255)', 'Descricao do cargo ou item.', 'descricao'),
   ('INT', 'Duracao media estimada do servico, em minutos.', 'tempoMedio')]),
 ('atendimento_servico',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('DECIMAL(10,2)', 'Valor cobrado pelo servico neste atendimento.', 'valor_unitario'),
   ('INT', 'Chave estrangeira que referencia a tabela servico.', 'fkServico'),
   ('INT', 'Chave estrangeira que referencia a tabela agendamento.', 'fkAgendamento'),
   ('VARCHAR(255)', 'Descricao do servico realizado no atendimento.', 'descricao'),
   ('VARCHAR(255)', 'Observacoes adicionais do atendimento.', 'observacoes')]),
 ('especialidade',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(60)', 'Nome da especialidade oferecida.', 'nome')]),
 ('especialidade_servico',
  [('INT', 'Chave estrangeira que referencia a tabela especialidade.', 'fkEspecialidade'),
   ('INT', 'Chave estrangeira que referencia a tabela servico.', 'fkServico')]),
 ('funcionario_especialidade',
  [('INT', 'Chave estrangeira que referencia a tabela funcionario.', 'fkFuncionario'),
   ('INT', 'Chave estrangeira que referencia a tabela especialidade.', 'fkEspecialidade')]),
 ('permissoes',
  [('INT', 'Identificador unico do registro.', 'id'),
   ('VARCHAR(45)', 'Nome do registro.', 'nome'),
   ('VARCHAR(255)', 'Descricao do cargo ou item.', 'descricao')]),
 ('permissoes_cargo',
  [('INT', 'Chave estrangeira que referencia a tabela permissoes.', 'fkPermissoes'),
   ('INT', 'Chave estrangeira que referencia a tabela cargo.', 'fkCargo')]),
 ('sala_servico',
  [('INT', 'Chave estrangeira que referencia a tabela sala.', 'fkSala'),
   ('INT', 'Chave estrangeira que referencia a tabela servico.', 'fkServico')])]


def read_system_tables() -> list[tuple[str, list[tuple[str, str, str]]]]:
    if not SQL_SCHEMA_PATH.exists():
        return SYSTEM_TABLES_FALLBACK

    sql = SQL_SCHEMA_PATH.read_text(encoding='utf-8')
    tables = []
    table_pattern = re.compile(
        r'CREATE TABLE IF NOT EXISTS\s+(\w+)\s*\((.*?)\n\);',
        re.IGNORECASE | re.DOTALL,
    )
    column_pattern = re.compile(
        r'\s*(\w+)\s+(TINYINT\(1\)|VARCHAR\(\d+\)|'
        r'DECIMAL\(\d+,\d+\)|INT|DATETIME|DATE|TIME)(?=\s|$)',
        re.IGNORECASE,
    )
    for table_match in table_pattern.finditer(sql):
        table, body = table_match.groups()
        fields = []
        for line in body.splitlines():
            column = column_pattern.match(line)
            if column:
                field, field_type = column.groups()
                fields.append((
                    field_type.upper(),
                    describe_system_field(table, field, body),
                    field,
                ))
        if fields:
            tables.append((table, fields))
    if not tables:
        raise ValueError(f'Nenhuma tabela encontrada em {SQL_SCHEMA_PATH}.')
    return tables


def write_system_dictionary() -> Path:
    DICTIONARY_DIR.mkdir(parents=True, exist_ok=True)
    output_path = DICTIONARY_DIR / 'sistema.csv'
    tables = read_system_tables()
    with output_path.open('w', encoding='utf-8-sig', newline='') as output:
        writer = csv.writer(output, delimiter=';')
        for index, (table, fields) in enumerate(tables):
            writer.writerow([f'Tabela {table}'])
            writer.writerow(['tipo', 'descricao_campo', 'campo'])
            for row in fields:
                writer.writerow(_clean_row(list(row)))
            if index < len(tables) - 1:
                writer.writerow([])
                writer.writerow([])
    return output_path


def main() -> None:
    for layer in ('bronze', 'silver'):
        layer_datasets = [
            (name, dataset)
            for name, dataset in DATASETS.items()
            if dataset['camada'] == layer
        ]
        output_path = write_layer_dictionary(layer, layer_datasets)
        print(f'Dicionario salvo: {output_path}')
    print(f'Dicionario salvo: {write_system_dictionary()}')


if __name__ == '__main__':
    main()
