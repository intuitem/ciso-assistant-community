// Intézkedési terv — magyar.
// Payload: `core.generators.action_plan_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let field(record, key, fallback: "-") = record.at(key, default: fallback)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")
#let status-label = (
  to_do: "Teendő",
  in_progress: "Folyamatban",
  on_hold: "Felfüggesztve",
  active: "Aktív",
  degraded: "Leromlott",
  deprecated: "Elavult",
)
#let category-label = (
  policy: "Szabályzat",
  process: "Folyamat",
  technical: "Technikai",
  physical: "Fizikai",
  procedure: "Eljárás",
)

#let treatment-label = (
  open: "Nyitott",
  mitigate: "Csökkentett",
  accept: "Elfogadott",
  avoid: "Elkerült",
  transfer: "Áthárított",
  cancelled: "Lemondva",
)

// Set when the report covers a scenario selection rather than the whole assessment.
#let selection = d.at("selection", default: none)
#let selection-filter-label = (
  within_tolerance: "Tűréshatáron belül",
  treatment: "Kezelés",
  current_level: "Jelenlegi szint",
  residual_level: "Maradványkockázat szintje",
  owner: "Felelős",
  threats: "Fenyegetések",
  assets: "Eszközök",
  qualifications: "Minősítések",
  filtering_labels: "Címkék",
)
#let tolerance-label = ("YES": "Igen", "NO": "Nem", "--": "Nincs megadva")
#let selection-value(key, value) = if key == "within_tolerance" {
  tolerance-label.at(value, default: value)
} else if key == "treatment" {
  treatment-label.at(value, default: value)
} else { value }
#let selection-box = if selection != none {
  block(width: 100%, fill: rgb("#eef2ff"), stroke: 0.6pt + accent, radius: 3pt, inset: 8pt)[
    #set par(justify: false)
    #set align(left)
    #text(weight: "bold", fill: accent)[Forgatókönyv-kijelölés] · #selection.count / #selection.total forgatókönyv
    #v(2pt)
    #for f in selection.filters [
      #selection-filter-label.at(f.key, default: f.key): #f.values.map(v => selection-value(f.key, v)).join(", ") \
    ]
    #text(fill: muted)[Csak a kijelölt forgatókönyvekhez kapcsolódó kontrollok szerepelnek.]
  ]
}

// Landscape: the table needs the width.
#set page(
  paper: "a4",
  flipped: true,
  margin: (x: 1.6cm, top: 2cm, bottom: 1.6cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Intézkedési terv], align(right)[#d.subject.name])
      line(length: 100%, stroke: 0.4pt + muted)
    }
  },
  footer: context {
    set text(8pt, fill: muted)
    grid(
      columns: (1fr, auto),
      [#d.date · #d.timezone#if selection != none [ · Kijelölés #selection.count/#selection.total]],
      align(right)[#counter(page).display("1 / 1", both: true)],
    )
  },
)
#set text(9pt, lang: "hu")
#show heading.where(level: 1): set text(14pt, fill: accent)

= Intézkedési terv

#block(width: 100%, inset: (bottom: 6pt))[
  #set text(9pt)
  #grid(
    columns: (auto, 1fr),
    row-gutter: 4pt,
    column-gutter: 12pt,
    [*Tartomány*], [#d.subject.domain],
    [*Hatókör*], [#d.subject.perimeter],
    [*Értékelés*], [#d.subject.name – #d.subject.version],
    ..if d.subject.framework != "" { ([*Keretrendszer*], [#d.subject.framework]) } else { () },
  )
]

#if selection != none [
  #selection-box
  #v(0.4em)
]

#text(fill: muted)[
  A kapcsolódó alkalmazott kontrollok állapot szerint csoportosítva, várható befejezés szerint rendezve.
  Összesen: #d.total.
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
      #status-label.at(group.status_key, default: "Nincs állapot")
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
      [*Név*],
      [*Leírás*],
      [*Kategória*],
      [*Felelős*],
      [*Várható befejezés*],
      [*Egyező elemek*],
    ),
    ..group
      .controls
      .map(c => (
        [#c.name],
        [#text(8pt)[#c.description]],
        [#category-label.at(c.category_key, default: "-")],
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
    [Készült], [#d.generated_at],
    [Időzóna], [#d.timezone – minden időpont mellett szerepel az UTC-eltolása],
    [Dokumentumazonosító], [#raw(d.id)],
  )
]
