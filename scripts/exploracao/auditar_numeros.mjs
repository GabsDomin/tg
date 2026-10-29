// Auditoria: os numeros escritos no texto (cap. 4, docs/resultados_*.md) batem com os dados publicados?
// Recalcula de web/data/*.json e dados/tratado/*.csv e procura o valor formatado no texto.
// Uso: node scripts/exploracao/auditar_numeros.mjs      (sai com codigo 1 se algo nao bater)
import { readFileSync, existsSync } from "node:fs";

const R = (p) => new URL(`../../${p}`, import.meta.url);
const J = (p) => JSON.parse(readFileSync(R(p), "utf-8"));
const T = (p) => readFileSync(R(p), "utf-8");
const csv = (p) => { const [h, ...l] = T(p).trim().split(/\r?\n/); const cols = h.split(","); return l.map((x) => Object.fromEntries(x.split(",").map((v, i) => [cols[i], v]))); };

const M = J("web/data/municipios.json"), REG = J("web/data/regioes.json"), SRV = J("web/data/servicos.json"), META = J("web/data/meta.json");
const REF = J("web/data/avaliacao_referencia.json");
const TEXTO = T("scripts/documento/conteudo_cap4_cap5.py");
const DOC_BUSCA = T("docs/resultados_busca.md"), DOC_AVAL = T("docs/resultados_avaliacao.md"), DOC_CL = T("docs/resultados_clusters.md");

const br = (x, d = 1) => Number(x).toFixed(d).replace(".", ",");
const mil = (n) => Math.round(n).toLocaleString("pt-BR");
const sgn = (x, d = 3) => (x >= 0 ? "+" : "−") + Math.abs(x).toFixed(d).replace(".", ",");
let ok = 0, falha = 0, nao = 0;
const linhas = [];
function checa(rotulo, doc, textoEsperado, valorCalculado = "") {
  const achou = doc.includes(textoEsperado);
  achou ? ok++ : falha++;
  linhas.push(`${achou ? "OK    " : "FALHA "} ${rotulo}  →  “${textoEsperado}”${valorCalculado ? "  [calculado: " + valorCalculado + "]" : ""}`);
}
const nv = (rotulo, motivo) => { nao++; linhas.push(`n/v    ${rotulo} — ${motivo}`); };

/* ---------- oferta e cobertura (municipios.json: k = CAPS AD dez/2024; a = acesso medio 2023-24; d = km) ---------- */
const popTot = M.reduce((a, m) => a + m.p, 0);
const sem = M.filter((m) => m.k === 0), popSem = sem.reduce((a, m) => a + m.p, 0);
checa("municípios sem CAPS AD", TEXTO, `${sem.length} municípios (${Math.round(sem.length / M.length * 100)}%)`);
checa("pop. nos municípios sem CAPS AD", TEXTO, `${br(popSem / popTot * 100)}%`);
checa("pop. em município com CAPS AD", TEXTO, `${br(100 - popSem / popTot * 100)}%`);
const dSorted = M.map((m) => m.d).sort((a, b) => a - b);
checa("mediana da distância ao CAPS AD", TEXTO, `mediana de ${Math.round(dSorted[Math.floor(dSorted.length / 2)])} km`, br(dSorted[Math.floor(dSorted.length / 2)], 2));
// d esta arredondado a 1 casa no JSON: um municipio a 30,03 km vira 30,0 e sai de "d > 30". Tolerancia de 1 municipio e 0,1 p.p.
for (const km of [30, 60]) {
  const ms = M.filter((m) => m.d > km), pct = ms.reduce((a, m) => a + m.p, 0) / popTot * 100;
  const re = new RegExp(`(\\d+,\\d)% (?:da população )?\\((\\d+) municípios\\)${km === 30 ? " vivia a mais de 30 km" : ", a mais de 60 km"}`);
  const t = TEXTO.match(re);
  const bate = t && Math.abs(Number(t[1].replace(",", ".")) - pct) <= 0.15 && Math.abs(Number(t[2]) - ms.length) <= 1;
  bate ? ok++ : falha++;
  linhas.push(`${bate ? "OK    " : "FALHA "} pop. a mais de ${km} km  →  texto ${t ? `${t[1]}% (${t[2]} mun.)` : "não encontrado"}  [calculado do JSON arredondado: ${br(pct)}% (${ms.length} mun.)]`);
}
const zero = M.filter((m) => m.a === 0);
checa("acessibilidade zero", TEXTO, `${zero.length} municípios, com ${br(zero.reduce((a, m) => a + m.p, 0) / 1e6, 2)} milhão`);
const dz = M.filter((m) => m.dz === 1), popDz = dz.reduce((a, m) => a + m.p, 0);
checa("desertos de cuidado", TEXTO, `${dz.length} municípios, com ${mil(popDz)} habitantes (${br(popDz / popTot * 100)}% da população do estado)`);
checa("CAPS AD dez/2024 (serviços)", TEXTO, "115", String(SRV.length)); if (SRV.length !== 115) { falha++; linhas.push("FALHA  servicos.json não tem 115 CAPS AD"); }
const mo = SRV.reduce((a, s) => ((a[s.mo] = (a[s.mo] || 0) + 1), a), {});
checa("modalidades dez/2024", TEXTO, `${mo["AD"]} deles tinham a habilitação genérica`, JSON.stringify(mo));
checa("modalidade AD III", TEXTO, `${mo["AD III"]}, a de CAPS AD III`);

