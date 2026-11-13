"""
Raio-X do Mercado de Trabalho Industrial de SC: painel analítico da FIESC.

Núcleo (só as bases do desafio: Novo CAGED, municípios e dicionário; IA para as CBOs):
  Visão geral · Comparar territórios · Polos e diagnóstico · Renda e escolaridade · Macrofamílias (IA) ·
  Acionamento de parceiros · Dados e método
Bônus (filtro "fontes externas", desligado por padrão): mapa e regiões geográficas do IBGE.

Rodar:  streamlit run dashboard/app.py
"""
import sys
from pathlib import Path

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parent))
import acionamento  # noqa: E402
import territorio as terr  # noqa: E402
import tema  # noqa: E402  (registra o template do Plotly)
from dados import MIN_MOV, carregar, fmt_int, fmt_pct, fmt_rs, fmt_sinal, mensal, resumo  # noqa: E402
from insights import gerar  # noqa: E402
from tema import AZUL, AZUL_CLARO, LARANJA, ROXO, TEXTO, TEXTO_2, VERDE, VERMELHO  # noqa: E402

st.set_page_config(page_title="Raio-X Industrial SC · FIESC", page_icon="🔎", layout="wide",
                   initial_sidebar_state="collapsed")
st.markdown(tema.CSS, unsafe_allow_html=True)

CFG = {"displayModeBar": False}
COR_DIAG = {"Apagão de mão de obra": VERMELHO, "Expansão sob pressão": LARANJA, "Expansão acelerada": AZUL,
            "Retração": ROXO, "Estável": "#94A3B8"}
COR_PARC = {"UniSENAI": VERDE, "Awtra": ROXO, "Way2": LARANJA, "Empresas do polo": VERMELHO,
            "Monitorar": "#64748B"}


@st.cache_data(show_spinner=False)
def acoes():
    d_ = carregar()
    return acionamento.calcular(d_["ind"], d_["rs"])


d = carregar()
IND, RS = d["ind"], d["rs"]
AC = acoes()
SC = resumo(IND)


def plot(fig, altura):
    fig.update_layout(height=altura)
    st.plotly_chart(fig, config=CFG, width="stretch")


def kpi(col, rotulo, valor, sub, cor=TEXTO):
    col.markdown(f'<div class="kpi" style="--c:{cor}"><div class="rot">{rotulo}</div><div class="val">{valor}</div>'
                 f'<div class="sub">{sub}</div></div>', unsafe_allow_html=True)


def chip(txt, cor):
    return (f"<span style='background:{cor};color:white;font-weight:800;font-size:14px;padding:4px 12px;"
            f"border-radius:999px;white-space:nowrap'>{txt}</span>")


def rotulo_polo(df):
    if df.empty:
        return df.assign(rot=[])
    return df.assign(rot=df["setor"] + " · " + df["municipio_nome"])


def barras(df, valor, cor, titulo, fmt, faixa_max=None, altura=320):
    df = df.iloc[::-1]
    cores = cor if isinstance(cor, list) else [cor] * len(df)
    if isinstance(cor, list):
        cores = cores[::-1]
    fig = go.Figure(go.Bar(x=df[valor], y=df["rot"], orientation="h", marker_color=cores,
                           text=[fmt(v) for v in df[valor]], textposition="outside", cliponaxis=False,
                           textfont=dict(size=16, color=TEXTO), hovertemplate="%{y}: %{text}<extra></extra>"))
    fig.update_layout(title=titulo, xaxis=dict(visible=False, range=[0, faixa_max or df[valor].max() * 1.28]),
                      yaxis=dict(showgrid=False, tickfont=dict(size=15, color=TEXTO)), bargap=0.28,
                      margin=dict(l=10, r=30, t=56, b=10))
    plot(fig, altura)


# ============================== Cabeçalho e filtros ==============================
st.markdown("<div class='topo'><div class='marca'>🔎 Raio-X <span>Industrial SC</span></div>"
            "<div class='sub'>Painel de inteligência de mão de obra · FIESC · Novo CAGED set/2025 a ago/2026</div>"
            "</div>", unsafe_allow_html=True)
f1, f2, f3 = st.columns([1.2, 1.2, 1.6])
MUNS = ["Santa Catarina (todos)"] + d["municipios_ind"]
escolha = f1.selectbox("Município", MUNS, help="Municípios com 300+ movimentações industriais no período")
MUN = None if escolha.startswith("Santa Catarina") else escolha
SETORES = ["Todos os setores"] + sorted(IND["setor"].dropna().unique())
escolha_setor = f2.selectbox("Setor industrial (CNAE)", SETORES)
SET = None if escolha_setor.startswith("Todos") else escolha_setor
with f3:
    st.markdown("<div style='height:30px'></div>", unsafe_allow_html=True)
    BONUS = st.toggle("➕ Bônus: incluir fontes externas (IBGE)", value=False, disabled=not d["externo"],
                      help="Desligado = só as bases fornecidas pelo desafio. Ligado = acrescenta mapa e regiões "
                           "geográficas do IBGE, sinalizados como fonte externa.")

F = IND
RSF, ACF = RS, AC
if MUN:
    F = F[F["municipio_nome"] == MUN]
    RSF = RSF[RSF["municipio_nome"] == MUN]
    ACF = ACF[ACF["municipio_nome"] == MUN]
if SET:
    F = F[F["setor"] == SET]
    RSF = RSF[RSF["setor"] == SET]
    ACF = ACF[ACF["setor"] == SET]
R = resumo(F)
POP = (d["municipios"]["pop_estimada_2026"].sum() if MUN is None else
       d["municipios"].loc[d["municipios"]["municipio_nome"] == MUN, "pop_estimada_2026"].sum())
ROBF = RSF[RSF["robusto"]]

NOMES_ABAS = ["Visão geral", "Comparar territórios", "Polos e diagnóstico", "Renda e escolaridade",
              "Macrofamílias (IA)", "Acionamento de parceiros", "Dados e método"]
abas = st.tabs(NOMES_ABAS + (["➕ Bônus: fontes externas"] if BONUS else []))


