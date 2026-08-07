# PLAN-BR-T4 — Rebranding visual

**Status:** 📋 Proposto — **não desenhado ainda**. Este documento é um placeholder de escopo, não uma spec aprovada.

## 1. Objetivo (rascunho)

Substituir a identidade visual do CISO Assistant (nome, logo, paleta) por uma marca própria para o produto comercial brasileiro.

## 2. O que já sabemos (levantamento técnico feito)

- Logo: componente único `frontend/src/lib/components/Logo/Logo.svelte`, aponta para `frontend/src/lib/assets/ciso.svg`.
- Cores/tema: centralizadas em `frontend/ciso-theme.css`.
- Apenas 6 ocorrências de "CISO Assistant" hardcoded no código-fonte (fora do i18n) — o grosso do nome do produto já está nas strings de `frontend/messages/*.json`.

## 3. Bloqueio conhecido — validar antes de prosseguir

**Licenciamento**: o CISO Assistant Community é distribuído sob licença que precisa ser conferida (`LICENSE` no repositório) antes de remover a marca original e revender como produto próprio. Pode haver obrigações de manter créditos/copyleft, ou pode existir uma via comercial já prevista pela intuitem (edição "enterprise"). **Esta validação é pré-requisito de negócio para todo o T4**, não apenas um risco técnico.

## 4. Próximos passos

1. Validar licenciamento (bloqueante).
2. Sessão de brainstorm dedicada para: nome comercial, identidade visual (logo, paleta), tom de voz.
3. Escrever a spec formal deste plano seguindo o mesmo processo usado no T3 (brainstorm → 2-3 abordagens → design aprovado → doc).

## 5. Critérios de aceite (a confirmar após o brainstorm)

- Definir na spec formal, após a sessão de brainstorm dedicada.
