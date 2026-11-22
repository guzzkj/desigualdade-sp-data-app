# Projeto Tema 2 — Parte 2: Data app
**"Onde mora a desigualdade em São Paulo?"** · Data app em Streamlit com os indicadores da Parte 1 e os resultados da modelagem preditiva da Parte 3 (modelo final Ridge + segmentação K-means).

**App online:** https://desigualdade-sp-tsi.streamlit.app/

Dados: *Mapa da Desigualdade 2025* (Rede Nossa São Paulo / Instituto Cidades Sustentáveis), 96 distritos da capital, indicadores de 2024.

## Como rodar localmente
Precisa de Python 3.12 (as versões fixadas no `requirements.txt` não instalam em Pythons antigos). No terminal (Anaconda Prompt ou outro), dentro desta pasta:

```bash
python -m venv .venv
.venv\Scripts\activate          # Windows  (Linux/Mac: source .venv/bin/activate)
pip install -r requirements.txt
streamlit run app.py
```
O app abre em `http://localhost:8501`. Com o Anaconda dá para pular o `venv` e rodar só `pip install -r requirements.txt` e `streamlit run app.py`.

Versões testadas: Python 3.12, streamlit 1.67, plotly 7.1, pandas 3.1, numpy 2.5, scikit-learn 1.9, openpyxl 3.1.

## Arquivos
| Arquivo | Função |
|---|---|
| `app.py` | Interface do data app (filtros, KPIs, gráficos, abas) |
| `processamento.py` | Carregamento da planilha + pré-processamento + índices I1 a I4 (mesmos passos do notebook da Parte 1) |
| `modelo.py` | Modelagem preditiva: regressão da idade média ao morrer com validação cruzada |
| `preparar_mapa.py` | Gera o mapa leve `data/distritos_sp_leve.geojson` a partir do original (rodar só uma vez; o arquivo já está pronto) |
| `data/mapa_da_desigualdade_2025_dados.xlsx` | Planilha original do Mapa da Desigualdade 2025 |
| `data/distritos_subprefeitura_regiao.csv` | Subprefeitura e região de cada distrito (tabela auxiliar da Parte 1) |
| `data/distritos-sp.geojson` | Contorno dos distritos (GeoSampa, via github.com/codigourbano/distritos-sp) |
| `data/parte3/*.csv` | Resultados exportados pelo notebook da Parte 3 (comparação de modelos, ablação, grupos K-means, importância e previsões) |

O app lê a **planilha original** e refaz todo o pré-processamento ao abrir (com `st.cache_data`, só na primeira vez). Os índices conferem exatamente com os do notebook da Parte 1.

## O que o app mostra
- **Cabeçalho:** frase-chave (62 x 82 anos de idade média ao morrer) e 4 KPIs: I1 Condições de vida, I2 Cultura e diversidade, I3 Ambiental urbano e I4 Índice geral.
- **Panorama:** mapa dos distritos, ranking dos piores e melhores e uma frase de leitura que muda com os filtros.
- **Relações:** dispersão entre dois indicadores à escolha (com a tendência e a correlação), boxplot por região e Desigualtômetro.
- **Previsão:** regressão que estima a idade média ao morrer a partir de 9 indicadores. Mostra R², MAE e RMSE, real x previsto, peso de cada variável e os distritos onde se vive menos do que o esperado. No fim da aba, **Resultados da Parte 3**: KPIs do modelo final (Ridge), comparação dos modelos com validação cruzada repetida, teste de ablação e segmentação K-means (k = 3) filtrada pelas regiões escolhidas.
- **Método:** como os índices são calculados, metadados oficiais, limitações, tabela filtrada e download em CSV.

## Justificativa dos componentes Streamlit
Cada componente tem uma função diferente na análise; evitamos widgets que repetem a mesma função.

| Componente | Onde | Função para a análise |
|---|---|---|
| `st.file_uploader` | Barra lateral › Fonte dos dados | **Carregamento da fonte.** O Mapa sai todo ano: enviar a planilha nova atualiza o app inteiro sem mexer no código. Sem envio, usa a planilha de 2025. |
| `st.multiselect` (Regiões) | Barra lateral | **Filtro de território.** Recorta KPIs, mapa, ranking, dispersão, boxplot, Desigualtômetro, gráfico real x previsto e tabela. |
| `st.selectbox` (Indicador) | Barra lateral | **Filtro de assunto.** Escolhe o que colore o mapa, ordena o ranking, aparece no boxplot e ordena a tabela. |
| `st.slider` (Distritos no ranking) | Barra lateral | **Filtro de detalhe.** Não muda os dados, só quantos distritos aparecem em cada ponta do ranking e na lista do modelo. |
| `st.metric` (×13) | Cabeçalho, Panorama e Previsão | **KPIs.** Os 4 índices do recorte com a diferença (delta) para a média da cidade; média, pior e melhor distrito do indicador; R², MAE (comparado a "chutar a média") e RMSE do modelo; R² e MAE do modelo final da Parte 3 e R² só com gravidez na adolescência. |
| `st.tabs` | Corpo | **Organização** por objetivo: ver o problema, entender relações, prever, conferir o método. |
| `st.columns` | Corpo | Coloca mapa e ranking lado a lado (onde x quem) e os KPIs em linha. |
| `st.plotly_chart` — mapa coroplético | Panorama | Mostra **onde** estão os problemas. Cores verde→vermelho invertidas quando "maior é pior". |
| `st.plotly_chart` — barras | Panorama, Previsão | Ranking: **quem atender primeiro**, com a linha da média da cidade. Peso das variáveis do modelo. Comparação dos modelos da Parte 3 (R² médio com barra de erro). |
| `st.plotly_chart` — dispersão | Relações, Previsão | **Relações** entre indicadores (com tendência e correlação), real x previsto e grupos do K-means (gravidez na adolescência x idade ao morrer). |
| `st.plotly_chart` — boxplot | Relações | **Desigualdade dentro de cada região** (a média esconde a dispersão). |
| `st.selectbox` (Eixo X / Eixo Y) | Relações | Escolher a dupla de indicadores do gráfico de dispersão. |
| `st.selectbox` (Modelo) + `st.multiselect` (Variáveis) | Previsão | Comparar 6 modelos (4 da Aula 14 + Ridge e Gradient Boosting ajustado da Parte 3) e ver quanto o modelo perde ao tirar uma variável. |
| `st.dataframe` | Relações, Previsão, Método | Consulta dos números exatos (Desigualtômetro, distritos com maior diferença entre real e previsto, ablação e perfil dos grupos da Parte 3, tabela do recorte). |
| `st.download_button` | Método | Baixar a tabela do recorte em CSV. |
| `st.markdown`, `st.caption`, `st.info`, `st.expander` | Todo o app | **Textos explicativos:** contexto, leitura de cada gráfico, metadados e limitações (o expander esconde o detalhe para não poluir). |
| `st.cache_data` | Código | Lê a planilha, o mapa e treina o modelo uma vez só; os filtros respondem rápido. |

