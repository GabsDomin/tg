// Teste rapido do motor com os dados de PRODUCAO (web/data): imprime a interpretacao e o topo de cada consulta.
import { readFileSync } from "node:fs";
import { criarMotor } from "../../web/js/busca.js";

const ler = (n) => JSON.parse(readFileSync(new URL(`../../web/data/${n}.json`, import.meta.url), "utf-8"));
const motor = criarMotor({ municipios: ler("municipios"), regioes: ler("regioes"), servicos: ler("servicos"), meta: ler("meta") });
console.log("corpus:", motor.corpus);

const consultas = process.argv.slice(2).length ? process.argv.slice(2) : [
  "municípios sem CAPS AD na região de Assis", "cidades pequenas com alta internação e sem serviço", "onde priorizar CAPS AD no interior",
  "para onde encaminhar paciente de Registro", "CAPS AD III em Campinas", "regiões com maior taxa de internação",
  "desertos de cuidado na Alta Mogiana", "maiores municípios sem CAPS AD habilitado", "Bauru", "pinhal", "Sorocaba: municípios sem serviço",
  "municípios entre 20 e 50 mil habitantes sem CAPS AD", "pior acesso a CAPS AD no Vale do Ribeira", "CAPS AD perto de Jundiaí", "Registro", "Itanhaen",
];
for (const q of consultas) {
  const r = motor.buscar(q);
  const i = r.interpretacao;
  console.log(`\n» ${q}\n  intenção=${i.intencao} | entidades=[${i.entidades.map((e) => e.rotulo).join("; ")}] | filtros=[${i.filtros.map((f) => f.id).join(", ")}] | ord=${i.ordenacao?.chave ?? "-"} | residuais=[${i.residuais.join(" ")}]`);
  console.log(`  ${r.total} resultado(s) em ${r.ms.toFixed(1)} ms${r.avisos.length ? " | " + r.avisos.join(" | ") : ""}`);
  r.resultados.slice(0, 4).forEach((x, k) => console.log(`   ${k + 1}. [${x.tipo}] ${x.titulo} — ${x.subtitulo} (score ${x.score.toFixed(2)})`));
}
