import { criarMotor, norm } from "./busca.js";

const $ = (s, r = document) => r.querySelector(s);
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const fmt = (v, d = 1) => (v == null || Number.isNaN(v) ? "—" : Number(v).toLocaleString("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d }));
const J = (n) => fetch(`data/${n}`).then((r) => { if (!r.ok) throw new Error(`${n}: ${r.status}`); return r.json(); });

let motor, meta, M, S, R, map, geoLayer, srvLayer, linhasLayer;
const munLayers = new Map(), srvMarkers = new Map(), cores = new Map();
let ignorar = new Set(), ultimo = null, mostrando = 20, selecionado = null, destMun = new Set(), destSrv = new Set(), temporizador = null;
const camposGlobais = {};

/* ---------------- tema ---------------- */
const TEMAS = [["auto", "Tema: automático"], ["claro", "Tema: claro"], ["escuro", "Tema: escuro"]];
const temaAtual = () => { const a = document.documentElement.getAttribute("data-theme"); return a === "dark" ? "escuro" : a === "light" ? "claro" : "auto"; };
function aplicarTema(t) {
  const r = document.documentElement;
  if (t === "escuro") r.setAttribute("data-theme", "dark"); else if (t === "claro") r.setAttribute("data-theme", "light"); else r.removeAttribute("data-theme");
  try { t === "auto" ? localStorage.removeItem("tema") : localStorage.setItem("tema", t); } catch (e) { /* sem armazenamento */ }
  $("#tema").textContent = TEMAS.find((x) => x[0] === t)[1];
}
$("#tema").addEventListener("click", () => aplicarTema(TEMAS[(TEMAS.findIndex((x) => x[0] === temaAtual()) + 1) % 3][0]));
$("#tema").textContent = TEMAS.find((x) => x[0] === temaAtual())[1];

/* ---------------- diálogos ---------------- */
document.querySelectorAll("[data-abre]").forEach((b) => b.addEventListener("click", () => { const d = $("#" + b.dataset.abre); if (b.dataset.abre === "dlg-aval") renderAvaliacao(); d.showModal(); }));
document.querySelectorAll("dialog").forEach((d) => {
  d.addEventListener("click", (e) => { if (e.target === d) d.close(); });
  d.querySelector("[data-fecha]").addEventListener("click", () => d.close());
});

/* ---------------- carga ---------------- */
Promise.all([J("meta.json"), J("municipios.json"), J("regioes.json"), J("servicos.json"), J("municipios.geojson")])
  .then(([m, mun, reg, srv, geo]) => init(m, mun, reg, srv, geo))
  .catch((e) => { $("#resultados").innerHTML = `<div class="vazio"><b>Não foi possível carregar os dados.</b><br>${esc(e.message)}</div>`; });

function init(m, mun, reg, srv, geo) {
  meta = m; M = mun; R = reg; S = srv;
  motor = criarMotor({ municipios: mun, regioes: reg, servicos: srv, meta: m });
  M.forEach((x) => { camposGlobais[x.c] = x; });
  iniciarMapa(geo);
  iniciarBusca();
  conteudoDialogos();
  const p = new URLSearchParams(location.search);
  const cam = p.get("camada");
  if (cam && ["a", "t", "d", "g"].includes(cam)) { $("#camada").value = cam; pintar(); }
  const q = p.get("q");
  if (q) { $("#q").value = q; executar(q, { rolar: false }); } else boasVindas();
  addEventListener("resize", () => map.invalidateSize());
  setTimeout(() => map.invalidateSize(), 80);
}

/* ---------------- mapa ---------------- */
const RAMPA = ["#fff5eb", "#fdd0a2", "#fd8d3c", "#d94801", "#7f2704"];
const CATEG = { 1: "#d55e00", 2: "#56b4e9", 3: "#0072b2", 4: "#009e73", 5: "#e6c200" };
const CAMADAS = { a: { rot: "Acessibilidade relativa (1 = média)", ruim: "baixo", d: 2 }, t: { rot: "Internações F10–F19 / 100 mil hab. 15+ / ano", ruim: "alto", d: 0 }, d: { rot: "Distância ao CAPS AD mais próximo (km)", ruim: "alto", d: 0 } };

function iniciarMapa(geo) {
  map = L.map("map", { zoomControl: true, zoomSnap: 0.25, maxZoom: 13 });
  map.attributionControl.addAttribution("Malha: IBGE");
  geoLayer = L.geoJSON(geo, {
    style: () => ({ weight: 0.4, className: "mun", fillOpacity: 0.85 }),
    onEachFeature: (f, l) => {
      const x = camposGlobais[f.properties.c]; if (!x) return;
      munLayers.set(x.c, l);
      l.bindTooltip(esc(x.n), { sticky: true });
      l.on("click", () => executar(x.n, { rolar: true }));
    },
  }).addTo(map);
  srvLayer = L.layerGroup(S.map((s) => {
    const mk = L.circleMarker([s.la, s.lo], { radius: 5, weight: 1.5, className: "srv", fillOpacity: 0.95 })
      .bindPopup(`<b>${esc(s.n)}</b><br>${esc(s.mn)} · CAPS ${esc(s.mo)}<br>Folga relativa: ${fmt(s.f, 2)} (1 = média)<br><a href="#" data-q="CAPS AD perto de ${esc(s.mn)}">Outros CAPS AD próximos</a>`);
    srvMarkers.set(s.id, mk);
    return mk;
  })).addTo(map);
  map.fitBounds(geoLayer.getBounds(), { padding: [10, 10] });
  $("#camada").addEventListener("change", () => { pintar(); atualizaUrl(); });
  $("#vsrv").addEventListener("change", () => ($("#vsrv").checked ? srvLayer.addTo(map) : map.removeLayer(srvLayer)));
  linhasLayer = L.layerGroup().addTo(map);
  pintar();
}

function pintar() {
  const k = $("#camada").value;
  if (k === "g") {
    M.forEach((x) => cores.set(x.c, CATEG[x.g]));
    legenda(`<b>Tipologia (K-Means, k = 5)</b><br>${[1, 2, 3, 4, 5].map((g) => `<i style="background:${CATEG[g]}"></i>${esc(meta.clusters[g])} (${M.filter((x) => x.g === g).length})`).join("<br>")}<br><span style="color:var(--muted)">Rótulos são interpretação nossa; a silhueta é baixa (≈0,28).</span>`);
  } else {
    const vals = M.map((x) => x[k]).filter((v) => v != null && !Number.isNaN(v)).sort((a, b) => a - b);
    const cortes = [1, 2, 3, 4].map((i) => vals[Math.floor(i * vals.length / 5)]);
    const ruimBaixo = CAMADAS[k].ruim === "baixo";
    const cor = (v) => { if (v == null || Number.isNaN(v)) return "#bbb"; let i = cortes.filter((c) => v >= c).length; if (ruimBaixo) i = 4 - i; return RAMPA[i]; };
    M.forEach((x) => cores.set(x.c, cor(x[k])));
    const lim = [vals[0], ...cortes, vals[vals.length - 1]];
    let h = `<b>${CAMADAS[k].rot}</b><br>`;
    for (let i = 0; i < 5; i++) { const idx = ruimBaixo ? 4 - i : i; h += `<i style="background:${RAMPA[idx]}"></i>${fmt(lim[i], CAMADAS[k].d)} – ${fmt(lim[i + 1], CAMADAS[k].d)}<br>`; }
    legenda(h + `<span style="color:var(--muted)">Tons escuros = ${ruimBaixo ? "menor acessibilidade" : "valores mais altos"} (quintis)</span>`);
  }
  munLayers.forEach((l, c) => l.setStyle({ fillColor: cores.get(c) }));
}
function legenda(html) {
  if (map._leg) map.removeControl(map._leg);
  const leg = L.control({ position: "bottomleft" });
  leg.onAdd = () => { const d = L.DomUtil.create("div", "legenda"); d.innerHTML = html; return d; };
  leg.addTo(map); map._leg = leg;
}

function destacar({ muns = [], srvs = [], linhas = [], ajustar = true }) {
  destMun.forEach((c) => munLayers.get(c)?.getElement()?.classList.remove("dest", "sel"));
  destSrv.forEach((id) => { const mk = srvMarkers.get(id); mk?.getElement()?.classList.remove("dest"); mk?.setRadius(5); });
  linhasLayer.clearLayers();
  destMun = new Set(muns); destSrv = new Set(srvs);
  const pts = [];
  muns.forEach((c) => { const l = munLayers.get(c); if (l) { l.getElement()?.classList.add("dest"); l.bringToFront(); const x = camposGlobais[c]; pts.push([x.la, x.lo]); } });
  srvs.forEach((id) => { const mk = srvMarkers.get(id); if (mk) { mk.getElement()?.classList.add("dest"); mk.setRadius(8); mk.bringToFront(); pts.push(mk.getLatLng()); } });
  linhas.forEach(([a, b]) => L.polyline([a, b], { color: getComputedStyle(document.documentElement).getPropertyValue("--accent").trim() || "#1f5f8b", weight: 2.5, dashArray: "6 6" }).addTo(linhasLayer));
  if (ajustar && pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.25), { maxZoom: 10, animate: true });
}

/* ---------------- busca ---------------- */
const INTENCAO = { planejamento: "Planejamento: municípios", regioes: "Planejamento: regiões", servicos: "Serviços (CAPS AD)", referencia: "Encaminhamento", perfil: "Perfil do município" };

function iniciarBusca() {
  const q = $("#q");
  $("#form").addEventListener("submit", (e) => { e.preventDefault(); fecharSug(); executar(q.value, { rolar: true }); });
  q.addEventListener("input", () => {
    $("#limpar").hidden = !q.value;
    sugerir(); clearTimeout(temporizador);
    if (q.value.trim().length >= 3) temporizador = setTimeout(() => executar(q.value, { rolar: false }), 650);
    else if (!q.value.trim()) { ignorar = new Set(); boasVindas(); atualizaUrl(); }
  });
  q.addEventListener("keydown", (e) => {
    const lista = [...document.querySelectorAll("#sugestoes li")];
    const i = lista.findIndex((li) => li.getAttribute("aria-selected") === "true");
    if (e.key === "ArrowDown" && lista.length) { e.preventDefault(); marcar(lista, (i + 1) % lista.length); }
    else if (e.key === "ArrowUp" && lista.length) { e.preventDefault(); marcar(lista, (i - 1 + lista.length) % lista.length); }
    else if (e.key === "Enter" && i >= 0) { e.preventDefault(); lista[i].click(); }
    else if (e.key === "Escape") fecharSug();
  });
  q.addEventListener("focus", () => sugerir());
  document.addEventListener("click", (e) => { if (!e.target.closest("#form")) fecharSug(); });
  $("#limpar").addEventListener("click", () => { q.value = ""; $("#limpar").hidden = true; ignorar = new Set(); boasVindas(); atualizaUrl(); q.focus(); });
  document.addEventListener("keydown", (e) => { if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName) && !document.querySelector("dialog[open]")) { e.preventDefault(); q.focus(); q.select(); } });
  document.addEventListener("click", (e) => { const a = e.target.closest("[data-q]"); if (a) { e.preventDefault(); $("#q").value = a.dataset.q; executar(a.dataset.q, { rolar: true }); } });
  $("#exemplos").innerHTML = `<p class="rotulo-chips">Experimente</p><div class="chips">${motor.exemplos.map((e) => `<button type="button" class="chip ex" data-q="${esc(e)}">${esc(e)}</button>`).join("")}</div>`;
}

