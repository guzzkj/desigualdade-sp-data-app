"""Data app — Onde mora a desigualdade em São Paulo? (Projeto ICD, Parte 2)

Rodar:  streamlit run app.py
"""
import io
import json
import textwrap

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import modelo
from processamento import (COMPONENTES, INDICADORES, INDICES, REGIOES, carregar_planilha,
                           desigualtometro, nome_variavel, preprocessar)

PLANILHA_PADRAO = 'data/mapa_da_desigualdade_2025_dados.xlsx'
ARQUIVO_REGIOES = 'data/distritos_subprefeitura_regiao.csv'
ARQUIVO_MAPA = 'data/distritos_sp_leve.geojson'

# Uma cor fixa por região em todos os gráficos (a legenda vale para o app inteiro)
CORES_REGIAO = {'Centro': '#7f3c8d', 'Leste': '#e68310', 'Norte': '#3969ac',
                'Oeste': '#11a579', 'Sul': '#f2b701', 'Sem região': '#a5aa99'}

st.set_page_config(page_title='Desigualdade em SP', page_icon=':material/map:', layout='wide')

# Responsividade: o Streamlit só empilha colunas quando a TELA tem menos de 640px.
# Com a barra lateral aberta num tablet, as colunas ficavam estreitas demais.
# Aqui cada coluna tem largura mínima e "quebra a linha" quando não cabe.
st.markdown('''<style>
[data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: min(100%, 10rem); }
[class*="st-key-graficos"] [data-testid="stHorizontalBlock"] > [data-testid="stColumn"] { min-width: min(100%, 24rem); }
</style>''', unsafe_allow_html=True)


# ---------------------------------------------------------------- funções auxiliares
def fmt(valor, casas=2):
    """Número no formato brasileiro: 1234.5 -> '1.234,50'."""
    if valor is None or pd.isna(valor):
        return '—'
    texto = f'{valor:,.{casas}f}'
    return texto.replace(',', 'X').replace('.', ',').replace('X', '.')


def maior_e_melhor(coluna):
    return True if coluna in INDICES else INDICADORES[coluna][2]


def unidade(coluna):
    return '0 a 1' if coluna in INDICES else INDICADORES[coluna][1]


@st.cache_data
def carregar_dados(conteudo_planilha):
    """Recebe a planilha (arquivo padrão ou enviado) e devolve os dados prontos."""
    origem = PLANILHA_PADRAO if conteudo_planilha is None else io.BytesIO(conteudo_planilha)
    brutos, metadados = carregar_planilha(origem)
    regioes = pd.read_csv(ARQUIVO_REGIOES)
    return preprocessar(brutos, regioes), metadados


@st.cache_data
def carregar_mapa():
    with open(ARQUIVO_MAPA, encoding='utf-8') as arquivo:
        return json.load(arquivo)


def enquadrar_mapa(mapa, chaves):
    """Centro e zoom que mostram só os distritos do recorte (ex.: zoom na Leste)."""
    lons, lats = [], []
    for distrito in mapa['features']:
        if distrito['properties']['chave'] in chaves:
            poligonos = distrito['geometry']['coordinates']
            if distrito['geometry']['type'] == 'Polygon':
                poligonos = [poligonos]
            for poligono in poligonos:
                for x, y in poligono[0]:
                    lons.append(x)
                    lats.append(y)
    centro = {'lon': (min(lons) + max(lons)) / 2, 'lat': (min(lats) + max(lats)) / 2}
    # 1.1 corrige a distorção da projeção na latitude de SP; 420 ~ largura do mapa no celular (px)
    extensao = max(max(lons) - min(lons), (max(lats) - min(lats)) * 1.1)
    zoom = np.log2(420 * 360 / (256 * extensao)) - 0.2
    return centro, float(min(zoom, 11))


@st.cache_data
def rodar_modelo(dados, nome_modelo, variaveis):
    return modelo.avaliar(dados, nome_modelo, list(variaveis))


# ---------------------------------------------------------------- barra lateral
st.sidebar.title(':material/filter_alt: Filtros')

