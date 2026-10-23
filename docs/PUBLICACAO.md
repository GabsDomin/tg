# Publicação do site (Vercel)

O site é **estático** (`web/`): HTML + JS + JSON. Não há servidor nem build.
A Vercel não hospeda Streamlit, por isso o site lê só dados pré-computados.

## Estado atual (23/10/2026)
- **Site no ar: https://tg-red.vercel.app** (projeto `tg`, conta `gabsdomin`, publicado pela CLI).
- O endereço com hash (`tg-<hash>-gabsdomins-projects.vercel.app`) fica atrás de login da
  Vercel; **divulgue só o `tg-red.vercel.app`**.
- **Deploy automático pelo GitHub NÃO está ligado** (o app da Vercel não tem acesso ao
  repositório). Para atualizar o site, rode a partir da pasta `web`:
  `npx vercel deploy --prod --yes`. Para ligar o deploy automático: Vercel → projeto `tg` →
  Settings → Git → conectar `GabsDomin/tg` (exige autorizar o app da Vercel no GitHub).
- `web/.env.local` e `web/.vercel/` contêm token/ids da Vercel: estão no `web/.gitignore`.
  **Nunca** versionar.

## Atualizar os dados
```
.venv\Scripts\python.exe -I pipeline.py demanda acessibilidade publicar
.venv\Scripts\python.exe -m pytest tests/test_publicar.py
```
`publicar` regrava `web/data/` (municípios, serviços, malha, meta). Só agregados saem daí
(o teste falha se aparecer coluna identificadora).

## Testar localmente
```
.venv\Scripts\python.exe -m http.server 8765 --directory web
```
Abrir `http://localhost:8765/`. Link direto para a aba Referência: `/#ref=Ilha Comprida`.

## Publicar na Vercel
Pré-requisito: repositório no GitHub (decisão D7: **nunca** versionar `dados/bruto/` nem
`dados/tratado/`; o `.gitignore` já bloqueia). `web/data/` **deve** ser versionado.

1. vercel.com → *Add New → Project* → importar o repositório.
2. **Root Directory: `web`**. *Framework Preset: Other*. Build Command e Output Directory: vazios.
3. *Deploy*.

Ou pela CLI: `npx vercel --cwd web` (primeiro acesso pede login).

## Antes de divulgar o endereço
- Rever a aba **Sobre** e o aviso do topo com o Prof. Ivan.
- Os pesos do ranqueamento de referência (`web/data/meta.json`) são provisórios.
- O site é rotulado "Versão preliminar" até a avaliação (Fase 4) existir.
