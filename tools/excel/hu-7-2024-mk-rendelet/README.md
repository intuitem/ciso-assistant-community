# `hu-7-2024-mk-rendelet` – 7/2024. (VI. 24.) MK rendelet (NIS2) · Hungarian NIS2 protective measures

[Magyar](#magyar) · [English](#english)

| fájl / file | tartalom / content |
|---|---|
| `hu-7-2024-mk-rendelet.xlsx` | a könyvtár forrása v2 Excel formátumban / the library source in the v2 Excel format |
| `../../../backend/library/libraries/hu-7-2024-mk-rendelet.yaml` | a konvertált könyvtár (`convert_library_v2.py`) / the converted library |

---

## Magyar

CISO Assistant keretrendszer-könyvtár a magyar NIS2 védelmi intézkedésekhez: a **7/2024. (VI. 24.) MK
rendelet** 2. melléklete (19 követelménycsalád, 914 követelménycsoport = védelmi intézkedés, Alap /
Jelentős / Magas biztonsági osztályok) és 3. melléklete (47 fenyegetés), kiegészítve az **1/2025. (I. 31.)
SZTFH rendelet** audit-mellékleteivel (6. melléklet: a 385 Magas osztályú követelménycsoport
audit-jellemzői; 7. melléklet: 2 148 elemi követelmény). Nyelv: `hu`, csomagoló (packager): `aafeher`.

### Felépítés

| szint | csomópont | ref_id | name | description | megvalósítási csoportok |
|---|---|---|---|---|---|
| 1 | követelménycsalád (19) | `1` … `19` | a család neve | – | – |
| 2 | követelménycsoport / védelmi intézkedés (914, értékelhető) | `1.1` | a rendeletben szereplő megnevezés (a kiterjesztések „Alap – Kiterjesztés” alakban) | a követelmény szövege, pontonként külön sorban | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR` = az osztály, amelyben elvárt × a 6. melléklet szerinti jelleg; `O` = egyik osztálynál sem elvárt |
| 3 | elemi követelmény (2 148, értékelhető) | `K01.001_P1`, `K01.001_O.1.1.1.1.a` | a hivatalos hivatkozási kód (`K01.001_P[1]`, `K01.001_O.1.1.1.1.(a)`) | az SZTFH 7. melléklet szövege | `AE-SZ` … `ME-EIR` = a szülő követelménycsoport csoportjai |

Az elemi követelmény `ref_id`-ja a kód szögletes zárójelek nélküli alakja (a kód maga a `name`
mezőben van). A 2. melléklet 20.6. pontja szerint a követelmények szövege a követelménycsoport
megnevezésével együtt értelmezendő. A 6.27. követelménycsoporthoz a 7. melléklet nem tartalmaz elemi
követelményt.

### Megvalósítási csoportok

A csoport a biztonsági osztályt és a követelménycsoport SZTFH 6. melléklet B oszlopa szerinti jellegét
együtt jelöli: `SZ` = szervezeti szintű, `EIR` = EIR-szintű. Az osztályok egymásra épülnek
(A 164 ⊂ J 302 ⊂ M 385 követelménycsoport), ezért például az `M-SZ` a Magas osztályban elvárt összes
szervezeti szintű csoportot tartalmazza, az alacsonyabb osztályokét is. Az egyik osztálynál sem elvárt
529 kiegészítő védelmi intézkedés (2. melléklet 20.4. pont; a 6. melléklet nem ad hozzájuk jelleget)
az `O` csoport. Az elemi szint külön kapcsolható be: az `ME-EIR` az `M-EIR` mellé, a `JE-SZ` a `J-SZ`
mellé választandó, és így tovább. Elemi csoport nélkül az értékelés a követelménycsoportoknál megáll;
elemi csoport önmagában a szülő csoportokat csak a fa szerkezete miatt tartja meg.

| csoport | követelménycsoport | csoport | elemi követelmény |
|---|---|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 | `AE-SZ` / `AE-EIR` | 717 / 683 |
| `J-SZ` / `J-EIR` | 108 / 194 | `JE-SZ` / `JE-EIR` | 815 / 1 064 |
| `M-SZ` / `M-EIR` | 132 / 253 | `ME-SZ` / `ME-EIR` | 896 / 1 252 |
| `O` | 529 | | |

A 19 családból 16 egynemű (szervezeti szintű: 1., 3., 9–12., 14., 19.; EIR-szintű: 2., 4–8., 17., 18.);
a 13., 15. és 16. család vegyes.

### Használat: csoportok kiválasztása egy audithoz

Az SZTFH rendelet 5. melléklete szerint a szervezeti szintű követelménycsoportok egyszer, valamennyi
EIR-re egységesen, a szervezet legmagasabb biztonsági osztályú EIR-je szerint vizsgálandók (2.2.1.1.,
2.2.3.1., 2.2.3.2. pont), az EIR-szintűek EIR-enként (2.2.1.2. pont), és az EIR védelmi megfelelési
indexébe (VMI) a szervezeti szintű csoportok is beszámítanak (2.2.5.7. pont). A CISO Assistant a
kiválasztott csoportok uniójával szűri a követelményfát, ezért:

* **Szervezeti audit**: a szervezet legmagasabb osztályának `SZ` csoportja, például `M-SZ`
  (elemi szinttel: + `ME-SZ`).
* **EIR-audit**: az EIR osztályának `EIR` csoportja, például `A-EIR` (+ `AE-EIR`). Ha az auditnak a
  VMI miatt a szervezeti szintű csoportokat is tartalmaznia kell, a legmagasabb osztály `SZ` csoportja
  hozzávehető (`A-EIR` + `M-SZ`).
* **Egyetlen EIR-rel rendelkező szervezet**: az osztály `SZ` és `EIR` csoportja együtt, például
  `J-SZ` + `J-EIR`.

Hogy a szervezeti szintű csoportokat ne kelljen minden EIR-auditban újra értékelni, az EIR-audit a
szervezeti audit *baseline*-jával hozható létre: a CISO Assistant azonos keretrendszernél átmásolja a
közös követelmények eredményeit és válaszait. Az alkalmazás két audit eredményét nem vonja össze egy
pontszámba, így a szervezeti és az EIR-auditot átfogó VMI-t az alkalmazáson kívül kell számolni.

### Megjegyzések (annotation)

A követelménycsoport megjegyzése tartalmazza az SZTFH 6. melléklet szerinti audit-jellemzőket
(szervezeti / EIR-szintű, kötelező dokumentumvizsgálat / interjú / teszt, Biztosító / Támogató típus,
„az értékelésből nem kizárható”), a kihirdetett szöveg elírásait (változatlanul átvéve, a helyes
alakkal), az SZTFH mellékletek és az NKI táblázat eltérő névírását, valamint az 5.3. és 5.4.
követelménycsoportnál a 18/2024. (XII. 30.) MK rendelet szerinti módosítás tényét. Az elemi
követelmények megjegyzése rögzíti a Magyar Közlönyben hibásan szedett kódot (`K013.003_P[1]`,
`K01.016_ O.1.16`) és a négy nem létező kódra mutató hivatkozást a nyilvánvalóan értendő kóddal.

### Fenyegetések

A 3. melléklet 47 fenyegetése `threats` objektumként (`ref_id` 1–47; a leírás a potenciálisan érintett
alapelvek: bizalmasság (B), sértetlenség (S), rendelkezésre állás (R)). A rendelet a védelmi
intézkedéseket nem rendeli fenyegetésekhez.

### Források és szövegállapot

* 7/2024. (VI. 24.) MK rendelet: az njt.hu szerinti egységes szerkezet 2025. 01. 02-i állapota
  (a 18/2024. (XII. 30.) MK rendelet az 5.3. és 5.4. követelménycsoportot és az 1. melléklet 1. pontját
  cserélte), a Magyar Közlöny 2024/68. és 2024/137. számával és az NKI „Védelmi intézkedések
  katalógusa” táblázatával (1.0, 2024. december) egybevetve.
* 1/2025. (I. 31.) SZTFH rendelet: a Magyar Közlöny 2025/8. számában kihirdetett szöveg (a
  6/2026. (VI. 8.) SZTFH rendelet a 6–7. mellékletet nem érinti).
* A kihirdetett szöveg elírásai változatlanul szerepelnek, a megjegyzésekben jelölve.
* A jogszabályok szövege nem áll szerzői jogi védelem alatt (Szjt. 1. § (4) bekezdés).

### Nem tartalmazza

Az 1. mellékletet (osztályba sorolás), a Kibertv. és a 418/2024. (XII. 23.) Korm. rendelet szervezeti
kötelezettségeit, az NKI táblázat hivatkozásait (41/2015. BM r., ISO 27001, NIST SP 800-53) és az
SZTFH 5. melléklet szerinti VMI / SZEKI pontozást (nincs pontszám-definíció, a CISO Assistant
alapértelmezett skálája érvényes).

### Ellenőrzés

A könyvtár a CISO Assistant 4.1.1 verziójába betöltve (2026. 10. 11.): az Excel forrás átmegy az
alkalmazáson belüli konverzión, a YAML betöltődik (3 081 követelménycsomópont, 13 megvalósítási csoport,
47 fenyegetés). A különböző csoportokkal létrehozott auditok a várt fát adják (értékelhető
csomópontok): `A-SZ` 82, `A-EIR` 82, `J-SZ` 108, `J-EIR` 194, `M-SZ` 132, `M-EIR` 253, `O` 529,
`M-SZ`+`M-EIR` 385, `M-SZ`+`ME-SZ` 1 028, `M-EIR`+`ME-EIR` 1 505, mind a négy Magas csoport 2 533,
`A-EIR`+`M-SZ` 214, kiválasztás nélkül 3 062. A szervezeti auditot baseline-ként használó EIR-audit
megkapta az ott rögzített eredményt.

---

## English

CISO Assistant framework library of the Hungarian NIS2 protective-measures catalogue:
**7/2024. (VI. 24.) MK rendelet**, annex 2 (19 követelménycsalád = families, 914 követelménycsoport =
protective measures, security classes Alap / Jelentős / Magas = basic / significant / high) and annex 3
(47 threats), extended with the audit annexes of **1/2025. (I. 31.) SZTFH rendelet** (annex 6: audit
metadata of the 385 Magas measures; annex 7: 2,148 elemi követelmény = elementary requirements).
Locale `hu`, packager `aafeher`.

### Structure

| depth | node | ref_id | name | description | implementation groups |
|---|---|---|---|---|---|
| 1 | követelménycsalád / family (19) | `1` … `19` | family name | – | – |
| 2 | követelménycsoport / protective measure (914, assessable) | `1.1` | the name as printed in the decree (enhancements as "Base – Enhancement") | the requirement text, one numbered point per line | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR` = class in which it is required × annex 6 nature; `O` = required in no class |
| 3 | elemi követelmény / elementary requirement (2,148, assessable) | `K01.001_P1`, `K01.001_O.1.1.1.1.a` | the official code (`K01.001_P[1]`, `K01.001_O.1.1.1.1.(a)`) | the requirement text of SZTFH annex 7 | `AE-SZ` … `ME-EIR` = the groups of the parent measure |

The `ref_id` of an elementary requirement is its code without the square brackets (the code itself is
the `name`). Annex 2 point 20.6 says the requirement texts are to be read together with the name of
the measure. Measure 6.27 has no elementary requirement in annex 7.

### Implementation groups

A group combines the security class with the nature of the measure given in SZTFH annex 6 column B:
`SZ` = szervezeti szintű (organisational level), `EIR` = EIR-szintű (per system; EIR = elektronikus
információs rendszer, electronic information system). The classes are nested (A 164 ⊂ J 302 ⊂ M 385
measures), so `M-SZ` holds every organisational measure required at Magas, including those of the
lower classes. The 529 measures required in no class ("kiegészítő védelmi intézkedések", annex 2
point 20.4; annex 6 gives them no nature) form the group `O`. The elementary level is opt-in: select
`ME-EIR` together with `M-EIR`, `JE-SZ` with `J-SZ`, and so on. Without an elementary group the
assessment stops at the measures; with an elementary group alone the parent measures stay only as
ancestors.

| group | measures | group | elementary requirements |
|---|---|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 | `AE-SZ` / `AE-EIR` | 717 / 683 |
| `J-SZ` / `J-EIR` | 108 / 194 | `JE-SZ` / `JE-EIR` | 815 / 1,064 |
| `M-SZ` / `M-EIR` | 132 / 253 | `ME-SZ` / `ME-EIR` | 896 / 1,252 |
| `O` | 529 | | |

16 of the 19 families are of one nature (organisational: 1, 3, 9–12, 14, 19; system level: 2, 4–8,
17, 18); families 13, 15 and 16 are mixed.

### Usage: selecting groups for an audit

SZTFH annex 5 audits organisational-level groups once, for all systems, at the class of the
organisation's highest-class system (points 2.2.1.1., 2.2.3.1., 2.2.3.2.), system-level groups per
system (2.2.1.2.), and counts the organisational groups in the compliance index (VMI) of every system
(2.2.5.7.). CISO Assistant filters the requirement tree by the union of the selected groups, hence:

* **Organisational audit**: the `SZ` group of the organisation's highest class, e.g. `M-SZ`
  (+ `ME-SZ` for the elementary level).
* **System audit**: the `EIR` group of the system's class, e.g. `A-EIR` (+ `AE-EIR`). Add the `SZ`
  group of the highest class (`A-EIR` + `M-SZ`) when the audit must also carry the organisational
  groups for the VMI of that system.
* **Organisation with a single system**: `SZ` + `EIR` of its class, e.g. `J-SZ` + `J-EIR`.

To avoid assessing the organisational groups again in every system audit, create the system audit
with the organisational audit as its *baseline*: CISO Assistant copies the results and answers of the
requirements the two audits share (same framework). The application does not merge the results of two
audits into one score, so a VMI that spans an organisational and a system audit has to be computed
outside it.

### Annotations

The annotation of a measure holds the SZTFH annex 6 audit metadata (organisational / system level,
mandatory document review / interview / test, "Biztosító" / "Támogató" type, "cannot be excluded from
the assessment"), the typos of the published text (kept as published, with the correct form), the
different spellings used by the SZTFH annexes and the NKI catalogue, and, for measures 5.3 and 5.4,
the amendment by 18/2024. (XII. 30.) MK rendelet. The annotation of an elementary requirement records
the code as misprinted in the gazette (`K013.003_P[1]`, `K01.016_ O.1.16`) and the four
cross-references to non-existent codes with the code evidently meant.

### Threats

The 47 threats of annex 3 as a `threats` object (`ref_id` 1–47; the description lists the affected
principles: confidentiality (B), integrity (S), availability (R)). The decree does not map measures to
threats.

### Sources and text state

* 7/2024. (VI. 24.) MK rendelet: the consolidated text on njt.hu as of 2025-01-02 (18/2024. (XII. 30.)
  MK rendelet replaced measures 5.3 and 5.4 and annex 1 point 1), cross-checked against Magyar Közlöny
  2024/68 and 2024/137 and the NKI "Védelmi intézkedések katalógusa" table (1.0, December 2024).
* 1/2025. (I. 31.) SZTFH rendelet: the text promulgated in Magyar Közlöny 2025/8 (6/2026. (VI. 8.)
  SZTFH rendelet does not touch annexes 6–7).
* The typos of the published text are kept as published and flagged in the annotations.
* Hungarian legal texts are not subject to copyright (Act LXXVI of 1999, Section 1(4)).

### Not included

Annex 1 (classification method), the organisational obligations of the Kibertv. and of 418/2024.
(XII. 23.) Korm. rendelet, the NKI cross-references (41/2015. BM r., ISO 27001, NIST SP 800-53) and
the VMI / SZEKI audit scoring of SZTFH annex 5 (no scores definition; CISO Assistant's default scale
applies).

### Verification

Loaded into CISO Assistant 4.1.1 on 2026-10-11: the Excel source passes the in-app conversion, the
YAML loads (3,081 requirement nodes, 13 implementation groups, 47 threats). Audits created with
different groups show the expected requirement trees (assessable nodes): `A-SZ` 82, `A-EIR` 82,
`J-SZ` 108, `J-EIR` 194, `M-SZ` 132, `M-EIR` 253, `O` 529, `M-SZ`+`M-EIR` 385, `M-SZ`+`ME-SZ` 1,028,
`M-EIR`+`ME-EIR` 1,505, all four Magas groups 2,533, `A-EIR`+`M-SZ` 214, and 3,062 without a
selection. A system audit created with the organisational audit as baseline received the result
recorded there.