def selo_externo(txt="Fonte externa (IBGE): fora das bases do desafio"):
    st.markdown(f"<div style='display:inline-block;background:#FEF3C7;color:#92400E;border:2px solid #F59E0B;"
                f"font-weight:800;font-size:14px;padding:4px 12px;border-radius:999px;margin:6px 0'>➕ {txt}</div>",
                unsafe_allow_html=True)


# ============================== 1. Visão geral ==============================
with abas[0]:
    k = st.columns(5)
    kpi(k[0], "Saldo de vagas", fmt_sinal(R["saldo"]), f"{fmt_sinal(round(R['saldo'] / POP * 10_000))} por 10 mil hab.",
        AZUL if R["saldo"] >= 0 else VERMELHO)
    kpi(k[1], "Movimentações", fmt_int(R["mov"]),
        f"{fmt_int(R['mov'] / R['saldo'])} por vaga criada" if R["saldo"] > 0 else "saldo negativo no recorte")
    kpi(k[2], "Saídas a pedido", fmt_pct(R["pct_pedido"]), f"{fmt_int(R['pedidos'])} pedidos de demissão", VERMELHO)
    kpi(k[3], "Salário de entrada", fmt_rs(R["sal_med"]), "mediana das admissões")
    kpi(k[4], "Polos em alerta", str(len(ROBF)), f"{(ACF['parceiro'] != 'Monitorar').sum()} com acionamento recomendado",
        LARANJA)

    ins = gerar(d, MUN, SET)
    cores_ins = {"alerta": VERMELHO, "ok": AZUL, "atencao": LARANJA, "info": AZUL}
    st.write("")
    for i in ins[:3]:
        st.markdown(f"<div class='insight' style='--c:{cores_ins[i['tipo']]}'>{i['ic']} {i['tx']}</div>",
                    unsafe_allow_html=True)

    c1, c2 = st.columns([7, 5])
    with c1:
        if not (BONUS and d["externo"]):
            g = F.groupby("municipio_nome", observed=True)["admissao"].agg(adm="sum", mov="size")
            g["saldo"] = 2 * g["adm"] - g["mov"]
            g["pct"] = F[~F["admissao"]].groupby("municipio_nome", observed=True)["pedido"].mean()
            g = g.reset_index().rename(columns={"municipio_nome": "rot"})
            cresce = g.nlargest(8, "saldo")
            cresce = cresce[cresce["saldo"] > 0]
            if len(cresce):
                barras(cresce, "saldo", AZUL, "📈 Municípios que mais criam vagas na indústria", fmt_sinal, altura=330)
            ped_alto = g[g["mov"] >= (1000 if not SET else 200)].nlargest(8, "pct")
            if len(ped_alto):
                barras(ped_alto, "pct", VERMELHO, "🚪 Municípios com mais saídas a pedido (1.000+ movimentações)",
                       lambda v: fmt_pct(v), 0.95, 330)
    if BONUS and d["externo"]:
      with c1:
        selo_externo("Mapa: malha municipal do IBGE (fonte externa)")
        modo = st.radio("Cor do mapa", ["% de saídas a pedido", "Saldo por 10 mil habitantes"], horizontal=True,
                        label_visibility="collapsed")
        base = F.groupby("cod_ibge")["admissao"].agg(adm="sum", mov="size")
        ped = F[~F["admissao"]].groupby("cod_ibge")["pedido"].mean().rename("pct")
        mun = d["ind_municipio"][["cod_ibge", "municipio_nome", "lat", "lon", "populacao"]].merge(
            base.join(ped), left_on="cod_ibge", right_index=True)
        mun = mun[(mun["mov"] >= (100 if not SET else 30))].dropna(subset=["lat"])
        mun["saldo"] = 2 * mun["adm"] - mun["mov"]
        mun["s10k"] = mun["saldo"] / mun["populacao"] * 10_000
        mun["raio"] = np.sqrt(mun["mov"]) / np.sqrt(mun["mov"].max() if len(mun) else 1) * 50 + 6
        mun = mun.sort_values("mov", ascending=False)
        ids = [ft["properties"]["id"] for ft in d["geo"]["features"]]
        destaque = (set(d["municipios"].loc[d["municipios"]["municipio_nome"] == MUN, "cod_ibge"].astype(str))
                    if MUN else set(ids))
        fig = go.Figure(go.Choroplethmap(
            geojson=d["geo"], locations=ids, z=[1 if i in destaque else 0 for i in ids], featureidkey="properties.id",
            colorscale=[[0, "#F1F5F9"], [1, AZUL_CLARO]], zmin=0, zmax=1, showscale=False,
            marker_line_color="white", marker_line_width=0.8, hoverinfo="skip"))
        if modo.startswith("%"):
            cor = dict(color=mun["pct"] * 100, colorscale=tema.ESCALA_PEDIDO, cmin=35, cmax=72,
                       colorbar=dict(title=dict(text="%"), ticksuffix="%", thickness=14, len=0.75))
        else:
            cor = dict(color=mun["s10k"], colorscale=tema.ESCALA_SALDO, cmin=-150, cmax=150,
                       colorbar=dict(title=dict(text="por 10 mil"), thickness=14, len=0.75))
        fig.add_trace(go.Scattermap(
            lat=mun["lat"], lon=mun["lon"], mode="markers", marker=dict(size=mun["raio"], opacity=0.9, **cor),
            text=mun["municipio_nome"],
            customdata=np.stack([mun["mov"], mun["saldo"], mun["pct"] * 100, mun["s10k"]], axis=1),
            hovertemplate="<b>%{text}</b><br>Movimentações: %{customdata[0]:,.0f}<br>Saldo: %{customdata[1]:,.0f}"
                          " (%{customdata[3]:+.0f} por 10 mil hab.)<br>Saídas a pedido: %{customdata[2]:.0f}%"
                          "<extra></extra>"))
        fig.update_layout(title=f"Municípios: tamanho = movimentações · cor = {modo.lower()}",
                          map=dict(style="white-bg", center=dict(lat=-27.3, lon=-51.05), zoom=6.0),
                          margin=dict(l=0, r=40, t=56, b=0))
        plot(fig, 600)
    with c2:
        st.markdown(f"<div style='font-size:19px;font-weight:900;color:{TEXTO};margin:6px 0 10px'>"
                    "🎯 Prioridades da FIESC</div>", unsafe_allow_html=True)
        top = ACF[ACF["parceiro"] != "Monitorar"].head(6)
        if top.empty:
            st.info("Nenhum polo com acionamento recomendado neste recorte.")
        for p in top.itertuples():
            cor_d = COR_DIAG[p.diagnostico]
            st.markdown(
                f"<div class='insight' style='--c:{cor_d};background:white;border:2px solid #DBE4F0;"
                f"border-left:6px solid {cor_d}'><b>{p.setor} · {p.municipio_nome}</b>"
                f"<br><span style='color:{cor_d};font-weight:800'>{p.diagnostico}</span> · {p.impacto_txt}"
                f"<div style='margin-top:8px'>{chip(p.parceiro, COR_PARC[p.parceiro])} "
                f"{chip(p.secundario, COR_PARC['Way2']) if p.secundario else ''}</div></div>",
                unsafe_allow_html=True)

    st.write("")
    m = mensal(F)
    fig = go.Figure(go.Bar(x=m["mes"], y=m["saldo"], marker_color=[AZUL if v >= 0 else VERMELHO for v in m["saldo"]],
                           text=[fmt_sinal(v) for v in m["saldo"]], textposition="outside", cliponaxis=False,
                           textfont=dict(size=14, color=TEXTO),
                           customdata=np.stack([m["adm"], m["desl"]], axis=1),
                           hovertemplate="%{x}<br>Saldo: %{y:,.0f}<br>Admissões: %{customdata[0]:,.0f}<br>"
                                         "Desligamentos: %{customdata[1]:,.0f}<extra></extra>"))
    fig.update_layout(title="Saldo mensal de vagas (admissões − desligamentos)",
                      yaxis=dict(title="Saldo", zeroline=True, zerolinecolor="#64748B"),
                      xaxis=dict(tickfont=dict(size=14, color=TEXTO)))
    plot(fig, 340)


