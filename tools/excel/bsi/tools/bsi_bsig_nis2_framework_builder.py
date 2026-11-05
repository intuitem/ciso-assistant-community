"""Rebuild bsi_bsig-nis2_2025.xlsx (framework_content, library/framework metadata) from the official text.

Source: https://www.gesetze-im-internet.de/bsig_2025/xml.zip (consolidated BSIG).
Usage: python bsi_bsig_nis2_framework_builder.py BJNR12D0B0025.xml bsi_bsig-nis2_2025.xlsx

When the law changes: refresh the XML, update STAND, review ASSESSABLE and TRANSITION_33.
"""

import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter

import openpyxl

STAND = "2026-10-22"  # Art. 8 G v. 22.10.2026 (BGBl. 2026 I Nr. 318), latest amendment
SOURCE_URL = "https://www.gesetze-im-internet.de/bsig_2025/"

GROUPS = [
    (
        "EINR",
        "Besonders wichtige Einrichtungen und wichtige Einrichtungen",
        "§ 28 Abs. 1 und 2",
        "x",
    ),
    (
        "KRITIS",
        "Betreiber kritischer Anlagen",
        "§ 28 Abs. 1 Nr. 1. Enthält die Pflichten besonders wichtiger Einrichtungen sowie § 31, § 32 Abs. 3, § 33 Abs. 2 und § 39.",
        None,
    ),
    (
        "BUND",
        "Einrichtungen der Bundesverwaltung",
        "§ 29 Abs. 1. Enthält die nach § 29 Abs. 2 anzuwendenden Pflichten sowie §§ 43 bis 45 und § 47.",
        None,
    ),
    (
        "RESSORT",
        "Ressorts und weitere oberste Bundesbehörden",
        "§ 46. Ergänzend zu BUND zu wählen.",
        None,
    ),
    (
        "DNS",
        "Top Level Domain Name Registries und Domain-Name-Registry-Dienstleister",
        "§ 33 und §§ 49 bis 51. Ergänzend zur jeweiligen Einrichtungsgruppe zu wählen.",
        None,
    ),
    (
        "DIG",
        "Einrichtungsarten nach § 60 Abs. 1 Satz 1",
        "§ 34. Ergänzend zur jeweiligen Einrichtungsgruppe zu wählen.",
        None,
    ),
]

A = "EINR,KRITIS,BUND"
L = "EINR,KRITIS"  # § 29 Abs. 2 excludes § 38 for federal bodies
AD = A + ",DNS"
K, B, R, D, G = "KRITIS", "BUND", "RESSORT", "DNS", "DIG"

# {§: {Absatz (0 = section without Absätze): groups}}. Only standing, self-executing duties of the
# audited organisation. Everything else stays as context: scope, tasks and powers of authorities,
# options, duties triggered by an authority's order or request, duties awaiting a regulation
# (§ 30 Abs. 6), and conditions of voluntary schemes (§§ 52 to 55).
ASSESSABLE = {
    30: {1: A},  # Abs. 1 is the only node holding the documentation duty (Satz 3)
    31: {1: K, 2: K},  # Abs. 1 is part of what § 39 Abs. 1 requires to be proven
    32: {2: A, 3: K},
    33: {1: AD, 2: K, 5: AD},
    34: {1: G, 2: G},
    35: {2: A},
    38: {1: L, 3: L},
    39: {1: K},
    43: {1: B, 2: B, 3: B, 5: B},
    44: {1: B},
    45: {1: B, 2: B, 3: B, 4: B},
    46: {1: R, 2: R, 3: R, 6: R},
    47: {1: B, 5: B},
    49: {1: D, 2: D, 3: D, 4: D},
    50: {1: D, 2: D},
    51: {0: D},
}
# Absätze split per Nummer, each Nummer being assessable: {(§, Absatz): groups}
SPLIT_NUMBERS = {(30, 2): A, (32, 1): A}

