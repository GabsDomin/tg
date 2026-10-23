// Teste de ponta a ponta do site com o Edge (headless) via DevTools Protocol. Sem dependencias.
// Uso: node scripts/busca/e2e.mjs <url-base> <pasta-saida> [roteiro]   (roteiro: mobile | desktop | tudo)
// Emula dispositivo de verdade (390x844, toque, escala 2), interage com a pagina e salva capturas.
import { spawn } from "node:child_process";
import { mkdirSync, writeFileSync } from "node:fs";
import { join } from "node:path";
import { tmpdir } from "node:os";

const BASE = process.argv[2] || "http://localhost:8766/";
const SAIDA = process.argv[3] || ".";
const ROTEIRO = process.argv[4] || "tudo";
mkdirSync(SAIDA, { recursive: true });
const EDGE = "C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe";
const PORTA = 9333 + Math.floor(Math.random() * 300);
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

const proc = spawn(EDGE, ["--headless=new", "--disable-gpu", `--remote-debugging-port=${PORTA}`, `--user-data-dir=${join(tmpdir(), "e2e-" + PORTA)}`, "--hide-scrollbars", "about:blank"], { stdio: "ignore" });
let ws, id = 0; const pend = new Map();
async function conectar() {
  for (let i = 0; i < 60; i++) {
    try {
      const abas = await (await fetch(`http://127.0.0.1:${PORTA}/json`)).json();
      const pg = abas.find((a) => a.type === "page");
      if (pg) { ws = new WebSocket(pg.webSocketDebuggerUrl); await new Promise((ok, er) => { ws.onopen = ok; ws.onerror = er; }); break; }
    } catch { /* ainda subindo */ }
    await sleep(250);
  }
  ws.onmessage = (m) => { const d = JSON.parse(m.data); if (d.id && pend.has(d.id)) { pend.get(d.id)(d); pend.delete(d.id); } };
}
const cmd = (method, params = {}) => new Promise((ok) => { const i = ++id; pend.set(i, ok); ws.send(JSON.stringify({ id: i, method, params })); });
const avaliar = async (expr) => { const r = await cmd("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true }); if (r.result?.exceptionDetails) throw new Error(JSON.stringify(r.result.exceptionDetails.exception?.description || r.result.exceptionDetails)); return r.result?.result?.value; };
async function esperar(expr, ms = 20000) { const t0 = Date.now(); while (Date.now() - t0 < ms) { try { if (await avaliar(expr)) return true; } catch { /* pagina navegando */ } await sleep(200); } return false; }
async function captura(nome, completa = false) {
  const p = { format: "png" };
  if (completa) { const h = await avaliar("Math.max(document.documentElement.scrollHeight, innerHeight)"); p.captureBeyondViewport = true; p.clip = { x: 0, y: 0, width: await avaliar("innerWidth"), height: Math.min(h, 6000), scale: 1 }; }
  const r = await cmd("Page.captureScreenshot", p);
  writeFileSync(join(SAIDA, nome), Buffer.from(r.result.data, "base64"));
}
async function abrir(url, { w, h, mobile, escuro }) {
  await cmd("Emulation.setDeviceMetricsOverride", { width: w, height: h, deviceScaleFactor: mobile ? 2 : 1, mobile: !!mobile });
  if (mobile) await cmd("Emulation.setTouchEmulationEnabled", { enabled: true });
  await cmd("Page.navigate", { url: url + (escuro ? (url.includes("?") ? "&" : "?") + "tema=escuro" : "") });
  await sleep(500);
  return esperar("!!document.querySelector('.boas, .cartao, .vazio')", 25000);
}
const relatorio = [];
const ok = (nome, cond, extra = "") => { relatorio.push([cond ? "OK " : "FALHA", nome, extra]); console.log(`${cond ? "OK   " : "FALHA"} ${nome}${extra ? " — " + extra : ""}`); };
const erros = () => avaliar("document.documentElement.getAttribute('data-erros') || ''");
const digitar = async (q) => avaliar(`(()=>{const i=document.querySelector('#q');i.value=${JSON.stringify(q)};document.querySelector('#form').requestSubmit();return true})()`);

const aberto = (alvo) => `(()=>{const d=document.getElementById('${alvo}'); const cs=getComputedStyle(d); return !d.hidden && cs.display!=='none' && cs.visibility!=='hidden'})()`;
const JARGAO = /NDCG|BM25|K-Means|silhueta|E2SFCA|recuperação de informação/i;

/** abre cada painel (Como funciona / Avaliação / Sobre): conteudo visivel, sem jargao no inicio, e fecha por botao, Esc e clique fora */
async function checarPaineis(pref) {
  for (const [rot, alvo, deve] of [["Como funciona", "dlg-como", /territórios prioritários/i], ["Avaliação", "dlg-aval", /dá para confiar|merece confiança/i], ["Sobre", "dlg-sobre", /Para que serve/i]]) {
    await avaliar(`document.querySelector('[data-abre="${alvo}"]').click(); true`);
    await sleep(800);
    const est = await avaliar(`(()=>{const d=document.getElementById('${alvo}'); const r=d.querySelector('.modal-caixa').getBoundingClientRect();
      const t=(d.innerText||'').trim(); return {aberto:${aberto(alvo)}, txt:t.length, h:Math.round(r.height), w:Math.round(r.width), ini:t.slice(0,600), foco: document.activeElement && document.activeElement.hasAttribute('data-fecha')}})()`);
    ok(`${pref}: "${rot}" abre e mostra conteúdo`, est.aberto && est.txt > 400 && est.h > 150, `${est.w}x${est.h}px, ${est.txt} caracteres`);
    ok(`${pref}: "${rot}" explica em linguagem simples`, deve.test(est.ini) && !JARGAO.test(est.ini), est.ini.slice(0, 70).replace(/\n/g, " "));
    ok(`${pref}: "${rot}" leva o foco para o botão Fechar`, est.foco);
    await captura(`${pref}_painel_${alvo}.png`);
    await avaliar(`document.querySelector('#${alvo} [data-fecha]').click(); true`); await sleep(250);
    ok(`${pref}: "${rot}" fecha pelo botão`, !(await avaliar(aberto(alvo))));
    await avaliar(`document.querySelector('[data-abre="${alvo}"]').click(); true`); await sleep(250);
    await avaliar(`document.dispatchEvent(new KeyboardEvent('keydown',{key:'Escape'})); true`); await sleep(250);
    ok(`${pref}: "${rot}" fecha com Esc`, !(await avaliar(aberto(alvo))));
    await avaliar(`document.querySelector('[data-abre="${alvo}"]').click(); true`); await sleep(250);
    await avaliar(`document.getElementById('${alvo}').click(); true`); await sleep(250);
    ok(`${pref}: "${rot}" fecha ao clicar fora`, !(await avaliar(aberto(alvo))));
  }
  ok(`${pref}: a rolagem da página volta ao fechar`, !(await avaliar("document.body.classList.contains('sem-rolagem')")));
}

/** a tela inicial recomenda territorios (3 criterios) e o mapa tem nomes claros */
async function checarInicio(pref) {
  const n = await avaliar("document.querySelectorAll('#lista-prio .cartao').length");
  ok(`${pref}: tela inicial lista territórios prioritários`, n === 8, `${n} cartões`);
  ok(`${pref}: cada território diz “por que aparece”`, await avaliar("[...document.querySelectorAll('#lista-prio .cartao')].every(c=>/Por que aparece/.test(c.innerText))"));
  ok(`${pref}: três critérios de prioridade`, await avaliar("document.querySelectorAll('.lente').length === 3"));
  const antes = await avaliar("document.querySelector('#lista-prio .cartao h3').innerText");
  await avaliar("document.querySelectorAll('.lente')[1].click(); true"); await sleep(300);
  const depois = await avaliar("document.querySelector('#lista-prio .cartao h3').innerText");
  ok(`${pref}: trocar o critério muda a lista`, antes !== depois, `${antes.replace(/\n/g, " ")} → ${depois.replace(/\n/g, " ")}`);
  await avaliar("document.querySelectorAll('.lente')[2].click(); true"); await sleep(300);
  ok(`${pref}: critério “regiões” recomenda regiões`, await avaliar("document.querySelectorAll('#lista-prio .badge.regiao').length === 8"));
  await avaliar("document.querySelectorAll('.lente')[0].click(); true"); await sleep(200);
  const ops = await avaliar("[...document.querySelectorAll('#camada option')].map(o=>o.textContent)");
  ok(`${pref}: nomes das camadas do mapa são claros`, ops.length === 4 && !ops.some((o) => /K-Means|Tipologia|Acessibilidade/.test(o)) && ops.every((o) => o.length > 12), ops.join(" | "));
  ok(`${pref}: o mapa explica o que está mostrando`, (await avaliar("document.querySelector('#camada-desc').textContent")).length > 60);
}

async function roteiroMobile() {
  console.log("\n--- MOBILE 390x844 (toque, escala 2) ---");
  const carregou = await abrir(BASE, { w: 390, h: 844, mobile: true });
  ok("mobile: página carrega (boas-vindas)", carregou);
  ok("mobile: sem erros de JS", (await erros()) === "", await erros());
  await checarInicio("mobile");
  const sw = await avaliar("document.documentElement.scrollWidth"), iw = await avaliar("innerWidth");
  ok("mobile: sem rolagem horizontal", sw <= iw + 1, `scrollWidth=${sw} innerWidth=${iw}`);
  const alt = await avaliar("Math.round(document.querySelector('#map').getBoundingClientRect().height)");
  ok("mobile: mapa visível com altura útil", alt >= 250, `${alt}px`);
  const tam = await avaliar("Math.min(...[...document.querySelectorAll('button, .btn, select, input')].filter(e=>e.offsetParent).map(e=>e.getBoundingClientRect().height))");
  ok("mobile: alvos de toque >= 24px (WCAG 2.2 AA)", tam >= 24, `menor: ${Math.round(tam)}px`);
  await captura("m_01_inicio.png");
  await digitar("para onde encaminhar paciente de Registro");
  ok("mobile: busca de encaminhamento mostra cartões", await esperar("document.querySelectorAll('.cartao').length >= 3"));
  ok("mobile: chips de interpretação", await avaliar("document.querySelectorAll('#interp .chip').length >= 2"));
  await captura("m_02_busca.png");
  await avaliar("document.querySelector('#resultados').scrollIntoView(); true"); await sleep(400);
  await captura("m_03_resultados.png");
  await checarPaineis("mobile");
  ok("mobile: sem erros de JS ao final", (await erros()) === "", await erros());
}

async function roteiroDesktop() {
  console.log("\n--- DESKTOP 1400x860 ---");
  const carregou = await abrir(BASE, { w: 1400, h: 860, mobile: false });
  ok("desktop: página carrega", carregou);
  await checarInicio("desktop");
  await captura("d_01_inicio.png");
  await digitar("cidades pequenas com alta internação e sem serviço");
  ok("desktop: busca de planejamento", await esperar("document.querySelectorAll('.cartao').length >= 5"));
  ok("desktop: interpretação com 3 filtros", await avaliar("document.querySelectorAll('#interp .chip button').length === 3"));
  await captura("d_02_planejamento.png");
  await avaliar("document.querySelector('#interp .chip button').click(); true"); await sleep(500);
  ok("desktop: remover chip refaz a busca", await avaliar("document.querySelectorAll('#interp .chip button').length === 2"));
  await avaliar("document.querySelector('#voltar').click(); true"); await sleep(400);
  ok("desktop: botão volta aos territórios prioritários", await avaliar("document.querySelectorAll('#lista-prio .cartao').length === 8 && document.querySelector('#q').value === ''"));
  await digitar("cidades pequenas com alta internação e sem serviço"); await esperar("document.querySelectorAll('.cartao').length >= 5");
  await avaliar("document.querySelector('.cartao details summary').click(); true"); await sleep(200);
  await avaliar("document.querySelector('.cartao').click(); true"); await sleep(900);
  ok("desktop: clicar no cartão seleciona no mapa", await avaliar("!!document.querySelector('path.mun.sel')"));
  await captura("d_03_selecao.png");
  await digitar("Registro");
  ok("desktop: perfil + encaminhamento", await esperar("document.querySelector('.sec-tit') && document.querySelectorAll('.cartao').length >= 4"));
  await captura("d_04_perfil.png");
  await digitar("Itanhaen");
  ok("desktop: corrige erro de digitação", await esperar("document.querySelector('.aviso-res') && /Itanha/.test(document.querySelector('.aviso-res').textContent)"));
  await avaliar("document.querySelector('#camada').value='g'; document.querySelector('#camada').dispatchEvent(new Event('change')); true"); await sleep(500);
  await avaliar("document.querySelector('#tema').click(); document.querySelector('#tema').click(); true"); await sleep(400);
  ok("desktop: tema escuro", await avaliar("document.documentElement.getAttribute('data-theme')==='dark'"));
  await digitar("regiões com maior taxa de internação"); await esperar("document.querySelectorAll('.badge.regiao').length >= 5");
  await captura("d_05_regioes_escuro.png");
  await checarPaineis("desktop");
  ok("desktop: sem erros de JS ao final", (await erros()) === "", await erros());
}

try {
  await conectar();
  await cmd("Page.enable"); await cmd("Runtime.enable");
  if (ROTEIRO !== "desktop") await roteiroMobile();
  if (ROTEIRO !== "mobile") await roteiroDesktop();
} catch (e) { console.log("ERRO NO TESTE:", e.message); relatorio.push(["FALHA", "execucao", e.message]); }
finally { try { ws.close(); } catch { /* */ } proc.kill(); }
const f = relatorio.filter((r) => r[0] === "FALHA").length;
console.log(`\n${relatorio.length - f}/${relatorio.length} verificações passaram.`);
process.exit(f ? 1 : 0);
