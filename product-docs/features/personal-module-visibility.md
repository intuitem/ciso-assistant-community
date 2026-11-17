---
description: Hide the modules you don't use from your own navigation, without affecting anyone else
---

# Personal module visibility

Your organisation decides which modules are switched on for everyone. Within that set, you can hide the ones you don't use, so your sidebar only shows what matters to your work. A risk manager can drop the privacy register; a privacy officer can drop EBIOS RM and vulnerabilities.

The choice is yours alone: it changes what _you_ see, never what your colleagues see, and it can't turn on a module your organisation has disabled.

## Where to find it

1. Open the **⋮** menu next to your name at the bottom of the sidebar and choose **My profile** (it's also available from the [command palette](command-palette.md)).
2. Click **Settings**.
3. Open the **Modules** tab.

The tab only appears when there's something you can personalise. Third-party users don't get it: their navigation is the same narrow set whatever the module settings are.

## Hiding and showing modules

Modules are laid out in the same groups as the organisation's feature-flag settings — **Organization**, **Catalog**, **Operations**, **Management and Governance**, **Project management**, **Compliance**, **Risk management**, **GDPR / Privacy** and **Extra** — each card with a short description of what it covers.

- **Untick a module** to hide it. **Tick it again** to bring it back.
- Changes are **saved as soon as you click**; there is no Save button. The page refreshes in the background and the sidebar and command palette update straight away.
- The counter at the top reads **_n_ of _m_ visible**. It only counts modules your organisation has enabled, so if you haven't hidden anything it shows all of them as visible.

If a change can't be saved, the checkbox flips back to its previous state.

## Modules disabled by your organisation

A module your organisation has switched off is shown unticked and greyed out, with the tooltip **Disabled by your organization.** You can't enable it from here. Ask an administrator if you need it.

Your own choices are kept independently of the organisation's:

- If the organisation **enables a new module**, it shows up for you by default. You only stop seeing it if you hide it yourself.
- If you hid a module and the organisation later **disables and then re-enables it**, it stays hidden for you until you show it again.

## Resetting

**Reset to organization settings** clears every module you've hidden, so your navigation matches the organisation's settings again. The button is greyed out when you haven't hidden anything. Modules the organisation has disabled stay off; the reset only undoes your own choices.

## What you can and can't hide

Only modules that are a navigation area in their own right can be hidden: registers, catalogues and workspaces such as audits, risk assessments, third parties, incidents, tasks or the privacy register.

Settings that change **how data is displayed or behaves** aren't listed. Examples are inherent-risk columns, DORA fields, focus mode, comments and custom fields. If you could switch those off for yourself, you and your colleagues could be looking at the same object and seeing different information. They stay under your organisation's control.

{% hint style="info" %}
Hiding a module is a display preference, not a permission. It doesn't change your role or what you're allowed to do, and nothing in the module is deleted or changed. Show the module again and everything is where you left it.
{% endhint %}

## Related

- [Feature flags](../configuration/settings/feature-flags.md) — the organisation-wide settings that set the limit on what you can show.
- [Focus mode](focus-mode.md) — another per-user way to narrow the workspace, to a single domain.
- [Command palette](command-palette.md) — its navigation entries follow your module visibility.
