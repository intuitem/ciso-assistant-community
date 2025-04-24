# CreateModal ordering

### Table of contents

<hr>

<!--toc:start-->
- [CreateModal ordering](#createmodal-ordering)
  - [General rules](#general-rules)
  - [Rules for forms with More section](#rules-for-forms-with-more-section)
  - [Exceptions](#exceptions)
    - [AppliedControlPolicyForm](#appliedcontrolpolicyform)
    - [RepresentativeForm](#representativeform)
    - [FilteringLabelsForm](#filteringlabelsform)
<!--toc:end-->
<hr>
Numbered fields follow a precise order, as well as 'specific fields'.

> [!IMPORTANT]  
> 'Specific fields' are fields that aren't numbered and have parenthesis in the beginning. These are fields that are specific to only one model which is indicated in parenthesis.
>
> E.g. "(assets) Security objectives"

> [!NOTE]  
> Categories are only here to differentiate each block of fields, it is not needed to show them on Forms.

##  General rules

#### Unique & frequents

1) Name
2) Description
3) Email
4) Reference ID
5) Domain
6) Perimeter

#### Related users

7) Owner(s)
8) Author(s)
9) Reviewer(s)
10) Approver(s)
11) Representative(s)
12) Provider(s)

#### Versioning & Classification

13) Version
14) Category
15) CSF Function

- (assets) Type
- (assets) Security objectives
- (assets) Disaster Recovery objectives
- (compliance assessments) Suggest controls
- (compliance assessments) Use documentation score
- (evidences) Attachments
- (entities) Mission
- (entity assessment) Create audit

#### Priority & Status

16) Priority
17) Status
18) Progress
19) Severity
20) Criticality

#### Resource & Cost

21) Effort
22) Cost

#### Other foreign keys

*All foreign keys not specified elsewhere must be placed here.
The order used here is the order of appearance in the navbar, this can be adapted depending on the form*

- Asset(s)
- Target framework / Framework
- Threat(s)
- Reference control
- Risk matrix
- Applied control(s)
- Exception(s)
- Risk assessment
- Risk scenario(s)
- Audit
- Evidence(s)
- Entity / Provider entity
- Solution(s)
- Label(s)
- (audits) Selected implementation groups

#### Dates & Deadlines

23) ETA
24) Due date
25) Start date
26) Expiry date
27) Expiration date

#### Additional

- (entity assessment) Conclusion

28) Link / Reference link
29) Annotation
30) Observation

## Rules for forms with More section

Forms that have a "More" section should follow this order :

#### Unique & frequents

1) Name
2) Description
3) Domain
4) Perimeter

#### Related users

5) Owner(s)
6) Author(s)

- (assets) Type
- (evidences) Attachments

#### Priority & Status

7) Priority
8) Status
9) Progress
10) Severity
11) Criticality

#### Dates & Deadlines

12) ETA

<details>

  <summary>More section</summary>

#### Unique & frequents

1) Email
2) Reference ID

#### Related users

3) Reviewer(s)
4) Approver(s)
5) Representative(s)
6) Provider(s)

#### Versioning & Classification

7) Version
8) Category
9) CSF Function

- (assets) Security objectives
- (assets) Disaster Recovery objectives
- (compliance assessments) Suggest controls
- (compliance assessments) Use documentation score
- (entities) Mission
- (entity assessment) Create audit

#### Resource & Cost

10) Effort
11) Cost

#### Other foreign keys

*All foreign keys not specified elsewhere must be placed here.
The order used here is the order of appearance in the navbar, this can be adapted depending on the form*

- Asset(s)
- Target framework / Framework
- Threat(s)
- Reference control
- Risk matrix
- Applied control(s)
- Exception(s)
- Risk assessment
- Risk scenario(s)
- Audit
- Evidence(s)
- Entity / Provider entity
- Solution(s)
- Label(s)
- (audits) Selected implementation groups

#### Dates & Deadlines

12) Due date
13) Start date
14) Expiry date
15) Expiration date

#### Additional

- (entity assessment) Conclusion

16) Link / Reference link
17) Annotation
18) Observation

</details>

## Exceptions

Some forms are very specific, so here is how they should look:

#### AppliedControlPolicyForm

The "reference control" field should be at the very top.
Other fields follow the general rules.

#### RepresentativeForm

1) Description
2) Email
3) Create user
4) Entity
5) First name
6) Last name
7) Phone
8) Role

#### FilteringLabelsForm

1) Label
