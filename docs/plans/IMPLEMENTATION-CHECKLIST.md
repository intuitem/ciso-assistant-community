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

- [x] Design aprovado: adaptar `nist-csf-20-preset.yaml`, aprofundar terceiros com `entity`/`vendor-due-diligence`
- [x] Criado `backend/library/libraries/preset-tsi-terceiros.yaml` (locale primário `pt-BR`, tradução `en`)
- [x] Traduzidos/tropicalizados os ~48 objetos e 16 passos (14 adaptados do NIST CSF + `vendors`/`vendor_due_diligence`)
- [x] Substituído o passo raso `supply_chain` por `vendors` (cadastro de 5 fornecedores críticos) + `vendor_due_diligence` (aponta para `entity-assessments`, sem scaffold — `entity_assessment`/`contract` não são tipos suportados por `preset_executor.py`)
- [x] Bug corrigido durante teste: `organisation_objective.status: to_do` inválido → `draft`
- [x] Validado: `StoredLibrary` + `upsert_preset_from_stored_library` + `PresetExecutor.apply()` em transação revertida — 48 objetos, 16 passos, sem erro, sem vazamento de dados de teste

## T4 — Rebranding visual (E4)

- [x] Levantamento técnico: logo (`Logo.svelte` → `ciso.svg`), tema (`ciso-theme.css`), 6 ocorrências hardcoded de "CISO Assistant"
- [x] Validar licenciamento do CISO Assistant Community — AGPLv3 permite rebranding fora de `enterprise/`, com obrigação de disponibilizar código-fonte no lançamento comercial
- [x] Nome comercial decidido: **CISO TSI**
- [x] `frontend/messages/*.json` (25 locales, 198 ocorrências) trocado para "CISO TSI"
- [x] 6 componentes Svelte hardcoded trocados para "CISO TSI"
- [x] `docs/plans/*.md` atualizados para referenciar "CISO TSI" como nome do produto (commit `8c952ef59`)
- [x] Nota de identificação de fork adicionada ao `README.md` principal (não reformulação completa — decisão deliberada)
- [x] Identidade visual: 3 candidatos de ícone comparados num artifact (legibilidade testada em 16/24px) → escolhido monograma "TSI" em círculo azul
- [x] Paleta retonalizada (`ciso-theme.css`, hue shift +4°/−3° preservando lightness/chroma)
- [x] `Logo.svelte`: variant `'icon'`/`'full'` (lockup ícone + "CISO TSI"), aplicado nas 4 páginas de autenticação
- [x] Favicon SVG novo + `<link rel="icon">` em `app.html`; 3 cores hardcoded do scrollbar trocadas para os tokens retonalizados
- [x] Validado via `svelte-check` (sem erros nos arquivos alterados) + verificação visual em servidor de desenvolvimento (commit `eca758bd6`)
- [ ] Regenerar `favicon.ico` binário (sem ferramenta de conversão de imagem disponível neste ambiente)
- [ ] Rebuild da imagem Docker do frontend para expor o rebranding em produção (pendência compartilhada com o T2)

## Documentação (esta rodada)

- [x] `docs/plans/README.md`, `PLAN-BR-MASTER.md`, `PLAN-BR-T1..T4.md`, `IMPLEMENTATION-CHECKLIST.md` criados, seguindo o padrão de estrutura de `~/Downloads/m12-terceiros/`
