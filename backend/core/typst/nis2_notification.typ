// NIS2 notification worksheet. Sections, order and field labels follow annex 2 of
// the CCB "NIS2 Notification guide" v1.3 (08.2025), FR/NL/EN; * = mandatory there.
// Payload: `core.generators.nis2_notification_context` via sys.inputs.data.

#let d = json(bytes(sys.inputs.data))
#let inc = d.incident

#let labels = (
  en: (
    title: "NIS2 notification worksheet",
    subtitle: "Prepared for the CCB notification form (notif.safeonweb.be), guide v1.3",
    disclaimer: "Worksheet generated from the GRC record to prepare the notification. It is not the CCB form: submit each stage on the CCB platform, then record the date sent and the tracking reference on the incident.",
    todo: "To complete", limit: "max. 500 characters", over: "over 500 characters: shorten",
    yes: "Yes", no: "No", uncertain: "Uncertain",
    s-timeline: "Notification timeline",
    stage: "Stage", due: "Due", sent: "Sent", state: "State",
    st-sent: "Sent", st-overdue: "Overdue", st-pending: "Pending",
    early_warning: "Early warning (24h)",
    incident_notification: "Incident notification (72h)",
    final_report: "Final report (1 month)",
    not-significant: "The incident is not flagged as significant under NIS2: no notification deadlines apply.",
    significance-pending: "NIS2 significance not assessed yet: set it on the incident to compute the notification deadlines.",
    s-entity: "Entity notifying the incident",
    Submitter: "Concerning...",
    s-nis: "NIS specific characteristics",
    NIS_Type: "How is the organisation defined under the NIS2 law?",
    Sector: "In which main sector(s) does your organisation operate?",
    NIS_Notification: "What type of NIS2 incident notification are you submitting?",
    s-details: "Incident details",
    Tracking_Reference: "Tracking Reference",
    Malicious_Intent: "Do you believe this incident is the result of malicious intent?",
    Incident_Type: "Incident type",
    Incident_Date: "When did the incident take place?",
    Incident_Description: "Describe the incident (initial cause, impact to organization, name of virus or malware, data and systems affected, actions taken, operating systems/software involved, etc.)",
    Assessment_Severity: "Please provide an assessment of the severity of the incident",
    Assessment_Consequence: "What are the consequences of the incident?",
    Threat_Type_Root_Cause: "What caused the incident?",
    Cross_Border_Impact: "Do you believe this incident might lead to cross-border issues?",
    Cross_Border_Impact_Description: "Provide details of the cross-border issues this incident might cause",
    Police_Involved: "Have you reported the incident to the police?",
    Help_Needed: "Do you need support, analysis or advice from the CCB?",
    Actions_Taken: "What actions did you take?",
    Resolved: "Is the incident now resolved?",
    s-more: "More information",
    Incident_Detection_Date: "When was the incident detected?",
    Incident_Detection_Description: "How was the incident detected?",
    Incident_Detection_Timeline: "Provide a detailed timeline with all actions taken.",
    Incident_Detection_Communication: "Which communication occurred in response to the incident?",
    Incident_Detection_Preventive_Measures: "What preventive measures were in place at the time of the incident?",
    Incident_Detection_Corrective_Measures: "What corrective measures were taken in response to the incident?",
    Incident_Detection_Lessons_Learned: "What lessons were learned from the incident?",
    Incident_Detection_New_Measures: "What new (adapted) preventive measures were implemented after the incident?",
    MFA_Applied: "Was MFA applied to your impacted environment when the incident occurred?",
    s-contact: "Contact details of the entity",
    Contact_Person: "Point of contact",
    Organization: "Organisation name",
    Email: "Email",
    Telephone: "Telephone",
    Location: "Where did the incident take place?",
    s-gdpr: "Linked personal data breaches",
    gdpr-note: "A NIS2 notification does not replace the notification to the data protection authority (GDPR art. 33, 72h).",
    breach: "Breach", discovered: "Discovered", apd-due: "Due (72h)", apd-sent: "Notified",
    generated: "Generated", doc-id: "Document ID",
    sev: ("1": "Critical", "2": "Major", "3": "Moderate", "4": "Minor", "5": "Low", "6": "Unknown"),
    det: (internally_detected: "Detected internally", externally_detected: "Reported by a third party"),
    bcp: "Business continuity plan activated",
  ),
  fr: (
    title: "Fiche de notification NIS2",
    subtitle: "Préparée pour le formulaire de notification du CCB (notif.safeonweb.be), guide v1.3",
    disclaimer: "Fiche générée depuis l'outil GRC pour préparer la notification. Ce n'est pas le formulaire du CCB : chaque étape se soumet sur la plateforme du CCB, puis la date d'envoi et le numéro de suivi s'enregistrent sur l'incident.",
    todo: "À compléter", limit: "500 caractères max.", over: "plus de 500 caractères : à raccourcir",
    yes: "Oui", no: "Non", uncertain: "Incertain",
    s-timeline: "Calendrier de notification",
    stage: "Étape", due: "Échéance", sent: "Envoyée", state: "État",
    st-sent: "Envoyée", st-overdue: "En retard", st-pending: "À faire",
    early_warning: "Alerte précoce (24 h)",
    incident_notification: "Notification d'incident (72 h)",
    final_report: "Rapport final (1 mois)",
    not-significant: "L'incident n'est pas qualifié de significatif au sens de NIS2 : aucun délai de notification ne s'applique.",
    significance-pending: "Caractère significatif au sens de NIS2 pas encore évalué : renseignez-le sur l'incident pour calculer les délais de notification.",
    s-entity: "Entité notifiant l'incident",
    Submitter: "Concernant…",
    s-nis: "Caractéristiques spécifiques NIS",
    NIS_Type: "Comment l'organisation est-elle définie dans le cadre de la loi NIS2 ?",
    Sector: "Dans quel(s) secteur(s) votre organisation opère-t-elle ?",
    NIS_Notification: "Quel type de notification d'incident NIS2 soumettez-vous ?",
    s-details: "Détails sur l'incident",
    Tracking_Reference: "Numéro de suivi",
    Malicious_Intent: "Pensez-vous que cet incident soit le résultat d'une intention malveillante",
    Incident_Type: "Type d'incident",
    Incident_Date: "Quand l'incident a-t-il eu lieu ?",
    Incident_Description: "Décrire l'incident (cause initiale, impact sur l'organisation, nom du virus ou du logiciel malveillant, données et systèmes affectés, mesures prises, systèmes d'exploitation/logiciels concernés, etc.)",
    Assessment_Severity: "Veuillez fournir une évaluation de la gravité de l'incident",
    Assessment_Consequence: "Quelles sont les conséquences de l'incident ?",
    Threat_Type_Root_Cause: "Quelle est la cause de l'incident ?",
    Cross_Border_Impact: "Pensez-vous que cet incident pourrait déboucher sur des problèmes transfrontaliers ?",
    Cross_Border_Impact_Description: "Donner des détails sur les problèmes frontaliers que cet incident pourrait engendrer",
    Police_Involved: "Avez-vous signalé l'incident à la police ?",
    Help_Needed: "Avez-vous besoin d'un support, d'une investigation ou d'un conseil de la part du CCB ?",
    Actions_Taken: "Quelles mesures avez-vous prises ?",
    Resolved: "L'incident est-il à présent résolu ?",
    s-more: "Plus d'informations",
    Incident_Detection_Date: "Quand l'incident a-t-il été détecté ?",
    Incident_Detection_Description: "Comment l'incident a-t-il été détecté ?",
    Incident_Detection_Timeline: "Détaillez la chronologie de toutes les actions entreprises.",
    Incident_Detection_Communication: "Quelle a été la communication en réponse à l'incident ?",
    Incident_Detection_Preventive_Measures: "Quelles mesures préventives étaient en place au moment de l'incident ?",
    Incident_Detection_Corrective_Measures: "Quelles mesures correctives ont été prises à la suite de l'incident ?",
    Incident_Detection_Lessons_Learned: "Quelles leçons ont été tirées de l'incident ?",
    Incident_Detection_New_Measures: "Quelles nouvelles mesures préventives (adaptées) ont été mises en œuvre après l'incident ?",
    MFA_Applied: "L'authentification multi-facteurs (MFA) a-t-elle été appliquée à votre environnement impacté lors de l'incident ?",
    s-contact: "Données de contact de l'entité",
    Contact_Person: "Personne de contact",
    Organization: "Nom de l'organisation",
    Email: "Email",
    Telephone: "Téléphone",
    Location: "Où l'incident a-t-il eu lieu ?",
    s-gdpr: "Violations de données à caractère personnel liées",
    gdpr-note: "La notification NIS2 ne remplace pas la notification à l'Autorité de protection des données (RGPD art. 33, 72 h).",
    breach: "Violation", discovered: "Découverte", apd-due: "Échéance (72 h)", apd-sent: "Notifiée",
    generated: "Généré le", doc-id: "Identifiant du document",
    sev: ("1": "Critique", "2": "Majeure", "3": "Modérée", "4": "Mineure", "5": "Faible", "6": "Inconnue"),
    det: (internally_detected: "Détecté en interne", externally_detected: "Signalé par un tiers"),
    bcp: "Plan de continuité activé",
  ),
  nl: (
    title: "Werkblad NIS2-melding",
    subtitle: "Voorbereid voor het meldingsformulier van het CCB (notif.safeonweb.be), gids v1.3",
    disclaimer: "Werkblad gegenereerd uit de GRC-tool om de melding voor te bereiden. Dit is niet het formulier van het CCB: dien elke fase in op het platform van het CCB en registreer daarna de verzenddatum en het referentienummer op het incident.",
    todo: "In te vullen", limit: "max. 500 tekens", over: "meer dan 500 tekens: inkorten",
    yes: "Ja", no: "Nee", uncertain: "Onzeker",
    s-timeline: "Meldingskalender",
    stage: "Fase", due: "Uiterlijk", sent: "Verzonden", state: "Status",
    st-sent: "Verzonden", st-overdue: "Te laat", st-pending: "Te doen",
    early_warning: "Vroegtijdige waarschuwing (24 u)",
    incident_notification: "Incidentmelding (72 u)",
    final_report: "Eindverslag (1 maand)",
    not-significant: "Het incident is niet als significant aangemerkt in de zin van NIS2: er gelden geen meldingstermijnen.",
    significance-pending: "Significantie in de zin van NIS2 nog niet beoordeeld: vul ze in op het incident om de meldingstermijnen te berekenen.",
    s-entity: "Entiteit die het incident meldt",
    Submitter: "Betreffende…",
    s-nis: "Specifieke NIS-kenmerken",
    NIS_Type: "Gaat de notificatie over een essential/important NIS2 organisatie?",
    Sector: "In welke voornaamste sector(en) is de organisatie actief?",
    NIS_Notification: "Welk type NIS2-incidentmelding dient u in?",
    s-details: "Details van het incident",
    Tracking_Reference: "Referentienummer voor tracking",
    Malicious_Intent: "Denkt u dat dit incident het gevolg is van kwaad opzet?",
    Incident_Type: "Type Incident",
    Incident_Date: "Wanneer vond het incident plaats?",
    Incident_Description: "Beschrijf het incident (initiële oorzaak, impact op de organisatie, naam van het virus of de malware, getroffen gegevens en systemen, genomen maatregelen, betrokken besturingssystemen/software, enz.)",
    Assessment_Severity: "Beoordeel de ernst van het incident",
    Assessment_Consequence: "Wat zijn de gevolgen van het incident?",
    Threat_Type_Root_Cause: "Wat is de oorzaak van het incident?",
    Cross_Border_Impact: "Denkt u dat dit incident kan leiden tot grensoverschrijdende gevolgen?",
    Cross_Border_Impact_Description: "Gelieve details te geven over de potentiële grensoverschrijdende gevolgen van dit incident",
    Police_Involved: "Hebt u het incident bij de politie gemeld?",
    Help_Needed: "Hebt u ondersteuning, onderzoek of advies nodig van het CCB?",
    Actions_Taken: "Welke acties heeft u ondernomen?",
    Resolved: "Is het incident nu opgelost?",
    s-more: "Meer informatie",
    Incident_Detection_Date: "Wanneer werd het incident gedetecteerd?",
    Incident_Detection_Description: "Hoe werd het incident gedetecteerd?",
    Incident_Detection_Timeline: "Geef een gedetailleerde tijdslijn met alle genomen acties.",
    Incident_Detection_Communication: "Welke communicatie werd er gedaan naar aanleiding van het incident?",
    Incident_Detection_Preventive_Measures: "Welke preventieve maatregelen waren er op het moment van het incident?",
    Incident_Detection_Corrective_Measures: "Welke correctieve maatregelen werden er genomen naar aanleiding van het incident?",
    Incident_Detection_Lessons_Learned: "Welke lessen werden er geleerd uit het incident?",
    Incident_Detection_New_Measures: "Welke nieuwe (aangepaste) preventieve maatregelen werden er geïmplementeerd na het incident?",
    MFA_Applied: "Werd MFA toegepast op uw geïmpacteerde omgeving toen het incident zich voordeed?",
    s-contact: "Contactgegevens van de entiteit",
    Contact_Person: "Contactpersoon",
    Organization: "Naam van de organisatie",
    Email: "Email",
    Telephone: "Telefoonnummer",
    Location: "Waar vond het incident plaats?",
    s-gdpr: "Gekoppelde inbreuken in verband met persoonsgegevens",
    gdpr-note: "Een NIS2-melding vervangt niet de melding aan de Gegevensbeschermingsautoriteit (AVG art. 33, 72 u).",
    breach: "Inbreuk", discovered: "Ontdekt", apd-due: "Uiterlijk (72 u)", apd-sent: "Gemeld",
    generated: "Gegenereerd op", doc-id: "Document-ID",
    sev: ("1": "Kritiek", "2": "Groot", "3": "Matig", "4": "Klein", "5": "Laag", "6": "Onbekend"),
    det: (internally_detected: "Intern gedetecteerd", externally_detected: "Gemeld door een derde"),
    bcp: "Bedrijfscontinuïteitsplan geactiveerd",
  ),
)
#let L = labels.at(d.lang, default: labels.en)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")
#let rule = rgb("#cbd5e1")

