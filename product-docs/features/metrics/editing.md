---
description: "Change a computed metric's formula in the drawer beside it, compare the new results with the current ones, and know what a save changes"
---

# Edit a formula

**Edit formula** opens a drawer on the right of the page. The metric stays in view while you work, and the drawer draws the results of your edit against the ones the metric holds now, before anything is saved.

<figure><img src="../../.gitbook/assets/metrics-drawer-page.png" alt="A computed metric's page with the formula drawer open on the right, an edited formula and its result"><figcaption><p>The drawer sits beside the metric: nothing to leave, nothing to lose</p></figcaption></figure>

The button is in two places:

- on the metric's page, next to **Refresh now**;
- on the metric's edit form, in the **Formula** card at the top.

The drawer has two forms, depending on [where the formula lives](README.md#where-the-formula-lives): a formula made of picked metrics, or a formula that is its definition's.

## A formula made of picked metrics

This is the formula of a metric created with the [New computed metric](creating.md) window. The drawer shows its first two steps as you know them, **Metrics to combine** and **Formula**, and a third, **How to read it**, holding the unit and **Higher is better**.

The metric's name, domain, collection frequency and target are not in the drawer: they stay on the metric's edit form, which is where you change them.

<figure><img src="../../.gitbook/assets/metrics-drawer.png" alt="The drawer with an edited formula; the chart shows the current results as a dashed line and the new ones as a solid line on the same scale"><figcaption><p>Dashed: what the metric holds now. Solid: what it would hold with this formula</p></figcaption></figure>

### Compare before you save

The chart under **Latest result** draws two lines over the last 24 periods, on one scale:

- **Now**, dashed: the results the metric holds today;
- **With this formula**, solid: the results your edit would give.

Hover a point to read both values for that period. When the two lines meet, the edit does not change that period.

### What you can change

- **Swap a metric** for another one, for example the same indicator in another country: remove the row, search, pick. The formula keeps its names.
- **Add, remove, rename or reorder** metrics, as when creating.
- **Rewrite the formula**, or switch its result between **Number** and **Level**.
- **Change the unit or Higher is better.**

**Save** stays off until something changes.

### What a save does

- The metric's past results are recomputed with the new formula. The drawer says so above **Save**: "Saving recomputes this metric's past results with the new formula."
- The drawer closes. On the metric's page, the value and the chart update by themselves once the computation is done. On the edit form, you stay on the form, and it takes the change in: saving the form afterwards keeps your new formula.

### When other metrics share the definition

A definition can be shared, for example when the same indicator computed in two countries reuses one definition. Editing one metric never changes the others: the drawer warns "Other metrics use its definition (2): saving gives this metric a definition of its own and leaves them unchanged", and the confirmation reads "Saved: this metric now has a definition of its own".

A few edits are refused rather than surprise someone:

| Message | Why | What to do |
|---|---|---|
| "Other metrics read this one (…); its definition is shared, so its formula can only change once they no longer read it" | Giving this metric a new definition would change what those formulas read | Edit those formulas first, or create a new computed metric instead |
| "Other formulas read this metric as a number: its result type cannot change while they do" | A level cannot be read by a formula | Keep the result a number, or create a separate level metric that reads this one |
| "*Domain* does not hold every picked metric: pick metrics within it, or move this metric to a higher domain first." | The metric can only read metrics in its domain and below | Pick metrics within it, or change the metric's domain on its edit form first |

Making a copy of a shared definition needs the right to add metric definitions in the metric's domain.

### When a picked metric is gone

If a metric the formula read was deleted, or is no longer visible to you, its row is missing and the drawer says "Pick again the instances of: *name*". Pick a replacement under the same name, or rewrite the formula without it.

## A formula that is its definition's

Some formulas are not made of picked metrics: they combine every metric of a kind in the domain (the sum of all clicks below a group, the maximum across sites), or they read objects such as controls and audits. Those formulas belong to the definition, which several metrics share on purpose, one per domain. The drawer says so at the top: "Its formula is its definition's, *name*: every metric using it follows."

<figure><img src="../../.gitbook/assets/metrics-drawer-definition.png" alt="The drawer for a definition formula: what the formula reads, its inputs with how their instances combine, and the expression"><figcaption><p>The definition's formula, as on the definition form</p></figcaption></figure>

The drawer shows the same block as the [definition form](definition-formulas.md): what the formula reads, its inputs and how each combines, the expression, and **Try it**.

**Try it** starts on this metric's domain and collection frequency, so it previews exactly what this metric would hold, and draws the **Now** line beside the result. Try it on another domain or frequency to see what the formula gives there; the **Now** line then disappears, since this metric is not computed there.

<figure><img src="../../.gitbook/assets/metrics-drawer-definition-preview.png" alt="Try it on the metric's own domain, with the current results dashed and the edited ones solid, and a warning that five other metrics use the definition"><figcaption><p>The warning counts the other metrics a save will change</p></figcaption></figure>

Saving changes the definition, so every metric using it gets the new formula. The drawer counts them above **Save**: "Other metrics use this definition (5): saving changes their formula too." This metric is recomputed right away; the others are recomputed on their own schedule.

If you may not change the definition, the drawer says "You can try this formula here, but its definition is not yours to change." and **Save** stays off. You can still try changes in the preview.

## Closing the drawer

- **✕**, **Cancel** or **Escape** close it. Escape first closes whatever list is open inside the drawer, such as the search results or the formula suggestions.
- With changes not saved, closing asks first:

<figure><img src="../../.gitbook/assets/metrics-drawer-discard.png" alt="The drawer footer asking about unsaved changes, with Keep editing and Discard"><figcaption><p>Keep editing, or Discard the changes</p></figcaption></figure>

- **Cmd+Enter** (macOS) or **Ctrl+Enter** saves from anywhere in the drawer, the formula field included.

On a phone, the drawer takes the full width of the screen.