# ============================== 2. Comparar territórios ==============================
COR_TERR = [AZUL, "#7C3AED", "#F59E0B"]
ROTULO_TERR = ["Referência", "Comparação 1", "Comparação 2"]


@st.cache_data(show_spinner=False)
def base_territorio(nivel):
    d_ = carregar()
    return terr.base(d_["ind"], d_["municipios"], nivel)


def badge(texto, nota, destaque_cor=None):
    nome, cor = terr.faixa(nota)
    borda = f"3px solid {destaque_cor}" if destaque_cor else f"2px solid {cor}"
    fundo = {"baixo": "#F1F5F9", "médio": "#E2E8F0", "bom": "#FEF3C7", "muito bom": "#D1FAE5"}[nome]
    tom = {"baixo": "#475569", "médio": "#1E293B", "bom": "#92400E", "muito bom": "#065F46"}[nome]
    return (f"<span style='display:inline-block;flex:0 0 auto;white-space:nowrap;min-width:92px;text-align:center;"
            f"font-weight:800;font-size:15px;line-height:1.4;"
            f"padding:3px 10px;border-radius:999px;border:{borda};background:{fundo};color:{tom}'>{texto}</span>")


with abas[1]:
    c = st.columns([1.1, 1.3, 1.3, 1.3, 1.1])
    nivel = c[0].radio("Tipo de comparação", ["Município"] + (["Região imediata ➕"] if BONUS else []),
                       horizontal=False)
    nivel = "Região imediata" if nivel.startswith("Região") else "Município"
    if nivel != "Município":
        selo_externo("Regiões imediatas do IBGE (fonte externa)")
    bt = base_territorio(nivel)
    nomes = list(bt["nome"])
    padrao = ["Joinville", "Blumenau", "Chapecó"]
    idx = [nomes.index(n) if n in nomes else i for i, n in enumerate(padrao)]
    ref = c[1].selectbox("Território de referência", nomes, index=idx[0])
    comp1 = c[2].selectbox("Comparar com", ["—"] + nomes, index=idx[1] + 1)
    comp2 = c[3].selectbox("Comparar com ", ["—"] + nomes, index=idx[2] + 1)
    valores = c[4].radio("Valores", ["Reais", "Notas (0–20)"])
    sel = [n for n in [ref, comp1, comp2] if n != "—"]
    sel = list(dict.fromkeys(sel))
    linhas_t = [bt[bt["nome"] == n].iloc[0] for n in sel]

    cols = st.columns(len(linhas_t))
    for i, (col, lt) in enumerate(zip(cols, linhas_t)):
        pct = lt["nota_geral"] / 20 * 100
        col.markdown(
            f"<div style='background:linear-gradient(120deg,{COR_TERR[i]},{COR_TERR[i]}CC);border-radius:18px;"
            f"padding:18px 22px;color:white;display:flex;justify-content:space-between;align-items:center'>"
            f"<div><div style='font-size:24px;font-weight:900'>{lt['nome']}</div>"
            f"<div style='font-size:15px;opacity:.95'>{ROTULO_TERR[i]} · {fmt_int(lt['pop'])} hab.</div></div>"
            f"<div style='background:rgba(15,23,42,.25);border-radius:14px;padding:10px 16px;min-width:150px'>"
            f"<div style='font-size:13px'>Nota geral</div><div style='font-size:32px;font-weight:900'>"
            f"{terr.formatar(lt['nota_geral'], 'dec1')}</div><div style='height:6px;background:rgba(255,255,255,.35);"
            f"border-radius:4px'><div style='width:{pct:.0f}%;height:6px;background:white;border-radius:4px'></div>"
            f"</div></div></div>", unsafe_allow_html=True)

    leg = " ".join(badge(f"{lo}–{hi}: {nome}", lo) for lo, hi, nome, _ in terr.FAIXAS)
    st.markdown(f"<div style='margin:14px 0 6px;font-size:15px;color:{TEXTO_2}'>Qualificação das notas: {leg}</div>",
                unsafe_allow_html=True)
    visao = st.radio("Visão", ["Síntese", "Indicadores"], horizontal=True, label_visibility="collapsed")

    if visao == "Indicadores":
        eixo = st.radio("Eixo", terr.EIXOS, horizontal=True, label_visibility="collapsed")
        inds = [x for x in terr.INDICADORES if x[2] == eixo]
        cols = st.columns(len(linhas_t))
        for i, (col, lt) in enumerate(zip(cols, linhas_t)):
            itens = ""
            for colname, nome, _, _, fmt in inds:
                nota = lt[f"n_{colname}"]
                melhor = len(linhas_t) > 1 and nota == max(x[f"n_{colname}"] for x in linhas_t)
                txt = terr.formatar(lt[colname], fmt) if valores == "Reais" else f"{nota:.0f}"
                itens += (f"<div style='display:flex;justify-content:space-between;align-items:center;padding:10px 0;"
                          f"border-bottom:1px solid #EDF2F7;gap:10px'><span style='font-size:16px;color:{TEXTO}'>{nome}</span>"
                          f"{badge(txt, nota, COR_TERR[i] if melhor else None)}</div>")
            col.markdown(
                f"<div style='border:2px solid #DBE4F0;border-radius:18px;padding:16px 20px;background:white'>"
                f"<div style='display:flex;justify-content:space-between;border-bottom:2px solid #DBE4F0;"
                f"padding-bottom:8px'><b style='font-size:19px;color:{TEXTO}'>"
                f"<span style='color:{COR_TERR[i]}'>●</span> {eixo}</b>"
                f"<span style='color:{TEXTO_2}'>nota do eixo: <b>{terr.formatar(lt[f'eixo_{eixo}'], 'dec1')}</b></span></div>"
                f"{itens}</div>", unsafe_allow_html=True)
        st.markdown(f"<div class='nota'>Borda colorida = melhor nota entre os territórios comparados. Notas de 0 a 20 = "
                    f"posição do território entre os {len(bt)} comparáveis "
                    f"({'municípios' if nivel == 'Município' else 'regiões imediatas'} com 300+ movimentações "
                    "industriais).</div>", unsafe_allow_html=True)
    else:
        c1, c2 = st.columns([5, 7])
        with c1:
            fig = go.Figure()
            for i, lt in enumerate(linhas_t):
                vals = [lt[f"eixo_{e}"] for e in terr.EIXOS]
                rgba = "rgba({},{},{},0.14)".format(*(int(COR_TERR[i][j:j + 2], 16) for j in (1, 3, 5)))
                fig.add_trace(go.Scatterpolar(r=vals + vals[:1], theta=terr.EIXOS + terr.EIXOS[:1], name=lt["nome"],
                                              fill="toself", line=dict(color=COR_TERR[i], width=4),
                                              fillcolor=rgba, marker=dict(size=9),
                                              hovertemplate="%{theta}: %{r:.1f}<extra>" + lt["nome"] + "</extra>"))
            fig.update_layout(title="Notas médias por eixo (0–20)",
                              polar=dict(radialaxis=dict(range=[0, 20], tickvals=[5, 10, 15, 20],
                                                         tickfont=dict(size=12, color=TEXTO_2), gridcolor="#E2E8F0"),
                                         angularaxis=dict(tickfont=dict(size=15, color=TEXTO), gridcolor="#E2E8F0",
                                                          rotation=90, direction="clockwise"),
                                         bgcolor="white"),
                              legend=dict(orientation="h", y=-0.08, x=0.5, xanchor="center"),
                              margin=dict(l=110, r=110, t=70, b=50))
            plot(fig, 540)
        with c2:
            for i, lt in enumerate(linhas_t):
                mel, pio = terr.melhores_piores(lt, 3)
                mel_html = "".join(f"<div style='display:flex;justify-content:space-between;align-items:center;"
                                   f"gap:10px;padding:4px 0'>"
                                   f"<span>{n}</span>{badge(f'{v:.0f}', v)}</div>" for n, v in mel)
                pio_html = "".join(f"<div style='display:flex;justify-content:space-between;align-items:center;"
                                   f"gap:10px;padding:4px 0'>"
                                   f"<span>{n}</span>{badge(f'{v:.0f}', v)}</div>" for n, v in pio)
                if nivel == "Município":
                    ac_t = AC[AC["municipio_nome"] == lt["nome"]]
                else:
                    muns_reg = d["municipios"].loc[d["municipios"]["regiao_imediata"] == lt["nome"], "municipio_nome"]
                    ac_t = AC[AC["municipio_nome"].isin(muns_reg)]
                st.markdown(
                    f"<div style='border:2px solid #DBE4F0;border-left:8px solid {COR_TERR[i]};border-radius:18px;"
                    f"padding:14px 18px;margin-bottom:12px;background:white;font-size:15px;color:{TEXTO}'>"
                    f"<div style='display:grid;grid-template-columns:1fr 1fr;gap:18px'>"
                    f"<div><b style='color:#059669;font-size:16px'>Melhores indicadores</b>{mel_html}</div>"
                    f"<div><b style='color:#D97706;font-size:16px'>Piores indicadores</b>{pio_html}</div></div>"
                    f"<div style='margin-top:10px;padding-top:10px;border-top:1px solid #EDF2F7;font-size:16px;"
                    f"line-height:1.5'>🧭 <b>Leitura do território:</b> {terr.leitura(lt, ac_t)}</div></div>",
                    unsafe_allow_html=True)

