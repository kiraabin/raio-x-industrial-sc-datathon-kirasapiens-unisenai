"""
Pipeline do Raio-X do Mercado de Trabalho Industrial de SC.

Entradas (raw/) — as únicas bases do diagnóstico principal (fornecidas pelo desafio):
    Novo_Caged_MOV_Limpo.csv     microdados de movimentação (12 meses, SC)
    Municipios_SC_limpo.csv      dados municipais
    Dicionario_de_dados.xlsx     dicionário do Novo CAGED
Apoio gerado pela equipe (data/):
    cbo_macrofamilias.csv        subgrupo CBO -> macrofamília (gerado com IA, ver backend/cbo_llm.py)
Opcional, FORA das bases do desafio (data/externos/, só para o filtro "Bônus" do painel):
    regioes_ibge.csv             regiões geográficas imediatas e intermediárias (IBGE, 2017)
    sc_municipios.geojson        malha municipal (IBGE)

Saídas (data/processed/):
    industria.parquet            microdados limpos da indústria de transformação (base do dashboard)
    municipios.csv               base municipal tratada
    ind_municipio_setor.csv      polos: município x setor industrial (divisão CNAE)  <- diagnóstico principal
    ind_municipio.csv            indicadores por município (indústria)
    ind_macrofamilia.csv         indicadores por macrofamília de CBO
    ind_regiao_setor.csv         [bônus] região imediata x setor
    ind_regiao_macrofamilia.csv  [bônus] região intermediária x macrofamília
    log_limpeza.csv              volumetria de cada etapa de limpeza
"""
from pathlib import Path
import unicodedata

import pandas as pd

from indicadores import tabela, classificar
import validacao

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "raw"
OUT = ROOT / "data/processed"
OUT.mkdir(parents=True, exist_ok=True)

JANELA = (202509, 202608)  # 12 competências do arquivo fornecido

DIVISOES_CNAE = {
    "10": "Alimentos", "11": "Bebidas", "12": "Fumo", "13": "Têxtil",
    "14": "Vestuário e acessórios", "15": "Couro e calçados", "16": "Madeira",
    "17": "Celulose e papel", "18": "Impressão", "19": "Derivados de petróleo",
    "20": "Químicos", "21": "Farmoquímicos", "22": "Borracha e plástico",
    "23": "Minerais não metálicos (cerâmica, vidro)", "24": "Metalurgia",
    "25": "Produtos de metal", "26": "Eletrônicos e informática",
    "27": "Máquinas e materiais elétricos", "28": "Máquinas e equipamentos",
    "29": "Veículos automotores", "30": "Outros equip. de transporte",
    "31": "Móveis", "32": "Produtos diversos", "33": "Manutenção e instalação de máquinas",
}

NOMES_REGIAO = {  # nomes oficiais com acentuação
    "BLUMENAU": "Blumenau", "CACADOR": "Caçador", "CHAPECO": "Chapecó",
    "CRICIUMA": "Criciúma", "FLORIANOPOLIS": "Florianópolis",
    "JOINVILLE": "Joinville", "LAGES": "Lages",
}


def sem_acento(s: str) -> str:
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode()
    return " ".join(s.upper().replace("'", " ").split())


def titulo(s: str) -> str:
    pequenas = {"de", "do", "da", "dos", "das", "e"}
    return " ".join(w if w in pequenas else w.capitalize() for w in s.lower().split())


def log(etapa, df, registro):
    registro.append({"etapa": etapa, "linhas": len(df)})
    print(f"{etapa:<55} {len(df):>10,}")