# § 66 keeps the previous wording applicable until the KRITIS-DachG regulation is in force.
_T66 = (
    "Übergangsregelung (§ 66): Dieser Absatz ist erst anzuwenden, wenn eine Rechtsverordnung auf der "
    "Grundlage des § 4 Absatz 3 und § 5 Absatz 1 des KRITIS-Dachgesetzes in Kraft getreten ist. "
    "Bis dahin gilt weiter die bis einschließlich {date} geltende Fassung:\n"
)
TRANSITION_33 = {
    2: _T66.format(date="16. März 2026")
    + "Betreiber kritischer Anlagen übermitteln mit den Angaben nach Absatz 1 die kritische Dienstleistung, "
    "die bei ihnen zum Einsatz kommenden Typen von kritischen Komponenten, die öffentlichen IP-Adressbereiche "
    "der von ihnen betriebenen Anlagen sowie die für die von ihnen betriebenen kritischen Anlagen ermittelte "
    "Anlagenkategorie und die ermittelten Versorgungskennzahlen gemäß der Rechtsverordnung nach § 56 Absatz 4 "
    "sowie den Standort der Anlagen und eine Kontaktstelle. Die Betreiber stellen sicher, dass sie über ihre "
    "in Satz 1 genannte Kontaktstelle jederzeit erreichbar sind.",
    5: _T66.format(date="28. Juli 2026")
    + "Bei Änderungen der nach Absatz 1 oder 2 zu übermittelnden Angaben sind dem Bundesamt geänderte "
    "Versorgungskennzahlen sowie Änderungen der bei Betreibern kritischer Anlagen zum Einsatz kommenden Typen "
    "von kritischen Komponenten einmal jährlich zu übermitteln und alle anderen Angaben unverzüglich, spätestens "
    "jedoch zwei Wochen ab dem Zeitpunkt, zu dem die Einrichtung Kenntnis von der Änderung erhalten hat, zu "
    "übermitteln.",
}

LIBRARY_DESCRIPTION = (
    "Gesetz über das Bundesamt für Sicherheit in der Informationstechnik und über die Sicherheit in der "
    "Informationstechnik von Einrichtungen (BSIG), Teile 3 bis 5 (§§ 28 bis 55), in der konsolidierten Fassung, "
    "zuletzt geändert durch Art. 8 G v. 22.10.2026 (BGBl. 2026 I Nr. 318).\n"
    f"Quelle: {SOURCE_URL}\n"
    "Die Bibliothek liegt nur auf Deutsch vor: Eine amtliche englische Fassung gibt es nicht."
)
FRAMEWORK_DESCRIPTION = (
    "BSIG in der Fassung des NIS-2-Umsetzungsgesetzes (BGBl. 2025 I Nr. 301), Teile 3 bis 5 (§§ 28 bis 55), "
    "Stand der konsolidierten Fassung: letzte Änderung durch Art. 8 G v. 22.10.2026 (BGBl. 2026 I Nr. 318).\n\n"
    "Bewertbar sind die Absätze, die der geprüften Organisation eine eigenständige, dauerhafte Pflicht auferlegen; "
    "§ 30 Abs. 2 und § 32 Abs. 1 sind nach Nummern gegliedert. Als nicht bewertbarer Kontext bleiben erhalten: "
    "Vorschriften zum Anwendungsbereich, Aufgaben und Befugnisse von Behörden, Wahlmöglichkeiten, Pflichten, die "
    "erst durch eine Anordnung oder ein Verlangen einer Behörde entstehen, Pflichten, die eine noch zu erlassende "
    "Rechtsverordnung voraussetzen (§ 30 Abs. 6), sowie die Bedingungen freiwilliger Verfahren (§§ 52 bis 55).\n\n"
    "Die Implementierungsgruppen bilden die Art der Einrichtung ab: Damit werden nur die jeweils einschlägigen "
    "Pflichten geprüft. Sektorspezifische Ausnahmen (§ 28 Abs. 5 bis 7, § 29 Abs. 3, § 37) sind im Einzelfall zu "
    "prüfen. Begriffsbestimmungen (§ 2), Aufsicht und Bußgelder sind nicht enthalten."
)


