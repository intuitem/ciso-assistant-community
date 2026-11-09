// GDPR art. 33 notification worksheet following the APD/GBA online form, part 1
// (user manual "Champs pour la notification d'une violation de données – partie 1", 04-2026).
// Payload: `core.generators.breach_notification_context` via sys.inputs.data.
// One file for en/fr/nl: numbering follows the authority's form, only labels vary.

#let d = json(bytes(sys.inputs.data))
#let b = d.breach

#let labels = (
  en: (
    title: "Personal data breach notification worksheet",
    subtitle: "GDPR art. 33: prepared for the Data Protection Authority (APD/GBA), form part 1",
    disclaimer: "Worksheet generated from the GRC record. It is not the authority's form: enter these answers in the APD/GBA online form (part 1) within 72 hours of discovering the breach, then record the date and reference on the breach. Part 2 can be completed later from the company account; it is considered final 21 days after part 1 is sent.",
    todo: "To complete", yes: "Yes", no: "No", mandatory: "* mandatory in the authority's form",
    s-deadline: "Follow-up",
    due: "Deadline (72h after discovery)", notified: "Authority notified on", ref: "Authority reference",
    not-required: "Not required (no risk to individuals)",
    s2: "2. Introduction", f2: "Under which regulation are you notifying?", legal: "GDPR, art. 33",
    nis2-hint: "Also notify the CCB (notif.safeonweb.be) if the entity is subject to NIS2.",
    s3: "3. Organisation",
    f32: "3.2 Organisation name", f33: "3.3 Main establishment (enterprise number / country)", f34: "3.4 Sector",
    f35: "3.5 Address of the controller", f36: "3.6 Controller e-mail", f37: "3.7 Operator registered with the BIPT?",
    f38: "3.8 Listed company?", f39: "3.9 Did the breach occur in a processing entrusted to a processor?",
    f391: "3.9.1 Which processor?", f310: "3.10 Contact person for the breach (name, first name, role, phone, e-mail)",
    s4: "4. International level",
    f411: "4.1.1 Consequences for data subjects in several countries?", f412: "4.1.2 Countries and number of data subjects per country",
    f421: "4.2.1 Notified to other data protection authorities?",
    s5: "5. Timeline",
    f51: "5.1 / 5.1.1 Date and time the breach occurred", f52: "5.2 Date and time the breach was discovered",
    f53: "5.3 Justification for late notification", f54: "5.4 Has the breach been resolved?",
    f541: "5.4.1 Reason", f542: "5.4.2 Resolved on", not-resolved: "Not yet resolved", resolved: "Resolved",
    estimated: "(state whether exact or estimated)",
    s6: "6. Processing",
    f61: "6.1 Purposes of the processing", f62: "6.2 Nature of the personal data affected",
    f63: "6.3 Number of data subjects affected", sensitive: "special category", processings: "Processing activities (register)",
    exact: "(state whether exact, or give a min/max range)",
    s7: "7. Causes",
    f71: "7.1 Type of breach (form list: misdirected communication, misconfigured access, lost or stolen device, publication or destruction error, cyber-attack, other)",
    f72: "7.2 Summary of the breach (max. 2500 characters)", recorded-as: "Recorded in the tool as",
    s8: "8. Communication",
    f81: "8.1 Already notified to the data subjects?", f81d: "8.1.1 Individually or collectively, channel, number, date",
    f82: "8.2 Will you still notify the data subjects?",
    s9: "9. Additional information (max. 2000 characters)",
    risk: "Risk to individuals (part 2, 9.2)", consequences: "Likely consequences (part 2, 9.3)",
    measures: "Measures taken or planned (part 2, 8.2 / 8.3)", incident: "Linked security incident",
    too-long: "exceeds the form's limit",
    generated: "Generated", doc-id: "Document ID",
    types: (privacy_destruction: "Destruction", privacy_loss: "Loss", privacy_alteration: "Alteration", privacy_unauthorized_disclosure: "Unauthorised disclosure", privacy_unauthorized_access: "Unauthorised access", privacy_other: "Other"),
    risks: (privacy_no_risk: "Probably no risk", privacy_risk: "Probable risk", privacy_high_risk: "Probable high risk"),
  ),
  fr: (
    title: "Fiche de notification de violation de données",
    subtitle: "RGPD art. 33 : préparée pour l'Autorité de protection des données (APD), formulaire partie 1",
    disclaimer: "Fiche générée depuis l'outil GRC. Ce n'est pas le formulaire de l'autorité : reportez ces réponses dans le formulaire en ligne de l'APD (partie 1) au plus tard 72 heures après la découverte, puis enregistrez la date et la référence sur la violation. La partie 2 se complète ensuite depuis le compte entreprise ; elle est considérée comme définitive 21 jours après l'envoi de la partie 1.",
    todo: "À compléter", yes: "Oui", no: "Non", mandatory: "* obligatoire dans le formulaire de l'autorité",
    s-deadline: "Suivi",
    due: "Échéance (72 h après la découverte)", notified: "Autorité notifiée le", ref: "Référence de l'autorité",
    not-required: "Non requise (pas de risque pour les personnes)",
    s2: "2. Introduction", f2: "En vertu de quelle réglementation procédez-vous à la notification ?", legal: "RGPD, article 33",
    nis2-hint: "Si l'entité est soumise à NIS2, notifiez aussi le CCB (notif.safeonweb.be).",
    s3: "3. Organisation",
    f32: "3.2 Nom de l'organisation", f33: "3.3 Établissement principal (numéro d'entreprise / pays)", f34: "3.4 Secteur",
    f35: "3.5 Adresse et coordonnées du responsable du traitement", f36: "3.6 E-mail du responsable du traitement", f37: "3.7 Opérateur enregistré auprès de l'IBPT ?",
    f38: "3.8 Entreprise cotée en bourse ?", f39: "3.9 La violation a-t-elle eu lieu dans le cadre d'un traitement confié à un sous-traitant ?",
    f391: "3.9.1 De quel sous-traitant s'agit-il ?", f310: "3.10 Personne de contact pour la violation (nom, prénom, fonction, téléphone, e-mail)",
    s4: "4. Niveau international",
    f411: "4.1.1 Conséquences pour des personnes concernées dans plusieurs pays ?", f412: "4.1.2 Pays et nombre de personnes concernées par pays",
    f421: "4.2.1 Notifiée à d'autres autorités de protection des données ?",
    s5: "5. Ligne du temps",
    f51: "5.1 / 5.1.1 Date et heure auxquelles la violation s'est produite", f52: "5.2 Date et heure de la découverte de la violation",
    f53: "5.3 Justification de la notification tardive", f54: "5.4 La violation a-t-elle été résolue ?",
    f541: "5.4.1 La raison est la suivante", f542: "5.4.2 Résolue le", not-resolved: "Pas encore résolue", resolved: "Résolue",
    estimated: "(préciser : exacte ou estimée)",
    s6: "6. Traitement",
    f61: "6.1 Finalités du traitement", f62: "6.2 Nature des données à caractère personnel touchées",
    f63: "6.3 Nombre de personnes concernées", sensitive: "catégorie particulière", processings: "Activités de traitement (registre)",
    exact: "(préciser : nombre exact, ou fourchette min/max)",
    s7: "7. Causes",
    f71: "7.1 Type de violation (liste du formulaire : communication mal adressée, accès mal configuré, appareil perdu ou volé, erreur de publication ou de destruction, cyberattaque, autre)",
    f72: "7.2 Résumé de la violation (2500 caractères max.)", recorded-as: "Enregistré dans l'outil comme",
    s8: "8. Communication",
    f81: "8.1 Avez-vous déjà notifié la violation aux personnes concernées ?", f81d: "8.1.1 Individuellement ou collectivement, canal, nombre, date",
    f82: "8.2 Allez-vous encore notifier la violation aux personnes concernées ?",
    s9: "9. Informations supplémentaires (2000 caractères max.)",
    risk: "Risque pour les personnes (partie 2, 9.2)", consequences: "Conséquences probables (partie 2, 9.3)",
    measures: "Mesures prises ou prévues (partie 2, 8.2 / 8.3)", incident: "Incident de sécurité lié",
    too-long: "dépasse la limite du formulaire",
    generated: "Généré le", doc-id: "Identifiant du document",
    types: (privacy_destruction: "Destruction", privacy_loss: "Perte", privacy_alteration: "Altération", privacy_unauthorized_disclosure: "Divulgation non autorisée", privacy_unauthorized_access: "Accès non autorisé", privacy_other: "Autre"),
    risks: (privacy_no_risk: "Probablement aucun risque", privacy_risk: "Risque probable", privacy_high_risk: "Risque élevé probable"),
  ),
  nl: (
    title: "Werkblad melding van een datalek",
    subtitle: "AVG art. 33: voorbereid voor de Gegevensbeschermingsautoriteit (GBA), formulier deel 1",
    disclaimer: "Werkblad gegenereerd uit de GRC-tool. Dit is niet het formulier van de autoriteit: neem deze antwoorden over in het online formulier van de GBA (deel 1), uiterlijk 72 uur na de ontdekking, en registreer daarna de datum en referentie op het datalek. Deel 2 wordt later ingevuld via de bedrijfsaccount; het wordt 21 dagen na de verzending van deel 1 als definitief beschouwd.",
    todo: "In te vullen", yes: "Ja", no: "Nee", mandatory: "* verplicht in het formulier van de autoriteit",
    s-deadline: "Opvolging",
    due: "Uiterlijk (72 u na de ontdekking)", notified: "Autoriteit gemeld op", ref: "Referentie van de autoriteit",
    not-required: "Niet vereist (geen risico voor personen)",
    s2: "2. Inleiding", f2: "Op grond van welke regelgeving meldt u?", legal: "AVG, artikel 33",
    nis2-hint: "Meld ook aan het CCB (notif.safeonweb.be) als de entiteit onder NIS2 valt.",
    s3: "3. Organisatie",
    f32: "3.2 Naam van de organisatie", f33: "3.3 Hoofdvestiging (ondernemingsnummer / land)", f34: "3.4 Sector",
    f35: "3.5 Adres en contactgegevens van de verwerkingsverantwoordelijke", f36: "3.6 E-mail van de verwerkingsverantwoordelijke", f37: "3.7 Operator geregistreerd bij het BIPT?",
    f38: "3.8 Beursgenoteerde onderneming?", f39: "3.9 Vond het datalek plaats bij een verwerking die aan een verwerker is toevertrouwd?",
    f391: "3.9.1 Welke verwerker?", f310: "3.10 Contactpersoon voor het datalek (naam, voornaam, functie, telefoon, e-mail)",
    s4: "4. Internationaal niveau",
    f411: "4.1.1 Gevolgen voor betrokkenen in meerdere landen?", f412: "4.1.2 Landen en aantal betrokkenen per land",
    f421: "4.2.1 Gemeld aan andere gegevensbeschermingsautoriteiten?",
    s5: "5. Tijdlijn",
    f51: "5.1 / 5.1.1 Datum en tijdstip waarop het datalek plaatsvond", f52: "5.2 Datum en tijdstip van de ontdekking van het datalek",
    f53: "5.3 Rechtvaardiging van de laattijdige melding", f54: "5.4 Is het datalek opgelost?",
    f541: "5.4.1 Reden", f542: "5.4.2 Opgelost op", not-resolved: "Nog niet opgelost", resolved: "Opgelost",
    estimated: "(vermelden: exact of geschat)",
    s6: "6. Verwerking",
    f61: "6.1 Doeleinden van de verwerking", f62: "6.2 Aard van de getroffen persoonsgegevens",
    f63: "6.3 Aantal getroffen betrokkenen", sensitive: "bijzondere categorie", processings: "Verwerkingsactiviteiten (register)",
    exact: "(vermelden: exact aantal, of min/max)",
    s7: "7. Oorzaken",
    f71: "7.1 Type datalek (lijst van het formulier: verkeerd geadresseerde communicatie, verkeerd geconfigureerde toegang, verloren of gestolen toestel, publicatie- of vernietigingsfout, cyberaanval, andere)",
    f72: "7.2 Samenvatting van het datalek (max. 2500 tekens)", recorded-as: "In de tool geregistreerd als",
    s8: "8. Communicatie",
    f81: "8.1 Hebt u het datalek al aan de betrokkenen gemeld?", f81d: "8.1.1 Individueel of collectief, kanaal, aantal, datum",
    f82: "8.2 Zult u het datalek nog aan de betrokkenen melden?",
    s9: "9. Bijkomende informatie (max. 2000 tekens)",
    risk: "Risico voor personen (deel 2, 9.2)", consequences: "Waarschijnlijke gevolgen (deel 2, 9.3)",
    measures: "Genomen of geplande maatregelen (deel 2, 8.2 / 8.3)", incident: "Gekoppeld beveiligingsincident",
    too-long: "overschrijdt de limiet van het formulier",
    generated: "Gegenereerd op", doc-id: "Document-ID",
    types: (privacy_destruction: "Vernietiging", privacy_loss: "Verlies", privacy_alteration: "Wijziging", privacy_unauthorized_disclosure: "Ongeoorloofde openbaarmaking", privacy_unauthorized_access: "Ongeoorloofde toegang", privacy_other: "Andere"),
    risks: (privacy_no_risk: "Waarschijnlijk geen risico", privacy_risk: "Waarschijnlijk risico", privacy_high_risk: "Waarschijnlijk hoog risico"),
  ),
)
#let L = labels.at(d.lang, default: labels.en)

