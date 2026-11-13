"""Identidade visual: base branca, azul na interface, cores vivas nos gráficos, letras grandes."""
import plotly.graph_objects as go
import plotly.io as pio

AZUL = "#2563EB"
AZUL_ESCURO = "#1E3A8A"
AZUL_CLARO = "#DBEAFE"
AZUL_FUNDO = "#EFF6FF"
TEXTO = "#0F172A"
TEXTO_2 = "#1E293B"
BORDA = "#DBE4F0"
VERMELHO = "#EF4444"
LARANJA = "#F97316"
AMARELO = "#FACC15"
VERDE = "#10B981"
ROXO = "#8B5CF6"
CIANO = "#06B6D4"

COR_PARCEIRO = {"FIESC": AZUL, "UniSENAI": VERDE, "Way2": LARANJA, "Awtra": ROXO, "Indústria": VERMELHO}

ESCALA_PEDIDO = [[0, "#FEF08A"], [0.35, "#FB923C"], [0.7, "#EF4444"], [1, "#991B1B"]]
ESCALA_SALDO = [[0, "#DC2626"], [0.5, "#F8FAFC"], [1, "#1D4ED8"]]

FONTE = "Inter, 'Segoe UI', system-ui, sans-serif"

pio.templates["raiox"] = go.layout.Template(layout=dict(
    font=dict(family=FONTE, color=TEXTO, size=15),
    title=dict(font=dict(color=TEXTO, size=18), x=0.01),
    paper_bgcolor="white",
    plot_bgcolor="white",
    separators=",.",
    colorway=[AZUL, LARANJA, VERDE, ROXO, VERMELHO, CIANO],
    xaxis=dict(gridcolor="#EDF2F7", zerolinecolor="#CBD5E1", linecolor="#CBD5E1", ticks="",
               tickfont=dict(size=14, color=TEXTO_2), title=dict(font=dict(size=15, color=TEXTO_2))),
    yaxis=dict(gridcolor="#EDF2F7", zerolinecolor="#CBD5E1", linecolor="#CBD5E1", ticks="",
               tickfont=dict(size=14, color=TEXTO_2), title=dict(font=dict(size=15, color=TEXTO_2))),
    hoverlabel=dict(bgcolor="white", bordercolor=BORDA, font=dict(family=FONTE, color=TEXTO, size=14)),
    legend=dict(font=dict(size=14, color=TEXTO), title_text=""),
    margin=dict(l=10, r=20, t=56, b=30),
    coloraxis=dict(colorbar=dict(thickness=14, outlinewidth=0, tickfont=dict(size=13, color=TEXTO))),
))
pio.templates.default = "raiox"

CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');
html, body, [class*="css"], .stMarkdown, p, li, label {{ font-family: {FONTE}; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 3rem; max-width: 1320px; }}
header[data-testid="stHeader"] {{ background: rgba(255,255,255,0.9); }}

/* Abas grandes, estilo navegação */
div[data-baseweb="tab-list"] {{ gap: 6px; border-bottom: 2px solid {BORDA}; }}
button[data-baseweb="tab"] {{ padding: 10px 18px; border-radius: 12px 12px 0 0; }}
button[data-baseweb="tab"] p, button[role="tab"] p, .stTabs button p {{ font-size: 19px !important;
    font-weight: 800 !important; color: {TEXTO_2}; }}
button[data-baseweb="tab"][aria-selected="true"] {{ background: {AZUL_FUNDO}; }}
button[data-baseweb="tab"][aria-selected="true"] p, button[role="tab"][aria-selected="true"] p {{ color: {AZUL} !important; }}

/* Abas (Streamlit 1.5x usa react-aria: div[role=tab][data-testid=stTab]) */
[data-testid="stTab"] {{ padding: 8px 12px !important; border-radius: 12px 12px 0 0; }}
[data-testid="stTab"] p {{ font-size: 17px !important; font-weight: 800 !important; color: {TEXTO_2} !important; }}
[data-testid="stTab"][aria-selected="true"] {{ background: {AZUL_FUNDO}; }}
[data-testid="stTab"][aria-selected="true"] p {{ color: {AZUL} !important; }}

.topo {{ display:flex; justify-content:space-between; align-items:center; margin-bottom:10px; }}
.topo .marca {{ font-size:22px; font-weight:900; color:{TEXTO}; letter-spacing:-.01em; }}
.topo .marca span {{ color:{AZUL}; }}
.topo .sub {{ font-size:15px; color:{TEXTO_2}; font-weight:500; }}

