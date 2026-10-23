/* Motor de busca do projeto "Desertos de cuidado em álcool e outras drogas".
 *
 * Modulo puro (sem DOM): roda no navegador e no Node (a avaliacao usa EXATAMENTE este codigo).
 *
 * Pipeline: consulta -> normalizacao -> entidades (municipios, regioes, grupos) -> filtros e ordenacao
 *           -> intencao (planejamento | regioes | servicos | referencia | perfil)
 *           -> recuperacao (BM25 sobre o corpus) + filtros duros -> ranqueamento explicavel.
 *
 * Corpus: um documento textual por municipio, regiao de saude e CAPS AD, gerado dos indicadores.
 * Sem dependencias externas. Os pesos de ranqueamento de referencia vem de meta.pesos_referencia
 * (calibrados contra fluxos reais; ver docs/resultados_avaliacao.md).
 */

export const norm = (s) =>
  String(s ?? "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9]+/g, " ").trim();

const stem = (t) => (t.length > 4 && t.endsWith("s") && !t.endsWith("ss") ? t.slice(0, -1) : t);

const STOP = new Set(("de do da dos das e em no na nos nas a o os as um uma uns umas para por com sem que ao aos se quais qual quem onde como " +
  "ha tem ter ser sao foi mais menos muito muita muitos muitas pelo pela pelos pelas entre ate sobre ja nao nem ou mas").split(" "));
const GENERICAS = new Set(("caps ad municipio municipios cidade cidades regiao regioes saude habilitado habilitados servico servicos paciente " +
  "pacientes usuario usuarios habitantes habitante populacao lista listar mostrar quero preciso taxa taxas indice numero volume nivel").split(" "));

const haversine = (a, b, c, d) => {
  const R = 6371.0088, r = Math.PI / 180, p = (c - a) * r, l = (d - b) * r;
  const x = Math.sin(p / 2) ** 2 + Math.cos(a * r) * Math.cos(c * r) * Math.sin(l / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(x));
};
export const distanciaKm = haversine;

const pctRank = (arr) => {
  const idx = arr.map((v, i) => [v, i]).sort((x, y) => x[0] - y[0]);
  const out = new Array(arr.length);
  idx.forEach(([, i], k) => { out[i] = arr.length > 1 ? k / (arr.length - 1) : 0; });
  return out;
};

/* ---------- BM25 ---------- */
class BM25 {
  constructor(docs, k1 = 1.2, b = 0.75) {
    this.k1 = k1; this.b = b; this.N = docs.length;
    this.tf = docs.map((d) => { const m = new Map(); d.tokens.forEach((t) => m.set(t, (m.get(t) || 0) + 1)); return m; });
    this.len = docs.map((d) => d.tokens.length);
    this.avg = this.len.reduce((a, c) => a + c, 0) / Math.max(1, this.N);
    this.df = new Map();
    this.tf.forEach((m) => m.forEach((_, t) => this.df.set(t, (this.df.get(t) || 0) + 1)));
    this.ids = docs.map((d) => d.id);
  }
  idf(t) { const n = this.df.get(t) || 0; return Math.log(1 + (this.N - n + 0.5) / (n + 0.5)); }
  /** Map id -> score para os documentos que contem ao menos um termo */
  buscar(termos) {
    const out = new Map();
    for (let i = 0; i < this.N; i++) {
      let s = 0;
      for (const t of termos) {
        const f = this.tf[i].get(t);
        if (!f) continue;
        s += this.idf(t) * (f * (this.k1 + 1)) / (f + this.k1 * (1 - this.b + this.b * this.len[i] / this.avg));
      }
      if (s > 0) out.set(this.ids[i], s);
    }
    return out;
  }
}

const tokensDoc = (texto) => norm(texto).split(" ").filter((t) => t && !STOP.has(t)).map(stem);
const termosConsulta = (tokens) => tokens.filter((t) => t && !STOP.has(t) && !GENERICAS.has(t)).map(stem);

/* ---------- distancia de edicao (sugestoes "voce quis dizer") ---------- */
const lev = (a, b) => {
  if (Math.abs(a.length - b.length) > 2) return 9;
  const m = Array.from({ length: a.length + 1 }, (_, i) => [i, ...new Array(b.length).fill(0)]);
  for (let j = 1; j <= b.length; j++) m[0][j] = j;
  for (let i = 1; i <= a.length; i++) for (let j = 1; j <= b.length; j++)
    m[i][j] = Math.min(m[i - 1][j] + 1, m[i][j - 1] + 1, m[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return m[a.length][b.length];
};

const descTercil = (v) => (v >= 2 / 3 ? "alta" : v <= 1 / 3 ? "baixa" : "média");
const fmt = (v, d = 1) => (v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const PORTE_PEQUENO = 20000, PORTE_GRANDE = 100000;

export function criarMotor({ municipios, regioes, servicos, meta }) {
  const mun = municipios.map((m) => ({ ...m }));
  const reg = regioes.map((r) => ({ ...r }));
  const srv = servicos.map((s) => ({ ...s }));
  const byC = new Map(mun.map((m) => [m.c, m]));
  const byRi = new Map(reg.map((r) => [r.ri, r]));
  const rotulos = (meta && meta.clusters) || {};

  /* percentis (o motor so enxerga os atributos que recebeu) */
  const pa = pctRank(mun.map((m) => m.a)), pt = pctRank(mun.map((m) => m.t));
  mun.forEach((m, i) => { m.pa = pa[i]; m.pt = pt[i]; m.need = 0.5 * (1 - m.pa) + 0.5 * m.pt; m.nn = norm(m.n); m.nr = norm(m.r); });
  const pra = pctRank(reg.map((r) => r.a)), prt = pctRank(reg.map((r) => r.t));
  reg.forEach((r, i) => { r.pa = pra[i]; r.pt = prt[i]; r.need = 0.5 * (1 - r.pa) + 0.5 * r.pt; r.nn = norm(r.n); });
  const pf = pctRank(srv.map((s) => s.f));
  srv.forEach((s, i) => { s.pf = pf[i]; });
  const needMax = Math.max(...mun.map((m) => m.need));

  /* ---------- corpus ---------- */
  const porte = (p) => (p < PORTE_PEQUENO ? "pequeno" : p >= PORTE_GRANDE ? "grande" : "médio");
  const docMun = (m) => {
    const n = m.n;
    return `${n} ${n} ${n} município de ${n} região de saúde ${m.r} ${m.r}. ` +
      `${m.k > 0 ? `possui ${m.k} caps ad habilitado` : "sem caps ad habilitado sem serviço"}. município de porte ${porte(m.p)}. ` +
      `acessibilidade ${descTercil(m.pa)}. taxa de internação ${descTercil(m.pt)}. ` +
      `${m.dz ? "deserto de cuidado em álcool e outras drogas. " : ""}${m.gs ? "grande são paulo região metropolitana. " : "interior. "}${m.lit ? "litoral. " : ""}` +
      `${rotulos[m.g] ? rotulos[m.g] : ""}`;
  };
  const docReg = (r) => `${r.n} ${r.n} ${r.n} região de saúde ${r.n}. ${r.nm} municípios, ${r.sem} sem caps ad. acessibilidade ${descTercil(r.pa)}. taxa de internação ${descTercil(r.pt)}. ${r.gs ? "grande são paulo. " : "interior. "}${r.lit ? "litoral. " : ""}`;
  const docSrv = (s) => `${s.n} ${s.n} caps ad ${s.mo} em ${s.mn} ${s.mn} região ${s.r} álcool e drogas centro de atenção psicossocial. modalidade ${s.mo}.`;

  const idxMun = new BM25(mun.map((m) => ({ id: m.c, tokens: tokensDoc(docMun(m)) })));
  const idxReg = new BM25(reg.map((r) => ({ id: r.ri, tokens: tokensDoc(docReg(r)) })));
  const idxSrv = new BM25(srv.map((s) => ({ id: s.id, tokens: tokensDoc(docSrv(s)) })));

  /* ---------- gazetteer ---------- */
  const gaz = new Map();
  const addG = (frase, ent) => { const k = norm(frase); if (!k) return; if (!gaz.has(k)) gaz.set(k, []); const l = gaz.get(k); if (!l.some((e) => e.tipo === ent.tipo && e.id === ent.id)) l.push(ent); };
  mun.forEach((m) => addG(m.n, { tipo: "municipio", id: m.c }));
  reg.forEach((r) => addG(r.n, { tipo: "regiao", id: r.ri }));
  const alias = {
    "alto tiete": ["Alto do Tietê"], "abc": ["Grande ABC"], "grande abc": ["Grande ABC"], "baixada": ["Baixada Santista"],
    "vale ribeira": ["Vale do Ribeira"], "vale do paraiba": ["Alto Vale do Paraíba", "Vale do Paraíba/Região Serrana"],
    "vale paraiba": ["Alto Vale do Paraíba", "Vale do Paraíba/Região Serrana"], "mogiana": ["Alta Mogiana", "Baixa Mogiana"],
    "campinas metropolitana": ["Região Metropolitana de Campinas"], "metropolitana de campinas": ["Região Metropolitana de Campinas"],
    "rmc": ["Região Metropolitana de Campinas"],
  };
  const regPorNome = new Map(reg.map((r) => [r.n, r]));
  Object.entries(alias).forEach(([a, nomes]) => nomes.forEach((n) => { const r = regPorNome.get(n); if (r) addG(a, { tipo: "regiao", id: r.ri }); }));
  const maxLenGaz = Math.max(...[...gaz.keys()].map((k) => k.split(" ").length));

  // palavras de nomes de municipios/regioes: forma normalizada -> grafia original (para "voce quis dizer")
  const grafia = new Map();
  [...mun.map((m) => m.n), ...reg.map((r) => r.n)].forEach((nome) => nome.split(/[\s/-]+/).forEach((w) => { const k = norm(w); if (k.length >= 5 && !STOP.has(k) && !grafia.has(k)) grafia.set(k, w); }));
  const nomesUnigramas = [...grafia.keys()];

  function entidades(tokens) {
    const achados = [], usado = new Array(tokens.length).fill(false);
    for (let i = 0; i < tokens.length;) {
      let hit = null;
      for (let L = Math.min(maxLenGaz, tokens.length - i); L >= 1; L--) {
        const cand = gaz.get(tokens.slice(i, i + L).join(" "));
        if (cand) { hit = { i, L, cand }; break; }
      }
      if (hit) { achados.push(hit); for (let k = 0; k < hit.L; k++) usado[i + k] = true; i += hit.L; } else i++;
    }
    return { achados, usado };
  }

  /* ---------- filtros (todos sobre municipios do conjunto que o motor recebeu) ---------- */
  const F = {
    sem_caps: { rot: "Sem CAPS AD habilitado", fn: (m) => m.k === 0 },
    com_caps: { rot: "Com CAPS AD habilitado", fn: (m) => m.k > 0 },
    deserto: { rot: "Deserto de cuidado (critério do cap. 4.7)", fn: (m) => m.dz === 1 },
    porte_pequeno: { rot: "Porte pequeno (< 20 mil hab.)", fn: (m) => m.p < PORTE_PEQUENO },
    porte_medio: { rot: "Porte médio (20 a 100 mil hab.)", fn: (m) => m.p >= PORTE_PEQUENO && m.p < PORTE_GRANDE },
    porte_grande: { rot: "Porte grande (≥ 100 mil hab.)", fn: (m) => m.p >= PORTE_GRANDE },
    acesso_baixo: { rot: "Acessibilidade baixa (terço inferior)", fn: (m) => m.pa <= 1 / 3 },
    acesso_alto: { rot: "Acessibilidade alta (terço superior)", fn: (m) => m.pa >= 2 / 3 },
    internacao_alta: { rot: "Internação alta (terço superior)", fn: (m) => m.pt >= 2 / 3 },
    internacao_baixa: { rot: "Internação baixa (terço inferior)", fn: (m) => m.pt <= 1 / 3 },
    longe: { rot: "A mais de 60 km de um CAPS AD", fn: (m) => (m.d ?? 999) > 60 },
    perto: { rot: "A até 15 km de um CAPS AD", fn: (m) => (m.d ?? 999) <= 15 },
    interior: { rot: "Interior (fora da Grande São Paulo)", fn: (m) => m.gs === 0 },
    grande_sp: { rot: "Grande São Paulo", fn: (m) => m.gs === 1 },
    litoral: { rot: "Litoral", fn: (m) => m.lit === 1 },
  };
  const ORD = {
    necessidade: { rot: "Maior necessidade estimada", chave: (m) => m.need, desc: true },
    internacao: { rot: "Maior taxa de internação", chave: (m) => m.t, desc: true },
    internacao_menor: { rot: "Menor taxa de internação", chave: (m) => m.t, desc: false },
    acesso: { rot: "Pior acessibilidade", chave: (m) => m.a, desc: false },
    acesso_melhor: { rot: "Melhor acessibilidade", chave: (m) => m.a, desc: true },
    populacao: { rot: "Maior população", chave: (m) => m.p, desc: true },
  };
  const num = (s, unidade) => {
    let v = Number(String(s).replace(/[. ]/g, "").replace(",", "."));
    if (/milh/.test(unidade || "")) v *= 1e6; else if (/mil/.test(unidade || "") || v < 1000) v *= 1000;
    return v;
  };
  const NUM = "(\\d+(?:[. ]\\d{3})*|\\d+)\\s*(mil|milhao|milhoes)?";
  const SUP = "(maior|maiores|mais|pior|piores|menor|menores|menos|melhor|melhores)";
  const ADJ = "(alta|altas|alto|altos|elevada|elevadas|muita|muito|muitas|forte|baixa|baixas|baixo|pouca|pouco|poucas)";

  /* Cada regra consome o trecho que reconhece (substitui por espaco) para nao vazar para os termos livres. */
  const REGRAS = [
    { re: /\bpolos?( medios?)? sob pressao\b/, f: (c) => c.filtros.push(["tipologia:1", `Tipologia: ${rotulos[1] || "grupo 1"}`, (m) => m.g === 1]) },
    { re: /\bsem atendimento registrado( em caps)?\b/, f: (c) => c.filtros.push(["tipologia:2", `Tipologia: ${rotulos[2] || "grupo 2"}`, (m) => m.g === 2]) },
    { re: /\bdependem? de caps de outro municipio\b/, f: (c) => c.filtros.push(["tipologia:3", `Tipologia: ${rotulos[3] || "grupo 3"}`, (m) => m.g === 3]) },
    { re: /\bgrandes centros\b/, f: (c) => c.filtros.push(["tipologia:4", `Tipologia: ${rotulos[4] || "grupo 4"}`, (m) => m.g === 4]) },
    { re: /\bdesert\w*( de cuidado)?\b/, f: (c) => c.flag("deserto") },
    { re: /\b(sem|nao (?:tem|tenha|possui|possuem|ha|existe)|nenhum|falta de|ausencia de|carentes? de)( o| um)? (caps( ad)?|servicos?( especializados?)?|cobertura|oferta|atendimento)( habilitados?)?\b/, f: (c) => c.flag("sem_caps") },
    { re: /\bdesassistid\w*|\bsem cobertura\b/, f: (c) => c.flag("sem_caps") },
    { re: /\b(com|que (?:tem|possui|possuem)|tem|possui) (caps( ad)?|servicos?)( habilitados?)?\b/, f: (c) => c.flag("com_caps") },
    { re: new RegExp(`\\b(?:acima|mais) de ${NUM}(?: habitantes)?`), f: (c, m) => { const v = num(m[1], m[2]); c.filtros.push([`porte_min:${v}`, `Mais de ${fmt(v, 0)} habitantes`, (x) => x.p > v]); } },
    { re: new RegExp(`\\b(?:abaixo|menos|inferior) de ${NUM}(?: habitantes)?`), f: (c, m) => { const v = num(m[1], m[2]); c.filtros.push([`porte_max:${v}`, `Menos de ${fmt(v, 0)} habitantes`, (x) => x.p < v]); } },
    { re: new RegExp(`\\bate ${NUM}(?: habitantes)?`), f: (c, m) => { const v = num(m[1], m[2]); c.filtros.push([`porte_max:${v}`, `Até ${fmt(v, 0)} habitantes`, (x) => x.p <= v]); } },
    { re: new RegExp(`\\bentre ${NUM} e ${NUM}(?: habitantes)?`), f: (c, m) => { const un = m[4] || m[2]; const a = num(m[1], m[2] || un), b = num(m[3], un); c.filtros.push([`porte_faixa:${a}-${b}`, `Entre ${fmt(a, 0)} e ${fmt(b, 0)} habitantes`, (x) => x.p >= a && x.p <= b]); } },
    // superlativos de ordenacao (antes dos adjetivos de filtro)
    { re: new RegExp(`\\b${SUP}\\s+(?:taxas?\\s+(?:de\\s+)?)?internac\\w*`), f: (c, m) => c.ord(/^(menor|menores|menos)$/.test(m[1]) ? "internacao_menor" : "internacao") },
    { re: new RegExp(`\\b(pior|piores|menor|menores)\\s+(?:acessibilidade|acesso|cobertura)`), f: (c) => c.ord("acesso") },
    { re: new RegExp(`\\b(melhor|melhores|maior|maiores)\\s+(?:acessibilidade|acesso|cobertura)`), f: (c) => c.ord("acesso_melhor") },
    { re: new RegExp(`\\b${ADJ}\\s+(?:taxas?\\s+(?:de\\s+)?)?(?:internac\\w*|demanda)`), f: (c, m) => c.flag(/^(baixa|baixas|baixo|pouca|pouco|poucas)$/.test(m[1]) ? "internacao_baixa" : "internacao_alta") },
    { re: /\b(?:internac\w*|demanda)\s+(alta|altas|elevada|elevadas|baixa|baixas)\b/, f: (c, m) => c.flag(/^baix/.test(m[1]) ? "internacao_baixa" : "internacao_alta") },
    { re: /\b(?:baixa|baixas|pouca|pouco|dificil|ruim|precari[ao]s?)\s+(?:acessibilidade|acesso|cobertura)\b/, f: (c) => c.flag("acesso_baixo") },
    { re: /\b(?:acessibilidade|acesso|cobertura)\s+(?:baixa|baixas|baixo|ruim|precari[ao]s?|dificil)\b/, f: (c) => c.flag("acesso_baixo") },
    // adjetivo/superlativo DEPOIS do substantivo: "a taxa de internacao e maior"
    { re: /\b(?:taxas?\s+(?:de\s+)?)?internac\w*\s+(?:e |sao |fica |esta )?(?:maior|maiores|mais alta|mais elevada)\b/, f: (c) => c.ord("internacao") },
    { re: /\b(?:taxas?\s+(?:de\s+)?)?internac\w*\s+(?:e |sao )?(?:menor|menores|mais baixa)\b/, f: (c) => c.ord("internacao_menor") },
    { re: /\b(?:alta|altas|alto|altos|boa|boas|bom|bons)\s+(?:acessibilidade|acesso|cobertura)\b/, f: (c) => c.flag("acesso_alto") },
    { re: /\b(?:acessibilidade|acesso|cobertura)\s+(?:alta|altas|alto|altos|boa|boas|bom|bons)\b/, f: (c) => c.flag("acesso_alto") },
    { re: /\bmal (?:atendid|cobert)\w*/, f: (c) => c.flag("acesso_baixo") },
    { re: /\b(?:longe|distantes?|afastad\w*|isolad\w*)\b/, f: (c) => c.flag("longe") },
    // encaminhamento antes de "perto de": "servico mais proximo de ENT" e pedido de referencia
    { re: /\b(?:encaminh\w*|referenci\w*|referir|onde (?:levar|tratar|atender|buscar|procurar|internar)|para onde|servico (?:mais )?proximo|caps (?:mais )?proximo)\b/, f: (c) => { c.refCue = true; } },
    { re: /\b(?:perto|proximos?)\s+d[eoa]s?\s+ENT\b/, f: (c) => { c.perto_de = true; } },
    { re: /\b(?:perto|proximos?)\b/, f: (c) => c.flag("perto") },
    { re: /\b(?:gruposp|metropole paulista)\b/, f: (c) => c.flag("grande_sp") },
    { re: /\binterior\b/, f: (c) => c.flag("interior") },
    { re: /\blitoral\b|\blitoranea\b/, f: (c) => c.flag("litoral") },
    { re: /\b(?:pequen[oa]s?|menores)\s*(?:portes?)?\b/, f: (c) => c.flag("porte_pequeno") },
    { re: /\bmedi[oa]s?(?: portes?)?\b/, f: (c) => c.flag("porte_medio") },
    { re: /\b(?:grandes?|maiores)\b(?!\s+(?:taxa|numero|indice|demanda|internac))/, f: (c) => c.flag("porte_grande") },
    { re: /\bprior\w*|\bnecessidade\w*|\bcarente\w*|\bcritic\w*|\burgen\w*|\bimplant\w*|\bampli\w*|\bexpand\w*|\bnovos?\b/, f: (c) => c.ord("necessidade") },
    { re: /\b(?:ad iii|ad 3|caps iii ad)\b/, f: (c) => { c.modalidade = "AD III"; c.servicoCue = true; } },
    { re: /\bregi(?:ao|oes)(?: de saude)?\b/, f: (c, m) => { c.regiaoCue = true; if (/oes/.test(m[0])) c.regiaoPlural = true; } },
    { re: /\b(?:servicos?|unidades?|estabelecimentos?|caps)\b/, f: (c) => { c.servicoCue = true; } },
    { re: /\b(?:municipios?|cidades?)\b/, f: (c) => { c.municipiosCue = true; } },
  ];

  function interpretar(texto, ignorar = new Set()) {
    const qn = norm(texto);
    // "Grande Sao Paulo" e um grupo, nao o municipio/regiao "Sao Paulo": marca antes de procurar entidades
    const toks = qn ? qn.replace(/\b(?:grande sao paulo|grande sp|rmsp|regiao metropolitana de sao paulo)\b/g, "gruposp").split(" ") : [];
    const { achados, usado } = entidades(toks);
    // trabalho: tokens de entidade viram o marcador ENT
    const w = toks.map((t, i) => (usado[i] ? "ENT" : t));
    // colapsa sequencias de ENT numa so
    let work = w.join(" ").replace(/(?:ENT )+ENT/g, "ENT");

    const c = {
      filtros: [], ordenacao: null, modalidade: null, refCue: false, servicoCue: false, regiaoCue: false, municipiosCue: false, perto_de: false,
      flag(id) { if (!F[id]) return; if (!this.filtros.some((f) => f[0] === id)) this.filtros.push([id, F[id].rot, F[id].fn]); },
      ord(id) { if (!this.ordenacao) this.ordenacao = id; },
    };
    for (const r of REGRAS) {
      let m;
      const re = new RegExp(r.re.source, "g");
      while ((m = re.exec(work)) !== null) {
        r.f(c, m);
        work = work.slice(0, m.index) + " ".repeat(m[0].length) + work.slice(m.index + m[0].length);
        re.lastIndex = m.index + m[0].length;
        if (m[0].length === 0) re.lastIndex++;
      }
    }
    const residuais = work.split(/\s+/).filter((t) => t && t !== "ENT" && !STOP.has(t) && !GENERICAS.has(t));

    // entidades: resolve ambiguidade municipio x regiao
    const ents = [];
    achados.forEach((a) => {
      const antes = toks.slice(Math.max(0, a.i - 3), a.i).join(" ");
      const cueRegiao = /\bregiao|regional|regioes|\brs\b|\bdrs\b/.test(antes) || c.regiaoCue;
      const temM = a.cand.filter((e) => e.tipo === "municipio"), temR = a.cand.filter((e) => e.tipo === "regiao");
      let escolhidas;
      if (temM.length && !temR.length && /\b(?:regiao|regional|rs|drs)(?: de saude)?(?: d[eoa])?$/.test(antes)) {
        // "regiao de Campinas": a regiao de saude do municipio citado
        escolhidas = [{ tipo: "regiao", id: byC.get(temM[0].id).ri }];
      } else if (temM.length && temR.length) {
        const preferirRegiao = /\bregiao|regional|\brs\b|\bdrs\b/.test(antes) || (c.municipiosCue && (c.filtros.length > 0 || c.ordenacao));
        escolhidas = preferirRegiao ? temR : temM;
      } else escolhidas = a.cand;
      escolhidas.forEach((e) => ents.push({ ...e, frase: toks.slice(a.i, a.i + a.L).join(" "), cueRegiao }));
    });

    const entsAtivas = ents.filter((e) => !ignorar.has(`${e.tipo}:${e.id}`));
    const origem = entsAtivas.find((e) => e.tipo === "municipio");
    const temFiltros = c.filtros.some((f) => !ignorar.has(f[0])) || (!!c.ordenacao && !ignorar.has(`ord:${c.ordenacao}`));
    // filtros "geograficos" (interior, litoral, Grande SP, porte) nao sao pedido de planejamento por si so: valem tambem para servicos
    const filtrosPlanejamento = c.filtros.filter((f) => !ignorar.has(f[0]) && !["interior", "litoral", "grande_sp"].includes(f[0]) && !f[0].startsWith("porte_"));
    const pedePlanejamento = c.municipiosCue || filtrosPlanejamento.length > 0 || (!!c.ordenacao && !ignorar.has(`ord:${c.ordenacao}`));
    let intencao = "planejamento";
    if (c.refCue && origem) intencao = "referencia";
    else if (c.servicoCue && !pedePlanejamento) intencao = "servicos";
    else if (c.regiaoCue && !entsAtivas.some((e) => e.tipo === "regiao") && (!c.municipiosCue || c.regiaoPlural)) intencao = "regioes";
    else if (entsAtivas.length === 1 && !temFiltros && residuais.length === 0 && !c.servicoCue && !c.regiaoCue) intencao = entsAtivas[0].tipo === "municipio" ? "perfil" : "planejamento";

    // monta a interpretacao final (cada item remove-se pelo id via `ignorar`)
    const filtros = [];
    c.filtros.forEach(([id, rot, fn]) => { if (!ignorar.has(id)) filtros.push({ id, rotulo: rot, fn }); });
    const entsUsadas = [];
    ents.forEach((e) => {
      const id = `${e.tipo}:${e.id}`;
      if (ignorar.has(id)) return;
      if (e.tipo === "regiao") {
        const r = byRi.get(e.id);
        entsUsadas.push({ id, tipo: "regiao", rotulo: `Região de saúde: ${r.n}`, ref: e.id });
      } else {
        const m = byC.get(e.id);
        entsUsadas.push({ id, tipo: "municipio", rotulo: `Município: ${m.n}`, ref: e.id });
      }
    });
    const ordId = c.ordenacao && !ignorar.has(`ord:${c.ordenacao}`) ? c.ordenacao : null;
    return {
      consulta: texto, normalizada: qn, intencao, entidades: entsUsadas, filtros, ordenacao: ordId ? { id: `ord:${ordId}`, chave: ordId, rotulo: ORD[ordId].rot } : null,
      modalidade: c.modalidade, residuais, perto_de: c.perto_de, entidadesRegiaoMunicipios: ents,
    };
  }

  /* ---------- ranqueamento ---------- */
  const pass = (m, filtros) => filtros.every((f) => f.fn(m));
  const regiaoDe = (itp) => itp.entidades.filter((e) => e.tipo === "regiao").map((e) => e.ref);
  const munDe = (itp) => itp.entidades.filter((e) => e.tipo === "municipio").map((e) => e.ref);

  const fatosMun = (m) => [
    m.k > 0 ? `${m.k} CAPS AD habilitado${m.k > 1 ? "s" : ""}` : "sem CAPS AD habilitado",
    `acessibilidade ${fmt(m.a, 2)} (${descTercil(m.pa)})`, `internação ${fmt(m.t, 0)}/100 mil (${descTercil(m.pt)})`,
    m.d != null ? `${fmt(m.d, 0)} km do CAPS AD mais próximo` : null,
  ].filter(Boolean);

  const cartaoMun = (m, score, expl) => ({
    tipo: "municipio", id: m.c, titulo: m.n, subtitulo: `${m.r} · ${m.p.toLocaleString("pt-BR")} hab.`, score, explicacao: expl, fatos: fatosMun(m),
    dados: m, selo: m.dz ? "deserto de cuidado" : (rotulos[m.g] || ""),
  });

  function rankMunicipios(itp, filtrosExtras = []) {
    const regs = regiaoDe(itp), muns = munDe(itp);
    let base = mun.filter((m) => pass(m, itp.filtros) && pass(m, filtrosExtras));
    if (regs.length) base = base.filter((m) => regs.includes(m.ri));
    const termos = termosConsulta(itp.residuais);
    const bm = termos.length ? idxMun.buscar(termos) : null;
    const bmMax = bm ? Math.max(0, ...bm.values()) : 0;
    const ord = itp.ordenacao ? ORD[itp.ordenacao.chave] : null;
    const temRestricao = itp.filtros.length > 0 || regs.length > 0 || !!ord;
    let itens = base.map((m) => ({ m, txt: bm && bmMax > 0 ? (bm.get(m.c) || 0) / bmMax : 0, hit: bm ? bm.has(m.c) : true }));
    if (termos.length) itens = itens.filter((x) => x.hit);
    const wTxt = termos.length ? (temRestricao ? 0.3 : 1) : 0;
    itens.forEach((x) => {
      const nec = x.m.need / needMax;
      x.score = ord ? null : wTxt * x.txt + (1 - wTxt) * nec;
      x.nec = nec;
    });
    if (ord) {
      const ch = itens.map((x) => ord.chave(x.m));
      const mn = Math.min(...ch), mx = Math.max(...ch), span = mx - mn || 1;
      itens.forEach((x, i) => { const v = (ch[i] - mn) / span; x.score = wTxt * x.txt + (1 - wTxt) * (ord.desc ? v : 1 - v); });
    }
    itens.sort((a, b) => b.score - a.score || b.m.p - a.m.p);
    return { itens, wTxt, termos, ord };
  }

  function explicaMun(x, wTxt, ord) {
    const e = [];
    if (wTxt > 0) e.push({ rotulo: "Correspondência de texto", valor: x.txt, peso: wTxt });
    if (ord) e.push({ rotulo: ord.rot, valor: Math.max(0, Math.min(1, x.score)), peso: 1 - wTxt });
    else { e.push({ rotulo: "Baixo acesso", valor: 1 - x.m.pa, peso: (1 - wTxt) * 0.5 }); e.push({ rotulo: "Alta internação", valor: x.m.pt, peso: (1 - wTxt) * 0.5 }); }
    return e;
  }

  function rankRegioes(itp) {
    const ord = itp.ordenacao ? ORD[itp.ordenacao.chave] : null;
    let base = reg.filter((r) => itp.filtros.every((f) => {
      if (f.id === "interior") return r.gs === 0;
      if (f.id === "grande_sp") return r.gs === 1;
      if (f.id === "litoral") return r.lit === 1;
      if (f.id === "sem_caps") return r.sem > 0;
      if (f.id === "deserto") return r.dz > 0;
      if (f.id === "acesso_baixo") return r.pa <= 1 / 3;
      if (f.id === "acesso_alto") return r.pa >= 2 / 3;
      if (f.id === "internacao_alta") return r.pt >= 2 / 3;
      if (f.id === "internacao_baixa") return r.pt <= 1 / 3;
      return true;
    }));
    const termos = termosConsulta(itp.residuais);
    const bm = termos.length ? idxReg.buscar(termos) : null;
    if (termos.length) base = base.filter((r) => bm.has(r.ri));
    const bmMax = bm ? Math.max(0, ...bm.values()) : 0;
    const porSem = itp.filtros.some((f) => f.id === "sem_caps") || itp.filtros.some((f) => f.id === "deserto");
    let chave = (r) => r.need;
    if (ord) chave = (r) => ({ internacao: r.t, internacao_menor: -r.t, acesso: -r.a, acesso_melhor: r.a, populacao: r.p, necessidade: r.need }[itp.ordenacao.chave]);
    else if (itp.filtros.some((f) => f.id === "deserto")) chave = (r) => r.dz + r.need * 0.01;
    else if (itp.filtros.some((f) => f.id === "sem_caps")) chave = (r) => r.sem + r.need * 0.01;
    const ks = base.map(chave), mn = Math.min(...ks), mx = Math.max(...ks), span = mx - mn || 1;
    const itens = base.map((r, i) => ({ r, score: (ks[i] - mn) / span, txt: bm && bmMax ? (bm.get(r.ri) || 0) / bmMax : 0 }));
    itens.sort((a, b) => b.score - a.score || b.r.p - a.r.p);
    return itens.map((x) => ({
      tipo: "regiao", id: x.r.ri, titulo: x.r.n, subtitulo: `${x.r.nm} municípios · ${x.r.p.toLocaleString("pt-BR")} hab.`, score: x.score,
      explicacao: [{ rotulo: ord ? ord.rot : (porSem ? "Municípios sem CAPS AD / desertos" : "Necessidade estimada"), valor: x.score, peso: 1 }],
      fatos: [`${x.r.sem} de ${x.r.nm} municípios sem CAPS AD`, `${x.r.dz} município${x.r.dz === 1 ? "" : "s"} em deserto de cuidado`,
        `acessibilidade ${fmt(x.r.a, 2)} (${descTercil(x.r.pa)})`, `internação ${fmt(x.r.t, 0)}/100 mil (${descTercil(x.r.pt)})`], dados: x.r, selo: "",
    }));
  }

  function cartaoSrv(s, score, expl, extra = []) {
    return { tipo: "servico", id: s.id, titulo: s.n, subtitulo: `${s.mn} · ${s.r} · CAPS ${s.mo}`, score, explicacao: expl, fatos: [`modalidade ${s.mo}`, ...extra], dados: s, selo: "" };
  }

  function rankServicos(itp) {
    const regs = regiaoDe(itp), muns = munDe(itp);
    const termos = termosConsulta(itp.residuais).filter((t) => !["iii", "ad"].includes(t));
    const bm = termos.length ? idxSrv.buscar(termos) : null;
    const bmMax = bm ? Math.max(0, ...bm.values()) : 0;
    const filtrosMun = itp.filtros;
    let base = srv.filter((s) => {
      const m = byC.get(s.m);
      if (!m || !pass(m, filtrosMun)) return false;
      if (regs.length && !regs.includes(m.ri)) return false;
      if (muns.length && !itp.perto_de && !muns.includes(s.m)) return false;
      if (itp.modalidade && s.mo !== itp.modalidade) return false;
      if (termos.length && !bm.has(s.id)) return false;
      return true;
    });
    const avisos = [];
    let ref = null;
    if (muns.length) ref = byC.get(muns[0]);
    let itens;
    if (muns.length && !itp.perto_de && base.length === 0) {
      // municipio sem servico: cai para o mais proximo (referencia)
      avisos.push(`${ref.n} não tem CAPS AD habilitado${itp.modalidade ? ` da modalidade ${itp.modalidade}` : ""}; mostrando os mais próximos.`);
      itens = srv.filter((s) => (!itp.modalidade || s.mo === itp.modalidade)).map((s) => ({ s, km: haversine(ref.la, ref.lo, s.la, s.lo) })).filter((x) => x.km <= 150)
        .sort((a, b) => a.km - b.km).slice(0, 8).map((x, i) => ({ ...x, score: 1 - x.km / 150 }));
    } else {
      itens = base.map((s) => ({ s, km: ref ? haversine(ref.la, ref.lo, s.la, s.lo) : null, score: bm && bmMax ? (bm.get(s.id) || 0) / bmMax : 0.5 }));
      if (itp.perto_de && ref) itens = itens.map((x) => ({ ...x, score: Math.max(0, 1 - x.km / 150) })).filter((x) => x.km <= 150);
      itens.sort((a, b) => b.score - a.score || (a.km ?? 0) - (b.km ?? 0) || a.s.n.localeCompare(b.s.n, "pt"));
    }
    return { avisos, cartoes: itens.map((x) => cartaoSrv(x.s, x.score, [{ rotulo: ref ? "Proximidade" : "Correspondência", valor: Math.max(0, Math.min(1, x.score)), peso: 1 }],
      x.km != null ? [`${fmt(x.km, 0)} km de ${ref.n}`] : [])) };
  }

  function referencia(origemC, modalidade = null, limite = 8) {
    const o = byC.get(origemC), W = meta.pesos_referencia;
    const lista = srv.filter((s) => !modalidade || s.mo === modalidade).map((s) => ({ s, km: haversine(o.la, o.lo, s.la, s.lo) })).filter((x) => x.km <= 150).map((x) => {
      const prox = 1 - x.km / 150, mesma = byC.get(x.s.m).ri === o.ri ? 1 : 0;
      const comps = [{ rotulo: "Proximidade", valor: prox, peso: W.proximidade }, { rotulo: "Mesma região de saúde", valor: mesma, peso: W.regiao }, { rotulo: "Abertura a moradores de fora", valor: x.s.ab, peso: W.abertura }];
      return { ...x, score: comps.reduce((a, c) => a + c.valor * c.peso, 0), comps };
    }).sort((a, b) => b.score - a.score || a.km - b.km);
    return lista.slice(0, limite).map((x) => cartaoSrv(x.s, x.score, x.comps, [`${fmt(x.km, 0)} km`, `folga relativa ${fmt(x.s.f, 2)} (informativa)`]));
  }

  /** palavras de nomes proximas (distancia de edicao <= 2) dos termos livres; `d` = distancia */
  function sugestoes(itp) {
    const out = [];
    itp.residuais.filter((t) => t.length >= 5).forEach((t) => {
      nomesUnigramas.map((n) => [n, lev(t, n)]).filter(([, d]) => d >= 1 && d <= 2).sort((a, b) => a[1] - b[1]).slice(0, 3)
        .forEach(([n, d]) => out.push({ de: t, norm: n, para: grafia.get(n), d }));
    });
    const vistos = new Set();
    return out.filter((s) => (vistos.has(s.para) ? false : vistos.add(s.para))).slice(0, 3);
  }

  /* ---------- baselines para a avaliacao (nao usadas pelo site) ---------- */
  const idxPorEscopo = { municipio: idxMun, regiao: idxReg, servico: idxSrv };
  const buscaBruta = (texto, escopo) => {
    const t = norm(texto).split(" ").filter((x) => x && !STOP.has(x)).map(stem);
    return [...idxPorEscopo[escopo].buscar(t).entries()].sort((a, b) => b[1] - a[1]).map(([id]) => id);
  };
  const hibridoSemInterpretacao = (texto) => {
    const t = norm(texto).split(" ").filter((x) => x && !STOP.has(x)).map(stem);
    const bm = idxMun.buscar(t), mx = Math.max(0, ...bm.values()) || 1;
    return mun.map((m) => ({ id: m.c, s: 0.3 * (bm.get(m.c) || 0) / mx + 0.7 * m.need / needMax })).sort((a, b) => b.s - a.s).map((x) => x.id);
  };
  const ordemNecessidade = (escopo) => (escopo === "regiao" ? [...reg].sort((a, b) => b.need - a.need).map((r) => r.ri) : [...mun].sort((a, b) => b.need - a.need).map((m) => m.c));

  function buscar(texto, opcoes = {}) {
    const itp = interpretar(texto, opcoes.ignorar || new Set());
    const t0 = typeof performance !== "undefined" ? performance.now() : 0;
    let resultados = [], avisos = [], extras = null;

    if (!itp.normalizada) return { interpretacao: itp, resultados: [], total: 0, avisos: [], ms: 0 };

    if (itp.intencao === "referencia") {
      const o = byC.get(munDe(itp)[0]);
      resultados = referencia(o.c, itp.modalidade);
      if (!resultados.length) avisos.push(`Nenhum CAPS AD habilitado a até 150 km de ${o.n}.`);
      extras = { origem: o };
    } else if (itp.intencao === "servicos") {
      const r = rankServicos(itp);
      resultados = r.cartoes; avisos = r.avisos;
    } else if (itp.intencao === "regioes") {
      resultados = rankRegioes(itp);
    } else if (itp.intencao === "perfil") {
      const m = byC.get(munDe(itp)[0]);
      resultados = [cartaoMun(m, 1, [{ rotulo: "Correspondência de nome", valor: 1, peso: 1 }])];
      extras = { origem: m, referencia: referencia(m.c, null, 5) };
    } else {
      const { itens, wTxt, termos, ord } = rankMunicipios(itp);
      const regs = regiaoDe(itp);
      if (regs.length === 1 && !itp.filtros.length && !itp.ordenacao && !termos.length) { /* so a regiao: ranking por necessidade */ }
      resultados = itens.map((x) => cartaoMun(x.m, x.score, explicaMun(x, wTxt, ord)));
      if (regs.length === 1) extras = { regiao: byRi.get(regs[0]) };
    }
    if (!resultados.length) {
      const sg = sugestoes(itp);
      // erro de digitacao de uma letra (>= 6 letras): corrige e refaz a busca uma vez
      const quase = sg.find((s) => s.d === 1 && s.de.length >= 6);
      if (quase && !opcoes._corrigido) {
        const texto2 = norm(texto).split(" ").map((t) => (t === quase.de ? quase.norm : t)).join(" ");
        const r2 = buscar(texto2, { ...opcoes, _corrigido: true });
        if (r2.total) {
          r2.avisos = [`Mostrando resultados para “${quase.para}” (você digitou “${quase.de}”).`, ...r2.avisos];
          r2.interpretacao.corrigido = { de: quase.de, para: quase.para };
          return r2;
        }
      }
      if (sg.length) avisos.push(`Você quis dizer: ${sg.map((s) => s.para).join(", ")}?`);
    }
    return { interpretacao: itp, resultados, total: resultados.length, avisos, extras, ms: typeof performance !== "undefined" ? performance.now() - t0 : 0 };
  }

  const exemplos = [
    "municípios sem CAPS AD na região de Assis",
    "cidades pequenas com alta internação e sem serviço",
    "onde priorizar CAPS AD no interior",
    "para onde encaminhar paciente de Registro",
    "CAPS AD III em Campinas",
    "regiões com maior taxa de internação",
    "desertos de cuidado na Alta Mogiana",
    "maiores municípios sem CAPS AD habilitado",
  ];

  return { interpretar, buscar, referencia, baselines: { buscaBruta, hibridoSemInterpretacao, ordemNecessidade }, municipio: (c) => byC.get(c), regiao: (ri) => byRi.get(ri), servicos: srv, municipios: mun, regioes: reg, exemplos,
    corpus: { municipios: mun.length, regioes: reg.length, servicos: srv.length, documentos: mun.length + reg.length + srv.length }, filtrosDisponiveis: F, ordenacoes: ORD };
}
