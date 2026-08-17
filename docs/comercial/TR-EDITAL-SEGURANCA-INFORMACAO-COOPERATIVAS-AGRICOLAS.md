# Termo de Referência — Solução de Governança, Risco e Conformidade (GRC) em Segurança da Informação para Cooperativas Agrícolas

**Tipo de documento:** Termo de Referência (TR) — modelo genérico, para adaptação a editais/processos de contratação específicos.
**Solução de referência:** CISO TSI (plataforma de GRC white-label, baseada em CISO Assistant Community, licença AGPLv3).
**Status:** minuta para revisão — campos entre colchetes `[ ]` devem ser preenchidos/ajustados para cada processo específico.

---

## 1. Objeto

Contratação de solução de software para **Gestão de Governança, Riscos e Conformidade (GRC) em Segurança da Informação**, incluindo licenciamento, implantação, capacitação e suporte técnico, destinada a apoiar a cooperativa **[NOME DA COOPERATIVA]** na estruturação, execução e monitoramento contínuo de seu programa de segurança da informação e proteção de dados pessoais.

## 2. Justificativa da Contratação

### 2.1 Contexto do setor

Cooperativas agrícolas ocupam posição crítica na cadeia produtiva do agronegócio brasileiro, concentrando um volume significativo de dados sensíveis: informações pessoais e financeiras de cooperados (CPF, dados bancários, histórico de produção e propriedades rurais), dados operacionais de produção, logística e comercialização, e, em cooperativas com operação de crédito, dados de natureza financeira sujeitos a regramento adicional.

A digitalização crescente do setor — sistemas de gestão (ERP), plataformas de agricultura de precisão, sensores de IoT em campo, portais para cooperados e integrações com fornecedores e compradores — amplia continuamente a superfície de exposição a incidentes cibernéticos. O setor agropecuário brasileiro tem registrado aumento expressivo de ataques de ransomware e vazamento de dados nos últimos anos, com impacto direto em continuidade operacional e na relação de confiança com os cooperados.

### 2.2 Obrigações legais

A **Lei Geral de Proteção de Dados (LGPD — Lei nº 13.709/2018)** aplica-se integralmente às cooperativas, que atuam como controladoras de dados pessoais de seus cooperados, colaboradores e parceiros. O não atendimento aos requisitos da LGPD expõe a cooperativa a sanções administrativas (multas de até 2% do faturamento, limitadas a R$ 50 milhões por infração), além de risco reputacional perante a base de cooperados.

Cooperativas com operações de crédito ou correspondência bancária estão adicionalmente sujeitas a regulamentação setorial específica de segurança cibernética e continuidade de negócios — cuja avaliação de aderência deve ser tratada em processo específico, complementar a este TR, dado que esta contratação tem escopo de aplicação geral.

### 2.3 Lacuna atual e necessidade

Atualmente, a gestão de segurança da informação e de conformidade com a LGPD é conduzida de forma fragmentada (planilhas, documentos avulsos, controles não centralizados), sem rastreabilidade adequada, sem visão consolidada de risco, e sem processo estruturado de avaliação e acompanhamento de fornecedores críticos (insumos, tecnologia, logística) — elo frequentemente negligenciado, mas de alto impacto potencial na cadeia de risco da cooperativa.

Justifica-se, portanto, a contratação de solução especializada que centralize a gestão de conformidade regulatória, avaliação e tratamento de riscos, gestão de auditorias e avaliação de terceiros, com trilha de evidências auditável.

## 3. Descrição da Solução

A solução deve ser uma **plataforma de GRC em Segurança da Informação**, com as seguintes capacidades centrais:

