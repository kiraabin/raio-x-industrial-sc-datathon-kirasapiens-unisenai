"""Exporta os dados prontos para o frontend React (data/processed/api/*.json).

- Uma versão JSON de cada CSV de data/processed/ (lista de registros; NaN vira null).
- cubo.json: contagens aditivas por região imediata × setor × competência, para o frontend
  filtrar e somar sem precisar do microdado (medianas não somam, por isso ficam de fora).
- salario_hist.json: histograma do salário de admissão (válido) por região intermediária × setor.
  Contagens somam, então o frontend recompõe a mediana do recorte filtrado (faixas de R$ 10 nos salários comuns; erro < R$ 10).
- escolaridade_cubo.json: movimentações por região intermediária × setor × (admitidos/desligados) ×
  faixa de escolaridade, para o gráfico "quem entra x quem sai".
- manifest.json: lista dos arquivos, colunas, número de linhas e metadados da base.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
# Os JSONs do frontend React (protótipo, não é o entregável oficial) agrupam por região do IBGE, um dado externo.
# Sem data/externos/regioes_ibge.csv, agrupam por município (base fornecida pelo desafio).


def _territorio(ind: pd.DataFrame, nivel: str) -> list[str]:
    if "regiao_intermediaria" in ind.columns:
        return ["regiao_intermediaria", "regiao_imediata"] if nivel == "imediata" else ["regiao_intermediaria"]
    return ["municipio_nome"]
OUT = ROOT / "data/processed"
API = OUT / "api"


def cubo(ind: pd.DataFrame) -> pd.DataFrame:
    x = ind.assign(adm=ind["admissao"].astype(int),
                   desl=(~ind["admissao"]).astype(int),
                   ped=(~ind["admissao"] & ind["pedido"]).astype(int),
                   adm_superior=(ind["admissao"] & ind["graudeinstrução"].isin({9, 10, 11, 80})).astype(int))
    c = (x.groupby(_territorio(ind, "imediata") + ["setor", "competênciamov"], observed=True)
         .agg(admissoes=("adm", "sum"), desligamentos=("desl", "sum"),
              a_pedido=("ped", "sum"), adm_superior=("adm_superior", "sum"))
         .reset_index())
    c["saldo"] = c["admissoes"] - c["desligamentos"]
    return c.rename(columns={"competênciamov": "competencia"})


ESC_MAP = {1: "Até fundamental", 2: "Até fundamental", 3: "Até fundamental", 4: "Até fundamental",
           5: "Até fundamental", 6: "Médio incompleto", 7: "Médio completo",
           8: "Superior (incompleto ou mais)", 9: "Superior (incompleto ou mais)",
           10: "Superior (incompleto ou mais)", 11: "Superior (incompleto ou mais)",
           80: "Superior (incompleto ou mais)"}


def bordas_salario() -> np.ndarray:
    """Faixas de R$ 10 até 4.000, de R$ 50 até 6.000 e de R$ 500 até 60.000 (salário válido = 800 a 60 mil)."""
    return np.unique(np.concatenate([np.arange(800, 4000, 10), np.arange(4000, 6000, 50),
                                     np.arange(6000, 60001, 500), [60001]]))


def salario_hist(ind: pd.DataFrame) -> pd.DataFrame:
    a = ind[ind["admissao"] & ind["salario_valido"]]
    b = bordas_salario()
    idx = np.clip(np.searchsorted(b, a["salario"].to_numpy(), side="right") - 1, 0, len(b) - 2)
    t = _territorio(ind, "intermediaria")
    h = (a.assign(i=idx).groupby(t + ["setor", "i"], observed=True)
         .size().reset_index(name="n"))
    h["lo"] = b[h["i"]]
    h["hi"] = b[h["i"] + 1]
    return h[t + ["setor", "lo", "hi", "n"]]


def escolaridade_cubo(ind: pd.DataFrame) -> pd.DataFrame:
    x = ind.assign(esc=ind["graudeinstrução"].map(ESC_MAP),
                   mov=np.where(ind["admissao"], "Admitidos", "Desligados")).dropna(subset=["esc"])
    return (x.groupby(_territorio(ind, "intermediaria") + ["setor", "mov", "esc"], observed=True)
            .size().reset_index(name="n"))


def _gravar(df: pd.DataFrame, nome: str) -> dict:
    caminho = API / f"{nome}.json"
    df.to_json(caminho, orient="records", force_ascii=False, double_precision=6)
    return {"arquivo": caminho.name, "linhas": len(df), "colunas": list(df.columns)}


def main():
    API.mkdir(parents=True, exist_ok=True)
    ind = pd.read_parquet(OUT / "industria.parquet")
    arquivos = {"cubo": _gravar(cubo(ind), "cubo"),
                "salario_hist": _gravar(salario_hist(ind), "salario_hist"),
                "escolaridade_cubo": _gravar(escolaridade_cubo(ind), "escolaridade_cubo")}
    for csv in sorted(OUT.glob("*.csv")):
        arquivos[csv.stem] = _gravar(pd.read_csv(csv), csv.stem)

    comp = ind["competênciamov"]
    manifest = {
        "gerado_em": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "base": "Novo CAGED SC, indústria de transformação (CNAE seção C)",
        "janela": {"inicio": int(comp.min()), "fim": int(comp.max())},
        "movimentacoes": len(ind),
        "admissoes": int(ind["admissao"].sum()),
        "desligamentos": int((~ind["admissao"]).sum()),
        "arquivos": arquivos,
    }
    (API / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2))
    for nome, a in arquivos.items():
        print(f"api/{a['arquivo']:<44} {a['linhas']:>6} linhas")
    return manifest


if __name__ == "__main__":
    main()
