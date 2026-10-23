// Testes de regressao do motor de busca (node:test). Rodar: node --test scripts/busca/testes_motor.mjs
import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { criarMotor, norm } from "../../web/js/busca.js";

const ler = (n) => JSON.parse(readFileSync(new URL(`../../web/data/${n}.json`, import.meta.url), "utf-8"));
const motor = criarMotor({ municipios: ler("municipios"), regioes: ler("regioes"), servicos: ler("servicos"), meta: ler("meta") });
const ids = (r) => r.interpretacao.filtros.map((f) => f.id);
const ents = (r) => r.interpretacao.entidades.map((e) => e.id);

test("normalizacao ignora acento, caixa e pontuacao", () => {
  assert.equal(norm("  Santa Bárbara d'Oeste! "), "santa barbara d oeste");
  assert.deepEqual(motor.buscar("ITANHAÉM").resultados.map((x) => x.id), motor.buscar("itanhaem").resultados.map((x) => x.id));
});

test("Grande Sao Paulo e um grupo, nao o municipio 'Sao Paulo'", () => {
  const r = motor.buscar("municípios da Grande São Paulo sem CAPS AD");
  assert.ok(ids(r).includes("grande_sp") && ids(r).includes("sem_caps"));
  assert.ok(!ids(r).includes("porte_grande"));
  assert.equal(ents(r).length, 0);
  assert.ok(r.resultados.every((x) => x.dados.gs === 1 && x.dados.k === 0));
});

test("nome de municipio sozinho vira perfil, com encaminhamento", () => {
  const r = motor.buscar("Bauru");
  assert.equal(r.interpretacao.intencao, "perfil");
  assert.equal(r.resultados[0].titulo, "Bauru");
  assert.ok(r.extras.referencia.length > 0);
});

test("'regiao de <municipio>' usa a regiao de saude do municipio", () => {
  const r = motor.buscar("baixa internação e alto acesso na região de Campinas");
  assert.equal(r.interpretacao.entidades[0].tipo, "regiao");
  assert.ok(ids(r).includes("internacao_baixa") && ids(r).includes("acesso_alto"));
});

test("municipio e regiao homonimos: lista de municipios prefere a regiao", () => {
  const r = motor.buscar("Sorocaba: municípios sem serviço");
  assert.equal(r.interpretacao.entidades[0].tipo, "regiao");
  assert.ok(r.resultados.every((x) => x.dados.k === 0));
});

test("pedido de encaminhamento identifica a origem e ordena por score", () => {
  for (const q of ["para onde encaminhar paciente de Registro", "serviço mais próximo de Taciba", "onde tratar dependência de álcool em Iguape"]) {
    const r = motor.buscar(q);
    assert.equal(r.interpretacao.intencao, "referencia", q);
    assert.ok(r.resultados.length > 0 && r.resultados.length <= 8, q);
    const sc = r.resultados.map((x) => x.score);
    assert.deepEqual(sc, [...sc].sort((a, b) => b - a), q);
  }
});

test("superlativo depois do substantivo vira ordenacao", () => {
  const r = motor.buscar("onde a taxa de internação é maior na Baixada Santista");
  assert.equal(r.interpretacao.ordenacao?.chave, "internacao");
  assert.equal(r.interpretacao.entidades[0].tipo, "regiao");
});

test("erro de digitacao de uma letra e corrigido, com aviso", () => {
  const r = motor.buscar("Itanhaen");
  assert.ok(r.avisos.some((a) => /Itanhaém/.test(a)));
  assert.equal(r.resultados[0].titulo, "Itanhaém");
});

test("faixa de porte numerica filtra de verdade", () => {
  const r = motor.buscar("municípios entre 20 e 50 mil habitantes sem CAPS AD");
  assert.ok(ids(r).includes("porte_faixa:20000-50000"));
  assert.ok(r.resultados.length > 20 && r.resultados.every((x) => x.dados.p >= 20000 && x.dados.p <= 50000 && x.dados.k === 0));
});

test("invariante: todo resultado satisfaz todos os filtros ativos e os scores nao crescem", () => {
  const consultas = ["cidades pequenas com alta internação e sem serviço", "maiores municípios sem CAPS AD habilitado", "municípios do litoral com baixa acessibilidade",
    "desertos de cuidado na região de Marília", "cidades grandes do interior com alta internação", "municípios longe de um CAPS AD"];
  for (const q of consultas) {
    const r = motor.buscar(q);
    assert.ok(r.total > 0, q);
    for (const x of r.resultados) for (const f of r.interpretacao.filtros) assert.ok(f.fn(x.dados), `${q}: ${x.titulo} viola ${f.id}`);
    const sc = r.resultados.map((x) => x.score);
    assert.deepEqual(sc, [...sc].sort((a, b) => b - a), q);
  }
});

test("remover um filtro (ignorar) amplia os resultados", () => {
  // (cidades pequenas quase nunca tem CAPS AD: la o filtro nao restringe; no interior em geral, sim)
  const q = "municípios do interior sem CAPS AD";
  const todos = motor.buscar(q).total, sem = motor.buscar(q, { ignorar: new Set(["sem_caps"]) }).total;
  assert.ok(sem > todos, `${sem} deveria ser maior que ${todos}`);
});

test("servicos: modalidade, municipio sem servico cai para os mais proximos", () => {
  const r = motor.buscar("CAPS AD III em Campinas");
  assert.equal(r.interpretacao.intencao, "servicos");
  assert.ok(r.resultados.length > 0 && r.resultados.every((x) => x.dados.mo === "AD III" && x.dados.mn === "Campinas"));
  const s = motor.buscar("CAPS AD em Registro");
  assert.ok(s.avisos.some((a) => /não tem CAPS AD/.test(a)) && s.resultados.length > 0);
});

test("regioes: ranking por taxa de internacao", () => {
  const r = motor.buscar("regiões com maior taxa de internação");
  assert.equal(r.interpretacao.intencao, "regioes");
  assert.equal(r.resultados[0].titulo, "Mantiqueira");
  assert.equal(r.total, 62);
});

test("consulta vazia ou sem sentido nao quebra e nao inventa resultados", () => {
  assert.equal(motor.buscar("").total, 0);
  assert.equal(motor.buscar("xyzzyqq").total, 0);
  assert.equal(motor.buscar("   ").total, 0);
});

test("desempenho: consulta tipica em menos de 250 ms", () => {
  const t0 = performance.now();
  for (let i = 0; i < 10; i++) motor.buscar("cidades pequenas com alta internação e sem serviço");
  assert.ok((performance.now() - t0) / 10 < 250);
});

test("corpus tem o tamanho esperado", () => {
  assert.deepEqual(motor.corpus, { municipios: 645, regioes: 62, servicos: 115, documentos: 822 });
});