/* ---------- tipologia ---------- */
const g = [1, 2, 3, 4, 5].map((k) => M.filter((m) => m.g === k).length);
const rot = META.clusters;
[1, 2, 3, 4, 5].forEach((k, i) => checa(`tipologia grupo ${k}`, TEXTO, `["${k}. ${rot[k]}", "${g[i]}"`));
const perfil = csv("dados/tratado/clusters_perfil.csv");
perfil.forEach((p) => {
  const lin = `"${p.n}", "${br(p.acesso, 2)}", "${br(p.dist_ad, 1)}", "${Math.round(p.taxa_int)}", "${Math.round(p.atend_caps)}", "${br(p.frac_fora, 2)}", "${br(p.pop_mediana / 1000, 1)}"`;
  checa(`perfil do grupo ${p.cluster} (tabela 4)`, TEXTO, lin);
});

/* ---------- regioes (taxa agregada 2023-24) ---------- */
const porT = [...REG].sort((a, b) => b.t - a.t);
checa("maiores taxas regionais", TEXTO, porT.slice(0, 4).map((r, i) => (i === 3 ? "e " : "") + `${r.n} (${br(r.t)})`).join(", ").replace(", e ", " e "), "");
const menores = [...REG].sort((a, b) => a.t - b.t).slice(0, 5).map((r) => `${r.n} ${br(r.t)}`).join(" | ");
for (const [nome, v] of [["Baixada Santista", "16,8"], ["Sorocaba", "19,3"], ["Itapetininga", "19,7"]]) {
  const r = REG.find((x) => x.n === nome);
  checa(`taxa regional ${nome}`, TEXTO, `(${v})`, r ? br(r.t) : "?");
  if (!r || br(r.t) !== v) { falha++; linhas.push(`FALHA  ${nome}: texto ${v}, dado ${r ? br(r.t) : "ausente"}`); }
}
linhas.push(`info   as 5 menores taxas regionais no dado: ${menores} (o texto restringe a regiões com mais de 50 internações; isso exige o parquet)`);
const dzPorReg = {}; dz.forEach((m) => { dzPorReg[m.r] = (dzPorReg[m.r] || 0) + 1; });
const top = Object.entries(dzPorReg).sort((a, b) => b[1] - a[1]).slice(0, 5);
linhas.push(`info   regiões com mais municípios em deserto: ${top.map(([r, n]) => `${r} ${n}`).join(", ")}`);
checa("região com mais desertos (Vale do Jurumirim)", TEXTO, `Vale do Jurumirim (${dzPorReg["Vale do Jurumirim"]})`);
checa("região com mais desertos (Assis)", TEXTO, `Assis (${dzPorReg["Assis"]})`);
checa("desertos por grupo", TEXTO, `grupos 1 (${dz.filter((m) => m.g === 1).length} municípios), 2 (${dz.filter((m) => m.g === 2).length}) e 3 (${dz.filter((m) => m.g === 3).length})`);

/* ---------- tabela 6: 12 desertos mais populosos ---------- */
dz.sort((a, b) => b.p - a.p).slice(0, 12).forEach((m) => {
  checa(`tabela 6: ${m.n}`, TEXTO, `["${m.n}", "${m.r}", "${mil(m.p)}", "${br(m.a, 2)}", "${Math.round(m.t)}"]`);
});