with st.sidebar.expander('Fonte dos dados', expanded=False):
    st.caption('O app usa a planilha do Mapa da Desigualdade 2025. Quando sair uma nova edição '
               'com o mesmo formato, é só enviar o arquivo aqui para atualizar tudo.')
    enviado = st.file_uploader('Outra planilha (.xlsx)', type='xlsx')

try:
    dados, metadados = carregar_dados(enviado.getvalue() if enviado else None)
    fonte_atual = enviado.name if enviado else 'mapa_da_desigualdade_2025_dados.xlsx'
except (ValueError, KeyError) as erro:
    st.sidebar.error(f'Não consegui ler essa planilha ({erro}). Voltando para a planilha padrão.')
    dados, metadados = carregar_dados(None)
    fonte_atual = 'mapa_da_desigualdade_2025_dados.xlsx'

regioes_escolhidas = st.sidebar.multiselect(
    'Regiões', REGIOES, default=REGIOES,
    help='Recorta o território: KPIs, mapa, ranking, gráficos e tabela mostram só essas regiões.')

opcoes_indicador = list(INDICES) + list(INDICADORES)
indicador = st.sidebar.selectbox(
    'Indicador', opcoes_indicador, format_func=nome_variavel,
    help='Define a cor do mapa, a ordem do ranking e o gráfico por região.')

n_ranking = st.sidebar.slider(
    'Distritos no ranking (piores e melhores)', min_value=5, max_value=20, value=10,
    help='Não muda os dados: só quantos distritos aparecem em cada ponta do ranking.')

st.sidebar.divider()
st.sidebar.caption(f'Fonte: Rede Nossa São Paulo / Instituto Cidades Sustentáveis, '
                   f'Mapa da Desigualdade 2025 (dados de 2024). Arquivo: `{fonte_atual}`')

if not regioes_escolhidas:
    st.warning('Escolha pelo menos uma região na barra lateral.')
    st.stop()

recorte = dados[dados['regiao'].isin(regioes_escolhidas)]
cidade_toda = len(regioes_escolhidas) == len(REGIOES)
if cidade_toda:
    nome_recorte, no_recorte = 'cidade toda', 'na cidade toda'
elif len(regioes_escolhidas) == 1:
    nome_recorte, no_recorte = regioes_escolhidas[0], f'na região {regioes_escolhidas[0]}'
else:
    nome_recorte = ', '.join(regioes_escolhidas)
    no_recorte = f'nas regiões {nome_recorte}'

# ---------------------------------------------------------------- cabeçalho + KPIs
st.title('Onde mora a desigualdade em São Paulo?')
st.markdown(
    '**Em São Paulo, o endereço muda quanto se vive:** a idade média ao morrer vai de '
    f'**{fmt(dados["idade_morte"].min(), 0)} anos** em {dados.loc[dados["idade_morte"].idxmin(), "distrito"]} '
    f'a **{fmt(dados["idade_morte"].max(), 0)} anos** em {dados.loc[dados["idade_morte"].idxmax(), "distrito"]}. '
    'Este app compara os 96 distritos da capital em três eixos (condições de vida, cultura e meio ambiente) '
    'para mostrar onde agir primeiro.')

st.caption(f'Recorte atual: **{nome_recorte}** · {len(recorte)} de {len(dados)} distritos · '
           'KPIs = média simples dos distritos do recorte; a seta compara com a média da cidade.')

colunas_kpi = st.columns(4)
for coluna_tela, indice in zip(colunas_kpi, INDICES):
    media_recorte = recorte[indice].mean()
    media_cidade = dados[indice].mean()
    coluna_tela.metric(
        INDICES[indice], fmt(media_recorte),
        delta=None if cidade_toda else f'{fmt(media_recorte - media_cidade)} vs. cidade',
        help='Índice de 0 a 1 (0 = pior distrito da cidade, 1 = melhor). Componentes: '
             + (', '.join(nome_variavel(c) for c in COMPONENTES[indice]) if indice in COMPONENTES
                else 'média de I1, I2 e I3') + '.')

aba_panorama, aba_explorar, aba_modelo, aba_dados = st.tabs(
    [':material/map: Panorama', ':material/scatter_plot: Relações',
     ':material/model_training: Previsão', ':material/description: Método'])

