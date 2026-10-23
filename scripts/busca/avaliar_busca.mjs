// Avaliacao do motor de busca (porta de PLANEJAMENTO, regioes, servicos, navegacional + interpretacao da referencia).
//
// Uso: node scripts/busca/avaliar_busca.mjs [--rotulo "texto"] [--saida web/data/avaliacao_busca.json]
//
// Protocolo (sem circularidade temporal):
//  - o MOTOR so ve atributos de 2019-2022 (dados.motor); o GABARITO usa desfechos de 2023-2024 (dados.gabarito);
//  - o gabarito vem de uma especificacao semantica da consulta, calculada por codigo INDEPENDENTE do parser do motor;
//  - relevancia graduada: pertence ao conjunto pedido -> 1; terco superior da ordem pedida (padrao: necessidade
//    medida em 2023-24) -> 2 e 3; navegacional: 3 so para o alvo; "perto": 3/2/1 por faixa de distancia.
//  - metricas: NDCG@10 (ganho 2^rel - 1), P@10 (rel >= 1), MRR; IC95% por bootstrap pareado sobre as consultas.
import { readFileSync, writeFileSync } from "node:fs";
import { criarMotor, norm, distanciaKm } from "../../web/js/busca.js";

const arg = (k, d) => { const i = process.argv.indexOf(k); return i > 0 ? process.argv[i + 1] : d; };
const ROTULO = arg("--rotulo", "rodada");
const SAIDA = arg("--saida", null);
const ler = (rel) => JSON.parse(readFileSync(new URL(rel, import.meta.url), "utf-8"));

const dados = ler("../../dados/tratado/avaliacao_busca_dados.json");
const meta = ler("../../web/data/meta.json");
const { consultas } = ler("../../avaliacao/consultas_busca.json");
const motor = criarMotor({ ...dados.motor, meta });

/* ---------- gabarito (independente do parser) ---------- */
const pctRank = (arr) => { const idx = arr.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]); const o = new Array(arr.length); idx.forEach(([, i], k) => { o[i] = arr.length > 1 ? k / (arr.length - 1) : 0; }); return o; };
const GM = dados.gabarito.municipios.map((m) => ({ ...m }));
{ const pa = pctRank(GM.map((m) => m.a)), pt = pctRank(GM.map((m) => m.t)); GM.forEach((m, i) => { m.pa = pa[i]; m.pt = pt[i]; m.need = 0.5 * (1 - pa[i]) + 0.5 * pt[i]; }); }
const GR = dados.gabarito.regioes.map((r) => ({ ...r }));
{ const pa = pctRank(GR.map((r) => r.a)), pt = pctRank(GR.map((r) => r.t)); GR.forEach((r, i) => { r.pa = pa[i]; r.pt = pt[i]; r.need = 0.5 * (1 - pa[i]) + 0.5 * pt[i]; }); }
const idsMotorSrv = new Set(dados.motor.servicos.map((s) => s.id));
const GS = dados.gabarito.servicos.filter((s) => idsMotorSrv.has(s.id));        // servicos existentes nos dois momentos
const munPorNome = new Map(dados.gabarito.municipios.map((m) => [m.n, m]));
const regPorNome = new Map(dados.gabarito.regioes.map((r) => [r.n, r]));
const munPorC = new Map(GM.map((m) => [m.c, m]));

