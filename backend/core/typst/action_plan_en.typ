// Action plan — English.
// Payload: `core.generators.action_plan_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")
// Landscape: the table needs the width.
#set page(
  paper: "a4",
  flipped: true,
  margin: (x: 1.6cm, top: 2cm, bottom: 1.6cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Action plan], align(right)[#d.subject.name])
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
#set text(9pt, lang: "en")
#show heading.where(level: 1): set text(14pt, fill: accent)

= Action plan

#block(width: 100%, inset: (bottom: 6pt))[
  #set text(9pt)
  #grid(
    columns: (auto, 1fr),
    row-gutter: 4pt,
    column-gutter: 12pt,
    [*Domain*], [#d.subject.domain],
    [*Perimeter*], [#d.subject.perimeter],
    [*Assessment*], [#d.subject.name — #d.subject.version],
    ..if d.subject.framework != "" { ([*Framework*], [#d.subject.framework]) } else { () },
  )
]

#text(fill: muted)[
  Associated applied controls, separated by status and sorted by ETA.
  #d.total in total.
]
#v(0.6em)
// Fractions, not auto: auto columns overflow and overlap.
#let columns-spec = (
  2.4fr, // name
  4.2fr, // description — the column actually read
  1.4fr, // category
  2.0fr, // owner
  1.2fr, // eta
  3.0fr, // linked items
)

#for group in d.groups [
  #block(
    width: 100%,
    fill: rgb(group.fill),
    inset: 6pt,
    radius: 3pt,
    above: 1em,
  )[
    #text(weight: "bold")[
      #if group.status != "" { group.status } else { "No status" }
      (#group.controls.len())
    ]
  ]
  #v(4pt)
  #table(
    columns: columns-spec,
    stroke: 0.5pt + rule,
    fill: (_, y) => if y == 0 { rgb("#e8edf7") },
    align: left + top,
    // Repeats on every page.
    table.header(
      [*Name*],
      [*Description*],
      [*Category*],
      [*Owner*],
      [*ETA*],
      [*Matching items*],
    ),
    ..group
      .controls
      .map(c => (
        [#c.name],
        [#text(8pt)[#c.description]],
        [#c.category],
        [#c.owner],
        [#c.eta],
        [#text(8pt)[#if c.linked.len() > 0 { c.linked.join(linebreak()) } else { "-" }]],
      ))
      .flatten(),
  )
]

#v(1.5em)
#block(width: 100%)[
  #set text(7.5pt, fill: muted)
  #grid(
    columns: (auto, 1fr),
    row-gutter: 3pt,
    column-gutter: 12pt,
    [Generated at], [#d.generated_at],
    [Document ID], [#raw(d.id)],
  )
]
