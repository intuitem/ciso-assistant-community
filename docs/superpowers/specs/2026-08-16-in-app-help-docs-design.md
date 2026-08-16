# Documentação in-app (Help/Docs) — Design

**Data:** 2026-08-16
**Status:** Aprovado
**Relacionado:** [PLAN-BR-MASTER.md](../../plans/PLAN-BR-MASTER.md), `product-docs/` (fonte GitBook upstream da Intuitem)

## 1. Problema

O menu "Sobre" do CISO TSI linka "Documentação online" para `https://intuitem.gitbook.io/ciso-assistant` — um site externo, de marca "CISO Assistant" (não CISO TSI), fora do controle do produto. O conteúdo-fonte dessa documentação já existe neste repositório em `product-docs/` (169 arquivos markdown, ~56MB majoritariamente em imagens), mas não é servido pela própria plataforma.

## 2. Escopo

Trazer o conteúdo de `product-docs/` para dentro da aplicação SvelteKit, como uma seção `/help` navegável, substituindo o link externo. **Fora de escopo nesta rodada**: tradução para pt-BR (fica para um T6 futuro, do mesmo porte do T2), busca full-text, sincronização contínua com mudanças futuras do upstream (é uma cópia pontual, como o T2 foi para as traduções).

## 3. Pipeline de conteúdo

- Cópia única (não symlink, não sync automático): `product-docs/**/*.md` (exceto `SUMMARY.md`, tratado à parte) → `frontend/src/lib/help-content/`; `product-docs/.gitbook/assets/**` → `frontend/static/help-assets/`.
- Carregado via `import.meta.glob('/src/lib/help-content/**/*.md', { eager: true, query: '?raw', import: 'default' })` — conteúdo vira parte do bundle da aplicação, sem leitura de filesystem em runtime.
- `SUMMARY.md` (árvore de navegação nativa do GitBook: lista aninhada de `[Título](caminho/pagina.md)`) é parseado em uma árvore JSON `{ title, slug, children[] }` para virar o menu lateral.

## 4. Pré-processador de markdown GitBook → HTML

Frequência real no conteúdo (`grep -rhoE '{% [a-z-]+' product-docs`): `hint` 66 arquivos, `embed` 20, `tabs`/`stepper` 3 cada, `content-ref`/`file`/`code` 1–2 cada.

- Front-matter (`--- description: ... ---`): removido do corpo, `description` extraída como subtítulo da página.
- `{% hint style="info|warning|success|danger" %}...{% endhint %}`: renderizado como caixa de destaque estilizada (reaproveitando classes de alerta já existentes no design system, se houver; senão, classe nova simples `.help-hint-{style}`).
- `{% embed url="X" %}LABEL{% endembed %}` (ou variante sem label): convertido para link markdown simples `[▶ LABEL](X)`, abre em nova aba — não embute iframe de terceiro (evita risco de segurança/CSP de embutir Loom/Guidde arbitrariamente).
- Tags de baixa frequência (`tabs`, `stepper`, `content-ref`, `file`, `code` — 1 a 3 arquivos cada): as marcações `{% %}`/`{% end%}` são removidas, conteúdo interno permanece como markdown sequencial simples (degradação aceitável, sem UI de abas/steps nesta rodada).
- Imagens: paths relativos a `.gitbook/assets/` reescritos para `/help-assets/<arquivo>`.
- Links internos entre páginas (`[texto](outra-pagina.md)` ou `[texto](../pasta/pagina.md)`): resolvidos para rotas internas `/help/<slug>`.
- Renderização final reaproveita `marked` + `sanitize-html` (já usados em `MarkdownRenderer.svelte`), com o pré-processamento acima aplicado antes de `marked()`.

## 5. Rotas e UI

- `frontend/src/routes/(app)/(internal)/help/+layout.svelte`: shell com sidebar de navegação (árvore do `SUMMARY.md`, colapsável) + slot de conteúdo.
- `frontend/src/routes/(app)/(internal)/help/[...slug]/+page.server.ts`: resolve o slug da URL contra o mapa de conteúdo pré-carregado; `error(404)` se não encontrado.
- `frontend/src/routes/(app)/(internal)/help/[...slug]/+page.svelte`: renderiza título, subtítulo (description) e corpo processado via um componente de renderização reaproveitando a lógica de `MarkdownRenderer.svelte`.
- `/help` sem slug: renderiza o conteúdo de `product-docs/README.md` (página de introdução do GitBook) como landing da seção.

## 6. Mudança no menu "Sobre"

Em `frontend/src/lib/components/SideBar/SideBarFooter.svelte`, o link `href="https://intuitem.gitbook.io/ciso-assistant" target="_blank"` (`data-testid="docs-button"`) passa a ser `href="/help"`, sem `target="_blank"` (navegação interna).

## 7. Testes

- Verificação manual: navegar pela árvore completa de `/help`, conferir que ao menos uma página de cada tipo de bloco GitBook (hint, embed, tabs, stepper) renderiza sem quebrar.
- `svelte-check` nos arquivos novos/alterados.
- Conferir que imagens carregam (`/help-assets/...`) em pelo menos as páginas que mais usam (`initial-setup.md`, guias com screenshots).

## 8. Critérios de aceite

1. Seção `/help` acessível, navegável via sidebar, cobrindo as 169 páginas de `product-docs/`.
2. Blocos `hint` e `embed` (as duas sintaxes mais frequentes) renderizam corretamente formatados, não como texto cru `{% ... %}`.
3. Link "Documentação online" no menu "Sobre" aponta para `/help` interno.
4. Nenhuma imagem quebrada nas páginas mais visitadas (guias de introdução/setup).