const ordemKey = { necessidade: (x) => x.need, internacao: (x) => x.t, acesso: (x) => -x.a };
function graduar(S, chave) {
  const rel = new Map();
  if (S.length <= 3) { S.forEach((x) => rel.set(x.__id, 3)); return rel; }
  const ord = [...S].sort((a, b) => chave(b) - chave(a));
  ord.forEach((x, i) => rel.set(x.__id, i < S.length / 3 ? 3 : i < (2 * S.length) / 3 ? 2 : 1));
  return rel;
}
const condMun = (s) => (m) => {
  if (s.regioes && !s.regioes.some((n) => regPorNome.get(n).ri === m.ri)) return false;
  if (s.grupo === "interior" && m.gs !== 0) return false;
  if (s.grupo === "grande_sp" && m.gs !== 1) return false;
  if (s.grupo === "litoral" && m.lit !== 1) return false;
  if (s.sem_caps && m.k !== 0) return false;
  if (s.com_caps && m.k === 0) return false;
  if (s.deserto && m.dz !== 1) return false;
  if (s.porte === "pequeno" && !(m.p < 20000)) return false;
  if (s.porte === "medio" && !(m.p >= 20000 && m.p < 100000)) return false;
  if (s.porte === "grande" && !(m.p >= 100000)) return false;
  if (s.porte_min != null && !(m.p > s.porte_min)) return false;
  if (s.porte_max != null && !(m.p < s.porte_max)) return false;
  if (s.porte_faixa && !(m.p >= s.porte_faixa[0] && m.p <= s.porte_faixa[1])) return false;
  if (s.acesso === "baixo" && !(m.pa <= 1 / 3)) return false;
  if (s.acesso === "alto" && !(m.pa >= 2 / 3)) return false;
  if (s.internacao === "alta" && !(m.pt >= 2 / 3)) return false;
  if (s.internacao === "baixa" && !(m.pt <= 1 / 3)) return false;
  if (s.longe && !((m.d ?? 999) > 60)) return false;
  if (s.tipologia != null && m.g !== s.tipologia) return false;
  return true;
};
function goldMunicipio(s) {
  const S = GM.filter(condMun(s)).map((m) => ({ ...m, __id: `municipio:${m.c}` }));
  return graduar(S, ordemKey[s.ordenar || "necessidade"]);
}
function goldRegiao(s) {
  const S = GR.filter((r) => (!s.grupo || (s.grupo === "interior" ? r.gs === 0 : s.grupo === "grande_sp" ? r.gs === 1 : r.lit === 1)) && (!s.sem_caps || r.sem > 0) && (!s.deserto || r.dz > 0))
    .map((r) => ({ ...r, __id: `regiao:${r.ri}` }));
  let chave = ordemKey[s.ordenar || "necessidade"];
  if (!s.ordenar && s.deserto) chave = (r) => r.dz + r.need * 0.01;
  else if (!s.ordenar && s.sem_caps) chave = (r) => r.sem + r.need * 0.01;
  return graduar(S, chave);
}
function goldServico(s) {
  const rel = new Map();
  const ref = s.municipio ? munPorNome.get(s.municipio) : s.perto_de ? munPorNome.get(s.perto_de) : null;
  const gradDist = (km) => (km <= 25 ? 3 : km <= 50 ? 2 : km <= 100 ? 1 : 0);
  let S = GS.filter((x) => {
    const m = munPorC.get(x.m);
    if (s.modalidade && x.mo !== s.modalidade) return false;
    if (s.regioes && !s.regioes.some((n) => regPorNome.get(n).ri === m.ri)) return false;
    if (s.grupo === "interior" && m.gs !== 0) return false;
    if (s.grupo === "grande_sp" && m.gs !== 1) return false;
    if (s.municipio && !s.perto_de && x.m !== ref.c) return false;
    return true;
  });
  if (s.perto_de || (s.municipio && S.length === 0)) {
    GS.filter((x) => !s.modalidade || x.mo === s.modalidade).forEach((x) => { const g = gradDist(distanciaKm(ref.la, ref.lo, x.la, x.lo)); if (g > 0) rel.set(`servico:${x.id}`, g); });
  } else S.forEach((x) => rel.set(`servico:${x.id}`, 2));
  return rel;
}
function goldNav(s) { return new Map([[`municipio:${munPorNome.get(s.municipio).c}`, 3]]); }
const gold = (s) => ({ municipio: goldMunicipio, regiao: goldRegiao, servico: goldServico, nav: goldNav }[s.escopo](s));