def flatten(node):
    """Text of a <P>, one line per list item; nested lists stay under their item."""
    out = []

    def walk(e):
        if e.tag == "DL":
            kids = list(e)
            for dt, dd in zip(kids[::2], kids[1::2]):
                out.append("\n" + "".join(dt.itertext()).strip() + " ")
                walk_inner(dd)
            out.append("\n")
        elif e.tag == "BR":
            out.append("\n")
        else:
            walk_inner(e)

    def walk_inner(e):
        out.append(e.text or "")
        for c in e:
            walk(c)
            out.append(c.tail or "")

    walk_inner(node)
    return re.sub(r" *\n\s*", "\n", re.sub(r"[ \t\r]+", " ", "".join(out))).strip()


def load(path):
    """Return ordered [{kind, ...}] for Teil 3-5."""
    items, in_scope = [], False
    for n in ET.parse(path).getroot().findall("norm"):
        md = n.find("metadaten")
        unit, enbez = md.find("gliederungseinheit"), md.findtext("enbez") or ""
        if unit is not None:
            bez, title = (
                unit.findtext("gliederungsbez"),
                unit.findtext("gliederungstitel"),
            )
            if bez.startswith("Teil"):
                in_scope = bez in ("Teil 3", "Teil 4", "Teil 5")
            if in_scope:
                items.append({"kind": "unit", "bez": bez, "title": title})
        elif in_scope and enbez.startswith("§"):
            paras = [flatten(p) for p in n.findall("textdaten/text/Content/P")]
            items.append(
                {
                    "kind": "sec",
                    "nr": int(enbez[2:]),
                    "title": md.findtext("titel"),
                    "paras": paras,
                }
            )
    return items


def split_numbers(text):
    """Split 'intro\\n1. a\\n2. b\\ntrailer' into (intro + trailer, [(n, item)])."""
    head, nums, tail = [], [], []
    for line in text.split("\n"):
        m = re.match(r"(\d+)\. (.*)", line)
        if m:
            nums.append((int(m[1]), m[2]))
        elif not nums:
            head.append(line)
        elif re.match(r"[a-z]\) ", line):
            nums[-1] = (nums[-1][0], nums[-1][1] + "\n" + line)
        else:
            tail.append(line)
    return "\n".join(head + tail), nums


def rows_for(items):
    rows, seen = [], set()
    teil = None

    def add(assessable, depth, ref_id, name=None, desc=None, ann=None, groups=None):
        rows.append(
            ["x" if assessable else None, str(depth), ref_id, name, desc, ann, groups]
        )

    for it in items:
        if it["kind"] == "unit":
            kapitel = it["bez"].startswith("Kapitel")
            teil = teil if kapitel else it["bez"]
            slug = teil.replace(" ", "-")
            ref = f"{slug}.{it['bez'].replace(' ', '-')}" if kapitel else slug
            add(False, 2 if kapitel else 1, ref, f"{it['bez']} - {it['title']}")
            continue
        nr, depth = it["nr"], 3 if teil == "Teil 3" else 2
        cfg = ASSESSABLE.get(nr, {})
        title = f"§ {nr} - {it['title']}"
        if len(it["paras"]) == 1 and not it["paras"][0].startswith("(1)"):
            add(0 in cfg, depth, str(nr), title, it["paras"][0], None, cfg.get(0))
            seen.add((nr, 0))
            continue
        add(False, depth, str(nr), title)
        for i, para in enumerate(it["paras"], 1):
            assert para.startswith(f"({i}) "), (nr, i)
            body = para[len(f"({i}) ") :]
            ann = TRANSITION_33.get(i) if nr == 33 else None
            ref, name = f"{nr}.{i}", f"§ {nr} Abs. {i}"
            if (nr, i) in SPLIT_NUMBERS:
                intro, nums = split_numbers(body)
                add(i in cfg, depth + 1, ref, name, intro, ann, cfg.get(i))
                for n, item in nums:
                    add(
                        True,
                        depth + 2,
                        f"{ref}.{n}",
                        f"{name} Nr. {n}",
                        item,
                        None,
                        SPLIT_NUMBERS[(nr, i)],
                    )
            else:
                add(i in cfg, depth + 1, ref, name, body, ann, cfg.get(i))
            seen.add((nr, i))
    wanted = {(s, a) for s, c in ASSESSABLE.items() for a in c} | set(SPLIT_NUMBERS)
    assert wanted <= seen, wanted - seen  # a renumbered Absatz must not fail silently
    return rows