# ============================== 3. Polos e diagnóstico ==============================
with abas[2]:
    st.markdown("<div class='titulo'>Diagnóstico por polo (município × setor)</div>"
                "<div class='lead'><b>Índice de Pressão</b> = sinais de apagão (saídas a pedido, reposição e prêmio "
                "salarial). <b>Índice de Expansão</b> = saldo por 10 mil habitantes. Acima de 0,5 = alerta. "
                "Só polos com 300+ movimentações.</div>", unsafe_allow_html=True)
    q = RSF[RSF["movimentacoes"] >= MIN_MOV].copy()
    c1, c2 = st.columns([3, 2])
    with c1:
        q["x"] = q["indice_expansao"].clip(-3, 6.5)
        q["y"] = q["indice_pressao"].clip(-2.5, 3)
        q["tam"] = np.sqrt(q["movimentacoes"]) / np.sqrt(max(q["movimentacoes"].max(), 1)) * 44 + 7
        fig = go.Figure()
        for x0, x1, y0, y1, cor, txt, xt, anc in [
                (-3.3, 0.5, 0.5, 3.3, "rgba(239,68,68,0.08)", "APAGÃO", -3.1, "left"),
                (0.5, 6.9, 0.5, 3.3, "rgba(249,115,22,0.10)", "EXPANSÃO SOB PRESSÃO", 6.7, "right"),
                (0.5, 6.9, -2.8, 0.5, "rgba(37,99,235,0.07)", "EXPANSÃO ACELERADA", 6.7, "right")]:
            fig.add_shape(type="rect", x0=x0, x1=x1, y0=y0, y1=y1, fillcolor=cor, line_width=0, layer="below")
            fig.add_annotation(x=xt, y=3.12 if y0 > 0 else -2.6, text=f"<b>{txt}</b>", showarrow=False,
                               xanchor=anc, font=dict(size=13, color=TEXTO_2))
        for diag in ["Estável", "Retração", "Expansão acelerada", "Expansão sob pressão", "Apagão de mão de obra"]:
            g = q[q["diagnostico"] == diag]
            if g.empty:
                continue
            fig.add_scatter(x=g["x"], y=g["y"], mode="markers", name=diag,
                            marker=dict(size=g["tam"], color=COR_DIAG[diag], opacity=0.85,
                                        line=dict(color="white", width=1.5)),
                            text=g["setor"] + " · " + g["municipio_nome"],
                            customdata=np.stack([g["pct_pedido_demissao"] * 100, g["saldo"]], axis=1),
                            hovertemplate="<b>%{text}</b><br>Saídas a pedido: %{customdata[0]:.0f}%<br>"
                                          "Saldo: %{customdata[1]:,.0f}<extra></extra>")
        fig.add_hline(y=0.5, line=dict(color="#64748B", dash="dot"))
        fig.add_vline(x=0.5, line=dict(color="#64748B", dash="dot"))
        fig.update_layout(title="Matriz de diagnóstico (bolha = movimentações)",
                          xaxis=dict(title="Índice de Expansão →", range=[-3.3, 6.9], zeroline=False),
                          yaxis=dict(title="Índice de Pressão →", range=[-2.8, 3.3], zeroline=False),
                          legend=dict(orientation="h", y=-0.16, x=0))
        plot(fig, 560)
    with c2:
        cont = q["diagnostico"].value_counts().reindex(list(COR_DIAG)).fillna(0)
        dfc = pd.DataFrame({"rot": cont.index, "n": cont.values})
        barras(dfc, "n", [COR_DIAG[i] for i in dfc["rot"]], "Quantos polos em cada diagnóstico",
               lambda v: fmt_int(v), altura=300)
        st.markdown(f"<div class='insight' style='--c:{AZUL}'>🛡️ <b>Robustez:</b> cada alerta foi recalculado em "
                    f"36 calibrações do índice. <b>{int(RSF['robusto'].sum())}</b> dos "
                    f"{int(q['diagnostico'].isin(acionamento.ALERTAS).sum())} alertas deste recorte se mantêm em pelo "
                    "menos 80% delas e são tratados como prioridade.</div>", unsafe_allow_html=True)

    tab = q.sort_values(["robusto", "indice_pressao"], ascending=False)[
        ["setor", "municipio_nome", "diagnostico", "robusto", "movimentacoes", "saldo", "saldo_10k_hab",
         "pct_pedido_demissao", "indice_reposicao", "salario_mediano_adm", "pct_superior_adm"]]
    st.dataframe(
        tab.rename(columns={"setor": "Setor", "municipio_nome": "Município", "diagnostico": "Diagnóstico",
                            "robusto": "Alerta robusto", "movimentacoes": "Movimentações", "saldo": "Saldo",
                            "saldo_10k_hab": "Saldo/10 mil hab.", "pct_pedido_demissao": "Saídas a pedido",
                            "indice_reposicao": "Reposição", "salario_mediano_adm": "Salário entrada",
                            "pct_superior_adm": "Admitidos c/ superior"}),
        hide_index=True, width="stretch", height=420,
        column_config={"Saídas a pedido": st.column_config.ProgressColumn(format="percent", min_value=0, max_value=1),
                       "Admitidos c/ superior": st.column_config.NumberColumn(format="percent"),
                       "Movimentações": st.column_config.NumberColumn(format="localized"),
                       "Saldo": st.column_config.NumberColumn(format="localized"),
                       "Saldo/10 mil hab.": st.column_config.NumberColumn(format="%.1f"),
                       "Reposição": st.column_config.NumberColumn(format="%.2f"),
                       "Salário entrada": st.column_config.NumberColumn(format="R$ %d")})

