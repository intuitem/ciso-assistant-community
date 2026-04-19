#!/usr/bin/env python3
"""Render a standalone HTML visualization of a mapping.

Inputs:
    spec.json (verdicts + metadata)  OR  a mapping library YAML
    parsed source framework JSON
    parsed target framework JSON

Output:
    single-file HTML with embedded JSON, vanilla JS + CSS, no network deps.

    View 1: Category-level heatmap (rows=src categories, cols=tgt categories)
    View 2: Pair list table, filterable by matrix click / search / relationship.

Stdlib + pyyaml only.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from html import escape
from pathlib import Path

import yaml


_LEVEL_PREFIX = re.compile(r"^(BASIC_|IMPORTANT_|KEY_)")
_CSF_CAT = re.compile(r"^(GV|ID|PR|DE|RS|RC)\.([A-Z]{2})")
_ISO_ANNEX = re.compile(r"^A\.(\d+)")
_NUMERIC = re.compile(r"^(\d+)\.")


def extract_category(ref_id: str, fallback: str = "") -> str:
    """Bucket a requirement ref_id into a category label.

    Tries in order: NIST CSF (ID.AM), ISO Annex A (A.5), numeric-prefix (1, 10),
    then falls back to the provided fallback (typically section_ref_id).
    """
    if not ref_id:
        return fallback or "?"
    stripped = _LEVEL_PREFIX.sub("", ref_id.upper())
    m = _CSF_CAT.match(stripped)
    if m:
        return f"{m.group(1)}.{m.group(2)}"
    m = _ISO_ANNEX.match(stripped)
    if m:
        return f"A.{m.group(1)}"
    m = _NUMERIC.match(stripped)
    if m:
        return m.group(1)
    return fallback or "OTHER"


def load_mappings(path: Path) -> tuple[list[dict], dict]:
    """Return (mappings_list, metadata) from a spec.json or mapping YAML."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.load(open(path))
        return data.get("verdicts", []), {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
        }
    if suffix in {".yaml", ".yml"}:
        data = yaml.safe_load(open(path))
        sets = (data or {}).get("objects", {}).get("requirement_mapping_sets") or []
        if not sets:
            raise SystemExit(f"{path}: no requirement_mapping_sets found")
        return sets[0].get("requirement_mappings") or [], {
            "name": data.get("name", ""),
            "description": data.get("description", ""),
        }
    raise SystemExit(f"{path}: unsupported extension")


def _disambiguate_numeric(cats: list[str]) -> dict[str, str]:
    """If both `A.5` and plain `5` appear, prefix the plain one with `Cl.` to disambiguate.

    Returns original → display mapping.
    """
    annex_digits = {c[2:] for c in cats if c.startswith("A.") and c[2:].isdigit()}
    out: dict[str, str] = {}
    for c in cats:
        if c.isdigit() and c in annex_digits:
            out[c] = f"Cl.{c}"
        else:
            out[c] = c
    return out


