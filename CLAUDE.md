# CLAUDE.md — TG Desertos de Cuidado em Álcool e Outras Drogas

Este arquivo é carregado automaticamente em toda sessão do Claude Code neste projeto.
Mantenha-o atualizado conforme o trabalho avança: ele é a memória do projeto.

**Mapa dos documentos:**
- este arquivo: regras + estado atual
- [docs/ARQUITETURA.md](docs/ARQUITETURA.md): o que construir e por quê, com achados, desenho e decisões pendentes
- [docs/PLANO_EXECUCAO.md](docs/PLANO_EXECUCAO.md): tarefas em ordem, com critérios de aceite

Em caso de conflito, **os achados empíricos da ARQUITETURA §1 prevalecem** sobre premissas
antigas.

---

## COMO QUERO QUE VOCÊ SE COMPORTE

Seja criticamente honesto. Antes de propor qualquer coisa, questione a própria proposta,
procure o furo, valide com busca na web quando a afirmação for verificável, e me diga
quando algo que eu quero fazer já existe ou não se sustenta. Não invente referência
bibliográfica nenhuma — se não puder confirmar autor, ano e veículo, diga que não
confirmou. Não me elogie por reflexo. Se eu estiver indo para um caminho ruim, fale.

---

## QUEM SOU E ONDE ESTOU

Sou aluno do Curso Superior de Tecnologia em **Ciência de Dados** na **FATEC Santana de
Parnaíba** (Centro Paula Souza), São Paulo. Estou fazendo meu **TG** (Trabalho de
Graduação), entrega prevista para **2026** (data exata a confirmar — decisão D0).

**Grupo de três integrantes:**
- Luís Davi Gomes de Santana
- Gabriel Domingues Fernandes
- Eloi Pires de Souza Ibiapino Filho

**Orientador:** Professor Ivan Souza (direção ainda aberta, não impôs tema).

**Meu perfil técnico:** sou "vibe coder", entendo Python mas não domino a fundo. Prazo
apertado.

---

## O PROJETO (estado entregue ao professor)

**Tema:**
> Desertos de cuidado em álcool e outras drogas: análise do gap entre demanda assistencial
> e cobertura de CAPS AD nos municípios do estado de São Paulo por meio de Ciência de Dados

**Pergunta de pesquisa:**
> Quais municípios do estado de São Paulo apresentam maior desproporção entre a demanda
> assistencial por transtornos decorrentes do uso de álcool e outras drogas e a oferta de
> Centros de Atenção Psicossocial Álcool e Drogas (CAPS AD), e quais características
> socioeconômicas caracterizam essas regiões?

**Objetivo geral:** identificar e mapear, por técnicas de Ciência de Dados, os municípios
paulistas com maior desproporção entre demanda assistencial por transtornos relacionados a
álcool/drogas e oferta de CAPS AD.

**Objetivos específicos no documento entregue (6):**
1. Coletar, tratar e integrar DATASUS, CNES e IBGE em dataset municipal unificado
2. Caracterizar o perfil da demanda por sexo, faixa etária e distribuição geográfica
3. Construir Índice de Cobertura Assistencial (ICA) com **exclusivamente** oferta,
   população e demanda
4. Aplicar K-Means sobre indicadores assistenciais, **reservando** as variáveis
   socioeconômicas para caracterização posterior
5. Analisar associação entre indicadores socioeconômicos e a classificação obtida
6. Desenvolver dashboard interativo com visualização geográfica → **será reescrito**
   (motor de busca) + **objetivo 7** novo (avaliação quantitativa)

**Recorte:** 645 municípios de SP; período 2019–2024; CID-10 F10–F19; CAPS AD como
equipamento de referência (camadas de sensibilidade em discussão, D1).

**Estrutura do documento entregue (19 páginas):** capa, folha de rosto, resumo, abstract,
sumário, 1 Introdução (1.1–1.6), 2 Referencial Teórico (2.1–2.5), 3 Metodologia
(3.1–3.8), 4 Análises e Resultados (vazio), 5 Considerações Finais (vazio), Referências.

---

## ESTADO ATUAL (atualize a cada tarefa concluída)

**Última atualização:** 23/10/2026

- ✅ Diagnóstico de viabilidade executado com dado estruturado. Ver ARQUITETURA §1.
  O `diagnostico_viabilidade.py` original foi **abandonado**: dependia da API inacessível e
  inferia modalidade por nome com bugs.