def self_check(items, rows):
    """Nodes must hold the source text, word for word."""
    # enumerators move to ref_id; a list trailer moves next to its intro, hence a word count
    words = lambda texts: Counter(
        w for t in texts for w in t.split() if not re.fullmatch(r"\(\d+\)|\d+\.", w)
    )
    source = words(p for i in items if i["kind"] == "sec" for p in i["paras"])
    assert source == words(r[4] or "" for r in rows), "text lost or altered"
    refs = [r[2] for r in rows]
    assert len(refs) == len(set(refs))
    assert all(
        re.fullmatch(r"[a-zA-Z0-9._-]+", r) for r in refs
    )  # check_library_v2.py validate_ref_id
    assert all(bool(r[0]) == bool(r[6]) for r in rows)
    assert {g for r in rows if r[6] for g in r[6].split(",")} == {g[0] for g in GROUPS}


def set_meta(ws, values):
    keep = {str(r[0].value): r[0].row for r in ws.iter_rows() if r[0].value}
    for k, v in values.items():
        if k in keep:
            ws.cell(keep[k], 2).value = v
        else:
            ws.append([k, v])


def main(xml_path, xlsx_path):
    wb = openpyxl.load_workbook(xlsx_path)
    items = load(xml_path)
    rows = rows_for(items)
    self_check(items, rows)

    lib = wb["library_meta"]
    for row in reversed(range(1, lib.max_row + 1)):
        key = lib.cell(row, 1).value
        if (
            key == "reference"
            or (key or "").startswith(("Note that", "No official"))
            or (not key and row > 10)
        ):
            lib.delete_rows(row)
    set_meta(
        lib,
        {
            "description": LIBRARY_DESCRIPTION,
            "provider": "Bundesministerium des Innern",
            "publication_date": STAND,
        },
    )
    set_meta(
        wb["framework_meta"],
        {
            "description": FRAMEWORK_DESCRIPTION,
            "implementation_groups_definition": "imp_grp",
        },
    )

    idx = wb.sheetnames.index("framework_content")
    del wb["framework_content"]
    ws = wb.create_sheet("framework_content", idx)
    ws.append(
        [
            "assessable",
            "depth",
            "ref_id",
            "name",
            "description",
            "annotation",
            "implementation_groups",
        ]
    )
    for r in rows:
        ws.append(r)

    for name in ("imp_grp_meta", "imp_grp_content"):
        if name in wb.sheetnames:
            del wb[name]
    meta = wb.create_sheet("imp_grp_meta", idx + 1)
    meta.append(["type", "implementation_groups"])
    meta.append(["name", "imp_grp"])
    content = wb.create_sheet("imp_grp_content", idx + 2)
    content.append(["ref_id", "name", "description", "default_selected"])
    for g in GROUPS:
        content.append(list(g))
    wb.save(xlsx_path)
    print(len(rows), "nodes,", sum(1 for r in rows if r[0]), "assessable")


if __name__ == "__main__":
    main(*sys.argv[1:3])
