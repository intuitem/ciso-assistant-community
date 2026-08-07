# BR — Tropicalização do CISO Assistant (planos)

Fork comercial white-label do CISO Assistant Community, adaptado para o mercado brasileiro: conteúdo regulatório nacional (LGPD), idioma pt-BR completo, jornada de maturidade de TI/SI + Gestão de Terceiros, e identidade visual própria. Ver [MASTER](PLAN-BR-MASTER.md).

## Planos (divisão por funcionalidade)

| Plano | Escopo | Status | Depende de |
|---|---|---|---|
| [MASTER](PLAN-BR-MASTER.md) | Visão, arquitetura, riscos, fases | 📋 Proposto | — |
| [T1 — Framework LGPD](PLAN-BR-T1-LGPD-FRAMEWORK.md) | Biblioteca de conformidade LGPD (433 requisitos, 10 capítulos) + preset de jornada | ✅ Concluído (commits `c624b9c4d`, `8eaad170d`) | — |
| [T2 — i18n pt-BR](PLAN-BR-T2-I18N-PTBR.md) | Cobertura de 100% das strings da UI em português brasileiro | ✅ Concluído (commit `d0a42d9aa`) | — |
| [T3 — Maturidade TSI + Terceiros](PLAN-BR-T3-TSI-TERCEIROS.md) | Jornada guiada de maturidade de TI/SI (NIST CSF 2.0 tropicalizado) + Gestão de Terceiros aprofundada | ✅ Concluído (2026-08-07) | T2 |
| [T4 — Rebranding visual](PLAN-BR-T4-REBRANDING.md) | Nome, logo, cores, tropicalização de marca | 🚧 Em andamento — licenciamento validado, nome de trabalho "CISO TSI" | — |

**Ordem recomendada:** T1 ∥ T2 ∥ T3 (concluídos) → T4.

## Artefatos relacionados

- Checklist granular: [IMPLEMENTATION-CHECKLIST](IMPLEMENTATION-CHECKLIST.md)
- Framework fonte: `backend/library/libraries/lgpd.yaml`, `backend/library/libraries/preset-lgpd.yaml`
- Traduções: `frontend/messages/pt.json`
- Referência de metodologia de documentação: estrutura adaptada de um projeto de gestão de terceiros interno do autor (`~/Downloads/m12-terceiros/`), aplicando o mesmo padrão de README índice + MASTER + planos por fatia + checklist granular com evidências.
