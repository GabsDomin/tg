# Arquitetura do TG — Desertos de Cuidado em Álcool e Outras Drogas

> Documento de referência para quem executa (agente ou integrante do grupo).
> Explica **o que** será construído e **por quê**. A ordem de execução, com critérios
> de aceite, está em [PLANO_EXECUCAO.md](PLANO_EXECUCAO.md). O que ainda depende de
> decisão humana está na seção 10 — **não decida essas questões sozinho**.

---

## 1. Achados empíricos que definem o desenho (out/2026)

Medidos com dado real, scripts em `scripts/exploracao/`. Eles substituem as premissas
antigas do CLAUDE.md onde houver conflito.

| # | Achado | Fonte | Consequência |
|---|---|---|---|
| A1 | 649 CAPS (tipo 70) em SP, em 293 municípios | CNES ST 2026-09 | — |
| A2 | **123 CAPS AD habilitados** (84 AD, 39 AD III, **0 AD IV**) em **83 municípios** (34 na capital) | CNES HB 2026-09 | 562 municípios sem CAPS AD |
| A3 | Modalidade vem de **habilitação** (`SGRUPHAB`): 0619 AD, 0635 AD III, 0637 AD IV, 0616 I, 0617 II, 0618 III, 0620 i | `TAB_CNES/DBF/HABILITA.DBF` | Nada de inferir modalidade pelo nome |
| A4 | 125 CAPS **sem nenhuma habilitação**; 16 deles se chamam "AD", incluindo o "CAPS AD IV Redenção" | CNES ST+HB | Definição operacional de CAPS AD é decisão (D2) |
| A5 | CNES **tem coordenadas**; 123/123 CAPS AD caem dentro do município declarado (625/632 no total) | OpenDataSUS jun/2025 + malha IBGE | Distância se sustenta sem geocodificação |
| A6 | SIA/PS (RAAS psicossocial) traz `CNES_EXEC` × `MUNPAC` × `CIDPRI` × `TP_DROGA` × `SIT_RUA` | SIA PS dez/2024 | **Dá para observar fluxos reais** residência → serviço |
| A7 | Só **1,2%** dos atendimentos em CAPS AD são de residentes de outro município (319 de 23.309 pacientes no mês) | SIA PS dez/2024 | Encaminhamento intermunicipal é **raro e concentrado** em poucos serviços regionais |
| A8 | **1.627 residentes de 178 municípios sem CAPS AD** foram tratados por F10–F19 em algum CAPS no mês, sobretudo **CAPS I** (5% de todos os pacientes F1x) | SIA PS dez/2024 | "Sem CAPS AD" ≠ "sem cuidado AD"; afeta a definição de deserto (D1) |
| A9 | Mediana de pacientes/mês: AD (0619) ≈ 168, AD III ≈ 288 | SIA PS dez/2024 | Capacidade empírica por modalidade |
| A10 | Todas as bases de 2019–2024 existem no FTP do DATASUS (SIH RD, SIA PS, SIM DO, CNES ST/HB/LT) | FTP | Coleta pelo FTP, não pela API |
| A11 | `apidadosabertos.saude.gov.br` derruba a conexão a partir da rede usada | — | Não depender da API |
| A12 | A oferta **cresceu**: CAPS AD habilitados 96 (2019) → 123 (2026-09); municípios com CAPS AD 66 → 83 | CNES HB, série dez/2019–2026 | A "cobertura" muda dentro do período; ICA precisa ser por ano, não um retrato |
| A13 | **Quebra de regime nos óbitos F10–F19 em SP**: 1.015 (2019) → 1.749 (2020), +72%. Confere 0,0% com o TabNet. Brasil +32%, RJ +31%, RS +15%, **MG +0,6%**. Causa **não verificada** | SIM DO; TabNet | Óbitos viram sinal **secundário**; a demanda principal é internação |
| A14 | **F17 (tabaco) = 21% dos óbitos F1x** em 2024 (285 de 1.379); álcool (F10) = 62% | SIM DO 2024 | Manter `cid3` nas tabelas; análise de sensibilidade sem F17 (D4) |
| A15 | No SIH, **33% dos registros F1x são `IDENT=5` (longa permanência)**, AIH reemitida todo mês. Contar só `IDENT=1` reproduz o TabNet com −0,14% a −0,30% | SIH RD; dicionário `IDENT.CNV` | "Internação" = `IDENT 1`; longa permanência em coluna separada |
| A16 | Série de internações F1x: 19.378 (2019), 15.389 (2020), 15.034 (2021), 17.262 (2022), 22.334 (2023), 24.786 (2024): queda pandêmica de ~21% e retomada acima do nível pré-pandemia | SIH RD | Anos 2020–21 são atípicos; testar robustez sem eles |
| A17 | **Sem estimativa municipal de população para 2022 e 2023** (tabela 6579). 2022 = Censo (44,41 mi); 2023 interpolado. Descontinuidade 2021→2022: 46,65 mi → 44,41 mi (−4,8%) | SIDRA 6579, 4714 | Taxas de 2019–21 têm denominador superestimado; limitação a declarar |
| A18 | População por idade só no Censo 2022. `pop_15mais` = total anual × proporção 15+ de 2022 (aproximação) | SIDRA 9514 | Declarar |
| A19 | O conversor oficial do CNES lista **62 Regiões de Saúde** em SP; o documento do TG diz 63. O campo `REGSAUDE` do arquivo ST está **sujo** (290 valores livres), **não usar** | TAB_CNES `SP_regsaud.cnv`; ST | Usar o conversor. Confirmar o número 63 com o Prof. Ivan |
| A20 | Distância mediana ao CAPS AD habilitado mais próximo: **28 km** (p90 63 km, máx. 164 km); todos os 645 municípios têm um a ≤ 200 km | haversine | O deserto em SP é mais de **capacidade** que de distância; raio de 60 km cobre ~90% |
| A22 | **A taxa de internação F1x reflete polos hospitalares, não só necessidade.** Espírito Santo do Pinhal: 797/100 mil (18× a média de 44,6), com 298 leitos SM SUS. Cidades pequenas sem hospital mandam ~100% das internações a um único polo (Taciba 91/91 e Tarabaí 92/92 → Presidente Prudente; Santo Antônio do Jardim 80/93 → Pinhal). 21 municípios têm 0 internações no bloco 2019–22 | `scripts/exploracao/investigar_*.py` | "Demanda" = **utilização hospitalar por residentes**, contaminada pela oferta/contratação regional de leitos. Declarar em 1.6; manter versão winsorizada (`taxa_suav_int_w99`) e óbitos como sinais de robustez. As **internações têm fluxos fortes** (concentradas), ao contrário do CAPS (A7) |
| A23 | **Validação externa do E2SFCA é fraca e o plano original tinha um viés.** Persistência da demanda 2019–22 → 2023–24: ρ = 0,84 (internação), 0,44 (óbito). Correlação bruta A×internação futura −0,21 cai para **−0,10** (parcial, controlando persistência). O índice só de oferta S dá −0,11: **E2SFCA ≈ oferta pura** em poder preditivo. Camadas O2/O3 sobem um pouco (parcial −0,15/−0,14 vs S −0,13/−0,11). Sensibilidade ao raio: ρ(30 km, 90 km) = 0,63 | `scripts/exploracao/validar_acessibilidade.py` | O valor do E2SFCA é **conceitual** (acesso entre fronteiras; fornece `R_j`, a pressão do serviço, para a porta de referência), **não preditivo**. Reportar como resultado, sem vender como validado. Insumo para D3 |
| A24 | Capacidade observada por modalidade (pacientes/mês, 2019+2022): **AD (0619) mediana 168 (IQR 103–287); AD III mediana 263 (IQR 153–374)**; razão 1,57. Dispersão grande entre serviços da mesma modalidade | `capacidade_modalidade.csv` | A norma por modalidade é grosseira; usar a produção individual só em sensibilidade |
| A25 | Com raio de 60 km e O1: 81 municípios têm acessibilidade **zero**; 294 estão abaixo de metade da média estadual; 476 abaixo da média | E2SFCA O1 r60 | Primeiro retrato do "deserto" (provisório, depende de D1–D3) |
| A21 | Habilitação `0619` chama-se "CAPS ALCOOL E DROGAS", **sem o "II"**. Rotulada "AD"; chamá-la de AD II é presunção **a confirmar na portaria** | HABILITA.DBF | Usar o rótulo "AD" |