/* autocompletar de entidades (municipios, regioes, servicos) */
let nomes = null;
function sugerir() {
  if (!nomes) nomes = [...M.map((m) => ({ t: "Município", n: m.n, nn: norm(m.n), p: m.p })), ...R.map((r) => ({ t: "Região", n: r.n, nn: norm(r.n), p: r.p })),
    ...S.map((s) => ({ t: "CAPS AD", n: s.n, nn: norm(s.n), p: 0 }))];
  const q = $("#q"), palavras = q.value.split(/\s+/).filter(Boolean);
  const ul = $("#sugestoes");
  if (!palavras.length) return fecharSug();
  let achou = [], usado = 0;
  for (let n = Math.min(3, palavras.length); n >= 1 && !achou.length; n--) {
    const frag = norm(palavras.slice(-n).join(" "));
    if (frag.length < 2) continue;
    achou = nomes.filter((x) => x.nn.startsWith(frag) && x.nn !== frag).sort((a, b) => b.p - a.p).slice(0, 7);
    if (achou.length) usado = n;
  }
  if (!achou.length) return fecharSug();
  ul.innerHTML = achou.map((x, i) => `<li role="option" id="sg${i}" aria-selected="false" data-n="${esc(x.n)}" data-u="${usado}"><span>${esc(x.n)}</span><span class="t">${x.t}</span></li>`).join("");
  ul.hidden = false; q.setAttribute("aria-expanded", "true");
  ul.querySelectorAll("li").forEach((li) => li.addEventListener("click", () => {
    const pal = q.value.split(/\s+/).filter(Boolean); pal.splice(pal.length - Number(li.dataset.u), Number(li.dataset.u), li.dataset.n);
    q.value = pal.join(" "); fecharSug(); $("#limpar").hidden = false; executar(q.value, { rolar: true }); q.focus();
  }));
}
const marcar = (lista, i) => { lista.forEach((li, k) => li.setAttribute("aria-selected", k === i ? "true" : "false")); $("#q").setAttribute("aria-activedescendant", lista[i].id); lista[i].scrollIntoView({ block: "nearest" }); };
function fecharSug() { const ul = $("#sugestoes"); ul.hidden = true; ul.innerHTML = ""; $("#q").setAttribute("aria-expanded", "false"); $("#q").removeAttribute("aria-activedescendant"); }

