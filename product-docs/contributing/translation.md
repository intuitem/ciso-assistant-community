---
description: How to translate the CISO Assistant interface and (in-coming) library content
---

# Contributing translations

CISO Assistant ships in multiple languages and welcomes new locales and translation improvements from the community.

## Translating the interface

Interface strings live in `frontend/messages/` as one JSON file per locale (`en.json`, `fr.json`, `de.json`, `es.json`, …). Each file maps a translation key to the string shown in the UI for that locale.

**The recommended workflow today is a direct pull request against those JSON files.** The previously-recommended [fink](https://fink.inlang.com/) web editor is currently broken; until that situation is resolved, please go through Git directly — it's also the cleanest path and what reviewers prefer.

### The flow

1. **Pick the file.** `frontend/messages/<locale>.json`. For a new locale that doesn't exist yet, copy `en.json` to `<your-locale>.json` and start from there.
2. **Edit the JSON.** Translate the values; keep the keys unchanged. Preserve any substitution tokens (`{count}`, `{name}`, `{date}`) verbatim — they're replaced at runtime and must stay intact.
3. **Mind the structure.** The file is flat key→value JSON. Don't reorder keys (it makes the diff harder to review). Don't add or remove keys — those track string changes on the English side.
4. **Open a PR** with a short description of the locale(s) touched and the scope of the change (full pass, partial, fix of a specific section). Reviewers will check for placeholder integrity and obvious register issues.

### Translation quality

- **Match the register.** CISO Assistant's English copy is direct and concrete — translations should be too. Avoid stiff calques or marketing flourishes.
- **Read it aloud.** If it sounds artificial, it probably is. Prefer natural verbs and ordinary phrasing in the target language.
- **Respect terminology.** When in doubt, align with the official translation used by the corresponding standard or regulator (ISO publishes localised versions of its standards; ANSSI, NIST, ENISA publish localised material).
- **Leave placeholders alone.** Substitution tokens like `{count}` or `{name}` must be preserved verbatim.

## Translating library content

Translating framework requirements, threat names, and other library content is **in-coming** — the format will be documented here once the tooling stabilises. In the meantime, get in touch through the discussion space if you'd like to contribute on a specific framework.

## Related

- [Changing the language](../configuration/language.md) — how end-users switch the UI locale
- [Contributing code](code.md) — for related infrastructure changes
