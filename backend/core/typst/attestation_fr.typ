// Attestation à contresigner — français.
// Payload: `core.generators.audit_context_for_typst` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
#let shown(key) = key not in d.hidden_fields
#let chart(name) = if name + ".png" in d.charts { image(name + ".png", width: 100%) }

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let result-label = (
  compliant: "Conforme",
  partially_compliant: "Partiellement conforme",
  non_compliant: "Non conforme",
  not_applicable: "Non applicable",
  not_assessed: "Non évaluée",
)
// Keyed on the raw value: labels are localised.
#let result-color(key) = (
  compliant: rgb("#dcfce7"),
  partially_compliant: rgb("#fef3c7"),
  non_compliant: rgb("#fee2e2"),
).at(key, default: rgb("#f1f5f9"))

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(
        columns: (1fr, auto),
        d.audit.name, align(right)[#d.audit.framework.name],
      )
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
#set text(10pt, lang: "en")
#set par(justify: true)
#show heading.where(level: 1): set text(15pt, fill: accent)
#show heading.where(level: 2): set text(12pt, fill: accent)

// ---------------------------------------------------------------- cover page

#let party = d.at("counterparty", default: none)

#page(header: none, footer: none)[
  // Ragged: justified metadata hyphenates addresses.
  #set par(justify: false)
  #align(center + horizon)[
    #text(26pt, weight: "bold", fill: accent)[#d.audit.name]
    #v(0.4em)
    #text(14pt, fill: muted)[#d.audit.framework.name]
    #if d.audit.framework.description != "-" [
      #v(0.4em)
      #block(width: 75%)[
        #set text(9.5pt, fill: muted)
        #set par(justify: false)
        #align(center)[#d.audit.framework.description]
      ]
    ]
    #v(2em)
    #block(width: 75%)[
      #set align(left)
      #set text(10pt)
      #if party != none [
        #grid(
          columns: (auto, 1fr),
          row-gutter: 8pt,
          column-gutter: 12pt,
          [*Entité évaluée*],
          [
            #party.entity#if party.ref_id != "" [ (#party.ref_id)]
            #if party.address != "" [
              \ #text(fill: muted)[#party.address.replace("\n", ", ")]
            ]
          ],
          ..if party.legal_identifiers.len() > 0 {
            (
              [*Identifiants légaux*],
              party
                .legal_identifiers
                .map(pair => [#pair.label: #pair.value])
                .join(" · "),
            )
          } else { () },
          ..if party.expiry_date != "-" {
            ([*Date d'expiration*], [#party.expiry_date])
          } else { () },
        )
        #v(0.6em)
        #line(length: 100%, stroke: 0.4pt + rgb("#e5e7eb"))
        #v(0.6em)
      ]
      #grid(
        columns: (auto, 1fr),
        row-gutter: 8pt,
        column-gutter: 12pt,
        [*Référence*], [#field(d.audit, "ref_id")],
        [*Date*], [#d.date],
        [*Groupes d'implémentation*], [#if d.igs != "" { d.igs } else { "Tous" }],
        [*Contributeurs*], [#d.contributors.replace("\n", ", ")],
      )
      #v(1em)
      #block(width: 100%)[
        #set text(7.5pt, fill: muted)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 3pt,
          column-gutter: 12pt,
          [Généré le], [#d.generated_at],
          [Identifiant du document], [#raw(d.audit.id)],
        )
      ]
    ]
  ]
]

// ------------------------------------------------------------------- summary

#let r = d.at("req", default: none)
#let total = if r != none { field(r, "total", fallback: 0) } else { 0 }

#if d.audit.description != "-" [
  == Périmètre
  #d.audit.description
]

#let drifts = field(d, "drifts_per_domain", fallback: ())
// -------------------------------------------------------------- category view

#let categories = field(d, "category_scores", fallback: (:))
// ------------------------------------------------------------------ controls

#let p1 = field(d, "p1_controls", fallback: ())
// ------------------------------------------------------- detailed assessment

#pagebreak(weak: true)
= Résultats détaillés

#let ras = field(d, "requirement_assessments", fallback: ())
#text(fill: muted)[#ras.len() exigences évaluables.]
#v(0.6em)

#for ra in ras [
  // Breakable: Typst silently discards overflow from a fixed block.
  #block(
    breakable: true,
    above: 1em,
    width: 100%,
    inset: (bottom: 0.7em),
    stroke: (bottom: 0.4pt + rgb("#e5e7eb")),
  )[
    #grid(
      columns: (1fr, auto),
      gutter: 8pt,
      text(weight: "bold")[#field(ra, "ref_id") — #field(ra, "name")],
      // No badge rather than an empty one.
      if "result" in ra {
        box(
          fill: result-color(ra.at("result_key", default: "")),
          inset: (x: 5pt, y: 2pt),
          radius: 3pt,
        )[#text(8pt)[#result-label.at(ra.result_key, default: ra.result)]]
      },
    )
    #set text(9pt)
    #v(3pt)
    #let meta = (
      if "status" in ra { ([*Progression:* #ra.status],) } else { () }
        + if "extended_result" in ra and ra.extended_result != "-" {
          ([*Précision du résultat:* #ra.extended_result],)
        } else { () }
        + if "score" in ra and ra.score != none {
          ([*Score:* #ra.score#if field(ra, "max_score", fallback: none) != none [
              \/#ra.max_score
            ]],)
        } else { () }
    )
    #if meta.len() > 0 [#meta.join(h(10pt))]

    #if field(ra, "description") != "-" [
      #v(2pt)
      #text(fill: muted)[#ra.description]
    ]
    #let answers = ra.at("answers", default: ())
    #if answers.len() > 0 [
      #v(3pt)
      #for qa in answers [
        #text(weight: "semibold")[#qa.question] \
        #text(fill: rgb("#4338ca"))[#qa.answer]
        #v(1pt)
      ]
    ]
    #if field(ra, "observation") != "-" [
      #v(2pt)
      *"Observation":* #ra.observation
    ]
    #let ra-tasks = ra.at("task_templates", default: ())
    #if ra-tasks.len() > 0 [
      #v(2pt)
      #text(8pt, fill: accent)["Tâches": #ra-tasks.join(", ")]
    ]
    #let ra-evidences = ra.at("evidences", default: ())
    #if ra-evidences.len() > 0 [
      #v(2pt)
      #text(8pt, fill: accent)["Preuves": #ra-evidences.join(", ")]
    ]
    #if field(ra, "applied_controls") != "-" [
      #v(2pt)
      #text(8pt, fill: accent)["Mesures appliquées": #ra.applied_controls]
    ]
  ]
]
// ------------------------------------------------- commitments and tasks