function executar(texto, { rolar = false, manterIgnorar = false } = {}) {
  clearTimeout(temporizador);
  if (!manterIgnorar) ignorar = new Set();
  const t = String(texto || "").trim();
  if (!t) { boasVindas(); return; }
  $("#q").value = texto; $("#limpar").hidden = false;
  const r = motor.buscar(t, { ignorar });
  ultimo = { r, t }; mostrando = 20; selecionado = null;
  renderInterpretacao(r);
  renderResultados(r);
  const alvo = destaquesDe(r);
  destacar({ ...alvo, ajustar: true });
  atualizaUrl();
  if (rolar && matchMedia("(max-width:900px)").matches) $("#resultados").scrollIntoView({ behavior: "smooth", block: "start" });
  else if (rolar) $("#resultados").scrollTo({ top: 0 });
}

function destaquesDe(r) {
  const itens = r.resultados.slice(0, r.interpretacao.intencao === "planejamento" ? 12 : 8);
  const muns = [], srvs = [], linhas = [];
  itens.forEach((x) => { if (x.tipo === "municipio") muns.push(x.id); else if (x.tipo === "servico") srvs.push(x.id); else if (x.tipo === "regiao") M.filter((m) => m.ri === x.id).forEach((m) => muns.push(m.c)); });
  const ex = r.extras;
  if (ex?.origem) { muns.push(ex.origem.c); (r.interpretacao.intencao === "referencia" ? r.resultados : ex.referencia || []).slice(0, 3).forEach((s) => { srvs.push(s.id); linhas.push([[ex.origem.la, ex.origem.lo], [s.dados.la, s.dados.lo]]); }); }
  return { muns: [...new Set(muns)], srvs: [...new Set(srvs)], linhas };
}

