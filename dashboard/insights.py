"""Insights automáticos: regras sobre os indicadores que geram frases para um recorte (SC ou um município).

Usa apenas as bases do desafio (CAGED, municípios e dicionário) e as macrofamílias de CBO criadas por IA.
"""
import numpy as np

from dados import MIN_MOV, fmt_int, fmt_pct, fmt_rs, fmt_sinal, mensal, resumo

ESC_SUPERIOR = {9, 10, 11, 80}


def _pp(a, b) -> str:
    return f"{(a - b) * 100:+.0f} p.p.".replace("-", "−")


def gerar(d: dict, municipio: str | None, setor: str | None = None) -> list[dict]:
    ind_sc = d["ind"]
    sc = resumo(ind_sc)
    ind, rs = ind_sc, d["rs"]
    nome = "Santa Catarina"
    if municipio:
        ind = ind[ind["municipio_nome"] == municipio]
        rs = rs[rs["municipio_nome"] == municipio]
        nome = municipio
    if setor:
        ind = ind[ind["setor"] == setor]
        rs = rs[rs["setor"] == setor]
        nome += f" ({setor})"
    r = resumo(ind)
    out = []
    if r["mov"] == 0:
        return [dict(tipo="info", ic="ℹ️", tx="Sem movimentações neste recorte.", nota="")]

    # 1. Retenção comparada a SC
    if municipio or setor:
        dif = r["pct_pedido"] - sc["pct_pedido"]
        tipo = "alerta" if dif > 0.03 else ("ok" if dif < -0.03 else "atencao")
        comp = f"{_pp(r['pct_pedido'], sc['pct_pedido'])} em relação a SC ({fmt_pct(sc['pct_pedido'])})"
    else:
        tipo, comp = "alerta", "o trabalhador sai porque tem opção ou porque a proposta não segura"
    out.append(dict(tipo=tipo, ic="🚪", tx=f"<b>{fmt_pct(r['pct_pedido'])} dos desligamentos foram pedidos do "
                    f"próprio trabalhador</b> ({fmt_int(r['pedidos'])} pedidos): {comp}.",
                    nota="Desligamento a pedido = tipo 40 do Novo CAGED"))

    # 2. Polo mais crítico (alerta robusto)
    rob = rs[rs["robusto"]].sort_values("movimentacoes", ascending=False)
    if len(rob):
        p = rob.iloc[0]
        rep = str(round(p["indice_reposicao"], 2)).replace(".", ",")
        local = "" if municipio else f" em {p['municipio_nome']}"
        out.append(dict(tipo="alerta", ic="🔥",
                        tx=f"Polo mais crítico: <b>{p['setor']}{local}</b>. {fmt_pct(p['pct_pedido_demissao'])} das "
                           f"saídas são a pedido e cada contratação só repõe uma saída (reposição {rep}). "
                           f"Salário de entrada: {fmt_rs(p['salario_mediano_adm'])}.",
                        nota=f"{len(rob)} polos com alerta robusto no recorte"))
    else:
        out.append(dict(tipo="ok", ic="✅", tx="Nenhum polo (município × setor) com <b>alerta robusto</b> de apagão "
                        "neste recorte.", nota="Alerta robusto = mantém-se em mais de 80% das calibrações aplicáveis (até 48)"))

    # 3. Quem mais cria vagas
    if setor:
        g = ind.groupby("municipio_nome", observed=True)["admissao"].agg(adm="sum", mov="size")
        rot = "Município que mais cria vagas"
    else:
        g = ind.groupby("setor", observed=True)["admissao"].agg(adm="sum", mov="size")
        rot = "Setor que mais cria vagas"
    g = g.assign(saldo=2 * g["adm"] - g["mov"]).sort_values("saldo", ascending=False)
    if len(g) and g["saldo"].iloc[0] > 0:
        extra = ""
        if not municipio and not setor:
            onde = rs[rs["setor"] == g.index[0]].sort_values("saldo", ascending=False)
            extra = f", puxado por {onde['municipio_nome'].iloc[0]} ({fmt_sinal(onde['saldo'].iloc[0])})" if len(onde) else ""
        out.append(dict(tipo="ok", ic="📈", tx=f"{rot}: <b>{g.index[0]}</b> ({fmt_sinal(g['saldo'].iloc[0])}){extra}.",
                        nota="Saldo = admissões − desligamentos no período"))

    # 4. Salário de entrada
    if not np.isnan(r["sal_med"]) and (municipio or setor):
        gap = r["sal_med"] / sc["sal_med"] - 1
        out.append(dict(tipo="atencao" if gap < -0.03 else "ok", ic="💰",
                        tx=f"Salário mediano de entrada de <b>{fmt_rs(r['sal_med'])}</b>, "
                           f"{'abaixo' if gap < 0 else 'acima'} da mediana de SC ({fmt_rs(sc['sal_med'])}) em "
                           f"{abs(gap) * 100:.0f}%.", nota="Salários válidos: R$ 800 a R$ 60 mil, jornada ≥ 30h"))

    # 5. Família de ocupações (IA) que mais perde gente
    dd = ind[~ind["admissao"]]
    fam = dd.groupby("macrofamilia", observed=True)["pedido"].agg(["mean", "size"])
    fam = fam[fam["size"] >= (MIN_MOV // 2)].sort_values("mean", ascending=False)
    if len(fam):
        out.append(dict(tipo="atencao", ic="🧠", tx=f"Família de ocupações (IA) que mais perde gente: "
                        f"<b>{fam.index[0]}</b>, com {fmt_pct(fam['mean'].iloc[0])} das saídas a pedido.",
                        nota="16 macrofamílias criadas por IA a partir de 1.467 CBOs"))

    # 6. Escolaridade
    sup = ind.loc[ind["admissao"], "graudeinstrução"].isin(ESC_SUPERIOR).mean()
    out.append(dict(tipo="info", ic="🎓", tx=f"Só <b>{fmt_pct(sup, 1)}</b> dos admitidos têm ensino superior: a "
                    "demanda é operacional, e os sinais de pressão aparecem mais na retenção do que na falta de diploma.", nota="Grau de instrução 9 a 11 e 80"))

    # 7. Pior mês
    mm = mensal(ind)
    pior = mm.loc[mm["saldo"].idxmin()]
    out.append(dict(tipo="info", ic="🗓️", tx=f"Pior mês: <b>{pior['mes']}</b> ({fmt_sinal(pior['saldo'])} vagas).",
                    nota="Dezembro concentra fim de contratos temporários e férias coletivas"))
    return out
