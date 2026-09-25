#let css-pixels-per-point = 96 / 72

#let typst-length-to-css-px(value, name: "merman length", allow-infinite: false) = {
  if type(value) != length {
    panic(name + " must be a Typst length")
  }

  let points = value.pt()
  if float.is-nan(points) {
    panic(name + " must not be NaN")
  } else if float.is-infinite(points) {
    if allow-infinite {
      none
    } else {
      panic(name + " must be finite")
    }
  } else {
    let pixels = points * css-pixels-per-point
    if pixels <= 0 {
      panic(name + " must be positive")
    }
    pixels
  }
}

#let css-px-number-string(value, name: "merman CSS pixel value") = {
  if (type(value) != int and type(value) != float) or float.is-nan(value) or float.is-infinite(value) or value <= 0 {
    panic(name + " must be positive and finite")
  }
  str(value) + "px"
}

#let canonical-css-px-string(value, name: "merman CSS pixel value") = {
  let value = value.trim()
  if not value.ends-with("px") {
    panic(name + " must use CSS px units")
  }
  css-px-number-string(float(value.slice(0, -2).trim()), name: name)
}

#let context-width-css-px(width) = {
  typst-length-to-css-px(
    width,
    name: "merman document context width",
    allow-infinite: true,
  )
}

#let css-px-string(value, name: "merman length") = {
  css-px-number-string(typst-length-to-css-px(value, name: name), name: name)
}