function renderInterpretacao(r) {
  const it = r.interpretacao, el = $("#interp"), ex = $("#exemplos");
  ex.hidden = true;
  const chip = (cls, texto, id) => `<span class="chip ${cls}">${esc(texto)}${id ? `<button type="button" aria-label="Remover: ${esc(texto)}" data-rm="${esc(id)}">×</button>` : ""}</span>`;
  let h = `<p class="rotulo-chips">Como entendi</p><div class="chips">${chip("int", INTENCAO[it.intencao])}`;
  it.entidades.forEach((e) => { h += chip("", e.rotulo, e.id); });
  it.filtros.forEach((f) => { h += chip("", f.rotulo, f.id); });
  if (it.ordenacao) h += chip("", `Ordem: ${it.ordenacao.rotulo.toLowerCase()}`, it.ordenacao.id);
  if (it.modalidade) h += chip("", `Modalidade: CAPS ${it.modalidade}`);
  if (it.perto_de) h += chip("", "Perto de");
  if (it.residuais.length) h += chip("", `Termos livres: ${it.residuais.join(" ")}`);
  el.innerHTML = h + "</div>";
  el.querySelectorAll("[data-rm]").forEach((b) => b.addEventListener("click", () => { ignorar.add(b.dataset.rm); executar($("#q").value, { manterIgnorar: true }); }));
}

