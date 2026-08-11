# PLAN-BR-MASTER — Tropicalização: CISO Assistant → CISO TSI

**Status:** ✅ Concluído (2026-08-08) — T1–T4 entregues
**Prioridade:** Alta
**Módulos impactados:** `backend/library/libraries/` (conteúdo), `frontend/messages/` (i18n), `frontend/src/lib/assets/` + `frontend/src/lib/components/Logo/` + `frontend/ciso-theme.css` (marca), licenciamento (a validar)

> **Divisão por funcionalidade:** este master define visão, escopo e riscos; a implementação é fatiada em planos por frente (T1–T4). Ver [README](README.md).

---

## 1. Visão e objetivos

Transformar o CISO Assistant Community (GRC open source, francês/inglês) em **CISO TSI**, um produto comercial white-label tropicalizado para o mercado brasileiro: conteúdo regulatório nacional, idioma nativo, uma jornada guiada de maturidade de TI/SI + Gestão de Terceiros como funcionalidade de destaque, e identidade visual própria.

**Resultado de negócio:** produto GRC pronto para venda a empresas brasileiras de qualquer setor, sem depender de tradução/adaptação manual pelo cliente, com um caminho claro de "primeiro uso" para maturidade interna e de fornecedores.

## 2. Escopo

### 2.1 Concluído

- **T1 — Framework LGPD**: biblioteca de conformidade completa (Lei 13.709/2018, 433 requisitos, 10 capítulos, texto vigente até Lei 15.352/2026) + preset de jornada guiada (DPO, registro de tratamentos, due diligence de operadores).
- **T2 — i18n pt-BR**: 100% das ~5.490 strings de UI traduzidas para português brasileiro (partiu de 27,7% de cobertura).

- **T3 — Maturidade de TSI + Gestão de Terceiros**: jornada guiada única, adaptada do preset NIST CSF 2.0 existente (que já usa o conceito de *Tiers* = maturidade), com a etapa de terceiros aprofundada usando o aparato completo de TPRM.
- **T4 — Rebranding visual**: nome comercial (**CISO TSI**), troca textual (i18n + UI) e identidade visual (ícone, lockup, paleta retonalizada, favicon) implementados.

### 2.2 Pendências residuais (fora do escopo desta rodada)

- ~~Regenerar o `favicon.ico` binário~~ — ✅ resolvido em 2026-08-10.
- ~~Rebuild da imagem Docker do frontend para expor o rebranding/i18n em produção~~ — ✅ resolvido em 2026-08-11 (ver detalhes no [T4](PLAN-BR-T4-REBRANDING.md#6-pendente)).
- Mecanismo de disponibilização de código-fonte exigido pela AGPL, antes do lançamento comercial como SaaS pago.
- Extensão do rebranding textual às ~300 referências fora do escopo aprovado (CI/CD, packaging, `product-docs/`, conectores de terceiros) — decisão de negócio separada.

### 2.3 Fora do escopo (por ora)

- Verticalização por setor regulado (ex.: Resolução CMN 4.658/2018 do Bacen) — descartado nesta rodada; produto mira setor genérico.
- Migração de dados de clientes de outra plataforma.
- Programa de certificação/selo formal para fornecedores avaliados.

## 3. Arquitetura

```
backend/library/libraries/*.yaml   ── conteúdo (frameworks, presets/journeys) ── carregado via StoredLibrary/LoadedLibrary
frontend/messages/{locale}.json    ── i18n (paraglide-js, compilado em build) ── frontend/src/paraglide/
frontend/src/lib/assets/ciso.svg   ── logo (via Logo.svelte) ── frontend/ciso-theme.css (paleta)
```

- Conteúdo de conformidade/journey é **dado**, não código: entra via arquivos YAML na pasta `library/libraries/`, sem alterar o motor do CISO Assistant Community (o código-base sobre o qual o CISO TSI é construído).
- i18n é compilado do JSON de mensagens para funções JS por locale (build time); qualquer alteração de string exige recompilar (`paraglide-js compile`) e, em produção, rebuild da imagem Docker do frontend (que hoje é pré-compilada, sem live-reload do host).
- Rebranding textual (nome "CISO TSI") já aplicado nas 198 strings de i18n e nas 6 strings hardcoded no código fonte; falta a troca de assets estáticos (logo/paleta).

## 4. Riscos e mitigações

| Risco | Mitigação |
|---|---|
| Licença AGPL do CISO Assistant Community poderia restringir o rebranding | **Resolvido**: `LICENSE.md`/`enterprise/LICENSE.md` validados — AGPL permite renomear/revender fora de `enterprise/`, com a obrigação de disponibilizar código-fonte modificado a usuários da rede antes do lançamento comercial |
| T3 depender de framework em inglês (NIST) pode soar "estrangeiro" para o público-alvo | Tropicalizar terminologia e exemplos (trocar CERT NZ/ACSC por ANPD/CERT.br, referenciar LGPD nas obrigações regulatórias) — já decidido no desenho do T3 |
| Rebuild da imagem Docker do frontend é necessário para o cliente ver qualquer mudança de i18n/marca — sem isso, mudanças só existem no repositório | Formalizar pipeline de build/release antes do lançamento comercial (fora do escopo desta rodada de specs) |
| Escopo de 4 frentes distintas (conteúdo, i18n, produto, marca) atrasar lançamento | Frentes já são independentes e paralelizáveis (ver tabela de fases); T1/T2 já entregues provam o padrão |

## 5. Critérios de aceite (do conjunto T1–T4)

1. Produto carrega em pt-BR sem strings em inglês nas telas principais (T2 — já atingido).
2. Cliente brasileiro consegue montar um programa de conformidade LGPD do zero usando apenas o preset (T1 — já validado via `PresetExecutor.apply()`).
3. Cliente consegue, numa jornada única, avaliar maturidade interna de TI/SI e cadastrar/avaliar fornecedores críticos, sem sair do produto (T3).
4. Nenhuma referência a "CISO Assistant" (nome) aparece para o usuário final no texto ou na identidade visual do produto (T4 — concluído).

## 6. Fases de entrega e planos

| Plano | Conteúdo | Depende de |
|---|---|---|
| [T1 — Framework LGPD](PLAN-BR-T1-LGPD-FRAMEWORK.md) | `lgpd.yaml` + `preset-lgpd.yaml` | — |
| [T2 — i18n pt-BR](PLAN-BR-T2-I18N-PTBR.md) | `frontend/messages/pt.json` completo | — |
| [T3 — Maturidade TSI + Terceiros](PLAN-BR-T3-TSI-TERCEIROS.md) | `preset-tsi-terceiros.yaml` | T2 |
| [T4 — Rebranding visual](PLAN-BR-T4-REBRANDING.md) | assets, tema, nome | — |

## 7. Trabalho ao final

- Atualizar este master (§2.1/§2.2) conforme T3/T4 forem concluídos.
- Atualizar `docs/plans/README.md` (tabela de status).
- Validar licenciamento antes de publicar/vender o fork rebrandado (bloqueante para T4).