**Riscos que A7 e A8 revelam sobre o desenho antigo:**
- A **porta de referência** original ("o mais próximo que não está afogado") recomendaria
  CAPS AD de outros municípios como se aceitassem qualquer residente. Na prática quase não
  aceitam (A7): o CAPS é municipal e o acesso de fora depende de pactuação regional. Uma
  banca de saúde coletiva derruba isso. **Correção:** a porta passa a ranquear destinos
  *acessíveis de fato*, usando como sinais a Região de Saúde e a abertura observada a
  pacientes de fora, e é avaliada contra os fluxos reais (seção 7).
- O **ICA só com CAPS AD** classificaria como deserto municípios que tratam AD no CAPS I
  (A8). **Correção:** o desenho usa uma definição de oferta em camadas (seção 5.2).

---

## 2. Princípios inegociáveis

1. **Reprodutibilidade:** todo dado sai de script. Bruto em `dados/bruto/` (imutável),
   tratado em `dados/tratado/`, publicável em `dados/publicar/`.
2. **Sem circularidade:** nenhum sinal usado para construir um ranking pode ser usado como
   gabarito desse ranking. O mecanismo para garantir isso é o **corte temporal**:
   - **construção** (features, índices, pesos): 2019–2022
   - **avaliação** (gabaritos): 2023–2024
   - A análise descritiva do TG (cap. 4) usa 2019–2024 completo; o corte vale só para o
     motor de busca e a validação do ICA.
