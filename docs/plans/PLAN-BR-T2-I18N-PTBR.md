# PLAN-BR-T2 — i18n pt-BR completo

**Status:** ✅ Concluído — commit `d0a42d9aa`

## 1. Objetivo

Eliminar o fallback silencioso para inglês nas telas do produto quando o usuário seleciona português, cobrindo 100% das strings de UI.

## 2. Escopo entregue

- `frontend/messages/pt.json`: de 1.522/5.489 chaves (27,7%) para 5.490/5.490 (100%), mantendo a ordem de `en.json` para diffabilidade.
- Locale usado: `pt` (já mapeado à bandeira 🇧🇷 em `frontend/src/lib/utils/locales.ts` — decisão deliberada de **não** criar um `pt-BR` separado, já que não existe distinção `pt-PT` no produto).
- 3 bugs pré-existentes de placeholder de pluralização corrigidos (`untreatedRiskScenarios`, `acceptedRiskScenarios`, `inconsistenciesFoundComposer`), alinhados ao padrão `{s}` já usado por `fr`/`es`.

## 3. Validação realizada

- Checagem de paridade de chaves e integridade de placeholders `{variável}` contra `en.json` em todos os lotes e no arquivo final.
- Compilação real do runtime paraglide (`npx @inlang/paraglide-js compile`) — confirmado que as funções de mensagem geradas para `pt` retornam o texto traduzido e interpolam variáveis corretamente.

## 4. Pendências conhecidas

- O frontend em produção roda a partir de uma imagem Docker pré-compilada (`ghcr.io/intuitem/.../frontend:latest`), sem bind mount do código-fonte — um rebuild da imagem é necessário para o cliente final ver as traduções (não feito nesta rodada).

## 5. Critérios de aceite

1. 100% das chaves de `en.json` presentes em `pt.json`. ✅
2. Nenhum placeholder `{variável}` divergente entre `en` e `pt`. ✅
3. Compilação do paraglide sem erros. ✅
