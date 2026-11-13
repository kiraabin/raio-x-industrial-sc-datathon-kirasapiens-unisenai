"""
Comparação de territórios no formato do Observatório FIESC: notas de 0 a 20 por indicador, agrupadas
em eixos do mercado de trabalho industrial, para municípios ou regiões imediatas.

Nota de cada indicador = posição relativa (percentil) entre os territórios comparáveis, em escala 0–20,
já no sentido "quanto maior, melhor" (ex.: % de saídas a pedido é invertida).
Nota do eixo = média das notas dos indicadores; nota geral = média dos eixos.
Faixas: 0–5 baixo · 6–10 médio · 11–15 bom · 16–20 muito bom.
"""
import numpy as np
import pandas as pd

ESC_SUPERIOR = {9, 10, 11, 80}
ESC_ATE_FUND = {1, 2, 3, 4, 5}

# (coluna, nome, eixo, sentido, formato)   sentido +1 = maior é melhor; -1 = menor é melhor
INDICADORES = [
    ("saldo_10k", "Saldo de vagas por 10 mil hab.", "Dinamismo", +1, "sinal1"),
    ("mov_mil", "Movimentações industriais por mil hab.", "Dinamismo", +1, "dec1"),
    ("pct_pedido", "Saídas a pedido do trabalhador", "Retenção", -1, "pct"),
    ("reposicao", "Desligamentos por admissão", "Retenção", -1, "dec2"),
    ("salario", "Salário mediano de entrada", "Renda", +1, "rs"),
    ("pib_pc", "PIB per capita", "Renda", +1, "rs"),
    ("pct_superior", "Admitidos com ensino superior", "Qualificação", +1, "pct"),
    ("pct_ate_fund", "Admitidos só com fundamental", "Qualificação", -1, "pct"),
    ("idhm", "IDHM", "Desenvolvimento", +1, "dec3"),
    ("escolarizacao", "Escolarização de 6 a 14 anos", "Desenvolvimento", +1, "pct100"),
]
EIXOS = ["Dinamismo", "Retenção", "Renda", "Qualificação", "Desenvolvimento"]
FAIXAS = [(0, 5, "baixo", "#94A3B8"), (6, 10, "médio", "#475569"), (11, 15, "bom", "#F59E0B"),
          (16, 20, "muito bom", "#10B981")]


def faixa(nota: float) -> tuple[str, str]:
    n = int(round(nota))
    for lo, hi, nome, cor in FAIXAS:
        if lo <= n <= hi:
            return nome, cor
    return "baixo", FAIXAS[0][3]


def formatar(valor: float, fmt: str) -> str:
    if valor is None or (isinstance(valor, float) and np.isnan(valor)):
        return "—"
    br = lambda s: s.replace(",", "X").replace(".", ",").replace("X", ".")
    return {
        "sinal1": lambda v: br(f"{v:+,.1f}"),
        "dec1": lambda v: br(f"{v:,.1f}"),
        "dec2": lambda v: br(f"{v:,.2f}"),
        "dec3": lambda v: br(f"{v:,.3f}"),
        "pct": lambda v: br(f"{v * 100:,.1f}") + "%",
        "pct100": lambda v: br(f"{v:,.1f}") + "%",
        "rs": lambda v: "R$ " + br(f"{v:,.0f}"),
    }[fmt](valor)


def _agregar(ind: pd.DataFrame, chave: str) -> pd.DataFrame:
    g = ind.groupby(chave, observed=True)
    out = pd.DataFrame({"adm": g["admissao"].sum(), "mov": g.size()})
    out["desl"] = out["mov"] - out["adm"]
    dd = ind[~ind["admissao"]]
    out["pct_pedido"] = dd.groupby(chave, observed=True)["pedido"].mean()
    out["reposicao"] = out["desl"] / out["adm"].replace(0, np.nan)
    adm = ind[ind["admissao"]]
    out["salario"] = adm[adm["salario_valido"]].groupby(chave, observed=True)["salario"].median()
    out["pct_superior"] = adm.groupby(chave, observed=True)["graudeinstrução"].apply(
        lambda s: s.isin(ESC_SUPERIOR).mean())
    out["pct_ate_fund"] = adm.groupby(chave, observed=True)["graudeinstrução"].apply(
        lambda s: s.isin(ESC_ATE_FUND).mean())
    return out


