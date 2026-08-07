# PLAN-BR-T4 — Rebranding visual

**Status:** 🚧 Em andamento — nome comercial decidido (**CISO TSI**), licenciamento validado, troca textual concluída. Identidade visual (logo/paleta) ainda não desenhada.

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

## 5. Pendente

1. Identidade visual: novo logo (`Logo.svelte`/`ciso.svg`) e paleta de cores (`ciso-theme.css`) — trabalho de design gráfico, não coberto por esta rodada de troca textual.
2. `README.md` principal do repositório e demais 300+ referências fora do escopo aprovado (CI/CD, packaging, conectores de terceiros, `product-docs/`) — deliberadamente não tocadas nesta rodada; decisão de negócio separada sobre se/quando estender o rebranding a essas áreas.
3. Antes do lançamento comercial: implementar o mecanismo de disponibilização de código-fonte exigido pela AGPL (§3).

## 6. Critérios de aceite

1. Nome comercial decidido e documentado: **CISO TSI**. ✅
2. Licenciamento validado, sem bloqueio para a troca textual. ✅
3. Nenhuma referência textual a "CISO Assistant" visível ao usuário final no escopo de docs/plans + UI + i18n. ✅
4. Identidade visual (logo, paleta) redesenhada. ⬜ Pendente — requer sessão de design dedicada.
