// Rapport de constats — français.
// Payload: `core.generators.findings_assessment_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")

#let severity-label = (
  critical: "Critique",
  high: "Élevée",
  medium: "Moyenne",
  low: "Faible",
  info: "Information",
  undefined: "Non définie",
)
// Keyed on the raw value: labels are localised.
#let severity-fill = (
  critical: rgb("#fecaca"),
  high: rgb("#fed7aa"),
  medium: rgb("#fef3c7"),
  low: rgb("#dbeafe"),
  info: rgb("#e0f2fe"),
  undefined: rgb("#f1f5f9"),
)

#let status-label = (
  undefined: "Non défini",
  identified: "Identifié",
  confirmed: "Confirmé",
  assigned: "Assigné",
  in_progress: "En cours",
  mitigated: "Atténué",
  resolved: "Résolu",
  dismissed: "Écarté",
  deprecated: "Déprécié",
  closed: "Clos",
)
#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Rapport de constats], align(right)[#d.assessment.name])
      line(length: 100%, stroke: 0.4pt + muted)
    }
  },
  footer: context {
    set text(8pt, fill: muted)
    grid(
      columns: (1fr, auto),
      d.date, align(right)[#counter(page).display("1 / 1", both: true)],
    )
  },
)
#set text(10pt, lang: "fr")
#set par(justify: true)
#show heading.where(level: 1): set text(15pt, fill: accent)
#show heading.where(level: 2): set text(12pt, fill: accent)

// ---------------------------------------------------------------- cover page

#page(header: none, footer: none)[
  #set par(justify: false)
  #align(center + horizon)[
    #text(26pt, weight: "bold", fill: accent)[#d.assessment.name]
    #v(0.4em)
    #text(14pt, fill: muted)[Rapport de constats — #d.assessment.category]
    #if d.assessment.description != "" [
      #v(0.6em)
      #block(width: 75%)[#text(9.5pt, fill: muted)[#d.assessment.description]]
    ]
    #v(2em)
    #block(width: 75%)[
      #set align(left)
      #set text(10pt)
      #grid(
        columns: (auto, 1fr),
        row-gutter: 8pt,
        column-gutter: 12pt,
        [*Référence*], [#d.assessment.ref_id],
        [*Domaine*], [#d.assessment.folder],
        [*Statut*], [#d.assessment.status],
        [*Auteurs*], [#d.assessment.authors],
        [*Relecteurs*], [#d.assessment.reviewers],
        [*Date*], [#d.date],
      )
      #v(1em)
      #block(width: 100%)[
        #set text(7.5pt, fill: muted)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 3pt,
          column-gutter: 12pt,
          [Généré le], [#d.generated_at],
          [Identifiant du document], [#raw(d.id)],
        )
      ]
    ]
  ]
]

// ------------------------------------------------------------------- summary

= Synthèse

#let m = d.metrics
#grid(
  columns: 4,
  gutter: 1em,
  ..(
    ("Total", m.total, rgb("#e8edf7")),
    ("Ouverts", m.open, rgb("#fee2e2")),
    ("Clos", m.closed, rgb("#dcfce7")),
    ("Importants non résolus", m.unresolved_important, rgb("#fef3c7")),
  ).map(((label, value, fill)) => block(
    fill: fill,
    radius: 4pt,
    inset: 10pt,
    width: 100%,
  )[
    #set align(center)
    #text(8pt, fill: muted)[#label] \
    #text(18pt, weight: "bold")[#value]
  ]),
)

#v(1.2em)
== Gravité

#let peak = calc.max(1, ..d.severity_rows.map(r => r.count))
#for row in d.severity_rows [
  #grid(
    columns: (3cm, 1fr, 1.2cm),
    gutter: 6pt,
    align(right)[#severity-label.at(row.key)],
    box(width: 100%, height: 10pt)[
      #place(
        left,
        rect(
          width: row.count / peak * 100%,
          height: 10pt,
          fill: severity-fill.at(row.key),
          radius: 2pt,
        ),
      )
    ],
    align(right)[#row.count],
  )
  #v(2pt)
]

#if d.assessment.observation != "" [
  #v(0.8em)
  == Observation
  #d.assessment.observation
]

// ------------------------------------------------------------------ findings

#pagebreak(weak: true)
= Constats

#for group in d.groups [
  #block(above: 1.2em, below: 0.4em)[
    #text(12pt, weight: "bold", fill: accent)[
      #severity-label.at(group.severity_key)
    ]
    #text(10pt, fill: muted)[ (#group.findings.len())]
  ]

  #for finding in group.findings [
    #block(
      breakable: true,
      width: 100%,
      above: 0.8em,
      inset: (bottom: 0.6em),
      stroke: (bottom: 0.4pt + rule),
    )[
      #grid(
        columns: (1fr, auto),
        gutter: 8pt,
        text(weight: "bold")[#finding.ref_id — #finding.name],
        box(
          fill: severity-fill.at(finding.severity_key),
          inset: (x: 5pt, y: 2pt),
          radius: 3pt,
        )[#text(8pt)[#status-label.at(finding.status_key, default: finding.status_key)]],
      )
      #set text(9pt)
      #v(3pt)
      // Deux lignes : une liste de responsables longue chevaucherait.
      #grid(
        columns: (2.6cm, 1fr),
        column-gutter: 6pt,
        row-gutter: 2pt,
        text(fill: muted)[Responsable], [#finding.owners],
        text(fill: muted)[Échéance / Limite], [#finding.eta — #finding.due_date],
      )
      #if finding.description != "" [
        #v(3pt)
        #text(fill: muted)[#finding.description]
      ]
      #if finding.observation != "" [
        #v(2pt)
        *Observation :* #finding.observation
      ]
      #if finding.controls.len() > 0 [
        #v(2pt)
        #text(8pt, fill: accent)[Mesures appliquées : #finding.controls.join(", ")]
      ]
      #if finding.evidences.len() > 0 [
        #v(2pt)
        #text(8pt, fill: accent)[Preuves : #finding.evidences.join(", ")]
      ]
      #if finding.labels.len() > 0 [
        #v(3pt)
        // One line: a newline here would end the expression.
        #finding.labels.map(label => box(
          fill: rgb("#dbeafe"),
          inset: (x: 5pt, y: 2pt),
          radius: 3pt,
        )[#text(7.5pt, fill: rgb("#1e40af"))[#label]]).join(h(3pt))
      ]
    ]
  ]
]