- ✅ Ambiente: `.venv` (Python 3.12, via `uv`), `requirements.txt`.
- ✅ Dados de diagnóstico em `dados/bruto/`, saída em `dados/tratado/caps_sp_202609.csv`.
- ✅ Arquitetura e plano escritos em `docs/`.
- ✅ **Fase 0 e Fase 1 concluídas (T0.1–T1.6)** em 23/10/2026. 33 testes passando
  (`.venv\Scripts\python.exe -m pytest -q`). Tabelas em `dados/tratado/`:
  `municipios`, `populacao`, `servicos`, `internacoes`, `internacoes_fluxo`, `obitos`,
  `raas_carga`, `raas_fluxos`, `distancias`. Reconstruir: `python pipeline.py coleta
  territorio servicos internacoes obitos raas distancias`.
- ✅ Internações e óbitos conferidos contra o **TabNet oficial** (internações −0,14% a
  −0,30%; óbitos 0,0%). Scripts em `scripts/exploracao/conferir_tabnet_*.py`.
- ✅ **T2.1 concluída**; **T2.2 e T2.3 implementadas de forma provisória** (`[~]` no plano:
  rodam com a recomendação O1 + E2SFCA, mas D1/D2/D3 ainda são do grupo). 47 testes.
  Reconstruir: `python pipeline.py demanda acessibilidade`.
- ⚠️ **Resultado que muda a conversa com o Prof. Ivan (ARQUITETURA A23):** o E2SFCA tem
  validação externa fraca (ρ parcial ≈ −0,10) e **não prevê melhor que a oferta pura**.
  O plano original tinha um viés mecânico (persistência da demanda, ρ = 0,84), já corrigido
  com correlação parcial. Defender o E2SFCA como ferramenta conceitual (acesso entre
  fronteiras + `R_j` para a porta de referência), não como índice validado.
- ⚠️ A22: a "demanda" por internação reflete polos hospitalares (ex.: Pinhal, 18× a média).
- ✅ **Site estático pronto em `web/`** (mapa + busca Planejamento/Referência + Sobre),
  para a **Vercel** (Root Directory = `web`). Guia em `docs/PUBLICACAO.md`. **Mudança de
  arquitetura:** a Vercel não hospeda Streamlit, então o site é HTML/JS lendo `web/data/*.json`
  (gerado por `python pipeline.py publicar`). Rotulado "Versão preliminar"; os pesos de
  referência (`web/data/meta.json`) NÃO foram avaliados. **No ar em https://tg-red.vercel.app**
  (publicado em 23/10/2026; código em github.com/GabsDomin/tg). Atualizar:
  `npx vercel deploy --prod --yes` dentro de `web/` (ver docs/PUBLICACAO.md). O motor de busca real, com recuperação semântica e avaliação (Fases
  3–4), ainda não existe: a busca atual é por nome + necessidade, em JS.
- ✅ **T2.4, T2.5, T4.1 e T4.2 da porta de referência concluídas** (73 testes). Ver
  `docs/resultados_clusters.md` e `docs/resultados_avaliacao.md`.
- ⚠️ **RESULTADO NEGATIVO CENTRAL (ARQUITETURA A26):** na avaliação contra fluxos reais
  2023–24, o sistema de referência **não supera "só distância"** de forma significativa
  (NDCG@5 0,726 vs 0,705; IC95% da diferença inclui 0) e a **folga (ICA/E2SFCA) tem peso
  zero**. O que prevê é a **região de saúde**. O site foi atualizado: score = proximidade
  0,3 + mesma região 0,5 + abertura 0,2; a folga aparece só como informação. **Isso muda a
  narrativa do TG**: a contribuição passa a ser a avaliação honesta, a tipologia e a
  caracterização, não "o buscador que sabe quem está lotado". Levar ao Prof. Ivan.
