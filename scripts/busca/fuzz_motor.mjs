// Robustez do motor: entradas hostis/aleatorias nao podem lancar excecao, travar (ReDoS) nem violar invariantes.
// Uso: node scripts/busca/fuzz_motor.mjs
import { readFileSync } from "node:fs";
import { criarMotor } from "../../web/js/busca.js";

const ler = (n) => JSON.parse(readFileSync(new URL(`../../web/data/${n}.json`, import.meta.url), "utf-8"));
const motor = criarMotor({ municipios: ler("municipios"), regioes: ler("regioes"), servicos: ler("servicos"), meta: ler("meta") });

let excecoes = 0, lentas = 0, piorMs = 0, piorTxt = "";
function roda(txt, rotulo = "") {
  const t0 = performance.now();
  try {
    const r = motor.buscar(txt);
    // invariantes: filtros ativos satisfeitos e scores nao crescentes (planejamento)
    if (r.interpretacao.intencao === "planejamento" && !r.interpretacao.ordenacao) {
      for (const x of r.resultados) for (const f of r.interpretacao.filtros) if (!f.fn(x.dados)) throw new Error(`invariante violada: ${x.titulo} vs ${f.id}`);
    }
    const sc = r.resultados.map((x) => x.score);
    for (let i = 1; i < sc.length; i++) if (sc[i] > sc[i - 1] + 1e-9) throw new Error("scores nao ordenados");
    if (r.resultados.some((x) => Number.isNaN(x.score))) throw new Error("score NaN");
  } catch (e) { excecoes++; console.log(`EXCECAO [${rotulo}] ${JSON.stringify(txt).slice(0, 80)} -> ${e.message}`); }
  const ms = performance.now() - t0;
  if (ms > piorMs) { piorMs = ms; piorTxt = `${rotulo}: ${JSON.stringify(txt).slice(0, 60)}`; }
  if (ms > 1000) { lentas++; console.log(`LENTA ${ms.toFixed(0)} ms [${rotulo}] ${JSON.stringify(txt).slice(0, 60)}`); }
}

// 1. entradas patologicas (candidatas a ReDoS)
const N = 20000;
const patologicas = {
  "vazio": "", "so espacos": " ".repeat(N), "so 'a'": "a".repeat(N), "digitos": "1".repeat(N), "digitos e espacos": "1 ".repeat(N / 2),
  "milhar repetido": "1.000 ".repeat(N / 6), "mais de N": "mais de " + "1 ".repeat(N / 2), "entre N e": "entre " + "1 e ".repeat(N / 4),
  "ENT repetido": "ENT ".repeat(N / 4), "mil repetido": "50 mil ".repeat(N / 7), "sem sem sem": "sem ".repeat(N / 4), "caps": "caps ad ".repeat(N / 8),
  "regex especial": "(((((.*+?[]{}\\^$|".repeat(500), "emoji": "😀🎉".repeat(2000), "acentos": "ãéíõç".repeat(4000), "quebras": "a\n\t\r".repeat(5000),
  "internacao": "taxa de internacao e ".repeat(N / 21), "sem atendimento": "sem atendimento registrado em caps ".repeat(N / 35),
  "nomes": "bauru assis registro ".repeat(N / 22), "tipologia": "polos medios sob pressao ".repeat(N / 25),
};
for (const [k, v] of Object.entries(patologicas)) roda(v, `patologica:${k}`);

// 2. fuzz aleatorio com vocabulario do dominio + ruido
const vocab = "municipios cidades regiao regioes sem com caps ad iii servico servicos pequenas pequeno grandes grande medias interior litoral grande sao paulo alta baixa internacao acessibilidade acesso longe perto mais menos maior menor pior melhor de do da em no na para onde encaminhar paciente de bauru assis registro campinas sorocaba itanhaem deserto cuidado priorizar acima abaixo entre 10 20 50 100 mil habitantes e ou taxa".split(" ");
let s = 20261029; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
const pick = (a) => a[Math.floor(rnd() * a.length)];
const ruido = ["", "", "", "!", "?", "...", "ç", "ã", "'", "-", "/", "%", "(", ")", "  ", "​", "İ"];
for (let i = 0; i < 4000; i++) {
  const n = 1 + Math.floor(rnd() * 14);
  let q = Array.from({ length: n }, () => pick(vocab) + pick(ruido)).join(" ");
  if (rnd() < 0.2) q = q.toUpperCase();
  if (rnd() < 0.1) q = q.replace(/[aeiou]/g, (c) => (rnd() < 0.2 ? "" : c));
  roda(q, "aleatoria");
}

console.log(`\n${Object.keys(patologicas).length} entradas patológicas + 4000 aleatórias | exceções: ${excecoes} | consultas > 1 s: ${lentas} | pior tempo: ${piorMs.toFixed(0)} ms (${piorTxt})`);
process.exit(excecoes || lentas ? 1 : 0);