3. **Demanda é necessidade, não produção.** A produção do CAPS (RAAS/PS) depende da
   existência do CAPS: onde não há serviço, a produção é zero. Usar RAAS como demanda
   faria a oferta "explicar" a demanda. A demanda vem de **internação (SIH) e óbito (SIM)
   por residência**. A RAAS entra como **atendimento realizado** (carga/pressão do serviço
   e fluxos), nunca como demanda.
4. **Município de residência** para toda demanda (`MUNIC_RES` no SIH, `CODMUNRES` no SIM,
   `MUNPAC` no PS). Município de internação é usado só para fluxo.
5. **Só agregados saem do ambiente local.** SIH, SIA e SIM são microdados com identificador
   de paciente (`CNS_PAC`). `CNS_PAC` pode ser usado em memória para contar pacientes
   únicos, mas **nunca é persistido** em `dados/tratado/`. A página publicada aplica
   supressão de células pequenas (seção 8.3).
6. **Código de domínio verificado, nunca lembrado.** Códigos de habilitação, tipo de leito,
   CID, tabelas SIDRA e limiares de portaria são conferidos na tabela oficial ou no texto
   normativo, e a fonte é registrada em `config.yaml`.

---

## 3. Visão geral

```
            ┌──────────────── COLETA (FTP DATASUS, IBGE) ────────────────┐
            │ CNES ST/HB/LT · SIH RD · SIA PS · SIM DO · Censo · malhas  │
            └──────────────────────────────┬─────────────────────────────┘
                                           ▼
                         TRATAMENTO (dados/tratado/*.parquet)
       estabelecimentos(ano) · internacoes(mun,ano) · obitos(mun,ano) ·
       atendimentos_raas(cnes,mun_res,ano) · populacao(mun,ano) · distancias
                                           ▼
   ┌─────────────── NÚCLEO ANALÍTICO (objetivos 2–5) ───────────────┐
   │ demanda suavizada (EB) · oferta em camadas · acessibilidade    │
   │ E2SFCA · ICA · K-Means · caracterização socioeconômica         │
   └─────────────────────────────┬──────────────────────────────────┘
                                 │  ICA, pressão por serviço, clusters
                                 ▼
   ┌─────────────── MOTOR DE BUSCA (objetivo 6) ────────────────────┐
   │ corpus (municípios, regiões, serviços) → índice BM25 + denso   │
   │ → interpretação da consulta → recuperação → ranqueamento       │
   │ multicritério explicável. Duas portas: PLANEJAMENTO, REFERÊNCIA│
   └─────────────────────────────┬──────────────────────────────────┘
                                 ▼
   AVALIAÇÃO (objetivo 7): gabaritos 2023–24, baselines, ablação,
   P@k / MRR / NDCG@k, bootstrap pareado
                                 ▼
   PÁGINA PUBLICADA (Streamlit): mapa + busca + "por que este resultado"
```

O ICA e a pressão assistencial calculados no núcleo analítico são **sinais de ranqueamento**
do motor. Isso integra os dois produtos em vez de deixá-los lado a lado.

---

## 4. Camada de dados

### 4.1 Fontes e arquivos

Base FTP: `ftp://ftp.datasus.gov.br/dissemin/publicos/`

