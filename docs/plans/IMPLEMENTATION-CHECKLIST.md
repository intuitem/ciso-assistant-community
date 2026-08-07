# BR Tropicalização — Checklist Granular de Implementação

## T1 — Framework LGPD (E1)

- [x] `lgpd.yaml`: 433 nós de requisito, 10 capítulos, texto vigente até Lei 15.352/2026 — `backend/library/libraries/lgpd.yaml` (commit `c624b9c4d`)
- [x] `preset-lgpd.yaml`: 19 objetos pré-configurados + 10 passos de jornada — `backend/library/libraries/preset-lgpd.yaml` (commit `8eaad170d`)
- [x] Bug corrigido durante teste: `policy.status: draft` inválido → `to_do`
- [x] Validado: `StoredLibrary` + `LoadedLibrary` (433 `RequirementNode`, 0 quebras) + `PresetExecutor.apply()` em transação revertida (19 objetos, 10 passos, sem erro)

## T2 — i18n pt-BR (E2)

- [x] `pt.json`: 27,7% → 100% de cobertura (5.490/5.490 chaves) — `frontend/messages/pt.json` (commit `d0a42d9aa`)
- [x] 12 lotes de ~350 chaves traduzidos e validados individualmente (paridade de chaves + placeholders)
- [x] 3 bugs de pluralização pré-existentes corrigidos (`untreatedRiskScenarios`, `acceptedRiskScenarios`, `inconsistenciesFoundComposer`)
- [x] Validado: compilação real do paraglide (`npx @inlang/paraglide-js compile`), funções `pt_*` geradas corretamente com interpolação
- [ ] Rebuild da imagem Docker do frontend para expor as traduções em produção (pendente — fora do escopo desta rodada)

## T3 — Maturidade de TSI + Terceiros (E3)

- [x] Design aprovado: adaptar `nist-csf-20-preset.yaml`, aprofundar terceiros com `entity`/`entity_assessment`/`vendor-due-diligence`
- [ ] Criar `backend/library/libraries/preset-tsi-terceiros.yaml` (locale primário `pt-BR`)
- [ ] Traduzir/tropicalizar os ~30 objetos e 14 passos herdados do preset NIST CSF
- [ ] Substituir o passo raso `supply_chain` por 2–3 passos de TPRM completo
- [ ] Validar via `StoredLibrary` + `PresetExecutor.apply()` (mesmo rigor do T1)

## T4 — Rebranding visual (E4)

- [x] Levantamento técnico: logo (`Logo.svelte` → `ciso.svg`), tema (`ciso-theme.css`), 6 ocorrências hardcoded de "CISO Assistant"
- [ ] **Validar licenciamento do CISO Assistant Community (bloqueante)**
- [ ] Sessão de brainstorm dedicada (nome, logo, paleta, tom de voz)
- [ ] Spec formal do T4

## Documentação (esta rodada)

- [x] `docs/plans/README.md`, `PLAN-BR-MASTER.md`, `PLAN-BR-T1..T4.md`, `IMPLEMENTATION-CHECKLIST.md` criados, seguindo o padrão de estrutura de `~/Downloads/m12-terceiros/`