- ✅ **MOTOR DE BUSCA implementado e no ar** (23/10/2026): `web/js/busca.js` (BM25 + interpretação de
  linguagem natural + ranqueamento explicável; corpus de 822 documentos; sem IA generativa e **sem
  busca semântica por vetores**). Interface redesenhada em torno da busca (`web/js/app.js`,
  `web/css/app.css`): chips "Como entendi" removíveis, cartões explicáveis, mapa interligado,
  autocompletar, correção de digitação, link compartilhável, tema escuro, mobile real.
  Avaliação: `docs/resultados_busca.md` — **rodada 1 (número a citar): NDCG@10 = 0,809**, +0,30 sobre
  BM25 puro (IC95% 0,18–0,42); rodada final 0,912 é otimista. Consultas escritas pelo assistente:
  **o grupo deve substituir/ampliar** (`avaliacao/LEIAME.md`). Testes: `pytest` (inclui o JS),
  `node scripts/busca/e2e.mjs <url> <pasta> tudo` (ponta a ponta, mobile 390x844 + desktop).
- 🚨 **PRAZO (descoberto em 23/10/2026):** o Termo T3 assinado (03/09/2026, em Downloads) fixa a
  **entrega da versão final em 16/10/2026** ("a não entrega reprova o trabalho"). O documento de
  15/10 (`TG_CAPS 1.docx`) tem os cap. 4 e 5 vazios. **Confirmar com o Prof. Ivan** se a data era do
  TG final ou de uma etapa e qual é a data vigente. O Termo T3 também **não cita motor de busca** (D0).
- ✅ **Rascunho dos cap. 4 e 5 pronto**: `docs/rascunho/TG_CAPS_rascunho_cap4_cap5.docx` (+ PDF), feito em
  CÓPIA do documento entregue (original intacto), mesmo padrão de formatação, sumário atualizado, 7
  tabelas e 3 figuras, trechos "[A CONFIRMAR]" em amarelo. Os cap. 1–3, resumo e abstract **não** foram
  alterados: ver `docs/ajustes_capitulos_1_a_3.md`.
- ⏳ Próxima: revisão do rascunho pelo grupo e pelo orientador; planejamento (porta 1) com recuperação textual e consultas escritas pelo grupo
  (T3.1–T3.3, T4.1); depois os capítulos 4 e 5 do documento (T10).
- (antigo) **T2.4** (K-Means) e **T2.5** (caracterização). Não começar a Fase 3 (motor de
  busca) antes de D0 (a exigência existe? qual a data?).
- ⛔ Pendente de humano: D0–D7 (ARQUITETURA §10). Prioridade: **D0** (exigência escrita
  e data de entrega) e **D3** (ICA espacial, alinhar com o Prof. Ivan).
- ⚠️ Achados novos que o grupo precisa conhecer (ARQUITETURA A12–A21): óbitos F1x de SP
  têm quebra de +72% em 2020 (causa desconhecida); população sem estimativa 2022/2023;
  conversor do CNES lista 62 regiões de saúde (documento diz 63); a oferta de CAPS AD
  cresceu 96 → 123 entre 2019 e 2026.

### Números-chave (CNES 2026-09; SIA/PS dez/2024)
- 649 CAPS em 293 municípios.
- **123 CAPS AD habilitados** (84 AD, 39 AD III, 0 AD IV) em **83 municípios**; 34 na
  capital.
- 125 CAPS sem nenhuma habilitação; 16 se chamam "AD", entre eles o CAPS AD IV Redenção.
- Coordenadas: 123/123 CAPS AD dentro do município declarado.
- Só 1,2% dos atendimentos em CAPS AD são de residentes de outro município.
- 1.627 residentes de 178 municípios sem CAPS AD foram tratados por F10–F19 em algum CAPS
  (sobretudo CAPS I).

---

## O MOTOR DE BUSCA (exigência do curso)

O curso exige um motor de busca. **Ainda não está confirmado** se a exigência está escrita
na rubrica ou plano de ensino (D0). Desenho completo na ARQUITETURA §6–7. Em resumo:

- **Duas portas:**
  - **planejamento:** municípios ranqueados por necessidade, com consulta em linguagem
    natural;
  - **referência:** dado um município, serviços *acessíveis de fato*, ranqueados por
    proximidade, região de saúde, abertura observada, adequação de modalidade e folga.
- **Mudança em relação ao desenho anterior:** os fluxos reais (SIA/PS) mostraram que o
  encaminhamento intermunicipal é raro. Ranquear "o mais próximo não lotado" sem considerar
  pactuação recomendaria serviços inacessíveis.