| Conjunto | Caminho FTP | Arquivos | Uso |
|---|---|---|---|
| CNES estabelecimentos | `CNES/200508_/Dados/ST/STSPaamm.dbc` | competência **dezembro** de cada ano 2019–2024 + 2026-09 (atual) | oferta, tipo, Região de Saúde (`REGSAUDE`) |
| CNES habilitações | `CNES/200508_/Dados/HB/HBSPaamm.dbc` | mesmas competências | modalidade (A3) |
| CNES leitos | `CNES/200508_/Dados/LT/LTSPaamm.dbc` | mesmas | leitos de saúde mental em hospital geral (destino da porta de referência) |
| Tabelas auxiliares | `CNES/200508_/Auxiliar/TAB_CNES.zip` | 1 | decodificar habilitação, tipo de leito etc. |
| SIH internações | `SIHSUS/200801_/Dados/RDSPaamm.dbc` | 72 (2019-01 a 2024-12) | demanda: internações F10–F19 por residência |
| SIA psicossocial | `SIASUS/200801_/Dados/PSSPaamm.dbc` | 72 | atendimento realizado, carga por CAPS, fluxos |
| SIM óbitos | `SIM/CID10/DORES/DOSPaaaa.dbc` | 6 | demanda: óbitos com causa básica F10–F19 (ver 5.1) |
| Coordenadas | OpenDataSUS `cnes_estabelecimentos.zip` (S3, jun/2025) | 1 (já em `dados/bruto/`) | lat/long; serviços ausentes recebem centroide do CEP ou município, com marcação |
| Malha municipal | IBGE API v3 malhas, SP, intrarregião município | 1 (já em `dados/bruto/`) | mapas, validação de coordenadas, centroides |
| População | IBGE: Censo 2022 + estimativas anuais (SIDRA) | — | denominadores; **tabelas SIDRA a confirmar** |
| Socioeconômico | IBGE Censo 2022 (SIDRA) | — | caracterização dos clusters; **variáveis disponíveis a confirmar** |

Leitura de `.dbc`: `pyreaddbc.dbc2dbf` + `dbfread` (já testado). O PySUS é opcional; o
leitor próprio já funciona e tem menos dependências.

### 4.2 Esquema de `dados/tratado/` (Parquet)

| Tabela | Granularidade | Colunas essenciais |
|---|---|---|
| `municipios` | município (645) | `cod_mun6`, `cod_mun7`, `nome`, `regiao_saude`, `drs`, `lat`, `lon` (centroide), `area_km2` |
| `populacao` | município × ano | `cod_mun6`, `ano`, `pop_total`, `pop_15mais` |
| `servicos` | CNES × ano | `cnes`, `ano`, `cod_mun6`, `nome`, `tipo`, `habilitacoes`, `modalidade`, `eh_caps_ad`, `lat`, `lon`, `origem_coord`, `coord_valida` |
| `internacoes` | município residência × ano × sexo × faixa | `n_internacoes`, `n_dias` (só F10–F19 em `DIAG_PRINC`) |
| `obitos` | município residência × ano | `n_obitos` |
| `raas_carga` | CNES × ano × mês | `pacientes_unicos`, `pacientes_f1x`, `procedimentos` |
| `raas_fluxos` | município residência × CNES × ano | `pacientes_unicos` (sem CNS) |
| `distancias` | município × serviço | `km_haversine` |

Chave municipal: código IBGE de **6 dígitos** (DATASUS). O de 7 dígitos fica guardado só
para cruzar com o IBGE.

### 4.3 Armadilhas conhecidas

- `ST.REGSAUDE` é lixo (A19). Região de saúde vem de `SP_regsaud.cnv`.
- `ST`/`HB` por competência: o campo `CMPT_FIM` vazio significa habilitação vigente.
- SEXO no SIH: 1 = masculino, 2 ou 3 = feminino. No SIM: 1 e 2.
- O TabNet derruba conexões em rajada: espaçar as consultas e repetir com pausa.
- A regex `CAPS AD` casa com "CAPS ADULTO". Modalidade sai só de habilitação.
- Habilitação vigente: `CMPT_FIM` vazio ou ≥ competência.
- O CSV derivado sem aspas quebra em campos com `;`. Leia sempre o original.
- Terminal Windows em cp1252: rode com `PYTHONIOENCODING=utf-8`.
- O SIH tem reinternações e AIH de continuidade. Conte AIH tipo 1 (`IDENT == '1'`),
  **campo a confirmar** no dicionário do RD.
- 2020–2021 (pandemia) distorce internação e produção. Sinalize nos gráficos e teste a
  robustez excluindo esses anos.

---

## 5. Núcleo analítico (objetivos 2–5)

### 5.1 Demanda (necessidade estimada)

- **D_int**: internações F10–F19 por residência, por 100 mil hab. 15+.
- **Hierarquia dos sinais (A13, A15):** D_int é o sinal principal de demanda. D_obito é
  **secundário**: tem quebra de regime em 2020 de origem desconhecida e é raro em municípios
  pequenos. Não somar os dois num índice sem padronizar por ano.
