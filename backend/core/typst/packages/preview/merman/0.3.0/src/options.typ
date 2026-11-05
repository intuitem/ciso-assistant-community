#import "units.typ": canonical-css-px-string, css-px-number-string, css-px-string

#let dictionary-or-none(value, name) = {
  if value == none {
    none
  } else if type(value) == dictionary {
    value
  } else {
    panic(name + " must be a dictionary")
  }
}

#let profile-field(profile, key, alt: none) = {
  let profile = dictionary-or-none(profile, "merman profile")
  if profile == none {
    none
  } else if key in profile {
    profile.at(key)
  } else if alt != none and alt in profile {
    profile.at(alt)
  } else {
    none
  }
}

#let choose-value(profile-value, direct-value, default: none) = {
  if direct-value != none {
    direct-value
  } else if profile-value != none {
    profile-value
  } else {
    default
  }
}

#let resolve-diagram-id(profile-id, profile-diagram-id, direct-id, direct-diagram-id) = {
  if direct-diagram-id != none {
    direct-diagram-id
  } else if direct-id != none {
    direct-id
  } else if profile-diagram-id != none {
    profile-diagram-id
  } else {
    profile-id
  }
}

#let merge-dict(base, override, name) = {
  let base = dictionary-or-none(base, name)
  let override = dictionary-or-none(override, name)
  if base == none {
    override
  } else if override == none {
    base
  } else {
    (: ..base, ..override)
  }
}

#let font-descriptor-name(font) = {
  if type(font) == str {
    font
  } else if type(font) == dictionary {
    if "name" not in font or type(font.at("name")) != str {
      panic("merman typography font descriptor must contain a string name")
    }
    font.at("name")
  } else {
    panic("merman typography font must contain only strings or font descriptors")
  }
}

#let font-family-value(font) = {
  if font == none {
    none
  } else if type(font) == array {
    font.map(font-descriptor-name).join(", ")
  } else {
    font-descriptor-name(font)
  }
}

#let font-size-value(size) = {
  if size == none {
    none
  } else if type(size) == str {
    canonical-css-px-string(size, name: "merman typography size")
  } else if type(size) == length {
    css-px-string(size, name: "merman typography size")
  } else if type(size) == int or type(size) == float {
    css-px-number-string(size, name: "merman typography size")
  } else {
    panic("merman typography size must be a CSS px string, absolute Typst length, or pixel number")
  }
}

#let host-theme-from-font(font-family, font-size) = {
  let family = font-family-value(font-family)
  let size = font-size-value(font-size)
  let out = if family == none { (:) } else { (font_family: family) }
  let out = if size == none { out } else { (: ..out, font_size: size) }
  if out.len() == 0 {
    none
  } else {
    out
  }
}

#let context-host-theme(font-family, font-size) = {
  host-theme-from-font(font-family, font-size)
}

#let field3(dict, a, b, c) = {
  if dict == none {
    none
  } else if a in dict {
    dict.at(a)
  } else if b in dict {
    dict.at(b)
  } else if c in dict {
    dict.at(c)
  } else {
    none
  }
}

#let typography-host-theme(typography) = {
  let typography = dictionary-or-none(typography, "merman typography")
  if typography == none {
    none
  } else {
    let allowed = (
      "font",
      "font-family",
      "font_family",
      "size",
      "font-size",
      "font_size",
    )
    for key in typography.keys() {
      if not allowed.contains(key) {
        panic("unsupported merman typography key: " + key)
      }
    }
    host-theme-from-font(
      field3(typography, "font", "font-family", "font_family"),
      field3(typography, "size", "font-size", "font_size"),
    )
  }
}

#let merged-host-theme(
  context-host-theme,
  profile-typography,
  profile-host-theme,
  typography,
  host-theme,
) = {
  let out = context-host-theme
  let out = merge-dict(out, typography-host-theme(profile-typography), "merman host-theme")
  let out = merge-dict(out, profile-host-theme, "merman host-theme")
  let out = merge-dict(out, typography-host-theme(typography), "merman host-theme")
  merge-dict(out, host-theme, "merman host-theme")
}

#let build-presentation-theme(theme) = {
  let theme = dictionary-or-none(theme, "merman host-theme")
  if theme == none {
    none
  } else {
    let allowed = (
      "preset",
      "appearance",
      "font-family",
      "font_family",
      "font-size",
      "font_size",
      "roles",
      "series-palette",
      "series_palette",
    )
    for key in theme.keys() {
      if not allowed.contains(key) {
        panic("unsupported merman host-theme key: " + key)
      }
    }

    let font-family = if "font-family" in theme {
      theme.at("font-family")
    } else if "font_family" in theme {
      theme.at("font_family")
    } else {
      none
    }
    let font-size = if "font-size" in theme {
      theme.at("font-size")
    } else if "font_size" in theme {
      theme.at("font_size")
    } else {
      none
    }
    let series-palette = if "series-palette" in theme {
      theme.at("series-palette")
    } else if "series_palette" in theme {
      theme.at("series_palette")
    } else {
      none
    }

    let out = (:)
    let out = if "preset" in theme and theme.at("preset") != none {
      (: ..out, preset: theme.at("preset"))
    } else {
      out
    }
    let out = if "appearance" in theme and theme.at("appearance") != none {
      (: ..out, appearance: theme.at("appearance"))
    } else {
      out
    }
    let out = if font-family != none { (: ..out, font_family: font-family) } else { out }
    let out = if font-size != none { (: ..out, font_size: font-size) } else { out }
    let out = if "roles" in theme and theme.at("roles") != none {
      (: ..out, roles: theme.at("roles"))
    } else {
      out
    }
    let out = if series-palette != none {
      (: ..out, series_palette: series-palette)
    } else {
      out
    }
    if out.len() == 0 { none } else { out }
  }
}