# ---------------------------------------------------------------- aba 1: panorama
with aba_panorama:
    nome_ind = nome_variavel(indicador)
    bom_alto = maior_e_melhor(indicador)
    # Distritos sem valor (ex.: abandono escolar no Centro) ficam fora do ranking
    ordenado = recorte.dropna(subset=[indicador]).sort_values(indicador, ascending=bom_alto)  # piores primeiro
    pior, melhor = ordenado.iloc[0], ordenado.iloc[-1]

    st.subheader(f'{nome_ind} ({unidade(indicador)})')
    c1, c2, c3 = st.columns(3)
    c1.metric('Média do recorte', fmt(recorte[indicador].mean()),
              delta=None if cidade_toda else fmt(recorte[indicador].mean() - dados[indicador].mean()) + ' vs. cidade',
              delta_color='normal' if bom_alto else 'inverse')
    c2.metric('Pior distrito', pior['distrito'], delta=fmt(pior[indicador]), delta_color='red', delta_arrow='off')
    c3.metric('Melhor distrito', melhor['distrito'], delta=fmt(melhor[indicador]), delta_color='green',
              delta_arrow='off')
    if len(ordenado) < len(recorte):
        st.caption(f'{len(recorte) - len(ordenado)} distrito(s) sem dado para este indicador ficam fora do ranking e do mapa.')

    col_mapa, col_ranking = st.container(key='graficos_panorama').columns([1.1, 1])

    with col_mapa:
        st.markdown('**Onde estão os problemas** (verde = melhor, vermelho = pior)')
        centro, zoom = enquadrar_mapa(carregar_mapa(), set(ordenado['chave']))
        fig_mapa = px.choropleth_map(
            recorte, geojson=carregar_mapa(), locations='chave', featureidkey='properties.chave',
            color=indicador, hover_name='distrito',
            hover_data={'chave': False, 'regiao': True, indicador: ':.2f'},
            color_continuous_scale='RdYlGn' if bom_alto else 'RdYlGn_r',
            map_style='carto-positron', center=centro, zoom=zoom,
            opacity=0.8, labels={indicador: nome_ind, 'regiao': 'Região'}, height=480)
        fig_mapa.update_layout(margin={'t': 0, 'b': 0, 'l': 0, 'r': 0},
                               coloraxis_colorbar={'title': '', 'thickness': 12})
        st.plotly_chart(fig_mapa, width='stretch')

    with col_ranking:
        if len(ordenado) > 2 * n_ranking:
            ranking = pd.concat([ordenado.head(n_ranking), ordenado.tail(n_ranking)])
            titulo = f'Os {n_ranking} piores e os {n_ranking} melhores'
        else:
            ranking = ordenado
            titulo = f'Todos os {len(ordenado)} distritos do recorte'
        st.markdown(f'**{titulo}**')
        fig_rank = px.bar(
            ranking, x=indicador, y='distrito', color='regiao', orientation='h',
            color_discrete_map=CORES_REGIAO, height=max(360, 24 * len(ranking) + 110),
            labels={indicador: nome_ind, 'distrito': '', 'regiao': 'Região'},
            category_orders={'distrito': list(ranking['distrito'])})
        fig_rank.add_vline(x=dados[indicador].mean(), line_dash='dash', line_color='gray',
                           annotation_text='média da cidade', annotation_position='top')
        fig_rank.update_layout(margin={'t': 30, 'b': 0, 'l': 0, 'r': 10},
                               legend={'orientation': 'h', 'yanchor': 'top', 'y': -0.12, 'title': ''})
        fig_rank.update_traces(hovertemplate='%{y}: %{x:.2f}<extra></extra>')
        st.plotly_chart(fig_rank, width='stretch')

    # Leitura automática do recorte (storytelling: o que o gráfico diz)
    abaixo = (recorte[indicador] < dados[indicador].mean()) if bom_alto else \
             (recorte[indicador] > dados[indicador].mean())
    razao = (max(pior[indicador], melhor[indicador]) / min(pior[indicador], melhor[indicador])
             if min(pior[indicador], melhor[indicador]) > 0 else None)
    st.info(
        f'**Leitura:** {no_recorte}, **{abaixo.sum()} de {len(ordenado)} distritos** estão pior que a média '
        f'da cidade em *{nome_ind}*. O pior é **{pior["distrito"]}** ({fmt(pior[indicador])}) e o melhor, '
        f'**{melhor["distrito"]}** ({fmt(melhor[indicador])})'
        + (f': diferença de **{fmt(razao, 1)} vezes**.' if razao else '.'))