function cartao(x, i) {
  const rotuloTipo = { municipio: "Município", regiao: "Região", servico: "CAPS AD" }[x.tipo];
  const comp = (x.explicacao || []).map((c) => `<div class="comp"><span>${esc(c.rotulo)} (${Math.round(c.peso * 100)}%)</span><span class="barra" role="img" aria-label="${esc(c.rotulo)}: ${Math.round(c.valor * 100)} de 100"><i style="width:${Math.round(Math.max(0, Math.min(1, c.valor)) * 100)}%"></i></span><span>${Math.round(c.valor * 100)}</span></div>`).join("");
  return `<article class="cartao${selecionado === `${x.tipo}:${x.id}` ? " sel" : ""}" tabindex="0" role="button" data-i="${i}" aria-label="${esc(x.titulo)}">
    <div class="topo-c"><span class="pos">${i + 1}</span><div><h3><span class="badge ${x.tipo}">${rotuloTipo}</span>${esc(x.titulo)}</h3><div class="sub">${esc(x.subtitulo)}</div></div></div>
    ${x.selo ? `<span class="selo">${esc(x.selo)}</span>` : ""}
    <ul class="fatos">${(x.fatos || []).map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
    ${comp ? `<details class="porque"><summary>Por que este resultado?</summary>${comp}</details>` : ""}
  </article>`;
}

function renderResultados(r) {
  const el = $("#resultados"), it = r.interpretacao;
  let h = `<div class="res-cab"><span class="n">${r.total} resultado${r.total === 1 ? "" : "s"}</span><span class="ms">${fmt(r.ms, 0)} ms</span><button class="btn" type="button" id="copiar">Copiar link</button></div>`;
  (r.avisos || []).forEach((a) => { h += `<div class="aviso-res">${esc(a)}</div>`; });
  if (r.extras?.regiao && it.intencao === "planejamento") {
    const g = r.extras.regiao;
    h += `<div class="aviso-res"><b>Região ${esc(g.n)}</b>: ${g.nm} municípios, ${g.sem} sem CAPS AD habilitado, ${g.dz} em deserto de cuidado. Acessibilidade ${fmt(g.a, 2)} · internação ${fmt(g.t, 0)}/100 mil.</div>`;
  }
  if (it.intencao === "referencia" && r.extras?.origem) {
    const o = r.extras.origem;
    h += `<div class="aviso-res"><b>Origem: ${esc(o.n)}</b> (${esc(o.r)}) · ${o.k > 0 ? `${o.k} CAPS AD no município` : "sem CAPS AD habilitado"}. Estar na lista <b>não garante vaga</b>: o acesso de moradores de outros municípios depende de pactuação regional.</div>`;
  }
  if (!r.total) {
    h += `<div class="vazio"><b>Nenhum resultado.</b><br>Tente remover um filtro (×) acima, usar menos palavras ou escolher um dos exemplos.</div>`;
  } else {
    h += r.resultados.slice(0, mostrando).map((x, i) => cartao(x, i)).join("");
    if (r.total > mostrando) h += `<button class="mais" type="button" id="mais">Mostrar mais (${r.total - mostrando} restantes)</button>`;
  }
  if (it.intencao === "perfil" && r.extras?.referencia?.length) {
    h += `<p class="sec-tit">Para onde encaminhar a partir de ${esc(r.extras.origem.n)}</p>` + r.extras.referencia.map((x, i) => cartao(x, 1000 + i)).join("") +
      `<p class="nota">Ranking de referência: proximidade ${Math.round(meta.pesos_referencia.proximidade * 100)}%, mesma região de saúde ${Math.round(meta.pesos_referencia.regiao * 100)}%, abertura a moradores de fora ${Math.round(meta.pesos_referencia.abertura * 100)}%. Avaliado em <a href="#" data-abre-aval>Avaliação</a>: não supera a simples distância de forma significativa.</p>`;
  }
  el.innerHTML = h;
  $("#copiar")?.addEventListener("click", copiarLink);
  $("#mais")?.addEventListener("click", () => { mostrando += 20; renderResultados(ultimo.r); });
  el.querySelector("[data-abre-aval]")?.addEventListener("click", (e) => { e.preventDefault(); renderAvaliacao(); $("#dlg-aval").showModal(); });
  el.querySelectorAll(".cartao").forEach((c) => {
    const go = () => { const i = Number(c.dataset.i); const x = i >= 1000 ? r.extras.referencia[i - 1000] : r.resultados[i]; selecionar(x, c); };
    c.addEventListener("click", (e) => { if (!e.target.closest("details")) go(); });
    c.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && !e.target.closest("details")) { e.preventDefault(); go(); } });
  });
}

