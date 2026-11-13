# Raio-X do Mercado de Trabalho Industrial de Santa Catarina
**Equipe Kirasapiens Neurotech · Datathon UniSENAI 2026 · consultoria de dados para a FIESC**

> **Pergunta central:** quais regiões (municípios) e setores industriais de SC enfrentam apagão de mão de obra ou expansão acelerada, e como renda e escolaridade explicam esses gargalos?

> **Regra de dados:** o diagnóstico usa **apenas as bases fornecidas pelo desafio** (Novo CAGED MOV, base municipal de SC e dicionário de dados), mais a classificação de CBOs feita por IA a partir dessas mesmas bases. Fontes externas (regiões geográficas e malha do IBGE) ficam isoladas em `data/externos/` e aparecem só no **Apêndice bônus** e no filtro *Bônus* do painel.

Este notebook documenta **todo o pipeline**, da carga inicial e exclusão de registros inválidos até a comunicação com a IA e a exportação final que alimenta o painel (`dashboard/app.py`). O código reutilizável está em `backend/`.

| Etapa do guia | Onde está neste notebook | Código |
|---|---|---|
| Ingestão e validação (schema, inconsistências, MOV × EXC) | Seção 1 | `backend/validacao.py`, `backend/pipeline.py` |
| Cruzamento relacional (CAGED × base municipal) e saldo por 10 mil hab. | Seção 2 | `backend/pipeline.py` |
| Enriquecimento com IA (prompt, amostra, API, importação) | Seção 3 | `backend/cbo_llm.py`, `data/ia/` |
| Análise: indicadores, diagnóstico e robustez | Seção 4 | `backend/indicadores.py`, `backend/estatistica.py` |
| Renda e escolaridade | Seção 5 | `backend/estatistica.py` |
| Exportação final | Seção 6 | `backend/exportar.py` |
| Bônus: fontes externas (fora das regras) | Apêndice | `data/externos/` |


```python
import sys; sys.path.insert(0, '../backend')
import pandas as pd, numpy as np
import matplotlib.pyplot as plt
import pipeline, validacao, cbo_llm, estatistica, exportar
pd.set_option('display.max_columns', 30); pd.set_option('display.width', 200)
P = '../data/processed/'
```

## 1. Ingestão e validação
### 1.1 Carga e schema
O arquivo `raw/Novo_Caged_MOV_Limpo.csv` (~413 MB, separador `;`, decimal `,`) não está no Git; o link do Kaggle está no README. Na primeira execução o pipeline converte o CSV para parquet (`data/processed/caged_raw.parquet`) para acelerar as demais.


```python
caged_csv = pipeline.RAW / 'Novo_Caged_MOV_Limpo.csv'
cache = pipeline.OUT / 'caged_raw.parquet'
if cache.exists():
    bruto = pd.read_parquet(cache)
elif caged_csv.exists():
    bruto = pd.read_csv(caged_csv, sep=';', decimal=',', low_memory=False)
    bruto = bruto.drop(columns=[c for c in bruto.columns if c.startswith('Unnamed')])
else:
    bruto = None
    print('CAGED bruto ausente: baixe do Kaggle (link no README) e coloque em raw/. '
          'As seções seguintes usam os arquivos processados já versionados.')
if bruto is not None:
    print(f'{len(bruto):,} registros · {bruto.shape[1]} colunas')
    display(bruto.dtypes.to_frame('tipo').T)
```

    3,397,416 registros · 28 colunas



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>competênciamov</th>
      <th>região</th>
      <th>uf</th>
      <th>município</th>
      <th>seção</th>
      <th>subclasse</th>
      <th>saldomovimentação</th>
      <th>cbo2002ocupação</th>
      <th>categoria</th>
      <th>graudeinstrução</th>
      <th>idade</th>
      <th>horascontratuais</th>
      <th>raçacor</th>
      <th>sexo</th>
      <th>tipoempregador</th>
      <th>tipoestabelecimento</th>
      <th>tipomovimentação</th>
      <th>tipodedeficiência</th>
      <th>indtrabintermitente</th>
      <th>indtrabparcial</th>
      <th>salário</th>
      <th>tamestabjan</th>
      <th>indicadoraprendiz</th>
      <th>origemdainformação</th>
      <th>competênciadec</th>
      <th>indicadordeforadoprazo</th>
      <th>unidadesaláriocódigo</th>
      <th>valorsaláriofixo</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>tipo</th>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>str</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>float64</td>
      <td>float64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>float64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>int64</td>
      <td>float64</td>
    </tr>
  </tbody>
</table>
</div>


### 1.2 Validação de schema e domínios
Cada coluna obrigatória é conferida quanto à presença e ao tipo, e cada código é comparado ao **dicionário de dados oficial** (`raw/Dicionario_de_dados.xlsx`). A coluna `status` diz o que aconteceu com cada inconsistência.


```python
mun = pipeline.carregar_municipios()
if bruto is not None:
    val = validacao.validar_schema(bruto, set(mun['cod_ibge']))
else:
    val = pd.read_csv(P + 'validacao_schema.csv')
val
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>regra</th>
      <th>registros</th>
      <th>status</th>
      <th>detalhe</th>
      <th>pct</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Colunas obrigatórias presentes</td>
      <td>0</td>
      <td>ok</td>
      <td>19 colunas</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Tipo numérico em 'idade'</td>
      <td>2202</td>
      <td>aviso</td>
      <td>0 não numéricos, 2202 nulos</td>
      <td>0.000648</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Domínio de 'uf' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>28 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Domínio de 'seção' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>22 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Domínio de 'categoria' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>10 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Domínio de 'graudeinstrução' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>13 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Domínio de 'sexo' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>3 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Domínio de 'tipomovimentação' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>18 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>8</th>
      <td>Domínio de 'cbo2002ocupação' conforme dicionário</td>
      <td>2117</td>
      <td>aviso</td>
      <td>2778 códigos válidos no dicionário; códigos CB...</td>
      <td>0.000623</td>
    </tr>
    <tr>
      <th>9</th>
      <td>Domínio de 'tamestabjan' conforme dicionário</td>
      <td>0</td>
      <td>ok</td>
      <td>14 códigos válidos no dicionário</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>10</th>
      <td>UF = 42 (Santa Catarina)</td>
      <td>0</td>
      <td>ok</td>
      <td>fora do escopo</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>11</th>
      <td>Saldo da movimentação em {-1, +1}</td>
      <td>0</td>
      <td>ok</td>
      <td>inconsistente</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>12</th>
      <td>Município existe na base do IBGE</td>
      <td>0</td>
      <td>ok</td>
      <td>sem chave de junção</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>13</th>
      <td>Categoria identificada (≠ 999)</td>
      <td>510</td>
      <td>tratado</td>
      <td>removido no pipeline</td>
      <td>0.000150</td>
    </tr>
    <tr>
      <th>14</th>
      <td>Tipo de movimentação identificado (≠ 99)</td>
      <td>0</td>
      <td>ok</td>
      <td>removido no pipeline</td>
      <td>0.000000</td>
    </tr>
    <tr>
      <th>15</th>
      <td>Idade entre 14 e 90 anos</td>
      <td>2216</td>
      <td>tratado</td>
      <td>mantido; idade não entra nos índices</td>
      <td>0.000652</td>
    </tr>
    <tr>
      <th>16</th>
      <td>Salário entre R$ 800 e R$ 60 mil</td>
      <td>63787</td>
      <td>tratado</td>
      <td>mantido na contagem; fora das comparações sala...</td>
      <td>0.018775</td>
    </tr>
    <tr>
      <th>17</th>
      <td>Declaração fora do prazo</td>
      <td>36940</td>
      <td>tratado</td>
      <td>mantida se a competência estiver na janela</td>
      <td>0.010873</td>
    </tr>
  </tbody>
</table>
</div>



**Leitura:** a base é toda de SC (UF 42), o saldo é sempre −1/+1 e 100% dos municípios têm correspondência na base municipal do desafio. As inconsistências são tratadas assim:
- **Categoria 999** (não identificada): removida.
- **Salário fora de R\$ 800 a R\$ 60 mil**: mantido nas contagens, mas fora das comparações salariais.
- **CBOs mais novos que o dicionário** (ex.: 142360): mantidos e classificados pelo subgrupo de 3 dígitos.

### 1.3 Exclusões MOV × EXC
O Novo CAGED publica duas bases: **MOV** (movimentações declaradas) e **EXC** (declarações que o empregador excluiu depois). O correto é remover da MOV os registros que aparecem na EXC. A função `validacao.aplicar_exclusoes()` faz esse anti-join, casando cada linha EXC com no máximo uma linha MOV idêntica. A organização forneceu **apenas a base MOV**; se um arquivo `*EXC*.csv` for colocado em `raw/`, a etapa é aplicada automaticamente.


```python
if bruto is not None:
    _, msg = validacao.aplicar_exclusoes(bruto.head(1000))
    print(msg)
