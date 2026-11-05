#import "render.typ": mermaid

#let show-mermaid-blocks(
  document-context: false,
  width: 100%,
  height: auto,
  fit: "contain",
  scale: none,
  alt: none,
  error-mode: "placeholder",
  ..args,
) = block => mermaid(
  block.text,
  document-context: document-context,
  width: width,
  height: height,
  fit: fit,
  scale: scale,
  alt: alt,
  error-mode: error-mode,
  ..args,
)
