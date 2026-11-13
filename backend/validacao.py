"""
Ingestão e validação do Novo CAGED: schema, domínios e exclusões (MOV × EXC).

- validar_schema(): confere colunas obrigatórias, tipos e se cada código pertence ao domínio do
  dicionário de dados oficial (Dicionario_de_dados.xlsx). Gera data/processed/validacao_schema.csv.
- aplicar_exclusoes(): remove da base MOV os registros que aparecem na base EXC do Novo CAGED
  (declarações excluídas pelo empregador). Se o arquivo EXC não estiver em raw/, registra que a etapa
  não pôde ser aplicada, sem interromper o pipeline.
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"

COLUNAS_OBRIGATORIAS = {
    "competênciamov": "int", "uf": "int", "município": "int", "seção": "str", "subclasse": "int",
    "saldomovimentação": "int", "cbo2002ocupação": "int", "categoria": "int", "graudeinstrução": "int",
    "idade": "num", "horascontratuais": "num", "sexo": "int", "tipomovimentação": "int",
    "indtrabintermitente": "int", "indtrabparcial": "int", "salário": "num", "tamestabjan": "int",
    "indicadoraprendiz": "int", "indicadordeforadoprazo": "int",
}

# Colunas cujo domínio é conferido contra a aba de mesmo nome no dicionário de dados
DOMINIOS_DICIONARIO = ["uf", "seção", "categoria", "graudeinstrução", "sexo", "tipomovimentação",
                       "cbo2002ocupação", "tamestabjan"]

# Chave usada para casar MOV e EXC (os registros EXC repetem os campos do registro original)
CHAVE_EXC = ["competênciamov", "município", "subclasse", "saldomovimentação", "cbo2002ocupação",
             "categoria", "graudeinstrução", "idade", "sexo", "tipomovimentação", "salário",
             "horascontratuais"]


def _codigos(dicionario: dict, aba: str) -> set:
    t = dicionario[aba]
    col = t.columns[0]
    valores = t[col].dropna()
    num = pd.to_numeric(valores, errors="coerce")
    return set(num.dropna().astype(int)) if num.notna().mean() > 0.9 else set(valores.astype(str).str.strip())


def validar_schema(df: pd.DataFrame, municipios_ibge: set[int]) -> pd.DataFrame:
    """Retorna uma tabela com cada regra verificada, quantos registros a violam e a ação tomada."""
    dic = pd.read_excel(RAW / "Dicionario_de_dados.xlsx", sheet_name=None)
    n = len(df)
    linhas = []

    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    linhas.append(("Colunas obrigatórias presentes", len(faltando), "erro" if faltando else "ok",
                   "faltando: " + ", ".join(faltando) if faltando else f"{len(COLUNAS_OBRIGATORIAS)} colunas"))

    for col, tipo in COLUNAS_OBRIGATORIAS.items():
        if col not in df.columns or tipo == "str":
            continue
        invalidos = int(pd.to_numeric(df[col], errors="coerce").isna().sum() - df[col].isna().sum())
        nulos = int(df[col].isna().sum())
        if invalidos or nulos:
            linhas.append((f"Tipo numérico em '{col}'", invalidos + nulos, "aviso",
                           f"{invalidos} não numéricos, {nulos} nulos"))

    for col in DOMINIOS_DICIONARIO:
        if col not in df.columns or col not in dic:
            continue
        validos = _codigos(dic, col)
        serie = df[col].astype(str).str.strip() if isinstance(next(iter(validos)), str) else df[col]
        fora = int((~serie.isin(validos)).sum())
        detalhe = f"{len(validos)} códigos válidos no dicionário"
        if col == "cbo2002ocupação" and fora:
            detalhe += "; códigos CBO criados após o dicionário (ex.: 142360). Mantidos e classificados pelo subgrupo"
        linhas.append((f"Domínio de '{col}' conforme dicionário", fora, "ok" if fora == 0 else "aviso", detalhe))

    regras = [
        ("UF = 42 (Santa Catarina)", (df["uf"] != 42).sum(), "fora do escopo"),
        ("Saldo da movimentação em {-1, +1}", (~df["saldomovimentação"].isin([-1, 1])).sum(), "inconsistente"),
        ("Município existe na base do IBGE", (~df["município"].isin({c // 10 for c in municipios_ibge})).sum(),
         "sem chave de junção"),
        ("Categoria identificada (≠ 999)", (df["categoria"] == 999).sum(), "removido no pipeline"),
        ("Tipo de movimentação identificado (≠ 99)", (df["tipomovimentação"] == 99).sum(), "removido no pipeline"),
        ("Idade entre 14 e 90 anos", (~pd.to_numeric(df["idade"], errors="coerce").between(14, 90)).sum(),
         "mantido; idade não entra nos índices"),
        ("Salário entre R$ 800 e R$ 60 mil", (~df["salário"].between(800, 60_000)).sum(),
         "mantido na contagem; fora das comparações salariais"),
        ("Declaração fora do prazo", (df["indicadordeforadoprazo"] == 1).sum(),
         "mantida se a competência estiver na janela"),
    ]
    for nome, qtd, acao in regras:
        qtd = int(qtd)
        linhas.append((nome, qtd, "ok" if qtd == 0 else "tratado", acao))

    out = pd.DataFrame(linhas, columns=["regra", "registros", "status", "detalhe"])
    out["pct"] = (out["registros"] / n).round(6)
    return out


def aplicar_exclusoes(mov: pd.DataFrame) -> tuple[pd.DataFrame, str]:
    """Remove da base MOV os registros presentes na base EXC (anti-join pela chave do registro).

    Cada linha EXC elimina no máximo uma linha MOV idêntica (casamento um a um), para não apagar
    movimentações legítimas repetidas.
    """
    arquivos = sorted(RAW.glob("*EXC*.csv")) + sorted(RAW.glob("*exc*.csv"))
    if not arquivos:
        return mov, "Base EXC não fornecida pela organização: exclusões não aplicadas (apenas MOV)"
    exc = pd.concat(pd.read_csv(a, sep=";", decimal=",", low_memory=False) for a in arquivos)
    chave = [c for c in CHAVE_EXC if c in mov.columns and c in exc.columns]
    mov = mov.copy()
    mov["_ord"] = mov.groupby(chave, dropna=False).cumcount()
    exc = exc[chave].copy()
    exc["_ord"] = exc.groupby(chave, dropna=False).cumcount()
    marcados = mov.merge(exc.assign(_exc=True), on=chave + ["_ord"], how="left")["_exc"].fillna(False).to_numpy()
    resultado = mov.loc[~marcados].drop(columns="_ord")
    return resultado, f"Exclusões MOV × EXC aplicadas: {int(marcados.sum())} registros removidos"