- **D_obito**: óbitos com causa básica F10–F19, por 100 mil. A lista de CIDs de óbito
  atribuível a álcool e drogas é mais ampla que F10–F19 (cirrose alcoólica K70,
  intoxicações X40–X45 etc.). **Decisão D4.** O padrão é **só F10–F19**, por coerência com
  o recorte.
- **Suavização Bayesiana empírica** (modelo Poisson-gama ou estimador de Marshall) sobre as
  taxas, para estabilizar municípios pequenos. Agregação plurianual: 2019–2022 (construção)
  e 2023–2024 (avaliação).
- Demanda esperada para a acessibilidade: `E_m = taxa_suavizada_m × pop_m`.

### 5.2 Oferta em camadas (responde a A8)

| Camada | Definição | Uso |
|---|---|---|
| O1 — estrita | CAPS AD habilitado (0619/0635/0637) | definição principal, fiel ao recorte |
| O2 — ampliada | O1 + CAPS AD sem habilitação, se D2 aprovar | sensibilidade |
| O3 — efetiva | O1 + CAPS I/II/III com produção F1x observada | sensibilidade, mostra a cobertura oculta (A8) |

Capacidade relativa por modalidade: razão das medianas de pacientes/mês em 2019–2022 (A9
sugere AD III ≈ 1,7 × AD (0619)). Isso é uma **norma empírica por modalidade**, não a carga do
CAPS individual. O peso vem de dado, não de suposição.

O texto do TG mantém "apenas CAPS AD como equipamento de referência" (O1). O2 e O3 entram
como **análise de sensibilidade**. Assim o recorte não muda, e a fragilidade (A8) é tratada
em vez de escondida.

### 5.3 ICA (objetivo 3)

São dois níveis, ambos usando só oferta, população, demanda e distância:

1. **ICA municipal (baseline):** `ICA_m = capacidade_O1_m / E_m`. Simples e comparável ao
   que o documento prometeu. Dá zero para 562 municípios, o que discrimina pouco.
2. **ICA espacial (proposta principal): E2SFCA** (*Enhanced Two-Step Floating Catchment
   Area*).
   - Passo 1: para cada serviço `j`, `R_j = cap_j / Σ_m E_m · w(d_mj)`.
   - Passo 2: para cada município `m`, `A_m = Σ_j R_j · w(d_mj)`.
   - `w` é decaimento por faixas de distância.
   - Raio de captação e faixas são parâmetros, com **análise de sensibilidade obrigatória**
     (ex.: 30/60/90 km).
   - Distância: haversine entre centroide municipal e serviço. Distância por estrada é
     melhoria opcional e entra como limitação declarada.
   - Referência canônica do 2SFCA: Luo e Wang (2003); do E2SFCA: Luo e Qi (2009).
     **Nenhuma das duas está confirmada. Confirmar autor, ano e veículo antes de citar.**

Por que o E2SFCA:
- Resolve o "município sem CAPS ao lado de um que tem", que o ICA municipal ignora.
- Seu `R_j` é exatamente a **pressão potencial do serviço `j`**, que a porta de referência
  precisa. Um único método produz o índice territorial e o sinal de ranqueamento.

"Deserto de cuidado" é operacionalizado como `A_m` abaixo de um limiar (ex.: quintil
inferior), mantendo a redação do documento: indicador de possível insuficiência, não prova
de ausência de atendimento.

**Validação externa do ICA (sem circularidade):** correlação de Spearman entre `A_m`
(2019–2022) e desfechos 2023–2024 que não entraram no índice, como taxa de internação
2023–24 e óbitos. A hipótese, coerente com Miliauskas et al. (2019), é que menor
acessibilidade se associa a mais internação. Se não houver associação, isso é resultado e
se reporta.

### 5.4 K-Means (objetivo 4)

- Variáveis **só assistenciais**: `A_m` (E2SFCA), `ICA_m`, D_int suavizada, D_obito
  suavizada, distância ao CAPS AD mais próximo, fração de demanda atendida fora do
  município (RAAS).
- Padronização com z-score. `k` escolhido por silhueta + cotovelo + interpretabilidade,
  testando k = 3..8. Estabilidade por bootstrap: índice de Rand ajustado entre reamostras.
- Socioeconômicas **fora** do agrupamento (decisão já tomada no CLAUDE.md).

### 5.5 Caracterização (objetivo 5)

- Comparar os clusters em variáveis do Censo 2022 com Kruskal-Wallis e post-hoc de Dunn
  com correção de Holm.
- Tamanho de efeito: épsilon² (ε²).
- Mapa coroplético dos clusters.

