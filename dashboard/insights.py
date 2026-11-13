"""Insights automáticos: regras sobre os indicadores que geram frases e recomendações para um recorte."""
import numpy as np

from dados import MIN_MOV, fmt_int, fmt_pct, fmt_rs, fmt_sinal, mensal, resumo

ESC_SUPERIOR = {9, 10, 11, 80}


def _pp(a, b) -> str:
    d = (a - b) * 100
    return f"{d:+.0f} p.p.".replace("-", "−")


def gerar(d: dict, regiao: str | None) -> tuple[list[dict], list[dict]]:
    """Retorna (insights, recomendacoes) para uma região intermediária (ou SC inteira se None)."""
    ind_sc = d["ind"]
    sc = resumo(ind_sc)
    if regiao:
        ind = ind_sc[ind_sc["regiao_intermediaria"] == regiao]
        rs = d["rs"][d["rs"]["regiao_intermediaria"] == regiao]
        rmf = d["ind_regiao_macrofamilia"][d["ind_regiao_macrofamilia"]["regiao_intermediaria"] == regiao]
        pop = d["municipios"].loc[d["municipios"]["regiao_intermediaria"] == regiao, "pop_estimada_2026"].sum()
        nome = f"A região de {regiao}"
    else:
        ind, rs = ind_sc, d["rs"]
        rmf = d["ind_macrofamilia"].assign(regiao_intermediaria="SC")
        pop = d["municipios"]["pop_estimada_2026"].sum()
        nome = "Santa Catarina"
    r = resumo(ind)
    pop_sc = d["municipios"]["pop_estimada_2026"].sum()
    out, rec = [], []

    # 1. Saldo e "esteira"
    s10 = r["saldo"] / pop * 10_000
    s10_sc = sc["saldo"] / pop_sc * 10_000
    verbo = "criou" if r["saldo"] >= 0 else "fechou"
    mov_por_vaga = r["mov"] / r["saldo"] if r["saldo"] > 0 else None
    extra = (f" Foram <b>{fmt_int(mov_por_vaga)} movimentações para cada vaga nova</b>: a indústria gira o quadro "
             "muito mais do que cresce.") if mov_por_vaga and mov_por_vaga > 50 else ""
    out.append(dict(tipo="ok" if r["saldo"] >= 0 else "alerta", ic="📍",
                    tx=f"{nome} {verbo} <b>{fmt_int(abs(r['saldo']))} vagas industriais</b> em 12 meses"
                       + (f" ({fmt_sinal(round(s10))} por 10 mil habitantes; média de SC: {fmt_sinal(round(s10_sc))})."
                          if regiao else ".") + extra,
                    nota=f"{fmt_int(r['adm'])} admissões e {fmt_int(r['desl'])} desligamentos"))

    # 2. Retenção
    dif = r["pct_pedido"] - sc["pct_pedido"]
    if regiao:
        tipo = "alerta" if dif > 0.03 else ("ok" if dif < -0.03 else "atencao")
        comp = f"{_pp(r['pct_pedido'], sc['pct_pedido'])} em relação a SC ({fmt_pct(sc['pct_pedido'])})"
    else:
        tipo, comp = "alerta", "o trabalhador sai porque tem opção ou porque a proposta não segura"
    out.append(dict(tipo=tipo, ic="🚪",
                    tx=f"<b>{fmt_pct(r['pct_pedido'])} dos desligamentos foram pedidos do próprio trabalhador</b> "
                       f"({fmt_int(r['pedidos'])} pedidos): {comp}.",
                    nota="Desligamento a pedido = tipo 40 do Novo CAGED"))

    # 3. Polo mais crítico (alerta robusto)
    rob = rs[rs["robusto"]].sort_values("movimentacoes", ascending=False)
    if len(rob):
        p = rob.iloc[0]
        out.append(dict(tipo="alerta", ic="🔥",
                        tx=f"Polo mais crítico: <b>{p['setor']} em {p['regiao_imediata']}</b>. "
                           f"{fmt_pct(p['pct_pedido_demissao'])} das saídas são a pedido e cada contratação só repõe "
                           f"uma saída (reposição {str(round(p['indice_reposicao'], 2)).replace('.', ',')}). Salário de entrada: "
                           f"{fmt_rs(p['salario_mediano_adm'])}.",
                        nota=f"Alerta robusto: mantém-se em {fmt_pct(p['pct_cenarios_alerta'])} dos 36 cenários "
                             f"de calibração. Total de polos robustos no recorte: {len(rob)}"))
    else:
        out.append(dict(tipo="ok", ic="✅", tx="Nenhum par região × setor com <b>alerta robusto</b> de apagão neste recorte.",
                        nota="Alerta robusto = aparece em pelo menos 80% dos 36 cenários de calibração"))

    # 4. Expansão
    setor = (ind.groupby("setor", observed=True)["admissao"].agg(adm="sum", mov="size")
             .assign(saldo=lambda x: 2 * x["adm"] - x["mov"]).sort_values("saldo", ascending=False))
    if len(setor) and setor["saldo"].iloc[0] > 0:
        s_nome, s_saldo = setor.index[0], setor["saldo"].iloc[0]
        onde = rs[(rs["setor"] == s_nome)].sort_values("saldo", ascending=False)
        local = f", puxado por {onde['regiao_imediata'].iloc[0]} ({fmt_sinal(onde['saldo'].iloc[0])})" if len(onde) else ""
        out.append(dict(tipo="ok", ic="📈",
                        tx=f"Quem mais cria vagas: <b>{s_nome}</b> ({fmt_sinal(s_saldo)}){local}.",
                        nota="Saldo = admissões − desligamentos no período"))

    # 5. Salário
    if regiao and not np.isnan(r["sal_med"]):
        gap = r["sal_med"] / sc["sal_med"] - 1
        out.append(dict(tipo="atencao" if gap < -0.03 else "ok", ic="💰",
                        tx=f"Salário mediano de admissão de <b>{fmt_rs(r['sal_med'])}</b>, "
                           f"{'abaixo' if gap < 0 else 'acima'} da mediana de SC ({fmt_rs(sc['sal_med'])}) em "
                           f"{abs(gap) * 100:.0f}%.",
                        nota="Salários válidos: R$ 800 a R$ 60 mil, jornada ≥ 30h, sem intermitentes/aprendizes"))
    elif not regiao:
        out.append(dict(tipo="atencao", ic="💰",
                        tx="Quem ganha até <b>R$ 2 mil</b> pede demissão em <b>57%</b> dos desligamentos; "
                           "acima de R$ 3,6 mil, em 41%. Pagar 10% acima da mediana da ocupação reduz a chance de "
                           "pedido de demissão em cerca de 6%.",
                        nota="Quintis salariais e regressão logística com 391 mil desligamentos"))

    # 6. Macrofamília (IA) mais pressionada
    m = rmf[rmf["movimentacoes"] >= MIN_MOV].sort_values("pct_pedido_demissao", ascending=False)
    if len(m):
        f = m.iloc[0]
        out.append(dict(tipo="atencao", ic="🧠",
                        tx=f"Família de ocupações (IA) que mais perde gente: <b>{f['macrofamilia']}</b>, com "
                           f"{fmt_pct(f['pct_pedido_demissao'])} das saídas a pedido e salário de entrada de "
                           f"{fmt_rs(f['salario_mediano_adm'])}.",
                        nota="16 macrofamílias criadas por IA a partir de 1.467 CBOs"))

    # 7. Escolaridade
    adm = ind[ind["admissao"]]
    sup = adm["graudeinstrução"].isin(ESC_SUPERIOR).mean()
    sup_sc = ind_sc.loc[ind_sc["admissao"], "graudeinstrução"].isin(ESC_SUPERIOR).mean()
    out.append(dict(tipo="info", ic="🎓",
                    tx=f"Só <b>{fmt_pct(sup, 1)}</b> dos admitidos têm ensino superior"
                       + (f" (SC: {fmt_pct(sup_sc, 1)})" if regiao else "")
                       + ": a demanda é operacional. O gargalo não é diploma, é retenção.",
                    nota="Grau de instrução 9 a 11 e 80 do Novo CAGED"))

    # 8. Sazonalidade
    mm = mensal(ind)
    pior = mm.loc[mm["saldo"].idxmin()]
    out.append(dict(tipo="info", ic="🗓️",
                    tx=f"Pior mês: <b>{pior['mes']}</b> ({fmt_sinal(pior['saldo'])} vagas). Planeje contratações e "
                       "turmas de formação para a recomposição de janeiro a março.",
                    nota="Dezembro concentra fim de contratos temporários e férias coletivas"))

    # ---------- Recomendações automáticas ----------
    if len(rob):
        p = rob.iloc[0]
        rec.append(dict(ic="🤝", t="Programa de retenção",
                        tx=f"Priorizar <b>{p['setor']} em {p['regiao_imediata']}</b>: trilha de carreira curta "
                           "(operador I → III em 12 meses) e bônus de permanência aos 6 e 12 meses.",
                        meta=f"Meta: reduzir em 10% os pedidos de demissão ({fmt_int(p['desligamentos'] * p['pct_pedido_demissao'] * 0.1)} saídas a menos por ano)"))
    if regiao and not np.isnan(r["sal_med"]) and r["sal_med"] < sc["sal_med"]:
        rec.append(dict(ic="💰", t="Piso de entrada competitivo",
                        tx="O salário de entrada está abaixo da mediana estadual. Comparar o piso com a mediana "
                           "da mesma ocupação: +10% sobre a mediana reduz em ~6% a chance de pedido de demissão.",
                        meta="Indicador: salário de admissão ÷ mediana da CBO em SC"))
    if len(setor) and setor["saldo"].iloc[0] > 200:
        rec.append(dict(ic="🎓", t="Formação onde há expansão",
                        tx=f"Turmas curtas (SENAI + empresas) para <b>{setor.index[0]}</b>, o setor que mais cria vagas "
                           "no recorte, antes que a expansão vire falta de gente.",
                        meta="Indicador: tempo de preenchimento das vagas abertas"))
    if not rec:
        rec.append(dict(ic="📊", t="Monitoramento trimestral",
                        tx="Sem alerta crítico agora. Acompanhar o Índice de Pressão a cada trimestre para agir "
                           "antes que um setor entre no quadrante de apagão.",
                        meta="Gatilho: dois trimestres seguidos acima de 0,5"))
    return out, rec
