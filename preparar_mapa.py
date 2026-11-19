"""Gera uma versão leve do mapa de distritos para o data app.

Fonte: GeoSampa / Prefeitura de São Paulo, via https://github.com/codigourbano/distritos-sp
O arquivo original (data/distritos-sp.geojson, ~7 MB) deixa o mapa lento no navegador.
Este script:
  1. arredonda as coordenadas para 4 casas decimais (~10 m de precisão);
  2. mantém só 1 a cada PASSO pontos de cada contorno (o mapa continua reconhecível);
  3. guarda o nome do distrito em uma chave sem acento ('chave'), igual à usada no app.

Rodar uma vez:  python preparar_mapa.py
"""
import json

from processamento import chave_distrito

ORIGEM = 'data/distritos-sp.geojson'
DESTINO = 'data/distritos_sp_leve.geojson'
PASSO = 8  # mantém 1 a cada 8 pontos


def simplificar_anel(anel):
    if len(anel) < 4 * PASSO:
        return [[round(x, 4), round(y, 4)] for x, y in anel]  # contorno pequeno: mantém inteiro
    pontos = anel[::PASSO]
    if pontos[-1] != anel[-1]:
        pontos.append(anel[-1])  # o contorno precisa terminar no ponto inicial
    return [[round(x, 4), round(y, 4)] for x, y in pontos]


def simplificar_geometria(geometria):
    if geometria['type'] == 'Polygon':
        geometria['coordinates'] = [simplificar_anel(a) for a in geometria['coordinates']]
    elif geometria['type'] == 'MultiPolygon':
        geometria['coordinates'] = [[simplificar_anel(a) for a in poligono]
                                    for poligono in geometria['coordinates']]
    return geometria


with open(ORIGEM, encoding='utf-8') as arquivo:
    mapa = json.load(arquivo)

for distrito in mapa['features']:
    nome = distrito['properties']['ds_nome']
    distrito['properties'] = {'chave': chave_distrito(nome)}
    distrito['geometry'] = simplificar_geometria(distrito['geometry'])

with open(DESTINO, 'w', encoding='utf-8') as arquivo:
    json.dump(mapa, arquivo, separators=(',', ':'))

print(f'{len(mapa["features"])} distritos salvos em {DESTINO}')
