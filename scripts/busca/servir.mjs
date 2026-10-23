// Servidor estatico minimo para testar web/ localmente (MIME correto para modulos ES).
// Uso: node scripts/busca/servir.mjs [porta]
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const RAIZ = fileURLToPath(new URL("../../web/", import.meta.url));
const MIME = { ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".json": "application/json; charset=utf-8",
  ".geojson": "application/geo+json", ".png": "image/png", ".svg": "image/svg+xml", ".ico": "image/x-icon" };
const porta = Number(process.argv[2] || 8766);

createServer(async (req, res) => {
  let p = decodeURIComponent(new URL(req.url, "http://x").pathname);
  if (p.endsWith("/")) p += "index.html";
  const arq = normalize(join(RAIZ, p));
  if (!arq.startsWith(RAIZ)) { res.writeHead(403).end(); return; }
  try {
    const dados = await readFile(arq);
    res.writeHead(200, { "Content-Type": MIME[extname(arq)] || "application/octet-stream", "Cache-Control": "no-store" }).end(dados);
  } catch { res.writeHead(404).end("nao encontrado"); }
}).listen(porta, () => console.log(`http://localhost:${porta}/`));