#let build-presentation-options(profile, theme) = {
  let theme = build-presentation-theme(theme)
  let out = if profile == none { (:) } else { (profile: profile) }
  let out = if theme == none { out } else { (: ..out, theme: theme) }
  if out.len() == 0 { none } else { out }
}

#let apply-theme-site-config(site-config, theme, theme-name, base-theme) = {
  let theme-name = choose-value(base-theme, theme-name)
  if theme == none and theme-name == none {
    dictionary-or-none(site-config, "merman site-config")
  } else {
    let out = if site-config == none {
      (:)
    } else {
      dictionary-or-none(site-config, "merman site-config")
    }
    let out = if theme-name != none {
      (: ..out, theme: theme-name)
    } else {
      out
    }
    if theme != none {
      (: ..out, themeVariables: theme)
    } else {
      out
    }
  }
}

#let build-layout-options(
  layout,
  container-width,
  container-height,
  base-layout: none,
) = {
  if layout != none {
    layout
  } else {
    let out = if base-layout != none {
      dictionary-or-none(base-layout, "merman layout")
    } else {
      (:)
    }
    let out = if container-width != none {
      (: ..out, container_width: container-width)
    } else {
      out
    }
    let out = if container-height != none {
      (: ..out, container_height: container-height)
    } else {
      out
    }
    out
  }
}

#let layout-container-width(layout) = {
  let layout = dictionary-or-none(layout, "merman layout")
  if layout != none and "container_width" in layout {
    layout.at("container_width")
  } else {
    none
  }
}

#let build-environment-options(
  environment,
  text-measurement,
  math-renderer,
  base-environment: none,
) = {
  let out = merge-dict(base-environment, environment, "merman environment")
  let out = if text-measurement != none {
    let out = if out == none { (:) } else { out }
    (: ..out, text_measurement: text-measurement)
  } else {
    out
  }
  if math-renderer != none {
    let out = if out == none { (:) } else { out }
    (: ..out, math_renderer: math-renderer)
  } else {
    out
  }
}

#let mermaid-profile(
  options: none,
  site-config: none,
  presentation-profile: none,
  host-theme: none,
  typography: none,
  theme: none,
  theme-name: none,
  base-theme: none,
  pipeline: none,
  id: none,
  diagram-id: none,
  background: none,
  layout: none,
  environment: none,
  scoped-css: none,
  css-override-policy: none,
  drop-native-duplicate-fallbacks: none,
  text-measurement: none,
  math-renderer: none,
  container-width: none,
  container-height: none,
  fixed-today: none,
  fixed-local-offset-minutes: none,
  figure: none,
) = {
  (
    options: options,
    site-config: site-config,
    presentation-profile: presentation-profile,
    host-theme: host-theme,
    typography: typography,
    theme: theme,
    theme-name: theme-name,
    base-theme: base-theme,
    pipeline: pipeline,
    id: id,
    diagram-id: diagram-id,
    background: background,
    layout: layout,
    environment: environment,
    scoped-css: scoped-css,
    css-override-policy: css-override-policy,
    drop-native-duplicate-fallbacks: drop-native-duplicate-fallbacks,
    text-measurement: text-measurement,
    math-renderer: math-renderer,
    container-width: container-width,
    container-height: container-height,
    fixed-today: fixed-today,
    fixed-local-offset-minutes: fixed-local-offset-minutes,
    figure: figure,
  )
}

#let opaque-render-config(binding-options, direct-options: none, profile-options: none) = {
  (
    binding_options: binding-options,
    direct_layout: none,
    direct_options: direct-options,
    direct_container_width: none,
    profile_layout: none,
    profile_layout_container_width: none,
    profile_options: profile-options,
  )
}