/* ---------- tabela 5 (Censo): medianas por grupo e epsilon^2, com CSV entre aspas ---------- */
function csvAspas(p) {
  const linhas = T(p).trim().split(/\r?\n/);
  const parte = (l) => { const o = []; let cur = "", q = false; for (const ch of l) { if (ch === '"') q = !q; else if (ch === "," && !q) { o.push(cur); cur = ""; } else cur += ch; } o.push(cur); return o; };
  const cols = parte(linhas[0]);
  return linhas.slice(1).map((l) => Object.fromEntries(parte(l).map((v, i) => [cols[i], v])));
}
const ROT5 = { renda_mediana: "Renda mediana do trabalho (R$)", anos_estudo: "Anos de estudo", analfabetismo_pct: "Analfabetismo (%)", esgoto_rede_pct: "Esgoto por rede (%)", densidade_hab_km2: "Densidade (hab/km²)" };
const numBR = (s) => Number(String(s).replace(/\./g, "").replace(",", "."));
for (const r of csvAspas("dados/tratado/clusters_socioeconomico.csv")) {
  const m = TEXTO.match(new RegExp(`\\["${ROT5[r.variavel].replace(/[()$/]/g, "\\$&")}", ((?:"[^"]*",? ?)+)\\]`));
  if (!m) { falha++; linhas.push(`FALHA  tabela 5: linha de ${r.variavel} não encontrada`); continue; }
  const textoCel = [...m[1].matchAll(/"([^"]*)"/g)].map((x) => x[1]);          // [ε², grupo1..grupo5], como escritos no texto
  let bom = br(r.epsilon2, 2) === textoCel[0];
  const dif = [];
  for (let k = 1; k <= 5; k++) {
    const real = Number(r[`cluster_${k}`].split(" ")[0].replace(/,/g, ""));      // "1,800.0 (1,700.0–2,000.0)" -> 1800
    const v = numBR(textoCel[k]);
    // tolerancia = meia unidade da ultima casa exibida no texto (o CSV de origem tem 1 casa decimal)
    const casas = (textoCel[k].split(",")[1] || "").length;
    const tol = 0.5 * 10 ** -casas + 0.051;
    if (Math.abs(v - real) > tol) { bom = false; dif.push(`g${k}: texto ${v} x dado ${real}`); }
  }
  bom ? ok++ : falha++;
  linhas.push(`${bom ? "OK    " : "FALHA "} tabela 5: ${r.variavel}  (ε² ${br(r.epsilon2, 2)})${dif.length ? "  " + dif.join("; ") : ""}`);
}

/* ---------- capacidade por modalidade ---------- */
const cap = csv("dados/tratado/capacidade_modalidade.csv");
const ad = cap.find((c) => c.modalidade_ad === "AD"), ad3 = cap.find((c) => c.modalidade_ad === "AD III");
checa("capacidade AD", TEXTO, `${Math.round(Number(ad.mediana))} pacientes por mês para o CAPS AD (intervalo interquartil de ${Math.round(ad.p25)} a ${Math.round(ad.p75)})`);
checa("capacidade AD III", TEXTO, `${Math.round(ad3.mediana)} para o CAPS AD III (${Math.round(ad3.p25)} a ${Math.round(ad3.p75)})`);

