# Resultados: avaliação da porta de referência

> Gerado em 23/10/2026 por `python pipeline.py avaliacao_referencia`. Código:
> `src/tg/avaliacao/`. Semente 20261023. Tabelas em `dados/tratado/avaliacao_referencia_*.csv`.

## 1. Protocolo

- **Consulta:** município de origem **sem CAPS AD habilitado** (dez/2022) e com ≥ 1 paciente F1x
  tratado em algum CAPS AD candidato em 2023–24. **219 consultas.**
- **Candidatos:** CAPS AD habilitados em dez/2022 a até 150 km (mediana 15 por consulta).
- **Relevância (gabarito):** pacientes F1x únicos origem → serviço em **2023–24**, em faixas
  (0 / 1–4 / 5–19 / 20+ → 0 a 3). 171 das 219 consultas têm **um único** serviço relevante.
- **Atributos do ranking:** só dados de **2019–2022** (corte temporal: sem circularidade).
- **Divisão:** 50% desenvolvimento (calibra pesos por grade, passo 0,1) / 50% teste (só reporta).
- **Métricas:** NDCG@5 (ganho exponencial 2^rel − 1; o `sklearn` usa ganho linear), MRR, P@5.
  Empates: menor distância primeiro.
- **IC 95%:** bootstrap pareado (2.000 reamostras) sobre as consultas de teste.

## 2. Resultado principal (110 consultas de teste)

| método | NDCG@5 | MRR | P@5 |
|---|---|---|---|
| só população do destino | 0,220 | 0,218 | 0,087 |
| **só distância** (o que os buscadores existentes fazem) | **0,705** | 0,713 | 0,191 |
| só mesma região (depois distância) | 0,724 | 0,724 | 0,196 |
| **SISTEMA** (pesos calibrados no dev) | **0,726** | 0,729 | 0,195 |
| persistência (fluxo 2019–22 do próprio município) | 0,789 | 0,827 | 0,198 |
| SISTEMA + histórico | 0,802 | 0,823 | 0,207 |

Diferença de NDCG@5 contra "só distância" (IC 95%):

| | diferença | IC 95% |
|---|---|---|
| SISTEMA | **+0,021** | [−0,021; +0,065] — **não significativa** |
| só mesma região | +0,019 | [−0,012; +0,053] — não significativa |
| persistência | +0,084 | [+0,046; +0,126] |
| SISTEMA + histórico | +0,097 | [+0,054; +0,142] |

Em 50 divisões repetidas, NDCG@5 médio no teste: só distância 0,734 (dp 0,020), persistência 0,811
(dp 0,020), sistema 0,767 (dp 0,020). A vantagem do sistema sobre a distância é pequena e sensível
à divisão.

## 3. O que o sistema calibrou

Pesos (dev): proximidade 0,4 · **mesma região 0,5** · adequação **0,0** · **folga 0,0** · abertura 0,1.
Pesos de produção (todas as consultas): proximidade 0,3 · mesma região 0,5 · abertura 0,2 ·
adequação 0 · folga 0.

**Ablação** (cada componente removido, pesos recalibrados no dev; NDCG@5 no teste):

| sem… | NDCG@5 |
|---|---|
| (sistema completo) | 0,726 |
| proximidade | 0,724 |
| **mesma região** | **0,703** (maior queda) |
| adequação | 0,726 |
| **folga** | **0,726** (nenhuma mudança) |
| abertura | 0,717 |

## 4. Leitura honesta

1. **A hipótese central da porta de referência não se confirmou.** A ideia era "o serviço mais
   próximo que não está sobrecarregado". A **folga** (pressão estimada do território de destino, via
   E2SFCA) teve **peso zero** e removê-la não altera nada. O ICA/E2SFCA **não funciona como sinal de
   ranqueamento** de encaminhamento neste conjunto de dados.
2. **O que prevê para onde as pessoas vão é a região de saúde** (pactuação), em linha com o achado de
   que só 1,2% dos atendimentos em CAPS AD são de moradores de outro município.
3. **O sistema não supera a distância de forma estatisticamente significativa.** Isso vale ser dito
   com todas as letras, inclusive no texto do TG.
4. **Persistência vence** (0,789) e, nos municípios com histórico, chega a 0,928; no *cold-start*
   (n = 31) o sistema (0,526) fica à frente da distância (0,486) e da persistência (0,437), mas com
   amostra pequena demais para conclusão.
5. O teto das métricas é baixo porque 78% das consultas têm um único relevante e o serviço mais
   próximo já é relevante em 62%.

## 5. Limitações

- **Fluxo observado ≠ necessidade.** Mede para onde as pessoas *foram*, que depende de pactuação,
  transporte e oferta. Um serviço lotado pode receber muitos pacientes; ele continua relevante no
  gabarito.
- Só serviços existentes em dez/2022 são candidatos: CAPS abertos depois (103 → 115 até 2024) ficam
  fora, e fluxos para eles não contam.
- Amostra pequena (110 de teste): ICs largos.
- O desempenho "SISTEMA + histórico" mede o valor do histórico, não de um critério de recomendação.
- A calibração em grade com 109 consultas de desenvolvimento pode superajustar; as divisões repetidas
  mitigam, mas não eliminam.
- Os pesos de produção, calibrados em todas as consultas, têm NDCG@5 = 0,78 *in-sample* (otimista).
- O gabarito não foi julgado por especialista da RAPS (decisão D5 em aberto).