# ============================== 3. Renda e escolaridade ==============================
with abas[3]:
    st.markdown("<div class='titulo'>Renda e escolaridade explicam o gargalo?</div>"
                "<div class='lead'>391 mil desligamentos analisados: a chance de pedir demissão cai com o salário e "
                "quase não muda com a escolaridade.</div>", unsafe_allow_html=True)
    ps = d["est_pedido_salario_escolaridade"]
    c1, c2 = st.columns(2)
    with c1:
        qs = ps[(ps["faixa_esc"] == "Todas") & (ps["quintil_sal"] != "Todas")]
        rot = ["até R$ 2 mil", "R$ 2,1 mil", "R$ 2,3 mil", "R$ 2,6 mil", "R$ 3,6 mil+"]
        fig = go.Figure(go.Bar(x=rot, y=qs["pct_pedido"] * 100,
                               marker_color=[VERMELHO, VERMELHO, LARANJA, "#60A5FA", AZUL],
                               text=[f"{v * 100:.0f}%" for v in qs["pct_pedido"]], textposition="outside",
                               textfont=dict(size=18, color=TEXTO), cliponaxis=False))
        fig.update_layout(title="💰 % de saídas a pedido por faixa salarial", yaxis=dict(visible=False, range=[0, 70]),
                          xaxis=dict(tickfont=dict(size=15, color=TEXTO)))
        plot(fig, 360)
    with c2:
        es = ps[(ps["quintil_sal"] == "Todas") & (ps["faixa_esc"] != "Todas")]
        fig = go.Figure(go.Bar(x=es["faixa_esc"].str.replace("Superior incompleto", "Sup. incompleto"),
                               y=es["pct_pedido"] * 100, marker_color=ROXO,
                               text=[f"{v * 100:.0f}%" for v in es["pct_pedido"]], textposition="outside",
                               textfont=dict(size=18, color=TEXTO), cliponaxis=False))
        fig.update_layout(title="🎓 % de saídas a pedido por escolaridade", yaxis=dict(visible=False, range=[0, 70]),
                          xaxis=dict(tickfont=dict(size=15, color=TEXTO)))
        plot(fig, 360)
    c1, c2 = st.columns([3, 2])
    with c1:
        sc_ = RSF[(RSF["movimentacoes"] >= MIN_MOV) & RSF["salario_mediano_adm"].between(1500, 4500)]
        fig = go.Figure()
        for robusto, cor, nome in [(False, "#60A5FA", "Polos"), (True, VERMELHO, "Polos em alerta robusto")]:
            g = sc_[sc_["robusto"] == robusto]
            fig.add_scatter(x=g["salario_mediano_adm"], y=g["pct_pedido_demissao"] * 100, mode="markers", name=nome,
                            marker=dict(size=np.sqrt(g["movimentacoes"]) / 7 + 6, color=cor, opacity=0.85,
                                        line=dict(color="white", width=1.5)),
                            text=g["setor"] + " · " + g["municipio_nome"],
                            hovertemplate="<b>%{text}</b><br>Salário: R$ %{x:,.0f}<br>Saídas a pedido: %{y:.0f}%"
                                          "<extra></extra>")
        if len(sc_) > 5:
            a, b = np.polyfit(sc_["salario_mediano_adm"], sc_["pct_pedido_demissao"] * 100, 1)
            xs = np.linspace(sc_["salario_mediano_adm"].min(), sc_["salario_mediano_adm"].max(), 30)
            fig.add_scatter(x=xs, y=a * xs + b, mode="lines", name="Tendência",
                            line=dict(color=TEXTO, width=3, dash="dash"), hoverinfo="skip")
        rho = d["est_correlacoes"].query("nivel=='municipio_setor' and var_x=='salario_mediano_adm' and "
                                         "var_y=='pct_pedido_demissao'")["rho"].iloc[0]
        fig.update_layout(title=f"Salário de entrada × saídas a pedido por polo (ρ = {rho:.2f})".replace(".", ","),
                          xaxis=dict(title="Salário de entrada (R$)"), yaxis=dict(title="% saídas a pedido"),
                          legend=dict(orientation="h", y=-0.2, x=0))
        plot(fig, 440)
    with c2:
        lg = d["est_logit_pedido"]
        nomes = {"sal_rel_cbo": "+10% de salário vs. ocupação", "faixa_esc = Superior ou mais": "Ensino superior",
                 "faixa_esc = Médio": "Ensino médio", "faixa_idade = 14-24": "Jovem (14–24)",
                 "faixa_idade = 50+": "50 anos ou mais", "mulher": "Mulher"}
        lg = lg[lg["termo"].isin(nomes)].copy()
        lg["ef"] = (np.where(lg["termo"] == "sal_rel_cbo", lg["razao_chance_10pct"], lg["razao_chance"]) - 1) * 100
        lg = lg.assign(rot=lg["termo"].map(nomes)).sort_values("ef")
        fig = go.Figure(go.Bar(x=lg["ef"], y=lg["rot"], orientation="h",
                               marker_color=[AZUL if v < 0 else LARANJA for v in lg["ef"]],
                               text=[f"{v:+.0f}%".replace("-", "−") for v in lg["ef"]], textposition="outside",
                               textfont=dict(size=16, color=TEXTO), cliponaxis=False))
        fig.update_layout(title="Efeito na chance de pedir demissão (regressão)",
                          xaxis=dict(visible=False, range=[-40, 100]),
                          yaxis=dict(showgrid=False, tickfont=dict(size=15, color=TEXTO)))
        plot(fig, 440)