#let chip(fill, ink, body) = box(fill: fill, inset: (x: 5pt, y: 2pt), radius: 3pt)[#text(8pt, fill: ink)[#body]]
#let todo = chip(rgb("#fef3c7"), rgb("#92400e"), L.todo)
#let empty(v) = v == none or v == "" or v == ()
#let val(v) = if empty(v) { todo } else if type(v) == array { v.join(", ") } else { v }
#let answer(v) = if empty(v) { todo } else { L.at(v, default: v) }
#let flag(b) = if b == none { todo } else if b { L.yes } else { L.no }
// CCB free-text fields hold 500 characters
#let text500(v) = if empty(v) { todo } else if v.clusters().len() > 500 {
  [#v #h(4pt) #chip(rgb("#fee2e2"), rgb("#991b1b"), L.over)]
} else { v }

// (CCB field key, mandatory, value): the label comes from the field key
#let fields(..rows) = grid(
  columns: (42%, 1fr),
  row-gutter: 8pt,
  column-gutter: 12pt,
  ..rows.pos().map(((key, required, v)) => (
    [*#L.at(key)*#if required [ \*] #h(2pt)#text(7pt, fill: muted)[#key]],
    [#v],
  )).flatten(),
)

#set page(
  paper: "a4",
  margin: (x: 2cm, top: 2cm, bottom: 2cm),
  footer: context {
    set text(8pt, fill: muted)
    grid(columns: (1fr, auto), [#L.generated #d.generated_at · #d.timezone], align(right)[#counter(page).display("1 / 1", both: true)])
  },
)
#set text(10pt, lang: d.lang)
#set par(justify: false)
#show heading.where(level: 1): set text(13pt, fill: accent)

#text(20pt, weight: "bold", fill: accent)[#L.title]
#v(-0.4em)
#text(11pt, fill: muted)[#L.subtitle]
#v(0.2em)
#text(12pt, weight: "bold")[#if inc.ref_id != "" [#inc.ref_id — ]#inc.name]
#v(0.3em)
#block(fill: rgb("#f1f5f9"), inset: 8pt, radius: 3pt, width: 100%)[#text(8.5pt, fill: muted)[#L.disclaimer]]

= #L.s-timeline
#if d.stages.len() == 0 [
  #text(fill: muted)[#if inc.significant == none { L.significance-pending } else { L.not-significant }]
] else [
  #table(
    columns: (1fr, auto, auto, auto),
    stroke: 0.4pt + rule,
    inset: 6pt,
    [*#L.stage*], [*#L.due*], [*#L.sent*], [*#L.state*],
    ..d.stages.map(s => (
      L.at(s.stage),
      s.due,
      if s.done_at == "" [-] else [#s.done_at],
      if s.done_at != "" { chip(rgb("#dcfce7"), black, L.st-sent) } else if s.overdue { chip(rgb("#fee2e2"), black, L.st-overdue) } else { chip(rgb("#fef3c7"), black, L.st-pending) },
    )).flatten(),
  )
]

= #L.s-entity
#fields(("Submitter", true, todo))

= #L.s-nis
#fields(
  ("NIS_Type", true, todo),
  ("Sector", true, todo),
  ("NIS_Notification", true, if d.next_stage != "" { L.at(d.next_stage) } else { todo }),
)

= #L.s-details
#fields(
  ("Tracking_Reference", false, val(inc.reference)),
  ("Malicious_Intent", true, answer(inc.malicious_intent)),
  ("Incident_Type", true, val(inc.incident_types)),
  ("Incident_Date", false, val(inc.occurred_at)),
  ("Incident_Description", true, [#text500(inc.description) \ #text(7pt, fill: muted)[#L.limit]]),
  ("Assessment_Severity", true, L.sev.at(inc.severity_key, default: todo)),
  ("Assessment_Consequence", true, if empty(inc.assets + inc.entities) { todo } else [
    #(inc.assets + inc.entities).join(", ")#if inc.is_bcp_activated == true [ \ #L.bcp]
  ]),
  ("Threat_Type_Root_Cause", true, text500(inc.root_cause)),
  ("Cross_Border_Impact", true, answer(inc.cross_border_impact)),
  ..if inc.cross_border_impact == "yes" { (("Cross_Border_Impact_Description", false, todo),) } else { () },
  ("Police_Involved", false, todo),
  ("Help_Needed", true, todo),
  ("Actions_Taken", false, if d.actions.len() == 0 { todo } else { d.actions.map(a => a.name).join(", ") }),
  ("Resolved", true, flag(inc.resolved)),
)

= #L.s-more
#fields(
  ("Incident_Detection_Date", true, val(inc.reported_at)),
  ("Incident_Detection_Description", true, L.det.at(inc.detection_key, default: todo)),
  ("Incident_Detection_Timeline", true, if d.timeline.len() == 0 { todo } else {
    d.timeline.map(e => [#e.timestamp: #e.entry]).join(linebreak())
  }),
  ("Incident_Detection_Communication", true, todo),
  ("Incident_Detection_Preventive_Measures", true, todo),
  ("Incident_Detection_Corrective_Measures", true, if empty(inc.resolution) and d.actions.len() == 0 { todo } else [
    #if not empty(inc.resolution) [#inc.resolution \ ]#d.actions.map(a => a.name).join(", ")
  ]),
  ("Incident_Detection_Lessons_Learned", true, todo),
  ("Incident_Detection_New_Measures", true, todo),
  ("MFA_Applied", true, todo),
)

= #L.s-contact
#fields(
  ("Contact_Person", false, val(inc.owners)),
  ("Organization", true, todo),
  ("Email", true, todo),
  ("Telephone", true, todo),
  ("Location", false, todo),
)

#if d.breaches.len() > 0 [
  = #L.s-gdpr
  #text(9pt, fill: muted)[#L.gdpr-note]
  #v(0.3em)
  #table(
    columns: (1fr, auto, auto, auto),
    stroke: 0.4pt + rule,
    inset: 6pt,
    [*#L.breach*], [*#L.discovered*], [*#L.apd-due*], [*#L.apd-sent*],
    ..d.breaches.map(b => (b.name, val(b.discovered_on), if b.due == "" [-] else [#b.due], val(b.notified_on))).flatten(),
  )
]

#v(1fr)
#text(7.5pt, fill: muted)[#L.doc-id: #raw(d.id)]