#let accent = rgb("#1e3a8a")
#let muted = rgb("#6b7280")

#let todo = box(fill: rgb("#fef3c7"), inset: (x: 5pt, y: 2pt), radius: 3pt)[#text(8pt, fill: rgb("#92400e"))[#L.todo]]
#let hint(t) = text(8pt, fill: muted)[#t]
#let val(v) = if v == none or v == "" or v == () { todo } else if type(v) == array { v.join(", ") } else { v }
#let count(n) = if n == none or n == 0 { todo } else { str(n) }
#let limited(v, max) = if v == "" { todo } else if v.clusters().len() > max {
  [#v #h(4pt) #text(8pt, fill: rgb("#b91c1c"))[(#v.clusters().len() / #max — #L.too-long)]]
} else { v }

// k* marks a field mandatory in the authority's form
#let fields(..rows) = grid(
  columns: (42%, 1fr),
  row-gutter: 7pt,
  column-gutter: 12pt,
  ..rows.pos().map(((k, v)) => ([*#k*], [#v])).flatten(),
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
#text(12pt, weight: "bold")[#if b.ref_id != "" [#b.ref_id — ]#b.name]
#v(0.3em)
#block(fill: rgb("#f1f5f9"), inset: 8pt, radius: 3pt, width: 100%)[#text(8.5pt, fill: muted)[#L.disclaimer]]
#hint(L.mandatory)

= #L.s-deadline
#fields(
  (L.due, if b.due == "" { L.not-required } else { b.due }),
  (L.notified, val(b.notified_on)),
  (L.ref, val(b.notification_ref)),
)

= #L.s2
#fields((L.f2 + "*", [#L.legal \ #hint(L.nis2-hint)]))

= #L.s3
#fields(
  (L.f32 + "*", todo),
  (L.f33 + "*", todo),
  (L.f34, todo),
  (L.f35 + "*", todo),
  (L.f36 + "*", todo),
  (L.f37 + "*", todo),
  (L.f38 + "*", todo),
  (L.f39 + "*", if b.processors.len() > 0 { L.yes } else { todo }),
  ..if b.processors.len() > 0 { ((L.f391 + "*", b.processors.join(", ")),) } else { () },
  (L.f310 + "*", val(b.assigned_to)),
)

= #L.s4
#fields(
  (L.f411 + "*", todo),
  (L.f412, todo),
  (L.f421 + "*", if b.authorities.len() > 0 [#todo #hint(b.authorities.join(", "))] else { todo }),
)

= #L.s5
#fields(
  (L.f51 + "*", if b.occurred_at == "" { todo } else [#b.occurred_at #hint(L.estimated)]),
  (L.f52 + "*", val(b.discovered_on)),
  ..if b.late { ((L.f53 + "*", todo),) } else { () },
  (L.f54 + "*", if b.resolved { L.resolved } else { L.not-resolved }),
  if b.resolved { (L.f542 + "*", todo) } else { (L.f541 + "*", todo) },
  ..if b.incident != "" { ((L.incident, b.incident),) } else { () },
)

= #L.s6
#fields(
  (L.f61 + "*", val(b.purposes)),
  (L.processings, val(b.processings)),
  (L.f62 + "*", if b.personal_data.len() == 0 { todo } else {
    b.personal_data.map(pd => pd.name + if pd.category != "" { " (" + pd.category + ")" } else { "" } + if pd.sensitive { " — " + L.sensitive } else { "" }).join(", ")
  }),
  (L.f63 + "*", if b.subjects_count == 0 { todo } else [#b.subjects_count #hint(L.exact)]),
)

= #L.s7
#fields(
  (L.f71 + "*", [#todo #h(4pt) #hint(L.recorded-as + ": " + L.types.at(b.breach_type, default: b.breach_type))]),
  (L.f72 + "*", limited(b.description, 2500)),
)

= #L.s8
#fields(
  (L.f81 + "*", if b.subjects_notified_on != "" { L.yes + " (" + b.subjects_notified_on + ")" } else { todo }),
  ..if b.subjects_notified_on != "" { ((L.f81d + "*", todo),) } else { ((L.f82 + "*", todo),) },
)

= #L.s9
#fields(
  (L.risk, L.risks.at(b.risk_level, default: todo)),
  (L.consequences, val(b.consequences)),
  (L.measures, if b.measures.len() == 0 { todo } else { b.measures.map(m => m.name).join(", ") }),
)
#if b.observation != "" [
  #v(0.4em)
  #limited(b.observation, 2000)
]

#v(1fr)
#text(7.5pt, fill: muted)[#L.doc-id: #raw(d.id)]