---

## 6. Motor de busca (objetivo 6)

### 6.1 O que o torna um motor de busca, e não um filtro

Um motor de busca, para a banca, tem quatro partes, e o sistema implementa cada uma de
forma explícita e avaliável:
1. **Corpus** de documentos
2. **Índice**
3. **Função de ranqueamento** que ordena por relevância a uma consulta
4. **Avaliação** com gabarito e métricas de recuperação

Um filtro devolve um conjunto. O motor devolve uma **ordem**, e essa ordem é medida.

### 6.2 Corpus

| Coleção | Documentos (aprox.) | Texto do documento (gerado de template) |
|---|---|---|
| Municípios | 645 | nome, região de saúde, DRS, porte, demanda, ICA, cluster, serviços próprios, "sem CAPS AD" etc. |
| Regiões de Saúde | ~63 (confirmar no ST) | agregados da região |
| Serviços | CAPS (649) + Unidades de Acolhimento + hospitais com leito de saúde mental (códigos **a confirmar** em TAB_CNES) | nome, modalidade, município, região, funcionamento 24h, carga observada |

Isso dá aproximadamente 1.500 documentos. **Não incluir UBS em massa:** elas não são
destino de encaminhamento equivalente, e inflar o corpus com elas é enchimento que a banca
percebe. A defesa do tamanho é a da seção 6.1.

Os documentos são **gerados por template** a partir das tabelas. Isso é deliberado e deve
ser declarado no texto. A recuperação textual existe para interpretar a linguagem do
usuário. A relevância substantiva vem dos sinais estruturados.

### 6.3 Pipeline de consulta

```
consulta em linguagem natural
   │
   ├─ 1. Interpretação (regras + gazetteer, determinístico):
   │     extrai município/região/DRS citados (gazetteer com variações sem acento),
   │     restrições ("sem CAPS AD", "interior", "acima de 50 mil", "24 horas",
   │     "situação de rua") e intenção (planejamento × referência)
   │
   ├─ 2. Recuperação de candidatos: híbrida
   │     BM25 (rank_bm25) + denso (sentence-transformers multilíngue),
   │     fundidos por Reciprocal Rank Fusion (RRF); restrições aplicadas como filtro
   │
   └─ 3. Ranqueamento multicritério explicável (por porta, abaixo)
         saída: lista ordenada + decomposição do score por componente
```

O modelo denso é uma **escolha a validar** (ex.:
`paraphrase-multilingual-MiniLM-L12-v2`). Prefira modelo local e gratuito, sem API paga,
por reprodutibilidade e custo. Se o modelo não couber na hospedagem (seção 8), a página usa
BM25 + interpretação, e o denso fica como experimento offline na ablação.

### 6.4 Porta de PLANEJAMENTO

- **Consulta:** "municípios do interior sem CAPS AD com mais internação",
  "onde priorizar CAPS AD na região de Bauru".
- **Unidades retornadas:** municípios ou regiões de saúde.
- **Score:** `S = α·rel_textual + β·necessidade`
  - `necessidade` = combinação normalizada de (1 − A_m) e demanda suavizada (2019–2022)
  - `rel_textual` = score RRF
  - restrições extraídas filtram antes do ranqueamento
  - α e β são calibrados num subconjunto de desenvolvimento, **nunca** no conjunto de teste
- **Explicação:** "aparece em 3º porque: acessibilidade no 5º percentil, internações 2,1×
  a mediana estadual, 74 km do CAPS AD mais próximo".

### 6.5 Porta de REFERÊNCIA (redesenhada por A7)

- **Consulta:** município de origem, mais um perfil opcional (precisa de 24h; situação de
  rua; tipo de droga). Pode vir em linguagem natural: "para onde encaminhar de Ilha
  Comprida, precisa de acolhimento noturno".
- **Unidades retornadas:** serviços, ou seja, CAPS AD, CAPS I/II/III com produção F1x, UA
  e leitos.
- **Candidatos:** serviços no município, na mesma Região de Saúde, ou a até X km.
- **Score** (componentes normalizados em [0,1], todos calculados em 2019–2022):

| Componente | Sinal | Racional |
|---|---|---|
| proximidade | 1 − km/km_max | acesso físico |
| mesma região de saúde | 0/1 | proxy de pactuação |
| abertura observada | fração de pacientes de fora do município atendidos no serviço (RAAS) | o serviço aceita gente de fora? (A7) |
| adequação | modalidade × perfil (AD III/IV para necessidade de 24h; AD > CAPS I) | 2.2 do TG: modalidades não equivalentes |
| folga | 1 − pressão (carga RAAS / norma da modalidade, combinada com `R_j` do E2SFCA) | "o mais próximo que não está afogado" |

