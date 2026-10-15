# `hungary/` – Magyar NIS2 könyvtárak · Hungarian NIS2 libraries (7/2024. (VI. 24.) MK rendelet, 1/2025. (I. 31.) SZTFH rendelet)

[Magyar](#magyar) · [English](#english)

| fájl / file | tartalom / content |
|---|---|
| `hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek.xlsx` | az elemi követelmények könyvtárának forrása v2 Excel formátumban / the source of the elementary-requirements library in the v2 Excel format |
| `hu-7-2024-mk-rendelet.xlsx` | a védelmi intézkedések katalógusának forrása v2 Excel formátumban / the source of the protective-measures catalogue in the v2 Excel format |
| `hu-7-2024-mk-rendelet-fenyegetesek.xlsx` | a fenyegetéskatalógus forrása v2 Excel formátumban / the source of the threat catalogue in the v2 Excel format |
| `../../../backend/library/libraries/hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek.yaml` | a konvertált könyvtár (`convert_library_v2.py`) / the converted library |
| `../../../backend/library/libraries/hu-7-2024-mk-rendelet.yaml` | a konvertált védelmiintézkedés-katalógus / the converted protective-measures catalogue |
| `../../../backend/library/libraries/hu-7-2024-mk-rendelet-fenyegetesek.yaml` | a konvertált fenyegetéskatalógus / the converted threat catalogue |

---

## Magyar

CISO Assistant könyvtárak a magyar NIS2 szabályozáshoz: a **7/2024. (VI. 24.) MK rendelet** (2. melléklet:
védelmi intézkedések katalógusa, 3. melléklet: fenyegetéskatalógus) és az **1/2025. (I. 31.) SZTFH rendelet**
(6. melléklet: audit-jellemzők, 7. melléklet: elemi követelmények) mellékleteiből. Nyelv: `hu`, csomagoló
(packager): `aafeher`.

### A könyvtárcsalád

| könyvtár | állapot | tartalom | rendeltetés |
|---|---|---|---|
| `hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` | kész | az SZTFH rendelet 7. melléklete szerinti 2 148 elemi követelmény a 7/2024. MK rendelet 2. mellékletének szerkezetében (19 követelménycsalád, 914 követelménycsoport), a 6. melléklet audit-jellemzőivel | az SZTFH-audit nézete: auditfelkészülés; az értékelés egysége az elemi követelmény |
| `hu-7-2024-mk-rendelet-fenyegetesek` | kész | a 7/2024. MK rendelet 3. mellékletének 47 fenyegetése | fenyegetéskatalógus a kockázatértékeléshez, mindkét keretrendszer mellé |
| `hu-7-2024-mk-rendelet` | kész | ugyanaz a 914 követelménycsoport elemi szint nélkül, értékelhető követelménycsoportokkal, ugyanazzal a 7 megvalósítási csoporttal | a jogszabályi kötelezettség követelménycsoport-szinten: kontrollkezelés |
| `mapping-hu-7-2024-mk-rendelet-and-hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` | tervezett | minden elemi követelmény a szülő követelménycsoportjához rendelve (`superset`; a fordított irány generált) | átjárhatóság a két keretrendszer között, például a másik keretrendszer auditját baseline-ként használó audit előtöltése |

A két keretrendszer csomópontjainak `ref_id`-ja azonos (`1.1`, `K01.001_P1` …), csak az URN-előtag
különbözik.

### `hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` – elemi követelmények (NIS2 audit)

Az 1/2025. (I. 31.) SZTFH rendelet 7. melléklete szerinti 2 148 elemi követelmény a 7/2024. (VI. 24.) MK
rendelet 2. mellékletének szerkezetében: 19 követelménycsalád, 914 követelménycsoport (védelmi intézkedés) az
Alap / Jelentős / Magas biztonsági osztályok jelölésével, a 6. melléklet szerinti audit-jellemzőkkel a
megjegyzésekben. Az értékelés egysége az elemi követelmény: az a 384 követelménycsoport, amelyhez elemi
követelmény tartozik, csak címsor, a többi 530 maga értékelhető.

#### Felépítés

| szint | csomópont | ref_id | name | description | megvalósítási csoportok |
|---|---|---|---|---|---|
| 1 | követelménycsalád (19) | `1` … `19` | a család neve | – | – |
| 2 | követelménycsoport / védelmi intézkedés (914; értékelhető az az 530, amelyhez nem tartozik elemi követelmény) | `1.1` | a rendeletben szereplő megnevezés (a kiterjesztések „Alap – Kiterjesztés” alakban) | a követelmény szövege, pontonként külön sorban | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR` = az osztály, amelyben elvárt × a 6. melléklet szerinti jelleg; `KIEG` = egyik osztálynál sem elvárt |
| 3 | elemi követelmény (2 148, értékelhető) | `K01.001_P1`, `K01.001_O.1.1.1.1.a` | a hivatalos hivatkozási kód (`K01.001_P[1]`, `K01.001_O.1.1.1.1.(a)`) | az SZTFH 7. melléklet szövege | a szülő követelménycsoport csoportjai |

Az elemi követelmény `ref_id`-ja a kód szögletes zárójelek nélküli alakja (a kód maga a `name`
mezőben van). A 2. melléklet 20.6. pontja szerint a követelmények szövege a követelménycsoport
megnevezésével együtt értelmezendő. A 6.27. követelménycsoporthoz a 7. melléklet nem tartalmaz elemi
követelményt.

#### Megvalósítási csoportok

A csoport a biztonsági osztályt és a követelménycsoport SZTFH 6. melléklet B oszlopa szerinti jellegét
együtt jelöli: `SZ` = szervezeti szintű, `EIR` = EIR-szintű. Az osztályok egymásra épülnek
(A 164 ⊂ J 302 ⊂ M 385 követelménycsoport), ezért például az `M-SZ` a Magas osztályban elvárt összes
szervezeti szintű csoportot tartalmazza, az alacsonyabb osztályokét is. Az egyik osztálynál sem elvárt
529 kiegészítő védelmi intézkedés (2. melléklet 20.4. pont; a 6. melléklet nem ad hozzájuk jelleget)
a `KIEG` csoport. Az elemi követelmények a szülő követelménycsoport csoportjaiba tartoznak, és helyette
értékelendők: ahol a követelménycsoporthoz elemi követelmények tartoznak, ott a követelménycsoport csak
címsor, így egy csoport kiválasztása a teljes elemi szintű értékelést adja, és egyetlen követelmény sem
számít kétszer a pontszámba.

| csoport | követelménycsoport | értékelhető követelmény |
|---|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 | 717 / 683 |
| `J-SZ` / `J-EIR` | 108 / 194 | 815 / 1 065 |
| `M-SZ` / `M-EIR` | 132 / 253 | 896 / 1 253 |
| `KIEG` | 529 | 529 |

A `J-EIR` és az `M-EIR` egy-egy többlete a 6.27. követelménycsoport, amelyhez nincs elemi követelmény,
ezért maga értékelendő.

A 19 családból 16 egynemű (szervezeti szintű: 1., 3., 9–12., 14., 19.; EIR-szintű: 2., 4–8., 17., 18.);
a 13., 15. és 16. család vegyes.

#### Használat: csoportok kiválasztása egy audithoz

Az SZTFH rendelet 5. melléklete szerint a szervezeti szintű követelménycsoportok egyszer, valamennyi
EIR-re egységesen, a szervezet legmagasabb biztonsági osztályú EIR-je szerint vizsgálandók (2.2.1.1.,
2.2.3.1., 2.2.3.2. pont), az EIR-szintűek EIR-enként (2.2.1.2. pont), és az EIR védelmi megfelelési
indexébe (VMI) a szervezeti szintű csoportok is beszámítanak (2.2.5.7. pont). A CISO Assistant a
kiválasztott csoportok uniójával szűri a követelményfát, ezért:

* **Szervezeti audit**: a szervezet legmagasabb osztályának `SZ` csoportja, például `M-SZ`.
* **EIR-audit**: az EIR osztályának `EIR` csoportja, például `A-EIR`. Ha az auditnak a
  VMI miatt a szervezeti szintű csoportokat is tartalmaznia kell, a legmagasabb osztály `SZ` csoportja
  hozzávehető (`A-EIR` + `M-SZ`).
* **Egyetlen EIR-rel rendelkező szervezet**: az osztály `SZ` és `EIR` csoportja együtt, például
  `J-SZ` + `J-EIR`.

Hogy a szervezeti szintű csoportokat ne kelljen minden EIR-auditban újra értékelni, az EIR-audit a
szervezeti audit *baseline*-jával hozható létre: a CISO Assistant azonos keretrendszernél átmásolja a
közös követelmények eredményeit és válaszait. Az alkalmazás két audit eredményét nem vonja össze egy
pontszámba, így a szervezeti és az EIR-auditot átfogó VMI-t az alkalmazáson kívül kell számolni.

#### Megjegyzések (annotation)

A követelménycsoport megjegyzése tartalmazza az SZTFH 6. melléklet szerinti audit-jellemzőket
(szervezeti / EIR-szintű, kötelező dokumentumvizsgálat / interjú / teszt, Biztosító / Támogató típus,
„az értékelésből nem kizárható”), a kihirdetett szöveg elírásait (változatlanul átvéve, a helyes
alakkal), az SZTFH mellékletek és az NKI táblázat eltérő névírását, valamint az 5.3. és 5.4.
követelménycsoportnál a 18/2024. (XII. 30.) MK rendelet szerinti módosítás tényét. Az elemi
követelmények megjegyzése rögzíti a Magyar Közlönyben hibásan szedett kódot (`K013.003_P[1]`,
`K01.016_ O.1.16`) és a négy nem létező kódra mutató hivatkozást a nyilvánvalóan értendő kóddal.

#### Ellenőrzés

A YAML 3 081 követelménycsomópontot és 7 megvalósítási csoportot tartalmaz. Az értékelhető csomópontok
száma kiválasztásonként: `A-SZ` 717, `A-EIR` 683, `J-SZ` 815, `J-EIR` 1 065, `M-SZ` 896, `M-EIR` 1 253,
`KIEG` 529, `M-SZ`+`M-EIR` 2 149, `A-EIR`+`M-SZ` 1 579, kiválasztás nélkül 2 678.

Betöltési teszt (CISO Assistant 4.1.1, dátum: 2026. 10. 15.): a könyvtár betölthető, az auditok kiválasztásonként a
fenti számokat adják, a szervezeti auditot baseline-ként használó EIR-audit megkapja az ott rögzített
eredményt.

### `hu-7-2024-mk-rendelet` – védelmi intézkedések katalógusa

A 7/2024. (VI. 24.) MK rendelet 2. mellékletének 914 követelménycsoportja (védelmi intézkedés) a 19
követelménycsalád alatt, elemi követelmények nélkül: minden követelménycsoport értékelhető. A csomópontok
`ref_id`-ja, neve, leírása, megjegyzése és megvalósítási csoportjai megegyeznek az elemi követelmények
könyvtárának 1–2. szintű csomópontjaival, csak az URN-előtag más
(`urn:aafeher:risk:req_node:hu-7-2024-mk-rendelet`). Rendeltetése a jogszabályi kötelezettség
követelménycsoport-szintű kezelése (kontrollok, megfelelés), az SZTFH-auditra való felkészüléshez az elemi
követelmények könyvtára szolgál.

| szint | csomópont | ref_id | name | description | megvalósítási csoportok |
|---|---|---|---|---|---|
| 1 | követelménycsalád (19) | `1` … `19` | a család neve | – | – |
| 2 | követelménycsoport / védelmi intézkedés (914, értékelhető) | `1.1` | a rendeletben szereplő megnevezés | a követelmény szövege, pontonként külön sorban | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR`, `KIEG`, mint fent |

A megvalósítási csoportok meghatározása, a 6. melléklet szerinti jelleg és a csoportok kiválasztása egy
audithoz ugyanaz, mint az elemi követelmények könyvtáránál; az értékelhető követelmény itt maga a
követelménycsoport:

| csoport | értékelhető követelménycsoport |
|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 |
| `J-SZ` / `J-EIR` | 108 / 194 |
| `M-SZ` / `M-EIR` | 132 / 253 |
| `KIEG` | 529 |

A megjegyzések (annotation) azonosak az elemi követelmények könyvtárának követelménycsoportjaival (6.
melléklet szerinti audit-jellemzők, elírások, eltérő névírás, a 18/2024. (XII. 30.) MK rendelet szerinti
módosítás).

Ellenőrzés: a YAML 933 követelménycsomópontot (19 család + 914 követelménycsoport) és 7 megvalósítási
csoportot tartalmaz. Az értékelhető csomópontok száma kiválasztásonként: `A-SZ` 82, `A-EIR` 82, `J-SZ` 108,
`J-EIR` 194, `M-SZ` 132, `M-EIR` 253, `KIEG` 529, `M-SZ`+`M-EIR` 385, `A-EIR`+`M-SZ` 214, kiválasztás nélkül
914. Betöltési teszt (CISO Assistant 4.1.1, dátum: 2026. 10. 15.).

### `hu-7-2024-mk-rendelet-fenyegetesek` – fenyegetéskatalógus

A 7/2024. (VI. 24.) MK rendelet 3. mellékletének 47 fenyegetése `threats` objektumként (`ref_id` 1–47;
a leírás a potenciálisan érintett alapelvek: bizalmasság (B), sértetlenség (S), rendelkezésre állás (R);
a megjegyzés a melléklet hivatkozása). A rendelet a védelmi intézkedéseket nem rendeli fenyegetésekhez.

A katalógus azért önálló könyvtár, mert a CISO Assistantban a fenyegetés URN-je egyedi, így ugyanaz a
fenyegetés nem szerepelhet két keretrendszer-könyvtárban; a katalógus az elemi követelmények könyvtárához
és a `hu-7-2024-mk-rendelet` keretrendszerhez egyaránt tartozik. A fenyegetések URN-előtagja
`urn:aafeher:risk:threat:hu-7-2024-mk-rendelet`.

Ellenőrzés: a YAML 47 fenyegetést tartalmaz. Betöltési teszt (CISO Assistant 4.1.1, dátum: 2026. 10. 15.).

### Források és szövegállapot

* 7/2024. (VI. 24.) MK rendelet: az njt.hu szerinti egységes szerkezet 2025. 01. 02-i állapota
  (a 18/2024. (XII. 30.) MK rendelet az 5.3. és 5.4. követelménycsoportot és az 1. melléklet 1. pontját
  cserélte; a 3. mellékletet nem érintette), a Magyar Közlöny 2024/68. és 2024/137. számával és az NKI
  „Védelmi intézkedések katalógusa” táblázatával (1.0, 2024. december) egybevetve.
* 1/2025. (I. 31.) SZTFH rendelet: a Magyar Közlöny 2025/8. számában kihirdetett szöveg (a
  6/2026. (VI. 8.) SZTFH rendelet a 6–7. mellékletet nem érinti).
* A kihirdetett szöveg elírásai változatlanul szerepelnek, a megjegyzésekben jelölve.
* A jogszabályok szövege nem áll szerzői jogi védelem alatt (Szjt. 1. § (4) bekezdés).

### Nem tartalmazza

Az 1. mellékletet (osztályba sorolás), a Kibertv. és a 418/2024. (XII. 23.) Korm. rendelet szervezeti
kötelezettségeit, az NKI táblázat hivatkozásait (41/2015. BM r., ISO 27001, NIST SP 800-53) és az
SZTFH 5. melléklet szerinti VMI / SZEKI pontozást (nincs pontszám-definíció, a CISO Assistant
alapértelmezett skálája érvényes).

---

## English

CISO Assistant libraries for the Hungarian NIS2 regulation, built from the annexes of
**7/2024. (VI. 24.) MK rendelet** (annex 2: catalogue of protective measures, annex 3: threat catalogue) and
**1/2025. (I. 31.) SZTFH rendelet** (annex 6: audit metadata, annex 7: elementary requirements). Locale `hu`,
packager `aafeher`.

### The library family

| library | status | content | purpose |
|---|---|---|---|
| `hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` | done | the 2,148 elemi követelmény (elementary requirements) of SZTFH annex 7 in the structure of annex 2 of 7/2024. MK rendelet (19 families, 914 protective measures), with the annex 6 audit metadata | the view of the SZTFH audit: audit preparation; the unit of assessment is the elementary requirement |
| `hu-7-2024-mk-rendelet-fenyegetesek` | done | the 47 threats of annex 3 of 7/2024. MK rendelet | threat catalogue for risk assessments, alongside both frameworks |
| `hu-7-2024-mk-rendelet` | done | the same 914 measures without the elementary level, with assessable measures and the same 7 implementation groups | the legal obligation at measure level: control management |
| `mapping-hu-7-2024-mk-rendelet-and-hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` | planned | every elementary requirement mapped to its parent measure (`superset`; the reverse direction is generated) | interoperability between the two frameworks, for example pre-filling an audit created with an audit of the other framework as its baseline |

The nodes of the two frameworks share their `ref_id` (`1.1`, `K01.001_P1` …); only the URN prefix differs.

### `hu-1-2025-sztfh-rendelet-elemi-kovetelmenyek` – elementary requirements (NIS2 audit)

The 2,148 elemi követelmény (elementary requirements) of annex 7 of 1/2025. (I. 31.) SZTFH rendelet in the
structure of annex 2 of 7/2024. (VI. 24.) MK rendelet: 19 követelménycsalád (families), 914
követelménycsoport (protective measures) with the security classes Alap / Jelentős / Magas (basic /
significant / high), and the annex 6 audit metadata in the annotations. The unit of assessment is the
elementary requirement: the 384 measures that have elementary requirements are headings only, the other
530 are assessable themselves.

#### Structure

| depth | node | ref_id | name | description | implementation groups |
|---|---|---|---|---|---|
| 1 | követelménycsalád / family (19) | `1` … `19` | family name | – | – |
| 2 | követelménycsoport / protective measure (914; the 530 without elementary requirements are assessable) | `1.1` | the name as printed in the decree (enhancements as "Base – Enhancement") | the requirement text, one numbered point per line | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR` = class in which it is required × annex 6 nature; `KIEG` = required in no class |
| 3 | elemi követelmény / elementary requirement (2,148, assessable) | `K01.001_P1`, `K01.001_O.1.1.1.1.a` | the official code (`K01.001_P[1]`, `K01.001_O.1.1.1.1.(a)`) | the requirement text of SZTFH annex 7 | the groups of the parent measure |

The `ref_id` of an elementary requirement is its code without the square brackets (the code itself is
the `name`). Annex 2 point 20.6 says the requirement texts are to be read together with the name of
the measure. Measure 6.27 has no elementary requirement in annex 7.

#### Implementation groups

A group combines the security class with the nature of the measure given in SZTFH annex 6 column B:
`SZ` = szervezeti szintű (organisational level), `EIR` = EIR-szintű (per system; EIR = elektronikus
információs rendszer, electronic information system). The classes are nested (A 164 ⊂ J 302 ⊂ M 385
measures), so `M-SZ` holds every organisational measure required at Magas, including those of the
lower classes. The 529 measures required in no class ("kiegészítő védelmi intézkedések", annex 2
point 20.4; annex 6 gives them no nature) form the group `KIEG`. Elementary requirements carry the groups
of their parent measure and are assessed in its place: a measure that has elementary requirements is a
heading only, so selecting a group gives the full elementary-level assessment and nothing is counted
twice in the score.

| group | measures | assessable requirements |
|---|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 | 717 / 683 |
| `J-SZ` / `J-EIR` | 108 / 194 | 815 / 1,065 |
| `M-SZ` / `M-EIR` | 132 / 253 | 896 / 1,253 |
| `KIEG` | 529 | 529 |

The extra one in `J-EIR` and `M-EIR` is measure 6.27, which has no elementary requirement and is
therefore assessed itself.

16 of the 19 families are of one nature (organisational: 1, 3, 9–12, 14, 19; system level: 2, 4–8,
17, 18); families 13, 15 and 16 are mixed.

#### Usage: selecting groups for an audit

SZTFH annex 5 audits organisational-level groups once, for all systems, at the class of the
organisation's highest-class system (points 2.2.1.1., 2.2.3.1., 2.2.3.2.), system-level groups per
system (2.2.1.2.), and counts the organisational groups in the compliance index (VMI) of every system
(2.2.5.7.). CISO Assistant filters the requirement tree by the union of the selected groups, hence:

* **Organisational audit**: the `SZ` group of the organisation's highest class, e.g. `M-SZ`.
* **System audit**: the `EIR` group of the system's class, e.g. `A-EIR`. Add the `SZ`
  group of the highest class (`A-EIR` + `M-SZ`) when the audit must also carry the organisational
  groups for the VMI of that system.
* **Organisation with a single system**: `SZ` + `EIR` of its class, e.g. `J-SZ` + `J-EIR`.

To avoid assessing the organisational groups again in every system audit, create the system audit
with the organisational audit as its *baseline*: CISO Assistant copies the results and answers of the
requirements the two audits share (same framework). The application does not merge the results of two
audits into one score, so a VMI that spans an organisational and a system audit has to be computed
outside it.

#### Annotations

The annotation of a measure holds the SZTFH annex 6 audit metadata (organisational / system level,
mandatory document review / interview / test, "Biztosító" / "Támogató" type, "cannot be excluded from
the assessment"), the typos of the published text (kept as published, with the correct form), the
different spellings used by the SZTFH annexes and the NKI catalogue, and, for measures 5.3 and 5.4,
the amendment by 18/2024. (XII. 30.) MK rendelet. The annotation of an elementary requirement records
the code as misprinted in the gazette (`K013.003_P[1]`, `K01.016_ O.1.16`) and the four
cross-references to non-existent codes with the code evidently meant.

#### Verification

The YAML holds 3,081 requirement nodes and 7 implementation groups. Assessable nodes per selection:
`A-SZ` 717, `A-EIR` 683, `J-SZ` 815, `J-EIR` 1,065, `M-SZ` 896, `M-EIR` 1,253, `KIEG` 529,
`M-SZ`+`M-EIR` 2,149, `A-EIR`+`M-SZ` 1,579, and 2,678 without a selection.

Load test (CISO Assistant 4.1.1, date: 2026-10-15): the library loads, audits give the counts above per selection,
and a system audit created with the organisational audit as its baseline receives the results recorded
there.

### `hu-7-2024-mk-rendelet` – protective-measures catalogue

The 914 követelménycsoport (protective measures) of annex 2 of 7/2024. (VI. 24.) MK rendelet under the 19
families, without the elementary requirements: every measure is assessable. The `ref_id`, name,
description, annotation and implementation groups of the nodes are those of the depth 1–2 nodes of the
elementary-requirements library; only the URN prefix differs
(`urn:aafeher:risk:req_node:hu-7-2024-mk-rendelet`). It serves the legal obligation at measure level
(controls, compliance); preparing for the SZTFH audit is what the elementary-requirements library is for.

| depth | node | ref_id | name | description | implementation groups |
|---|---|---|---|---|---|
| 1 | követelménycsalád / family (19) | `1` … `19` | family name | – | – |
| 2 | követelménycsoport / protective measure (914, assessable) | `1.1` | the name as printed in the decree | the requirement text, one numbered point per line | `A-SZ`, `A-EIR`, `J-SZ`, `J-EIR`, `M-SZ`, `M-EIR`, `KIEG`, as above |

The definition of the implementation groups, the annex 6 nature and the selection of groups for an audit
are the same as for the elementary-requirements library; here the assessable requirement is the measure
itself:

| group | assessable measures |
|---|---|
| `A-SZ` / `A-EIR` | 82 / 82 |
| `J-SZ` / `J-EIR` | 108 / 194 |
| `M-SZ` / `M-EIR` | 132 / 253 |
| `KIEG` | 529 |

The annotations are those of the measures of the elementary-requirements library (annex 6 audit metadata,
typos, different spellings, the amendment by 18/2024. (XII. 30.) MK rendelet).

Verification: the YAML holds 933 requirement nodes (19 families + 914 measures) and 7 implementation
groups. Assessable nodes per selection: `A-SZ` 82, `A-EIR` 82, `J-SZ` 108, `J-EIR` 194, `M-SZ` 132,
`M-EIR` 253, `KIEG` 529, `M-SZ`+`M-EIR` 385, `A-EIR`+`M-SZ` 214, and 914 without a selection. Load test
(CISO Assistant 4.1.1, date: 2026-10-15).

### `hu-7-2024-mk-rendelet-fenyegetesek` – threat catalogue

The 47 threats of annex 3 of 7/2024. (VI. 24.) MK rendelet as a `threats` object (`ref_id` 1–47; the
description lists the affected principles: confidentiality (B), integrity (S), availability (R); the
annotation is the reference to the annex). The decree does not map measures to threats.

The catalogue is a library of its own because a threat URN is unique in CISO Assistant, so the same threat
cannot be part of two framework libraries; the catalogue belongs to the elementary-requirements library and
to the `hu-7-2024-mk-rendelet` framework alike. The URN prefix of the threats is
`urn:aafeher:risk:threat:hu-7-2024-mk-rendelet`.

Verification: the YAML holds 47 threats. Load test (CISO Assistant 4.1.1, date: 2026-10-15).

### Sources and text state

* 7/2024. (VI. 24.) MK rendelet: the consolidated text on njt.hu as of 2025-01-02 (18/2024. (XII. 30.)
  MK rendelet replaced measures 5.3 and 5.4 and annex 1 point 1; it did not touch annex 3), cross-checked
  against Magyar Közlöny 2024/68 and 2024/137 and the NKI "Védelmi intézkedések katalógusa" table (1.0,
  December 2024).
* 1/2025. (I. 31.) SZTFH rendelet: the text promulgated in Magyar Közlöny 2025/8 (6/2026. (VI. 8.)
  SZTFH rendelet does not touch annexes 6–7).
* The typos of the published text are kept as published and flagged in the annotations.
* Hungarian legal texts are not subject to copyright (Act LXXVI of 1999, Section 1(4)).

### Not included

Annex 1 (classification method), the organisational obligations of the Kibertv. and of 418/2024.
(XII. 23.) Korm. rendelet, the NKI cross-references (41/2015. BM r., ISO 27001, NIST SP 800-53) and
the VMI / SZEKI audit scoring of SZTFH annex 5 (no scores definition; CISO Assistant's default scale
applies).
