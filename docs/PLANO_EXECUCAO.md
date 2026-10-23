# Plano de Execução

> Para o agente executor. Leia antes: [ARQUITETURA.md](ARQUITETURA.md) (o porquê) e o
> CLAUDE.md (regras). Execute **na ordem**. Cada tarefa só está pronta quando **todos** os
> critérios de aceite passam. Ao terminar uma tarefa, marque-a aqui (`[x]`) e atualize a
> seção "Estado atual" do CLAUDE.md.

## Regras de execução

- **Ambiente:** `.venv` criado com `uv`. Para rodar Python:
  `.venv\Scripts\python.exe -I ...`, com `PYTHONIOENCODING=utf-8`. Para nova dependência:
  `uv pip install --python .venv <pacote>` e depois regenere o `requirements.txt`.
- **Tarefa marcada ⛔:** depende de decisão humana (ARQUITETURA §10). Implemente
  parametrizado com a recomendação e **pare para perguntar** antes de tratá-la como final.
- **Código de domínio novo** (habilitação, leito, CID, tabela SIDRA): confira na fonte
  oficial e registre em `config.yaml` com o campo `fonte:`.
- **Antes de declarar uma tarefa pronta:** rode os testes (`pytest`) e a etapa do pipeline
  do zero numa pasta limpa, se for barato.
- **Não toque no .docx do TG.** A escrita é a tarefa T10 e exige revisão humana.

---

## Fase 0 — Fundação

### [x] T0.1 Repositório e configuração
- `git init` e primeiro commit, com o `.gitignore` já existente. **Não** criar remoto nem
  dar push sem autorização (D7).
- Criar `config.yaml` com:
  - `uf: SP`, `cod_uf: 35`
  - `anos_construcao: [2019, 2020, 2021, 2022]`, `anos_avaliacao: [2023, 2024]`
  - `competencia_cnes_atual: 202609`
  - `cid_demanda: F10-F19`
  - `habilitacoes`: códigos de ARQUITETURA A3, com `fonte: TAB_CNES/DBF/HABILITA.DBF`
  - `oferta_camada: O1` ⛔D1
  - `e2sfca: {raio_km: 60, faixas_km: [15, 30, 60], pesos: [1.0, 0.68, 0.22]}`.
    São valores iniciais. Os pesos são placeholders a substituir por decaimento justificado
    na literatura **confirmada**.
  - `supressao_min: 5`
- `src/tg/config.py` lê o YAML e expõe os caminhos `dados/bruto|tratado|publicar`.
- **Aceite:** `python -c "from tg.config import CFG; print(CFG.uf)"` imprime `SP`, com o
  pacote instalado via `uv pip install -e .` (crie um `pyproject.toml` mínimo).

### [x] T0.2 Coleta FTP com cache
- `src/tg/coleta/ftp.py`: `baixar(caminho_remoto) -> Path` em `dados/bruto/<conjunto>/`.
  - Não baixa de novo se já existe com o mesmo tamanho (`SIZE` do FTP).
  - Até 3 tentativas com espera crescente.
  - Registra em `dados/bruto/_manifesto.csv`: arquivo, tamanho, data de modificação
    remota, data do download.
- `src/tg/leitura/dbc.py`: `ler_dbc(path, colunas=None) -> DataFrame`, reaproveitando o
  `.dbf` se já existir. Para arquivos grandes (SIH), use leitura por colunas.
- CLI: `python pipeline.py coleta` baixa tudo da ARQUITETURA §4.1.
- **Aceite:**
  - o manifesto lista 72 RD, 72 PS, 6 DO, ST/HB/LT de dez/2019..dez/2024 + 202609;
  - rodar duas vezes não baixa nada na segunda;
  - teste de unidade para `ler_dbc` com `HBSP2609.dbc`.

---

## Fase 1 — Tratamento

### [x] T1.1 Municípios, malha e população
- `tratado/municipios.parquet`:
  - 645 linhas, com centroide calculado da malha (use `representative_point`);
  - região de saúde vinda do ST ou de TAB_CNES (`br_regsaud*.cnv`, conferir o arquivo
    certo).
- `tratado/populacao.parquet` por ano (2019–2024).
  - **Pesquise e registre a tabela SIDRA usada**: estimativas anuais + Censo 2022.
  - Se a faixa 15+ por município não existir anualmente, use a total e registre a
    limitação.
- **Aceite:**
  - 645 municípios únicos e nenhum nulo em região de saúde;
  - número de regiões de saúde registrado no CLAUDE.md (o documento diz 63; conferir);
  - população total de SP em 2022 dentro de ±1% do Censo 2022.

### [x] T1.2 Serviços
- `tratado/servicos.parquet` por ano: tipo 70 + Unidades de Acolhimento + hospitais com
  leito de saúde mental.
  - Códigos de UA e de leito: **descobrir e conferir** em TAB_CNES.