#let render-config(
  options: none,
  profile: none,
  typography: none,
  context-host-theme: none,
  site-config: none,
  presentation-profile: none,
  host-theme: none,
  theme: none,
  theme-name: none,
  base-theme: none,
  pipeline: none,
  id: none,
  diagram-id: none,
  background: none,
  layout: none,
  environment: none,
  scoped-css: none,
  css-override-policy: none,
  drop-native-duplicate-fallbacks: none,
  text-measurement: none,
  math-renderer: none,
  container-width: none,
  container-height: none,
  fixed-today: none,
  fixed-local-offset-minutes: none,
) = {
  if options != none {
    opaque-render-config(options, direct-options: options)
  } else {
    let profile-options = profile-field(profile, "options")
    if profile-options != none {
      opaque-render-config(profile-options, profile-options: profile-options)
    } else {
      let profile-site-config = profile-field(profile, "site-config", alt: "site_config")
      let profile-presentation-profile = profile-field(profile, "presentation-profile")
      let profile-host-theme = profile-field(profile, "host-theme")
      let profile-typography = profile-field(profile, "typography")
      let profile-layout = profile-field(profile, "layout")
      let profile-layout-container-width = layout-container-width(profile-layout)
      let profile-environment = profile-field(profile, "environment")
      let profile-text-measurement = profile-field(profile, "text-measurement")
      let profile-math-renderer = profile-field(profile, "math-renderer")

      let profile-site-config = apply-theme-site-config(
        profile-site-config,
        profile-field(profile, "theme"),
        profile-field(profile, "theme-name", alt: "theme_name"),
        profile-field(profile, "base-theme", alt: "base_theme"),
      )
      let site-config = if site-config == none {
        profile-site-config
      } else {
        dictionary-or-none(site-config, "merman site-config")
      }
      let site-config = apply-theme-site-config(site-config, theme, theme-name, base-theme)
      let pipeline = choose-value(profile-field(profile, "pipeline"), pipeline, default: "resvg-safe")
      let profile-id = profile-field(profile, "id")
      let profile-diagram-id = profile-field(profile, "diagram-id", alt: "diagram_id")
      let background = choose-value(profile-field(profile, "background"), background)
      let scoped-css = choose-value(profile-field(profile, "scoped-css", alt: "scoped_css"), scoped-css)
      let css-override-policy = choose-value(
        profile-field(profile, "css-override-policy", alt: "css_override_policy"),
        css-override-policy,
      )
      let drop-native-duplicate-fallbacks = choose-value(
        profile-field(
          profile,
          "drop-native-duplicate-fallbacks",
          alt: "drop_native_duplicate_fallbacks",
        ),
        drop-native-duplicate-fallbacks,
      )
      let container-width = choose-value(
        profile-field(profile, "container-width", alt: "container_width"),
        container-width,
      )
      let container-height = choose-value(
        profile-field(profile, "container-height", alt: "container_height"),
        container-height,
      )
      let fixed-today = choose-value(profile-field(profile, "fixed-today", alt: "fixed_today"), fixed-today)
      let fixed-local-offset-minutes = choose-value(
        profile-field(profile, "fixed-local-offset-minutes", alt: "fixed_local_offset_minutes"),
        fixed-local-offset-minutes,
      )
      let presentation-profile = choose-value(profile-presentation-profile, presentation-profile)

      let host-theme = merged-host-theme(
        context-host-theme,
        profile-typography,
        profile-host-theme,
        typography,
        host-theme,
      )
      let presentation = build-presentation-options(presentation-profile, host-theme)

      let binding-options = (
        version: 2,
        fixed_today: fixed-today,
        fixed_local_offset_minutes: fixed-local-offset-minutes,
        site_config: site-config,
        layout: build-layout-options(
          layout,
          container-width,
          container-height,
          base-layout: profile-layout,
        ),
        environment: build-environment-options(
          environment,
          text-measurement,
          math-renderer,
          base-environment: build-environment-options(
            profile-environment,
            profile-text-measurement,
            profile-math-renderer,
          ),
        ),
        svg: (
          diagram_id: resolve-diagram-id(
            profile-id,
            profile-diagram-id,
            id,
            diagram-id,
          ),
          pipeline: pipeline,
          root_background_color: background,
          scoped_css: scoped-css,
          css_override_policy: css-override-policy,
          drop_native_duplicate_fallbacks: drop-native-duplicate-fallbacks,
        ),
      )
      let binding-options = if presentation == none {
        binding-options
      } else {
        (: ..binding-options, presentation: presentation)
      }
      (
        binding_options: binding-options,
        direct_layout: layout,
        direct_options: none,
        direct_container_width: container-width,
        profile_layout: profile-layout,
        profile_layout_container_width: profile-layout-container-width,
        profile_options: none,
      )
    }
  }
}

#let config-with-context-width(config, width) = {
  if width == none or config.direct_layout != none or config.direct_container_width != none or config.direct_options != none or config.profile_options != none or config.profile_layout_container_width != none {
    config
  } else {
    let binding-options = config.binding_options
    let layout = build-layout-options(
      none,
      width,
      none,
      base-layout: config.profile_layout,
    )
    (: ..config, binding_options: (: ..binding-options, layout: layout))
  }
}

#let build-binding-options(..args) = {
  render-config(..args).binding_options
}

#let options-bytes(options) = {
  if options == none {
    bytes(())
  } else {
    bytes(json.encode(options))
  }
}