# ============================== 4. Macrofamílias (IA) ==============================
with abas[4]:
    st.markdown("<div class='titulo'>Famílias de ocupações agrupadas por IA</div>"
                "<div class='lead'>1.467 CBOs da indústria em 16 macrofamílias (LLM). Mostra se o gargalo está no "
                "chão de fábrica ou nas funções técnicas e de gestão.</div>", unsafe_allow_html=True)
    fam = F.groupby("macrofamilia", observed=True).agg(adm=("admissao", "sum"), mov=("admissao", "size"))
    fam["saldo"] = 2 * fam["adm"] - fam["mov"]
    fam["pct"] = F[~F["admissao"]].groupby("macrofamilia", observed=True)["pedido"].mean()
    fam["sal"] = F[F["admissao"] & F["salario_valido"]].groupby("macrofamilia", observed=True)["salario"].median()
    fam = fam[fam["adm"] >= (500 if not (MUN or SET) else 50)].reset_index()
    fam["rot"] = fam["macrofamilia"].str.replace(r" \(.*\)", "", regex=True)
    c1, c2 = st.columns(2)
    with c1:
        barras(fam.nlargest(8, "pct"), "pct", ROXO, "% de saídas a pedido (maiores)", lambda v: fmt_pct(v), 0.85, 420)
    with c2:
        sal = fam.nlargest(8, "pct")
        barras(sal, "sal", AZUL, "Salário de entrada dessas famílias", fmt_rs, altura=420)
    top_mun = IND.groupby("municipio_nome", observed=True).size().nlargest(8).index
    dd_ = IND[~IND["admissao"] & IND["municipio_nome"].isin(top_mun)]
    hm = dd_.groupby(["macrofamilia", "municipio_nome"], observed=True)["pedido"].agg(["mean", "size"]).reset_index()
    hm = hm[hm["size"] >= 150]
    piv = hm.pivot(index="macrofamilia", columns="municipio_nome", values="mean") * 100
    piv = piv[[m for m in top_mun if m in piv.columns]]
    piv = piv.loc[piv.mean(axis=1).sort_values().index]
    piv.index = piv.index.str.replace(r" \(.*\)", "", regex=True)
    fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale=tema.ESCALA_PEDIDO, zmin=25,
                               zmax=70, texttemplate="%{z:.0f}", textfont=dict(size=14), xgap=3, ygap=3,
                               hovertemplate="%{y} · %{x}: %{z:.0f}% a pedido<extra></extra>",
                               colorbar=dict(ticksuffix="%", thickness=14)))
    fig.update_layout(title="% de saídas a pedido: família de ocupações × 8 maiores municípios industriais",
                      xaxis=dict(showgrid=False, tickfont=dict(size=15, color=TEXTO)),
                      yaxis=dict(showgrid=False, tickfont=dict(size=14, color=TEXTO)))
    plot(fig, 560)