- Coordenadas pela ordem de prioridade:
  1. OpenDataSUS jun/2025;
  2. centroide do CEP, se houver fonte confiável;
  3. centroide do município.
  - Coluna `origem_coord` diz qual foi usada; `coord_valida` vem do ponto-no-polígono.
- Generalize `scripts/exploracao/diagnostico_v2.py`.
- **Aceite:**
  - em 202609: 123 CAPS AD habilitados em 83 municípios (reproduz A2);
  - 100% dos serviços com coordenada e `origem_coord` preenchida;
  - teste garante que nenhum "CAPS ADULTO" é marcado como AD.

### [x] T1.3 Internações (SIH)
- Filtrar `DIAG_PRINC` F10–F19.
  - Confirmar no dicionário do RD o campo de AIH principal vs. continuação e usar só a
    principal.
- Agregar por `MUNIC_RES` × ano × sexo × faixa etária.
- **Aceite:**
  - total anual de SP conferido contra o TabNet (SIH, internações por residência, CID
    capítulo/categoria F10–F19, SP) com diferença < 2%;
  - registrar o número conferido e a data da consulta no CLAUDE.md.

### [x] T1.4 Óbitos (SIM)
- Causa básica (`CAUSABAS`) F10–F19 ⛔D4, por `CODMUNRES` × ano.
- **Aceite:** conferência com o TabNet SIM com diferença < 2%.

### [x] T1.5 RAAS psicossocial (SIA/PS)
- `raas_carga` por CNES × mês: pacientes únicos (por `CNS_PAC`, só em memória) e pacientes
  F1x.
- `raas_fluxos` por `MUNPAC` × `CNES_EXEC` × ano.
- **Nenhuma coluna de identificação** nas saídas.
- **Aceite:**
  - dez/2024 reproduz A7 (cerca de 23,3 mil pacientes em CAPS AD; 1,2% de fora) e A8
    (1.627 / 178);
  - teste: colunas proibidas ausentes em `tratado/`.

### [x] T1.6 Matriz de distâncias
- Haversine entre o centroide de cada município e cada serviço, num raio de até 200 km.
- **Aceite:** distância Santana de Parnaíba → capital (centroides) entre 20 e 45 km, como
  teste de sanidade.

---

## Fase 2 — Núcleo analítico

### [ ] T2.1 Demanda suavizada
- Bayes empírico (Poisson-gama, ou Marshall) para D_int e D_obito, em dois blocos:
  2019–22 e 2023–24.
- **Aceite:**
  - a variância das taxas suavizadas é menor que a das brutas;
  - municípios grandes mudam pouco: correlação bruta × suavizada > 0,95 em municípios
    acima de 100 mil hab.;
  - gráfico funil (taxa × população) salvo em `figuras/`.

### [ ] T2.2 Oferta em camadas e capacidade ⛔D1 ⛔D2
- O1, O2, O3 conforme ARQUITETURA §5.2.
- Capacidade por modalidade = razão das medianas de pacientes/mês em 2019–22.
- **Aceite:** tabela de capacidade por modalidade salva; contagem de serviços por camada e
  ano.

### [ ] T2.3 ICA municipal e E2SFCA ⛔D3
- `indicadores/acessibilidade.py` com função pura
  `e2sfca(oferta, demanda, distancias, raio, faixas, pesos)`.
- **Aceite:**
  - teste de unidade com um caso de brinquedo calculado à mão (3 municípios, 2 serviços);
  - sensibilidade para raios de 30/60/90 km (Spearman entre rankings reportado);
  - validação externa: Spearman entre `A_m` (2019–22) e internações 2023–24 (ARQUITETURA
    §5.3), com resultado registrado, seja qual for.

### [ ] T2.4 K-Means
- Variáveis conforme ARQUITETURA §5.4. `k` de 3 a 8, avaliado por silhueta, cotovelo e
  estabilidade (ARI em 100 bootstraps).
- **Aceite:**
  - figura de silhueta;
  - `k` escolhido com justificativa escrita em `docs/resultados_clusters.md`;
  - ARI médio reportado.

### [ ] T2.5 Caracterização socioeconômica
- Variáveis do Censo 2022: **descobrir o que está disponível no SIDRA em nível municipal e
  registrar as tabelas**.
- Kruskal-Wallis + Dunn/Holm + ε².
- **Aceite:** tabela por cluster com mediana (IQR) e p-valor ajustado.

---

## Fase 3 — Motor de busca

### [ ] T3.1 Corpus
- `busca/corpus.py` gera os documentos por template (ARQUITETURA §6.2), com id estável e
  metadados estruturados.
- **Aceite:**
  - cerca de 1.500 documentos;
  - todo documento tem `colecao`, `id`, `texto`, `atributos`;
  - 5 exemplos impressos no relatório da tarefa.

