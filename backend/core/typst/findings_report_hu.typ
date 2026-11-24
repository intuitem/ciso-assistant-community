// Megállapítási jelentés — magyar.
// Payload: `core.generators.findings_assessment_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")

#let assessment-status-label = (
  "planned": "Tervezett",
  "in_progress": "Folyamatban",
  "in_review": "Felülvizsgálat alatt",
  "done": "Kész",
  "deprecated": "Elavult",
)
#let category-label = (
  "--": "Nincs meghatározva",
  "pentest": "Behatolásteszt",
  "threat_hunting": "Fenyegetésvadászat",
  "red_teaming": "Red teaming",
  "audit": "Audit",
  "self_identified": "Saját azonosítás",
  "posture": "Helyzetkép nyomon követése",
  "responsible_disclosure": "Felelős közzététel",
)

#let severity-label = (
  critical: "Kritikus",
  high: "Magas",
  medium: "Közepes",
  low: "Alacsony",
  info: "Információ",
  undefined: "Nincs meghatározva",
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
  "--": "Nincs meghatározva",
  undefined: "Nincs meghatározva",
  identified: "Azonosítva",
  confirmed: "Megerősítve",
  assigned: "Hozzárendelve",
  in_progress: "Folyamatban",
  mitigated: "Csökkentve",
  resolved: "Megoldva",
  dismissed: "Elvetve",
  deprecated: "Elavult",
  closed: "Lezárva",
)

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Megállapítási jelentés], align(right)[#d.assessment.name])
      line(length: 100%, stroke: 0.4pt + muted)
    }
  },
  footer: context {
    set text(8pt, fill: muted)
    grid(
      columns: (1fr, auto),
      [#d.date · #d.timezone], align(right)[#counter(page).display("1 / 1", both: true)],
    )
  },
)
#set text(10pt, lang: "hu")
#set par(justify: true)
#show heading.where(level: 1): set text(15pt, fill: accent)
#show heading.where(level: 2): set text(12pt, fill: accent)

// ---------------------------------------------------------------- cover page

#page(header: none, footer: none)[
  #set par(justify: false)
  #align(center + horizon)[
    #text(26pt, weight: "bold", fill: accent)[#d.assessment.name]
    #v(0.4em)
    #text(14pt, fill: muted)[Megállapítási jelentés – #category-label.at(d.assessment.category_key, default: d.assessment.category_key)]
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
        [*Hivatkozási azonosító*], [#d.assessment.ref_id],
        [*Tartomány*], [#d.assessment.folder],
        [*Állapot*], [#assessment-status-label.at(d.assessment.status_key, default: "-")],
        [*Szerzők*], [#d.assessment.authors],
        [*Felülvizsgálók*], [#d.assessment.reviewers],
        [*Dátum*], [#d.date],
      )
      #v(1em)
      #block(width: 100%)[
        #set text(7.5pt, fill: muted)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 3pt,
          column-gutter: 12pt,
          [Készült], [#d.generated_at],
          [Időzóna], [#d.timezone – minden időpont mellett szerepel az UTC-eltolása],
          [Dokumentumazonosító], [#raw(d.id)],
        )
      ]
    ]
  ]
]

// ------------------------------------------------------------------- summary

= Összefoglaló

#let m = d.metrics
#grid(
  columns: 4,
  gutter: 1em,
  ..(
    ("Összesen", m.total, rgb("#e8edf7")),
    ("Nyitott", m.open, rgb("#fee2e2")),
    ("Lezárt", m.closed, rgb("#dcfce7")),
    ("Megoldatlan jelentős", m.unresolved_important, rgb("#fef3c7")),
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
== Súlyosság

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
  == Észrevétel
  #d.assessment.observation
]

// ------------------------------------------------------------------ findings

#pagebreak(weak: true)
= Megállapítások

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
        text(weight: "bold")[#finding.ref_id – #finding.name],
        box(
          fill: severity-fill.at(finding.severity_key),
          inset: (x: 5pt, y: 2pt),
          radius: 3pt,
        )[#text(8pt)[#status-label.at(finding.status_key, default: finding.status_key)]],
      )
      #set text(9pt)
      #v(3pt)
      // One row each: a wrapped owner list would collide in a shared row.
      #grid(
        columns: (4.2cm, 1fr),
        column-gutter: 6pt,
        row-gutter: 2pt,
        text(fill: muted)[Felelős], [#finding.owners],
        text(fill: muted)[Prioritás], [#finding.priority],
        text(fill: muted)[Várható befejezés / Határidő], [#finding.eta – #finding.due_date],
      )
      #if finding.description != "" [
        #v(3pt)
        #text(fill: muted)[#finding.description]
      ]
      #if finding.observation != "" [
        #v(2pt)
        *Észrevétel:* #finding.observation
      ]
      #if finding.recommendation != "" [
        #v(2pt)
        *Ajánlás:* #finding.recommendation
      ]
      #if finding.controls.len() > 0 [
        #v(2pt)
        #text(8pt, fill: accent)[Alkalmazott kontrollok: #finding.controls.join(", ")]
      ]
      #if finding.evidences.len() > 0 [
        #v(2pt)
        #text(8pt, fill: accent)[Bizonyítékok: #finding.evidences.join(", ")]
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
