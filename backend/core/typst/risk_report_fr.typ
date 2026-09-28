// Rapport d'analyse de risque — français.
// Payload: `core.generators.risk_assessment_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let ra = d.assessment

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")

#let assessment-status-label = (
  "planned": "Planifié",
  "in_progress": "En cours",
  "in_review": "En revue",
  "done": "Terminé",
  "deprecated": "Déprécié",
)

#let view-label = (
  inherent: "Risque inhérent",
  current: "Risque courant",
  residual: "Risque résiduel",
)
#let axis-title = (
  probabilityISO: "Vraisemblance",
  probabilityEBIOS: "Vraisemblance",
  impactISO: "Conséquence",
  impactEBIOS: "Gravité",
)
#let axis-name(kind) = axis-title.at(kind + d.label_standard)
#let qualification-label = if d.use_risk_category_label { "Catégories de risque" } else { "Qualifications" }

#let treatment-label = (
  open: "Ouvert",
  mitigate: "Atténuer",
  accept: "Accepter",
  avoid: "Éviter",
  transfer: "Transférer",
  cancelled: "Annulé",
)

#let level-badge(level) = box(
  fill: rgb(level.hexcolor),
  inset: (x: 5pt, y: 2pt),
  radius: 3pt,
)[#text(8pt)[#level.name]]

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2.2cm, bottom: 2cm),
  header: context {
    if counter(page).get().first() > 1 {
      set text(8pt, fill: muted)
      grid(columns: (1fr, auto), [Analyse de risque], align(right)[#ra.name])
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
  // Ragged : le texte justifié coupe les adresses.
  #set par(justify: false)
  #align(center + horizon)[
    #text(26pt, weight: "bold", fill: accent)[#ra.name]
    #v(0.4em)
    #text(14pt, fill: muted)[Analyse de risque — #ra.version]
    #if ra.description != "" [
      #v(0.6em)
      #block(width: 75%)[#text(9.5pt, fill: muted)[#ra.description]]
    ]
    #v(2em)
    #block(width: 75%)[
      #set align(left)
      #set text(10pt)
      #grid(
        columns: (auto, 1fr),
        row-gutter: 8pt,
        column-gutter: 12pt,
        [*Domaine*], [#ra.folder],
        [*Périmètre*], [#ra.perimeter],
        [*Matrice de risque*], [#ra.matrix],
        [*Statut*], [#assessment-status-label.at(ra.status_key, default: "-")],
        [*Auteurs*], [#ra.authors],
        [*Relecteurs*], [#ra.reviewers],
        [*Échéance / Limite*], [#ra.eta — #ra.due_date],
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

// -------------------------------------------------------------- matrix views

= Matrice de risque

#for view in d.matrix_views [
  #block(breakable: false, above: 1.2em)[
    #text(12pt, weight: "bold", fill: accent)[#view-label.at(view.key)]
    #v(0.5em)
    #grid(
      columns: (0.9cm, 1fr),
      align: center + horizon,
      rotate(-90deg, reflow: true)[#text(9pt, fill: muted)[#axis-name(view.y_type)]],
      table(
      columns: (2.2cm,) + view.x_axis.map(_ => 1fr),
      rows: (auto,) * view.cells.len() + (auto,),
      stroke: 2pt + white,
      align: center + horizon,
      inset: (x: 5pt, y: 12pt),
      ..view
        .cells
        .enumerate()
        .map(((index, row)) => (
          table.cell(fill: rgb("#e5e7eb"))[#text(8pt)[#view.y_axis.at(index).name]],
        ) + row.map(cell => table.cell(fill: rgb(cell.hexcolor))[
          #text(7.5pt)[#cell.refs.join(", ")]
        ]))
        .flatten(),
      table.cell(fill: white)[],
      ..view.x_axis.map(axis => table.cell(fill: rgb("#e5e7eb"))[#text(8pt)[#axis.name]]),
      ),
    )
    #align(center)[#text(9pt, fill: muted)[#axis-name(view.x_type)]]
  ]
]

#pagebreak(weak: true)
= Synthèse des scénarios

#let with-inherent = d.include_inherent
#table(
  columns: if with-inherent { (1.6cm, 3fr, 4fr, auto, auto, auto, auto) } else {
    (1.6cm, 3fr, 4fr, auto, auto, auto)
  },
  stroke: 0.5pt + rule,
  fill: (_, y) => if y == 0 { rgb("#e8edf7") },
  align: left + top,
  inset: 5pt,
  // Repeats on every page.
  table.header(
    [*Réf.*],
    [*Nom*],
    [*Description*],
    ..if with-inherent { ([*Inhérent*],) } else { () },
    [*Courant*],
    [*Résiduel*],
    [*Traitement*],
  ),
  ..d.scenarios.enumerate().map(((index, scenario)) => (
    // Jumps to the matching block under "Risk scenarios".
    [#text(8pt)[#link(label("scn-" + str(index)))[#scenario.ref_id]]],
    [#text(8pt)[#scenario.name]],
    [#text(8pt)[#scenario.description]],
  ) + (if with-inherent { (level-badge(scenario.inherent),) } else { () }) + (
    level-badge(scenario.current),
    level-badge(scenario.residual),
    [#text(8pt)[#treatment-label.at(scenario.treatment_key, default: scenario.treatment_key)]],
  )).flatten(),
)

// ----------------------------------------------------------------- scenarios

#pagebreak(weak: true)
= Scénarios de risque

#text(fill: muted)[#d.scenarios.len() scénarios.]
#v(0.6em)

#for (index, scenario) in d.scenarios.enumerate() [
  #block(
    breakable: true,
    width: 100%,
    above: 0.9em,
    inset: (bottom: 0.7em),
    stroke: (bottom: 0.4pt + rule),
  )[
    #text(weight: "bold")[#scenario.ref_id — #scenario.name] #label("scn-" + str(index))
    #v(4pt)
    #set text(9pt)
    #let row(label, body) = (text(fill: muted)[#label], body)
    #grid(
      // Wide enough for the longest label: a narrow column hyphenates them.
      columns: (4.2cm, 1fr),
      column-gutter: 6pt,
      row-gutter: 3pt,
      ..(
        if scenario.description != "" { row("Description", [#scenario.description]) } else { () }
          + if scenario.qualifications.len() > 0 { row(qualification-label, [#scenario.qualifications.join(", ")]) } else { () }
          + if scenario.assets.len() > 0 { row("Actifs", [#scenario.assets.join(", ")]) } else { () }
          + if scenario.threats.len() > 0 { row("Menaces", [#scenario.threats.join(", ")]) } else { () }
          + if "inherent" in scenario { row("Niveau inhérent", level-badge(scenario.inherent)) } else { () }
          + if scenario.existing_controls.len() > 0 { row("Mesures existantes", [#scenario.existing_controls.join(", ")]) } else { () }
          + row("Niveau courant", level-badge(scenario.current))
          + if scenario.controls.len() > 0 { row("Mesures supplémentaires", [#scenario.controls.join(", ")]) } else { () }
          + row("Niveau résiduel", level-badge(scenario.residual))
          + row("Force de la connaissance", [#scenario.strength_of_knowledge])
          + row("Traitement", [#treatment-label.at(scenario.treatment_key, default: scenario.treatment_key)])
          + if scenario.justification != "" { row("Justification", [#scenario.justification]) } else { () }
      ),
    )
  ]
]
