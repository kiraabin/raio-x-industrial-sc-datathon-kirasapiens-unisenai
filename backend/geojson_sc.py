"""Regenera data/externos/sc_municipios.geojson com a malha atual do IBGE (295 municípios).

A malha anterior tinha 293: faltavam Pescaria Brava (4212650) e Balneário Rincão (4220000),
criados em 2013, que apareciam em branco no mapa. Mantém as propriedades id/name/description
usadas pelo dashboard Streamlit e pelo frontend.
"""
import gzip
import json
import urllib.request
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
URL = ("https://servicodados.ibge.gov.br/api/v3/malhas/estados/42?intrarregiao=municipio"
       "&formato=application/vnd.geo%2Bjson&qualidade=intermediaria")
resp = urllib.request.urlopen(urllib.request.Request(URL, headers={"Accept-Encoding": "identity"}), timeout=60)
raw = resp.read()
g = json.loads(gzip.decompress(raw) if raw[:2] == b"\x1f\x8b" else raw)
nomes = pd.read_csv(ROOT / 'data/processed/municipios.csv').set_index('cod_ibge')['municipio_nome'].to_dict()


def arredonda(c):
    return round(c, 5) if isinstance(c, float) else [arredonda(x) for x in c]


feats = []
for f in g['features']:
    cod = int(f['properties']['codarea'])
    feats.append({"type": "Feature",
                  "properties": {"id": str(cod), "name": nomes[cod], "description": nomes[cod]},
                  "geometry": {"type": f['geometry']['type'], "coordinates": arredonda(f['geometry']['coordinates'])}})
ids = {int(f['properties']['id']) for f in feats}
assert ids == set(nomes), (len(ids), set(nomes) ^ ids)
out = {"type": "FeatureCollection", "features": sorted(feats, key=lambda f: f['properties']['id'])}
(ROOT / 'data/externos/sc_municipios.geojson').write_text(json.dumps(out, ensure_ascii=False, separators=(',', ':')))
print(len(feats), 'municípios,', (ROOT / 'data/externos/sc_municipios.geojson').stat().st_size // 1024, 'KB')
