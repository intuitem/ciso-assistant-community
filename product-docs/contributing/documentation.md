---
description: How to fix or extend the documentation you're reading right now
---

# Contributing documentation

This documentation lives alongside the code in the `product-docs/` directory of the [community repository](https://github.com/intuitem/ciso-assistant-community). It's authored in Markdown using GitBook's flavoured syntax and synced one-way from `main` to the published GitBook space.

That means **the source of truth is the repository** — every change goes through a pull request, gets reviewed, then ships when it's merged.

## Where things live

```
product-docs/
├── README.md                    # GitBook welcome page
├── SUMMARY.md                   # left-hand navigation; every page must be referenced here
├── .gitbook/
│   └── assets/                  # screenshots and downloadable templates
├── introduction/                # philosophy and vocabulary
├── concepts/                    # the central objects (domains, audits, controls, …)
├── installation/                # getting CISO Assistant running
├── configuration/               # organisation setup, IAM, SSO, libraries, settings
├── guides/                   # end-to-end walkthroughs
├── features/                    # catalogue of shipped capabilities
├── integrations/                # API, MCP, webhooks, third-party
└── contributing/                # this section
```

## When to send a doc PR

- A page is wrong, outdated, or confusing.
- You shipped a feature and there's no page describing it (or the page omits something important).
- A vocabulary term is missing or its definition no longer matches the code.
- Screenshots are stale.
- Cross-references are broken or point at the wrong place.

For small fixes — typos, broken links, factual corrections — a one-commit PR is fine. For larger restructures, open a discussion first so we can align on shape before you invest the writing time.

## Conventions

- **Style.** Direct, concrete, scannable. Lead with the answer; explain mechanics second. Aim for one screen of content per section.
- **Titles.** Sentence case, no leading emoji or icon. The page metadata's `description:` line shows up as a subtitle in GitBook.
- **Vocabulary discipline.** When a user-facing term differs from the model name (Domain ↔ Folder, Audit ↔ ComplianceAssessment), use the user-facing term in copy and reserve the model name for "for implementers" sections or code references.
- **PRO features.** Label PRO-only capabilities with a hint block at the top of the page or an inline `_PRO._` tag in catalogue rows. Community features get no tag.
- **Cross-links.** Use relative Markdown links (`../concepts/audits.md`) rather than absolute URLs — they survive directory moves.
- **Vocabulary entries.** When adding a new concept or feature, also add the term to `introduction/vocabulary.md` so it's discoverable through the glossary.

## GitBook-flavoured syntax

GitBook accepts standard Markdown plus a few block extensions worth knowing:

- **Hint blocks:** `{% hint style="info" %}` / `warning` / `danger` — for inline callouts.
- **Embeds:** `{% embed url="..." %}` — for videos and rich previews.
- **File attachments:** `{% file src="../.gitbook/assets/template.xlsx" %}` — for downloadable templates.
- **Steppers:** `{% stepper %}` `{% step %} … {% endstep %}` `{% endstepper %}` — for numbered walkthroughs.
- **Cross-references:** prefer plain Markdown links; the legacy `{% content-ref %}` block also works but the inline link is shorter.

Plain Markdown renders fine on GitHub too, so PRs are easy to review without the GitBook preview.

## Adding screenshots

1. Drop the image into `product-docs/.gitbook/assets/` using a descriptive filename (avoid the GitBook-generated `image (47).png` style if you can — they're fine if you can't).
2. Reference it via `<figure><img src="../.gitbook/assets/your-image.png" alt=""><figcaption></figcaption></figure>` (the figure wrapper renders nicely in GitBook; the bare `![]()` syntax also works).
3. Adjust the relative path depth (`../`, `../../`) based on where the Markdown file sits.

## Adding a new page

1. Create the file in the right subdirectory.
2. Add an entry to `SUMMARY.md` so it appears in the navigation — GitBook only renders pages that are listed there.
3. If the page documents a feature, copy [the feature page template](feature-page-template.md) as a starting point.
4. If the page introduces new terminology, add the term to `introduction/vocabulary.md`.
5. Run a quick link check before pushing — every relative link should resolve to an existing file.

## Preview before merge

When you open a PR that touches `product-docs/`, the maintainers can render a GitBook preview to review the rendered output. You don't need GitBook access yourself — pushing the PR is enough.

## Related

- [Feature page template](feature-page-template.md)
- [Repository CONTRIBUTING.md](https://github.com/intuitem/ciso-assistant-community/blob/main/CONTRIBUTING.md)