def build_payload(
    mappings: list[dict],
    src_parsed: dict,
    tgt_parsed: dict,
) -> dict:
    src_items = {it["urn"]: it for it in src_parsed["items"]}
    tgt_items = {it["urn"]: it for it in tgt_parsed["items"]}

    # Category + hover name for each item (hover = section_name of a representative item)
    def cat_for(it: dict) -> str:
        return extract_category(
            it.get("ref_id") or "", fallback=(it.get("section_ref_id") or "OTHER")
        )

    src_cat_of = {u: cat_for(it) for u, it in src_items.items()}
    tgt_cat_of = {u: cat_for(it) for u, it in tgt_items.items()}

    # Ordered unique categories (preserve source file order)
    def ordered_uniq(parsed: dict, cat_of: dict) -> list[str]:
        seen: set[str] = set()
        out: list[str] = []
        for it in parsed["items"]:
            c = cat_of[it["urn"]]
            if c not in seen:
                seen.add(c)
                out.append(c)
        return out

    src_cats_raw = ordered_uniq(src_parsed, src_cat_of)
    tgt_cats_raw = ordered_uniq(tgt_parsed, tgt_cat_of)

    # Disambiguate `5` vs `A.5` clashes (ISO-style)
    src_disp = _disambiguate_numeric(src_cats_raw)
    tgt_disp = _disambiguate_numeric(tgt_cats_raw)

    # Hover label = first item's section_name for that category
    def first_section_name(cat_of: dict, items: list[dict]) -> dict[str, str]:
        seen: dict[str, str] = {}
        for it in items:
            c = cat_of[it["urn"]]
            if c in seen:
                continue
            seen[c] = (it.get("section_name") or "").strip()
        return seen

    src_cat_name = first_section_name(src_cat_of, src_parsed["items"])
    tgt_cat_name = first_section_name(tgt_cat_of, tgt_parsed["items"])

    # Compact mapping records; use display labels for cat fields so matrix keys match
    compact = []
    for m in mappings:
        su = m["source_requirement_urn"]
        tu = m["target_requirement_urn"]
        src = src_items.get(su, {})
        tgt = tgt_items.get(tu, {})
        compact.append(
            {
                "sr": src.get("ref_id") or su.split(":")[-1],
                "su": su,
                "sd": (src.get("description") or "").strip(),
                "sc": src_disp.get(src_cat_of.get(su, "?"), "?"),
                "tr": tgt.get("ref_id") or tu.split(":")[-1],
                "tu": tu,
                "td": (tgt.get("description") or "").strip(),
                "tc": tgt_disp.get(tgt_cat_of.get(tu, "?"), "?"),
                "re": (m.get("relationship") or "").lower(),
                "st": m.get("strength_of_relationship"),
                "ra": (m.get("rationale") or "").strip(),
            }
        )

    src_cat_counts = Counter(src_cat_of.values())
    tgt_cat_counts = Counter(tgt_cat_of.values())

    used_rels = sorted({m["re"] for m in compact if m["re"]})

    return {
        "src_fw": src_parsed.get("framework_name")
        or src_parsed.get("framework_ref_id", ""),
        "tgt_fw": tgt_parsed.get("framework_name")
        or tgt_parsed.get("framework_ref_id", ""),
        "src_cats": [
            {"id": src_disp[c], "n": src_cat_counts[c], "nm": src_cat_name.get(c, "")}
            for c in src_cats_raw
        ],
        "tgt_cats": [
            {"id": tgt_disp[c], "n": tgt_cat_counts[c], "nm": tgt_cat_name.get(c, "")}
            for c in tgt_cats_raw
        ],
        "mappings": compact,
        "used_rels": used_rels,
    }


HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>__TITLE__</title>
<style>
:root {
  --bg: #fafafa;
  --fg: #111;
  --muted: #666;
  --border: #d8d8d8;
  --card: #fff;
  --teal-0: #ffffff;
  --teal-1: #e6f3f1;
  --teal-2: #b8ded8;
  --teal-3: #7bc4b9;
  --teal-4: #3ea396;
  --teal-5: #1e7c70;
  --equal: #1e7c70;
  --intersect: #d48836;
  --subset: #7859b2;
  --superset: #b23f7f;
}
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; color: var(--fg); background: var(--bg); font-size: 13px; }
.container { max-width: 1400px; margin: 0 auto; padding: 24px; }
header h1 { margin: 0 0 4px; font-size: 18px; font-weight: 600; }
header .subtitle { color: var(--muted); font-size: 12px; margin-bottom: 4px; }
header .subtitle code { background: #eee; padding: 1px 5px; border-radius: 3px; font-size: 11px; }
.stats { margin-top: 8px; display: flex; gap: 16px; font-size: 12px; color: var(--muted); }
.stats b { color: var(--fg); }
.section { background: var(--card); border: 1px solid var(--border); border-radius: 6px; padding: 18px; margin-top: 18px; }
.section h2 { margin: 0 0 10px; font-size: 14px; font-weight: 600; }
.section h2 .hint { font-weight: 400; color: var(--muted); font-size: 11px; margin-left: 8px; }

/* ---- Matrix ---- */
.matrix-wrap { overflow: auto; max-width: 100%; }
table.matrix { border-collapse: collapse; font-size: 11px; }
table.matrix th, table.matrix td { border: 1px solid #eee; text-align: center; white-space: nowrap; }
table.matrix thead th {
  vertical-align: bottom;
  height: 70px;
  padding: 0 3px;
  font-weight: 500;
  color: var(--muted);
  background: var(--bg);
}
table.matrix thead th .label {
  display: inline-block;
  transform: rotate(-55deg) translate(6px, -2px);
  transform-origin: left bottom;
  white-space: nowrap;
  font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
  font-size: 10.5px;
}
table.matrix thead th.corner { background: transparent; border: none; }
table.matrix tbody th {
  text-align: right;
  padding: 2px 6px;
  font-weight: 500;
  color: var(--muted);
  background: var(--bg);
  font-family: "SF Mono", Menlo, Monaco, Consolas, monospace;
  font-size: 10.5px;
  border-right: 1px solid var(--border);
}
table.matrix td.cell {
  width: 30px; height: 22px; padding: 0;
  cursor: pointer; position: relative;
  transition: outline 0.08s;
}
table.matrix td.cell:hover { outline: 2px solid var(--fg); outline-offset: -2px; z-index: 2; }
table.matrix td.cell.active { outline: 2px solid #e4572e; outline-offset: -2px; z-index: 3; }
table.matrix td.cell.empty { background: transparent; cursor: default; }
table.matrix td.cell.empty:hover { outline: none; }

/* heat levels: 1-5 */
td.cell.h1 { background: var(--teal-1); }
td.cell.h2 { background: var(--teal-2); }
td.cell.h3 { background: var(--teal-3); color: #fff; }
td.cell.h4 { background: var(--teal-4); color: #fff; }
td.cell.h5 { background: var(--teal-5); color: #fff; }
td.cell .count { font-size: 11px; font-weight: 500; }

/* Legend */
.legend { margin-top: 10px; display: flex; align-items: center; gap: 12px; font-size: 11px; color: var(--muted); }
.legend .scale { display: inline-flex; border: 1px solid var(--border); }
.legend .scale span { display: inline-block; width: 22px; height: 14px; font-size: 10px; text-align: center; line-height: 14px; color: #fff; }

/* ---- Controls / filters ---- */
.controls { display: flex; flex-wrap: wrap; gap: 10px; align-items: center; margin-bottom: 12px; font-size: 12px; }
.controls input[type="search"] { padding: 6px 10px; border: 1px solid var(--border); border-radius: 4px; font: inherit; min-width: 280px; }
.controls .chipgroup { display: inline-flex; gap: 4px; }
.chip { padding: 4px 10px; border-radius: 999px; border: 1px solid var(--border); cursor: pointer; user-select: none; background: #fff; font-size: 11.5px; }
.chip.on { background: var(--fg); color: #fff; border-color: var(--fg); }
.chip.rel-equal.on { background: var(--equal); border-color: var(--equal); }
.chip.rel-intersect.on { background: var(--intersect); border-color: var(--intersect); }
.chip.rel-subset.on { background: var(--subset); border-color: var(--subset); }
.chip.rel-superset.on { background: var(--superset); border-color: var(--superset); }
.controls label { color: var(--muted); display: inline-flex; align-items: center; gap: 6px; }
.controls input[type="range"] { width: 100px; }
.active-filter { padding: 4px 10px; background: #ffe5d9; border: 1px solid #e4572e; border-radius: 4px; color: #a53813; font-size: 11.5px; }
.active-filter button { background: none; border: none; color: #a53813; cursor: pointer; font-size: 13px; padding: 0 0 0 6px; }
.status { margin-left: auto; color: var(--muted); font-size: 11px; }

/* ---- Pair table ---- */
.pairs-wrap { max-height: 60vh; overflow: auto; border: 1px solid var(--border); border-radius: 4px; }
table.pairs { width: 100%; border-collapse: collapse; font-size: 12px; }
table.pairs thead th { position: sticky; top: 0; background: var(--bg); padding: 8px 10px; text-align: left; font-weight: 500; color: var(--muted); border-bottom: 1px solid var(--border); z-index: 1; }
table.pairs td { padding: 7px 10px; border-bottom: 1px solid #f0f0f0; vertical-align: top; }
table.pairs tr:hover { background: #f7f7f7; }
table.pairs .ref { font-family: "SF Mono", Menlo, monospace; font-size: 11px; color: #333; white-space: nowrap; }
table.pairs .desc { color: var(--muted); font-size: 11.5px; max-width: 380px; }
.pill { display: inline-block; padding: 1px 7px; border-radius: 3px; font-size: 10px; font-weight: 500; color: #fff; letter-spacing: 0.3px; text-transform: uppercase; }
.pill.rel-equal { background: var(--equal); }
.pill.rel-intersect { background: var(--intersect); }
.pill.rel-subset { background: var(--subset); }
.pill.rel-superset { background: var(--superset); }
.strength { font-family: "SF Mono", Menlo, monospace; font-size: 11px; color: #333; }
.strength.low { color: #a53813; font-weight: 500; }
.rationale { color: var(--muted); font-size: 11px; font-style: italic; }
.empty-state { padding: 40px; text-align: center; color: var(--muted); font-size: 13px; }
</style>
</head>
<body>
<div class="container">
  <header>
    <h1 id="title"></h1>
    <div class="subtitle" id="subtitle"></div>
    <div class="stats" id="stats"></div>
  </header>

  <section class="section">
    <h2>Category heatmap <span class="hint">source categories × target categories • click a cell to filter below</span></h2>
    <div class="matrix-wrap" id="matrix-wrap"></div>
    <div class="legend">
      <span>Count</span>
      <span class="scale">
        <span style="background: var(--teal-1); color: #333">1</span>
        <span style="background: var(--teal-2); color: #333">·</span>
        <span style="background: var(--teal-3)">·</span>
        <span style="background: var(--teal-4)">·</span>
        <span style="background: var(--teal-5)">max</span>
      </span>
      <span style="margin-left: 16px;">Relationships:</span>
      <span><span class="pill rel-equal">equal</span></span>
      <span><span class="pill rel-intersect">intersect</span></span>
      <span><span class="pill rel-subset">subset</span></span>
      <span><span class="pill rel-superset">superset</span></span>
    </div>
  </section>

  <section class="section">
    <h2>Mappings <span class="hint">click a row to expand descriptions</span></h2>
    <div class="controls" id="controls">
      <input type="search" id="search" placeholder="Search ref_id, description, or rationale...">
      <div class="chipgroup" id="rel-filter">
        <span class="chip rel-equal on" data-rel="equal">equal</span>
        <span class="chip rel-intersect on" data-rel="intersect">intersect</span>
        <span class="chip rel-subset on" data-rel="subset">subset</span>
        <span class="chip rel-superset on" data-rel="superset">superset</span>
      </div>
      <label>Min strength <input type="range" id="strength" min="0" max="10" value="0"> <span id="strength-val">0</span></label>
      <label><input type="checkbox" id="borderline"> Only borderline (≤6)</label>
      <div id="active-matrix-filter"></div>
      <div class="status" id="status"></div>
    </div>
    <div class="pairs-wrap">
      <table class="pairs" id="pairs">
        <thead>
          <tr>
            <th style="width: 14%">Source</th>
            <th style="width: 9%">Rel.</th>
            <th style="width: 5%">Str.</th>
            <th style="width: 14%">Target</th>
            <th>Rationale / descriptions</th>
          </tr>
        </thead>
        <tbody id="pairs-body"></tbody>
      </table>
      <div class="empty-state" id="empty-state" style="display: none;">No mappings match the current filters.</div>
    </div>
  </section>
</div>

<script>
const DATA = __PAYLOAD__;

const state = {
  search: "",
  rels: new Set(["equal", "intersect", "subset", "superset"]),
  minStrength: 0,
  borderlineOnly: false,
  matrixCell: null,   // [srcCat, tgtCat] or null
};

document.getElementById("title").textContent = (DATA.src_fw + "  ↔  " + DATA.tgt_fw);
document.getElementById("subtitle").innerHTML = (DATA.title_meta || "");
document.getElementById("stats").innerHTML = (
  "<span><b>" + DATA.mappings.length + "</b> forward mappings</span>" +
  "<span><b>" + DATA.src_cats.length + "</b> source categories</span>" +
  "<span><b>" + DATA.tgt_cats.length + "</b> target categories</span>"
);

// Hide relationship pills/chips that never appear in this mapping
const usedRels = new Set(DATA.used_rels || []);
document.querySelectorAll(".legend .pill, #rel-filter .chip").forEach(el => {
  const rel = (el.getAttribute("data-rel") || Array.from(el.classList).find(c => c.startsWith("rel-"))?.slice(4));
  if (rel && !usedRels.has(rel)) {
    const parent = el.closest(".chip") ? el : (el.closest("span") || el);
    parent.style.display = "none";
  }
});

function buildMatrix() {
  const cells = {}; // "src|tgt" → {count, rels:{equal:n,intersect:n,...}}
  let maxCount = 0;
  for (const m of DATA.mappings) {
    const k = m.sc + "|" + m.tc;
    const c = cells[k] || (cells[k] = { count: 0, rels: {} });
    c.count += 1;
    c.rels[m.re] = (c.rels[m.re] || 0) + 1;
    if (c.count > maxCount) maxCount = c.count;
  }

  function heatLevel(n) {
    if (n <= 0) return 0;
    if (maxCount <= 1) return 1;
    const p = n / maxCount;
    if (p <= 0.2) return 1;
    if (p <= 0.4) return 2;
    if (p <= 0.6) return 3;
    if (p <= 0.8) return 4;
    return 5;
  }

  let html = '<table class="matrix"><thead><tr><th class="corner"></th>';
  for (const tc of DATA.tgt_cats) {
    const tt = tc.nm ? `${tc.id} — ${tc.nm} (${tc.n} items)` : `${tc.id} (${tc.n} items)`;
    html += `<th title="${escapeHtml(tt)}"><div class="label">${escapeHtml(tc.id)} <span style="color:#aaa">(${tc.n})</span></div></th>`;
  }
  html += '</tr></thead><tbody>';
  for (const sc of DATA.src_cats) {
    const ttS = sc.nm ? `${sc.id} — ${sc.nm} (${sc.n} items)` : `${sc.id} (${sc.n} items)`;
    html += `<tr><th title="${escapeHtml(ttS)}">${escapeHtml(sc.id)} <span style="color:#aaa">(${sc.n})</span></th>`;
    for (const tc of DATA.tgt_cats) {
      const c = cells[sc.id + "|" + tc.id];
      if (!c) {
        html += '<td class="cell empty"></td>';
        continue;
      }
      const lv = heatLevel(c.count);
      const parts = Object.entries(c.rels).map(([k, v]) => `${v} ${k}`).join(", ");
      const tt = `${sc.id} → ${tc.id}\n${c.count} mapping(s): ${parts}`;
      html += `<td class="cell h${lv}" data-src="${escapeHtml(sc.id)}" data-tgt="${escapeHtml(tc.id)}" title="${escapeHtml(tt)}"><span class="count">${c.count}</span></td>`;
    }
    html += '</tr>';
  }
  html += '</tbody></table>';
  document.getElementById("matrix-wrap").innerHTML = html;

  document.querySelectorAll("table.matrix td.cell:not(.empty)").forEach(el => {
    el.addEventListener("click", () => {
      const src = el.getAttribute("data-src");
      const tgt = el.getAttribute("data-tgt");
      if (state.matrixCell && state.matrixCell[0] === src && state.matrixCell[1] === tgt) {
        state.matrixCell = null;
      } else {
        state.matrixCell = [src, tgt];
      }
      renderActiveFilter();
      renderMatrixHighlight();
      renderPairs();
    });
  });
}

function renderMatrixHighlight() {
  document.querySelectorAll("table.matrix td.cell").forEach(el => el.classList.remove("active"));
  if (state.matrixCell) {
    const sel = `td.cell[data-src="${CSS.escape(state.matrixCell[0])}"][data-tgt="${CSS.escape(state.matrixCell[1])}"]`;
    const el = document.querySelector(sel);
    if (el) el.classList.add("active");
  }
}

function renderActiveFilter() {
  const div = document.getElementById("active-matrix-filter");
  if (state.matrixCell) {
    div.innerHTML = `<span class="active-filter">${escapeHtml(state.matrixCell[0])} → ${escapeHtml(state.matrixCell[1])}<button title="Clear">×</button></span>`;
    div.querySelector("button").addEventListener("click", () => {
      state.matrixCell = null;
      renderActiveFilter();
      renderMatrixHighlight();
      renderPairs();
    });
  } else {
    div.innerHTML = "";
  }
}

function filterMappings() {
  const q = state.search.toLowerCase();
  return DATA.mappings.filter(m => {
    if (!state.rels.has(m.re)) return false;
    if ((m.st ?? 10) < state.minStrength) return false;
    if (state.borderlineOnly && (m.st ?? 10) > 6) return false;
    if (state.matrixCell && (m.sc !== state.matrixCell[0] || m.tc !== state.matrixCell[1])) return false;
    if (q) {
      const hay = (m.sr + " " + m.tr + " " + m.sd + " " + m.td + " " + m.ra).toLowerCase();
      if (!hay.includes(q)) return false;
    }
    return true;
  });
}

function renderPairs() {
  const rows = filterMappings();
  const tbody = document.getElementById("pairs-body");
  const empty = document.getElementById("empty-state");
  document.getElementById("status").textContent = `${rows.length} / ${DATA.mappings.length} shown`;
  if (rows.length === 0) {
    tbody.innerHTML = "";
    empty.style.display = "";
    return;
  }
  empty.style.display = "none";

  // Truncate long text
  const trunc = (s, n) => s.length > n ? s.slice(0, n - 1) + "…" : s;

  let html = "";
  for (const m of rows) {
    const lowStr = (m.st ?? 10) <= 6;
    const rat = m.ra ? `<div class="rationale">${escapeHtml(m.ra)}</div>` : "";
    const descs = `<div class="desc" title="${escapeHtml(m.sd)}"><b>Src:</b> ${escapeHtml(trunc(m.sd, 180))}</div>
                   <div class="desc" title="${escapeHtml(m.td)}"><b>Tgt:</b> ${escapeHtml(trunc(m.td, 180))}</div>`;
    html += `<tr>
      <td><div class="ref">${escapeHtml(m.sr)}</div><div class="desc">${escapeHtml(trunc(m.sd, 70))}</div></td>
      <td><span class="pill rel-${m.re}">${escapeHtml(m.re)}</span></td>
      <td class="strength${lowStr ? ' low' : ''}">${m.st ?? '-'}</td>
      <td><div class="ref">${escapeHtml(m.tr)}</div><div class="desc">${escapeHtml(trunc(m.td, 70))}</div></td>
      <td>${rat}</td>
    </tr>`;
  }
  tbody.innerHTML = html;
}

function escapeHtml(s) {
  return String(s ?? "").replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
}

// Event wiring
document.getElementById("search").addEventListener("input", e => { state.search = e.target.value; renderPairs(); });
document.querySelectorAll("#rel-filter .chip").forEach(el => {
  el.addEventListener("click", () => {
    const r = el.getAttribute("data-rel");
    if (state.rels.has(r)) { state.rels.delete(r); el.classList.remove("on"); }
    else { state.rels.add(r); el.classList.add("on"); }
    renderPairs();
  });
});
document.getElementById("strength").addEventListener("input", e => {
  state.minStrength = Number(e.target.value);
  document.getElementById("strength-val").textContent = String(state.minStrength);
  renderPairs();
});
document.getElementById("borderline").addEventListener("change", e => {
  state.borderlineOnly = e.target.checked;
  renderPairs();
});

buildMatrix();
renderPairs();
</script>
</body>
</html>
"""


def render(spec_or_yaml: Path, src_parsed: Path, tgt_parsed: Path, out: Path) -> None:
    mappings, meta = load_mappings(spec_or_yaml)
    src = json.load(open(src_parsed))
    tgt = json.load(open(tgt_parsed))
    payload = build_payload(mappings, src, tgt)
    payload["title_meta"] = escape(meta.get("name", "")) + (
        f" &mdash; <code>{escape(meta.get('description', ''))[:120]}</code>"
        if meta.get("description")
        else ""
    )
    html = HTML_TEMPLATE.replace("__TITLE__", escape(meta.get("name") or "Mapping"))
    html = html.replace("__PAYLOAD__", json.dumps(payload, ensure_ascii=False))
    out.write_text(html, encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("spec_or_yaml", help="spec.json or mapping YAML")
    p.add_argument("src_parsed", help="parsed source framework JSON")
    p.add_argument("tgt_parsed", help="parsed target framework JSON")
    p.add_argument("output_html", help="Output HTML path")
    a = p.parse_args()
    render(
        Path(a.spec_or_yaml),
        Path(a.src_parsed),
        Path(a.tgt_parsed),
        Path(a.output_html),
    )
    print(f"wrote {a.output_html}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