.hero {{ background: linear-gradient(120deg, {AZUL} 0%, #3B82F6 55%, #60A5FA 100%); border-radius: 22px;
        padding: 34px 40px; color: white; margin: 10px 0 22px; }}
.hero .tag {{ font-size:14px; font-weight:800; letter-spacing:.08em; text-transform:uppercase; opacity:.95; }}
.hero h1 {{ font-size: 42px; line-height:1.12; font-weight:900; margin:10px 0 12px; color:white; letter-spacing:-.02em; }}
.hero p {{ font-size:20px; margin:0; line-height:1.5; color:white; max-width: 980px; }}

.titulo {{ font-size: 28px; font-weight:900; color:{TEXTO}; margin: 18px 0 4px; letter-spacing:-.01em; }}
.lead {{ font-size: 18px; color:{TEXTO_2}; margin: 0 0 16px; line-height:1.5; }}

.persona {{ background:white; border:2px solid {BORDA}; border-top:8px solid var(--c); border-radius:18px;
            padding:20px 20px 18px; height:100%; }}
.persona .av {{ font-size:40px; line-height:1; }}
.persona .org {{ display:inline-block; margin-top:10px; font-size:14px; font-weight:800; color:white;
                 background:var(--c); padding:4px 12px; border-radius:999px; }}
.persona h4 {{ font-size:19px; font-weight:800; color:{TEXTO}; margin:10px 0 4px; }}
.persona .q {{ font-size:18px; font-weight:700; color:var(--c); margin:8px 0 8px; line-height:1.35; }}
.persona p {{ font-size:16px; color:{TEXTO_2}; margin:0; line-height:1.45; }}

.kpi {{ background:white; border:2px solid {BORDA}; border-radius:18px; padding:18px 20px; height:100%; }}
.kpi .rot {{ font-size:16px; color:{TEXTO_2}; font-weight:700; }}
.kpi .val {{ font-size:44px; font-weight:900; color:var(--c, {TEXTO}); letter-spacing:-.02em; line-height:1.1;
             margin:6px 0 4px; }}
.kpi .sub {{ font-size:15px; color:{TEXTO_2}; line-height:1.35; }}

.achado {{ background:white; border:2px solid {BORDA}; border-left:10px solid var(--c); border-radius:18px;
           padding:22px 24px; height:100%; }}
.achado .num {{ font-size:54px; font-weight:900; color:var(--c); line-height:1; letter-spacing:-.02em; }}
.achado h4 {{ font-size:22px; font-weight:800; color:{TEXTO}; margin:12px 0 6px; }}
.achado p {{ font-size:17px; color:{TEXTO_2}; margin:0; line-height:1.5; }}

.insight {{ font-size:17px; color:{TEXTO}; background:{AZUL_FUNDO}; border-radius:14px; padding:12px 16px;
            margin-bottom:8px; line-height:1.45; border-left:6px solid var(--c, {AZUL}); }}

.hub {{ text-align:center; background:{AZUL}; color:white; border-radius:22px; padding:22px; margin: 6px 0 16px; }}
.hub h3 {{ font-size:26px; font-weight:900; margin:0 0 4px; color:white; }}
.hub p {{ font-size:18px; margin:0; color:white; }}
.parceiro {{ background:white; border:2px solid var(--c); border-radius:18px; padding:18px 20px; height:100%; }}
.parceiro .cab {{ display:flex; align-items:center; gap:10px; }}
.parceiro .cab span {{ font-size:30px; }}
.parceiro .cab b {{ font-size:21px; color:var(--c); font-weight:900; }}
.parceiro .rot {{ font-size:13px; font-weight:800; text-transform:uppercase; letter-spacing:.06em; color:var(--c);
                  margin:12px 0 2px; }}
.parceiro p {{ font-size:16px; color:{TEXTO}; margin:0; line-height:1.45; }}

.fluxo {{ display:flex; flex-wrap:wrap; gap:12px; }}
.fluxo .passo {{ flex:1 1 160px; background:{AZUL_FUNDO}; border-radius:16px; padding:16px; }}
.fluxo .passo .n {{ font-size:28px; font-weight:900; color:{AZUL}; }}
.fluxo .passo .d {{ font-size:15px; color:{TEXTO}; line-height:1.4; margin-top:2px; }}

div[data-testid="stPlotlyChart"] {{ border:2px solid {BORDA}; border-radius:18px; padding:6px; background:white; }}
div[data-testid="stSelectbox"] label p {{ font-size:16px !important; font-weight:700; color:{TEXTO}; }}
.nota {{ font-size:14px; color:{TEXTO_2}; margin-top:4px; }}
</style>
"""
