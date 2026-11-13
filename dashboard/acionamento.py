"""
Motor de acionamento: para cada polo (município × setor) com diagnóstico de alerta ou expansão,
escolhe UM parceiro principal para a FIESC acionar (e, só quando o critério é forte, um secundário),
sempre com a justificativa tirada dos indicadores.

Regras (avaliadas nesta ordem):
  Polos em alerta (Apagão ou Expansão sob pressão)
    0. Alerta frágil (some em mais de 20% das 36 calibrações do índice)
         → sem acionamento: monitorar e confirmar no próximo trimestre.
    1. Salário de entrada ≥ 3% abaixo da mediana estadual do setor
         → Empresas do polo (via sindicato patronal): revisar piso de entrada.
           Evidência: +10% sobre a mediana da ocupação reduz ~6% a chance de pedido de demissão.
    2. Salário na média do setor, mas saídas a pedido acima da média de SC
         → Awtra: integração, compliance e formação de lideranças (o problema não é o piso).
  Polos em expansão acelerada
    3. Saldo de pelo menos 200 vagas
         → UniSENAI: formar para a família de ocupações que mais está sendo contratada.
    4. Saldo menor que 200 vagas
         → sem acionamento: apenas monitorar.
  Limite (foco da FIESC): no máximo 6 alertas robustos (os de mais saídas a pedido/ano) e 4 expansões
  (as de maior saldo) recebem parceiro. Os demais entram na fila de monitoramento, com o motivo.
  Secundário (só em expansão)
    5. Setor eletrointensivo com saldo de pelo menos 500 vagas
         → Way2: telemetria e eficiência energética para a planta que cresce.
"""
import numpy as np
import pandas as pd

ALERTAS = ["Apagão de mão de obra", "Expansão sob pressão"]
ELETROINTENSIVOS = {"Alimentos", "Bebidas", "Celulose e papel", "Químicos", "Borracha e plástico",
                    "Minerais não metálicos (cerâmica, vidro)", "Metalurgia", "Têxtil"}
PARCEIROS = ["UniSENAI", "Awtra", "Way2", "Empresas do polo"]


def _br(v: float) -> str:
    return f"{v:,.0f}".replace(",", ".")


LIMITE_ALERTAS, LIMITE_EXPANSAO = 6, 4


