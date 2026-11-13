"""Insights estatísticos do Raio-X, calculados a partir das saídas do pipeline.

Roda só com data/processed/ (não precisa do CSV bruto do CAGED).

Saídas (data/processed/est_*.csv):
  1. Renda, escolaridade e desligamento a pedido
     est_pedido_salario_escolaridade.csv  % a pedido por quintil de salário × faixa de escolaridade
     est_correlacoes.csv                  correlações de Spearman (microdado, município × setor, município)
     est_logit_pedido.csv                 razões de chance (regressão logística) de o desligamento ser a pedido
  2. Sensibilidade do Índice de Pressão
     est_sensibilidade_cenarios.csv       contagem de diagnósticos por método × volume mínimo × limiar
     est_sensibilidade_pares.csv          estabilidade do alerta de cada par município × setor
  3. Sazonalidade (perfil intra-anual: a base cobre 12 meses, então não separa sazonalidade de tendência)
     est_sazonalidade_mensal.csv          fluxo mensal total, por setor, região intermediária e nível
     est_sazonalidade_resumo.csv          pico, vale, amplitude e risco de recorte por setor
"""
from itertools import product
from pathlib import Path

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy.stats import spearmanr

from indicadores import METODOS_PRESSAO, MIN_MOV, classificar

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data/processed"

ALERTA = ["Apagão de mão de obra", "Expansão sob pressão"]
FAIXA_ESC = {1: "Até fundamental", 2: "Até fundamental", 3: "Até fundamental",
             4: "Até fundamental", 5: "Até fundamental", 6: "Médio", 7: "Médio",
             8: "Superior incompleto", 9: "Superior ou mais", 10: "Superior ou mais",
             11: "Superior ou mais", 80: "Superior ou mais"}
ORDEM_ESC = ["Até fundamental", "Médio", "Superior incompleto", "Superior ou mais"]
# Anos de estudo aproximados, para tratar a escolaridade como variável ordinal
ANOS_ESTUDO = {1: 0, 2: 3, 3: 5, 4: 7, 5: 9, 6: 10, 7: 12, 8: 14, 9: 16, 80: 17, 10: 18, 11: 22}
FAIXA_IDADE = [13, 24, 29, 39, 49, 120]
ROTULO_IDADE = ["14-24", "25-29", "30-39", "40-49", "50+"]
MES = {1: "jan", 2: "fev", 3: "mar", 4: "abr", 5: "mai", 6: "jun",
       7: "jul", 8: "ago", 9: "set", 10: "out", 11: "nov", 12: "dez"}


# ---------------------------------------------------------------- 1. Renda e escolaridade

