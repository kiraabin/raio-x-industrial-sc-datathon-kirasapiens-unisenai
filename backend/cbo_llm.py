"""
Agrupamento de CBOs em macrofamílias com IA generativa.

Como funciona
-------------
1. Para cada subgrupo de CBO (3 primeiros dígitos) presente na indústria,
   coletamos os títulos das ocupações mais frequentes no CAGED.
2. Enviamos essa lista a um LLM com um conjunto fechado de macrofamílias
   e pedimos uma classificação em JSON.
3. O resultado vira `data/cbo_macrofamilias.csv`, usado pelo pipeline.

Três modos de uso (o guia aceita chamada de API ou exportação/importação de amostras textuais):

    python backend/cbo_llm.py exportar          # gera data/ia/prompt_cbo.txt com a amostra pronta para colar no LLM
    python backend/cbo_llm.py importar ARQ.json # importa a resposta do LLM e gera data/cbo_macrofamilias.csv
    python backend/cbo_llm.py api               # chama a API da Anthropic direto (precisa de ANTHROPIC_API_KEY)

O mapeamento versionado foi gerado pelo Claude (Anthropic) com este prompt, salvo em
data/ia/resposta_llm.json e revisado pela equipe.

Requer: pip install anthropic pandas pyarrow openpyxl (anthropic só no modo api)
"""
import json
import os
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]

MACROFAMILIAS = [
    "Gestão e Liderança",
    "Engenharia, TI e P&D",
    "Técnicos Industriais e Qualidade",
    "Supervisão de Produção (Mestres e Encarregados)",
    "Administrativo, Comercial e Negócios",
    "Logística e Movimentação",
    "Produção de Base (Linha e Embalagem)",
    "Agroindústria e Alimentos",
    "Têxtil, Vestuário, Couro e Calçados",
    "Metalmecânica e Montagem",
    "Processos Químicos, Plásticos, Papel e Cerâmica",
    "Madeira e Móveis",
    "Manutenção Industrial",
    "Construção e Extração Mineral",
    "Agropecuária, Pesca e Florestal",
    "Serviços de Apoio",
]

PROMPT = """Você é especialista na Classificação Brasileira de Ocupações (CBO 2002)
e no parque industrial de Santa Catarina.

Classifique cada subgrupo de CBO abaixo em EXATAMENTE UMA das macrofamílias:
{familias}

Regras:
- Use os títulos de ocupação como evidência principal.
- Mestres, encarregados e supervisores de produção vão para
  "Supervisão de Produção (Mestres e Encarregados)".
- Ocupações de nível superior em engenharia, TI, química e design de produto
  vão para "Engenharia, TI e P&D".
- Responda SOMENTE com JSON no formato {{"<subgrupo>": "<macrofamília>", ...}}.

Subgrupos:
{subgrupos}
"""


def montar_entrada(caged: pd.DataFrame, dic_cbo: pd.DataFrame, top: int = 5) -> str:
    nomes = dict(zip(dic_cbo["cod"], dic_cbo["desc"]))
    c = caged.assign(sub=caged["cbo2002ocupação"] // 1000)
    freq = c.groupby(["sub", "cbo2002ocupação"]).size().reset_index(name="n")
    linhas = []
    for sub, g in freq.sort_values("n", ascending=False).groupby("sub"):
        titulos = [str(nomes.get(x, "?")) for x in g["cbo2002ocupação"].head(top)]
        linhas.append(f"{sub}: " + "; ".join(titulos))
    return "\n".join(linhas)


def classificar(texto_subgrupos: str, modelo: str = "claude-sonnet-5-5") -> dict:
    import anthropic

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    msg = client.messages.create(
        model=modelo,
        max_tokens=8000,
        messages=[{
            "role": "user",
            "content": PROMPT.format(
                familias="\n".join(f"- {f}" for f in MACROFAMILIAS),
                subgrupos=texto_subgrupos,
            ),
        }],
    )
    texto = msg.content[0].text
    return json.loads(texto[texto.find("{"): texto.rfind("}") + 1])


IA = ROOT / "data/ia"


def _entrada() -> str:
    caged = pd.read_parquet(ROOT / "data/processed/industria.parquet", columns=["cbo"])
    caged = caged.rename(columns={"cbo": "cbo2002ocupação"})
    dic = pd.read_excel(ROOT / "raw/Dicionario_de_dados.xlsx", sheet_name="cbo2002ocupação")
    dic.columns = ["cod", "desc"]
    dic = dic.dropna()
    dic["cod"] = pd.to_numeric(dic["cod"], errors="coerce")
    dic = dic.dropna().astype({"cod": int})
    return montar_entrada(caged, dic)


def prompt_completo(entrada: str) -> str:
    return PROMPT.format(familias="\n".join(f"- {f}" for f in MACROFAMILIAS), subgrupos=entrada)


def salvar_mapa(mapa: dict) -> pd.DataFrame:
    invalidas = {k: v for k, v in mapa.items() if v not in MACROFAMILIAS + ["Não identificado"]}
    if invalidas:
        raise ValueError(f"Macrofamílias fora da lista fechada: {invalidas}")
    out = pd.DataFrame(sorted((int(k), v) for k, v in mapa.items()), columns=["subgrupo", "macrofamilia"])
    out.to_csv(ROOT / "data/cbo_macrofamilias.csv", index=False)
    return out


def exportar():
    IA.mkdir(parents=True, exist_ok=True)
    entrada = _entrada()
    (IA / "amostra_subgrupos.txt").write_text(entrada, encoding="utf-8")
    (IA / "prompt_cbo.txt").write_text(prompt_completo(entrada), encoding="utf-8")
    print(f"{entrada.count(chr(10)) + 1} subgrupos exportados para {IA / 'prompt_cbo.txt'}")


def importar(arquivo: str):
    texto = Path(arquivo).read_text(encoding="utf-8")
    mapa = json.loads(texto[texto.find("{"): texto.rfind("}") + 1])
    out = salvar_mapa(mapa)
    print(out["macrofamilia"].value_counts().to_string())


def via_api():
    IA.mkdir(parents=True, exist_ok=True)
    mapa = classificar(_entrada())
    (IA / "resposta_llm.json").write_text(json.dumps(mapa, ensure_ascii=False, indent=1), encoding="utf-8")
    print(salvar_mapa(mapa)["macrofamilia"].value_counts().to_string())


if __name__ == "__main__":
    import sys

    modo = sys.argv[1] if len(sys.argv) > 1 else "exportar"
    if modo == "exportar":
        exportar()
    elif modo == "importar":
        importar(sys.argv[2])
    elif modo == "api":
        via_api()
    else:
        sys.exit("Use: exportar | importar ARQUIVO.json | api")