function selecionar(x, elCartao) {
  document.querySelectorAll(".cartao.sel").forEach((c) => c.classList.remove("sel"));
  elCartao?.classList.add("sel");
  munLayers.forEach((l) => l.getElement()?.classList.remove("sel"));
  selecionado = `${x.tipo}:${x.id}`;
  if (x.tipo === "municipio") {
    const l = munLayers.get(x.id); l?.getElement()?.classList.add("sel"); l?.bringToFront();
    const m = camposGlobais[x.id]; map.flyTo([m.la, m.lo], Math.max(map.getZoom(), 9), { duration: 0.6 });
  } else if (x.tipo === "servico") {
    const mk = srvMarkers.get(x.id); if (mk) { map.flyTo(mk.getLatLng(), Math.max(map.getZoom(), 10), { duration: 0.6 }); mk.openPopup(); }
  } else if (x.tipo === "regiao") {
    const pts = M.filter((m) => m.ri === x.id).map((m) => [m.la, m.lo]);
    if (pts.length) map.fitBounds(L.latLngBounds(pts).pad(0.3), { maxZoom: 10 });
  }
}

function boasVindas() {
  ultimo = null; destacar({ ajustar: false });
  $("#interp").innerHTML = ""; $("#exemplos").hidden = false;
  const k = (b, s) => `<div class="kpi"><b>${b}</b><span>${s}</span></div>`;
  $("#resultados").innerHTML = `<div class="boas"><h2>O que você quer saber?</h2>
    <p>Pergunte em linguagem natural. O motor entende municípios, regiões de saúde, filtros e pedidos de encaminhamento, e explica cada resultado.</p>
    <div class="kpis">${k(meta.n_municipios, "municípios")}${k(meta.n_servicos, `CAPS AD habilitados (dez/${meta.ano})`)}${k(meta.n_desertos, "em “deserto de cuidado”")}${k(R.length, "regiões de saúde")}</div>
    <ul><li><b>Planejamento:</b> “cidades pequenas com alta internação e sem serviço”</li>
    <li><b>Encaminhamento:</b> “para onde encaminhar paciente de Registro”</li>
    <li><b>Serviços:</b> “CAPS AD III em Campinas”</li>
    <li><b>Regiões:</b> “regiões com maior taxa de internação”</li></ul>
    <p class="nota">Dica: clique em qualquer município do mapa para ver o perfil e o encaminhamento. Os resultados são estimativas e <b>não substituem avaliação profissional</b>.</p></div>`;
}

function atualizaUrl() {
  const p = new URLSearchParams(location.search);
  const q = $("#q").value.trim();
  q ? p.set("q", q) : p.delete("q");
  $("#camada").value !== "a" ? p.set("camada", $("#camada").value) : p.delete("camada");
  history.replaceState(null, "", `${location.pathname}${p.toString() ? "?" + p : ""}`);
}
async function copiarLink() {
  try { await navigator.clipboard.writeText(location.href); $("#copiar").textContent = "Link copiado"; }
  catch (e) { prompt("Copie o link:", location.href); }
  setTimeout(() => { const b = $("#copiar"); if (b) b.textContent = "Copiar link"; }, 1800);
}