- **Avaliação principal da referência:** fluxos observados em 2023–24, como gabarito
  automático e sem circularidade (features de 2019–22). Isso **substitui** o painel de
  especialista como camada principal; o especialista vira opcional (D5).
- **Métricas:** P@k, MRR, NDCG@k, com baselines (distância, população, persistência) e
  ablação.

---

## BASES DE DADOS — VERIFICADAS

| Camada | Base | Acesso que funciona |
|---|---|---|
| Demanda | SIH/SUS RD (internações F10–F19, residência) | FTP DATASUS `SIHSUS/200801_/Dados/RDSPaamm.dbc`, 2019–2024 ok |
| Demanda | SIM DO (óbitos) | FTP `SIM/CID10/DORES/DOSPaaaa.dbc`, 2019–2024 ok |
| Atendimento realizado | SIA/SUS PS (RAAS psicossocial) | FTP `SIASUS/200801_/Dados/PSSPaamm.dbc`. Tem `CNES_EXEC`, `MUNPAC`, `CIDPRI`, `TP_DROGA`, `SIT_RUA`. **Não é medida de demanda** |
| Oferta | CNES ST/HB/LT | FTP `CNES/200508_/Dados/{ST,HB,LT}/`, até 2026-09 |
| Oferta | Códigos de habilitação | `TAB_CNES.zip` → `DBF/HABILITA.DBF`: 0619 AD, 0635 AD III, 0637 AD IV, 0616 I, 0617 II, 0618 III, 0620 i |
| Coordenadas | OpenDataSUS `cnes_estabelecimentos.zip` (S3, jun/2025) | tem `NU_LATITUDE`/`NU_LONGITUDE`, validadas contra a malha |
| Contexto | Censo 2022, malhas (API v3) | IBGE ok |
| Contexto | PNS 2019 | **só nível estadual — não serve para análise municipal** |

**Não funciona daqui:** `apidadosabertos.saude.gov.br` (conexão resetada). O portal
OpenDataSUS redireciona para `dadosabertos.saude.gov.br`.

**Correção de premissa antiga:** o CNES (extração OpenDataSUS) **traz coordenadas**. Não é
preciso geocodificar, nem usar o dataset do Kaggle. A limitação a declarar é outra:
distância haversine, não por estrada, e 17 CAPS recentes sem coordenada no arquivo de
jun/2025.

---

## DECISÕES JÁ TOMADAS E POR QUÊ (não reabrir sem motivo)

**Por que álcool e drogas e não depressão.** O CAPS AD atende exclusivamente esse público,
então "demanda por AD" × "oferta de CAPS AD" é uma razão que faz sentido matemático. No
CAPS adulto, o denominador mistura depressão, ansiedade, bipolaridade e esquizofrenia.
Além disso F10–F19 gera muito mais internação no SIH que F32/F33, e depressão + PNS + ML
já foi feito.

**Por que ansiedade foi descartada.** Quase não gera internação nem óbito e frequentemente
nem chega ao CAPS. É a condição mais difícil de rastrear em dados administrativos do SUS.

**Por que a PNS não é fonte primária.** Só tem representatividade para grandes regiões,
UFs, capitais e RMs.

**Por que a vulnerabilidade não entra no ICA.** Evita circularidade: o índice mede
adequação oferta/demanda; a vulnerabilidade é usada só na caracterização dos clusters.

**Por que o gabarito normativo não pode ser a avaliação principal.** População é insumo do
ICA; a baseline "ordenar por população" iria bem demais contra ele.

**Por que RAAS/PS não é demanda (23/10/2026).** A produção existe onde há serviço. Usá-la
como demanda faria a oferta explicar a demanda. A demanda vem de SIH + SIM, por residência.

**Por que corte temporal 2019–22 / 2023–24 no motor (23/10/2026).** É o que impede que o
gabarito seja construído com os mesmos dados que o ranking.

**Por que modalidade sai de habilitação (23/10/2026).** O nome fantasia omite a modalidade
em mais da metade dos CAPS AD, e a regex casa "CAPS ADULTO".

---

## O QUE JÁ EXISTE LÁ FORA (verificado — não repetir)