def carregar_municipios() -> pd.DataFrame:
    m = pd.read_csv(RAW / "Municipios_SC_limpo.csv", nrows=295, na_values=["-"])
    m = m.iloc[:, :14]
    m.columns = ["municipio_nome", "cod_ibge", "gentilico", "prefeito", "area_km2",
                 "pop_censo_2022", "densidade_2022", "pop_estimada_2026",
                 "escolarizacao_6_14", "idhm_2010", "mortalidade_infantil",
                 "receitas", "despesas", "pib_per_capita_2023"]
    m["cod_ibge"] = m["cod_ibge"].astype(int)
    m["cod_caged"] = m["cod_ibge"] // 10  # CAGED usa 6 dígitos (sem dígito verificador)

    # DADO EXTERNO (fora das bases do desafio): regiões geográficas do IBGE. Só alimenta a seção
    # "Dados externos" do painel; o diagnóstico principal usa apenas município (base fornecida).
    arq_reg = ROOT / "data/externos/regioes_ibge.csv"
    if not arq_reg.exists():
        return m
    reg = pd.read_csv(arq_reg)
    reg = reg[reg["cod_municipio"].between(4200000, 4299999)]
    reg = reg.rename(columns={"cod_municipio": "cod_ibge"})
    reg["regiao_intermediaria"] = reg["regiao_intermediaria"].map(NOMES_REGIAO)
    # Regiões imediatas levam nomes de municípios: recupera a acentuação pela base municipal
    acentos = {sem_acento(n): n for n in m["municipio_nome"]}
    reg["regiao_imediata"] = reg["regiao_imediata"].map(
        lambda s: " - ".join(acentos.get(sem_acento(p), titulo(p)) for p in s.split(" - ")))
    m = m.merge(reg[["cod_ibge", "cod_reg_imediata", "regiao_imediata",
                     "cod_reg_intermediaria", "regiao_intermediaria"]],
                on="cod_ibge", how="left")
    return m


def carregar_caged(registro, mun: pd.DataFrame | None = None) -> pd.DataFrame:
    parquet = OUT / "caged_raw.parquet"
    if parquet.exists():
        df = pd.read_parquet(parquet)
    else:
        df = pd.read_csv(RAW / "Novo_Caged_MOV_Limpo.csv", sep=";", decimal=",", low_memory=False)
        df = df.drop(columns=[c for c in df.columns if c.startswith("Unnamed")])
        df["idade"] = pd.to_numeric(df["idade"], errors="coerce")
        df.to_parquet(parquet)
    log("Carga inicial (todas as seções)", df, registro)

    # Validação de schema e domínios contra o dicionário de dados
    if mun is not None:
        val = validacao.validar_schema(df, set(mun["cod_ibge"]))
        val.to_csv(OUT / "validacao_schema.csv", index=False)
        print(val[["regra", "registros", "status"]].to_string(index=False))

    # Exclusões MOV x EXC (aplicadas se a base EXC estiver em raw/)
    df, msg = validacao.aplicar_exclusoes(df)
    print(msg)
    log("Após exclusões MOV × EXC", df, registro)

    df = df[df["competênciamov"].between(*JANELA)]
    log(f"Competência dentro da janela {JANELA}", df, registro)

    df = df[df["categoria"] != 999]
    df = df[~df["tipomovimentação"].isin([99])]
    log("Remove categoria/tipo de movimentação não identificados", df, registro)
    return df