- **Explicação** por resultado, com cada componente e seu peso.

### 6.6 Ética na interface

- A página é para **gestão e planejamento**, não para triagem clínica.
- Aviso fixo: "Este sistema não substitui avaliação profissional. Em crise: CVV 188, SAMU
  192."
- A porta de referência sugere serviços a contatar, não garante vaga.

---

## 7. Avaliação (objetivo 7: novo)

### 7.1 Porta de REFERÊNCIA: gabarito por fluxos observados (principal)

- **Consultas:** todo município de origem com pelo menos 1 paciente atendido fora do
  próprio município em 2023–2024, segundo o PS. Estimativa: algumas centenas (A7/A8
  indicam 73 a 178 por mês). Isso dá um conjunto grande e automático, sem depender de
  especialista.
- **Relevância graduada** do serviço `j` para a origem `m`: pacientes únicos de `m` em `j`
  em 2023–24, em faixas (0 / 1–4 / 5–19 / 20+ → 0/1/2/3).
- **Métricas:** NDCG@5, NDCG@10, MRR, P@5.
- **Baselines:**
  - (a) só distância, que é o que os buscadores existentes fazem;
  - (b) só população do destino;
  - (c) persistência, ou seja, fluxo 2019–22 como único sinal. Esse é o adversário honesto:
    "quem foi antes vai depois".
- **Ablação:** sistema completo − cada componente, um por vez.
- **Teste:** bootstrap pareado sobre as consultas (IC 95% da diferença de NDCG).

**Limitação a declarar:** fluxos observados medem onde as pessoas *foram*, não onde
*deveriam* ir. O componente "folga" pode piorar a métrica de fluxos e ainda assim ser
desejável, porque os fluxos reais podem se concentrar em serviços lotados. Por isso a folga
tem avaliação própria: estudo de casos e, se houver especialista (D5), julgamento humano.

### 7.2 Porta de PLANEJAMENTO

- **40–60 consultas** escritas pelo grupo **antes** de olhar os resultados. Cada uma é
  registrada com a restrição estruturada esperada, em `avaliacao/consultas_planejamento.yaml`.
- **Relevância:**
  - satisfaz as restrições: binário, calculado dos atributos;
  - × necessidade medida em **2023–2024** (internações e óbitos suavizados), em quartis
    0–3.
  - O ranking é construído com 2019–22, então não há circularidade com o ICA.
- **Métricas:** NDCG@10, P@10. A interpretação da consulta tem métrica própria: acurácia
  de extração das restrições.
- **Baselines:** só BM25; filtro + ordenação por população; filtro + ICA sem
  interpretação de linguagem.

### 7.3 Gabarito normativo (complementar, opcional)

O gabarito derivado das portarias só entra se D6 aprovar, e sempre com a ressalva de
circularidade já registrada no CLAUDE.md. Os limiares populacionais precisam ser
**confirmados no texto da portaria**.

---

## 8. Página publicada

### 8.1 Stack e hospedagem

- **Streamlit** (convenção do repositório) + folium/plotly.
- Hospedagem recomendada: Streamlit Community Cloud, conectado ao repositório GitHub.
  **Confirmar limites atuais de memória e regras para repositório privado antes de
  escolher.** Alternativa: Hugging Face Spaces.
- A página **não roda o pipeline**. Ela lê só artefatos pré-computados em
  `dados/publicar/`: Parquet agregado, índice BM25 serializado, embeddings dos documentos
  em `.npy`.

### 8.2 Seções da página

1. **Mapa:** acessibilidade E2SFCA, clusters e serviços, com seletor de camada O1/O2/O3.
2. **Busca:** caixa única, que detecta a porta pela intenção, com abas manuais de reserva.
3. **Resultado:** lista ranqueada + "por que este resultado" (barras de contribuição por
   componente).
4. **Sobre/Método:** fontes, datas das competências, limitações e aviso ético.
5. **Avaliação:** tabela de métricas vs. baselines, o que mostra que o motor é medido.

### 8.3 Proteção de dados

- `dados/publicar/` contém **apenas agregados**. Nenhum CNS, data de nascimento ou registro
  individual.
- **Supressão:** em fluxos origem→destino e contagens por município, valores de 1 a 4
  aparecem como "<5".
- Um teste automatizado falha se alguma coluna proibida (`CNS_PAC`, `DTNASC`, `N_AIH`)
  aparecer em `dados/publicar/`.