def base_desligamentos(ind: pd.DataFrame) -> pd.DataFrame:
    """Desligamentos com salário válido e escolaridade conhecida, com variáveis derivadas."""
    d = ind[~ind["admissao"] & ind["salario_valido"] & ind["graudeinstrução"].isin(ANOS_ESTUDO)].copy()
    d["faixa_esc"] = pd.Categorical(d["graudeinstrução"].map(FAIXA_ESC), ORDEM_ESC, ordered=True)
    d["anos_estudo"] = d["graudeinstrução"].map(ANOS_ESTUDO)
    d["quintil_sal"] = pd.qcut(d["salario"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"])
    # Salário relativo à ocupação: separa "ocupação bem paga" de "pago acima dos colegas"
    mediana_cbo = d.groupby("cbo")["salario"].transform("median")
    d["log_sal_cbo"] = np.log(mediana_cbo)
    d["sal_rel_cbo"] = np.log(d["salario"] / mediana_cbo)
    d["faixa_idade"] = pd.cut(d["idade"], FAIXA_IDADE, labels=ROTULO_IDADE)
    d["porte"] = d["tamestabjan"].astype(str)
    d["mulher"] = (d["sexo"] == 3).astype(int)
    d["ped"] = d["pedido"].astype(int)
    return d


def grade_salario_escolaridade(d: pd.DataFrame) -> pd.DataFrame:
    """% a pedido em cada célula quintil de salário × escolaridade, com as margens ('Todas')."""
    partes = []
    for q, e in [("quintil_sal", "faixa_esc"), ("quintil_sal", None), (None, "faixa_esc"), (None, None)]:
        chaves = [c for c in (q, e) if c]
        g = (d.groupby(chaves, observed=True) if chaves else d.assign(_=0).groupby("_"))
        r = g.agg(desligamentos=("ped", "size"), a_pedido=("ped", "sum"),
                  salario_mediano=("salario", "median"),
                  salario_min=("salario", "min"), salario_max=("salario", "max")).reset_index()
        r["quintil_sal"] = r[q].astype(str) if q else "Todas"
        r["faixa_esc"] = r[e].astype(str) if e else "Todas"
        partes.append(r[["quintil_sal", "faixa_esc", "desligamentos", "a_pedido",
                         "salario_mediano", "salario_min", "salario_max"]])
    r = pd.concat(partes, ignore_index=True)
    r["pct_pedido"] = r["a_pedido"] / r["desligamentos"]
    return r


def _spearman(df: pd.DataFrame, pares: list[tuple[str, str]], nivel: str) -> list[dict]:
    linhas = []
    for x, y in pares:
        s = df[[x, y]].dropna()
        rho, p = spearmanr(s[x], s[y])
        linhas.append({"nivel": nivel, "var_x": x, "var_y": y, "rho": rho, "p_valor": p, "n": len(s)})
    return linhas


def correlacoes(d: pd.DataFrame, rs: pd.DataFrame, mun_ind: pd.DataFrame,
                mun: pd.DataFrame) -> pd.DataFrame:
    """Spearman em três níveis. No microdado o n é enorme (p ≈ 0 sempre): leia o rho."""
    linhas = _spearman(d, [("salario", "ped"), ("anos_estudo", "ped"), ("salario", "anos_estudo"),
                           ("sal_rel_cbo", "ped"), ("log_sal_cbo", "ped"), ("idade", "ped")],
                       "desligamento")
    agregadas = ["salario_mediano_adm", "pct_superior_adm", "pct_ate_fundamental_adm",
                 "idade_media_adm"]
    alvos = ["pct_pedido_demissao", "indice_pressao", "premio_salarial", "saldo_10k_hab"]
    rs_ok = rs[rs["movimentacoes"] >= MIN_MOV]
    linhas += _spearman(rs_ok, list(product(agregadas, alvos)), "municipio_setor")
    m = mun_ind.merge(mun[["cod_ibge", "idhm_2010", "pib_per_capita_2023", "escolarizacao_6_14"]],
                      on="cod_ibge")
    m = m[m["movimentacoes"] >= MIN_MOV]
    linhas += _spearman(m, list(product(agregadas + ["idhm_2010", "pib_per_capita_2023",
                                                     "escolarizacao_6_14"], alvos)), "municipio")
    r = pd.DataFrame(linhas)
    r["significativo_5pct"] = r["p_valor"] < 0.05
    return r


def logit_pedido(d: pd.DataFrame) -> pd.DataFrame:
    """Chance de o desligamento ser a pedido, controlando setor, porte, idade e sexo.

    O log do salário é decomposto em duas partes:
      log_sal_cbo  quanto a ocupação paga (mediana da CBO)
      sal_rel_cbo  quanto o trabalhador ganhava acima ou abaixo dos colegas da mesma CBO
    Erros-padrão agrupados por CBO. Os efeitos fixos de setor e porte não são exportados.
    """
    d = d.dropna(subset=["faixa_idade"])
    formula = ("ped ~ log_sal_cbo + sal_rel_cbo + C(faixa_esc, Treatment('Até fundamental'))"
               " + C(faixa_idade, Treatment('30-39')) + mulher"
               " + C(setor) + C(porte)")
    d = d.assign(faixa_esc=d["faixa_esc"].astype(str), faixa_idade=d["faixa_idade"].astype(str),
                 setor=d["setor"].astype(str))
    m = smf.logit(formula, data=d).fit(disp=0, cov_type="cluster",
                                       cov_kwds={"groups": d["cbo"].to_numpy()})
    ic = m.conf_int()
    termos = [t for t in m.params.index
              if not t.startswith(("C(setor", "C(regiao", "C(porte", "Intercept"))]
    r = pd.DataFrame({"termo": termos,
                      "coef": m.params[termos].to_numpy(),
                      "razao_chance": np.exp(m.params[termos]).to_numpy(),
                      "ic95_inf": np.exp(ic.loc[termos, 0]).to_numpy(),
                      "ic95_sup": np.exp(ic.loc[termos, 1]).to_numpy(),
                      "p_valor": m.pvalues[termos].to_numpy()})
    r["termo"] = (r["termo"].str.replace(r"C\((\w+), Treatment\('[^']+'\)\)\[T\.(.+)\]",
                                         r"\1 = \2", regex=True))
    # Para os termos em log: razão de chance de um salário 10% maior
    log = r["termo"].isin(["log_sal_cbo", "sal_rel_cbo"])
    r["razao_chance_10pct"] = np.where(log, np.exp(r["coef"] * np.log(1.1)), np.nan)
    r["n"] = int(m.nobs)
    r["pseudo_r2"] = m.prsquared
    return r


# ---------------------------------------------------------------- 2. Sensibilidade

def sensibilidade(rs: pd.DataFrame, min_movs=(200, 300, 500, 1000),
                  limiares=(0.3, 0.5, 0.7), chave=("regiao_imediata", "setor")) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Reclassifica os pares território × setor em todos os cenários método × volume × limiar."""
    base = rs.drop(columns=["indice_pressao", "indice_expansao", "diagnostico"], errors="ignore")
    chave = list(chave)
    contagens, por_par = [], []
    for metodo, mm, lim in product(METODOS_PRESSAO, min_movs, limiares):
        t = classificar(base, min_mov=mm, metodo=metodo, limiar=lim)
        c = t["diagnostico"].value_counts()
        contagens.append({"metodo": metodo, "min_mov": mm, "limiar": lim,
                          "padrao": metodo == "atual" and mm == MIN_MOV and lim == 0.5,
                          **{k: int(c.get(k, 0)) for k in
                             ["Apagão de mão de obra", "Expansão sob pressão", "Expansão acelerada",
                              "Retração", "Estável", "Volume insuficiente"]}})
        por_par.append(t[chave + ["diagnostico", "indice_pressao"]].assign(
            metodo=metodo, min_mov=mm, limiar=lim))
    cen = pd.DataFrame(contagens)
    cen["alertas"] = cen[ALERTA].sum(axis=1)

    p = pd.concat(por_par, ignore_index=True)
    p["avaliado"] = p["diagnostico"] != "Volume insuficiente"
    p["alerta"] = p["diagnostico"].isin(ALERTA)
    pares = (p.groupby(chave).agg(cenarios_avaliados=("avaliado", "sum"),
                                  cenarios_alerta=("alerta", "sum"))
             .reset_index())
    pares["pct_cenarios_alerta"] = pares["cenarios_alerta"] / pares["cenarios_avaliados"].replace(0, np.nan)
    atual = rs[chave + ["movimentacoes", "saldo", "pct_pedido_demissao", "premio_salarial",
                        "indice_reposicao", "indice_pressao", "diagnostico"]]
    pares = atual.merge(pares, on=chave)
    # Pressão no método sem reposição (volume e limiar padrão), para comparar com a atual
    sem_rep = classificar(base, metodo="sem_reposicao")[chave + ["indice_pressao", "diagnostico"]]
    pares = pares.merge(sem_rep.rename(columns={"indice_pressao": "indice_pressao_sem_reposicao",
                                                "diagnostico": "diagnostico_sem_reposicao"}), on=chave)
    pares["estabilidade"] = pd.cut(pares["pct_cenarios_alerta"], [-0.01, 0, 0.2, 0.8, 1.0],
                                   labels=["Nunca em alerta", "Alerta raro", "Alerta frágil",
                                           "Alerta robusto"]).astype(str)
    # Abaixo do volume padrão o par só é avaliado nos cenários de volume baixo: não dá para chamar de robusto
    pares.loc[pares["movimentacoes"] < MIN_MOV, "estabilidade"] = "Sem volume"
    return cen, pares.sort_values("pct_cenarios_alerta", ascending=False)


# ---------------------------------------------------------------- 3. Sazonalidade

def _fluxo_mensal(ind: pd.DataFrame, recorte: str | None) -> pd.DataFrame:
    chaves = ([recorte] if recorte else []) + ["competênciamov"]
    x = ind.assign(adm=ind["admissao"].astype(int),
                   desl=(~ind["admissao"]).astype(int),
                   ped=(~ind["admissao"] & ind["pedido"]).astype(int),
                   termino=(ind["tipomovimentação"] == 43).astype(int),
                   sal_adm=ind["salario"].where(ind["admissao"] & ind["salario_valido"]))
    g = (x.groupby(chaves, observed=True)
         .agg(admissoes=("adm", "sum"), desligamentos=("desl", "sum"), a_pedido=("ped", "sum"),
              termino_contrato=("termino", "sum"), salario_mediano_adm=("sal_adm", "median"))
         .reset_index())
    g["recorte_tipo"] = recorte or "total"
    g["recorte"] = g[recorte].astype(str) if recorte else "Indústria de transformação"
    return g.drop(columns=[recorte] if recorte else [])


def sazonalidade_mensal(ind: pd.DataFrame) -> pd.DataFrame:
    recortes = [None, "setor", "nivel_ocupacao"] + (["regiao_intermediaria"] if "regiao_intermediaria" in ind else [])
    g = pd.concat([_fluxo_mensal(ind, r) for r in recortes], ignore_index=True)
    g = g.sort_values(["recorte_tipo", "recorte", "competênciamov"])
    g["mes"] = (g["competênciamov"] % 100).map(MES) + "/" + (g["competênciamov"] // 100 % 100).astype(str)
    g["saldo"] = g["admissoes"] - g["desligamentos"]
    g["movimentacoes"] = g["admissoes"] + g["desligamentos"]
    g["pct_pedido"] = g["a_pedido"] / g["desligamentos"]
    g["pct_termino_contrato"] = g["termino_contrato"] / g["desligamentos"]
    grp = g.groupby(["recorte_tipo", "recorte"])
    g["saldo_acumulado"] = grp["saldo"].cumsum()
    # Saldo do mês em relação ao fluxo médio mensal do recorte: compara setores de tamanhos diferentes
    g["saldo_sobre_fluxo_medio"] = g["saldo"] / grp["movimentacoes"].transform("mean")
    cols = ["recorte_tipo", "recorte", "competênciamov", "mes", "admissoes", "desligamentos",
            "saldo", "saldo_acumulado", "saldo_sobre_fluxo_medio", "movimentacoes", "a_pedido",
            "pct_pedido", "termino_contrato", "pct_termino_contrato", "salario_mediano_adm"]
    return g[cols].reset_index(drop=True)


def sazonalidade_resumo(mensal: pd.DataFrame) -> pd.DataFrame:
    """Uma linha por recorte: onde está o pico, o vale e quanto um recorte parcial engana."""
    linhas = []
    for (tipo, rec), g in mensal.groupby(["recorte_tipo", "recorte"]):
        g = g.set_index("mes")
        anual = g["saldo"].sum()
        linhas.append({
            "recorte_tipo": tipo, "recorte": rec,
            "saldo_anual": anual,
            "movimentacoes_anuais": g["movimentacoes"].sum(),
            "mes_pico": g["saldo"].idxmax(), "saldo_pico": g["saldo"].max(),
            "mes_vale": g["saldo"].idxmin(), "saldo_vale": g["saldo"].min(),
            # Amplitude em unidades de fluxo médio mensal: 1,0 = oscila o equivalente a um mês inteiro
            "amplitude_relativa": g["saldo_sobre_fluxo_medio"].max() - g["saldo_sobre_fluxo_medio"].min(),
            "saldo_dez": g["saldo"].filter(like="dez").sum(),
            "saldo_sem_dez_jan": anual - g["saldo"].filter(regex="^(dez|jan)").sum(),
            "pior_saldo_acumulado": g["saldo_acumulado"].min(),
            "mes_pior_acumulado": g["saldo_acumulado"].idxmin(),
            "pct_pedido_min": g["pct_pedido"].min(), "pct_pedido_max": g["pct_pedido"].max(),
            "pct_termino_contrato_dez": g["pct_termino_contrato"].filter(like="dez").mean(),
            "pct_termino_contrato_medio": g["termino_contrato"].sum() / g["desligamentos"].sum(),
        })
    r = pd.DataFrame(linhas)
    # Fração do ano em que o saldo acumulado esteve com sinal oposto ao do saldo anual:
    # mede o risco de um recorte parcial (ex.: set–dez) contar a história errada
    sinal = mensal.merge(r[["recorte_tipo", "recorte", "saldo_anual"]], on=["recorte_tipo", "recorte"])
    sinal["oposto"] = np.sign(sinal["saldo_acumulado"]) != np.sign(sinal["saldo_anual"])
    r = r.merge(sinal.groupby(["recorte_tipo", "recorte"])["oposto"].mean()
                .rename("pct_meses_sinal_oposto").reset_index(), on=["recorte_tipo", "recorte"])
    return r.sort_values(["recorte_tipo", "amplitude_relativa"], ascending=[True, False])


# ---------------------------------------------------------------- Execução

def main():
    ind = pd.read_parquet(OUT / "industria.parquet")
    rs = pd.read_csv(OUT / "ind_municipio_setor.csv")
    mun_ind = pd.read_csv(OUT / "ind_municipio.csv")
    mun = pd.read_csv(OUT / "municipios.csv")

    d = base_desligamentos(ind)
    saidas = {
        "est_pedido_salario_escolaridade": grade_salario_escolaridade(d),
        "est_correlacoes": correlacoes(d, rs, mun_ind, mun),
        "est_logit_pedido": logit_pedido(d),
    }
    cen, pares = sensibilidade(rs, chave=("cod_ibge", "setor"))
    pares = pares.merge(rs[["cod_ibge", "municipio_nome"]].drop_duplicates(), on="cod_ibge")
    saidas["est_sensibilidade_cenarios"], saidas["est_sensibilidade_pares"] = cen, pares
    # Seção externa: robustez também para região imediata × setor (regiões do IBGE)
    if (OUT / "ind_regiao_setor.csv").exists():
        saidas["est_sensibilidade_pares_regiao"] = sensibilidade(pd.read_csv(OUT / "ind_regiao_setor.csv"))[1]
    mensal = sazonalidade_mensal(ind)
    saidas["est_sazonalidade_mensal"] = mensal
    saidas["est_sazonalidade_resumo"] = sazonalidade_resumo(mensal)

    for nome, df in saidas.items():
        df.to_csv(OUT / f"{nome}.csv", index=False)
        print(f"{nome + '.csv':<42} {len(df):>6} linhas")
    return saidas


if __name__ == "__main__":
    main()
