---
description: "Enable the feature, import a ready-made derogation form, publish it to an audience, file a request as a requester and decide it as a reviewer"
---

# Filing and deciding your first request

This walkthrough takes about ten minutes. You will enable the feature, import a ready-made **Derogation request** form, publish it so people can actually file it, submit one as a requester, then decide it as a reviewer.

You need an administrator for the first three steps. For the last two you need **two different people** — or at least two accounts — because whoever submits a request may not decide it.

## 1. Enable the feature

Quick forms ship behind a feature flag.

1. Open **Extra > Settings**, then the **Feature flags** tab.
2. Turn on **Forms and Requests**. The description reads: "Standalone forms filled outside an audit, and the requests they raise".
3. Turn on **Custom portals** as well. A portal tile is how a requester starts a request, so without it the rest of this walkthrough has no entry point.
4. Save. Three entries appear in the sidebar: **Quick forms** under Catalog, **Requests** under Governance, and **My requests** at the top.

## 2. Import a form

A quick form is library content, like a framework. One ships with the platform.

1. Go to **Libraries**.
2. Find **Derogation request** and import it. There is no quick-forms filter chip on this page yet, so search by name rather than filtering by type.
3. Open **Quick forms** under Catalog. The form is listed there.

Open it to see what you imported: three pages — *What you need*, *Risk and duration*, *What you are doing instead* — and two outcome rules.

{% hint style="info" %}
No **+** button on the **Quick forms** list is intentional. Forms come from libraries; to write your own, use the library builder (see step 6).
{% endhint %}

## 3. Put it on a portal

A form in the catalog cannot be filled by anyone. A **portal tile** is what people click to start a request, and wiring that tile is what makes the form reachable.

1. Go to **Extra > Manage portals** and open a portal your requesters can see, or create one.
2. Add a tile and set its kind to **Quick form**.
3. Wire it. The **Form source** dropdown offers two ways, and they authorise differently:
   - **A published form**, if one exists — the tile then inherits its audience, submission domain and reviewers.
   - **Otherwise pick the quick form directly**, and choose the domain requests should land in. This is the inline wiring.
4. Save the portal.

{% hint style="warning" %}
The two wirings authorise differently, and that is the whole of the choice:

- **Configure on this tile** — whoever clicks it must hold the right to create a request **in the domain the tile names**, or they get "No permission to file a request in '…'". Use it for internal tiles, where the people clicking already work in that domain.
- **A published form** — authorises on audience membership instead, so someone with no role in the domain can still file. Use it for self-service.

Published forms have no screen of their own in the navigation yet, so inline is the easier of the two to reach today.
{% endhint %}

## 4. File a request

Sign in as someone in the audience — a person with no particular permissions on the submission domain. That is the point: audience membership is the authorisation.

1. Open **My requests**. The subtitle reads "Everything you have asked for — drafts first."
2. Under **Start a request from**, click the portal that carries your tile, then click the tile.
3. Answer the first page and move on. Answers save as you go — the request appears in your list as **Unfinished** with the hint "Your answers are saved. Pick up where you left off."
4. On the last page, answer **Is a compensating control already in place?** with **No**. Watch the question below it change: answering *No* asks what you plan to put in place, answering *Yes* asks which control already covers it.
5. Click **Submit**.

If **Submit** is greyed out, hover it: "Answer every required question on every visible page before submitting." Required questions on hidden pages do not count — only what you can actually see.

The request moves to **Awaiting review**, and its content freezes. From here you can still **Drop** it, which withdraws it without a reviewer's decision.

## 5. Decide it

Sign in as a reviewer — someone with approval rights on the submission domain.

1. Open **Requests** under Governance. The queue has three columns: **Open**, **In progress**, **Done**.
2. Your request is in **Open**. Open it.
3. Read the answers, then either:
   - Click **Take it** first if you want to signal you are working on it. It moves to **In progress** and shows your name. This is optional — a quick decision does not need it.
   - Or decide straight away with **Accept** or **Reject**.
4. Add an observation if the decision needs explaining, then decide.

Two things worth noticing on this screen:

- If the answers said no compensating control is in place, a **Suggested actions** button appears. That is a supervised action: a workflow the platform offers *because of* what the answers said. You run it deliberately; it does not fire on its own.
- If you try to decide a request you filed yourself, you are refused. Whoever submitted a request may not decide it, whatever permissions they hold.

Instead of deciding, you can send the request back to the requester. It returns to **Draft**, they change their answers and resubmit.

## 6. Write your own form

Once the ready-made one makes sense, build one of your own.

1. Go to **Extra > Library builder**.
2. Click **New quick form**. Give it a name and a packager, then **Create and edit**.
3. You land in the editor with one page. Add pages, questions and choices.

A few things worth knowing before you design one:

- **Scores and outcomes are what make it more than a web form.** Give choices a score, then write outcome rules over the answers — either on a specific answer ("personal data was ticked") or on the total ("anything above 100 needs a full assessment").
- **Check your outcomes by filling the form in.** A rule that references a question that does not exist does not raise an error — it silently never fires, and the form looks like it works. Use the preview, answer it, and confirm the outcomes you expect actually appear.
- **A published form is versioned like any library.** Re-importing a newer version updates it in place, except for questions already answered by a request that has left draft. Those are kept on purpose — deleting them would rewrite the record a decision was made on.

## Where to go next

- [Quick forms and requests](../concepts/quick-forms.md) — the concepts behind what you just did: publication, outcomes, separation of duties, and turning an accepted request into a governed object.
- [Workflows](../concepts/workflows.md) — supervised actions are workflows with a manual trigger.
