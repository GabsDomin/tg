# Motor de busca: desenho e avaliação

> Código: `web/js/busca.js` (o **mesmo** módulo roda no site e na avaliação). Avaliação:
> `scripts/busca/avaliar_busca.mjs`. Consultas: `avaliacao/consultas_busca.json`. Resultados:
> `avaliacao/resultados_busca_rodada1.json` e `web/data/avaliacao_busca.json` (final).
> Testes: `scripts/busca/testes_motor.mjs` (rodam dentro do `pytest`); site: `scripts/busca/e2e.mjs`.

## 1. O que é

Um motor de recuperação de informação sobre um corpus próprio, **sem IA generativa**, explicável:

1. **Corpus** — 822 documentos de texto gerados dos indicadores: 645 municípios, 62 regiões de saúde e
   115 CAPS AD habilitados (dez/2024).
2. **Interpretação** — normalização (acento, caixa, pontuação), reconhecimento de entidades por
   dicionário (municípios, regiões e apelidos como "Alto Tietê"), grupos ("interior", "litoral", "Grande São
   Paulo" = os 39 municípios da RMSP), filtros por regras (porte, "sem CAPS AD", "alta internação" etc.),
   ordenação ("maior", "pior"), modalidade ("CAPS AD III") e intenção (planejamento, regiões, serviços,
   encaminhamento, perfil).
3. **Recuperação** — BM25 (k1 = 1,2; b = 0,75) para os termos livres + filtros duros dos critérios entendidos;
   correção de erro de digitação de uma letra.
4. **Ranqueamento explicável** — planejamento: necessidade (baixo acesso 50% + alta internação 50%)
   combinada ao texto; encaminhamento: pesos calibrados contra fluxos reais (ver `resultados_avaliacao.md`).
   Cada resultado mostra a decomposição do score.

Definições dos filtros: porte pequeno < 20 mil, médio 20–100 mil, grande ≥ 100 mil; "alta/baixa" =
terço superior/inferior do estado; "longe" = a mais de 60 km do CAPS AD mais próximo; "deserto de cuidado" =
acessibilidade no quintil inferior e internação ≥ mediana (66 municípios, 1.105.988 habitantes).

**Não implementado:** busca semântica por vetores (embeddings). Fica como trabalho futuro; o motor é
BM25 + regras.

## 2. Protocolo de avaliação

- **Sem circularidade temporal:** o motor só enxerga atributos de 2019–2022 (`dados.motor`); o gabarito usa
  desfechos de 2023–2024 (`dados.gabarito`).
- **Gabarito independente do parser:** cada consulta tem uma especificação *semântica* (região, grupo,
  filtros, ordenação) e o gabarito é calculado por código separado do motor, sobre os dados de 2023–24.
- **Relevância graduada:** pertencer ao conjunto pedido = 1; dentro dele, terço superior da ordem pedida
  (padrão: necessidade medida em 2023–24) = 2 e 3; navegacional: 3 só para o alvo; "perto": 3/2/1 por faixa
  de distância (≤ 25 / ≤ 50 / ≤ 100 km).
- **Métricas:** NDCG@10 (ganho 2^rel − 1), P@10, MRR; IC 95% por bootstrap pareado (2.000 reamostras).
- **Baselines:** BM25 puro (consulta crua sobre o corpus), só necessidade (ignora a consulta) e
  BM25 + necessidade sem interpretar.
- **58 consultas:** 30 de planejamento (municípios), 6 de regiões, 8 de serviços, 6 navegacionais
  (inclui 2 com erro de digitação ou sem acento) e 8 de encaminhamento (só interpretação). 2 consultas que
  usam a tipologia ficam só na interpretação (a tipologia usa dados de 2023–24).
- Consulta com **gabarito vazio** (nenhum item satisfaz a consulta em 2023–24; ocorreu com P22) tem NDCG
  indefinido e é excluída do ranqueamento. Essa regra foi adotada **depois** de ver o resultado.

## 3. Resultados (NDCG@10)

| grupo | n | **motor (rodada 1)** | motor (final) | BM25 puro | só necessidade | BM25+necess. |
|---|---|---|---|---|---|---|
| planejamento (municípios) | 27–28 | 0,759 | **0,850** | 0,320 | 0,213 | 0,360 |
| regiões | 6 | 0,832 | **0,993** | 0,666 | 0,645 | — |
| serviços | 8 | 0,948 | **0,992** | 0,828 | — | — |
| navegacional | 6 | 0,833 | **1,000** | 0,833 | 0,000 | 0,333 |
| **geral** | 47–48 | **0,809** | 0,912 | | | |

- **Rodada 1 (estimativa não enviesada): NDCG@10 = 0,809**; P@10 = 0,573; MRR = 0,865.
  Interpretação: intenção correta em 95%, interpretação exata em 88% (precisão 93%, revocação 93%).
  Diferença contra BM25 puro: **+0,304 (IC 95% 0,181 a 0,421)**; contra só necessidade +0,540
  (0,418 a 0,668); contra BM25 + necessidade sem interpretar +0,427 (0,294 a 0,558).
- **Rodada final: NDCG@10 = 0,912** (P@10 = 0,643; MRR = 0,968); interpretação exata em 100%. Diferença
  contra BM25 puro +0,395 (0,284 a 0,507).

### O que foi corrigido entre as rodadas
Após a rodada 1 foram corrigidos **sete pontos**, todos defeitos reais, não ajustes às respostas:
1. "Grande São Paulo" era lida como o município/região "São Paulo" (entidade extraída antes do grupo);
2. "região de Campinas" não usava a região de saúde do município citado;
3. "a taxa de internação é **maior**" (adjetivo depois do substantivo) não era entendido;
4. uma regra de "perto de" consumia "serviço mais próximo de X" antes da regra de encaminhamento;
5. faltava correção de digitação ("Itanhaen");
6. "**alto** acesso" não era reconhecido (só "alta/boa");
7. "**regiões** com municípios sem CAPS" era lida como consulta de municípios.
E um defeito do avaliador: gabarito vazio (acima).

**Por que a rodada 1 é o número a citar:** as mesmas 58 consultas orientaram as correções, então a
rodada final é otimista, e o 100% de interpretação reflete isso. As consultas foram escritas pelo
assistente que construiu o motor, antes de rodá-lo, mas **não por usuários reais** nem por especialista.

### Falhas que restam
- **P17** ("municípios com CAPS AD e baixa acessibilidade", 1 relevante) e **P25** (104 relevantes): falham
  por **mudança temporal**, não por leitura. O que era "baixa acessibilidade" em 2019–22 não é o mesmo em
  2023–24. Isso é uma limitação do gabarito (e da própria definição de "baixa"), não um erro do parser.
- P@10 é baixo em serviços e navegação porque há poucos itens relevantes (teto da métrica).

## 4. Limitações
- Consultas escritas pelo desenvolvedor; **o grupo deve substituir e ampliar** (formato em `avaliacao/LEIAME.md`).
- Gabarito derivado de indicadores, sem julgamento de especialista da RAPS.
- Amostra pequena por grupo (6 a 8 consultas em três deles).
- O motor entende as formas de linguagem implementadas; frases livres arbitrárias podem falhar.
- Sem busca semântica (embeddings).
