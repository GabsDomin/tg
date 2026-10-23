# Resultados: tipologia de municípios (K-Means) e caracterização socioeconômica

> Gerado em 23/10/2026 por `python pipeline.py clusters censo caracterizacao`. Período: bloco de
> avaliação (2023–2024). Seed: 20261023. Todos os números abaixo saem de `dados/tratado/`.

## 1. Variáveis (só assistenciais)

`acesso` (E2SFCA relativo, O1, raio 60 km), `dist_ad` (km ao CAPS AD habilitado mais próximo),
`taxa_int` e `taxa_obito` (suavizadas, por 100 mil 15+), `atend_caps` (pacientes F1x em qualquer
CAPS por 100 mil 15+), `frac_fora` (fração desses pacientes tratada em CAPS de outro município).
Transformação: log(1+x) e z-score (`frac_fora` só z-score). **Variáveis socioeconômicas ficam fora.**

`atend_caps` e `frac_fora` vêm do SIA/PS: medem atendimento **realizado**, não demanda.

## 2. Escolha de k

| k | silhueta | ARI médio (bootstrap, 100) | menor grupo |
|---|---|---|---|
| 3 | 0,260 | 0,809 | 161 |
| 4 | 0,270 | 0,815 | 97 |
| **5** | **0,278** | **0,797** | **68** |
| 6 | 0,257 | 0,754 | 66 |
| 7 | 0,249 | 0,725 | 60 |
| 8 | 0,235 | 0,675 | 41 |

**k = 5**: maior silhueta, estabilidade ≈ 0,80 e nenhum grupo minúsculo. **A silhueta é baixa em
todos os k (< 0,3): os municípios formam um contínuo, não grupos naturais.** A tipologia é uma
ferramenta de leitura, não uma descoberta de classes. k = 4 é quase equivalente (silhueta 0,270 e
ARI 0,815); a diferença entre 4 e 5 não é decisiva e é uma escolha de interpretabilidade.

## 3. Perfil (medianas) e rótulos propostos

| grupo | n | acesso | km | internação | óbito | atend. CAPS | fração fora | pop. | rótulo proposto |
|---|---|---|---|---|---|---|---|---|---|
| 1 | 93 | 0,36 | 34,5 | 142 | 5,4 | 289 | 0,00 | 32,9 mil | Polos médios sob pressão |
| 2 | 214 | 0,38 | 39,9 | 65 | 4,5 | 0 | 0,00 | 7,8 mil | Pequenos sem atendimento registrado em CAPS |
| 3 | 184 | 0,43 | 33,3 | 92 | 4,5 | 35 | 1,00 | 7,1 mil | Pequenos que dependem de CAPS de outro município |
| 4 | 68 | 1,23 | 4,9 | 39 | 2,3 | 278 | 0,01 | 124 mil | Grandes centros com boa oferta |
| 5 | 86 | 2,01 | 15,5 | 23 | 5,5 | 15 | 0,01 | 38 mil | Médios com acesso alto e baixa internação |

Os **rótulos são interpretação nossa**; o algoritmo só devolve números. Um teste
(`tests/test_clusters.py`) falha se uma nova execução mudar o sentido dos grupos.

**Grupo 2 merece atenção:** 214 municípios (33%) sem nenhum paciente F1x registrado em CAPS.
Com estes dados **não dá para saber se é ausência de demanda ou ausência de cuidado**.

## 4. Caracterização socioeconômica (Censo 2022)

Tabelas SIDRA conferidas nos metadados: 6805 (esgoto por rede geral/pluvial), 10289 (rendimento
mediano de todos os trabalhos, 14+), 10062 (anos de estudo, 11+), 10135 (analfabetismo, 15+);
densidade = população 2022 / área.

| variável | ε² | grupos 1 / 2 / 3 / 4 / 5 (mediana) |
|---|---|---|
| renda mediana (R$) | 0,19 | 1.800 / 1.700 / 1.700 / 2.000 / 1.800 |
| anos de estudo | 0,25 | 9,5 / 9,1 / 9,1 / 10,3 / 9,6 |
| analfabetismo (%) | 0,23 | 3,9 / 5,3 / 5,1 / 3,0 / 3,8 |
| esgoto por rede (%) | 0,06 | 92 / 87 / 87 / 92 / 84 |
| densidade (hab/km²) | 0,36 | 64 / 28 / 28 / 834 / 131 |

Kruskal-Wallis com p ajustado por Holm < 0,001 em todas. ε² = H/(n−1).

**Leitura honesta:**
1. As diferenças são reais mas **moderadas** (ε² 0,19–0,25), e a maior é de **densidade**: o
   porte do município se mistura com tudo.
2. Controlando log(população), a acessibilidade continua associada a renda (ρ parcial +0,26),
   escolaridade (+0,21) e analfabetismo (−0,15), mas **não** a esgoto (−0,05; p = 0,17).
3. **Grupos 2 e 3 não se distinguem** (Dunn/Holm) em renda, escolaridade, analfabetismo nem
   densidade; o mesmo vale para os grupos 1 e 5. Eles diferem no **caminho do cuidado** (tratar
   fora ou não ter registro), não na condição socioeconômica.
4. **Internação praticamente não se associa** à vulnerabilidade socioeconômica nesta amostra
   (|ρ parcial| ≤ 0,13 para renda, escolaridade e analfabetismo), e a associação com esgoto (+0,27)
   tem sinal oposto ao esperado. Coerente com a limitação de que internação reflete polos
   hospitalares (ARQUITETURA A22).
5. São associações **ecológicas** (municípios), sem inferência causal nem individual.
