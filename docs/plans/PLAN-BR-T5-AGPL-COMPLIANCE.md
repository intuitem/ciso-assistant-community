# PLAN-BR-T5 — Conformidade AGPL (disponibilização de código-fonte)

**Status:** ✅ Concluído (2026-08-13)
**Relacionado:** [PLAN-BR-MASTER.md](PLAN-BR-MASTER.md), [PLAN-BR-T4-REBRANDING.md](PLAN-BR-T4-REBRANDING.md), [design spec](../superpowers/specs/2026-08-13-agpl-source-disclosure-design.md)

## 1. Objetivo

Implementar o mecanismo de disponibilização de código-fonte exigido pela AGPLv3 §13 para o CISO TSI, fechando a última pendência bloqueante identificada em `PLAN-BR-T4-REBRANDING.md` §3/§6 antes de qualquer lançamento comercial como SaaS pago.

## 2. Obrigação da AGPL (em termos práticos)

O CISO Assistant Community é licenciado sob AGPLv3 fora de `enterprise/`. Rodar uma versão modificada ("CISO TSI") e permitir que usuários interajam com ela pela rede exige, pela AGPLv3 §13:

1. Preservar os avisos de copyright e licença nos arquivos originais.
2. Manter o texto da licença disponível (já preservado: `LICENSE.md`, `LICENSE-AGPL.txt`).
3. Oferecer, de forma acessível a qualquer usuário que interaja com o sistema pela rede, uma forma de obter o **"Corresponding Source"** — o código-fonte completo, com as modificações, da versão exata que está rodando.

## 3. Mecanismo implementado

- **Repositório-fonte**: o fork público já existente, `https://github.com/tarcisiolisboayamada/ciso-assistant-community`, branch `ciso-tsi`, é a fonte oficial disponibilizada. Nenhum repositório dedicado adicional foi criado (decisão consciente — ver design spec §3).
- **Link na UI**: item "Código-fonte" adicionado ao menu "Sobre" (`frontend/src/lib/components/SideBar/SideBarFooter.svelte`), ao lado do link "Documentação online" já existente, apontando para `https://github.com/tarcisiolisboayamada/ciso-assistant-community/tree/ciso-tsi`. Visível para usuários autenticados não-terceiros (mesma regra de visibilidade do menu "Sobre").
- **i18n**: chave `sourceCode` adicionada em `frontend/messages/en.json` ("Source code") e `frontend/messages/pt.json` ("Código-fonte"); fallback automático do paraglide para os demais 23 locales.

## 4. Regra de processo — sincronia obrigatória

**Sempre `git push fork main:ciso-tsi` ANTES de qualquer rebuild/deploy de imagem Docker para produção.**

O link na UI é estático e aponta para o HEAD do branch `ciso-tsi`. Isso só cumpre a AGPL se esse HEAD corresponder exatamente ao código rodando. Não há automação de CI para isso nesta rodada — é disciplina manual, documentada aqui para não depender de memória.

### Checklist de release

1. Commitar as mudanças localmente (`git commit`).
2. **Enviar para o fork público**: `git push fork main:ciso-tsi`.
3. Só então buildar a imagem Docker: `docker compose -f docker-compose-build.yml build frontend` (e/ou `backend`, se houver mudança de backend).
4. Recriar o(s) container(s) em produção com a imagem nova.
5. Confirmar visualmente: o link "Código-fonte" no menu "Sobre" deve apontar para um commit que já está publicado no fork antes do deploy ir ao ar.

Se esse checklist não for seguido (deploy antes do push), o link fica temporariamente incorreto — deploy sem publicar antes é uma violação técnica da AGPL §13, não apenas um descuido de processo.

## 5. Critérios de aceite

1. Link "Código-fonte" visível no menu "Sobre". ✅
2. Link aponta para o branch público correto. ✅
3. Chaves i18n `sourceCode` presentes em `en.json`/`pt.json`. ✅
4. Regra de sincronia documentada e checklist de release definido. ✅
5. Pendência #3 de `PLAN-BR-T4-REBRANDING.md` §6 e pendência equivalente em `PLAN-BR-MASTER.md` §2.2 marcadas como resolvidas.
