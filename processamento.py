"""Carregamento e pré-processamento dos dados (mesmos passos do notebook da Parte 1).

Fica separado do app.py para que o app só cuide da interface.
"""
import unicodedata

import pandas as pd

ABA_DADOS = '2. Dados_distritos_2025'
ABA_METADADOS = '1. Metadados_2025'

NOVOS_NOMES = {
    'Distrito': 'distrito',
    'Remuneração média mensal do emprego formal': 'remuneracao',
    'Idade média ao morrer': 'idade_morte',
    'Velocidade média ônibus (km/h)': 'vel_onibus',
    'Equipamentos públicos de cultura': 'equip_cultura',
    'Homicídios': 'homicidios',
    'Famílias em atendimento habitacional provisório por situação de risco e emergência': 'risco_habitacional',
    'Mortalidade infantil': 'mort_infantil',
    'Abandono escolar no ensino fundamental da rede municipal': 'abandono_escolar',
    'Emissão de poluentes atmosféricos por área (kg/km²/dia)': 'emissao_poluentes',
    'Gravidez na adolescência': 'gravidez_adolesc',
    'Violência racial': 'violencia_racial',
    'Tempo de atendimento para vaga em creche': 'espera_creche',
}

# Nome curto, unidade e sentido ("maior é melhor?") de cada indicador original
INDICADORES = {
    'idade_morte': ('Idade média ao morrer', 'anos', True),
    'mort_infantil': ('Mortalidade infantil', 'por mil nascidos vivos', False),
    'gravidez_adolesc': ('Gravidez na adolescência', '% dos nascidos vivos', False),
    'homicidios': ('Homicídios', 'por 100 mil hab.', False),
    'equip_cultura': ('Equipamentos públicos de cultura', 'por 100 mil hab.', True),
    'violencia_racial': ('Violência racial', 'por 100 mil hab.', False),
    'emissao_poluentes': ('Emissão de poluentes dos ônibus', 'kg/km²/dia', False),
    'vel_onibus': ('Velocidade média dos ônibus', 'km/h', True),
    'risco_habitacional': ('Auxílio-aluguel por risco (enchente, deslizamento)', '% das famílias atendidas', False),
    'remuneracao': ('Remuneração do emprego formal', 'R$ por mês', True),
    'abandono_escolar': ('Abandono escolar (rede municipal)', '%', False),
    'espera_creche': ('Espera por vaga em creche', 'dias', False),
}

# Os índices criados na Parte 1 (todos de 0 a 1, maior é melhor)
INDICES = {
    'I1_social': 'I1 · Condições de vida',
    'I2_cultural': 'I2 · Cultura e diversidade',
    'I3_ambiental': 'I3 · Ambiental urbano',
    'I4_geral': 'I4 · Índice geral',
}

COMPONENTES = {
    'I1_social': ['idade_morte', 'mort_infantil', 'gravidez_adolesc', 'homicidios'],
    'I2_cultural': ['equip_cultura', 'violencia_racial'],
    'I3_ambiental': ['emissao_poluentes', 'vel_onibus', 'risco_habitacional'],
}

REGIOES = ['Centro', 'Leste', 'Norte', 'Oeste', 'Sul']


def chave_distrito(nome):
    """'Jardim São Luís' -> 'JARDIM SAO LUIS' (para casar com o mapa, que vem sem acento)."""
    sem_acento = unicodedata.normalize('NFKD', str(nome)).encode('ascii', 'ignore').decode()
    return sem_acento.upper().replace('-', ' ').strip()


def nome_variavel(coluna):
    if coluna in INDICES:
        return INDICES[coluna]
    if coluna in INDICADORES:
        return INDICADORES[coluna][0]
    return coluna


def normalizar(coluna, maior_e_melhor=True):
    """Mínimo-máximo (lógica do IDH): pior distrito = 0, melhor = 1."""
    nota = (coluna - coluna.min()) / (coluna.max() - coluna.min())
    return nota if maior_e_melhor else 1 - nota


def carregar_planilha(arquivo):
    """Lê a aba de dados e a de metadados da planilha do Mapa da Desigualdade."""
    dados = pd.read_excel(arquivo, sheet_name=ABA_DADOS)
    metadados = pd.read_excel(arquivo, sheet_name=ABA_METADADOS)
    metadados['FONTE(S)'] = metadados['FONTE(S)'].str.replace('–', '-')
    return dados, metadados


def preprocessar(dados_brutos, regioes):
    """Renomeia, junta região/subprefeitura, normaliza e calcula I1 a I4."""
    dados = dados_brutos.rename(columns=NOVOS_NOMES)

    faltando = [c for c in NOVOS_NOMES.values() if c not in dados.columns]
    if faltando:
        raise ValueError(f'A planilha não tem as colunas esperadas: {faltando}')

    dados = dados.merge(regioes, left_on='distrito', right_on='Distrito', how='left')
    dados = dados.drop(columns='Distrito')
    dados['regiao'] = dados['regiao'].fillna('Sem região')

    # Notas de 0 a 1 de cada componente
    for indice, colunas in COMPONENTES.items():
        for coluna in colunas:
            maior_e_melhor = INDICADORES[coluna][2]
            dados[f'n_{coluna}'] = normalizar(dados[coluna], maior_e_melhor)
        dados[indice] = dados[[f'n_{c}' for c in colunas]].mean(axis=1)

    dados['I4_geral'] = dados[['I1_social', 'I2_cultural', 'I3_ambiental']].mean(axis=1)
    dados['chave'] = dados['distrito'].map(chave_distrito)
    return dados


def desigualtometro(dados, colunas):
    """Quantas vezes o maior valor é o menor (só quando o menor é maior que zero)."""
    linhas = []
    for coluna in colunas:
        maior = dados.loc[dados[coluna].idxmax()]
        menor = dados.loc[dados[coluna].idxmin()]
        razao = maior[coluna] / menor[coluna] if menor[coluna] > 0 else None
        linhas.append({
            'Indicador': nome_variavel(coluna),
            'Maior valor': maior[coluna],
            'Distrito (maior)': maior['distrito'],
            'Menor valor': menor[coluna],
            'Distrito (menor)': menor['distrito'],
            'Maior ÷ menor': razao,
        })
    return pd.DataFrame(linhas)