```

    Base EXC não fornecida pela organização: exclusões não aplicadas (apenas MOV)


### 1.4 Pipeline completo e volumetria
Roda carga, validação, exclusões, filtros, junção, macrofamílias e indicadores, gravando tudo em `data/processed/`.


```python
if bruto is not None:
    del bruto
    pipeline.main()
pd.read_csv(P + 'log_limpeza.csv')
```

    Carga inicial (todas as seções)                          3,397,416


                                                regra  registros  status
                       Colunas obrigatórias presentes          0      ok
                             Tipo numérico em 'idade'       2202   aviso
                  Domínio de 'uf' conforme dicionário          0      ok
               Domínio de 'seção' conforme dicionário          0      ok
           Domínio de 'categoria' conforme dicionário          0      ok
     Domínio de 'graudeinstrução' conforme dicionário          0      ok
                Domínio de 'sexo' conforme dicionário          0      ok
    Domínio de 'tipomovimentação' conforme dicionário          0      ok
     Domínio de 'cbo2002ocupação' conforme dicionário       2117   aviso
         Domínio de 'tamestabjan' conforme dicionário          0      ok
                             UF = 42 (Santa Catarina)          0      ok
                    Saldo da movimentação em {-1, +1}          0      ok
                     Município existe na base do IBGE          0      ok
                       Categoria identificada (≠ 999)        510 tratado
             Tipo de movimentação identificado (≠ 99)          0      ok
                             Idade entre 14 e 90 anos       2216 tratado
                     Salário entre R$ 800 e R$ 60 mil      63787 tratado
                             Declaração fora do prazo      36940 tratado
    Base EXC não fornecida pela organização: exclusões não aplicadas (apenas MOV)
    Após exclusões MOV × EXC                                 3,397,416


    Competência dentro da janela (202509, 202608)            3,391,288


    Remove categoria/tipo de movimentação não identificados  3,390,779


    Indústria de transformação (seção C)                       835,776


     ...das quais com salário válido p/ comparações            781,353


    
    Diagnóstico município × setor (bases do desafio):
    diagnostico
    Volume insuficiente      2567
    Estável                   365
    Apagão de mão de obra      59
    Expansão acelerada         56
    Retração                   47
    Expansão sob pressão       11





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>etapa</th>
      <th>linhas</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Carga inicial (todas as seções)</td>
      <td>3397416</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Após exclusões MOV × EXC</td>
      <td>3397416</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Competência dentro da janela (202509, 202608)</td>
      <td>3391288</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Remove categoria/tipo de movimentação não iden...</td>
      <td>3390779</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Indústria de transformação (seção C)</td>
      <td>835776</td>
    </tr>
    <tr>
      <th>5</th>
      <td>...das quais com salário válido p/ comparações</td>
      <td>781353</td>
    </tr>
  </tbody>
</table>
</div>



## 2. Cruzamento relacional (CAGED × base municipal)
O CAGED identifica o município com **6 dígitos** e a base municipal do desafio com **7** (o último é dígito verificador). A chave de junção é `cod_ibge // 10`. A unidade territorial do diagnóstico é o **município**, e o polo é **município × setor**: não usamos agrupamentos regionais externos no núcleo da análise.


```python
ind = pd.read_parquet(P + 'industria.parquet')
print(f"{len(ind):,} movimentações na indústria de transformação (CNAE C)")
print('Registros sem município na base fornecida após a junção:', ind['cod_ibge'].isna().sum())
mun[['municipio_nome', 'cod_ibge', 'cod_caged', 'pop_estimada_2026']].head()
```

    835,776 movimentações na indústria de transformação (CNAE C)
    Registros sem município na base fornecida após a junção: 0





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>municipio_nome</th>
      <th>cod_ibge</th>
      <th>cod_caged</th>
      <th>pop_estimada_2026</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Abdon Batista</td>
      <td>4200051</td>
      <td>420005</td>
      <td>2628</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Abelardo Luz</td>
      <td>4200101</td>
      <td>420010</td>
      <td>17797</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Agrolândia</td>
      <td>4200200</td>
      <td>420020</td>
      <td>11798</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Agronômica</td>
      <td>4200309</td>
      <td>420030</td>
      <td>6453</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Água Doce</td>
      <td>4200408</td>
      <td>420040</td>
      <td>6547</td>
    </tr>
  </tbody>
</table>
</div>



**Saldo de vagas por 10 mil habitantes** normaliza a comparação entre cidades grandes e pequenas: saldo ÷ população estimada 2026 × 10.000.


