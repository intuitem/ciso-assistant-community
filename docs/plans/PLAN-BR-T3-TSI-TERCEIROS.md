# PLAN-BR-T3 — Maturidade de TSI + Gestão de Terceiros

**Status:** 📋 Proposto — design aprovado (2026-08-07), implementação não iniciada
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

O passo único e raso `supply_chain` do preset de referência (hoje só cria `assets`) vira 2–3 passos dedicados, reaproveitando o aparato de TPRM já usado no T1:

1. Cadastro de fornecedores críticos (`entity`).
2. Due diligence de fornecedores (`entity_assessment`, framework `vendor-due-diligence`).
3. Gestão de contratos (`contract`, vinculado às entidades).

### 2.3 Fora do escopo

- Qualquer verticalização setorial (Bacen, ANS, etc.) — decidido no brainstorm (produto genérico).
- Novo modelo de dados/UI de maturidade fora do mecanismo de `compliance_assessment` já existente.

## 3. Arquitetura / arquivos

- Novo arquivo `backend/library/libraries/preset-tsi-terceiros.yaml`, seguindo exatamente o padrão de `preset-lgpd.yaml` (locale primário `pt-BR`, tradução `en`).
- Dependências: `urn:intuitem:risk:library:nist-csf-2.0-journey`, `urn:intuitem:risk:library:risk-matrix-5x5-iso27005`, `urn:intuitem:risk:library:vendor-due-diligence`, `urn:intuitem:risk:library:intuitem-common-catalog`.
- Nome definitivo do preset (`ref_id`/`name`) depende do T4 (rebranding) — usar título de trabalho "Maturidade de TSI e Gestão de Terceiros" até lá.

## 4. Validação planejada (mesmo rigor do T1)

1. Carregar como `StoredLibrary` + `upsert_preset_from_stored_library`.
2. Aplicar via `PresetExecutor.apply()` numa transação revertida — confirmar que todos os objetos e os ~16 passos de jornada (14 originais + 2–3 novos de terceiros, menos o `supply_chain` substituído) são criados sem erro.
3. Checagem de placeholders/traduções como no T2.

## 5. Riscos

| Risco | Mitigação |
|---|---|
| Enums inválidos em campos de status (como ocorreu no T1 com `policy.status`) | Testar `apply()` de ponta a ponta antes de considerar concluído, igual ao T1 |
| Framework NIST CSF em inglês no catálogo pode ter nós de requisito não traduzidos | A tradução do preset não traduz o framework subjacente — verificar se isso é aceitável ou se o framework também precisa de tradução (decisão pendente) |

## 6. Critérios de aceite

1. Um único preset cobre maturidade de TI/SI e terceiros, sem exigir que o cliente aplique dois presets separados.
2. Passo de terceiros usa `entity` + `entity_assessment` (due diligence real), não apenas `asset`.
3. `PresetExecutor.apply()` roda sem erro em transação de teste.