1. **Gestão de conformidade regulatória**, com biblioteca de frameworks pré-carregada incluindo, no mínimo, a **LGPD** de forma nativa e completa (todos os capítulos e requisitos da Lei 13.709/2018), permitindo à cooperativa conduzir auditorias internas de aderência, atribuir responsáveis, associar controles e evidências, e acompanhar o progresso de forma quantitativa.
2. **Gestão de riscos de segurança da informação**, com suporte a matrizes de risco configuráveis, catálogo de ameaças, cenários de risco, avaliação atual e residual (pré e pós-mitigação), e associação de controles aplicados.
3. **Avaliação de maturidade de TI/Segurança da Informação**, com jornada estruturada baseada em níveis de maturidade (*tiers*), permitindo à cooperativa autodiagnosticar seu estágio de maturidade e priorizar investimentos.
4. **Gestão de risco de terceiros (TPRM — Third-Party Risk Management)**, com cadastro e avaliação de fornecedores e parceiros críticos, integrada ao mesmo fluxo de trabalho da avaliação de maturidade interna — sem necessidade de ferramenta separada.
5. **Gestão de auditorias e planos de ação**, com trilha de evidências, controles aplicados, responsáveis e prazos.
6. **Painéis gerenciais (dashboards)** com indicadores de conformidade, risco e progresso, para apoio à tomada de decisão pela direção/conselho da cooperativa.

## 4. Requisitos Técnicos

### 4.1 Requisitos funcionais

| # | Requisito |
|---|---|
| RF01 | Biblioteca de conformidade nativa da LGPD (Lei 13.709/2018), com todos os requisitos legais mapeados e atualizável conforme mudanças normativas. |
| RF02 | Suporte à importação de frameworks e normas adicionais (ex.: ISO/IEC 27001, NIST CSF), com possibilidade de mapeamento cruzado entre frameworks para reaproveitamento de evidências. |
| RF03 | Gestão de matrizes de risco configuráveis (probabilidade × impacto), com suporte a avaliação qualitativa e quantitativa. |
| RF04 | Cadastro e avaliação de cenários de risco, com histórico de avaliação atual e residual. |
| RF05 | Módulo de avaliação de maturidade de TI/Segurança da Informação, baseado em níveis/tiers, com jornada guiada. |
| RF06 | Módulo de gestão de risco de terceiros/fornecedores (TPRM), com cadastro de entidades externas, questionários de avaliação e classificação de criticidade. |
| RF07 | Gestão de controles aplicados, com responsável, prazo, status e evidências anexadas. |
| RF08 | Estrutura organizacional hierárquica (domínios/unidades e perímetros/escopos de avaliação), compatível com a estrutura de uma cooperativa (matriz, filiais, unidades de negócio). |
| RF09 | Controle de usuários e permissões por papel (RBAC), com suporte a múltiplos perfis (administrador, gestor de domínio, analista, auditor, terceiro externo). |
| RF10 | Painéis gerenciais com indicadores de conformidade, risco e progresso de auditorias. |
| RF11 | Interface em **português do Brasil**, sem necessidade de tradução manual pela cooperativa. |

### 4.2 Requisitos de segurança

| # | Requisito |
|---|---|
| RS01 | Autenticação multifator (MFA). |
| RS02 | Suporte a autenticação federada / Single Sign-On (SSO), compatível com protocolos padrão de mercado. |
| RS03 | Controle de acesso baseado em papéis (RBAC), com princípio de menor privilégio. |
| RS04 | Registro de auditoria (audit log) de ações realizadas na plataforma, com rastreabilidade de usuário, ação e data/hora. |
| RS05 | Criptografia de dados em trânsito (TLS) e em repouso. |
| RS06 | Política de senhas configurável e mecanismo de expiração/reset seguro de credenciais. |

### 4.3 Requisitos de hospedagem e soberania de dados

| # | Requisito |
|---|---|
| RH01 | Possibilidade de hospedagem em território nacional (data center no Brasil) ou em ambiente on-premise/self-hosted controlado pela própria cooperativa, atendendo a requisitos de soberania de dados. |
| RH02 | Backup periódico dos dados, com procedimento documentado de restauração. |
| RH03 | Plano de continuidade/disponibilidade compatível com a criticidade da informação tratada. |

### 4.4 Requisitos de interoperabilidade

| # | Requisito |
|---|---|
| RI01 | Disponibilização de API para integração com sistemas corporativos da cooperativa (ex.: ERP, diretório de usuários). |
| RI02 | Exportação de dados e relatórios em formatos abertos (ex.: CSV, PDF, JSON). |
| RI03 | Suporte à importação de dados estruturados (ex.: planilhas de cadastro de ativos, fornecedores) para migração inicial. |

