# PLAN-BR-T4 — Rebranding visual

**Status:** ✅ Concluído (2026-08-08) — nome comercial decidido (**CISO TSI**), licenciamento validado, troca textual e identidade visual (ícone, lockup, paleta, favicon) implementadas e commitadas. Itens residuais fora do escopo aprovado, ver §6.

## 1. Objetivo

Substituir a identidade visual do CISO Assistant (nome, logo, paleta) pela marca própria **CISO TSI** no produto comercial brasileiro.

## 2. O que já sabemos (levantamento técnico feito)

- Logo: componente único `frontend/src/lib/components/Logo/Logo.svelte`, aponta para `frontend/src/lib/assets/ciso.svg`.
- Cores/tema: centralizadas em `frontend/ciso-theme.css`.
- 6 ocorrências de "CISO Assistant" hardcoded no código-fonte (fora do i18n) — já trocadas para "CISO TSI" (ver §4).

## 3. Bloqueio de licenciamento — validado (2026-08-07)

O CISO Assistant Community tem duas licenças: **AGPLv3** para tudo fora de `enterprise/` (o que roda hoje via `ghcr.io/intuitem/ciso-assistant-community`), e **licença comercial proprietária da Intuitem** para o conteúdo de `enterprise/` (não pode ser usado em produção, copiado, modificado ou revendido sem contrato).

**Conclusão:** renomear/rebrandear para "CISO TSI" é permitido pela AGPLv3, desde que:
1. Fique restrito ao código fora de `enterprise/`.
2. As obrigações da AGPL sejam mantidas: preservar avisos de copyright/licença dos arquivos originais, manter o texto da licença disponível, e — a obrigação central da AGPL — **disponibilizar o código-fonte completo (com modificações) para qualquer usuário que interaja com o sistema pela rede**, quando isso for para produção como SaaS pago. Isso é um item de compliance para o lançamento comercial, não um bloqueio para o trabalho de rebranding em si.
3. Nada de `enterprise/` seja usado/revendido sem contrato com a Intuitem.

"CISO Assistant" não é uma marca licenciada pela AGPL — trocar de nome reduz risco de marca registrada, não aumenta.

## 4. Trabalho realizado (troca textual, 2026-08-07)

- `frontend/messages/*.json` (25 locales): 198 ocorrências de "CISO Assistant"/"Ciso Assistant" trocadas para "CISO TSI"/"Ciso TSI" nos valores das strings (chaves i18n como `welcomeToCISOAssistant` mantidas intactas — são identificadores, não texto exibido).
- 6 componentes Svelte com nome hardcoded (`login/+page.svelte`, `setup-mfa/+page.svelte`, `+layout.svelte`, `ActivateTOTPModal.svelte`, `executive-summary/+page.svelte`, `ChatWidget.svelte`) — títulos de página, issuer do TOTP/MFA, e rótulos do chat widget atualizados.
- Documentos de planejamento (`docs/plans/*.md`) atualizados para referenciar "CISO TSI" como nome do produto, mantendo "CISO Assistant Community" onde o texto se refere factualmente ao projeto open source de origem (proveniência/licenciamento).

## 5. Trabalho realizado (identidade visual, 2026-08-08)

Sessão de brainstorm dedicada (design lead → 3 candidatos de mark comparados visualmente num artifact, com teste de legibilidade em escala real de favicon 16/24px) resultou em:

- **Paleta**: retonalização do roxo/azul do tema atual (Skeleton UI, `oklch`) — hue shift de +4° no primário e −3° no secundário, mantendo lightness/chroma originais (preserva o ajuste de acessibilidade/contraste já feito). `frontend/ciso-theme.css`.
- **Ícone**: monograma "TSI" num círculo azul (`#1E4FD8`) — candidato "B" do comparativo, escolhido por manter a melhor legibilidade em 16px entre os 3 testados. `frontend/src/lib/assets/ciso.svg`.
- **Lockup**: `Logo.svelte` ganhou um prop `variant: 'icon' | 'full'` — `'icon'` (padrão, compatível com todos os usos existentes, incluindo a sidebar) e `'full'` (ícone + "CISO TSI" por extenso), aplicado nas 4 páginas de autenticação (login, first-connexion, password-reset ×2).
- **Favicon**: `frontend/static/favicon.svg` novo, referenciado via `<link rel="icon">` em `app.html`. O `.ico` binário foi regenerado em 2026-08-10 (`librsvg`/`rsvg-convert` + Pillow, nos 6 tamanhos padrão 16–256px) em `frontend/static/favicon.ico` e `frontend/src/lib/assets/favicon.ico`.
- **Scrollbar**: as 3 cores hardcoded em `app.html` (`#694998` etc.) trocadas para referenciar os tokens retonalizados do tema.
- Validado via `svelte-check` (nenhum erro introduzido nos arquivos alterados) e verificação visual ao vivo em servidor de desenvolvimento (login renderiza o lockup corretamente).
- Commit `eca758bd6`.

## 6. Pendente

1. ~~Regenerar o `favicon.ico` binário~~ — ✅ resolvido em 2026-08-10.
2. `README.md` principal do repositório recebeu apenas uma nota de identificação do fork (não uma reformulação completa) — e as demais 300+ referências fora do escopo aprovado (CI/CD, packaging, conectores de terceiros, `product-docs/`) seguem deliberadamente não tocadas; decisão de negócio separada sobre se/quando estender o rebranding a essas áreas.
3. ~~Antes do lançamento comercial: implementar o mecanismo de disponibilização de código-fonte exigido pela AGPL (§3)~~ — ✅ resolvido em 2026-08-13, ver [PLAN-BR-T5](PLAN-BR-T5-AGPL-COMPLIANCE.md).
4. ~~Rebuild da imagem Docker do frontend~~ — ✅ resolvido em 2026-08-11: imagem `ciso-assistant-community-frontend:latest` construída localmente via `docker-compose-build.yml` (foi necessário subir a RAM alocada ao Docker Desktop de 7.75GB para ~15.8GB — o build do SvelteKit/Vite estourava OOM no limite anterior) e o container `frontend` em execução foi recriado com essa imagem. Verificado via `curl https://localhost:8443/` — título "CISO TSI | Login" e favicon novo servidos corretamente.

## 7. Critérios de aceite

1. Nome comercial decidido e documentado: **CISO TSI**. ✅
2. Licenciamento validado, sem bloqueio para a troca textual e visual. ✅
3. Nenhuma referência textual a "CISO Assistant" visível ao usuário final no escopo de docs/plans + UI + i18n. ✅
4. Identidade visual (ícone, lockup, paleta, favicon) implementada e validada. ✅
5. Favicon binário `.ico` regenerado. ✅