```python
im = pd.read_csv(P + 'ind_municipio.csv')
im = im[im['movimentacoes'] >= 300]
cols = ['municipio_nome', 'saldo', 'populacao', 'saldo_10k_hab']
print('Maior crescimento relativo'); display(im.nlargest(5, 'saldo_10k_hab')[cols].round(1))
print('Maior retração relativa'); display(im.nsmallest(5, 'saldo_10k_hab')[cols].round(1))
```

    Maior crescimento relativo



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>municipio_nome</th>
      <th>saldo</th>
      <th>populacao</th>
      <th>saldo_10k_hab</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>103</th>
      <td>Guatambú</td>
      <td>563.0</td>
      <td>9947.0</td>
      <td>566.0</td>
    </tr>
    <tr>
      <th>169</th>
      <td>Nova Erechim</td>
      <td>169.0</td>
      <td>5553.0</td>
      <td>304.3</td>
    </tr>
    <tr>
      <th>168</th>
      <td>Navegantes</td>
      <td>2381.0</td>
      <td>98421.0</td>
      <td>241.9</td>
    </tr>
    <tr>
      <th>273</th>
      <td>Treze Tílias</td>
      <td>207.0</td>
      <td>9749.0</td>
      <td>212.3</td>
    </tr>
    <tr>
      <th>185</th>
      <td>Paraíso</td>
      <td>81.0</td>
      <td>4412.0</td>
      <td>183.6</td>
    </tr>
  </tbody>
</table>
</div>


    Maior retração relativa



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>municipio_nome</th>
      <th>saldo</th>
      <th>populacao</th>
      <th>saldo_10k_hab</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>53</th>
      <td>Campo Alegre</td>
      <td>-423.0</td>
      <td>13007.0</td>
      <td>-325.2</td>
    </tr>
    <tr>
      <th>83</th>
      <td>Ermo</td>
      <td>-70.0</td>
      <td>2342.0</td>
      <td>-298.9</td>
    </tr>
    <tr>
      <th>260</th>
      <td>Siderópolis</td>
      <td>-365.0</td>
      <td>14223.0</td>
      <td>-256.6</td>
    </tr>
    <tr>
      <th>205</th>
      <td>Pouso Redondo</td>
      <td>-374.0</td>
      <td>18270.0</td>
      <td>-204.7</td>
    </tr>
    <tr>
      <th>256</th>
      <td>Saudades</td>
      <td>-147.0</td>
      <td>10922.0</td>
      <td>-134.6</td>
    </tr>
  </tbody>
</table>
</div>


## 3. Enriquecimento com IA generativa: CBOs → macrofamílias
Os **1.467 códigos CBO** presentes na indústria pertencem a **177 subgrupos** (3 dígitos). Para cada subgrupo, montamos uma amostra com os títulos das ocupações mais frequentes e pedimos a um LLM que o classifique em uma de **16 macrofamílias** fechadas, com resposta em JSON.

O script `backend/cbo_llm.py` tem três modos:
- `exportar`: gera `data/ia/prompt_cbo.txt` com a amostra textual pronta para o LLM;
- `importar ARQ.json`: valida a resposta (só macrofamílias da lista) e grava `data/cbo_macrofamilias.csv`;
- `api`: chama a API da Anthropic diretamente (precisa de `ANTHROPIC_API_KEY`).


