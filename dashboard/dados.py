"""Carga e agregações usadas pelo painel. Tudo vem de data/processed/ (gerado por backend/main.py)."""
import json
from pathlib import Path

import numpy as np
import pandas as pd
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
P = ROOT / "data/processed"

ALERTAS = ["Apagão de mão de obra", "Expansão sob pressão"]
MIN_MOV = 300

TIPO_DESLIG = {40: "Pediu para sair", 31: "Demitido sem justa causa", 43: "Fim de contrato temporário",
               45: "Fim de contrato temporário", 90: "Acordo", 32: "Justa causa"}

MESES = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun", 7: "jul", 8: "ago",
         9: "set", 10: "out", 11: "nov", 12: "dez"}


def rotulo_mes(comp: int) -> str:
    return f"{MESES[comp % 100]}/{str(comp // 100)[2:]}"


def _centroide(geom: dict) -> tuple[float, float]:
    """Centroide do maior anel do polígono (fórmula da área com sinal)."""
    if geom["type"] == "Polygon":
        aneis = [geom["coordinates"][0]]
    else:
        aneis = [poligono[0] for poligono in geom["coordinates"]]
    melhor, area_max = (np.nan, np.nan), -1
    for anel in aneis:
        xy = np.asarray(anel, dtype=float)
        x, y = xy[:, 0], xy[:, 1]
        cruz = x[:-1] * y[1:] - x[1:] * y[:-1]
        a = cruz.sum() / 2
        if abs(a) > area_max and a != 0:
            cx = ((x[:-1] + x[1:]) * cruz).sum() / (6 * a)
            cy = ((y[:-1] + y[1:]) * cruz).sum() / (6 * a)
            melhor, area_max = (cy, cx), abs(a)
    return melhor


@st.cache_data(show_spinner=False)
def carregar() -> dict:
    d = {}
    d["ind"] = pd.read_parquet(P / "industria.parquet")
    for nome in ["ind_regiao_setor", "ind_macrofamilia", "ind_regiao_macrofamilia", "ind_municipio",
                 "municipios", "log_limpeza", "est_logit_pedido", "est_correlacoes",
                 "est_pedido_salario_escolaridade", "est_sensibilidade_pares", "est_sensibilidade_cenarios"]:
        d[nome] = pd.read_csv(P / f"{nome}.csv")
    geo = json.loads((ROOT / "data/sc_municipios.geojson").read_text(encoding="utf-8"))
    d["geo"] = geo
    cent = {int(f["properties"]["id"]): _centroide(f["geometry"]) for f in geo["features"]}
    mun = d["ind_municipio"].copy()
    mun["lat"] = mun["cod_ibge"].map(lambda c: cent.get(c, (np.nan, np.nan))[0])
    mun["lon"] = mun["cod_ibge"].map(lambda c: cent.get(c, (np.nan, np.nan))[1])
    d["ind_municipio"] = mun

    # Região imediata -> intermediária
    reg = d["municipios"][["regiao_imediata", "regiao_intermediaria"]].drop_duplicates()
    d["mapa_regioes"] = reg

    # Robustez do alerta (36 cenários de sensibilidade) anexada ao diagnóstico região x setor
    rs = d["ind_regiao_setor"].merge(
        d["est_sensibilidade_pares"][["regiao_imediata", "setor", "estabilidade", "pct_cenarios_alerta"]],
        on=["regiao_imediata", "setor"], how="left").merge(reg, on="regiao_imediata", how="left")
    rs["robusto"] = rs["diagnostico"].isin(ALERTAS) & (rs["estabilidade"] == "Alerta robusto")
    d["rs"] = rs
    return d


def resumo(df: pd.DataFrame) -> dict:
    """KPIs de um recorte da base de microdados."""
    adm = int(df["admissao"].sum())
    desl = len(df) - adm
    dd = df[~df["admissao"]]
    sal = df.loc[df["admissao"] & df["salario_valido"], "salario"]
    return {
        "adm": adm, "desl": desl, "saldo": adm - desl, "mov": len(df),
        "pedidos": int(dd["pedido"].sum()),
        "pct_pedido": dd["pedido"].mean() if len(dd) else np.nan,
        "sal_med": float(sal.median()) if len(sal) else np.nan,
    }


def mensal(df: pd.DataFrame) -> pd.DataFrame:
    m = df.groupby("competênciamov")["admissao"].agg(adm="sum", mov="size").reset_index()
    m["desl"] = m["mov"] - m["adm"]
    m["saldo"] = m["adm"] - m["desl"]
    m["mes"] = m["competênciamov"].map(rotulo_mes)
    return m


def fmt_int(x) -> str:
    return f"{x:,.0f}".replace(",", ".")


def fmt_sinal(x) -> str:
    return ("+" if x > 0 else "") + fmt_int(x)


def fmt_pct(x, casas=0) -> str:
    return f"{x * 100:.{casas}f}%".replace(".", ",")


def fmt_rs(x) -> str:
    return "R$ " + fmt_int(x)