/* ---------- metricas ---------- */
const dcg = (rels, k) => rels.slice(0, k).reduce((a, r, i) => a + (2 ** r - 1) / Math.log2(i + 2), 0);
function medir(rankIds, rel, k = 10) {
  const rels = rankIds.map((id) => rel.get(id) || 0);
  const ideal = [...rel.values()].sort((a, b) => b - a);
  const idc = dcg(ideal, k);
  const p = rels.slice(0, k).filter((r) => r > 0).length / k;
  const primeiro = rels.findIndex((r) => r > 0);
  return { ndcg: idc > 0 ? dcg(rels, k) / idc : 0, p, mrr: primeiro >= 0 ? 1 / (primeiro + 1) : 0, n_rel: ideal.length };
}
const media = (a) => a.reduce((x, y) => x + y, 0) / Math.max(1, a.length);
function bootstrap(a, b, n = 2000) {
  let s = 20261023; const rnd = () => { s = (s * 1664525 + 1013904223) % 4294967296; return s / 4294967296; };
  const d = a.map((x, i) => x - b[i]); const bs = [];
  for (let i = 0; i < n; i++) { let t = 0; for (let j = 0; j < d.length; j++) t += d[Math.floor(rnd() * d.length)]; bs.push(t / d.length); }
  bs.sort((x, y) => x - y);
  return { dif: media(d), lo: bs[Math.floor(0.025 * n)], hi: bs[Math.floor(0.975 * n)] };
}

/* ---------- interpretacao esperada, derivada da especificacao ---------- */
function esperado(s) {
  const filtros = new Set(), ents = new Set();
  ["sem_caps", "com_caps", "deserto", "longe"].forEach((k) => s[k] && filtros.add(k));
  if (s.porte) filtros.add(`porte_${s.porte}`);
  if (s.porte_min != null) filtros.add(`porte_min:${s.porte_min}`);
  if (s.porte_max != null) filtros.add(`porte_max:${s.porte_max}`);
  if (s.porte_faixa) filtros.add(`porte_faixa:${s.porte_faixa[0]}-${s.porte_faixa[1]}`);
  if (s.acesso) filtros.add(`acesso_${s.acesso}`);
  if (s.internacao) filtros.add(`internacao_${s.internacao}`);
  if (s.grupo) filtros.add(s.grupo);
  if (s.tipologia != null) filtros.add(`tipologia:${s.tipologia}`);
  (s.regioes || []).forEach((n) => ents.add(`regiao:${regPorNome.get(n).ri}`));
  [s.municipio, s.perto_de].filter(Boolean).forEach((n) => ents.add(`municipio:${munPorNome.get(n).c}`));
  const intencao = { municipio: "planejamento", regiao: "regioes", servico: "servicos", referencia: "referencia" }[s.escopo]
    ?? "perfil";
  return { intencao, filtros, ents, ord: s.ordenar ?? null, modalidade: s.modalidade ?? null };
}
const f1 = (esp, obt) => { const e = new Set(esp), o = new Set(obt); const tp = [...e].filter((x) => o.has(x)).length; return { tp, fp: o.size - tp, fn: e.size - tp }; };