```python
cbo_llm.exportar()
prompt = (cbo_llm.IA / 'prompt_cbo.txt').read_text(encoding='utf-8')
print(prompt[:1400], '\n[...]')
```

    177 subgrupos exportados para /home/claude/raio-x-industrial-sc/data/ia/prompt_cbo.txt
    Você é especialista na Classificação Brasileira de Ocupações (CBO 2002)
    e no parque industrial de Santa Catarina.
    
    Classifique cada subgrupo de CBO abaixo em EXATAMENTE UMA das macrofamílias:
    - Gestão e Liderança
    - Engenharia, TI e P&D
    - Técnicos Industriais e Qualidade
    - Supervisão de Produção (Mestres e Encarregados)
    - Administrativo, Comercial e Negócios
    - Logística e Movimentação
    - Produção de Base (Linha e Embalagem)
    - Agroindústria e Alimentos
    - Têxtil, Vestuário, Couro e Calçados
    - Metalmecânica e Montagem
    - Processos Químicos, Plásticos, Papel e Cerâmica
    - Madeira e Móveis
    - Manutenção Industrial
    - Construção e Extração Mineral
    - Agropecuária, Pesca e Florestal
    - Serviços de Apoio
    
    Regras:
    - Use os títulos de ocupação como evidência principal.
    - Mestres, encarregados e supervisores de produção vão para
      "Supervisão de Produção (Mestres e Encarregados)".
    - Ocupações de nível superior em engenharia, TI, química e design de produto
      vão para "Engenharia, TI e P&D".
    - Responda SOMENTE com JSON no formato {"<subgrupo>": "<macrofamília>", ...}.
    
    Subgrupos:
    111: Analista de Planejamento e Orçamento - Apo; Secretario - Executivo
    121: Diretor Geral de Empresa e Organizacoes (Exceto de Interesse Publico); Diretor de Planejamento Estrategico
    122: Diretor de Producao e Operacoes da Industria de Transformacao, Extracao Mineral e Utilidades; Diretor de Operacoes Comerciais (Comerci 
    [...]


A resposta do LLM (Claude, Anthropic) está salva em `data/ia/resposta_llm.json`. A importação valida e reproduz o mapeamento usado em todo o projeto:


```python
cbo_llm.importar(str(cbo_llm.IA / 'resposta_llm.json'))
mf_map = pd.read_csv('../data/cbo_macrofamilias.csv')
print(len(mf_map), 'subgrupos classificados')
```

    macrofamilia
    Administrativo, Comercial e Negócios               36
    Técnicos Industriais e Qualidade                   18
    Supervisão de Produção (Mestres e Encarregados)    15
    Gestão e Liderança                                 13
    Processos Químicos, Plásticos, Papel e Cerâmica    13
    Engenharia, TI e P&D                               12
    Metalmecânica e Montagem                           11
    Serviços de Apoio                                  10
    Agropecuária, Pesca e Florestal                    10
    Manutenção Industrial                               9
    Têxtil, Vestuário, Couro e Calçados                 8
    Madeira e Móveis                                    7
    Construção e Extração Mineral                       5
    Logística e Movimentação                            4
    Agroindústria e Alimentos                           3
    Produção de Base (Linha e Embalagem)                2
    Não identificado                                    1
    177 subgrupos classificados


**Validação do agrupamento:** comparamos as macrofamílias da IA com o grande grupo oficial da CBO (1º dígito). A IA separa, por exemplo, o grande grupo 7 (produção industrial) em famílias por cadeia produtiva, o que a hierarquia oficial não mostra.


```python
gg = {1: 'Dirigentes', 2: 'Nível superior', 3: 'Técnicos', 4: 'Administrativos', 5: 'Serviços',
      6: 'Agropecuária', 7: 'Produção industrial (7)', 8: 'Processos contínuos (8)', 9: 'Manutenção (9)'}
x = ind.assign(grande_grupo=(ind['cbo'] // 100000).map(gg))
pd.crosstab(x['macrofamilia'], x['grande_grupo']).loc[:, lambda t: t.sum() > 1000]
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th>grande_grupo</th>
      <th>Administrativos</th>
      <th>Agropecuária</th>
      <th>Dirigentes</th>
      <th>Manutenção (9)</th>
      <th>Nível superior</th>
      <th>Processos contínuos (8)</th>
      <th>Produção industrial (7)</th>
      <th>Serviços</th>
      <th>Técnicos</th>
    </tr>
    <tr>
      <th>macrofamilia</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Administrativo, Comercial e Negócios</th>
      <td>45746</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>7669</td>
      <td>0</td>
      <td>0</td>
      <td>16799</td>
      <td>8171</td>
    </tr>
    <tr>
      <th>Agroindústria e Alimentos</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>56896</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Agropecuária, Pesca e Florestal</th>
      <td>0</td>
      <td>4764</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Construção e Extração Mineral</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>16506</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Engenharia, TI e P&amp;D</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>3811</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>1614</td>
    </tr>
    <tr>
      <th>Gestão e Liderança</th>
      <td>1581</td>
      <td>32</td>
      <td>8235</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>922</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Logística e Movimentação</th>
      <td>48368</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>23001</td>
      <td>0</td>
      <td>799</td>
    </tr>
    <tr>
      <th>Madeira e Móveis</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>22083</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Manutenção Industrial</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>20665</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Metalmecânica e Montagem</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>7235</td>
      <td>83934</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Não identificado</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>51</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Processos Químicos, Plásticos, Papel e Cerâmica</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>39434</td>
      <td>9518</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Produção de Base (Linha e Embalagem)</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>216351</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Serviços de Apoio</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>332</td>
      <td>0</td>
      <td>0</td>
      <td>31275</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Supervisão de Produção (Mestres e Encarregados)</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>688</td>
      <td>0</td>
      <td>1579</td>
      <td>4390</td>
      <td>0</td>
      <td>0</td>
    </tr>
    <tr>
      <th>Técnicos Industriais e Qualidade</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>86</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>34467</td>
    </tr>
    <tr>
      <th>Têxtil, Vestuário, Couro e Calçados</th>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>0</td>
      <td>116001</td>
      <td>2773</td>
      <td>0</td>
    </tr>
  </tbody>
</table>
</div>




```python
# Para regenerar via API (não executado aqui):
# import os; os.environ['ANTHROPIC_API_KEY'] = '...'
# cbo_llm.via_api()
```

## 4. Indicadores, diagnóstico e robustez
| Indicador | Definição | Leitura |
|---|---|---|
| Saldo por 10 mil hab. | (admissões − desligamentos) ÷ população × 10.000 | expansão |
| % saídas a pedido | desligamentos tipo 40 ÷ desligamentos | trabalhador sai porque tem opção |
| Índice de reposição | desligamentos ÷ admissões | perto de 1 = contrata só para repor |
| Prêmio salarial ajustado | média ponderada, por CBO, de log(mediana adm ÷ mediana desl) | empresa paga mais para repor |
| **Índice de Pressão** | média dos z-scores dos três acima | > 0,5 = indício de pressão ("apagão") |
| **Índice de Expansão** | z-score do saldo por 10 mil hab. | > 0,5 = expansão acelerada |


```python
saldo = lambda s: 2 * s.sum() - len(s)
s = ind.groupby('setor', observed=True)['admissao'].agg(movimentacoes='size', saldo=saldo)
s.sort_values('saldo', ascending=False)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>movimentacoes</th>
      <th>saldo</th>
    </tr>
    <tr>
      <th>setor</th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Alimentos</th>
      <td>176832</td>
      <td>4748</td>
    </tr>
    <tr>
      <th>Máquinas e materiais elétricos</th>
      <td>33000</td>
      <td>2018</td>
    </tr>
    <tr>
      <th>Manutenção e instalação de máquinas</th>
      <td>27356</td>
      <td>1622</td>
    </tr>
    <tr>
      <th>Outros equip. de transporte</th>
      <td>9395</td>
      <td>1029</td>
    </tr>
    <tr>
      <th>Veículos automotores</th>
      <td>26353</td>
      <td>835</td>
    </tr>
    <tr>
      <th>Celulose e papel</th>
      <td>21434</td>
      <td>534</td>
    </tr>
    <tr>
      <th>Metalurgia</th>
      <td>16952</td>
      <td>384</td>
    </tr>
    <tr>
      <th>Químicos</th>
      <td>13958</td>
      <td>286</td>
    </tr>
    <tr>
      <th>Borracha e plástico</th>
      <td>65542</td>
      <td>270</td>
    </tr>
    <tr>
      <th>Farmoquímicos</th>
      <td>2251</td>
      <td>35</td>
    </tr>
    <tr>
      <th>Derivados de petróleo</th>
      <td>179</td>
      <td>23</td>
    </tr>
    <tr>
      <th>Bebidas</th>
      <td>5869</td>
      <td>-7</td>
    </tr>
    <tr>
      <th>Máquinas e equipamentos</th>
      <td>45821</td>
      <td>-89</td>
    </tr>
    <tr>
      <th>Produtos diversos</th>
      <td>13298</td>
      <td>-116</td>
    </tr>
    <tr>
      <th>Impressão</th>
      <td>6039</td>
      <td>-179</td>
    </tr>
    <tr>
      <th>Fumo</th>
      <td>2251</td>
      <td>-189</td>
    </tr>
    <tr>
      <th>Produtos de metal</th>
      <td>52403</td>
      <td>-295</td>
    </tr>
    <tr>
      <th>Eletrônicos e informática</th>
      <td>9337</td>
      <td>-371</td>
    </tr>
    <tr>
      <th>Couro e calçados</th>
      <td>8796</td>
      <td>-550</td>
    </tr>
    <tr>
      <th>Têxtil</th>
      <td>66812</td>
      <td>-784</td>
    </tr>
    <tr>
      <th>Minerais não metálicos (cerâmica, vidro)</th>
      <td>33490</td>
      <td>-840</td>
    </tr>
    <tr>
      <th>Móveis</th>
      <td>32426</td>
      <td>-1316</td>
    </tr>
    <tr>
      <th>Madeira</th>
      <td>46432</td>
      <td>-1388</td>
    </tr>
    <tr>
      <th>Vestuário e acessórios</th>
      <td>119550</td>
      <td>-4562</td>
    </tr>
  </tbody>
</table>
</div>




```python
ms = pd.read_csv(P + 'ind_municipio_setor.csv')
ms = ms[ms['movimentacoes'] >= 300]
print(len(ms), 'polos município × setor com 300+ movimentações')
print(ms['diagnostico'].value_counts())
cols = ['municipio_nome', 'setor', 'movimentacoes', 'saldo', 'saldo_10k_hab', 'pct_pedido_demissao',
        'indice_reposicao', 'salario_mediano_adm', 'indice_pressao', 'indice_expansao', 'diagnostico']
ms[ms['diagnostico'] == 'Expansão acelerada'].nlargest(8, 'saldo')[cols].round(2)
```

    538 polos município × setor com 300+ movimentações
    diagnostico
    Estável                  365
    Apagão de mão de obra     59
    Expansão acelerada        56
    Retração                  47
    Expansão sob pressão      11
    Name: count, dtype: int64





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>municipio_nome</th>
      <th>setor</th>
      <th>movimentacoes</th>
      <th>saldo</th>
      <th>saldo_10k_hab</th>
      <th>pct_pedido_demissao</th>
      <th>indice_reposicao</th>
      <th>salario_mediano_adm</th>
      <th>indice_pressao</th>
      <th>indice_expansao</th>
      <th>diagnostico</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>1798</th>
      <td>Navegantes</td>
      <td>Veículos automotores</td>
      <td>5054.0</td>
      <td>1620.0</td>
      <td>164.60</td>
      <td>0.58</td>
      <td>0.51</td>
      <td>2079.00</td>
      <td>-0.15</td>
      <td>3.79</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>663</th>
      <td>Chapecó</td>
      <td>Alimentos</td>
      <td>19473.0</td>
      <td>1273.0</td>
      <td>44.02</td>
      <td>0.53</td>
      <td>0.88</td>
      <td>2175.80</td>
      <td>-0.16</td>
      <td>0.97</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>1793</th>
      <td>Navegantes</td>
      <td>Outros equip. de transporte</td>
      <td>1687.0</td>
      <td>625.0</td>
      <td>63.50</td>
      <td>0.47</td>
      <td>0.46</td>
      <td>2693.46</td>
      <td>-0.43</td>
      <td>1.42</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>1108</th>
      <td>Guatambú</td>
      <td>Alimentos</td>
      <td>5277.0</td>
      <td>551.0</td>
      <td>553.94</td>
      <td>0.56</td>
      <td>0.81</td>
      <td>2156.23</td>
      <td>-0.12</td>
      <td>12.90</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>2983</th>
      <td>Urussanga</td>
      <td>Borracha e plástico</td>
      <td>1744.0</td>
      <td>296.0</td>
      <td>137.43</td>
      <td>0.57</td>
      <td>0.71</td>
      <td>2494.57</td>
      <td>0.00</td>
      <td>3.15</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>1157</th>
      <td>Içara</td>
      <td>Alimentos</td>
      <td>2187.0</td>
      <td>245.0</td>
      <td>37.86</td>
      <td>0.54</td>
      <td>0.80</td>
      <td>2181.00</td>
      <td>-0.13</td>
      <td>0.82</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Abelardo Luz</td>
      <td>Alimentos</td>
      <td>2232.0</td>
      <td>244.0</td>
      <td>137.10</td>
      <td>0.56</td>
      <td>0.80</td>
      <td>2044.14</td>
      <td>-0.06</td>
      <td>3.15</td>
      <td>Expansão acelerada</td>
    </tr>
    <tr>
      <th>3075</th>
      <td>Xaxim</td>
      <td>Alimentos</td>
      <td>3026.0</td>
      <td>224.0</td>
      <td>63.89</td>
      <td>0.55</td>
      <td>0.86</td>
      <td>2146.01</td>
      <td>-0.19</td>
      <td>1.43</td>
      <td>Expansão acelerada</td>
    </tr>
  </tbody>
</table>
</div>



**Robustez:** cada alerta foi recalculado em até 48 calibrações (4 métodos × 4 volumes mínimos × 3 limiares). Cada polo entra só nas calibrações em que tem volume suficiente (12, 24, 36 ou 48). Os que ficam em alerta em **mais de 80%** das calibrações aplicáveis são tratados como **alerta robusto**.


```python
estatistica.main()
sp = pd.read_csv(P + 'est_sensibilidade_pares.csv')
alertas = sp[sp['diagnostico'].isin(['Apagão de mão de obra', 'Expansão sob pressão'])]
print(alertas['estabilidade'].value_counts())
alertas[alertas['estabilidade'] == 'Alerta robusto'].nlargest(8, 'movimentacoes')[
    ['municipio_nome', 'setor', 'diagnostico', 'movimentacoes', 'pct_pedido_demissao', 'pct_cenarios_alerta']].round(2)
```

    est_pedido_salario_escolaridade.csv            30 linhas
    est_correlacoes.csv                            50 linhas
    est_logit_pedido.csv                           10 linhas
    est_sensibilidade_cenarios.csv                 48 linhas
    est_sensibilidade_pares.csv                  3105 linhas
    est_sensibilidade_pares_regiao.csv            503 linhas
    est_sazonalidade_mensal.csv                   432 linhas
    est_sazonalidade_resumo.csv                    36 linhas
    estabilidade
    Alerta robusto    44
    Alerta frágil     26
    Name: count, dtype: int64





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>municipio_nome</th>
      <th>setor</th>
      <th>diagnostico</th>
      <th>movimentacoes</th>
      <th>pct_pedido_demissao</th>
      <th>pct_cenarios_alerta</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>14</th>
      <td>Itapiranga</td>
      <td>Alimentos</td>
      <td>Expansão sob pressão</td>
      <td>3453.0</td>
      <td>0.78</td>
      <td>1.00</td>
    </tr>
    <tr>
      <th>24</th>
      <td>Campo Alegre</td>
      <td>Veículos automotores</td>
      <td>Apagão de mão de obra</td>
      <td>2820.0</td>
      <td>0.66</td>
      <td>0.96</td>
    </tr>
    <tr>
      <th>8</th>
      <td>Sangão</td>
      <td>Veículos automotores</td>
      <td>Apagão de mão de obra</td>
      <td>2131.0</td>
      <td>0.72</td>
      <td>1.00</td>
    </tr>
    <tr>
      <th>27</th>
      <td>Timbó</td>
      <td>Vestuário e acessórios</td>
      <td>Apagão de mão de obra</td>
      <td>1751.0</td>
      <td>0.61</td>
      <td>0.94</td>
    </tr>
    <tr>
      <th>30</th>
      <td>Tijucas</td>
      <td>Vestuário e acessórios</td>
      <td>Apagão de mão de obra</td>
      <td>1452.0</td>
      <td>0.67</td>
      <td>0.92</td>
    </tr>
    <tr>
      <th>41</th>
      <td>Morro da Fumaça</td>
      <td>Vestuário e acessórios</td>
      <td>Apagão de mão de obra</td>
      <td>1305.0</td>
      <td>0.64</td>
      <td>0.90</td>
    </tr>
    <tr>
      <th>28</th>
      <td>Treze de Maio</td>
      <td>Vestuário e acessórios</td>
      <td>Apagão de mão de obra</td>
      <td>1201.0</td>
      <td>0.71</td>
      <td>0.94</td>
    </tr>
    <tr>
      <th>34</th>
      <td>Ipumirim</td>
      <td>Alimentos</td>
      <td>Apagão de mão de obra</td>
      <td>1167.0</td>
      <td>0.66</td>
      <td>0.92</td>
    </tr>
  </tbody>
</table>
</div>



## 5. Renda e escolaridade: o gargalo é diploma ou salário?


```python
ps = pd.read_csv(P + 'est_pedido_salario_escolaridade.csv')
tab = ps.pivot(index='quintil_sal', columns='faixa_esc', values='pct_pedido').round(3)
tab
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th>faixa_esc</th>
      <th>Até fundamental</th>
      <th>Médio</th>
      <th>Superior incompleto</th>
      <th>Superior ou mais</th>
      <th>Todas</th>
    </tr>
    <tr>
      <th>quintil_sal</th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
      <th></th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>Q1</th>
      <td>0.567</td>
      <td>0.563</td>
      <td>0.613</td>
      <td>0.592</td>
      <td>0.565</td>
    </tr>
    <tr>
      <th>Q2</th>
      <td>0.565</td>
      <td>0.561</td>
      <td>0.627</td>
      <td>0.644</td>
      <td>0.565</td>
    </tr>
    <tr>
      <th>Q3</th>
      <td>0.537</td>
      <td>0.547</td>
      <td>0.591</td>
      <td>0.593</td>
      <td>0.547</td>
    </tr>
    <tr>
      <th>Q4</th>
      <td>0.478</td>
      <td>0.498</td>
      <td>0.565</td>
      <td>0.554</td>
      <td>0.499</td>
    </tr>
    <tr>
      <th>Q5</th>
      <td>0.375</td>
      <td>0.391</td>
      <td>0.466</td>
      <td>0.471</td>
      <td>0.408</td>
    </tr>
    <tr>
      <th>Todas</th>
      <td>0.521</td>
      <td>0.515</td>
      <td>0.550</td>
      <td>0.511</td>
      <td>0.517</td>
    </tr>
  </tbody>
</table>
</div>




```python
fig, ax = plt.subplots(1, 2, figsize=(12, 4), sharey=True)
q = ps[(ps.faixa_esc == 'Todas') & (ps.quintil_sal != 'Todas')]
ax[0].bar(q['quintil_sal'], q['pct_pedido'] * 100, color=['#EF4444', '#EF4444', '#F97316', '#60A5FA', '#2563EB'])
ax[0].set_title('% de saídas a pedido por faixa salarial'); ax[0].set_ylabel('%')
e = ps[(ps.quintil_sal == 'Todas') & (ps.faixa_esc != 'Todas')]
ax[1].bar(e['faixa_esc'], e['pct_pedido'] * 100, color='#8B5CF6')
ax[1].set_title('% de saídas a pedido por escolaridade'); ax[1].tick_params(axis='x', rotation=15)
plt.tight_layout()
```


    
![png](raio_x_industria_sc_files/raio_x_industria_sc_29_0.png)
    



```python
pd.read_csv(P + 'est_logit_pedido.csv')[['termo', 'razao_chance', 'ic95_inf', 'ic95_sup', 'p_valor', 'razao_chance_10pct']].round(3)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>termo</th>
      <th>razao_chance</th>
      <th>ic95_inf</th>
      <th>ic95_sup</th>
      <th>p_valor</th>
      <th>razao_chance_10pct</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>faixa_esc = Médio</td>
      <td>1.050</td>
      <td>1.007</td>
      <td>1.095</td>
      <td>0.023</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>1</th>
      <td>faixa_esc = Superior incompleto</td>
      <td>1.345</td>
      <td>1.241</td>
      <td>1.458</td>
      <td>0.000</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>2</th>
      <td>faixa_esc = Superior ou mais</td>
      <td>1.585</td>
      <td>1.456</td>
      <td>1.727</td>
      <td>0.000</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>3</th>
      <td>faixa_idade = 14-24</td>
      <td>1.095</td>
      <td>1.052</td>
      <td>1.140</td>
      <td>0.000</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>4</th>
      <td>faixa_idade = 25-29</td>
      <td>1.026</td>
      <td>0.987</td>
      <td>1.066</td>
      <td>0.198</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>5</th>
      <td>faixa_idade = 40-49</td>
      <td>0.947</td>
      <td>0.909</td>
      <td>0.987</td>
      <td>0.011</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>6</th>
      <td>faixa_idade = 50+</td>
      <td>0.840</td>
      <td>0.785</td>
      <td>0.900</td>
      <td>0.000</td>
      <td>NaN</td>
    </tr>
    <tr>
      <th>7</th>
      <td>log_sal_cbo</td>
      <td>0.417</td>
      <td>0.360</td>
      <td>0.482</td>
      <td>0.000</td>
      <td>0.920</td>
    </tr>
    <tr>
      <th>8</th>
      <td>sal_rel_cbo</td>
      <td>0.495</td>
      <td>0.459</td>
      <td>0.535</td>
      <td>0.000</td>
      <td>0.935</td>
    </tr>
    <tr>
      <th>9</th>
      <td>mulher</td>
      <td>1.103</td>
      <td>1.062</td>
      <td>1.146</td>
      <td>0.000</td>
      <td>NaN</td>
    </tr>
  </tbody>
</table>
</div>



**Leitura:** nas faixas salariais mais baixas (Q1–Q2) 57% das saídas são pedidos; na mais alta (Q5), 41%. Por escolaridade a taxa fica entre 51% e 55%. Na regressão logística (controles: setor, porte, idade, sexo; erros agrupados por CBO), **salário 10% acima da mediana da mesma ocupação está associado a odds ~6,5% menores de a saída ser a pedido** (razão de chances 0,935), e ensino superior a odds 59% maiores (o profissional qualificado é disputado). Como a amostra é de desligados, isso fala das odds de a saída ser a pedido, não da probabilidade de um empregado sair, e indica associação, não causa. Entre os 538 polos município × setor, salário de entrada e % a pedido têm correlação de Spearman de −0,38, e a % de admitidos só com fundamental, de +0,40.


```python
pd.read_csv(P + 'est_correlacoes.csv').query("nivel == 'municipio_setor'")[['var_x', 'var_y', 'rho', 'p_valor', 'n']].round(3)
```




<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>var_x</th>
      <th>var_y</th>
      <th>rho</th>
      <th>p_valor</th>
      <th>n</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>6</th>
      <td>salario_mediano_adm</td>
      <td>pct_pedido_demissao</td>
      <td>-0.376</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>7</th>
      <td>salario_mediano_adm</td>
      <td>indice_pressao</td>
      <td>-0.295</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>8</th>
      <td>salario_mediano_adm</td>
      <td>premio_salarial</td>
      <td>-0.007</td>
      <td>0.876</td>
      <td>537</td>
    </tr>
    <tr>
      <th>9</th>
      <td>salario_mediano_adm</td>
      <td>saldo_10k_hab</td>
      <td>0.057</td>
      <td>0.184</td>
      <td>538</td>
    </tr>
    <tr>
      <th>10</th>
      <td>pct_superior_adm</td>
      <td>pct_pedido_demissao</td>
      <td>-0.309</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>11</th>
      <td>pct_superior_adm</td>
      <td>indice_pressao</td>
      <td>-0.283</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>12</th>
      <td>pct_superior_adm</td>
      <td>premio_salarial</td>
      <td>-0.114</td>
      <td>0.008</td>
      <td>537</td>
    </tr>
    <tr>
      <th>13</th>
      <td>pct_superior_adm</td>
      <td>saldo_10k_hab</td>
      <td>0.007</td>
      <td>0.870</td>
      <td>538</td>
    </tr>
    <tr>
      <th>14</th>
      <td>pct_ate_fundamental_adm</td>
      <td>pct_pedido_demissao</td>
      <td>0.400</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>15</th>
      <td>pct_ate_fundamental_adm</td>
      <td>indice_pressao</td>
      <td>0.226</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>16</th>
      <td>pct_ate_fundamental_adm</td>
      <td>premio_salarial</td>
      <td>-0.056</td>
      <td>0.192</td>
      <td>537</td>
    </tr>
    <tr>
      <th>17</th>
      <td>pct_ate_fundamental_adm</td>
      <td>saldo_10k_hab</td>
      <td>0.074</td>
      <td>0.085</td>
      <td>538</td>
    </tr>
    <tr>
      <th>18</th>
      <td>idade_media_adm</td>
      <td>pct_pedido_demissao</td>
      <td>-0.235</td>
      <td>0.000</td>
      <td>538</td>
    </tr>
    <tr>
      <th>19</th>
      <td>idade_media_adm</td>
      <td>indice_pressao</td>
      <td>-0.007</td>
      <td>0.863</td>
      <td>538</td>
    </tr>
    <tr>
      <th>20</th>
      <td>idade_media_adm</td>
      <td>premio_salarial</td>
      <td>0.244</td>
      <td>0.000</td>
      <td>537</td>
    </tr>
    <tr>
      <th>21</th>
      <td>idade_media_adm</td>
      <td>saldo_10k_hab</td>
      <td>-0.069</td>
      <td>0.108</td>
      <td>538</td>
    </tr>
  </tbody>
</table>
</div>



## 6. Exportação final
O pipeline grava os indicadores em `data/processed/`, lidos pelo painel Streamlit, e o JSON em `data/processed/api/`.


```python
exportar.main()
sorted(p.name for p in pipeline.OUT.glob('*.csv'))
```

    api/cubo.json                                      5546 linhas
    api/salario_hist.json                             19373 linhas
    api/escolaridade_cubo.json                         1246 linhas
    api/est_correlacoes.json                             50 linhas
    api/est_logit_pedido.json                            10 linhas
    api/est_pedido_salario_escolaridade.json             30 linhas
    api/est_sazonalidade_mensal.json                    432 linhas
    api/est_sazonalidade_resumo.json                     36 linhas
    api/est_sensibilidade_cenarios.json                  48 linhas
    api/est_sensibilidade_pares.json                   3105 linhas
    api/est_sensibilidade_pares_regiao.json             503 linhas
    api/ind_macrofamilia.json                            17 linhas
    api/ind_municipio.json                              294 linhas
    api/ind_municipio_setor.json                       3105 linhas
    api/ind_regiao_macrofamilia.json                    119 linhas
    api/ind_regiao_setor.json                           503 linhas
    api/log_limpeza.json                                  6 linhas
    api/municipios.json                                 295 linhas
    api/validacao_schema.json                            18 linhas





    ['est_correlacoes.csv',
     'est_logit_pedido.csv',
     'est_pedido_salario_escolaridade.csv',
     'est_sazonalidade_mensal.csv',
     'est_sazonalidade_resumo.csv',
     'est_sensibilidade_cenarios.csv',
     'est_sensibilidade_pares.csv',
     'est_sensibilidade_pares_regiao.csv',
     'ind_macrofamilia.csv',
     'ind_municipio.csv',
     'ind_municipio_setor.csv',
     'ind_regiao_macrofamilia.csv',
     'ind_regiao_setor.csv',
     'log_limpeza.csv',
     'municipios.csv',
     'validacao_schema.csv']



## 6b. Acionamento de parceiros (regras de negócio)
Para cada polo com alerta ou expansão, `dashboard/acionamento.py` escolhe **um** parceiro principal para a FIESC acionar, com a justificativa tirada dos indicadores:
- **Alerta frágil** → só monitorar;
- **Alerta robusto com salário de entrada 3%+ abaixo da mediana do setor** → empresas do polo (revisar piso);
- **Alerta robusto com salário na média** → Awtra (integração, compliance e lideranças);
- **Expansão acelerada com +200 vagas** → UniSENAI (formar para a família de ocupações mais contratada);
- **Foco:** no máximo 6 alertas robustos (mais saídas a pedido/ano) e 4 expansões (maior saldo) recebem parceiro; os demais vão para a fila de monitoramento;
- **Secundário:** setor eletrointensivo crescendo +500 vagas → Way2 (eficiência energética).


```python
sys.path.insert(0, '../dashboard')
import acionamento
rs = pd.read_csv(P + 'ind_municipio_setor.csv').merge(
    pd.read_csv(P + 'est_sensibilidade_pares.csv')[['cod_ibge', 'setor', 'estabilidade', 'pct_cenarios_alerta']],
    on=['cod_ibge', 'setor'], how='left')
rs['robusto'] = rs['diagnostico'].isin(acionamento.ALERTAS) & (rs['estabilidade'] == 'Alerta robusto')
ac = acionamento.calcular(ind, rs)
print(ac['parceiro'].value_counts().to_string()); print('Way2 (secundário):', (ac['secundario'] == 'Way2').sum())
ac[ac['parceiro'] != 'Monitorar'][['setor', 'municipio_nome', 'diagnostico', 'parceiro', 'familia_ia', 'porque']].head(10)
```

    parceiro
    Monitorar           116
    Awtra                 4
    UniSENAI              4
    Empresas do polo      2
    Way2 (secundário): 2





<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>setor</th>
      <th>municipio_nome</th>
      <th>diagnostico</th>
      <th>parceiro</th>
      <th>familia_ia</th>
      <th>porque</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>0</th>
      <td>Alimentos</td>
      <td>Itapiranga</td>
      <td>Expansão sob pressão</td>
      <td>Awtra</td>
      <td>Produção de Base (Linha e Embalagem)</td>
      <td>O salário já está na média do setor (R$ 2.084)...</td>
    </tr>
    <tr>
      <th>1</th>
      <td>Veículos automotores</td>
      <td>Campo Alegre</td>
      <td>Apagão de mão de obra</td>
      <td>Empresas do polo</td>
      <td>Metalmecânica e Montagem</td>
      <td>Salário de entrada de R$ 2.000, 8% abaixo da m...</td>
    </tr>
    <tr>
      <th>2</th>
      <td>Veículos automotores</td>
      <td>Sangão</td>
      <td>Apagão de mão de obra</td>
      <td>Awtra</td>
      <td>Metalmecânica e Montagem</td>
      <td>O salário já está na média do setor (R$ 2.413)...</td>
    </tr>
    <tr>
      <th>3</th>
      <td>Vestuário e acessórios</td>
      <td>Timbó</td>
      <td>Apagão de mão de obra</td>
      <td>Awtra</td>
      <td>Têxtil, Vestuário, Couro e Calçados</td>
      <td>O salário já está na média do setor (R$ 2.300)...</td>
    </tr>
    <tr>
      <th>4</th>
      <td>Vestuário e acessórios</td>
      <td>Tijucas</td>
      <td>Apagão de mão de obra</td>
      <td>Awtra</td>
      <td>Têxtil, Vestuário, Couro e Calçados</td>
      <td>O salário já está na média do setor (R$ 2.200)...</td>
    </tr>
    <tr>
      <th>5</th>
      <td>Vestuário e acessórios</td>
      <td>Treze de Maio</td>
      <td>Apagão de mão de obra</td>
      <td>Empresas do polo</td>
      <td>Têxtil, Vestuário, Couro e Calçados</td>
      <td>Salário de entrada de R$ 1.837, 12% abaixo da ...</td>
    </tr>
    <tr>
      <th>6</th>
      <td>Veículos automotores</td>
      <td>Navegantes</td>
      <td>Expansão acelerada</td>
      <td>UniSENAI</td>
      <td>Produção de Base (Linha e Embalagem)</td>
      <td>O polo criou +1.620 vagas em 12 meses; a famíl...</td>
    </tr>
    <tr>
      <th>7</th>
      <td>Alimentos</td>
      <td>Chapecó</td>
      <td>Expansão acelerada</td>
      <td>UniSENAI</td>
      <td>Agroindústria e Alimentos</td>
      <td>O polo criou +1.273 vagas em 12 meses; a famíl...</td>
    </tr>
    <tr>
      <th>8</th>
      <td>Outros equip. de transporte</td>
      <td>Navegantes</td>
      <td>Expansão acelerada</td>
      <td>UniSENAI</td>
      <td>Produção de Base (Linha e Embalagem)</td>
      <td>O polo criou +625 vagas em 12 meses; a família...</td>
    </tr>
    <tr>
      <th>9</th>
      <td>Alimentos</td>
      <td>Guatambú</td>
      <td>Expansão acelerada</td>
      <td>UniSENAI</td>
      <td>Agroindústria e Alimentos</td>
      <td>O polo criou +551 vagas em 12 meses; a família...</td>
    </tr>
  </tbody>
</table>
</div>



## 7. Conclusões, recomendações e limites
1. **A indústria gira o quadro mas não cresce:** 835.776 movimentações para +1.098 vagas, ou 761 movimentações por vaga criada.
2. **Os sinais de pressão estão na retenção:** 51% das saídas são pedidos do trabalhador. Dos 538 polos município × setor analisados, **44 estão em alerta robusto** (mais de 80% das calibrações aplicáveis), liderados por alimentos em Itapiranga (78% a pedido), veículos em Campo Alegre e Sangão e vestuário em Timbó, Tijucas, Morro da Fumaça e Treze de Maio.
3. **Expansão concentrada:** veículos/equipamentos de transporte em Navegantes (+1.620 e +625) e alimentos em Chapecó (+1.273) e Guatambú (+551).
4. **Remuneração e escolaridade:** a proporção de saídas a pedido cai de 57% para 41% do menor ao maior salário e varia pouco por escolaridade na comparação descritiva; com controles, o ensino superior aparece associado a mais pedidos.
5. **IA:** Agroindústria e Alimentos, Produção de Base e Têxtil/Vestuário perdem 55–60% por pedido e pagam ~R\$ 2,1 mil na entrada.

**Recomendações (FIESC como hub):** UniSENAI com formação nos polos em expansão; empresas do polo revendo piso onde o salário de entrada está abaixo do setor; Awtra com integração e lideranças onde o salário está na média e a rotatividade segue alta (hipótese a validar com as empresas); Way2 como apoio em polos eletrointensivos que crescem.

**Limites:** só as bases do desafio entram no diagnóstico; o CAGED mede fluxo, não vagas abertas, então "apagão" é indício de pressão, não prova de falta de profissionais; só a base MOV foi fornecida; correlação e regressão indicam associação, não causalidade.

## Apêndice bônus: fontes externas (fora das regras do desafio)
Esta seção **não entra no diagnóstico nem nos indicadores principais**. Ela mostra o que muda ao cruzar os mesmos dados com as regiões geográficas imediatas e intermediárias do IBGE (2017), arquivo `data/externos/regioes_ibge.csv`. Se o arquivo for removido, o pipeline roda normalmente e esta célula é pulada.


```python
from pathlib import Path
if Path(P + 'ind_regiao_setor.csv').exists():
    rr = pd.read_csv(P + 'est_sensibilidade_pares_regiao.csv')
    rr = rr[rr['diagnostico'].isin(['Apagão de mão de obra', 'Expansão sob pressão']) & (rr['estabilidade'] == 'Alerta robusto')]
    print(len(rr), 'polos região imediata × setor em alerta robusto (visão bônus)')
    display(rr.nlargest(8, 'movimentacoes')[['regiao_imediata', 'setor', 'movimentacoes', 'pct_pedido_demissao']].round(2))
else:
    print('Fontes externas ausentes: apêndice não executado.')
```

    16 polos região imediata × setor em alerta robusto (visão bônus)



<div>
<style scoped>
    .dataframe tbody tr th:only-of-type {
        vertical-align: middle;
    }

    .dataframe tbody tr th {
        vertical-align: top;
    }

    .dataframe thead th {
        text-align: right;
    }
</style>
<table border="1" class="dataframe">
  <thead>
    <tr style="text-align: right;">
      <th></th>
      <th>regiao_imediata</th>
      <th>setor</th>
      <th>movimentacoes</th>
      <th>pct_pedido_demissao</th>
    </tr>
  </thead>
  <tbody>
    <tr>
      <th>18</th>
      <td>Joaçaba - Herval d'Oeste</td>
      <td>Alimentos</td>
      <td>12233.0</td>
      <td>0.68</td>
    </tr>
    <tr>
      <th>9</th>
      <td>Ibirama - Presidente Getúlio</td>
      <td>Vestuário e acessórios</td>
      <td>6596.0</td>
      <td>0.72</td>
    </tr>
    <tr>
      <th>12</th>
      <td>São Bento do Sul - Rio Negrinho</td>
      <td>Veículos automotores</td>
      <td>3671.0</td>
      <td>0.63</td>
    </tr>
    <tr>
      <th>8</th>
      <td>Tubarão</td>
      <td>Veículos automotores</td>
      <td>2398.0</td>
      <td>0.68</td>
    </tr>
    <tr>
      <th>17</th>
      <td>Caçador</td>
      <td>Couro e calçados</td>
      <td>1294.0</td>
      <td>0.70</td>
    </tr>
    <tr>
      <th>11</th>
      <td>Ituporanga</td>
      <td>Vestuário e acessórios</td>
      <td>1139.0</td>
      <td>0.64</td>
    </tr>
    <tr>
      <th>2</th>
      <td>São Bento do Sul - Rio Negrinho</td>
      <td>Produtos diversos</td>
      <td>778.0</td>
      <td>0.56</td>
    </tr>
    <tr>
      <th>13</th>
      <td>Araranguá</td>
      <td>Máquinas e equipamentos</td>
      <td>743.0</td>
      <td>0.48</td>
    </tr>
  </tbody>
</table>
</div>