def calcular(ind: pd.DataFrame, rs: pd.DataFrame, min_mov: int = 300,
             limite_alertas: int | None = LIMITE_ALERTAS, limite_expansao: int | None = LIMITE_EXPANSAO) -> pd.DataFrame:
    sal_setor = ind[ind["admissao"] & ind["salario_valido"]].groupby("setor", observed=True)["salario"].median()
    dd = ind[~ind["admissao"]]
    pct_sc = dd["pedido"].mean()

    polos = rs[(rs["movimentacoes"] >= min_mov) &
               rs["diagnostico"].isin(ALERTAS + ["Expansão acelerada"])].copy()

    # Família de ocupações (IA) mais afetada: a que mais pede para sair (alertas) ou a mais contratada (expansão)
    chave = ["setor", "municipio_nome"]
    ped = (dd[dd["pedido"]].groupby(chave + ["macrofamilia"], observed=True).size()
           .reset_index(name="n").sort_values("n").drop_duplicates(chave, keep="last"))
    adm = (ind[ind["admissao"]].groupby(chave + ["macrofamilia"], observed=True).size()
           .reset_index(name="n").sort_values("n").drop_duplicates(chave, keep="last"))
    fam_ped = {(r.setor, r.municipio_nome): (r.macrofamilia, r.n) for r in ped.itertuples()}
    fam_adm = {(r.setor, r.municipio_nome): (r.macrofamilia, r.n) for r in adm.itertuples()}

    linhas = []
    for p in polos.itertuples():
        k = (p.setor, p.municipio_nome)
        mediana = sal_setor.get(p.setor, np.nan)
        gap = p.salario_mediano_adm / mediana - 1 if mediana and not np.isnan(p.salario_mediano_adm) else np.nan
        pedidos_ano = p.desligamentos * p.pct_pedido_demissao
        robusto = bool(getattr(p, "robusto", False))
        sec, sec_porque = "", ""
        if p.diagnostico in ALERTAS:
            fam, n_fam = fam_ped.get(k, ("—", 0))
            impacto, impacto_txt = pedidos_ano, f"{_br(pedidos_ano)} saídas a pedido/ano"
            if not robusto:
                parceiro = "Monitorar"
                cen = getattr(p, "pct_cenarios_alerta", np.nan)
                porque = (f"Alerta frágil: aparece em só {cen * 100:.0f}% das 36 calibrações do índice. "
                          "Confirmar no próximo trimestre antes de mobilizar parceiros.")
                acao = "Acompanhar no próximo trimestre."
                meta = "—"
            elif not np.isnan(gap) and gap <= -0.03:
                parceiro = "Empresas do polo"
                porque = (f"Salário de entrada de R$ {_br(p.salario_mediano_adm)}, {abs(gap) * 100:.0f}% abaixo da "
                          f"mediana do setor em SC (R$ {_br(mediana)}), e {p.pct_pedido_demissao * 100:.0f}% das "
                          "saídas são pedido do trabalhador.")
                acao = "Revisar o piso de entrada: +10% sobre a mediana da ocupação reduz ~6% a chance de pedido."
                meta = "Salário de entrada ≥ mediana do setor; −10% de pedidos"
            else:
                parceiro = "Awtra"
                porque = (f"O salário já está na média do setor (R$ {_br(p.salario_mediano_adm)}), mas "
                          f"{p.pct_pedido_demissao * 100:.0f}% das saídas são a pedido (SC: {pct_sc * 100:.0f}%). "
                          "O gargalo é integração e liderança, não piso.")
                acao = "Onboarding de compliance e segurança e formação de lideranças de linha."
                meta = "−10% de pedidos nos primeiros 6 meses de casa"
        else:
            fam, n_fam = fam_adm.get(k, ("—", 0))
            impacto, impacto_txt = p.saldo, f"+{_br(p.saldo)} vagas/ano"
            if p.saldo >= 200:
                parceiro = "UniSENAI"
                porque = (f"O polo criou +{_br(p.saldo)} vagas em 12 meses; a família mais contratada é {fam} "
                          f"({_br(n_fam)} admissões).")
                acao = f"Turmas curtas de {fam} com as empresas do polo, antes que a expansão vire falta de gente."
                meta = "Vagas preenchidas por formandos em 6 meses"
            else:
                parceiro = "Monitorar"
                porque = f"Expansão real, mas pequena (+{_br(p.saldo)} vagas): ainda não justifica acionar parceiro."
                acao = "Acompanhar no próximo trimestre."
                meta = "—"
            if p.setor in ELETROINTENSIVOS and p.saldo >= 500:
                sec = "Way2"
                sec_porque = (f"{p.setor} é eletrointensivo e o polo cresce +{_br(p.saldo)} vagas: a demanda de energia "
                              "sobe junto. Telemetria e eficiência energética reduzem o custo da expansão.")
        linhas.append(dict(
            setor=p.setor, cod_ibge=p.cod_ibge, municipio_nome=p.municipio_nome,
            diagnostico=p.diagnostico, robusto=robusto, movimentacoes=p.movimentacoes, saldo=p.saldo,
            pct_pedido=p.pct_pedido_demissao, salario=p.salario_mediano_adm, gap_salario=gap,
            familia_ia=fam, impacto=impacto, impacto_txt=impacto_txt, parceiro=parceiro, porque=porque,
            acao=acao, meta=meta, secundario=sec, secundario_porque=sec_porque))
    out = pd.DataFrame(linhas)
    # Prioridade da FIESC: alertas robustos primeiro, depois pelo tamanho do impacto
    out["ordem"] = np.select([out["robusto"], out["diagnostico"].isin(ALERTAS)], [0, 1], 2)
    out = out.sort_values(["ordem", "impacto"], ascending=[True, False]).reset_index(drop=True)
    # Foco: só os polos de maior impacto recebem parceiro; os demais vão para a fila de monitoramento
    for lim, eh_alerta in ((limite_alertas, True), (limite_expansao, False)):
        if lim is None:
            continue
        sel = (out["parceiro"] != "Monitorar") & (out["diagnostico"].isin(ALERTAS) == eh_alerta)
        fila = out.index[sel][lim:]
        tipo = "alertas robustos" if eh_alerta else "polos em expansão"
        out.loc[fila, "porque"] = (f"Indicaria {out.loc[fila, 'parceiro']}, mas está fora dos {lim} {tipo} de maior impacto "
                                   "em SC: entra na fila do próximo ciclo. " + out.loc[fila, "porque"])
        out.loc[fila, ["parceiro", "acao", "meta", "secundario", "secundario_porque"]] = [
            "Monitorar", "Fila do próximo ciclo (fora do top de impacto).", "—", "", ""]
    out["ordem2"] = (out["parceiro"] == "Monitorar").astype(int)
    out = out.sort_values(["ordem2", "ordem", "impacto"], ascending=[True, True, False])
    return out.drop(columns=["ordem", "ordem2"]).reset_index(drop=True)