# ---------------------------------------------------------------- aba 2: explorar
with aba_explorar:
    st.markdown('Escolha dois indicadores para ver se andam juntos. Cada ponto é um distrito; '
                'a linha mostra a tendência (regressão linear simples).')
    cx, cy = st.columns(2)
    eixo_x = cx.selectbox('Eixo X', opcoes_indicador, index=opcoes_indicador.index('gravidez_adolesc'),
                          format_func=nome_variavel)
    eixo_y = cy.selectbox('Eixo Y', opcoes_indicador, index=opcoes_indicador.index('idade_morte'),
                          format_func=nome_variavel)

    pares = recorte[list(dict.fromkeys(['distrito', 'regiao', eixo_x, eixo_y]))].dropna()
    fig_disp = px.scatter(
        pares, x=eixo_x, y=eixo_y, color='regiao', hover_name='distrito',
        color_discrete_map=CORES_REGIAO, height=480,
        labels={eixo_x: nome_variavel(eixo_x), eixo_y: nome_variavel(eixo_y), 'regiao': 'Região'})
    if len(pares) > 2 and eixo_x != eixo_y:
        inclinacao, intercepto = np.polyfit(pares[eixo_x], pares[eixo_y], 1)
        xs = np.linspace(pares[eixo_x].min(), pares[eixo_x].max(), 50)
        fig_disp.add_trace(go.Scatter(x=xs, y=inclinacao * xs + intercepto, mode='lines',
                                      name='tendência', line={'color': 'gray', 'dash': 'dash'}))
    fig_disp.update_traces(marker={'size': 10, 'line': {'width': 0.5, 'color': 'white'}},
                           selector={'mode': 'markers'})
    fig_disp.update_layout(margin={'t': 10, 'l': 0, 'r': 10},
                           legend={'orientation': 'h', 'yanchor': 'top', 'y': -0.18, 'title': ''})
    st.plotly_chart(fig_disp, width='stretch')

    if len(pares) > 2 and eixo_x != eixo_y:
        r = pares[eixo_x].corr(pares[eixo_y])
        forca = 'forte' if abs(r) >= 0.7 else 'moderada' if abs(r) >= 0.4 else 'fraca'
        sentido = 'quando um sobe, o outro sobe' if r > 0 else 'quando um sobe, o outro desce'
        st.caption(f'Correlação no recorte: **{fmt(r)}** ({forca}; {sentido}). '
                   'Correlação não prova causa: os dois podem depender de um terceiro fator, como a renda.')

    st.subheader(f'{nome_variavel(indicador)} por região')
    fig_box = px.box(
        recorte, x='regiao', y=indicador, color='regiao', points='all', hover_name='distrito',
        color_discrete_map=CORES_REGIAO, category_orders={'regiao': REGIOES}, height=420,
        labels={indicador: nome_variavel(indicador), 'regiao': 'Região'})
    fig_box.update_layout(showlegend=False, margin={'t': 10, 'l': 0, 'r': 10})
    st.plotly_chart(fig_box, width='stretch')
    st.caption('A caixa vai do 1º ao 3º quartil e a linha do meio é a mediana. Caixas altas = muita '
               'desigualdade dentro da própria região. O indicador é o escolhido na barra lateral.')

    st.subheader('Desigualtômetro do recorte')
    st.caption('Quantas vezes o maior valor é o menor entre os distritos do recorte '
               '("—" quando o menor valor é zero e a divisão não é possível).')
    tabela_desig = desigualtometro(recorte, [c for c in INDICADORES if c not in ('abandono_escolar', 'espera_creche')])
    st.dataframe(tabela_desig, hide_index=True, width='stretch',
                 column_config={'Maior valor': st.column_config.NumberColumn(format='%.2f'),
                                'Menor valor': st.column_config.NumberColumn(format='%.2f'),
                                'Maior ÷ menor': st.column_config.NumberColumn(format='%.1f ×')})

