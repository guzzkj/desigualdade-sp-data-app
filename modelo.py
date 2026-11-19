"""Modelagem preditiva (versão inicial, será aprofundada na Parte 3).

Pergunta: dá para estimar a IDADE MÉDIA AO MORRER de um distrito a partir dos
outros indicadores sociais, culturais e ambientais?

- Tarefa: regressão (alvo numérico contínuo, em anos).
- Modelos (vistos na Aula 14): Regressão Linear, KNN, Árvore de Decisão e Random Forest.
- Avaliação: validação cruzada com 5 partes (KFold). Com só 96 distritos, um único
  train_test_split deixaria ~20 distritos no teste e o resultado mudaria muito
  conforme o sorteio. Na validação cruzada cada distrito é previsto uma vez por um
  modelo que NÃO o viu no treino, então temos uma previsão "honesta" para todos.
- Uso para a decisão: o resíduo (real - previsto) mostra distritos onde se vive
  menos do que os indicadores sugerem, ou seja, onde há algo além do que medimos.
"""
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, r2_score, root_mean_squared_error
from sklearn.model_selection import KFold, cross_val_predict
from sklearn.neighbors import KNeighborsRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.tree import DecisionTreeRegressor

ALVO = 'idade_morte'

# Abandono escolar (8 ausentes) e espera por creche (correlação perto de zero) ficam de fora,
# como na construção dos índices da Parte 1.
VARIAVEIS = ['gravidez_adolesc', 'mort_infantil', 'homicidios', 'remuneracao', 'risco_habitacional',
             'equip_cultura', 'violencia_racial', 'emissao_poluentes', 'vel_onibus']

SEMENTE = 42


def criar_modelo(nome):
    # KNN e regressão linear dependem da escala das variáveis, então padronizamos antes
    modelos = {
        'Regressão Linear': make_pipeline(StandardScaler(), LinearRegression()),
        'KNN (5 vizinhos)': make_pipeline(StandardScaler(), KNeighborsRegressor(n_neighbors=5)),
        'Árvore de Decisão': DecisionTreeRegressor(max_depth=3, random_state=SEMENTE),
        'Random Forest': RandomForestRegressor(n_estimators=300, random_state=SEMENTE),
    }
    return modelos[nome]


NOMES_MODELOS = ['Regressão Linear', 'KNN (5 vizinhos)', 'Árvore de Decisão', 'Random Forest']


def avaliar(dados, nome_modelo, variaveis):
    """Treina com validação cruzada e devolve métricas, previsões por distrito e importâncias."""
    X = dados[variaveis]
    y = dados[ALVO]
    divisao = KFold(n_splits=5, shuffle=True, random_state=SEMENTE)

    modelo = criar_modelo(nome_modelo)
    previsto = cross_val_predict(modelo, X, y, cv=divisao)

    metricas = {
        'r2': r2_score(y, previsto),
        'mae': mean_absolute_error(y, previsto),
        'rmse': root_mean_squared_error(y, previsto),
        # Referência: "chutar" a média da cidade para todo distrito
        'mae_base': mean_absolute_error(y, [y.mean()] * len(y)),
    }

    previsoes = dados[['distrito', 'regiao', ALVO]].copy()
    previsoes['previsto'] = previsto
    previsoes['residuo'] = previsoes[ALVO] - previsoes['previsto']

    modelo.fit(X, y)  # modelo final com todos os dados, só para ler a importância
    importancia = importancia_variaveis(modelo, variaveis, X, y)
    return metricas, previsoes, importancia


def importancia_variaveis(modelo, variaveis, X, y):
    """Quanto cada variável pesa no modelo (escala comparável entre variáveis)."""
    final = modelo[-1] if hasattr(modelo, 'steps') else modelo
    if hasattr(final, 'coef_'):
        # Coeficiente com variáveis padronizadas: anos a mais/menos por 1 desvio-padrão
        valores = final.coef_
        tipo = 'Coeficiente (anos por 1 desvio-padrão)'
    elif hasattr(final, 'feature_importances_'):
        valores = final.feature_importances_
        tipo = 'Importância (0 a 1)'
    else:
        # KNN não tem coeficientes: usamos a correlação de cada variável com o alvo
        valores = [X[v].corr(y) for v in variaveis]
        tipo = 'Correlação com a idade média ao morrer'
    tabela = pd.DataFrame({'variavel': variaveis, 'valor': valores})
    tabela['tipo'] = tipo
    return tabela.sort_values('valor', key=abs)
