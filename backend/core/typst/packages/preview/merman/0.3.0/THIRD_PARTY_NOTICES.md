# Third-Party Notices

This file records the third-party material in the `typst-publish` artifact scope.
It is generated from the release component contract and is intentionally limited to this artifact.
The wrapper and Merman-authored code remain under the project license; each component below keeps its own terms.

## Artifact scope

- ID: `typst-publish`
- Description: The Typst WASM publish profile, including ELK and wasm-minimal-protocol but excluding RaTeX.
- Components: `cose-base-v1`, `cose-base-v2`, `cytoscape`, `cytoscape-cose-bilkent`, `cytoscape-fcose`, `d3-shape`, `dagre`, `dompurify`, `fmin`, `graphlib`, `layout-base-v1`, `layout-base-v2`, `mermaid`, `rough-rs`, `roughjs`, `sanitize-url`, `venn-js`, `zenuml-core`, `eclipse-elk`, `elkjs`, `wasm-minimal-protocol`

## Components

### cose-base 1.x

Manatee contains Rust translations and adaptations of CoSE layout behavior from this baseline.

- Version: `1.0.3`
- Source: https://github.com/iVis-at-Bilkent/cose-base.git @ `914bfe712991534af1d8b795d6f262687edc2563`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`
- Legal file: `THIRD_PARTY_LICENSES/cose-base-v1/LICENSE`

### cose-base 2.x

Manatee contains Rust translations and adaptations of the newer CoSE base behavior from this baseline.

- Version: `2.2.0`
- Source: https://github.com/iVis-at-Bilkent/cose-base.git @ `37f07ed2b8803211ec6c74110574cc47c156a136`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`
- Legal file: `THIRD_PARTY_LICENSES/cose-base-v2/LICENSE`

### Cytoscape.js

Architecture layout and styling use source-backed Cytoscape behavior and defaults.

- Version: `3.34.0`
- Source: https://github.com/cytoscape/cytoscape.js.git @ `22716bfb75834b56fa6679648b0abb06f4ae691c`
- Source path: `.`
- Relationship: `behavior-reference`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`, `crates/merman-render/src/architecture.rs`
- Legal file: `THIRD_PARTY_LICENSES/cytoscape/LICENSE`

### cytoscape.js-cose-bilkent

Manatee includes source-backed CoSE-Bilkent layout behavior translated to Rust.

- Version: `4.1.0`
- Source: https://github.com/iVis-at-Bilkent/cytoscape.js-cose-bilkent.git @ `999090a8438b4f14788d636ef4fd7a5355e29e8c`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`
- Legal file: `THIRD_PARTY_LICENSES/cytoscape-cose-bilkent/LICENSE`

### cytoscape.js-fcose

The headless Architecture layout is a modified Rust implementation of FCoSE behavior.

- Version: `2.2.0`
- Source: https://github.com/iVis-at-Bilkent/cytoscape.js-fcose.git @ `78afcf96512a409abc903699277ad616c02dfad9`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`, `crates/merman-render/src/architecture.rs`
- Legal file: `THIRD_PARTY_LICENSES/cytoscape-fcose/LICENSE`

### d3-shape

The SVG parity layer translates D3 curve algorithms, including basis, natural, step, cardinal, bump, and Catmull-Rom variants.

- Version: `3.2.0`
- Source: https://github.com/d3/d3-shape.git @ `8ec82658454750cfa29efb1e0ea514e3dd9b2297`
- Source path: `src/curve`
- Relationship: `modified`, `translated`
- License: `ISC`
- Local evidence: `crates/merman-render/src/svg/parity/curve.rs`
- Legal file: `THIRD_PARTY_LICENSES/d3-shape/LICENSE`

### Dagre

Dugong is a modified Rust translation of Dagre's directed graph layout pipeline.

- Version: `2.0.2`
- Source: https://github.com/dagrejs/dagre.git @ `ba986662394f8f3ed608717194e5958f3386ce01`
- Source path: `lib`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/dugong`
- Legal file: `THIRD_PARTY_LICENSES/dagre/LICENSE`

### DOMPurify

Merman selects DOMPurify's Apache-2.0 option for generated sanitizer defaults; the exact upstream Apache-2.0 license file is preserved.

- Version: `3.4.13`
- Source: https://github.com/cure53/DOMPurify.git @ `3067f774676975de12306effd6db6ad7a9a8c17f`
- Source path: `.`
- Relationship: `generated`, `translated`
- License: `(Apache-2.0 OR MPL-2.0)`
- Local evidence: `crates/merman-core/src/generated/dompurify_defaults.rs`
- Legal file: `THIRD_PARTY_LICENSES/dompurify/LICENSE`

### fmin

The Venn layout kernel translates the fmin Nelder-Mead and conjugate-gradient optimization behavior.

- Version: `0.0.4`
- Source: https://github.com/benfred/fmin.git @ `6b155c9f4a6ecf73ea5d71666da8e5dcd418b18b`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `BSD-3-Clause`
- Local evidence: `crates/merman-render/src/venn.rs`
- Legal file: `THIRD_PARTY_LICENSES/fmin/LICENSE`

### Graphlib

dugong-graphlib is a modified Rust translation of the graph model used by Dagre.

- Version: `2.2.4`
- Source: https://github.com/dagrejs/graphlib.git @ `380d5efa1f4ab0904539f046bdba583d14ac2add`
- Source path: `lib`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/dugong-graphlib`
- Legal file: `THIRD_PARTY_LICENSES/graphlib/LICENSE`

### layout-base 1.x

Manatee translates shared layout-base geometry, graph, and force-layout primitives from this baseline.

