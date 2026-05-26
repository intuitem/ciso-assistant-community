---
description: The Ctrl/Cmd+K palette for jumping anywhere in the workspace
---

# Command palette

The **command palette** is a keyboard-first jump-to surface for navigating the workspace and triggering a small set of actions, without leaving the keyboard or scanning the sidebar.

It complements the sidebar and breadcrumbs: pick the sidebar when you want to browse what's available, the palette when you already know where you're going.

## How to open it

There are two ways to open the palette, and both produce the same UI:

- **The search pill in the top-right** of the application bar — labelled **Search…** with a small `⌘K` / `Ctrl+K` hint chip on its right.
- **The keyboard shortcut**:
  - macOS — `⌘ + K`
  - Windows / Linux — `Ctrl + K`

The shortcut works from any page in the app — there's no need to focus the search button first.

{% hint style="info" %}
The palette is **not available** to third-party users (representatives logging into the auditee surface). It's an internal-user tool — the search pill and shortcut are simply not wired up on that surface.
{% endhint %}

## What's inside

Open the palette and you'll see a search input over two grouped lists:

### Navigation

Every destination reachable from the sidebar — Domains, Audits, Risks, Applied controls, Insights, and so on, including the **My profile** entry. Type to filter; matching is **accent-insensitive** so `frameworks` matches whether you type `frameworks`, `Frameworks`, or `framework`. Selecting a row navigates there and closes the palette.

The list is automatically pruned by the same **feature-flag visibility** that hides sidebar sections — if your instance has the privacy module disabled, _Processings_ and _Personal data_ never show up in the palette either.

### Actions

A small group of non-navigation commands. Today it contains:

- **Open assistant** — opens the chat assistant. Visible only when the `chat_mode` [feature flag](../configuration/settings/feature-flags.md) is on.

More actions are expected here over time — the palette is designed to host shortcut commands that don't fit the sidebar.

## Keyboard controls

While the palette is open:

| Key | Action |
|---|---|
| `↑` / `↓` | Move selection between rows |
| `↵` (Enter) | Open the selected row |
| `Esc` | Close the palette |
| Click outside | Close the palette |

If the typed text **doesn't match any row** in Navigation or Actions, pressing `↵` falls through to [universal search](search.md): the palette closes, and the search results page opens with your query pre-filled. There's also an explicit **Press Enter to search across all objects** button rendered below the empty state — same outcome, just clickable.

## Why use it

- **Faster than the sidebar** for "I know what I want" navigation — three keys (`⌘K`, then a few letters, then `↵`) versus reach-for-the-mouse and scroll.
- **Discovery** — typing the start of a name surfaces destinations you may have forgotten existed, including any pages added by a recent platform upgrade.
- **Search escape hatch** — when the typed text isn't a page name, the palette is also the front door to the [universal search](search.md) over your actual data (assets, audits, controls, evidences, …).

## Related

- [Universal search](search.md) — the search results page reached by typing a query and pressing Enter.
- [Feature flags](../configuration/settings/feature-flags.md) — what controls which Navigation and Actions entries show up.
