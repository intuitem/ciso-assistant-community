#let error-message(result) = {
  if result.message == none {
    result.code_name
  } else {
    result.message
  }
}

#let validate-error-mode(error-mode) = {
  if not ("panic", "text", "placeholder").contains(error-mode) {
    panic("unknown merman error-mode: " + str(error-mode))
  }
  error-mode
}

#let diagram-error(result, error-mode, width) = {
  if error-mode == "text" {
    text(fill: rgb("#b91c1c"))[merman: #error-message(result)]
  } else if error-mode == "placeholder" {
    block(
      width: width,
      inset: 8pt,
      fill: rgb("#fff7f7"),
      stroke: rgb("#ef4444"),
    )[
      #strong[merman diagram error]
      #linebreak()
      #error-message(result)
    ]
  } else {
    panic("unknown merman error-mode: " + str(error-mode))
  }
}