/* ---------- execucao ---------- */
const porEscopo = {}, linhas = [], interp = [], excluidas = [];
const escopoMotor = { municipio: "municipio", regiao: "regiao", servico: "servico", nav: "municipio" };
for (const s of consultas) {
  // interpretacao
  const r = motor.buscar(s.texto);
  const it = r.interpretacao, esp = esperado(s);
  const obt = { filtros: new Set(it.filtros.map((f) => f.id)), ents: new Set(it.entidades.map((e) => e.id)), ord: it.ordenacao?.chave ?? null, modalidade: it.modalidade ?? null };
  const intencaoOk = it.intencao === esp.intencao || (s.escopo === "nav" && ["perfil", "planejamento"].includes(it.intencao));
  const sets = [["filtros", esp.filtros, obt.filtros], ["ents", esp.ents, obt.ents]];
  let tp = 0, fp = 0, fn = 0;
  sets.forEach(([, e, o]) => { const c = f1(e, o); tp += c.tp; fp += c.fp; fn += c.fn; });
  const ordOk = (esp.ord ?? null) === (obt.ord ?? null), modOk = (esp.modalidade ?? null) === (obt.modalidade ?? null);
  if (!ordOk) { if (esp.ord) fn++; if (obt.ord) fp++; } else if (esp.ord) tp++;
  if (!modOk) { if (esp.modalidade) fn++; if (obt.modalidade) fp++; } else if (esp.modalidade) tp++;
  const exato = intencaoOk && fp === 0 && fn === 0 && ordOk && modOk;
  interp.push({ id: s.id, escopo: s.escopo, intencaoOk, exato, tp, fp, fn, texto: s.texto, intencao: it.intencao, filtros: [...obt.filtros], ents: it.entidades.map((e) => e.rotulo), ord: obt.ord });
  if (s.escopo === "referencia" || s.so_interpretacao) continue;

  // ranqueamento
  const rel = gold(s);
  if (rel.size === 0) { excluidas.push({ id: s.id, texto: s.texto, motivo: "gabarito vazio (nenhum item satisfaz a consulta em 2023-24): NDCG indefinido" }); continue; }
  const topo = r.resultados.map((x) => `${x.tipo}:${x.id}`);
  const sistema = medir(topo, rel);
  const esc = escopoMotor[s.escopo];
  const pref = esc === "municipio" ? "municipio:" : esc === "regiao" ? "regiao:" : "servico:";
  const bruto = motor.baselines.buscaBruta(s.texto, esc).map((id) => pref + id);
  const nec = motor.baselines.ordemNecessidade(esc === "servico" ? "municipio" : esc).map((id) => pref + id);
  const hib = esc === "municipio" ? motor.baselines.hibridoSemInterpretacao(s.texto).map((id) => pref + id) : null;
  linhas.push({ id: s.id, escopo: s.escopo, texto: s.texto, n_rel: sistema.n_rel, sistema, bm25: medir(bruto, rel), necessidade: esc === "servico" ? null : medir(nec, rel), hibrido: hib ? medir(hib, rel) : null });
}

const grupos = { "planejamento (municípios)": (l) => l.escopo === "municipio", "regiões": (l) => l.escopo === "regiao", "serviços": (l) => l.escopo === "servico", "navegacional": (l) => l.escopo === "nav" };
const tabela = {};
console.log(`\n=== ${ROTULO} ===`);
if (excluidas.length) console.log(`excluídas do ranqueamento por gabarito vazio: ${excluidas.map((e) => e.id).join(", ")}`);
console.log(`consultas: ${consultas.length} (${linhas.length} ranqueadas; ${consultas.filter((c) => c.escopo === "referencia").length} só interpretação de referência; ${consultas.filter((c) => c.so_interpretacao).length} tipologia só interpretação)`);
for (const [nome, f] of Object.entries(grupos)) {
  const L = linhas.filter(f);
  if (!L.length) continue;
  const m = (k, met) => { const a = L.filter((l) => l[k]).map((l) => l[k][met]); return a.length ? media(a) : null; };
  tabela[nome] = { n: L.length };
  for (const k of ["sistema", "bm25", "necessidade", "hibrido"]) if (L.some((l) => l[k])) tabela[nome][k] = { ndcg: m(k, "ndcg"), p: m(k, "p"), mrr: m(k, "mrr") };
}
const fmtN = (v) => (v == null ? "  —  " : v.toFixed(3));
console.log("\nNDCG@10 | P@10 | MRR  (sistema vs baselines)");
for (const [nome, t] of Object.entries(tabela)) {
  console.log(`\n${nome} (n=${t.n})`);
  for (const k of ["sistema", "bm25", "necessidade", "hibrido"]) if (t[k]) console.log(`  ${k.padEnd(12)} ${fmtN(t[k].ndcg)} | ${fmtN(t[k].p)} | ${fmtN(t[k].mrr)}`);
}
const todos = linhas;
const dif = {};
for (const base of ["bm25", "necessidade", "hibrido"]) {
  const L = todos.filter((l) => l[base]);
  dif[base] = { n: L.length, ...bootstrap(L.map((l) => l.sistema.ndcg), L.map((l) => l[base].ndcg)) };
}
console.log("\nDiferença de NDCG@10 (sistema − baseline), IC95% bootstrap pareado:");
for (const [b, d] of Object.entries(dif)) console.log(`  vs ${b.padEnd(12)} n=${d.n}  ${d.dif >= 0 ? "+" : ""}${d.dif.toFixed(3)} [${d.lo.toFixed(3)}, ${d.hi.toFixed(3)}]`);
const geral = { ndcg: media(todos.map((l) => l.sistema.ndcg)), p: media(todos.map((l) => l.sistema.p)), mrr: media(todos.map((l) => l.sistema.mrr)) };
console.log(`\nGeral (sistema, ${todos.length} consultas): NDCG@10 ${geral.ndcg.toFixed(3)} | P@10 ${geral.p.toFixed(3)} | MRR ${geral.mrr.toFixed(3)}`);

