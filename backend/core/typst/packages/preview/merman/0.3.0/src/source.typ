#let source-text-value(source) = {
  if type(source) == str {
    source
  } else {
    source.text
  }
}