#let undertaking-table(rows) = table(
  columns: (1fr, auto, auto, auto),
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (_, y) => if y == 0 { rgb("#e8edf7") },
  [*Engagement*],
  [*Statut*],
  [*Date d'engagement*],
  [*Date actuelle*],
  ..rows
    .map(row => (
      [
        #field(row, "name")
        #if field(row, "notes", fallback: "") != "" [
          \ #text(8pt, fill: muted)["Notes": #row.notes]
        ]
      ],
      field(row, "state"),
      align(right)[#field(row, "committedDate", fallback: field(row, "committed_eta"))],
      align(right)[
        #field(row, "current_date")
        #if row.at("has_slipped", default: false) [
          #text(8pt, fill: rgb("#b91c1c"))[("reporté")]
        ]
      ],
    ))
    .flatten(),
)

#let commitments = field(d, "commitments", fallback: ())
  #pagebreak(weak: true)
  = Engagements

  #if commitments.len() > 0 [
    #undertaking-table(commitments)
  ] else [
    #text(fill: muted)[Aucun engagement consigné.]
  ]
#let tasks = field(d, "tasks", fallback: ())
#if tasks.len() > 0 [
  = Tâches
  #undertaking-table(tasks)
]

// ------------------------------------------------------------ signatures

  #pagebreak(weak: true)
  = Signatures

  #par(justify: true)[En signant ci-dessous, les parties reconnaissent l'état de conformité et les engagements consignés dans ce document.]
  #v(1.5em)

  #grid(
    columns: (1fr, 1fr),
    gutter: 2em,
    ..("Pour l'entité évaluée", "Pour l'organisation évaluatrice").map(party => [
      #text(weight: "bold")[#party]
      #v(2.5em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[Nom et fonction]
      #v(2em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[Signature — Date]
    ]),
  )
