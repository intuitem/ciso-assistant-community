// Olay raporu — Türkçe.
// Payload: `core.generators.incident_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let inc = d.incident

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")
#let chip-fill = rgb("#dbeafe")
#let chip-text = rgb("#1e40af")

#let severity-label = (
  "1": "Kritik",
  "2": "Büyük",
  "3": "Orta",
  "4": "Küçük",
  "5": "Düşük",
  "6": "Bilinmiyor",
)
#let incident-status-label = (
  "new": "Yeni",
  "ongoing": "Devam ediyor",
  "resolved": "Çözüldü",
  "closed": "Kapandı",
  "dismissed": "Reddedildi",
)
#let detection-label = (
  "internally_detected": "İç",
  "externally_detected": "Dış",
)

#let entry-label = (
  detection: "Tespit",
  mitigation: "Hafifletme",
  observation: "Gözlem",
  severity_changed: "Önem derecesi değişti",
  status_changed: "Durum değişti",
)
// Keyed on the raw value: labels are localised.
#let entry-accent = (
  detection: rgb("#3b82f6"),
  mitigation: rgb("#22c55e"),
  observation: rgb("#9ca3af"),
  severity_changed: rgb("#f97316"),
  status_changed: rgb("#a855f7"),
)

#let chips(items) = items.map(name => box(fill: chip-fill, inset: (x: 5pt, y: 2pt), radius: 3pt)[#text(8pt, fill: chip-text)[#name]]).join(h(3pt))

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Olay raporu], align(right)[#inc.name])
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
#set text(10pt, lang: "tr")
#set par(justify: true)
#show heading.where(level: 1): set text(15pt, fill: accent)
#show heading.where(level: 2): set text(12pt, fill: accent)

// ---------------------------------------------------------------- cover page

#page(header: none, footer: none)[
  #set par(justify: false)
  #align(center + horizon)[
    #text(26pt, weight: "bold", fill: accent)[
      #if inc.ref_id != "" [#inc.ref_id — ]#inc.name
    ]
    #v(0.4em)
    #text(14pt, fill: muted)[Olay raporu]
    #v(2em)
    #block(width: 78%)[
      #set align(left)
      #set text(10pt)
      #grid(
        columns: (auto, 1fr),
        row-gutter: 8pt,
        column-gutter: 12pt,
        [*Önem derecesi*], [#severity-label.at(inc.severity_key, default: "-")],
        [*Durum*], [#incident-status-label.at(inc.status_key, default: "-")],
        [*Tespit*], [#detection-label.at(inc.detection_key, default: "-")],
        [*Etki alanı*], [#inc.folder],
        [*Sorumlular*], [#inc.owners],
        [*Gerçekleşme zamanı*], [#inc.occurred_at],
        [*Bildirim zamanı*], [#inc.reported_at],
        [*Çözülme zamanı*], [#inc.resolved_at],
        [*İş sürekliliği planı (BCP) devreye alındı*], [#if inc.is_bcp_activated [Evet] else [Hayır]],
      )
      #v(1em)
      #block(width: 100%)[
        #set text(7.5pt, fill: muted)
        #grid(
          columns: (auto, 1fr),
          row-gutter: 3pt,
          column-gutter: 12pt,
          [Oluşturulma zamanı], [#d.generated_at],
          [Belge kimliği], [#raw(d.id)],
        )
      ]
    ]
  ]
]

// ------------------------------------------------------------------- context

#if inc.description != "" [
  = Açıklama
  #inc.description
]

#if inc.resolution != "" [
  = Çözüm
  #inc.resolution
]

#let scope = (
  ("Nitelendirmeler", inc.qualifications),
  ("İlgili taraflar", inc.entities),
  ("Etkilenen varlıklar", inc.assets),
  ("İlgili tehditler", inc.threats),
).filter(((label, items)) => items.len() > 0)

#if scope.len() > 0 [
  = Kapsam
  #for (label, items) in scope [
    #block(above: 0.7em)[
      #text(weight: "bold")[#label] \
      #v(2pt)
      #chips(items)
    ]
  ]
]

// ------------------------------------------------------------------ timeline

#pagebreak(weak: true)
= Zaman çizelgesi

#text(fill: muted)[
  Kronolojik sırayla #d.counts.total kayıt; saatler UTC.
  Tespit: #d.counts.detection, hafifletme: #d.counts.mitigation.
]
#v(0.8em)

#for entry in d.timeline [
  #block(
    breakable: true,
    width: 100%,
    above: 0.8em,
    inset: (left: 8pt, bottom: 0.6em),
    stroke: (
      left: 2pt + entry-accent.at(entry.type_key, default: muted),
      bottom: 0.4pt + rule,
    ),
  )[
    #grid(
      columns: (1fr, auto),
      gutter: 8pt,
      text(weight: "bold")[#entry.entry],
      box(
        fill: chip-fill,
        inset: (x: 5pt, y: 2pt),
        radius: 3pt,
      )[#text(8pt, fill: chip-text)[#entry-label.at(entry.type_key, default: entry.type_key)]],
    )
    #set text(9pt)
    #v(3pt)
    #text(fill: muted)[
      #entry.timestamp#if entry.author != "" [ — #entry.author tarafından]
    ]
    #if entry.observation != "" [
      #v(3pt)
      #entry.observation
    ]
    #if entry.evidences.len() > 0 [
      #v(3pt)
      #chips(entry.evidences)
    ]
  ]
]