# ============================== 5. Acionamento de parceiros ==============================
with abas[5]:
    st.markdown("<div class='titulo'>Quem a FIESC aciona, onde e por quê</div>"
                "<div class='lead'>Cada polo recebe <b>um</b> parceiro principal, escolhido por regra a partir dos "
                "indicadores. Alertas frágeis e expansões pequenas ficam só em monitoramento.</div>",
                unsafe_allow_html=True)
    ativos = ACF[ACF["parceiro"] != "Monitorar"]
    regras = [
        ("Empresas do polo", "💰", "Alerta robusto e salário de entrada 3%+ abaixo da mediana do setor em SC",
         "Revisar o piso de entrada (via sindicato patronal)"),
        ("Awtra", "🛡️", "Alerta robusto com salário na média: o problema é integração e liderança",
         "Onboarding de compliance e segurança e formação de lideranças"),
        ("UniSENAI", "🎓", "Expansão acelerada com +200 vagas no ano",
         "Turmas curtas para a família de ocupações mais contratada"),
        ("Way2", "⚡", "Secundário: setor eletrointensivo crescendo +500 vagas",
         "Telemetria e eficiência energética na planta que cresce"),
    ]
    cols = st.columns(4)
    for col, (parc, ic, quando, oque) in zip(cols, regras):
        n = int((ativos["parceiro"] == parc).sum() + (ativos["secundario"] == parc).sum())
        col.markdown(f"<div class='parceiro' style='--c:{COR_PARC[parc]}'><div class='cab'><span>{ic}</span>"
                     f"<b>{parc}</b></div><div class='val' style='font-size:40px;font-weight:900;color:{COR_PARC[parc]}'>"
                     f"{n} polos</div><div class='rot'>Quando</div><p>{quando}</p><div class='rot'>O que faz</div>"
                     f"<p>{oque}</p></div>", unsafe_allow_html=True)

    st.write("")
    so = st.radio("Mostrar", ["Só polos com acionamento", "Todos os polos (inclui monitoramento)"], horizontal=True,
                  label_visibility="collapsed")
    lista = ativos if so.startswith("Só") else ACF
    linhas = ""
    for p in lista.itertuples():
        cor_d = COR_DIAG[p.diagnostico]
        sec = (f"<div style='margin-top:8px'>{chip('+ Way2', COR_PARC['Way2'])} "
               f"<span style='font-size:14px'>{p.secundario_porque}</span></div>") if p.secundario else ""
        linhas += (
            f"<tr><td><b>{p.setor}</b><br>{p.municipio_nome}</td>"
            f"<td><span style='color:{cor_d};font-weight:800'>{p.diagnostico}</span><br>{p.impacto_txt}"
            f"{'<br><b>alerta robusto</b>' if p.robusto else ''}</td>"
            f"<td>{chip(p.parceiro, COR_PARC[p.parceiro])}</td>"
            f"<td><b>Por quê:</b> {p.porque}<br><b>Ação:</b> {p.acao}{sec}</td>"
            f"<td style='color:{ROXO};font-weight:700'>{p.familia_ia}</td></tr>")
    estilo_td = 'style="padding:12px 10px;border-bottom:1px solid #E2E8F0;vertical-align:top"'
    st.markdown(f"""<table style="width:100%;border-collapse:collapse;font-size:16px;color:{TEXTO};line-height:1.45">
    <thead><tr style="text-align:left;border-bottom:3px solid #DBE4F0;font-size:15px">
    <th style="padding:10px;width:17%">Polo</th><th style="padding:10px;width:16%">Diagnóstico</th>
    <th style="padding:10px;width:12%">Acionar</th><th style="padding:10px">Justificativa (dados) e ação</th>
    <th style="padding:10px;width:15%">Família (IA)</th></tr></thead>
    <tbody>{linhas.replace('<td', '<td ' + estilo_td)}</tbody></table>""", unsafe_allow_html=True)
    if lista.empty:
        st.info("Nenhum polo neste recorte.")