/* ---------- avaliacao do encaminhamento (avaliacao_referencia.json) ---------- */
const lin = (k) => REF.tabela.find((x) => x.metodo === k);
for (const [k, rotulo] of [["so populacao do destino", "população"], ["so distancia", "distância"], ["so mesma regiao (depois distancia)", "região"], ["SISTEMA (pesos calibrados)", "sistema"], ["persistencia (fluxo 2019-22)", "persistência"], ["SISTEMA + historico", "sistema+histórico"]]) {
  const x = lin(k); checa(`tabela 7: ${rotulo}`, TEXTO, `"${br(x["NDCG@5"], 3)}", "${br(x.MRR, 3)}", "${br(x["P@5"], 3)}"`);
}
const d = REF.diffs["SISTEMA (pesos calibrados)"];
checa("Δ sistema − distância", TEXTO, `${sgn(d[0])}, tem intervalo de confiança de 95% de ${sgn(d[1])} a ${sgn(d[2])}`);
const dh = REF.diffs["SISTEMA + historico"];
checa("Δ histórico − distância", TEXTO, `diferença de ${sgn(dh[0])} em relação à distância, com intervalo de 95% de ${sgn(dh[1])} a ${sgn(dh[2])}`);
const ab = Object.fromEntries(REF.ablacao.map((x) => [x.sem, x]));
checa("ablação sem região", TEXTO, `reduz o NDCG@5 para ${br(ab.mesma_regiao["NDCG@5"], 3)}`);
checa("ablação sem folga", TEXTO, `(${br(ab.folga["NDCG@5"], 3)} sem folga)`);
const pw = REF.pesos;
checa("pesos finais", TEXTO, `foram de ${br(pw.mesma_regiao, 1)} para a região, ${br(pw.proximidade, 1)} para a proximidade e ${br(pw.abertura, 1)} para a abertura`);
const est = (e, m) => REF.estratos.find((x) => x.estrato === e && x.metodo === m);
checa("estrato com histórico", TEXTO, `a persistência alcançou ${br(est("com historico", "persistencia (fluxo 2019-22)")["NDCG@5"], 3)}, contra ${br(est("com historico", "so distancia")["NDCG@5"], 3)} da distância e ${br(est("com historico", "SISTEMA (pesos calibrados)")["NDCG@5"], 3)} do sistema`);
checa("estrato cold-start", TEXTO, `o sistema obteve ${br(est("cold-start", "SISTEMA (pesos calibrados)")["NDCG@5"], 3)}, ante ${br(est("cold-start", "so distancia")["NDCG@5"], 3)} da distância e ${br(est("cold-start", "persistencia (fluxo 2019-22)")["NDCG@5"], 3)} da persistência`);
const rp = REF.repeticoes;
checa("50 divisões repetidas", TEXTO, `${br(rp["SISTEMA (pesos calibrados)"][0], 3)} para o sistema, ${br(rp["so distancia"][0], 3)} para a distância e ${br(rp["persistencia (fluxo 2019-22)"][0], 3)} para a persistência`);
checa("nº de consultas de referência", TEXTO, `os 219 municípios`, String(REF.n_consultas));
if (REF.n_consultas !== 219) { falha++; linhas.push(`FALHA  n_consultas = ${REF.n_consultas}`); }

/* ---------- avaliacao da busca (docs/resultados_busca.md) ---------- */
const r1 = J("web/data/avaliacao_busca_rodada1.json"), fin = J("web/data/avaliacao_busca.json");
checa("busca rodada 1: NDCG@10 geral", DOC_BUSCA, `NDCG@10 = ${br(r1.geral.ndcg, 3)}`);
checa("busca rodada final: NDCG@10 geral", DOC_BUSCA, `NDCG@10 = ${br(fin.geral.ndcg, 3)}`);
checa("busca rodada 1: Δ vs BM25", DOC_BUSCA, `${sgn(r1.diferencas.bm25.dif)} (IC 95% ${br(r1.diferencas.bm25.lo, 3)} a ${br(r1.diferencas.bm25.hi, 3)})`);
checa("busca final: Δ vs BM25", DOC_BUSCA, `${sgn(fin.diferencas.bm25.dif)} (${br(fin.diferencas.bm25.lo, 3)} a ${br(fin.diferencas.bm25.hi, 3)})`);
checa("busca rodada 1: interpretação exata", DOC_BUSCA, `interpretação exata em ${Math.round(r1.interpretacao.exato * 100)}%`);

/* ---------- docs/resultados_avaliacao.md ---------- */
const s = lin("SISTEMA (pesos calibrados)"), dist = lin("so distancia");
checa("avaliação (doc): sistema", DOC_AVAL, `| ${br(s["NDCG@5"], 3)} |`);
checa("avaliação (doc): só distância", DOC_AVAL, `**${br(dist["NDCG@5"], 3)}**`);

/* ---------- limitacoes ja conhecidas ---------- */
nv("114.183 internações; 78,9% homens; faixas etárias; 8.777 óbitos; 37,4% nos 10 maiores", "exigem os parquets (Python bloqueado nesta sessão); foram conferidos com o TabNet antes (−0,14% a −0,30%)");
nv("tabelas 2 e 3 (CAPS AD por ano; k do K-Means)", "série histórica e silhuetas não estão nos arquivos publicados");

console.log(linhas.join("\n"));
console.log(`\n${ok} conferidos OK | ${falha} FALHAS | ${nao} não verificáveis nesta sessão`);
process.exit(falha ? 1 : 0);
