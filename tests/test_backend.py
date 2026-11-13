"""Testes de consistência do backend. Rode com: pytest tests/

Usam o industria.parquet e os CSVs versionados em data/processed/ (não precisam do CAGED bruto).
"""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

import estatistica  # noqa: E402
import exportar  # noqa: E402
from indicadores import METODOS_PRESSAO, classificar  # noqa: E402

P = ROOT / "data/processed"
DERIVADAS = ["indice_pressao", "indice_expansao", "diagnostico", "taxa_saldo"]


@pytest.fixture(scope="module")
def ind():
    return pd.read_parquet(P / "industria.parquet")


@pytest.fixture(scope="module")
def rs():
    return pd.read_csv(P / "ind_regiao_setor.csv")


# ---------------------------------------------------------------- indicadores

@pytest.mark.parametrize("arquivo", ["ind_regiao_setor", "ind_municipio", "ind_macrofamilia", "ind_municipio_setor",
                                     "ind_regiao_macrofamilia"])
def test_classificar_padrao_reproduz_tabelas(arquivo):
    t = pd.read_csv(P / f"{arquivo}.csv")
    n = classificar(t.drop(columns=DERIVADAS, errors="ignore"))
    assert (n["diagnostico"] == t["diagnostico"]).all()
    assert np.allclose(n["indice_pressao"], t["indice_pressao"], equal_nan=True)


@pytest.mark.parametrize("metodo", METODOS_PRESSAO)
def test_metodos_nao_mudam_expansao_nem_volume(rs, metodo):
    base = rs.drop(columns=DERIVADAS, errors="ignore")
    n = classificar(base, metodo=metodo)
    assert np.allclose(n["indice_expansao"], rs["indice_expansao"], equal_nan=True)
    assert ((n["diagnostico"] == "Volume insuficiente") == (rs["movimentacoes"] < 300)).all()


def test_metodo_invalido(rs):
    with pytest.raises(ValueError):
        classificar(rs, metodo="xyz")


# ---------------------------------------------------------------- base

def test_totais_da_base(ind):
    assert len(ind) == 835_776
    assert ind["admissao"].sum() - (~ind["admissao"]).sum() == 1_098
    assert ind["competênciamov"].nunique() == 12


def test_pedido_so_em_desligamento(ind):
    assert not (ind["admissao"] & ind["pedido"]).any()


# ---------------------------------------------------------------- estatística

def test_sensibilidade_cenario_padrao_bate_com_diagnostico(rs):
    cen, pares = estatistica.sensibilidade(rs)
    assert len(cen) == len(METODOS_PRESSAO) * 4 * 3
    padrao = cen[cen["padrao"]].iloc[0]
    c = rs["diagnostico"].value_counts()
    assert padrao["Apagão de mão de obra"] == c["Apagão de mão de obra"]
    assert padrao["Expansão sob pressão"] == c["Expansão sob pressão"]
    assert len(pares) == len(rs)
    assert pares["pct_cenarios_alerta"].dropna().between(0, 1).all()
    assert (pares.loc[pares["movimentacoes"] < 300, "estabilidade"] == "Sem volume").all()


def test_sazonalidade_fecha_com_a_base(ind):
    m = estatistica.sazonalidade_mensal(ind)
    for tipo, g in m.groupby("recorte_tipo"):
        assert g["saldo"].sum() == 1_098, tipo
        assert g["movimentacoes"].sum() == len(ind), tipo
    total = m[m["recorte_tipo"] == "total"]
    assert total["saldo_acumulado"].iloc[-1] == 1_098
    r = estatistica.sazonalidade_resumo(m)
    assert r.loc[r["recorte_tipo"] == "total", "mes_vale"].item() == "dez/25"