# ============================== 6. Dados e método ==============================
with abas[6]:
    lg = d["log_limpeza"]
    ind_n = lg.loc[lg["etapa"].str.startswith("Indústria"), "linhas"].iloc[0]
    st.markdown("<div class='titulo'>Dados, validação e método</div>", unsafe_allow_html=True)
    st.markdown("<div class='fluxo'>" + "".join(
        f"<div class='passo'><div class='n'>{n}</div><div class='d'>{t}</div></div>" for n, t in [
            (fmt_int(lg["linhas"].iloc[0]), "registros do Novo CAGED SC (MOV)"),
            (fmt_int(ind_n), "movimentações da indústria (CNAE C) após limpeza"),
            ("295", "municípios da base fornecida, 100% casados com o CAGED"),
            ("1.467 → 16", "CBOs agrupadas por IA em macrofamílias"),
            ("36", "calibrações para validar cada alerta"),
            ("20", "testes automáticos")]) + "</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([3, 2])
    with c1:
        st.markdown(f"<div style='font-size:19px;font-weight:800;color:{TEXTO};margin:18px 0 8px'>"
                    "Validação de schema e domínios (dicionário oficial)</div>", unsafe_allow_html=True)
        val = pd.read_csv(Path(__file__).resolve().parents[1] / "data/processed/validacao_schema.csv")
        st.dataframe(val[["regra", "registros", "status", "detalhe"]].rename(
            columns={"regra": "Regra", "registros": "Registros", "status": "Status", "detalhe": "Tratamento"}),
            hide_index=True, width="stretch", height=430,
            column_config={"Registros": st.column_config.NumberColumn(format="localized")})
    with c2:
        st.markdown("""<div style="font-size:16px;color:#0F172A;line-height:1.6;margin-top:18px">

**Premissas**
- Janela: set/2025 a ago/2026. Só a base MOV foi fornecida; o filtro MOV × EXC está pronto em
  `backend/validacao.py` e roda se a base EXC for colocada em `raw/`.
- **Fontes do diagnóstico: só as 3 bases do desafio** (Novo CAGED MOV, municípios de SC e dicionário de dados),
  mais IA generativa para agrupar as CBOs. Território = município; polo = município × setor.
- Junção CAGED (6 dígitos) × base municipal (7 dígitos) por `cod_ibge // 10`; saldo por 10 mil hab. com a
  população estimada 2026 da própria base municipal.
- Índice de Pressão: média dos z-scores de % saídas a pedido, reposição e prêmio salarial ajustado por ocupação.
- IA: LLM classificou 177 subgrupos de CBO (prompt e resposta em `data/ia/`).
- Regras de acionamento em `dashboard/acionamento.py`.

**Limites**
- O CAGED mede fluxo, não vagas abertas: o apagão é inferido pela retenção e pelo salário.
- Associação não é causalidade.
- Sem fontes externas, o painel não usa mapa nem regiões geográficas. Eles ficam no filtro **Bônus**,
  sinalizados como fonte externa (IBGE).
</div>""", unsafe_allow_html=True)

# ============================== Bônus: fontes externas ==============================
if BONUS:
    with abas[7]:
        st.markdown("<div class='titulo'>➕ Bônus: o que muda ao cruzar com fontes externas</div>"
                    "<div class='lead'>Esta aba usa dados <b>fora das bases do desafio</b> e não entra no diagnóstico "
                    "principal. Serve para mostrar o potencial do Raio-X quando a FIESC conectar outras fontes.</div>",
                    unsafe_allow_html=True)
        selo_externo("Regiões geográficas imediatas e intermediárias do IBGE (2017) e malha municipal do IBGE")
        if "est_sensibilidade_pares_regiao" in d:
            rr = d["est_sensibilidade_pares_regiao"]
            rr = rr[rr["diagnostico"].isin(acionamento.ALERTAS) & (rr["estabilidade"] == "Alerta robusto")]
            rr = rotulo_polo(rr.rename(columns={"regiao_imediata": "municipio_nome"})).nlargest(8, "movimentacoes")
            c1, c2 = st.columns(2)
            with c1:
                barras(rr.sort_values("pct_pedido_demissao", ascending=False), "pct_pedido_demissao", VERMELHO,
                       "Polos em alerta robusto por região imediata (% saídas a pedido)", lambda v: fmt_pct(v), 0.95, 380)
            with c2:
                rmf = d["ind_regiao_macrofamilia"]
                rmf = rmf[rmf["movimentacoes"] >= MIN_MOV]
                piv = rmf.pivot(index="macrofamilia", columns="regiao_intermediaria",
                                values="pct_pedido_demissao") * 100
                piv = piv.loc[piv.mean(axis=1).sort_values().index]
                piv.index = piv.index.str.replace(r" \(.*\)", "", regex=True)
                fig = go.Figure(go.Heatmap(z=piv.values, x=piv.columns, y=piv.index, colorscale=tema.ESCALA_PEDIDO,
                                           zmin=25, zmax=70, texttemplate="%{z:.0f}", textfont=dict(size=12),
                                           xgap=2, ygap=2, colorbar=dict(ticksuffix="%", thickness=12)))
                fig.update_layout(title="Família (IA) × região intermediária: % a pedido",
                                  yaxis=dict(tickfont=dict(size=12, color=TEXTO)))
                plot(fig, 380)
        st.markdown(f"<div style='font-size:20px;font-weight:900;color:{TEXTO};margin:18px 0 10px'>"
                    "Novos insights possíveis com mais fontes</div>", unsafe_allow_html=True)
        ideias = [
            ("🗺️", "Mapa e regiões do IBGE", "Já disponível nesta aba e no mapa da visão geral: mostra os polos "
             "em contexto geográfico e permite comparar regiões imediatas."),
            ("📦", "RAIS (estoque de empregos)", "O CAGED mede fluxo. Com a RAIS dá para calcular taxa de rotatividade "
             "real (saídas ÷ estoque) e o tamanho de cada polo."),
            ("📝", "Vagas abertas (SINE e plataformas)", "Confirmaria o apagão de forma direta: vagas que ficam "
             "abertas por mais tempo nos polos em alerta."),
            ("🎓", "Matrículas do ensino técnico (INEP/SENAI)", "Compara quantos se formam por família de ocupações "
             "com quantos a indústria contrata, polo a polo."),
            ("⚡", "Consumo de energia industrial (Way2)", "Sinal antecipado de expansão: o consumo das plantas sobe "
             "antes das contratações aparecerem no CAGED."),
        ]
        cols = st.columns(len(ideias))
        for col, (ic, t, txt) in zip(cols, ideias):
            col.markdown(f"<div class='parceiro' style='--c:#F59E0B'><div class='cab'><span>{ic}</span>"
                         f"<b style='font-size:18px'>{t}</b></div><p style='margin-top:10px'>{txt}</p></div>",
                         unsafe_allow_html=True)
