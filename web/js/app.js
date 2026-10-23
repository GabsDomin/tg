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

/* ---------------- painéis (Como funciona / Avaliação / Sobre) ---------------- */
let modalAberto = null, focoAnterior = null;
function abrirModal(id) {
  fecharModal();
  const d = $("#" + id); if (!d) return;
  if (id === "dlg-aval") renderAvaliacao();
  focoAnterior = document.activeElement; d.hidden = false; modalAberto = d;
  document.body.classList.add("sem-rolagem");
  d.querySelector(".modal-caixa").scrollTop = 0;
  d.querySelector("[data-fecha]").focus();
}
function fecharModal() {
  if (!modalAberto) return;
  modalAberto.hidden = true; modalAberto = null;
  document.body.classList.remove("sem-rolagem");
  focoAnterior?.focus?.();
}
document.querySelectorAll("[data-abre]").forEach((b) => b.addEventListener("click", () => abrirModal(b.dataset.abre)));
document.querySelectorAll(".modal").forEach((d) => {
  d.addEventListener("click", (e) => { if (e.target === d) fecharModal(); });
  d.querySelector("[data-fecha]").addEventListener("click", fecharModal);
});
document.addEventListener("keydown", (e) => {
  if (!modalAberto) return;
  if (e.key === "Escape") { fecharModal(); return; }
  if (e.key === "Tab") {                                   // mantem o foco dentro do painel
    const f = [...modalAberto.querySelectorAll("button, a[href], summary, input, select")].filter((x) => x.offsetParent !== null);
    if (!f.length) return;
    const i = f.indexOf(document.activeElement);
    if (e.shiftKey && i <= 0) { e.preventDefault(); f[f.length - 1].focus(); }
    else if (!e.shiftKey && i === f.length - 1) { e.preventDefault(); f[0].focus(); }
  }
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
const CAMADAS = {
  a: { rot: "Acesso a CAPS AD (1 = média do estado)", ruim: "baixo", d: 2, nota: "Tons escuros = acesso menor",
    desc: "Mostra se o município e seus vizinhos têm CAPS AD suficientes para a demanda. 1,0 é a média do estado; tons escuros = acesso menor." },
  t: { rot: "Internações por álcool e drogas (por 100 mil hab./ano)", ruim: "alto", d: 0, nota: "Tons escuros = mais internações",
    desc: "Internações no SUS por transtornos de álcool e outras drogas (2023–24). Atenção: valores altos podem refletir um hospital psiquiátrico na região, não só necessidade." },
  d: { rot: "Distância até o CAPS AD mais próximo (km)", ruim: "alto", d: 0, nota: "Tons escuros = mais longe",
    desc: "Distância em linha reta até o CAPS AD habilitado mais próximo." },
  g: { desc: "Agrupa municípios parecidos em acesso, distância, internações e atendimento em CAPS. É uma classificação nossa, não oficial, e os grupos se misturam." },
};

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
    legenda(`<b>Perfil do município (5 grupos)</b><br>${[1, 2, 3, 4, 5].map((g) => `<i style="background:${CATEG[g]}"></i>${esc(meta.clusters[g])} (${M.filter((x) => x.g === g).length})`).join("<br>")}<br><span style="color:var(--muted)">Classificação nossa; os nomes são interpretação dos autores.</span>`);
  } else {
    const vals = M.map((x) => x[k]).filter((v) => v != null && !Number.isNaN(v)).sort((a, b) => a - b);
    const cortes = [1, 2, 3, 4].map((i) => vals[Math.floor(i * vals.length / 5)]);
    const ruimBaixo = CAMADAS[k].ruim === "baixo";
    const cor = (v) => { if (v == null || Number.isNaN(v)) return "#bbb"; let i = cortes.filter((c) => v >= c).length; if (ruimBaixo) i = 4 - i; return RAMPA[i]; };
    M.forEach((x) => cores.set(x.c, cor(x[k])));
    const lim = [vals[0], ...cortes, vals[vals.length - 1]];
    let h = `<b>${CAMADAS[k].rot}</b><br>`;
    for (let i = 0; i < 5; i++) { const idx = ruimBaixo ? 4 - i : i; h += `<i style="background:${RAMPA[idx]}"></i>${fmt(lim[i], CAMADAS[k].d)} – ${fmt(lim[i + 1], CAMADAS[k].d)}<br>`; }
    const ordem = ruimBaixo ? [4, 3, 2, 1, 0] : [0, 1, 2, 3, 4];           // do menor ao maior valor
    const extremos = { a: ["menos acesso", "mais acesso"], t: ["menos internações", "mais internações"], d: ["mais perto", "mais longe"] }[k];
    const titulo = { a: "Acesso a CAPS AD", t: "Internações por álcool e drogas", d: "Distância até o CAPS AD" }[k];
    const mini = `<b>${titulo}</b><div class="cores">${ordem.map((i) => `<i style="background:${RAMPA[i]}"></i>`).join("")}</div><div class="extremos"><span>${extremos[0]}</span><span>${extremos[1]}</span></div>`;
    legenda(h + `<span style="color:var(--muted)">${CAMADAS[k].nota} (cinco faixas de tamanho igual)</span>`, mini);
  }
  $("#camada-desc").textContent = CAMADAS[k].desc;
  munLayers.forEach((l, c) => l.setStyle({ fillColor: cores.get(c) }));
}
/** `mini`: versao compacta (barra de cores) usada no celular; sem `mini`, a legenda completa aparece sempre */
function legenda(html, mini) {
  if (map._leg) map.removeControl(map._leg);
  const leg = L.control({ position: "bottomleft" });
  leg.onAdd = () => {
    const d = L.DomUtil.create("div", mini ? "legenda" : "legenda sempre");
    d.innerHTML = mini ? `<div class="leg-full">${html}</div><div class="leg-mini">${mini}</div>` : html;
    return d;
  };
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
  document.addEventListener("keydown", (e) => { if (e.key === "/" && !/input|textarea|select/i.test(document.activeElement.tagName) && !modalAberto) { e.preventDefault(); q.focus(); q.select(); } });
  document.addEventListener("click", (e) => { const a = e.target.closest("[data-q]"); if (a) { e.preventDefault(); fecharModal(); $("#q").value = a.dataset.q; executar(a.dataset.q, { rolar: true }); } });
  $("#camada-info").addEventListener("click", () => { const d = $("#camada-desc"), a = d.classList.toggle("aberto"); $("#camada-info").setAttribute("aria-expanded", a); });
  $("#exemplos").innerHTML = `<p class="rotulo-chips">Experimente</p><div class="chips">${motor.exemplos.slice(0, 4).map((e) => `<button type="button" class="chip ex" data-q="${esc(e)}">${esc(e)}</button>`).join("")}</div>`;
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
    ${x.motivo ? `<p class="motivo"><b>Por que aparece:</b> ${esc(x.motivo)}</p>` : ""}
    ${x.selo ? `<span class="selo">${esc(x.selo)}</span>` : ""}
    <ul class="fatos">${(x.fatos || []).map((f) => `<li>${esc(f)}</li>`).join("")}</ul>
    ${comp ? `<details class="porque"><summary>Ver como a posição foi calculada</summary>${comp}</details>` : ""}
  </article>`;
}

function renderResultados(r) {
  const el = $("#resultados"), it = r.interpretacao;
  let h = `<div class="res-cab"><span class="n">${r.total} resultado${r.total === 1 ? "" : "s"}</span><button class="voltar" type="button" id="voltar">← Territórios prioritários</button><button class="btn" type="button" id="copiar">Copiar link</button></div>`;
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
  $("#voltar")?.addEventListener("click", voltarAsPrioridades);
  $("#mais")?.addEventListener("click", () => { mostrando += 20; renderResultados(ultimo.r); });
  el.querySelector("[data-abre-aval]")?.addEventListener("click", (e) => { e.preventDefault(); abrirModal("dlg-aval"); });
  ligarCartoes(el, (i) => (i >= 1000 ? r.extras.referencia[i - 1000] : r.resultados[i]));
}

function ligarCartoes(el, itemDe) {
  el.querySelectorAll(".cartao").forEach((c) => {
    const go = () => selecionar(itemDe(Number(c.dataset.i)), c);
    c.addEventListener("click", (e) => { if (!e.target.closest("details")) go(); });
    c.addEventListener("keydown", (e) => { if ((e.key === "Enter" || e.key === " ") && !e.target.closest("details")) { e.preventDefault(); go(); } });
  });
}
function voltarAsPrioridades() { $("#q").value = ""; $("#limpar").hidden = true; ignorar = new Set(); boasVindas(); atualizaUrl(); $("#resultados").scrollTo({ top: 0 }); }

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

/* ---------------- tela inicial: territórios prioritários ---------------- */
let lente = "necessidade";
function boasVindas() {
  ultimo = null; selecionado = null;
  $("#interp").innerHTML = ""; $("#exemplos").hidden = false;
  renderPrioridades();
}
function renderPrioridades() {
  const L = motor.lentes[lente], cards = motor.prioridades(lente, 8);
  const sem = M.filter((m) => m.k === 0), popSem = sem.reduce((a, m) => a + m.p, 0), popTot = M.reduce((a, m) => a + m.p, 0);
  $("#resultados").innerHTML = `<div class="boas">
    <h2 class="tit">Onde falta cuidado em álcool e outras drogas?</h2>
    <p class="intro">Nos ${meta.n_municipios} municípios de São Paulo: onde há <b>CAPS AD</b> (serviço público de saúde para álcool e outras drogas), onde faltam e para onde encaminhar.</p>
    <ul class="stats"><li><b>${sem.length}</b> municípios sem CAPS AD (${Math.round(sem.length / M.length * 100)}%)</li><li><b>${fmt(popSem / popTot * 100, 0)}%</b> da população mora neles</li><li><b>${meta.n_desertos}</b> em “deserto de cuidado”</li></ul>
    <h3 class="prio-tit">Territórios prioritários</h3>
    <p style="margin:2px 0 6px">${esc(L.desc)}</p>
    <div class="lentes" role="group" aria-label="Critério de prioridade">${Object.entries(motor.lentes).map(([id, l]) => `<button type="button" class="lente" data-lente="${id}" aria-pressed="${id === lente}">${esc(l.rot)}</button>`).join("")}</div>
    <div id="lista-prio">${cards.map((x, i) => cartao(x, i)).join("")}</div>
    <button class="mais" type="button" data-q="${esc(L.consulta)}">Ver a lista completa</button>
    <p class="nota"><b>Leia com cuidado:</b> são estimativas a partir de dados públicos. Municípios com muitas internações podem refletir um hospital psiquiátrico na região (ex.: Espírito Santo do Pinhal), e não só necessidade. Confirme com a gestão regional.</p></div>`;
  document.querySelectorAll(".lente").forEach((b) => b.addEventListener("click", () => { lente = b.dataset.lente; renderPrioridades(); }));
  ligarCartoes($("#lista-prio"), (i) => cards[i]);
  const muns = [];
  cards.forEach((x) => { if (x.tipo === "municipio") muns.push(x.id); else if (x.tipo === "regiao") M.filter((m) => m.ri === x.id).forEach((m) => muns.push(m.c)); });
  destacar({ muns, ajustar: false });
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

/* ---------------- painéis: conteúdo (linguagem simples) ---------------- */
function conteudoDialogos() {
  const W = meta.pesos_referencia, c = motor.corpus;
  const ex = (q, o) => `<button type="button" class="exemplo-btn" data-q="${esc(q)}">“${esc(q)}”<small>${esc(o)}</small></button>`;
  $("#corpo-como").innerHTML = `
    <p class="lead">Este site ajuda a ver <b>onde falta cuidado em álcool e outras drogas</b> no estado de São Paulo. Há três formas de explorar:</p>

    <h3>1. Veja os territórios prioritários</h3>
    <p>Na tela inicial listamos os municípios e as regiões onde um CAPS AD faria mais falta. Você escolhe o critério: <b>maior necessidade</b>, <b>mais pessoas afetadas</b> ou <b>regiões de saúde</b>. Cada cartão diz “por que aparece”.</p>

    <h3>2. Pergunte com suas palavras</h3>
    <p>Digite na caixa de busca, como numa conversa. Toque em um exemplo para testar:</p>
    ${ex("municípios sem CAPS AD na região de Assis", "lista os municípios daquela região que não têm CAPS AD")}
    ${ex("cidades pequenas com alta internação e sem serviço", "combina vários critérios numa só frase")}
    ${ex("para onde encaminhar paciente de Registro", "sugere os CAPS AD mais indicados para esse município")}
    ${ex("CAPS AD III em Campinas", "mostra os serviços desse tipo naquela cidade")}
    ${ex("regiões com maior taxa de internação", "compara as regiões de saúde")}

    <h3>3. Clique no mapa</h3>
    <p>Clicar em um município mostra o perfil dele e para onde encaminhar. No quadro do mapa você escolhe <b>o que mostrar</b>: acesso a CAPS AD, internações, distância ou o perfil do município.</p>

    <h3>Como ler cada resultado</h3>
    <ul>
      <li><b>“Como entendi”</b>: as etiquetas logo abaixo da busca mostram como interpretamos sua frase. Toque no <b>×</b> de uma etiqueta para tirar aquele critério.</li>
      <li><b>“Por que aparece”</b>: a razão em uma linha (por exemplo, “sem CAPS AD habilitado · 74 km do mais próximo”).</li>
      <li><b>“Ver como a posição foi calculada”</b>: barras com o peso de cada fator.</li>
    </ul>

    <h3>O que as palavras significam</h3>
    <dl>
      <dt>CAPS AD</dt><dd>Centro de Atenção Psicossocial Álcool e Drogas: serviço público de saúde especializado. Aqui contamos só os <b>habilitados</b> no cadastro nacional (CNES).</dd>
      <dt>Acesso a CAPS AD</dt><dd>Quanto o município e seus vizinhos têm de CAPS AD em relação à demanda. <b>1,0 é a média do estado</b>; abaixo disso, o acesso é menor.</dd>
      <dt>Internações por álcool e drogas</dt><dd>Internações no SUS por transtornos causados por álcool e outras drogas, por 100 mil habitantes de 15 anos ou mais por ano.</dd>
      <dt>Necessidade</dt><dd>Nossa nota de prioridade: junta <b>acesso baixo a CAPS AD</b> (50%) e <b>muitas internações</b> (50%).</dd>
      <dt>Deserto de cuidado</dt><dd>Município com acesso muito baixo a CAPS AD <i>e</i> internações acima da mediana. São ${meta.n_desertos} municípios, com ${meta.pop_desertos.toLocaleString("pt-BR")} habitantes.</dd>
      <dt>Para onde encaminhar</dt><dd>Lista de CAPS AD até 150 km, ordenada por proximidade (${Math.round(W.proximidade * 100)}%), pertencer à mesma região de saúde (${Math.round(W.regiao * 100)}%) e abertura a moradores de outros municípios (${Math.round(W.abertura * 100)}%). <b>Não garante vaga</b>: contate o serviço antes.</dd>
    </dl>

    <h3>Filtros que a busca entende</h3>
    <ul>
      <li><b>Tamanho:</b> “pequenas” (menos de 20 mil habitantes), “médias” (20 a 100 mil), “grandes” (100 mil ou mais), ou números (“acima de 50 mil”).</li>
      <li><b>Acesso e internações “alto” ou “baixo”:</b> terço superior ou inferior do estado.</li>
      <li><b>“Longe”:</b> a mais de 60 km do CAPS AD mais próximo. <b>“Interior”:</b> fora da Grande São Paulo.</li>
    </ul>

    <h3>O que o site não faz</h3>
    <ul><li>Não entende qualquer frase: use as formas dos exemplos.</li><li>Não é triagem clínica e não substitui avaliação profissional. Em crise: CVV 188 ou SAMU 192.</li><li>“Sem CAPS AD” significa sem CAPS AD <b>habilitado</b>; outros serviços não entram na conta.</li></ul>

    <details><summary>Detalhes técnicos (para quem quiser)</summary>
      <p>É um motor de busca sobre ${c.documentos} documentos de texto gerados dos dados (${c.municipios} municípios, ${c.regioes} regiões e ${c.servicos} CAPS AD). Ele (1) lê a frase e reconhece lugares, filtros e intenção; (2) busca por palavras com o método BM25; (3) aplica os filtros e (4) ordena pela nota de necessidade, mostrando o peso de cada fator. Não usa inteligência artificial generativa. As etapas e os testes estão descritos no repositório do projeto.</p>
    </details>`;

  $("#corpo-sobre").innerHTML = `
    <p class="lead">Protótipo de um Trabalho de Graduação do curso de Ciência de Dados da FATEC Santana de Parnaíba. Ele compara a <b>demanda por cuidado</b> em álcool e outras drogas com a <b>oferta de CAPS AD</b> nos ${meta.n_municipios} municípios paulistas.</p>
    <h3>Para que serve</h3>
    <p>Apoiar conversas e decisões de <b>planejamento</b>: onde um CAPS AD faria mais falta e para onde encaminhar. <b>Não</b> é uma ferramenta para decidir o cuidado de uma pessoa.</p>
    <h3>De onde vêm os dados</h3>
    <ul>
      <li><b>CAPS AD:</b> Cadastro Nacional de Estabelecimentos de Saúde (CNES), dezembro de ${meta.ano}.</li>
      <li><b>Internações e óbitos:</b> SIH/SUS e SIM (DATASUS, Ministério da Saúde), 2019–2024.</li>
      <li><b>População, Censo e mapa:</b> IBGE.</li>
    </ul>
    <p>Usamos apenas dados públicos agregados; nenhum dado de pessoa é publicado.</p>
    <h3>Limites importantes</h3>
    <ul>
      <li><b>Internação não é só necessidade.</b> Regiões com hospital psiquiátrico grande têm muitas internações (ex.: Espírito Santo do Pinhal), o que pode aumentar a nota de vizinhos.</li>
      <li><b>O índice de acesso é uma estimativa.</b> Em nossos testes ele só se associa fracamente a internações futuras.</li>
      <li><b>O “para onde encaminhar” não é melhor que indicar o CAPS mais próximo</b> (veja <i>Avaliação</i>).</li>
      <li>Município sem CAPS AD não é município sem atendimento: o cuidado pode ser feito em cidades vizinhas ou em outros tipos de CAPS.</li>
      <li>Os 5 “perfis de município” são uma classificação nossa; os grupos se misturam.</li>
    </ul>
    <h3>Quem fez</h3>
    <p>Luís Davi Gomes de Santana, Gabriel Domingues Fernandes e Eloi Pires de Souza Ibiapino Filho. Orientador: Prof. Ivan Souza.</p>
    <p class="nota">Versão preliminar. Código aberto: github.com/GabsDomin/tg</p>`;
}

let avalCarregada = false;
async function renderAvaliacao() {
  if (avalCarregada) return;
  const el = $("#corpo-aval");
  try {
    const [f, r1, rf] = await Promise.all([J("avaliacao_busca.json"), J("avaliacao_busca_rodada1.json"), J("avaliacao_referencia.json").catch(() => null)]);
    const n2 = (v) => v.toFixed(2).replace(".", ",");
    const barra = (rot, v, nosso) => `<div class="vbar${nosso ? " nosso" : ""}"><span>${esc(rot)}</span><span class="fundo"><i style="width:${Math.round(Math.max(0, Math.min(1, v)) * 100)}%"></i></span><span class="v">${n2(v)}</span></div>`;
    const gb = f.geral_baselines, nossa = r1.geral.ndcg;
    let h = `<p class="lead">Antes de usar um resultado, vale saber <b>o quanto ele merece confiança</b>. Testamos a busca e a sugestão de encaminhamento comparando com o que realmente aconteceu em 2023–2024.</p>

      <div class="veredito"><span class="sel-v bom">✔ Funciona bem</span>
        <h4>1. A busca entende o que você pergunta?</h4>
        <p>Sim, na maior parte. Fizemos ${f.n_consultas} perguntas de teste e conferimos se os resultados certos apareciam no topo da lista. A nota vai de 0 a 1: <b>quanto mais perto de 1, melhor</b>.</p>
        ${barra("Nossa busca", nossa, true)}${barra("Busca comum por palavras", gb.bm25.ndcg)}${barra("Palavras + nota de necessidade, sem entender a pergunta", gb.hibrido.ndcg)}${barra("Só ordenar por necessidade (ignora a pergunta)", gb.necessidade.ndcg)}
        <p>Interpretou corretamente o que foi pedido em <b>${Math.round(r1.interpretacao.exato * 100)}%</b> das perguntas.</p>
        <p class="nota">Depois de corrigirmos as falhas que o teste mostrou, a nota subiu para ${n2(f.geral.ndcg)}. Esse número é <b>otimista</b>, porque usamos as mesmas perguntas para corrigir; por isso mostramos ${n2(nossa)}. Além disso, as perguntas foram escritas por quem fez a busca, não por usuários: o grupo vai substituí-las.</p>
      </div>`;
    if (rf) {
      const t = rf.tabela, g = (nome) => t.find((x) => x.metodo === nome)["NDCG@5"];
      const sis = g("SISTEMA (pesos calibrados)"), dist = g("so distancia"), hist = g("persistencia (fluxo 2019-22)");
      const d = rf.diffs["SISTEMA (pesos calibrados)"];
      h += `<div class="veredito"><span class="sel-v atencao">⚠ Use com cautela</span>
        <h4>2. A sugestão de “para onde encaminhar” acerta?</h4>
        <p>Só em parte. Comparamos a lista sugerida com <b>para onde pacientes de ${rf.n_consultas} municípios realmente foram atendidos</b>. A sugestão ficou praticamente igual a simplesmente indicar o CAPS mais próximo.</p>
        ${barra("Nossa sugestão", sis, true)}${barra("Só o CAPS mais próximo", dist)}${barra("Repetir para onde o município já encaminhava", hist)}
        <p>A diferença entre a nossa sugestão e “o mais próximo” (${d[0] >= 0 ? "+" : ""}${n2(d[0])}) é <b>pequena demais para afastar o acaso</b>. O que mais pesa é o serviço <b>estar na mesma região de saúde</b>. Testamos também a “folga” do serviço (se está sobrecarregado), mas ela não ajudou e foi retirada do cálculo.</p>
        <p class="nota">O histórico do próprio município é o melhor guia (${n2(hist)}), mas ele não é publicado aqui, por privacidade.</p>
      </div>`;
    }
    h += `<div class="veredito"><span class="sel-v atencao">⚠ São estimativas</span>
        <h4>3. E os números do mapa?</h4>
        <ul><li><b>Internações</b> refletem também onde ficam os hospitais psiquiátricos, não só a necessidade.</li>
        <li><b>Acesso a CAPS AD</b> é um índice nosso; em testes, ele só se associa fracamente a internações futuras.</li>
        <li>Só contamos CAPS AD <b>habilitados</b>; outros serviços ficam de fora.</li></ul>
      </div>
      <h3>O que isso significa para você</h3>
      <p>Use o site como <b>ponto de partida</b> para conversar e planejar. Confirme as sugestões com a gestão regional e com quem conhece o território.</p>

      <details><summary>Como testamos (para quem quiser os detalhes)</summary>
        <p>O motor só enxergava dados de 2019–2022; o “gabarito” usou 2023–2024. A nota é o <b>NDCG@10</b> (busca) e o <b>NDCG@5</b> (encaminhamento): medem se os resultados corretos aparecem no topo da lista, de 0 a 1. Comparamos com métodos simples (busca por palavras, ordenar por necessidade, só distância) e calculamos intervalos de confiança por reamostragem. Resultados completos e limitações nos arquivos <i>docs/resultados_busca.md</i> e <i>docs/resultados_avaliacao.md</i> do repositório.</p>
        <p>Diferença da nossa busca para a busca comum: +${n2(f.diferencas.bm25.dif)} (intervalo de 95%: ${n2(f.diferencas.bm25.lo)} a ${n2(f.diferencas.bm25.hi)}).</p>
      </details>`;
    el.innerHTML = h; avalCarregada = true;
  } catch (e) { el.innerHTML = `<p>Não foi possível carregar a avaliação (${esc(e.message)}).</p>`; }
}
