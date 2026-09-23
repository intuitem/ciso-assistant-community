// Renders the trees built by `core/markdown_render.py`. User text only ever
// arrives as string values, which Typst prints literally.

#let _heading-sizes = (1.3em, 1.15em, 1.05em, 1em, 1em, 1em)

#let _md-node(n) = {
  if type(n) == str { return [#n] }
  let t = n.at("t")
  let kids = n.at("c", default: ())
  if t in ("md", "li", "quote") {
    // A tight list item holds a "span", which must not be pushed apart from a
    // nested list by a paragraph break.
    let loose = kids.any(k => type(k) == dictionary and k.t == "p")
    let body = [#kids.map(_md-node).join(if t != "li" or loose { parbreak() })]
    if t == "quote" { quote(block: true, body) } else { body }
  } else if t in ("p", "span") {
    [#kids.map(_md-node).join()]
  } else if t == "h" {
    block(below: 0.6em, text(
      weight: "bold",
      size: _heading-sizes.at(calc.clamp(n.l, 1, 6) - 1),
    )[#kids.map(_md-node).join()])
  } else if t == "strong" {
    strong[#kids.map(_md-node).join()]
  } else if t == "em" {
    emph[#kids.map(_md-node).join()]
  } else if t == "s" {
    strike[#kids.map(_md-node).join()]
  } else if t == "a" {
    link(n.href)[#kids.map(_md-node).join()]
  } else if t == "code" {
    raw(n.v)
  } else if t == "pre" {
    raw(n.v, block: true)
  } else if t == "br" {
    linebreak()
  } else if t == "hr" {
    line(length: 100%, stroke: 0.5pt + gray)
  } else if t == "ul" {
    list(..kids.map(_md-node))
  } else if t == "ol" {
    enum(start: n.start, ..kids.map(_md-node))
  } else if t == "table" {
    let cells = ()
    for (i, row) in n.rows.enumerate() {
      for j in range(n.cols) {
        let body = [#row.at(j, default: ()).map(_md-node).join()]
        cells.push(if i == 0 and n.header { strong(body) } else { body })
      }
    }
    table(columns: n.cols, ..cells)
  }
}

// `value` is a tree from `markdown_tree`, or a plain string it passed through.
#let md(value) = {
  if type(value) == dictionary { _md-node(value) } else if value == none { [] } else { [#value] }
}