def base(ind: pd.DataFrame, municipios: pd.DataFrame, nivel: str, min_mov: int = 300) -> pd.DataFrame:
    """Tabela de indicadores e notas por território. nivel = 'Município' ou 'Região imediata'."""
    m = municipios.copy()
    m["pib_total"] = m["pib_per_capita_2023"] * m["pop_censo_2022"]
    if nivel == "Município":
        cols = ["municipio_nome", "pop_estimada_2026", "pib_per_capita_2023", "idhm_2010", "escolarizacao_6_14"]
        t = _agregar(ind, "cod_ibge").join(m.set_index("cod_ibge")[cols], how="inner")
        t = t.rename(columns={"municipio_nome": "nome", "pop_estimada_2026": "pop", "pib_per_capita_2023": "pib_pc",
                              "idhm_2010": "idhm", "escolarizacao_6_14": "escolarizacao"})
    else:
        demo = m.groupby("regiao_imediata").apply(lambda x: pd.Series({
            "pop": x["pop_estimada_2026"].sum(),
            "pib_pc": x["pib_total"].sum() / x["pop_censo_2022"].sum(),
            "idhm": np.average(x["idhm_2010"].fillna(x["idhm_2010"].mean()), weights=x["pop_censo_2022"]),
            "escolarizacao": np.average(x["escolarizacao_6_14"].fillna(x["escolarizacao_6_14"].mean()),
                                        weights=x["pop_censo_2022"])}), include_groups=False)
        t = _agregar(ind, "regiao_imediata").join(demo, how="inner")
        t["nome"] = t.index.astype(str)
    t = t[t["mov"] >= min_mov].copy()
    t["saldo"] = t["adm"] - t["desl"]
    t["saldo_10k"] = t["saldo"] / t["pop"] * 10_000
    t["mov_mil"] = t["mov"] / t["pop"] * 1_000
    for col, _, _, sentido, _ in INDICADORES:
        rank = t[col].rank(pct=True, ascending=(sentido > 0))
        t[f"n_{col}"] = (rank * 20).round().clip(0, 20)
    for eixo in EIXOS:
        cols = [f"n_{c}" for c, _, e, _, _ in INDICADORES if e == eixo]
        t[f"eixo_{eixo}"] = t[cols].mean(axis=1)
    t["nota_geral"] = t[[f"eixo_{e}" for e in EIXOS]].mean(axis=1)
    return t.reset_index(drop=True).sort_values("nome")


def melhores_piores(linha: pd.Series, n: int = 5) -> tuple[list, list]:
    notas = [(nome, linha[f"n_{col}"]) for col, nome, _, _, _ in INDICADORES if not np.isnan(linha[f"n_{col}"])]
    ordem = sorted(notas, key=lambda x: x[1])
    return ordem[::-1][:n], ordem[:n]


def leitura(linha: pd.Series, ac: pd.DataFrame | None = None) -> str:
    """Parágrafo automático (regras, sem texto escrito à mão) sobre o território."""
    eixos = sorted(((e, linha[f"eixo_{e}"]) for e in EIXOS), key=lambda x: x[1])
    forte, fraco = eixos[-1], eixos[0]
    saldo = linha["saldo"]
    partes = [
        f"<b>{linha['nome']}</b> tem nota geral <b>{formatar(linha['nota_geral'], 'dec1')}</b> "
        f"({faixa(linha['nota_geral'])[0]}). ",
        f"Em 12 meses, a indústria local {'criou' if saldo >= 0 else 'fechou'} "
        f"<b>{f'{abs(saldo):,.0f}'.replace(',', '.')} vagas</b> ({formatar(linha['saldo_10k'], 'sinal1')} por 10 mil "
        f"habitantes), com {formatar(linha['pct_pedido'], 'pct')} das saídas a pedido do trabalhador e salário de "
        f"entrada de {formatar(linha['salario'], 'rs')}. ",
        f"O ponto mais forte é <b>{forte[0].lower()}</b> (nota {forte[1]:.0f}) e o mais frágil é "
        f"<b>{fraco[0].lower()}</b> (nota {fraco[1]:.0f}). ",
    ]
    dica = {
        "Retenção": "A prioridade é segurar quem já foi contratado: piso de entrada e integração dos novos.",
        "Renda": "O salário de entrada abaixo dos pares tende a alimentar pedidos de demissão.",
        "Qualificação": "Há espaço para formação técnica alinhada ao que as indústrias locais contratam.",
        "Dinamismo": "O emprego industrial cresce menos que nos pares: vale investigar perda de competitividade.",
        "Desenvolvimento": "Indicadores sociais de base limitam a atração e a fixação de trabalhadores.",
    }
    partes.append(dica[fraco[0]])
    if ac is not None and len(ac):
        a = ac[ac["parceiro"] != "Monitorar"]
        if len(a):
            p = a.iloc[0]
            partes.append(f" No polo de <b>{p['setor']}</b> ({p['municipio_nome']}), o Raio-X recomenda acionar "
                          f"<b>{p['parceiro']}</b>.")
    return "".join(partes)