# ---------------------------------------------------------------- aba 3: modelo
with aba_modelo:
    st.markdown(
        '**Pergunta:** dá para estimar a **idade média ao morrer** de um distrito só com os outros indicadores? '
        'Se sim, o modelo mostra *quais fatores mais pesam* e, pelo erro de cada distrito, '
        '*onde se vive menos do que seria esperado*.')
    st.caption('Regressão supervisionada · 96 distritos · validação cruzada com 5 partes: '
               'cada distrito é previsto por um modelo treinado sem ele. Versão inicial; a Parte 3 do projeto aprofunda.')

    cm, cv = st.columns([1, 2])
    nome_modelo = cm.selectbox('Modelo', modelo.NOMES_MODELOS,
                               help='Os quatro modelos vistos na Aula 14. Compare as métricas.')
    variaveis = cv.multiselect('Variáveis usadas pelo modelo', modelo.VARIAVEIS, default=modelo.VARIAVEIS,
                               format_func=nome_variavel,
                               help='Tire uma variável para ver quanto o modelo perde sem ela.')

    if not variaveis:
        st.warning('Escolha pelo menos uma variável.')
    else:
        metricas, previsoes, importancia = rodar_modelo(dados, nome_modelo, tuple(variaveis))

        m1, m2, m3 = st.columns(3)
        m1.metric('R² (0 a 1)', fmt(metricas['r2']),
                  help='Parte da diferença entre distritos que o modelo explica. 1 = perfeito, 0 = igual a chutar a média.')
        m2.metric('Erro médio (MAE)', f'{fmt(metricas["mae"], 1)} anos',
                  delta=f'{fmt(metricas["mae"] - metricas["mae_base"], 1)} anos vs. chutar a média',
                  delta_color='inverse',
                  help=f'Chutando a média da cidade para todos, o erro médio seria {fmt(metricas["mae_base"], 1)} anos.')
        m3.metric('RMSE', f'{fmt(metricas["rmse"], 1)} anos',
                  help='Parecido com o MAE, mas pune mais os erros grandes.')

        prev_recorte = previsoes[previsoes['regiao'].isin(regioes_escolhidas)]
        g1, g2 = st.container(key='graficos_modelo').columns(2)
        with g1:
            st.markdown('**Real × previsto**')
            fig_real = px.scatter(
                prev_recorte, x='previsto', y='idade_morte', color='regiao', hover_name='distrito',
                color_discrete_map=CORES_REGIAO, height=420,
                labels={'previsto': 'Idade prevista (anos)', 'idade_morte': 'Idade real (anos)', 'regiao': 'Região'})
            limites = [previsoes[['previsto', 'idade_morte']].min().min() - 1,
                       previsoes[['previsto', 'idade_morte']].max().max() + 1]
            fig_real.add_trace(go.Scatter(x=limites, y=limites, mode='lines', name='acerto perfeito',
                                          line={'color': 'gray', 'dash': 'dash'}))
            fig_real.update_traces(marker={'size': 9}, selector={'mode': 'markers'})
            fig_real.update_layout(margin={'t': 10, 'l': 0, 'r': 10},
                                   legend={'orientation': 'h', 'yanchor': 'top', 'y': -0.2, 'title': ''})
            st.plotly_chart(fig_real, width='stretch')
            st.caption('Pontos abaixo da linha: distritos onde se vive **menos** do que o modelo previu.')
        with g2:
            # Nomes longos quebram em linhas para não espremer o gráfico no celular
            importancia['nome'] = importancia['variavel'].map(
                lambda v: '<br>'.join(textwrap.wrap(nome_variavel(v), 18)))
            if importancia['tipo'].iloc[0].startswith('Importância'):
                importancia['efeito'] = 'importância (sem sentido de sinal)'  # árvores não dizem se sobe ou desce
            else:
                importancia['efeito'] = np.where(importancia['valor'] < 0, 'reduz a idade', 'aumenta a idade')
            st.markdown('**O que mais pesa no modelo**')
            fig_imp = px.bar(importancia, x='valor', y='nome', orientation='h', height=max(420, 48 * len(importancia)),
                             color='efeito',
                             color_discrete_map={'reduz a idade': '#d6604d', 'aumenta a idade': '#4393c3',
                                                 'importância (sem sentido de sinal)': '#8c8c8c'},
                             labels={'valor': importancia['tipo'].iloc[0], 'nome': '', 'efeito': ''})
            fig_imp.update_layout(margin={'t': 10, 'l': 0, 'r': 10},
                                  legend={'orientation': 'h', 'yanchor': 'top', 'y': -0.2, 'title': ''})
            st.plotly_chart(fig_imp, width='stretch')
            st.caption('Regressão linear: anos a mais ou a menos quando a variável sobe 1 desvio-padrão. '
                       'Árvore e Random Forest: só o peso de cada variável. KNN: correlação simples com o alvo.')

        st.subheader('Distritos onde se vive menos do que o esperado')
        piores_residuos = prev_recorte.sort_values('residuo').head(n_ranking)
        st.dataframe(
            piores_residuos.rename(columns={'distrito': 'Distrito', 'regiao': 'Região', 'idade_morte': 'Real',
                                            'previsto': 'Previsto', 'residuo': 'Real − previsto'}),
            hide_index=True, width='stretch',
            column_config={c: st.column_config.NumberColumn(format='%.1f anos')
                           for c in ['Real', 'Previsto', 'Real − previsto']})
        st.caption('Esses distritos têm indicadores parecidos com outros, mas vivem menos. Vale investigar '
                   'fatores que o Mapa não mede (acesso a hospitais, saneamento, idade da população). '
                   'O número de linhas segue o slider da barra lateral.')