def test_grade_salario_escolaridade(ind):
    d = estatistica.base_desligamentos(ind)
    g = estatistica.grade_salario_escolaridade(d)
    total = g[(g["quintil_sal"] == "Todas") & (g["faixa_esc"] == "Todas")]
    assert total["desligamentos"].item() == len(d)
    celulas = g[(g["quintil_sal"] != "Todas") & (g["faixa_esc"] != "Todas")]
    assert celulas["desligamentos"].sum() == len(d)
    assert g["pct_pedido"].between(0, 1).all()


# ---------------------------------------------------------------- exportação

def test_cubo_soma_igual_a_base(ind):
    c = exportar.cubo(ind)
    assert c["admissoes"].sum() == ind["admissao"].sum()
    assert c["desligamentos"].sum() == (~ind["admissao"]).sum()
    assert c["a_pedido"].sum() == ind["pedido"].sum()


def test_salario_hist_mediana_bate_com_a_base(ind):
    h = exportar.salario_hist(ind)
    a = ind[ind["admissao"] & ind["salario_valido"]]
    assert h["n"].sum() == len(a)
    h = h.sort_values("lo")
    acum = h.groupby("lo")["n"].sum().cumsum()
    meio = len(a) / 2
    lo = acum[acum >= meio].index[0]
    assert lo <= a["salario"].median() < h.loc[h["lo"] == lo, "hi"].iloc[0]


def test_escolaridade_cubo_cobre_todas_as_movimentacoes(ind):
    assert exportar.escolaridade_cubo(ind)["n"].sum() == len(ind)


def test_geojson_cobre_todos_os_municipios():
    """Pescaria Brava e Balneário Rincão (criados em 2013) já ficaram sem polígono; o mapa não pode ter buraco."""
    geo = json.loads((ROOT / "data/externos/sc_municipios.geojson").read_text())
    ids = {int(f["properties"]["id"]) for f in geo["features"]}
    mun = pd.read_csv(P / "municipios.csv")
    assert set(mun["cod_ibge"]) == ids
    assert len(ids) == 295


def test_regioes_batem_com_a_base_oficial_do_ibge():
    ibge = pd.read_csv(ROOT / "data/externos/regioes_ibge.csv").set_index("cod_municipio")
    mun = pd.read_csv(P / "municipios.csv").set_index("cod_ibge")
    assert mun["regiao_intermediaria"].nunique() == 7 and mun["regiao_imediata"].nunique() == 24
    ref = ibge.loc[mun.index]
    assert (mun["cod_reg_imediata"] == ref["cod_reg_imediata"]).all()
    assert (mun["cod_reg_intermediaria"] == ref["cod_reg_intermediaria"]).all()


def test_manifest_lista_arquivos_existentes():
    manifest = P / "api/manifest.json"
    if not manifest.exists():
        pytest.skip("rode python backend/main.py exportar antes")
    m = json.loads(manifest.read_text())
    for a in m["arquivos"].values():
        dados = json.loads((P / "api" / a["arquivo"]).read_text())
        assert len(dados) == a["linhas"]


def test_pipeline_funciona_sem_regioes_externas():
    """Sem as regiões do IBGE (fonte externa), a junção usa só a base municipal do desafio."""
    import pipeline
    mun = pipeline.carregar_municipios().drop(
        columns=["cod_reg_imediata", "regiao_imediata", "cod_reg_intermediaria", "regiao_intermediaria"],
        errors="ignore")
    df = pd.DataFrame({"município": mun["cod_caged"].head(3).to_numpy(), "subclasse": [1011201] * 3,
                       "cbo2002ocupação": [784205] * 3, "saldomovimentação": [1, -1, -1],
                       "tipomovimentação": [10, 40, 31], "salário": [2000.0] * 3, "horascontratuais": [44] * 3,
                       "indtrabintermitente": [0] * 3, "indicadoraprendiz": [0] * 3, "indtrabparcial": [0] * 3})
    e = pipeline.enriquecer(df, mun)
    assert e["cod_ibge"].notna().all() and "regiao_imediata" not in e.columns
