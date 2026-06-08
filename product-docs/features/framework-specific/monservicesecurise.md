---
description: Controls export aligned with France's ANSSI MonServiceSécurisé portal
---

# MonServiceSécurisé

[MonServiceSécurisé](https://monservicesecurise.cyber.gouv.fr/) is the French ANSSI portal that lets public-sector organisations declare and track the security of their digital services. The portal accepts an Excel-based declaration of measures with a specific layout — three columns (_Intitulé_, _Description_, _Catégorie_) and a fixed taxonomy for the category column (_Gouvernance_, _Protection_, _Défense_, _Résilience_).

CISO Assistant exports your applied controls directly into that template.

## How it works

1. Open the **Applied controls** list. Optionally filter to the subset you want to submit (by domain, framework, status, …).
2. From the export menu, choose **MonServiceSécurisé Excel**. You can export everything visible, or just the filtered subset.
3. The platform fills the official ANSSI template with your controls and downloads it.

## Category mapping

The portal's four-category taxonomy maps onto the NIST CSF function tagged on each control:

| NIST CSF function on the control | MSS category |
|----------------------------------|--------------|
| Govern / Identify                | Gouvernance  |
| Protect                          | Protection   |
| Detect / Respond                 | Défense      |
| Recover                          | Résilience   |

When a control has no CSF function set, a coarse fallback derives the category from the control category (policy / process / procedure → _Gouvernance_; technical / physical → _Protection_). _Défense_ and _Résilience_ are only reachable when a CSF function is set — so tagging your detect/respond/recover controls is what makes them land in the right MSS section.

## Related

- [MonServiceSécurisé portal](https://monservicesecurise.cyber.gouv.fr/)
- [Applied controls concept](../../concepts/applied-controls.md)