/* ---------------- diálogos: conteúdo ---------------- */
function conteudoDialogos() {
  const c = motor.corpus, W = meta.pesos_referencia;
  $("#corpo-como").innerHTML = `
    <p>A busca é um <b>motor de recuperação de informação</b> sobre um corpus próprio, com interpretação da pergunta e ranqueamento <b>explicável</b>. Não usa IA generativa: cada resultado traz a decomposição do seu score.</p>
    <div class="passos">
      <div class="passo"><b>1. Corpus</b>${c.documentos} documentos: ${c.municipios} municípios, ${c.regioes} regiões de saúde e ${c.servicos} CAPS AD, gerados a partir dos indicadores (texto + atributos).</div>
      <div class="passo"><b>2. Interpretação</b>Reconhece municípios, regiões, “Grande São Paulo”, filtros (“sem CAPS AD”, “cidades pequenas”, “alta internação”, “acima de 50 mil”) e a intenção (planejamento, regiões, serviços, encaminhamento).</div>
      <div class="passo"><b>3. Recuperação</b>Índice BM25 sobre os documentos para os termos livres, mais filtros duros dos critérios entendidos. Corrige erros de digitação de uma letra.</div>
      <div class="passo"><b>4. Ranqueamento</b>Planejamento: <b>necessidade</b> = baixo acesso (50%) + alta internação (50%), combinada ao texto. Mostra os pesos de cada resultado.</div>
      <div class="passo"><b>5. Encaminhamento</b>Proximidade ${Math.round(W.proximidade * 100)}%, mesma região de saúde ${Math.round(W.regiao * 100)}%, abertura a moradores de fora ${Math.round(W.abertura * 100)}% (calibrado contra fluxos reais de pacientes).</div>
    </div>
    <h3>Como os filtros são definidos</h3>
    <ul>
      <li><b>Porte:</b> pequeno &lt; 20 mil; médio 20 a 100 mil; grande ≥ 100 mil habitantes.</li>
      <li><b>Acessibilidade e internação “alta” ou “baixa”:</b> terço superior ou inferior do estado.</li>
      <li><b>“Longe”:</b> a mais de 60 km do CAPS AD mais próximo. <b>“Interior”:</b> fora da Grande São Paulo (39 municípios da RMSP).</li>
      <li><b>“Deserto de cuidado”:</b> acessibilidade no quintil inferior <i>e</i> internação ≥ mediana (${meta.n_desertos} municípios, ${meta.pop_desertos.toLocaleString("pt-BR")} habitantes).</li>
    </ul>
    <h3>O que ele não faz</h3>
    <ul><li>Não entende frases arbitrárias nem negações complexas; use as formas mostradas nos exemplos.</li>
    <li>Não usa busca semântica por vetores nesta versão (BM25 + regras).</li>
    <li>“Sem CAPS AD” refere-se a CAPS AD <b>habilitados</b> no CNES; outros CAPS e serviços não entram.</li></ul>`;
  $("#corpo-sobre").innerHTML = `
    <p>Protótipo do Trabalho de Graduação do curso de Ciência de Dados da FATEC Santana de Parnaíba. Compara a <b>demanda hospitalar</b> por transtornos F10–F19 (CID-10) com a <b>oferta de CAPS AD</b> nos ${meta.n_municipios} municípios paulistas.</p>
    <h3>Como ler os números</h3>
    <ul><li><b>Acessibilidade relativa:</b> índice E2SFCA (raio de 60 km), média de 2023–24. <b>1,0 = média estadual</b>.</li>
    <li><b>Taxa de internação:</b> internações F10–F19 por 100 mil habitantes de 15+ por ano (2023–24), suavizada por Bayes empírico.</li>
    <li><b>Distância:</b> em linha reta, do ponto representativo do município ao serviço (CNES, dez/${meta.ano}).</li></ul>
    <h3>Limitações — leia antes de usar</h3>
    <ul>
      <li><b>Internação não é necessidade pura:</b> regiões com hospital psiquiátrico de referência concentram internações (ex.: Espírito Santo do Pinhal).</li>
      <li><b>O índice de acessibilidade tem validação externa fraca</b> (correlação parcial ≈ −0,10) e não prevê melhor do que a simples quantidade de oferta próxima.</li>
      <li><b>O ranqueamento de encaminhamento não supera a simples distância</b> de forma significativa; o que mais pesa é a região de saúde. Veja <i>Avaliação</i>.</li>
      <li>Só entram CAPS AD <b>habilitados</b>. Município sem CAPS AD não significa município sem atendimento: a assistência pode ser regionalizada.</li>
      <li>A tipologia é um agrupamento, não classes naturais (silhueta ≈ 0,28). Os rótulos são interpretação dos autores.</li>
    </ul>
    <h3>Fontes</h3>
    <p>CNES, SIH/SUS, SIM e SIA/SUS (DATASUS, Ministério da Saúde); estimativas de população, Censo 2022 e malha municipal (IBGE). Apenas dados públicos agregados; nenhum dado individual é publicado.</p>
    <p class="nota">Autores: Luís Davi Gomes de Santana, Gabriel Domingues Fernandes e Eloi Pires de Souza Ibiapino Filho. Orientador: Prof. Ivan Souza. Código: github.com/GabsDomin/tg</p>`;
}