- Version: `1.0.2`
- Source: https://github.com/iVis-at-Bilkent/layout-base.git @ `836898aa4a88e2794774997d7128b383108a3d5a`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`
- Legal file: `THIRD_PARTY_LICENSES/layout-base-v1/LICENSE`

### layout-base 2.x

Manatee also follows the newer layout-base behavior selected by the FCoSE dependency graph.

- Version: `2.0.1`
- Source: https://github.com/iVis-at-Bilkent/layout-base.git @ `3f7549940feef31416cc35ef8256282ebc4d1ecd`
- Source path: `.`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/manatee`
- Legal file: `THIRD_PARTY_LICENSES/layout-base-v2/LICENSE`

### Mermaid

Merman independently implements Mermaid-compatible behavior while translating selected algorithms, generating defaults, copying architecture icon data, and retaining upstream fixtures and snapshots.

- Version: `11.16.1`
- Source: https://github.com/mermaid-js/mermaid.git @ `7ecca0cd7f1658ef74f4e7e91f925724ef403bbf`
- Source path: `packages/mermaid`
- Relationship: `behavior-reference`, `copied`, `fixtures`, `generated`, `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/merman-core/src`, `crates/merman-render/src`, `crates/merman-render/src/svg/parity/architecture/icons.rs`, `fixtures`
- Legal file: `THIRD_PARTY_LICENSES/mermaid/LICENSE`

### rough-rs roughr

roughr-merman is a modified in-tree fork of the rough-rs roughr crate.

- Version: `0.12.0`
- Source: https://github.com/orhanbalci/rough-rs.git @ `b1c2d96c944da4e74275aa09892be14e2d54445a`
- Source path: `roughr`
- Relationship: `copied`, `modified`
- License: `MIT`
- Local evidence: `crates/roughr`
- Legal file: `THIRD_PARTY_LICENSES/rough-rs/LICENSE`

### Rough.js

The roughr fork aligns its randomization and drawing-operation semantics with Rough.js as used by Mermaid.

- Version: `4.6.6`
- Source: https://github.com/pshihn/rough.git @ `56a2762171b1294d643501e8d14f120db6b27bd7`
- Source path: `src`
- Relationship: `behavior-reference`, `translated`
- License: `MIT`
- Local evidence: `crates/roughr`
- Legal file: `THIRD_PARTY_LICENSES/roughjs/LICENSE`

### sanitize-url

Merman's URL sanitization behavior is a source-backed Rust translation of sanitize-url.

- Version: `7.1.1`
- Source: https://github.com/braintree/sanitize-url.git @ `b1e8d50e4066a9af00fa042176676374747f754b`
- Source path: `src`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/merman-core/src/utils.rs`
- Legal file: `THIRD_PARTY_LICENSES/sanitize-url/LICENSE`

### @upsetjs/venn.js

The Venn family uses a modified Rust translation of the venn.js geometry and layout kernel.

- Version: `2.0.0`
- Source: https://github.com/upsetjs/venn.js.git @ `350c835aab4a92a7570963c28f725cf9f6e5f258`
- Source path: `src`
- Relationship: `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/merman-core/src/diagrams/venn.rs`, `crates/merman-render/src/venn.rs`
- Legal file: `THIRD_PARTY_LICENSES/venn-js/LICENSE`

### ZenUML Core

Merman's ZenUML grammar, model, renderer, emoji/icon data, and behavior probes follow the admitted ZenUML Core 3.50.1 source baseline.

- Version: `3.50.1`
- Source: https://github.com/mermaid-js/zenuml-core.git @ `38404ccc14243ed54ab45b804b2eb6f2ca73af36`
- Source path: `.`
- Relationship: `behavior-reference`, `copied`, `modified`, `translated`
- License: `MIT`
- Local evidence: `crates/merman-core/src/diagrams/zenuml`, `crates/merman-render/assets/zenuml`, `crates/merman-render/src/zenuml.rs`
- Legal file: `THIRD_PARTY_LICENSES/zenuml-core/LICENSE`

### Eclipse Layout Kernel

The merman-elk-layered crate contains a modified Rust source translation of Eclipse ELK layered algorithms under EPL-2.0.

- Version: `0.9.1`
- Source: https://github.com/eclipse-elk/elk.git @ `62d5909f96fad541bc101ad52dabaece6b7eab7e`
- Source path: `plugins/org.eclipse.elk.alg.layered`
- Relationship: `modified`, `translated`
- License: `EPL-2.0`
- Local evidence: `crates/merman-elk-layered`, `crates/merman-layout-elk`
- Legal file: `THIRD_PARTY_LICENSES/eclipse-elk/LICENSE.md`

### elkjs

Mermaid's ELK adapter behavior is compared against this JavaScript distribution, which is generated from Eclipse ELK sources.

- Version: `0.9.3`
- Source: https://github.com/kieler/elkjs.git @ `a8304cf79fde75bc2ab1a89d28320f53f8637436`
- Source path: `.`
- Relationship: `behavior-reference`
- License: `EPL-2.0`
- Local evidence: `crates/merman-layout-elk`, `playground`
- Legal file: `THIRD_PARTY_LICENSES/elkjs/LICENSE.md`

### wasm-minimal-protocol

The Typst WASM transport links wasm-minimal-protocol; its upstream license file is the Unlicense text.

- Version: `0.2.0`
- Source: https://github.com/typst-community/wasm-minimal-protocol.git @ `cc08c96b8e7683188eb16ad315a9689b89290f85`
- Source path: `crates/macro`
- Relationship: `linked`
- License: `Unlicense`
- Local evidence: `Cargo.lock`, `crates/merman-typst-plugin`
- Legal file: `THIRD_PARTY_LICENSES/wasm-minimal-protocol/LICENSE`
