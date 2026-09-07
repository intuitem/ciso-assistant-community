// Attestation to countersign — English.
//
// SELF-CONTAINED ON PURPOSE — one document, one locale, no shared module. A
// customer can download this file, edit it and upload it back without knowing
// anything about the rest of the system, and customising it cannot affect the
// other three. The price is deliberate duplication: a layout change belongs in
// every sibling, and a test renders each to catch drift.
//
// The payload arrives as JSON on `sys.inputs.data`, built by
// `core.generators.audit_context_for_typst`. Fields hidden from the reader's role
// are ABSENT from the payload, not blanked — so optional reads go through
// `field()`. Never add a role check here: redaction belongs in the context
// builder, because this file is overridable and a guard living in it could be
// removed.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
// Chrome strings come from the payload, never inlined here: one template serves
// every locale once core.i18n_catalog backs `report_labels`.
#let shown(key) = key not in d.hidden_fields
#let chart(name) = if name + ".png" in d.charts { image(name + ".png", width: 100%) }

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")

// Row badges name one requirement; the summary headers sit above counts.
// English does not inflect these, but the split matters in other locales.
#let result-label = (
  compliant: "Compliant",
  partially_compliant: "Partially compliant",
  non_compliant: "Non compliant",
  not_applicable: "Not applicable",
  not_assessed: "Not assessed",
)

// Keyed on the raw enum value, never the label: matching English substrings
// mis-colours every other locale ("Conforme" contains no "compliant").
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
  // Ragged on the cover: justified metadata hyphenates addresses mid-word.
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
          [*Assessed entity*],
          [
            #party.entity#if party.ref_id != "" [ (#party.ref_id)]
            #if party.address != "" [
              \ #text(fill: muted)[#party.address.replace("\n", ", ")]
            ]
          ],
          ..if party.legal_identifiers.len() > 0 {
            (
              [*Legal identifiers*],
              party
                .legal_identifiers
                .map(pair => [#pair.label: #pair.value])
                .join(" · "),
            )
          } else { () },
          ..if party.expiry_date != "-" {
            ([*Expiry date*], [#party.expiry_date])
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
        [*Reference*], [#field(d.audit, "ref_id")],
        [*Date*], [#d.date],
        [*Implementation groups*], [#if d.igs != "" { d.igs } else { "All" }],
        [*Contributors*], [#d.contributors.replace("\n", ", ")],
      )
      #v(1em)
      // Cheap traceability: which render, of which audit.
      #block(width: 100%)[
        #set text(7.5pt, fill: muted)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 3pt,
          column-gutter: 12pt,
          [Generated at], [#d.generated_at],
          [Document ID], [#raw(d.audit.id)],
        )
      ]
    ]
  ]
]

// ------------------------------------------------------------------- summary

#let r = d.at("req", default: none)
#let total = if r != none { field(r, "total", fallback: 0) } else { 0 }

#if d.audit.description != "-" [
  == Scope
  #d.audit.description
]

#let drifts = field(d, "drifts_per_domain", fallback: ())
// -------------------------------------------------------------- category view

#let categories = field(d, "category_scores", fallback: (:))
// ------------------------------------------------------------------ controls

#let p1 = field(d, "p1_controls", fallback: ())
// ------------------------------------------------------- detailed assessment

#pagebreak(weak: true)
= Detailed results

#let ras = field(d, "requirement_assessments", fallback: ())
#text(fill: muted)[#ras.len() assessable requirements.]
#v(0.6em)

#for ra in ras [
  // Breakable on purpose: Typst silently discards content that overflows a
  // non-breakable block, and `observation` is unbounded text.
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
      // No badge at all when the verdict is not disclosed — an empty one reads
      // as "no result recorded", which is a different statement.
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

    // Absent keys mean the reader's role may not see them — print nothing.
    #let meta = (
      if "status" in ra { ([*Progress:* #ra.status],) } else { () }
        + if "extended_result" in ra and ra.extended_result != "-" {
          ([*Result detail:* #ra.extended_result],)
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
      #text(8pt, fill: accent)["Tasks": #ra-tasks.join(", ")]
    ]
    #let ra-evidences = ra.at("evidences", default: ())
    #if ra-evidences.len() > 0 [
      #v(2pt)
      #text(8pt, fill: accent)["Evidences": #ra-evidences.join(", ")]
    ]
    #if field(ra, "applied_controls") != "-" [
      #v(2pt)
      #text(8pt, fill: accent)["Applied controls": #ra.applied_controls]
    ]
  ]
]
// ------------------------------------------------- commitments and tasks

#let undertaking-table(rows) = table(
  columns: (1fr, auto, auto, auto),
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (_, y) => if y == 0 { rgb("#e8edf7") },
  [*Undertaking*],
  [*Status*],
  [*Committed date*],
  [*Current date*],
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
          #text(8pt, fill: rgb("#b91c1c"))[("slipped")]
        ]
      ],
    ))
    .flatten(),
)

#let commitments = field(d, "commitments", fallback: ())
  #pagebreak(weak: true)
  = Commitments

  #if commitments.len() > 0 [
    #undertaking-table(commitments)
  ] else [
    #text(fill: muted)[No commitments recorded.]
  ]
#let tasks = field(d, "tasks", fallback: ())
#if tasks.len() > 0 [
  = Tasks
  #undertaking-table(tasks)
]

// ------------------------------------------------------------ signatures

  #pagebreak(weak: true)
  = Signatures

  #par(justify: true)[By signing below, the parties agree to the compliance status and the commitments recorded in this document.]
  #v(1.5em)

  #grid(
    columns: (1fr, 1fr),
    gutter: 2em,
    ..("For the assessed entity", "For the assessing organisation").map(party => [
      #text(weight: "bold")[#party]
      #v(2.5em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[Name and role]
      #v(2em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[Signature — Date]
    ]),
  )