---

## 9. Estrutura do repositório

```
TG/
├── CLAUDE.md                  memória do projeto (estado + regras)
├── config.yaml                período, UF, competências, códigos verificados e suas fontes
├── requirements.txt
├── docs/
│   ├── ARQUITETURA.md         este arquivo
│   └── PLANO_EXECUCAO.md      tarefas com critérios de aceite
├── src/tg/
│   ├── config.py              lê config.yaml
│   ├── coleta/                ftp.py (download com cache e checagem de tamanho), ibge.py
│   ├── leitura/               dbc.py (dbc → DataFrame)
│   ├── tratamento/            cnes.py, sih.py, sia_ps.py, sim.py, populacao.py, geo.py
│   ├── indicadores/           demanda.py (EB), oferta.py (camadas), acessibilidade.py (E2SFCA), ica.py
│   ├── clusters/              kmeans.py, caracterizacao.py
│   ├── busca/                 corpus.py, indice.py, consulta.py (interpretação),
│   │                          recuperacao.py (BM25/denso/RRF), ranking.py (portas), explicacao.py
│   ├── avaliacao/             gabaritos.py, metricas.py, baselines.py, ablacao.py, bootstrap.py
│   └── publicar/              exporta artefatos agregados + supressão
├── pipeline.py                python pipeline.py <etapa>|tudo (idempotente, pula o que já existe)
├── app/streamlit_app.py
├── avaliacao/consultas_planejamento.yaml
├── tests/                     testes de unidade e de "contrato de dados"
├── scripts/exploracao/        diagnósticos já executados (não fazem parte do pipeline)
├── notebooks/                 só leitura e figuras do TG; nada de transformação
└── dados/{bruto,tratado,publicar}/
```

---

## 10. Decisões que dependem de humano (bloqueantes)

O executor **não decide** estes pontos. Implementa a recomendação de forma parametrizada em
`config.yaml`, para que a troca seja barata, e registra a decisão no CLAUDE.md quando ela
for tomada.

| ID | Decisão | Recomendação | Quem |
|---|---|---|---|
| D0 | A exigência do motor de busca está escrita? Qual é a **data de entrega**? | confirmar na rubrica/plano de ensino | grupo |
| D1 | Oferta: só CAPS AD (O1) ou camadas O2/O3 como sensibilidade? | O1 principal, O2/O3 sensibilidade | grupo + Prof. Ivan |
| D2 | CAPS "AD" sem habilitação conta? | não na O1; sim na O2 | grupo + Prof. Ivan |
| D3 | ICA: municipal (prometido) ou E2SFCA (proposto)? | os dois, com E2SFCA como principal; muda redação da 3.x | Prof. Ivan |
| D4 | Óbitos: só F10–F19 ou lista ampliada de causas atribuíveis? | só F10–F19 | grupo |
| D5 | Existe especialista da RAPS para julgar 15–20 consultas? | desejável, não obrigatório | grupo |
| D6 | Gabarito normativo entra? | só se sobrar tempo | grupo |
| D7 | Repositório público no GitHub? (necessário para hospedagem gratuita típica) | sim, sem `dados/bruto` | grupo |

---

## 11. Riscos e linhas de corte

Ordem de corte se faltar tempo, cortando primeiro o que está no topo:
1. Recuperação densa (fica BM25 + interpretação)
2. Gabarito normativo
3. Camadas O2/O3 (fica só O1, com A8 citado como limitação)
4. Porta de planejamento em linguagem natural (fica filtro estruturado + ranking)
5. **Nunca cortar:** porta de referência, avaliação por fluxos, ICA e K-Means

Outros riscos:
- **Prazo.** Hoje é 23/10/2026 e a entrega é "2026". Com 5–7 semanas, tudo além do núcleo
  vira risco. Confirmar a data é D0.
- **Volume de download:** cerca de 1,2 GB de SIH. O FTP às vezes oscila, então o download
  precisa de cache, retomada e checagem de tamanho.
- **Pandemia (2020–21) no período de construção:** verificar a robustez construindo também
  só com 2019 + 2022.

---

## 12. O que não fazer

- Não usar a API `apidadosabertos` (A11).
- Não inferir modalidade pelo nome (A3).
- Não usar RAAS/PS como medida de demanda (princípio 3).
- Não calibrar pesos olhando o conjunto de teste (2023–24).
- Não publicar nada que não passe pela supressão e pelo teste de colunas proibidas.
- Não citar referência, código ou limiar normativo não conferido. Marque "a confirmar".
- Não editar arquivos em `dados/bruto/`.