# ---------------------------------------------------------------- aba 4: dados e método
with aba_dados:
    st.subheader('Como os índices são calculados')
    st.markdown(
        'Seguimos a lógica do **IDH**: cada indicador vira uma nota de 0 a 1 '
        '(nota = (valor − mínimo) ÷ (máximo − mínimo); invertida quando *maior é pior*) e o índice é a média das notas.')
    st.dataframe(pd.DataFrame([
        {'Índice': INDICES[i], 'Componentes': ', '.join(nome_variavel(c) for c in COMPONENTES[i])}
        for i in COMPONENTES] + [{'Índice': INDICES['I4_geral'], 'Componentes': 'média de I1, I2 e I3'}]),
        hide_index=True, width='stretch')

    with st.expander('Metadados oficiais de cada indicador (fonte e ano)'):
        st.dataframe(metadados[['TEMA', 'nome', 'UNIDADE DE MEDIDA', 'ANO', 'FONTE(S)']],
                     hide_index=True, width='stretch')

    with st.expander('Limitações e cuidados na interpretação'):
        st.markdown(
            '- Médias por região são **médias simples dos distritos** (a planilha não traz população para ponderar).\n'
            '- Indicadores **por morador** ficam distorcidos no Centro: poucos moradores e muita circulação.\n'
            '- Homicídios são de 2021 e remuneração de 2023; o resto é de 2024.\n'
            '- A nota de 0 a 1 é **relativa**: mostra a posição do distrito frente aos outros, não uma meta.\n'
            '- Remuneração mede o emprego **no endereço da empresa**, não a renda de quem mora no distrito.\n'
            '- O modelo mostra **associação**, não causa. Com 96 distritos, as métricas variam com o sorteio das partes.')

    st.subheader('Tabela do recorte')
    colunas_tabela = ['distrito', 'subprefeitura', 'regiao'] + list(INDICES) + list(INDICADORES)
    tabela = recorte[colunas_tabela].sort_values(indicador, ascending=not maior_e_melhor(indicador))
    st.dataframe(tabela.rename(columns={c: nome_variavel(c) for c in colunas_tabela}),
                 hide_index=True, width='stretch', height=380)
    st.download_button('Baixar tabela do recorte (CSV)', tabela.to_csv(index=False).encode('utf-8-sig'),
                       file_name=f'desigualdade_sp_{"_".join(regioes_escolhidas).lower()}.csv', mime='text/csv')
