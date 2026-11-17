#import "plugin.typ": merman-plugin

#let merman-capabilities() = {
  json(merman-plugin.capabilities_json())
}
