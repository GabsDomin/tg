# Ajustes necessários nos capítulos 1 a 3, resumo e abstract

> O rascunho `docs/rascunho/TG_CAPS_rascunho_cap4_cap5.docx` preenche só os capítulos 4 e 5 (e acrescenta
> as subseções 4.1–4.9 ao sumário). **Os capítulos 1 a 3 continuam como foram entregues** (tempo futuro,
> "dashboard", ICA genérico) e **ficam inconsistentes com o capítulo 4** até serem revisados. Abaixo, o que
> mudar. Nada foi reescrito sem decisão de vocês e do Prof. Ivan.

## Antes de tudo
- O **Termo T3 assinado (03/09/2026) fixa a entrega da versão final em 16/10/2026**, e o documento de
  15/10 tem os capítulos 4 e 5 vazios. Confirmar com o Prof. Ivan se essa data era do TG final ou de uma
  etapa, e qual é a data de entrega/apresentação vigente.
- O Termo T3 **não menciona motor de busca**. A exigência (D0) continua sem confirmação escrita.

## Resumo e abstract
- Trocar o tempo futuro ("integrará", "pretende-se") por passado e acrescentar os resultados principais.
- Trocar "dashboard interativo" por "painel interativo com mapa e consulta de municípios e serviços".
- Citar: tipologia de 5 grupos; 66 municípios com maior desproporção; e o resultado da avaliação do
  ranqueamento (não superou a distância de forma significativa).
- Mesma revisão no *abstract*.

## 1.4 Objetivos específicos
- **Objetivo 6** (reescrever): "Desenvolver um painel interativo com visualização geográfica e consulta de
  municípios e de serviços de referência."
- **Objetivo 7** (novo): "Avaliar quantitativamente o ranqueamento de referência com métricas de
  recuperação de informação e fluxos observados de pacientes."

## 1.5 Delimitação
- Explicitar que "CAPS AD" significa **habilitado no CNES** (códigos 0619, 0635, 0637).

## 1.6 Limitações (acrescentar)
- A taxa de internação reflete **polos hospitalares** (ex.: Espírito Santo do Pinhal), não só necessidade.
- Fluxos observados de pacientes ≠ necessidade.
- Quebra não explicada na série de óbitos de 2020 (+72% em SP).
- População de 2022 (Censo) e 2023 (interpolada); descontinuidade 2021→2022.
- Gabarito da avaliação não julgado por especialista da RAPS.
- Distâncias em linha reta.

## 2 Referencial teórico
- **2.2:** a habilitação 0619 chama-se "CAPS ÁLCOOL E DROGAS" (sem o "II"); conferir o texto da Portaria
  GM/MS 336/2002 antes de afirmar que ela corresponde ao CAPS ad II.
- **Nova 2.6 – Recuperação da informação e avaliação de ranqueamento:** fundamentar NDCG, MRR e
  precisão@k, protocolo com gabarito e corte temporal. Referência canônica sugerida: Manning, Raghavan e
  Schütze, *Introduction to Information Retrieval* (Cambridge, 2008) — **confirmar autor, ano e edição**.
- **Acessibilidade espacial (E2SFCA):** citar o método original (autores e ano **a confirmar**; não foram
  confirmados nesta sessão, por isso aparecem "[A CONFIRMAR]" no rascunho).
- Referências de Bayes empírico (Poisson-gama), Kruskal-Wallis, Dunn e ε² também **a confirmar**.

## 3 Metodologia
- **3.2:** o SIA/SUS entra como **atendimento realizado**, não como demanda; o SIM, só F10–F19.
- **3.3:** suavização por Bayes empírico; população 2022/2023; município de residência; divisão temporal
  2019–2022 (construção) e 2023–2024 (avaliação).
- **3.4 (ICA):** descrever as duas versões (municipal e E2SFCA), a capacidade por modalidade (mediana
  observada de pacientes/mês) e a validação por correlação parcial. Corrigir "oferta ponderada por
  modalidade" para essa definição.
- **3.5:** incluir as variáveis usadas no K-Means (acessibilidade, distância, internação, óbito, atendimento
  em CAPS e fração atendida fora do município) e k = 5 com silhueta e estabilidade.
- **3.6:** Kruskal-Wallis, Dunn com Holm, ε² e correlação parcial controlando o porte.
- **3.7 (reescrever):** painel web estático (Vercel) com duas consultas e dados públicos agregados.
- **Nova 3.9 – Protocolo de avaliação:** 219 consultas, gabarito 2023–24, atributos ≤ 2022, divisão
  desenvolvimento/teste, baselines, ablação, bootstrap pareado.

## Referências
- Acrescentar só as que forem **confirmadas** (autor, ano, veículo). Pendentes: E2SFCA, Manning et al.
  (2008), NDCG, Bayes empírico, Kruskal-Wallis/Dunn/ε².

## Como regenerar o rascunho
```
.venv\Scripts\python.exe -I scripts\documento\fechar_documento.py "<TG_CAPS 1.docx>" docs\rascunho\TG_CAPS_rascunho_cap4_cap5.docx <pasta_tmp>
```
Requer o Word instalado (paginação do sumário). O original nunca é alterado. Texto em
`scripts/documento/conteudo_cap4_cap5.py`.