let avalCarregada = false;
async function renderAvaliacao() {
  if (avalCarregada) return;
  const el = $("#corpo-aval");
  try {
    const [f, r1, rf] = await Promise.all([J("avaliacao_busca.json"), J("avaliacao_busca_rodada1.json"), J("avaliacao_referencia.json").catch(() => null)]);
    const n3 = (v) => (v == null ? "—" : v.toFixed(3).replace(".", ","));
    const linha = (rot, k) => { const a = r1.por_escopo[k], b = f.por_escopo[k]; if (!b) return ""; const g = (o, s) => (o?.[s] ? o[s].ndcg : null);
      return `<tr><td>${rot} (n=${b.n})</td><td>${n3(g(a, "sistema"))}</td><td class="melhor">${n3(g(b, "sistema"))}</td><td>${n3(g(b, "bm25"))}</td><td>${n3(g(b, "necessidade"))}</td><td>${n3(g(b, "hibrido"))}</td></tr>`; };
    const d = f.diferencas, pt = (x) => (x >= 0 ? "+" : "") + x.toFixed(3).replace(".", ",");
    let h = `<div class="nota"><b>Leia antes:</b> as ${f.n_consultas} consultas foram escritas pelo assistente que construiu o motor, <b>antes de rodá-lo</b>; devem ser substituídas e ampliadas pelo grupo. O gabarito usa dados de 2023–24 e o motor só enxerga 2019–22.</div>
      <h3>1. Motor de busca (planejamento, regiões, serviços e navegação)</h3>
      <div class="kpis"><div class="kpi"><b>${n3(r1.geral.ndcg)}</b><span>NDCG@10 na rodada 1 (estimativa não enviesada)</span></div><div class="kpi"><b>${n3(f.geral.ndcg)}</b><span>NDCG@10 final (otimista: corrigido após a rodada 1)</span></div>
      <div class="kpi"><b>${Math.round(r1.interpretacao.exato * 100)}% → ${Math.round(f.interpretacao.exato * 100)}%</b><span>interpretação exata (rodada 1 → final)</span></div></div>
      <div class="tab-wrap"><table><thead><tr><th>NDCG@10</th><th>Motor (rodada 1)</th><th>Motor (final)</th><th>BM25 puro</th><th>Só necessidade</th><th>BM25+necess. (sem interpretar)</th></tr></thead><tbody>
      ${linha("Planejamento (municípios)", "planejamento (municípios)")}${linha("Regiões", "regiões")}${linha("Serviços", "serviços")}${linha("Navegacional", "navegacional")}</tbody></table></div>
      <p>Diferença de NDCG@10 do motor final contra: BM25 puro <b>${pt(d.bm25.dif)}</b> [${pt(d.bm25.lo)}; ${pt(d.bm25.hi)}] · só necessidade <b>${pt(d.necessidade.dif)}</b> · BM25 + necessidade sem interpretação <b>${pt(d.hibrido.dif)}</b> (IC 95%, bootstrap pareado).</p>
      <p>As falhas restantes são de <b>mudança temporal</b>: o que era “baixa acessibilidade” em 2019–22 nem sempre é o mesmo em 2023–24.</p>`;
    if (rf) {
      const t = rf.tabela, dif = rf.diffs, sis = t.find((x) => x.metodo.startsWith("SISTEMA (")), dist = t.find((x) => x.metodo === "so distancia");
      h += `<h3>2. Encaminhamento (referência)</h3><p>${rf.n_consultas} municípios sem CAPS AD, comparados aos <b>fluxos reais de pacientes de 2023–24</b> (atributos só de ≤ 2022).</p>
        <div class="tab-wrap"><table><thead><tr><th>Método (n=${rf.n_teste} de teste)</th><th>NDCG@5</th><th>MRR</th><th>P@5</th></tr></thead><tbody>${t.map((x) => `<tr><td>${esc(x.metodo)}</td><td>${n3(x["NDCG@5"])}</td><td>${n3(x.MRR)}</td><td>${n3(x["P@5"])}</td></tr>`).join("")}</tbody></table></div>
        <p>O sistema (${n3(sis["NDCG@5"])}) <b>não supera “só distância”</b> (${n3(dist["NDCG@5"])}): diferença ${pt(dif["SISTEMA (pesos calibrados)"][0])} [${pt(dif["SISTEMA (pesos calibrados)"][1])}; ${pt(dif["SISTEMA (pesos calibrados)"][2])}], que inclui zero. A <b>folga</b> do serviço recebeu peso zero; o que mais pesa é a <b>região de saúde</b>.</p>`;
    }
    h += `<h3>Limitações da avaliação</h3><ul><li>Consultas não escritas por usuários reais nem julgadas por especialista da RAPS.</li><li>Fluxos observados mostram para onde as pessoas foram, não necessariamente para onde deveriam ir.</li><li>Amostras pequenas: intervalos largos.</li></ul>`;
    el.innerHTML = h; avalCarregada = true;
  } catch (e) { el.innerHTML = `<p>Não foi possível carregar a avaliação (${esc(e.message)}).</p>`; }
}