### 4.5 Requisitos de suporte, capacitação e transparência

| # | Requisito |
|---|---|
| RT01 | Capacitação inicial da equipe técnica e dos usuários-chave da cooperativa na utilização da plataforma. |
| RT02 | Suporte técnico durante a vigência do contrato, com prazo de atendimento definido em Acordo de Nível de Serviço (SLA) — a especificar em `[SLA a definir]`. |
| RT03 | Documentação de uso disponível em português. |
| RT04 | **Transparência de código-fonte**: a solução deve ser baseada em software com código-fonte auditável e disponível, permitindo à cooperativa verificar de forma independente os controles de segurança implementados e evitar dependência exclusiva (*vendor lock-in*) de um único fornecedor proprietário fechado. |

## 5. Benefícios Esperados

1. **Conformidade com a LGPD**: redução do risco de sanções administrativas e de incidentes envolvendo dados pessoais de cooperados, colaboradores e parceiros, por meio de um processo estruturado e auditável de gestão de conformidade.
2. **Redução de risco cibernético**: identificação, avaliação e tratamento sistemático de riscos de segurança da informação, reduzindo a probabilidade e o impacto de incidentes (ex.: ransomware, vazamento de dados) que possam comprometer a operação da cooperativa.
3. **Gestão de risco de terceiros**: visibilidade e controle sobre fornecedores e parceiros críticos (insumos, tecnologia, logística), historicamente um elo frágil na cadeia de risco de organizações do agronegócio.
4. **Governança e rastreabilidade**: trilha de evidências auditável para apoiar prestação de contas ao conselho de administração, ao conselho fiscal e, quando aplicável, a órgãos reguladores e certificadores.
5. **Maturidade organizacional**: diagnóstico objetivo do estágio de maturidade em segurança da informação, permitindo priorização racional de investimentos e evolução contínua e mensurável.
6. **Centralização e eficiência**: substituição de controles fragmentados (planilhas, documentos avulsos) por uma plataforma única, reduzindo retrabalho e risco de perda de informação.
7. **Apoio à tomada de decisão**: painéis gerenciais que traduzem o estado de conformidade e risco em indicadores acessíveis à liderança da cooperativa, não apenas à equipe técnica.
8. **Redução de dependência tecnológica**: por se basear em software com código-fonte disponível, a cooperativa preserva capacidade de auditoria independente e de continuidade operacional mesmo em cenário de descontinuidade do fornecedor.

## 6. Modelo de Execução (resumo)

1. **Fase de implantação** `[prazo a definir, ex.: até 30 dias corridos]`: parametrização inicial (estrutura organizacional, importação de frameworks, cadastro de usuários).
2. **Fase de capacitação** `[prazo a definir]`: treinamento da equipe técnica e dos usuários-chave.
3. **Fase de operação assistida** `[prazo a definir]`: acompanhamento do primeiro ciclo de auditoria e avaliação de risco, com suporte técnico ativo.
4. **Operação continuada**: suporte técnico e atualização da biblioteca de conformidade (incluindo mudanças na legislação da LGPD) durante toda a vigência contratual.

## 7. Critérios de Aceitação

1. Ambiente disponível e acessível aos usuários designados pela cooperativa.
2. Estrutura organizacional (domínios/perímetros) da cooperativa corretamente parametrizada.
3. Framework LGPD importado e disponível para uso imediato.
4. Ao menos um ciclo completo de auditoria de conformidade e uma avaliação de risco realizados com sucesso durante a fase de operação assistida, validando a funcionalidade fim a fim da solução.
5. Capacitação realizada e registrada (lista de presença/certificado).

## 8. Vigência e Valor Estimado

`[Campos a preencher conforme o processo específico: prazo de vigência contratual, valor estimado com base em pesquisa de mercado, dotação orçamentária.]`

---

**Nota metodológica:** este TR foi elaborado como modelo genérico de referência técnica. Recomenda-se revisão jurídica e adequação aos requisitos formais da Lei nº 14.133/2021 (Nova Lei de Licitações) e às normas internas da cooperativa antes da publicação em processo de contratação formal.
