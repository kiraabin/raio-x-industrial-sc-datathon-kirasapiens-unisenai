<div align="center">

# Raio-X do Mercado de Trabalho de Santa Catarina

**Datathon CDIA 2026 · UniSENAI**

Desafio prático de análise de dados e inteligência artificial, Bacharelado em Ciência de Dados e IA.

![Status](https://img.shields.io/badge/status-em%20andamento-blue)
![Python](https://img.shields.io/badge/python-3.11%2B-informational)
![Dados](https://img.shields.io/badge/dados-Novo%20CAGED-informational)
![Região](https://img.shields.io/badge/regi%C3%A3o-SC-success)
</div>

---

## Pergunta central

> Quais regiões e setores industriais de SC enfrentam **apagão de mão de obra** ou **expansão acelerada**,
> e como **renda** e **escolaridade** explicam esses gargalos?

---

## Equipe

| Integrante | Papel | Responsável por |
|---|---|---|
| Samuel | Product Owner | Pergunta de negócio, recomendações, slides do pitch e hospedagem (Replit, se necessário) |
| Filipe | Visualização de dados | Evolução do dashboard (`dashboard/app.py`), em especial as visualizações de raio/círculo (bolhas) e os mapas de calor |
| Vinicius | Backend, estatística e QA | Insights estatísticos (`backend/indicadores.py`, notebook) e testes finais de todo o projeto |
| Guilherme | Front e Git | Frontend em React (`frontend/`), controle de versão e documentação |
| Bernardo | Front e Git | Frontend em React (`frontend/`), controle de versão e otimização |

**Stack:** frontend da aplicação em React (JavaScript); dados, IA e dashboard em Python, com pandas e pyarrow (dados), Plotly e Streamlit (dashboard), Jupyter (notebook) e o SDK da Anthropic (agrupamento de CBOs por IA).

---

## Principais achados

| # | Achado | Evidência |
|---|---|---|
| 1 | **A indústria girou o quadro sem crescer** | 835.776 movimentações na indústria de transformação em 12 meses para um saldo de apenas **+1.098** vagas |
| 2 | **O crescimento é operacional e se concentra no Oeste e em Itajaí** | A região intermediária de Chapecó soma +3.748 vagas, e as regiões imediatas de Itajaí (+2.558) e Chapecó (+2.351) lideram. Ocupações operacionais: +6.326. Técnicos: −2.729, gestão: −1.699, nível superior: −800 |
| 3 | **O apagão é de retenção, não de diploma** | Agroindústria, produção de base, têxtil e vestuário: cerca de 55 a 60% dos desligamentos são **a pedido** do trabalhador, salário de admissão de R$ 2,0 a 2,2 mil e menos de 2% dos admitidos com ensino superior |
| 4 | **16 polos em alerta robusto** | Dos 26 pares região × setor em alerta no cenário padrão, 16 se mantêm em pelo menos 80% das 36 calibrações testadas. Os maiores: alimentos em Joaçaba, vestuário em Ibirama e Ituporanga, veículos em São Bento do Sul e Tubarão, couro e calçados em Caçador |
| 5 | **Salário segura; diploma, não** | Quem ganha até ~R$ 2 mil pede demissão em 57% das saídas; acima de ~R$ 3,6 mil, em 41%. Entre escolaridades, a taxa fica entre 51% e 55%. Pagar 10% acima da mediana da ocupação reduz em ~6% a chance de pedido de demissão (regressão logística, 391 mil desligamentos) |
| 6 | **Polos em expansão acelerada** | Alimentos em Chapecó, Concórdia, Xanxerê e Criciúma; têxtil em Brusque; máquinas e materiais elétricos em Joinville e Blumenau; veículos e equipamentos de transporte em Itajaí |

---

## Painel analítico (Python)

O entregável oficial é o **painel de inteligência de mão de obra da FIESC** em Streamlit (`dashboard/app.py`).
Filtros globais por região intermediária e setor industrial; 6 abas:

| Aba | O que mostra |
|---|---|
| Visão geral | 5 KPIs (saldo e saldo por 10 mil hab., movimentações, % de saídas a pedido, salário de entrada, polos em alerta), insights automáticos, mapa com raios por município, prioridades da FIESC e saldo mensal |
| Polos e diagnóstico | Matriz Índice de Pressão × Índice de Expansão, contagem por diagnóstico, robustez dos alertas e tabela completa dos polos |
| Renda e escolaridade | % de saídas a pedido por faixa salarial e por escolaridade, dispersão salário × saída a pedido por polo e efeitos da regressão logística |
| Macrofamílias (IA) | As famílias de ocupações (LLM) que mais perdem gente, salário de entrada e mapa de calor família × região |
| Acionamento de parceiros | Um parceiro principal por polo (UniSENAI, Awtra ou empresas do polo; Way2 como secundário), escolhido por regra e com a justificativa tirada dos dados (`dashboard/acionamento.py`) |
| Dados e método | Volumetria, validação de schema contra o dicionário, premissas e limites |

Visual: base branca com azul, letras grandes e cores vivas nos gráficos (`.streamlit/config.toml`, `dashboard/tema.py`).

---

## O que o desafio pede

| Eixo | Descrição |
|:---:|:---:|
| Visão territorial | Mapear os polos industriais e analisar a rotatividade por região |
| Agrupamento por IA | Categorizar os CBOs (ocupações) em macro famílias |
| Data storytelling | Dashboard executivo com recomendações práticas e acionáveis |

---

## Entregáveis

| Item | Status |
|:---:|:---:|
| Scripts ou notebook da análise | pendente |
| Painel analítico (dashboard) | pendente |
| Pitch de 3 minutos em slides | pendente |

Todas as entregas saem deste repositório Git público.

---

## Cronograma

| Data | Horário | Etapa |
|:---:|:---:|:---:|
| 10/11 | 10:00 - 11:40 | Montagem dos grupos e início do desenvolvimento |
| 13/11 | 08:30 - 09:50 | Elaboração dos pitches |
| 13/11 | 10:00 - 11:40 | Apresentação dos pitches (3 min) para a banca |

Grupos de 5 estudantes (2ª e 4ª fase). Banca formada por especialistas de empresas parceiras.

---

## Dados

Ficam em `raw/`.

O `Novo_Caged_MOV_Limpo.csv` (~413 MB) passa do limite de 100 MB por arquivo do GitHub, então não está neste repositório. Baixe no Kaggle:

**[Caged MOV Limpo no Kaggle](https://www.kaggle.com/datasets/guilhermeanselmo/caged-mov-limpo/data)**

Coloque o arquivo baixado em `raw/Novo_Caged_MOV_Limpo.csv`.

| Arquivo | Conteúdo |
|:---:|:---:|
| `Novo_Caged_MOV_Limpo.csv` | Movimentações de emprego em SC nos últimos 12 meses (~3,4 milhões de linhas, separador `;`). Baixar do Kaggle |
| `Municipios_SC_limpo.csv` | Dados demográficos e socioeconômicos dos 295 municípios de SC |
| `Dicionario_de_dados.xlsx` | Documentação das variáveis das bases |

---

## Estrutura

| Pasta | Conteúdo |
|:---:|:---:|
| `docs/` | Material do evento (slides do desafio e Guia do Participante) |
| `raw/` | Dados brutos fornecidos (o CAGED fica fora do Git) |
| `backend/` | Pipeline em Python: `main.py` (ponto de entrada, por etapas), `validacao.py` (schema, domínios do dicionário e exclusões MOV × EXC), `pipeline.py` (carga, limpeza, junção e exportação), `indicadores.py` (indicadores e diagnóstico), `estatistica.py` (renda × escolaridade × pedido, sensibilidade do Índice de Pressão e sazonalidade), `exportar.py` (JSON para o frontend em `data/processed/api/`), `cbo_llm.py` (IA para as CBOs: exporta a amostra e o prompt, chama a API ou importa a resposta do LLM) |
| `tests/` | Testes de consistência do backend (`pytest tests/`) |
| `frontend/` | Frontend da aplicação em React (JavaScript) |
| `dashboard/` | Painel analítico em Python (Streamlit), entregável oficial: `app.py` (abas do painel), `dados.py` (carga e agregações), `insights.py` (insights automáticos), `acionamento.py` (regras de acionamento de parceiros), `tema.py` (identidade visual) |
| `data/` | Apoio: regiões do IBGE, malha municipal, macrofamílias de CBO, `ia/` (prompt, amostra de subgrupos e resposta do LLM) e `processed/` (saídas do pipeline, incluindo `validacao_schema.csv`) |
| `notebooks/` | Notebook documentado (`raio_x_industria_sc.ipynb`, com versão `.md`) cobrindo ingestão e validação, cruzamento com o IBGE, IA, indicadores, renda × escolaridade e exportação |

---

## Como rodar

```bash
pip install -r requirements.txt

# 1. Gere os dados do dashboard (pipeline -> estatística -> exportação JSON).
#    Com o Novo_Caged_MOV_Limpo.csv em raw/ (link em "Dados") o pipeline roda do zero;
#    sem ele, a etapa é pulada e as demais usam o industria.parquet versionado.
python backend/main.py
python backend/main.py estatistica exportar   # só algumas etapas

# Testes de consistência
pytest tests/

# 2. Abra o painel (funciona mesmo sem o CSV bruto, porque lê data/processed/)
streamlit run dashboard/app.py      # abre em http://localhost:8501
```

---

## Metodologia

**Limpeza** (volumetria em `data/processed/log_limpeza.csv`)
- 3.397.416 registros → janela de 12 competências (set/2025 a ago/2026) → remoção de categorias e movimentações não identificadas → **835.776 movimentações na indústria de transformação** (CNAE seção C).
- Salário só entra nas comparações se estiver entre R$ 800 e R$ 60 mil, com jornada de pelo menos 30h e sem contratos intermitentes, de aprendiz ou parciais.

**Junção territorial**
- O código de município do CAGED tem 6 dígitos, e o do IBGE tem 7. A junção usa `cod_ibge // 10`.
- As regiões são as **7 intermediárias e 24 imediatas** oficiais do IBGE.
- A população é a estimativa do IBGE para 2026.

**Agrupamento de CBOs por IA**
- Os 1.467 CBOs presentes na indústria pertencem a 177 subgrupos. Para cada subgrupo, um LLM (Claude) recebeu os títulos das ocupações mais frequentes e classificou o subgrupo em uma de **16 macrofamílias** fechadas.
- O prompt e o código para regenerar a classificação via API estão em `backend/cbo_llm.py`. O resultado foi revisado pela equipe.

**Indicadores**

| Indicador | Definição |
|---|---|
| Saldo por 10 mil hab. | (admissões − desligamentos) ÷ população × 10.000 |
| % desligamentos a pedido | desligamentos do tipo 40 ÷ total de desligamentos |
| Índice de reposição | desligamentos ÷ admissões |
| Prêmio salarial ajustado | média, ponderada pelas admissões, de log(mediana da admissão ÷ mediana do desligamento) **dentro da mesma CBO** |
| **Índice de pressão (apagão)** | média dos z-scores dos três indicadores acima |
| **Índice de expansão** | z-score do saldo por 10 mil hab. |

**Diagnóstico** (aplicado a recortes com pelo menos 300 movimentações):
- pressão ≥ 0,5 → *Apagão*
- expansão ≥ 0,5 → *Expansão acelerada*
- ambos ≥ 0,5 → *Expansão sob pressão*
- expansão ≤ −0,5 → *Retração*
- demais casos → *Estável*

---

## Dicionário estatístico

Saídas de `backend/estatistica.py`, gravadas em `data/processed/est_*.csv` e espelhadas em JSON em `data/processed/api/`.
Geradas com `python backend/main.py estatistica exportar`, sem precisar do CSV bruto.

**Convenções:** colunas `pct_*` são proporções de 0 a 1, não percentuais. `mes` está no formato `dez/25`.
Recortes com menos de 300 movimentações ficam fora das correlações e dos rankings.

### 1. Renda, escolaridade e desligamento a pedido

Base: 391 mil desligamentos com salário válido e escolaridade conhecida.

**`est_pedido_salario_escolaridade.csv`**: taxa de pedido por quintil de salário × faixa de escolaridade. As linhas com `Todas` são os totais de cada linha e coluna.

| Coluna | Descrição |
|---|---|
| `quintil_sal` | `Q1` (menor salário) a `Q5`, ou `Todas` |
| `faixa_esc` | `Até fundamental`, `Médio`, `Superior incompleto`, `Superior ou mais` ou `Todas` |
| `desligamentos`, `a_pedido` | Contagens da célula |
| `pct_pedido` | `a_pedido ÷ desligamentos` |
| `salario_mediano`, `salario_min`, `salario_max` | Salário do desligado na célula (R$) |

Uso sugerido: mapa de calor com `quintil_sal` nas linhas, `faixa_esc` nas colunas e `pct_pedido` na cor, sem as células `Todas`.

**`est_correlacoes.csv`**: correlações de Spearman em formato longo (uma linha por par de variáveis).

| Coluna | Descrição |
|---|---|
| `nivel` | `desligamento` (microdado), `regiao_setor` (pares região imediata × setor) ou `municipio` |
| `var_x`, `var_y` | Variáveis comparadas (ver abaixo) |
| `rho` | Correlação de Spearman, de −1 a 1 |
| `p_valor`, `significativo_5pct` | Teste de significância (`p < 0,05`) |
| `n` | Observações usadas |

Variáveis do nível `desligamento`:

| Variável | Descrição |
|---|---|
| `ped` | 1 = a pedido |
| `salario` | Salário do desligado |
| `anos_estudo` | Escolaridade aproximada em anos |
| `log_sal_cbo` | Quanto a ocupação paga (log da mediana da CBO) |
| `sal_rel_cbo` | Quanto o trabalhador ganhava acima ou abaixo da mediana da CBO (em log) |
| `idade` | Idade do desligado |

Nos níveis agregados, as variáveis vêm de `ind_regiao_setor.csv` e `ind_municipio.csv`. No nível `municipio` entram também `idhm_2010`, `pib_per_capita_2023` e `escolarizacao_6_14`.

No microdado o `n` é tão grande que quase tudo dá significativo: leia o tamanho do `rho`, não o p-valor.

**`est_logit_pedido.csv`**: regressão logística da chance de um desligamento ser a pedido.
Controla setor, região imediata, porte do estabelecimento, faixa etária e sexo, com erros-padrão agrupados por CBO.

| Coluna | Descrição |
|---|---|
| `termo` | Variável do modelo. Categorias aparecem como `faixa_esc = Superior ou mais`; a referência é `Até fundamental` (escolaridade) e `30-39` (idade) |
| `coef` | Coeficiente em log-odds |
| `razao_chance` | `exp(coef)`. Acima de 1 aumenta a chance de pedir demissão; abaixo de 1 reduz |
| `ic95_inf`, `ic95_sup` | Intervalo de confiança de 95% da razão de chance |
| `p_valor` | Significância |
| `razao_chance_10pct` | Só em `log_sal_cbo` e `sal_rel_cbo`: efeito de um salário 10% maior |
| `n`, `pseudo_r2` | Tamanho da amostra e ajuste do modelo (McFadden) |

Leitura:
- Um salário 10% maior reduz a chance de pedir demissão. O efeito é de cerca de 8% quando vem da ocupação (`log_sal_cbo` = 0,92) e de cerca de 6% quando o trabalhador ganha acima dos colegas da mesma CBO (`sal_rel_cbo` = 0,94).
- Com salário igual, quem tem superior tem 1,67 vez a chance de pedir demissão de quem tem até o fundamental.
- O pseudo-R² de 0,03 mostra que a decisão individual depende de fatores que a base não tem, como o tempo de casa.

### 2. Sensibilidade do Índice de Pressão

O diagnóstico é refeito em 48 cenários, combinando:
- **4 métodos de cálculo da pressão:**
  - `atual`: o padrão do projeto;
  - `sem_reposicao`: tira o índice de reposição, que é quase o inverso do saldo (ρ ≈ −0,9);
  - `winsor`: limita os componentes aos percentis 1 e 99;
  - `robusto`: usa mediana e MAD no lugar de média e desvio-padrão.
- **4 volumes mínimos:** 200, 300, 500 e 1.000 movimentações.
- **3 limiares:** 0,3, 0,5 e 0,7.

O método altera só a pressão; a expansão fica igual em todos os cenários.

**`est_sensibilidade_cenarios.csv`**: uma linha por cenário.

| Coluna | Descrição |
|---|---|
| `metodo`, `min_mov`, `limiar` | Parâmetros do cenário |
| `padrao` | `True` no cenário usado pelo projeto (`atual`, 300, 0,5) |
| `Apagão de mão de obra` … `Volume insuficiente` | Quantidade de pares região × setor em cada diagnóstico |
| `alertas` | Apagão + Expansão sob pressão |

**`est_sensibilidade_pares.csv`**: uma linha por par região imediata × setor (503 pares).

| Coluna | Descrição |
|---|---|
| `regiao_imediata`, `setor` | Chave do par |
| `movimentacoes`, `saldo`, `pct_pedido_demissao`, `premio_salarial`, `indice_reposicao` | Indicadores do par (iguais a `ind_regiao_setor.csv`) |
| `indice_pressao`, `diagnostico` | Resultado no cenário padrão |
| `indice_pressao_sem_reposicao`, `diagnostico_sem_reposicao` | Resultado no método `sem_reposicao` (volume e limiar padrão) |
| `cenarios_avaliados` | Em quantos cenários o par teve volume suficiente |
| `cenarios_alerta`, `pct_cenarios_alerta` | Em quantos (e em que proporção) deles o par ficou em alerta |
| `estabilidade` | Classificação do alerta (ver abaixo) |

Valores de `estabilidade`:

| Valor | Proporção de cenários em alerta |
|---|---|
| `Alerta robusto` | Mais de 80% |
| `Alerta frágil` | Entre 20% e 80% |
| `Alerta raro` | Até 20% |
| `Nunca em alerta` | Nenhum |
| `Sem volume` | Par com menos de 300 movimentações |

Uso sugerido: no pitch e no mapa de calor, destaque só os `Alerta robusto`. O 1º lugar em pressão no cenário padrão (Mafra × Veículos) é `Alerta frágil`: é uma retração (12 admissões, 297 desligamentos, 5% a pedido), não falta de mão de obra.

### 3. Sazonalidade

A base cobre só 12 meses, então isto é o perfil dentro do ano, não uma decomposição de sazonalidade e tendência.

**`est_sazonalidade_mensal.csv`**: fluxo mensal em formato longo.

| Coluna | Descrição |
|---|---|
| `recorte_tipo` | `total`, `setor`, `regiao_intermediaria` ou `nivel_ocupacao` |
| `recorte` | Valor do recorte (ex.: `Alimentos`, `Chapecó`). No `total`: `Indústria de transformação` |
| `competênciamov`, `mes` | Competência (`202512`) e rótulo (`dez/25`) |
| `admissoes`, `desligamentos`, `saldo`, `movimentacoes` | Fluxo do mês |
| `saldo_acumulado` | Soma do saldo desde set/2025 |
| `saldo_sobre_fluxo_medio` | Saldo do mês ÷ movimentações médias mensais do recorte. Serve para comparar recortes de tamanhos diferentes |
| `a_pedido`, `pct_pedido` | Desligamentos a pedido no mês |
| `termino_contrato`, `pct_termino_contrato` | Fim de contrato por prazo determinado (temporários) |
| `salario_mediano_adm` | Salário mediano de admissão no mês |

**`est_sazonalidade_resumo.csv`**: uma linha por recorte.

| Coluna | Descrição |
|---|---|
| `saldo_anual`, `movimentacoes_anuais` | Totais dos 12 meses |
| `mes_pico`, `saldo_pico`, `mes_vale`, `saldo_vale` | Melhor e pior mês de saldo |
| `amplitude_relativa` | Diferença entre o maior e o menor `saldo_sobre_fluxo_medio`. 1,0 = oscila o equivalente a um mês inteiro de fluxo |
| `saldo_dez`, `saldo_sem_dez_jan` | Saldo de dezembro e saldo anual sem dezembro e janeiro |
| `pior_saldo_acumulado`, `mes_pior_acumulado` | Fundo do saldo acumulado |
| `pct_meses_sinal_oposto` | Proporção de meses em que o saldo acumulado teve sinal oposto ao saldo anual. Mede o risco de um recorte parcial contar a história errada |
| `pct_pedido_min`, `pct_pedido_max` | Variação da taxa de pedido ao longo do ano |
| `pct_termino_contrato_dez`, `pct_termino_contrato_medio` | Peso dos temporários em dezembro e na média do ano |

Leitura:
- Na indústria como um todo, o saldo acumulado ficou negativo em 10 dos 12 meses (−25.738 em dez/25) e só virou positivo em ago/26. Evite filtros de período parcial sem aviso.
- Dezembro é o vale em quase todos os setores. Os términos de contrato vão de 14% para 28% dos desligamentos.
- Alimentos é o setor mais estável (amplitude de 0,24). Fumo é o mais sazonal: 78% dos desligamentos são fim de contrato (safra).

### 4. JSON para o frontend (`data/processed/api/`)

| Arquivo | Conteúdo |
|---|---|
| `manifest.json` | Data de geração, janela, totais da base e lista de arquivos com colunas e número de linhas |
| `cubo.json` | Contagens por `regiao_intermediaria` × `regiao_imediata` × `setor` × `competencia`: `admissoes`, `desligamentos`, `saldo`, `a_pedido`, `adm_superior`. Para filtrar no React, some as contagens e só depois calcule as taxas (ex.: `Σ a_pedido ÷ Σ desligamentos`) |
| `<nome>.json` | Cada CSV de `data/processed/` como lista de registros (`NaN` vira `null`) |

---

## Limites da análise
- O CAGED mede **fluxo** de admissões e desligamentos, não estoque de empregos nem vagas abertas. Por isso o "apagão" é inferido pelo comportamento de retenção e salário.
- Só foi fornecida a base MOV; não houve desconto das exclusões (EXC).
- O prêmio salarial tende a ser negativo, porque quem sai tem mais tempo de casa. O sinal está na comparação entre setores e regiões.
- O índice é relativo à própria indústria catarinense e não deve ser comparado com outros estados.

---

## Fontes
- Novo CAGED: Ministério do Trabalho e Emprego (base do desafio)
- IBGE: Cidades@ (base municipal do desafio) e Divisão Regional do Brasil em Regiões Geográficas Imediatas e Intermediárias (2017)
- Malha municipal: [tbrugz/geodata-br](https://github.com/tbrugz/geodata-br)
