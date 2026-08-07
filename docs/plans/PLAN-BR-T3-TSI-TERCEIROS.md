# PLAN-BR-T3 — Maturidade de TSI + Gestão de Terceiros

**Status:** ✅ Concluído (2026-08-07)
**Depende de:** T2 (i18n pt-BR)

## 1. Objetivo

Entregar uma jornada guiada única dentro do produto que leve o cliente a: (a) avaliar a maturidade da governança interna de TI/SI (TSI — Tecnologia e Sistemas de Informação), e (b) gerenciar e avaliar fornecedores/terceiros críticos — sem sair do CISO Assistant, reaproveitando ao máximo capacidades já existentes.

## 2. Escopo

### 2.1 Backbone de maturidade (TSI)

Adaptar o preset `nist-csf-20-preset.yaml` já existente no catálogo (não construir do zero): 6 funções do NIST CSF 2.0 (Governar/Identificar/Proteger/Detectar/Responder/Recuperar), que usam nativamente o conceito de *Tiers* (níveis de maturidade 1–4). Traduzir e tropicalizar:

- Trocar exemplos de reguladores estrangeiros (CERT NZ, ACSC) por ANPD/CERT.br.
- Referenciar a LGPD nas questões organizacionais de obrigação regulatória (`organisation_issue` "Regulatory and legal compliance obligations").
- Traduzir integralmente os ~30 objetos pré-configurados e os 14 passos de jornada para pt-BR (locale primário, como no T1).

### 2.2 Gestão de Terceiros (aprofundamento)

O passo único e raso `supply_chain` do preset de referência (hoje só cria `assets`) vira 2 passos dedicados, reaproveitando o aparato de TPRM já usado no T1:

1. Cadastro de fornecedores críticos (`entity`) — 5 entidades pré-criadas (nuvem, identidade/SSO, e-mail/colaboração, monitoramento/SIEM, pagamentos).
2. Due diligence de fornecedores (`entity-assessments`, framework `vendor-due-diligence`).

**Correção em relação ao design original:** `entity_assessment` e `contract` **não são tipos suportados** em `scaffolded_objects` (confirmado em `backend/library/preset_executor.py` — apenas `entity` é suportado entre os tipos de terceiros). O passo de due diligence aponta para `target_model: entity-assessments` **sem objeto pré-criado** (o usuário cria a avaliação a partir da entidade, dentro do produto) — mesmo padrão já usado pelo passo "vendors" do `preset-lgpd.yaml` (T1). O passo dedicado de "gestão de contratos" foi removido do escopo por não ter tipo de objeto suportado.

### 2.3 Fora do escopo

- Qualquer verticalização setorial (Bacen, ANS, etc.) — decidido no brainstorm (produto genérico).
- Novo modelo de dados/UI de maturidade fora do mecanismo de `compliance_assessment` já existente.

## 3. Arquitetura / arquivos

- Novo arquivo `backend/library/libraries/preset-tsi-terceiros.yaml`, seguindo exatamente o padrão de `preset-lgpd.yaml` (locale primário `pt-BR`, tradução `en`).
- Dependências: `urn:intuitem:risk:library:nist-csf-2.0-journey`, `urn:intuitem:risk:library:risk-matrix-5x5-iso27005`, `urn:intuitem:risk:library:vendor-due-diligence`, `urn:intuitem:risk:library:intuitem-common-catalog`.
- Nome definitivo do preset (`ref_id`/`name`) depende do T4 (rebranding) — usar título de trabalho "Maturidade de TSI e Gestão de Terceiros" até lá.

## 4. Validação realizada (mesmo rigor do T1)

1. Carregado como `StoredLibrary` (`store_library_file`) + `upsert_preset_from_stored_library` — `backend/library/libraries/preset-tsi-terceiros.yaml`.
2. Aplicado via `PresetExecutor.apply()` numa transação revertida — todos os objetos (6 `organisation_issue`, 5 `organisation_objective`, 12 `entity`, 3 `findings_assessment`, 1 `risk_assessment`, 1 `compliance_assessment` com `create_suggested_controls: true`, 8 `asset`, 7 `risk_scenario`, 8 `task_template`) e os 16 passos de jornada (14 originais adaptados + `vendors` e `vendor_due_diligence`, substituindo o `supply_chain` raso) criados sem erro.
3. Nenhum vazamento de `Folder`/`PresetJourney`/`StoredLibrary` de teste confirmado após rollback.

## 5. Riscos

| Risco | Status |
|---|---|
| Enums inválidos em campos de status (como ocorreu no T1 com `policy.status`) | Ocorreu de novo: `OrganisationObjective.status` não aceita `to_do` (só `draft`, `in_progress`, `achieved`, `degraded`, `deprecated`) — corrigido durante a validação |
| `entity_assessment`/`contract` não suportados como `scaffolded_objects` | Confirmado via grep em `preset_executor.py` — corrigido no design (ver §2.2) antes da implementação |
| Framework NIST CSF em inglês no catálogo pode ter nós de requisito não traduzidos | A tradução do preset não traduz o framework subjacente — aceito como limitação conhecida, fora do escopo do T3 |

## 6. Critérios de aceite

1. Um único preset cobre maturidade de TI/SI e terceiros, sem exigir que o cliente aplique dois presets separados. ✅
2. Passo de terceiros usa `entity` (cadastro) + `entity-assessments` (due diligence via UI), dentro dos tipos suportados pelo executor. ✅
3. `PresetExecutor.apply()` roda sem erro em transação de teste. ✅
