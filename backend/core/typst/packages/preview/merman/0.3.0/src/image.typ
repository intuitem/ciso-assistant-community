#import "errors.typ": diagram-error, error-message

#let scale-factor(factor) = {
  if type(factor) == int or type(factor) == float {
    factor * 100%
  } else {
    factor
  }
}

#let scaled(body, factor) = {
  if factor == none {
    body
  } else {
    scale(x: scale-factor(factor), y: scale-factor(factor), reflow: true, body)
  }
}

#let svg-bytes-or-panic(result) = {
  if result.ok {
    bytes(result.svg)
  } else {
    panic(error-message(result))
  }
}

#let result-image(
  result,
  width,
  height,
  fit,
  alt,
  scale,
  error-mode,
) = {
  if result.ok {
    scaled(image(
      bytes(result.svg),
      format: "svg",
      width: width,
      height: height,
      fit: fit,
      alt: alt,
    ), scale)
  } else if error-mode == "panic" {
    panic(error-message(result))
  } else {
    diagram-error(result, error-mode, width)
  }
}
