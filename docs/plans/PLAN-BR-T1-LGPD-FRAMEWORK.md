# PLAN-BR-T1 — Framework LGPD (conformidade + jornada)

**Status:** ✅ Concluído — commits `c624b9c4d`, `8eaad170d`

## 1. Objetivo

Dar ao produto um framework de conformidade nativo brasileiro (LGPD) e uma jornada guiada para o cliente implantar um programa de adequação do zero, sem depender de frameworks estrangeiros (GDPR) como proxy.

## 2. Escopo entregue

- `backend/library/libraries/lgpd.yaml`: biblioteca de conformidade com a Lei 13.709/2018, texto consolidado até as alterações de 2025/2026 (MP 1.317/2025, Lei 15.352/2026). 433 nós de requisito, 10 capítulos, 351 avaliáveis. Capítulo IX (ANPD/Conselho Nacional) modelado em nível de artigo — normas de organização do regulador, não obrigações do agente de tratamento.
- `backend/library/libraries/preset-lgpd.yaml`: jornada "Empresa Brasileira - LGPD" com 19 objetos pré-configurados (avaliação de risco, auditoria de conformidade, matriz de responsabilidades DPO, registros de tratamento, entidades operadoras típicas, objetivos, tarefas recorrentes, política de privacidade) e 10 passos guiados.

## 3. Validação realizada

- Framework carregado via `StoredLibrary.store_library_file()` + `LoadedLibrary` — 433 `RequirementNode`, 0 referências de pai quebradas.
- Preset aplicado de ponta a ponta via `PresetExecutor.apply()` numa transação revertida — 19 objetos e 10 passos de jornada criados sem erro (um bug real de enum inválido em `status: draft` para `policy` foi encontrado e corrigido durante o teste, `to_do`).

## 4. Critérios de aceite

1. Framework aparece em Catalog → Frameworks com 433 requisitos. ✅
2. Preset aplicável cria um domínio funcional com DPO, registro de tratamento e auditoria LGPD sem intervenção manual. ✅
3. Nenhum erro de validação do backend ao carregar ou aplicar. ✅