### [ ] T3.2 Interpretação de consultas
- Gazetteer com nomes de municípios, regiões e DRS, normalizando acentos, caixa e "SP".
- Regras para restrições e intenção.
- **Aceite:** conjunto de 30 consultas de teste com restrição esperada, e acurácia de
  extração ≥ 90%. Escreva as consultas de teste **antes** das regras.

### [ ] T3.3 Recuperação
- BM25 (`rank_bm25`) e denso (`sentence-transformers`; modelo registrado no
  `config.yaml`), fundidos por RRF (k = 60).
- **Aceite:**
  - cada recuperador é chamável isoladamente, o que a ablação exige;
  - latência < 1 s por consulta numa CPU comum.

### [ ] T3.4 Ranqueamento e explicação
- Funções das duas portas (ARQUITETURA §6.4 e §6.5), com componentes normalizados e pesos
  vindos do `config.yaml`.
- `explicacao.py` devolve a contribuição de cada componente.
- **Aceite:**
  - a soma das contribuições é igual ao score (teste);
  - nenhum componente usa dado de 2023–24. Teste: monkeypatch que remove os anos de
    avaliação e verifica que o ranking não muda.

---

## Fase 4 — Avaliação

### [ ] T4.1 Gabaritos
- Referência: gerado automaticamente de `raas_fluxos` 2023–24, com as faixas de relevância
  da ARQUITETURA §7.1.
- Planejamento: `avaliacao/consultas_planejamento.yaml` com 40–60 consultas. O **grupo**
  escreve as consultas; o agente gera os rótulos pelos atributos e pela necessidade
  2023–24.
- **Aceite:** número de consultas por porta reportado; nenhuma consulta de planejamento
  usada para calibrar pesos (divisão desenvolvimento/teste registrada).

### [ ] T4.2 Métricas, baselines, ablação
- P@k, MRR, NDCG@k implementados e testados contra exemplos calculados à mão.
  `sklearn.metrics.ndcg_score` serve como conferência.
- Baselines e ablação conforme ARQUITETURA §7.
- Bootstrap pareado com 1.000 reamostras e IC 95%.
- **Aceite:** `docs/resultados_avaliacao.md` com:
  - tabela sistema × baselines × ablação;
  - os ICs;
  - um parágrafo honesto sobre o que **não** funcionou.

---

## Fase 5 — Página publicada

### [ ] T5.1 Exportação
- `python pipeline.py publicar` gera `dados/publicar/`: agregados com supressão `<5`,
  índice BM25 serializado, embeddings `.npy` e métricas de avaliação.
- **Aceite:**
  - teste de colunas proibidas passa;
  - teste de supressão passa;
  - pasta com menos de 100 MB.

### [ ] T5.2 App Streamlit
- Seções da ARQUITETURA §8.2, aviso ético fixo e data das competências visível.
- **Aceite:**
  - `streamlit run app/streamlit_app.py` abre local;
  - as 3 consultas de demonstração retornam resultado com explicação;
  - a app funciona sem `dados/bruto/` e sem `dados/tratado/`.

### [ ] T5.3 Deploy ⛔D7
- Conferir os limites atuais da hospedagem escolhida.
  - Se o modelo denso não couber, publicar com BM25 + interpretação e registrar no
    CLAUDE.md.
- **Push e publicação só com autorização explícita.**
- **Aceite:** URL pública funcionando, registrada no CLAUDE.md.

---

## Fase 6 — Documento (humano no comando)

### [ ] T10 Seções novas do .docx
O agente **rascunha**, mas não substitui o texto, nas seguintes partes:
- resumo/abstract;
- objetivos 6 e 7;
- 2.6 (RI e avaliação de ranking);
- 3.7 reescrita + 3.9 e 3.10 novas;
- limitações (A4, A7, A8, haversine, fluxos ≠ necessidade).

Padrão de formatação conforme CLAUDE.md. Toda referência nova deve ser **confirmada**
(autor, ano, veículo), ou o rascunho deve marcá-la como "[A CONFIRMAR]".

---

## Cronograma de referência (ajustar quando D0 for respondida)

| Semana | Fases | Entregável para o orientador |
|---|---|---|
| 1 | 0, T1.1–T1.2 | repositório + serviços reproduzindo A2 |
| 2 | T1.3–T1.6 | demanda conferida com TabNet |
| 3 | Fase 2 | mapa de acessibilidade + clusters |
| 4 | Fase 3 | motor respondendo às duas portas |
| 5 | Fase 4 | tabela de avaliação |
| 6 | Fase 5 + T10 | página no ar + seções do documento |

Divisão sugerida para 3 pessoas:
- **(A) dados e núcleo:** Fases 1 e 2
- **(B) motor e avaliação:** Fases 3 e 4. Começa na semana 2 com dados de 202609.
- **(C) documento, consultas de planejamento e página:** T4.1 (consultas), T10, T5.2