Todos os gráficos são do Plotly: passar o mouse mostra o distrito e o valor, dá para dar zoom e clicar na legenda para esconder uma região. São 8 gráficos de 4 tipos (mapa, barras, dispersão e boxplot).

## Como cada filtro muda o app (exemplo para a apresentação)
1. **Só a região Leste no multiselect:** os KPIs mostram a média da Leste com a diferença para a cidade (I1 = 0,46, ou seja, 0,08 abaixo). Mapa, ranking, dispersão, boxplot e tabela passam a ter só os 33 distritos da Leste; a frase de leitura diz quantos estão abaixo da média da cidade.
2. **Indicador de I1 para "Mortalidade infantil":** o mapa muda de cor (agora vermelho = mais mortes), o ranking reordena com os piores no topo e o boxplot mostra a mortalidade por região.
3. **Slider de 10 para 5:** o ranking mostra só os 5 piores e os 5 melhores; a lista do modelo também fica com 5 linhas.
4. **Modelo de "Ridge" (padrão) para "KNN":** o R² cai de 0,85 para 0,72 e o erro médio sobe de 1,6 para 2,3 anos.
5. **Tirar "Gravidez na adolescência" das variáveis:** dá para ver quanto o modelo depende do indicador mais ligado à idade média ao morrer.

## Modelagem preditiva (Parte 3)
- **Pergunta:** os outros indicadores do distrito permitem estimar a idade média ao morrer?
- **Tarefa:** regressão supervisionada. Alvo: `idade_morte` (anos). Variáveis: gravidez na adolescência, mortalidade infantil, homicídios, remuneração, auxílio-aluguel por risco, equipamentos de cultura, violência racial, emissão de poluentes e velocidade dos ônibus.
- **Modelos:** Ridge (modelo final), Regressão Linear, KNN, Árvore de Decisão, Random Forest e Gradient Boosting com hiperparâmetros ajustados.
- **Avaliação:** validação cruzada com 5 partes (`KFold` + `cross_val_predict`). Com só 96 distritos, um único `train_test_split` deixaria uns 20 no teste e o resultado mudaria muito com o sorteio. Assim, cada distrito é previsto por um modelo que não o viu no treino.
- **Resultado no app (5 partes):** Ridge e Regressão Linear empatam (R² = 0,85; erro médio de 1,6 ano, contra 4,6 anos se chutássemos a média da cidade).
- **Resultado no notebook da Parte 3** (validação cruzada repetida 5×10 e ajuste com validação aninhada): Ridge R² = 0,83, MAE 1,62 ano; Random Forest 0,74; Gradient Boosting 0,73; KNN e Árvore 0,69. Só gravidez na adolescência já dá R² 0,78; sem ela cai para 0,62.
- **Segmentação (K-means, k = 3):** Vulnerável (36 distritos, ~66 anos), Intermediário (35, ~72) e Consolidado (25, ~77). Silhueta 0,16: gradiente contínuo, não ilhas.
- **Uso para a decisão:** distritos com idade real bem abaixo da prevista têm algo que os indicadores do Mapa não captam. São candidatos a uma investigação mais detalhada.

## Limitações
- Médias por região são médias simples dos distritos (a planilha não tem população para ponderar).
- Indicadores "por morador" ficam distorcidos no Centro (poucos moradores, muita circulação).
- Homicídios são de 2021 e remuneração de 2023.
- O índice de 0 a 1 é relativo (posição entre os distritos), não uma meta.
- O modelo mostra associação, não causa.

## Deploy no Streamlit Community Cloud
1. Criar um repositório no GitHub e subir **o conteúdo desta pasta** (o `app.py` precisa ficar na raiz do repositório):
   ```bash
   git init
   git add .
   git commit -m "feat: add inequality data app"
   git branch -M main
   git remote add origin https://github.com/<usuario>/<repositorio>.git
   git push -u origin main
   ```
2. Entrar em [share.streamlit.io](https://share.streamlit.io) com a conta do GitHub › **Create app** › **Deploy a public app from GitHub**.
3. Escolher o repositório, a branch `main` e o *Main file path* `app.py`.
4. Em **Advanced settings**, escolher **Python 3.12** (versão testada) e clicar em **Deploy**.

O `requirements.txt` fixa as versões testadas. Os dados ficam em `data/` e são lidos por caminho relativo, então não há nada a configurar. O app não usa segredos nem chaves de API.
