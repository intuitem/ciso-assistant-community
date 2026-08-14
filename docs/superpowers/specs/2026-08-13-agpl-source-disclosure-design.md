# AGPL Source-Disclosure Mechanism — Design

**Data:** 2026-08-13
**Status:** Aprovado
**Relacionado:** [PLAN-BR-MASTER.md](../../plans/PLAN-BR-MASTER.md), [PLAN-BR-T4-REBRANDING.md](../../plans/PLAN-BR-T4-REBRANDING.md)

## 1. Problema

O CISO TSI é um fork comercial do CISO Assistant Community, licenciado sob AGPLv3 (fora de `enterprise/`). A AGPLv3 §13 exige que qualquer usuário que interaja com o sistema pela rede tenha uma forma de obter o "Corresponding Source" — o código-fonte exato (com modificações) da versão rodando. Esse mecanismo ainda não existe: a UI não oferece nenhum link para o código-fonte modificado, e não há uma regra de processo garantindo que a versão publicada bata com a versão deployada. Isso é um item bloqueante antes do lançamento comercial (SaaS pago), conforme já identificado em `PLAN-BR-T4-REBRANDING.md` §3 e §6.

## 2. Escopo

Implementar o mecanismo mínimo viável de disponibilização de código-fonte: reaproveitar o fork público já existente, adicionar um link visível na UI, e formalizar a disciplina de processo que mantém esse link correto. Fora de escopo: automação de CI/tagging por versão, repositório dedicado separado, cobertura de usuários não autenticados (login/first-connexion).

## 3. Mecanismo (arquitetura)

- **Repositório-fonte**: o fork público já existente, `https://github.com/tarcisiolisboayamada/ciso-assistant-community`, branch `ciso-tsi`, continua sendo a fonte oficial disponibilizada — sem repositório dedicado adicional.
- **Sincronia**: manual, por disciplina de processo — `git push fork main:ciso-tsi` deve acontecer **antes** de qualquer rebuild/deploy de imagem Docker para produção. Sem automação de CI nesta rodada (o produto ainda não está em produção real).
- **Link na UI**: estático, apontando para o branch `ciso-tsi` (HEAD) — não precisa ser dinâmico por commit/tag, já que a sincronia manual garante que o HEAD do branch público corresponde ao que está deployado.

## 4. Mudança de UI

Arquivo: `frontend/src/lib/components/SideBar/SideBarFooter.svelte`.

No menu "Sobre" existente (acionado pelo botão de reticências no rodapé da sidebar), ao lado do link já existente "Online documentation" (linha ~139-144), adicionar um novo item:

```svelte
<a
	href="https://github.com/tarcisiolisboayamada/ciso-assistant-community/tree/ciso-tsi"
	target="_blank"
	class="unstyled cursor-pointer flex items-center gap-2 w-full px-4 py-2.5 text-left text-sm hover:bg-surface-200-800 disabled:text-surface-400-600 text-surface-950-50"
	data-testid="source-code-button"
	><i class="fa-solid fa-code mr-2"></i>{m.sourceCode()}</a
>
```

- Nova chave i18n `sourceCode`: `"Source code"` em `frontend/messages/en.json`, `"Código-fonte"` em `frontend/messages/pt.json`. Paraglide faz fallback para inglês nos outros 23 locales (mesmo padrão usado no rebranding do T4).
- Herda a mesma visibilidade do menu "Sobre" atual (`!page.data?.user?.is_third_party`) — usuários autenticados, exceto terceiros. Cobertura de usuários não autenticados (login) fica fora de escopo por decisão do usuário.
- Nenhuma mudança de backend necessária — o link é estático, não depende do endpoint `/fe-api/build`.

## 5. Documentação do processo

Novo arquivo `docs/plans/PLAN-BR-T5-AGPL-COMPLIANCE.md`, seguindo o padrão dos planos T1–T4 existentes, contendo:

1. A obrigação da AGPL §13 em termos práticos: preservar avisos de copyright/licença nos arquivos originais, manter o texto da licença disponível, disponibilizar o "Corresponding Source" para usuários que interagem pela rede.
2. A regra de processo: sempre `git push fork main:ciso-tsi` antes de qualquer rebuild/deploy de imagem Docker para produção.
3. Checklist de release (passo a passo) cobrindo a ordem correta: commit → push para o fork → build da imagem → deploy.
4. Nota explícita marcando como resolvida a pendência #3 de `PLAN-BR-T4-REBRANDING.md` §6 e a pendência residual equivalente em `PLAN-BR-MASTER.md` §2.2.

`PLAN-BR-MASTER.md` §6 (tabela de fases) ganha uma linha para o T5.

## 6. Testes

- `svelte-check` no arquivo alterado (mesma prática usada no T4 visual).
- Verificação manual no navegador: menu "Sobre" mostra o novo item, o link abre em nova aba e aponta para a URL correta.
- Não é necessário teste E2E novo (link estático, sem lógica condicional além da visibilidade já testada do menu).

## 7. Critérios de aceite

1. Link "Código-fonte" visível no menu "Sobre" para usuários autenticados não-terceiros.
2. Link aponta para `https://github.com/tarcisiolisboayamada/ciso-assistant-community/tree/ciso-tsi`.
3. `docs/plans/PLAN-BR-T5-AGPL-COMPLIANCE.md` criado e referenciado no master.
4. Pendência da AGPL marcada como resolvida em `PLAN-BR-T4-REBRANDING.md` e `PLAN-BR-MASTER.md`.