- **Mapa interativo da RAPS do Ministério da Saúde** (2020), com 3.164 serviços
- **mapasaudemental.com.br**
- **Guia privado** com 4.765 serviços e filtro por CEP/estado/cidade/tipo
- **Busca Saúde CAPS do DF** (CEP → unidade de referência)
- **Miliauskas et al. (2019)**, Ciência & Saúde Coletiva, v.24, n.5, p.1935-1944 —
  cobertura de CAPS × internações psiquiátricas nas RMs do RJ e SP

Todos esses ranqueiam por proximidade. O espaço do projeto: acessibilidade espacial com
demanda, pressão assistencial, fluxos reais e avaliação medida. Miliauskas é fundamentação:
o escopo aqui é estadual, o método é clusterização + recuperação, e o produto é índice +
sistema.

---

## RISCOS QUE EU JÁ CONHEÇO

- **Escopo/prazo:** linhas de corte na ARQUITETURA §11. Nunca cortar a porta de referência
  nem a avaliação.
- **Corpus pequeno:** cerca de 1.500 documentos (municípios, regiões, serviços). A defesa é
  a função de ranqueamento + avaliação. Não inflar com UBS.
- **Granularidade:** 562 de 645 municípios sem CAPS AD. O ICA espacial (E2SFCA) e a Região
  de Saúde tratam isso.
- **Municípios pequenos:** suavização Bayesiana empírica + agregação plurianual.
- **Residência vs. internação:** usar residência para demanda.
- **Ética/LGPD:**
  - página voltada a gestão, com aviso e CVV 188 / SAMU 192;
  - só agregados publicados, com supressão <5;
  - `CNS_PAC` nunca persistido;
  - a seção 3.8 invoca a Resolução CNS 510/2016 (dispensa de CEP para dados públicos
    agregados).

---

## REFERÊNCIAS JÁ VALIDADAS NO DOCUMENTO

Lei 10.216/2001 · Portaria GM/MS 336/2002 · Portaria GM/MS 3.088/2011 · Resolução CNS
510/2016 · Portaria de Consolidação 3/2017 · Portaria SAS/MS 544/2018 (cria CAPS AD IV no
CNES) · CNES · CAPS/MS · DATASUS TABNET · HAIR JUNIOR et al. (2009) · IBGE Censo 2022 ·
IBGE Malhas · IBGE PNS 2019 · JESUS; ASSIS (2010) · MACQUEEN (1967) · MILIAUSKAS et al.
(2019) · PEREIRA et al. (2022) · WHO CID-10 (2019)

**A confirmar antes de usar:**
- edição do Hair Junior;
- limiares populacionais da Portaria 336/2002;
- Manning, Raghavan e Schütze (2008) para a seção 2.6;
- Luo e Wang (2003) — 2SFCA;
- Luo e Qi (2009) — E2SFCA;
- referência para RRF (Cormack et al., 2009);
- referência para NDCG (Järvelin e Kekäläinen, 2002);
- se a Portaria 3.088/2011 atribui ao CAPS I o atendimento a usuários de álcool e drogas.

---

## CONVENÇÕES DESTE REPOSITÓRIO

**Stack:** Python 3.12 em `.venv` (criado com `uv`).
- pandas + `pyreaddbc`/`dbfread` para `.dbc`;
- geopandas;
- scikit-learn;
- `rank_bm25` + `sentence-transformers` para busca;
- plotly/folium;
- streamlit.

Rodar: `.venv\Scripts\python.exe -I <script>`, com `PYTHONIOENCODING=utf-8`.

**Reprodutibilidade é requisito do TG.** Tudo que altera dado tem que estar em script.

**Dados:**
- `dados/bruto/` é imutável e fora do git;
- `dados/tratado/` é gerado por script e fora do git;
- `dados/publicar/` tem só agregados com supressão e é o único que vai para a página.

**Ao escrever no documento .docx**, mantenha o padrão existente:
- estilo `Heading2` nos títulos de subseção;
- corpo em Arial 12pt, entrelinha 1,5, recuo de primeira linha de 1,25 cm, justificado;
- referências ABNT, sem recuo e com espaçamento simples;
- valide o XML após editar.

**Nunca invente referência bibliográfica.** Se não puder confirmar autor, ano e veículo,
diga que não confirmou.

**Antes de citar um limiar normativo**, confirme no texto da portaria.

**Antes de usar um código de domínio** (habilitação, leito, CID, tabela SIDRA), confira na
tabela oficial e registre a fonte no `config.yaml`.