def enriquecer(df: pd.DataFrame, mun: pd.DataFrame) -> pd.DataFrame:
    df = df.merge(mun[["cod_caged", "cod_ibge", "municipio_nome", "regiao_imediata",
                       "regiao_intermediaria"]],
                  left_on="município", right_on="cod_caged", how="left")
    sub = df["subclasse"].astype(str).str.zfill(7)
    df["divisao_cnae"] = sub.str[:2]
    df["setor"] = df["divisao_cnae"].map(DIVISOES_CNAE)
    df["cbo"] = df["cbo2002ocupação"]
    df["admissao"] = df["saldomovimentação"] == 1
    df["pedido"] = df["tipomovimentação"] == 40

    mf = pd.read_csv(ROOT / "data/cbo_macrofamilias.csv")
    df["macrofamilia"] = (df["cbo"] // 1000).map(dict(zip(mf["subgrupo"], mf["macrofamilia"])))
    df["macrofamilia"] = df["macrofamilia"].fillna("Outras ocupações")
    gg = (df["cbo"] // 100000).clip(upper=9)
    df["nivel_ocupacao"] = gg.map({0: "Forças armadas", 1: "Gestão", 2: "Nível superior",
                                   3: "Técnico (nível médio)"}).fillna("Operacional")

    # Salário válido para comparações: jornada >= 30h, sem intermitente/aprendiz/parcial,
    # e dentro de uma faixa plausível (remove zeros e erros de digitação).
    df["salario"] = df["salário"]
    df["salario_valido"] = (
        df["salario"].between(800, 60_000)
        & (df["horascontratuais"] >= 30)
        & (df["indtrabintermitente"] == 0)
        & (df["indicadoraprendiz"] == 0)
        & (df["indtrabparcial"] == 0)
    )
    return df


def main():
    registro = []
    mun = carregar_municipios()
    df = carregar_caged(registro, mun)
    df = enriquecer(df, mun)
    assert df["cod_ibge"].notna().all(), "movimentação sem município na base fornecida"

    ind = df[df["seção"] == "C"].copy()
    log("Indústria de transformação (seção C)", ind, registro)
    log(" ...das quais com salário válido p/ comparações", ind[ind["salario_valido"]], registro)

    externos = [c for c in ["regiao_imediata", "regiao_intermediaria"] if c in ind.columns]
    cols = ["competênciamov", "cod_ibge", "municipio_nome"] + externos + ["divisao_cnae", "setor", "cbo", "macrofamilia",
            "nivel_ocupacao", "admissao", "pedido", "tipomovimentação", "salario",
            "salario_valido", "graudeinstrução", "idade", "sexo", "tamestabjan"]
    ind = ind[cols]
    for c in ["municipio_nome", "setor", "macrofamilia", "nivel_ocupacao", "divisao_cnae"] + externos:
        ind[c] = ind[c].astype("category")
    ind.to_parquet(OUT / "industria.parquet", index=False)
    mun.drop(columns=["prefeito", "gentilico"]).to_csv(OUT / "municipios.csv", index=False)

    pop_mun = mun.set_index("cod_ibge")["pop_estimada_2026"]
    nomes_reg = [c for c in ["regiao_imediata", "regiao_intermediaria"] if c in mun.columns]

    # ---- Diagnóstico principal: só bases do desafio (CAGED + municípios + dicionário) ----
    classificar(tabela(ind, ["macrofamilia"])).to_csv(OUT / "ind_macrofamilia.csv", index=False)
    tm = tabela(ind, ["cod_ibge"], pop_mun)
    tm = tm.merge(mun[["cod_ibge", "municipio_nome"] + nomes_reg], on="cod_ibge")
    classificar(tm).to_csv(OUT / "ind_municipio.csv", index=False)
    ms = classificar(tabela(ind, ["cod_ibge", "setor"], pop_mun))
    ms = ms.merge(mun[["cod_ibge", "municipio_nome"] + nomes_reg], on="cod_ibge")
    ms.to_csv(OUT / "ind_municipio_setor.csv", index=False)

    # ---- Seção externa (regiões do IBGE): só se o arquivo externo estiver presente ----
    if nomes_reg:
        pop_imed = mun.groupby("regiao_imediata")["pop_estimada_2026"].sum()
        pop_inter = mun.groupby("regiao_intermediaria")["pop_estimada_2026"].sum()
        classificar(tabela(ind, ["regiao_imediata", "setor"], pop_imed)).to_csv(
            OUT / "ind_regiao_setor.csv", index=False)
        classificar(tabela(ind, ["regiao_intermediaria", "macrofamilia"], pop_inter)).to_csv(
            OUT / "ind_regiao_macrofamilia.csv", index=False)

    pd.DataFrame(registro).to_csv(OUT / "log_limpeza.csv", index=False)
    print("\nDiagnóstico município × setor (bases do desafio):")
    print(ms["diagnostico"].value_counts().to_string())


if __name__ == "__main__":
    main()