const geralBase = {};
for (const b of ["bm25", "necessidade", "hibrido"]) { const L = todos.filter((l) => l[b]); geralBase[b] = { n: L.length, ndcg: media(L.map((l) => l[b].ndcg)) }; }
const acInt = { n: interp.length, exato: media(interp.map((i) => +i.exato)), intencao: media(interp.map((i) => +i.intencaoOk)) };
const TP = interp.reduce((a, i) => a + i.tp, 0), FP = interp.reduce((a, i) => a + i.fp, 0), FN = interp.reduce((a, i) => a + i.fn, 0);
acInt.precisao = TP / Math.max(1, TP + FP); acInt.revocacao = TP / Math.max(1, TP + FN);
console.log(`\nInterpretação (${acInt.n} consultas): intenção correta ${(acInt.intencao * 100).toFixed(0)}% | interpretação exata ${(acInt.exato * 100).toFixed(0)}% | precisão ${(acInt.precisao * 100).toFixed(0)}% | revocação ${(acInt.revocacao * 100).toFixed(0)}%`);
console.log("\nConsultas com interpretação NÃO exata:");
interp.filter((i) => !i.exato).forEach((i) => console.log(`  ${i.id} "${i.texto}"\n      obtido: intenção=${i.intencao} filtros=[${i.filtros}] entidades=[${i.ents}] ord=${i.ord} | tp/fp/fn=${i.tp}/${i.fp}/${i.fn}`));
console.log("\nPiores consultas (NDCG@10 do sistema):");
[...linhas].sort((a, b) => a.sistema.ndcg - b.sistema.ndcg).slice(0, 8).forEach((l) => console.log(`  ${l.id} ndcg=${l.sistema.ndcg.toFixed(2)} (relevantes=${l.n_rel}) "${l.texto}"`));

if (SAIDA) {
  const saida = { rotulo: ROTULO, gerado_em: new Date().toISOString().slice(0, 10), n_consultas: consultas.length, n_ranqueadas: linhas.length, autoria: "rascunho do assistente; o grupo deve substituir/ampliar",
    excluidas, corpus: motor.corpus, por_escopo: tabela, geral, geral_baselines: geralBase, diferencas: dif, interpretacao: acInt };
  writeFileSync(new URL(SAIDA, `file://${process.cwd().replace(/\\/g, "/")}/`), JSON.stringify(saida, null, 1), "utf-8");
  console.log(`\nsalvo em ${SAIDA}`);
}
