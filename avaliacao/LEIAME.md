# Como escrever as consultas de avaliação do motor de busca

O arquivo `consultas_busca.json` hoje tem 58 consultas **escritas pelo assistente** (rascunho). O
orientador pediu um conjunto de 40 a 60 consultas **do grupo** (ideal: de usuários reais, julgadas por quem
conhece a RAPS). Troque ou acrescente consultas seguindo o formato abaixo e rode:

```
node scripts/busca/avaliar_busca.mjs --rotulo "minhas consultas" --saida avaliacao/resultados_busca_minhas.json
```

Escreva as consultas **antes** de olhar o resultado do motor; se mudar o motor depois, registre a rodada.

## Formato de cada consulta
```json
{"id": "P99", "texto": "municípios sem CAPS AD na região de Assis", "escopo": "municipio",
 "regioes": ["Assis"], "sem_caps": true}
```
`texto` é a frase livre. Os demais campos são a **especificação semântica** (o que a frase *significa*), da
qual o gabarito é calculado com os dados de 2023–24.

| campo | valores | significado |
|---|---|---|
| `escopo` | `municipio`, `regiao`, `servico`, `nav`, `referencia` | o que se quer achar |
| `regioes` | lista de nomes de região de saúde | restringe à(s) região(ões) |
| `grupo` | `interior`, `grande_sp`, `litoral` | recorte geográfico |
| `sem_caps` / `com_caps` | `true` | sem / com CAPS AD habilitado |
| `deserto` | `true` | "deserto de cuidado" (cap. 4.7) |
| `porte` | `pequeno`, `medio`, `grande` | < 20 mil; 20–100 mil; ≥ 100 mil |
| `porte_min`, `porte_max` | número | acima de / abaixo de N habitantes |
| `porte_faixa` | `[a, b]` | entre a e b habitantes |
| `acesso` | `baixo`, `alto` | acessibilidade no terço inferior / superior |
| `internacao` | `alta`, `baixa` | taxa de internação no terço superior / inferior |
| `longe` | `true` | a mais de 60 km de um CAPS AD |
| `ordenar` | `necessidade`, `internacao`, `acesso` | ordem pedida (padrão: necessidade) |
| `municipio` | nome | alvo (navegação, serviços, encaminhamento) |
| `modalidade` | `AD III` | para serviços |
| `perto_de` | nome de município | serviços próximos de |
| `so_interpretacao` | `true` | avalia só a leitura da frase (não o ranking) |

Cuidados: (1) cada consulta precisa ter **ao menos um item relevante** em 2023–24, senão é excluída;
(2) consultas com `tipologia` só podem usar `so_interpretacao` (a tipologia usa dados de 2023–24);
(3) use os nomes de região exatamente como em `web/data/regioes.json`.
