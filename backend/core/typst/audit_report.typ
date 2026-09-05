// Audit posture report.
//
// The payload arrives as JSON on `sys.inputs.data`, built by
// `core.generators.audit_context_for_typst`. Fields hidden from the reader's
// role are ABSENT from the payload, not blanked — so every optional read goes
// through `field()` and every optional section through `shown()`. Never add a
// role check here: redaction belongs in the context builder, because this file
// is overridable and a guard living in it could be removed.
//
// Charts are PNGs written next to this file by the renderer; `d.charts` lists
// the ones actually present.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)
// Chrome strings come from the payload, never inlined here: one template serves
// every locale once core.i18n_catalog backs `report_labels`.
#let t(key) = d.labels.at(key, default: key)
// Layout gate. Data the reader must not see is already absent from the payload
// (core.generators.REPORT_PROFILES), so this only decides what gets drawn.
#let shows(name) = name in d.sections
#let shown(key) = key not in d.hidden_fields
#let chart(name) = if name + ".png" in d.charts { image(name + ".png", width: 100%) }

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")

#let result-color(result) = {
  let key = lower(result)
  if key.contains("non") { rgb("#fee2e2") } else if key.contains("partial") {
    rgb("#fef3c7")
  } else if key.contains("compliant") { rgb("#dcfce7") } else { rgb("#f1f5f9") }
}

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
          [*#t("assessedEntity")*],
          [
            #party.entity#if party.ref_id != "" [ (#party.ref_id)]
            #if party.address != "" [
              \ #text(fill: muted)[#party.address.replace("\n", ", ")]
            ]
          ],
          ..if party.legal_identifiers.len() > 0 {
            (
              [*#t("legalIdentifiers")*],
              party
                .legal_identifiers
                .map(pair => [#pair.label: #pair.value])
                .join(" · "),
            )
          } else { () },
          ..if party.expiry_date != "-" {
            ([*#t("expiryDate")*], [#party.expiry_date])
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
        [*#t("reference")*], [#field(d.audit, "ref_id")],
        [*#t("date")*], [#d.date],
        [*#t("implementationGroups")*], [#if d.igs != "" { d.igs } else { t("all") }],
        [*#t("contributors")*], [#d.contributors.replace("\n", ", ")],
      )
    ]
  ]
]

// ------------------------------------------------------------------- summary

#let r = d.req
#let total = field(r, "total", fallback: 0)

#if shows("summary") [
  = #t("executiveSummary")
  #table(
    columns: 5,
    align: center,
    stroke: 0.5pt + rgb("#cbd5e1"),
    fill: (_, y) => if y == 0 { rgb("#e8edf7") },
    [*#t("compliant")*],
    [*#t("partiallyCompliant")*],
    [*#t("nonCompliant")*],
    [*#t("notApplicable")*],
    [*#t("notAssessed")*],
    [#r.compliant],
    [#r.partially_compliant],
    [#r.non_compliant],
    [#r.not_applicable],
    [#r.not_assessed],
  )
]

#if shows("summary") and total > 0 [
  #v(0.6em)
  Compliant on *#calc.round(100 * r.compliant / total, digits: 1)%* of
  #total assessed requirements. #field(d, "ac_count", fallback: 0) applied
  controls are linked to this audit.
]

#if shows("charts") [
  #v(1em)
  #grid(
    columns: (1fr, 1fr),
    gutter: 1em,
    chart("compliance_donut"), chart("compliance_radar"),
  )
]

#if shows("scope") and d.audit.description != "-" [
  == #t("scope")
  #d.audit.description
]

#let drifts = field(d, "drifts_per_domain", fallback: ())
#if shows("drifts") and drifts.len() > 0 [
  == #t("driftsPerDomain")
  #table(
    columns: (1fr, auto),
    stroke: 0.5pt + rgb("#cbd5e1"),
    fill: (_, y) => if y == 0 { rgb("#e8edf7") },
    [*#t("domain")*], [*#t("findings")*],
    ..drifts.map(x => (field(x, "name"), align(right)[#x.drift_count])).flatten(),
  )
]

// -------------------------------------------------------------- category view

#let categories = field(d, "category_scores", fallback: (:))
#if shows("categories") and shown("score") and categories.len() > 0 [
  = #t("scoresPerCategory")

  #table(
    columns: (1fr, auto, auto, auto),
    stroke: 0.5pt + rgb("#cbd5e1"),
    fill: (_, y) => if y == 0 { rgb("#e8edf7") },
    [*#t("category")*], [*#t("average")*], [*#t("scored")*], [*#t("items")*],
    ..categories
      .values()
      .map(c => (
        field(c, "name"),
        align(right)[#field(c, "average_score", fallback: 0)],
        align(right)[#field(c, "scored_count", fallback: 0)],
        align(right)[#field(c, "item_count", fallback: 0)],
      ))
      .flatten(),
  )

  #v(0.8em)
  #chart("category_radar")
]

// ------------------------------------------------------------------ controls

#let p1 = field(d, "p1_controls", fallback: ())
#if shows("controls") and p1.len() > 0 [
  = #t("priorityControls")

  #chart("chart_controls")
  #v(0.8em)

  #table(
    columns: (1fr, auto, auto),
    stroke: 0.5pt + rgb("#cbd5e1"),
    fill: (_, y) => if y == 0 { rgb("#e8edf7") },
    [*#t("control")*], [*#t("status")*], [*#t("category")*],
    ..p1
      .map(c => (field(c, "name"), field(c, "status"), field(c, "category")))
      .flatten(),
  )
]

// ------------------------------------------------------- detailed assessment

#if shows("requirements") [
#pagebreak(weak: true)
= #t("detailedResults")

#let ras = field(d, "requirement_assessments", fallback: ())
#text(fill: muted)[#ras.len() #t("assessableRequirements").]
#v(0.6em)

#for ra in ras [
  #block(
    breakable: false,
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
          fill: result-color(ra.result),
          inset: (x: 5pt, y: 2pt),
          radius: 3pt,
        )[#text(8pt)[#ra.result]]
      },
    )
    #set text(9pt)
    #v(3pt)

    // Absent keys mean the reader's role may not see them — print nothing.
    #let meta = (
      if "status" in ra { ([*#t("progress"):* #ra.status],) } else { () }
        + if "extended_result" in ra and ra.extended_result != "-" {
          ([*#t("resultDetail"):* #ra.extended_result],)
        } else { () }
        + if "score" in ra and ra.score != none {
          ([*#t("score"):* #ra.score#if field(ra, "max_score", fallback: none) != none [
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
    #if shows("answers") and answers.len() > 0 [
      #v(3pt)
      #for qa in answers [
        #text(weight: "semibold")[#qa.question] \
        #text(fill: rgb("#4338ca"))[#qa.answer]
        #v(1pt)
      ]
    ]
    #if field(ra, "observation") != "-" [
      #v(2pt)
      *#t("observation"):* #ra.observation
    ]
    #let ra-tasks = ra.at("task_templates", default: ())
    #if ra-tasks.len() > 0 [
      #v(2pt)
      #text(8pt, fill: accent)[#t("tasks"): #ra-tasks.join(", ")]
    ]
    #let ra-evidences = ra.at("evidences", default: ())
    #if ra-evidences.len() > 0 [
      #v(2pt)
      #text(8pt, fill: accent)[#t("evidences"): #ra-evidences.join(", ")]
    ]
    #if field(ra, "applied_controls") != "-" [
      #v(2pt)
      #text(8pt, fill: accent)[#t("appliedControls"): #ra.applied_controls]
    ]
  ]
]
]

// ------------------------------------------------- commitments and tasks

#let undertaking-table(rows) = table(
  columns: (1fr, auto, auto, auto),
  stroke: 0.5pt + rgb("#cbd5e1"),
  fill: (_, y) => if y == 0 { rgb("#e8edf7") },
  [*#t("undertaking")*],
  [*#t("status")*],
  [*#t("committedDate")*],
  [*#t("currentDate")*],
  ..rows
    .map(row => (
      [
        #field(row, "name")
        #if field(row, "notes", fallback: "") != "" [
          \ #text(8pt, fill: muted)[#t("notes"): #row.notes]
        ]
      ],
      field(row, "state"),
      align(right)[#field(row, "committedDate", fallback: field(row, "committed_eta"))],
      align(right)[
        #field(row, "current_date")
        #if row.at("has_slipped", default: false) [
          #text(8pt, fill: rgb("#b91c1c"))[(#t("slipped"))]
        ]
      ],
    ))
    .flatten(),
)

#let commitments = field(d, "commitments", fallback: ())
#if shows("commitments") [
  #pagebreak(weak: true)
  = #t("commitments")

  #if commitments.len() > 0 [
    #undertaking-table(commitments)
  ] else [
    #text(fill: muted)[#t("noCommitments")]
  ]
]

#let tasks = field(d, "tasks", fallback: ())
#if shows("tasks") and tasks.len() > 0 [
  = #t("tasks")
  #undertaking-table(tasks)
]

// ------------------------------------------------------------ signatures

#if shows("signatures") [
  #pagebreak(weak: true)
  = #t("signatures")

  #par(justify: true)[#t("signatureIntro")]
  #v(1.5em)

  #grid(
    columns: (1fr, 1fr),
    gutter: 2em,
    ..(t("forTheAssessedEntity"), t("forTheAssessingOrganisation")).map(party => [
      #text(weight: "bold")[#party]
      #v(2.5em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[#t("nameAndRole")]
      #v(2em)
      #line(length: 100%, stroke: 0.5pt)
      #text(8pt, fill: muted)[#t("signature") — #t("date")]
    ]),
  )
]
