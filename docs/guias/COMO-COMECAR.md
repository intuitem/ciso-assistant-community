# Como começar — Guia de configuração inicial do CISO TSI

**Público:** administradores que estão configurando o CISO TSI pela primeira vez para uma organização.
**Baseado em:** [`product-docs/guides/`](../../product-docs/guides/) (documentação oficial upstream da Intuitem, em inglês), adaptado e consolidado em português para o fluxo do CISO TSI.

---

## 1. Primeiro acesso

1. Acesse a URL do seu ambiente CISO TSI (ex.: `https://localhost:8443` em ambiente local).
2. Se for a primeira vez que o sistema roda, será necessário um usuário administrador (superusuário). Isso é criado via variável de ambiente `DJANGO_SUPERUSER_EMAIL`/`DJANGO_SUPERUSER_PASSWORD` no backend, ou já existe se o ambiente foi herdado de uma configuração anterior.
3. Faça login. Se for seu primeiro acesso com um convite, o fluxo de "primeira conexão" (`/first-connexion`) pede para você definir sua senha.

## 2. Estrutura organizacional: domínios, perímetros e usuários

O CISO TSI organiza tudo dentro de **domínios** (áreas/unidades da organização) e, dentro deles, **perímetros** (o que antes se chamava "projetos" — o escopo concreto que será avaliado em auditorias e análises de risco).

1. Vá em **Organização → Domínios** e crie um domínio (ex.: o nome da sua empresa ou de uma unidade de negócio).
2. Dentro do domínio, crie um **perímetro** (ex.: "Operação Principal", "Produto X") — é o que vai ser avaliado.
3. Vá em **Organização → Usuários** e convide os usuários da sua equipe, atribuindo um papel (ex.: Analista, Administrador de domínio) por domínio.

> Dica: comece simples — um domínio e um perímetro já bastam para o primeiro ciclo. Você expande a estrutura depois, conforme a necessidade.

## 3. Importar frameworks e matrizes de risco

Antes de avaliar qualquer coisa, importe o conteúdo de referência que você vai usar:

1. Vá em **Catálogo → Frameworks** e importe os frameworks relevantes. Para o mercado brasileiro, priorize:
   - **LGPD** (Lei 13.709/2018) — framework de conformidade completo já incluído no CISO TSI.
   - Frameworks internacionais conforme necessidade (ex.: ISO/IEC 27001:2022, NIST CSF 2.0).
2. Vá em **Catálogo → Matrizes de risco** e importe ao menos uma matriz (ex.: a matriz crítica padrão), necessária para qualquer análise de risco.
3. Se for usar mapeamentos entre frameworks (ex.: para evitar retrabalho de evidências entre LGPD e ISO 27001), importe também os **mappings** disponíveis no catálogo.

## 4. Primeira auditoria (conformidade)

1. Com um framework já importado (ex.: LGPD), crie uma **auditoria** dentro do perímetro.
2. Cada requisito do framework começa com status "A fazer".
3. Avalie requisito por requisito: associe **controles aplicados** e **evidências**, e atualize o status conforme o progresso.
4. Acompanhe a barra de progresso da auditoria — ela reflete o quanto da conformidade já foi endereçado.

## 5. Primeira análise de risco

1. Importe os objetos de apoio necessários: uma **matriz de risco**, uma lista de **ameaças** e uma lista de **controles de referência** (pode vir de biblioteca ou ser customizada).
2. Crie a **análise de risco** dentro do perímetro.
3. Adicione um **cenário de risco**: descreva a ameaça, faça a avaliação atual (probabilidade × impacto).
4. Se for mitigar o cenário, associe um **controle aplicado** e refaça a avaliação — agora como **avaliação residual** (o risco depois da mitigação), indicando o nível de confiança da avaliação ("strength of knowledge").

## 6. Diferenciais do CISO TSI: maturidade de TI/SI + Gestão de Terceiros

Além do fluxo padrão de auditoria/risco acima, o CISO TSI já vem com uma **jornada guiada própria** (preset "TSI + Terceiros", ver [PLAN-BR-T3](../plans/PLAN-BR-T3-TSI-TERCEIROS.md)) que combina:

- Avaliação de maturidade interna de TI/Segurança da Informação (baseada em *Tiers*, adaptado do NIST CSF 2.0).
- Avaliação aprofundada de fornecedores críticos (TPRM — Third-Party Risk Management), no mesmo fluxo, sem precisar sair do produto.

Para usar: importe o preset correspondente no Catálogo e siga a jornada guiada — ela já vem com a estrutura de perguntas e etapas pré-configurada, então você não precisa montar do zero.

## 7. Boas práticas gerais (para quem está começando)

Adaptado de [`product-docs/guides/general-tips.md`](../../product-docs/guides/general-tips.md):

1. Mapeie sua organização em domínios e perímetros (comece simples).
2. Cadastre seus usuários e organize por grupos/papéis (SSO e MFA estão disponíveis mesmo na edição Community).
3. *(recomendado)* Identifique os ativos a proteger.
4. *(recomendado)* Liste as capacidades e controles que você já tem.
5. Defina sua linha de base — escolha ou crie os controles principais.
6. Coloque as ações em prática e reflita isso no progresso das auditorias.
7. Conduza uma análise de risco contextual.
8. Compartilhe os resultados com a organização, revise prioridades, e mantenha o processo vivo.
9. Expanda a cobertura aos poucos: tarefas periódicas, incidentes, risco de terceiros, gestão de achados (findings).
10. Mantenha o foco nas ações — e reflita os dados delas nos outros conceitos do sistema.

## 8. Onde encontrar mais

- Documentação completa (em inglês, upstream): menu "Sobre" → **Documentação online**, ou [`product-docs/`](../../product-docs/) neste repositório.
- Código-fonte da versão CISO TSI: menu "Sobre" → **Código-fonte** (ver [PLAN-BR-T5](../plans/PLAN-BR-T5-AGPL-COMPLIANCE.md)).
- Planos de tropicalização do produto para o Brasil: [`docs/plans/PLAN-BR-MASTER.md`](../plans/PLAN-BR-MASTER.md).
