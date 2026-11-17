---
description: Animate risk scenarios across the matrix from inherent to residual, and project when they will reach residual risk from the ETAs of their extra controls
---

# Risk trajectory

The **Risk trajectory** view replays a risk assessment on its risk matrix. Each scenario is a dot that moves from cell to cell as it goes from inherent to current to residual risk, so you can see at a glance which scenarios your treatment actually moves, and which ones it doesn't.

A second mode, **Projection**, turns the same matrix into a forecast: drag a date slider and scenarios drop to their residual position on the day their planned controls are due. A chart underneath shows how many scenarios sit at each risk level over time.

## Where to find it

Open a risk assessment and click **Risk trajectory** in the button column on the right of the detail page, next to **Action plan** and **Analytics**. The page title repeats the assessment name and version; the back arrow returns you to the assessment.

The view is read-only and available in every edition. There is no dedicated feature flag, but the **Inherent Risk** feature flag decides how many stages are shown (see below).

## What you see

### The animated matrix

The page shows the assessment's risk matrix, using the same axis orientation and labels as the rest of the application. Each scenario is a round badge carrying its reference ID (or a sequence number when it has none). When several scenarios share a cell, they are laid out side by side rather than stacked.

The animation starts on its own when the page opens. The toolbar above the matrix gives you:

- **Play** / **Pause** — run or stop the animation. Pressing **Play** at the last stage replays from the beginning.
- **Stage buttons** — **Inherent Risk**, **Current risk** and **Residual risk**, in that order. Click one to jump straight to it. The **Inherent Risk** stage only appears when the **Inherent Risk** feature flag is on; otherwise the replay goes from current to residual.
- **Speed** — a slider from 0.25× to 2×.
- **A counter** — after the first stage, it reads _"x/y scenarios moved"_ for the step just played. If some scenarios got worse, it adds _"n worsened"_ in red.

While dots move, a faint dashed line traces their path from the previous stage. A scenario whose risk level goes **up** from one stage to the next gets a pulsing red ring, so regressions stand out.

Hover a dot to see its full path: a solid line through every earlier stage, with a small marker at each previous position. Click a dot to open the risk scenario.

### Projection

Switch from **Stages** to **Projection** with the toggle at the left of the toolbar. The matrix now shows each scenario either at its current or at its residual position, depending on the date you are looking at.

Above the matrix, a timeline runs from today to the latest planned ETA (and covers at least 30 days):

- The selected date is shown in large type, with _Today_ beside it when you are on today's date.
- Drag the slider to move through time, or press **Play** to sweep through the whole window.
- Each date on which one or more extra controls are due appears as a marker under the slider. Hover a marker to see the date, the controls due that day and the scenarios waiting on them; those scenarios are highlighted on the matrix and the others are dimmed. Click a marker to jump to that date.

The toolbar counter switches to _"x/y scenarios at residual risk"_ for the selected date.

### Projected risk levels

Below the matrix, the **Projected risk levels** chart is a stacked step chart of how many scenarios sit at each risk level, from today to the end of the window. It uses the colours of your matrix's risk levels and steps down each time a scenario reaches residual. A dashed vertical line follows the selected date. Click anywhere on the chart to jump the projection to that date.

### Overdue and No ETA

When some scenarios can't be projected, two lists appear under the chart:

- **Overdue** — extra controls whose ETA is already past and that are not yet active.
- **No ETA** — extra controls that are not yet active and have no ETA.

Each entry names the control and the scenarios it holds back. On the matrix, a scenario blocked by an overdue control has an amber ring; one blocked by a control without an ETA has a dashed outline.

## How the projection is computed

The projection only looks at each scenario's **extra controls** (the planned controls you expect to bring the scenario down to its residual risk), and at two fields on each of them: its status and its ETA. Existing controls don't move anything.

For every scenario:

- **No extra controls** — the scenario stays at its current risk for the whole timeline.
- **All extra controls active** — the scenario is already at residual risk, from today.
- **At least one extra control overdue** — the scenario stays at current risk for the whole timeline and is flagged _Overdue_. A missed deadline gives no date to project from, so the projection does not guess one.
- **At least one extra control without an ETA** (and none overdue) — the scenario stays at current risk and is listed under _No ETA_.
- **Otherwise** — the scenario moves to residual risk on the **latest** ETA among its extra controls that are not yet active. Risk drops only when the last planned control is due, not gradually as each one lands.

A control shared by several scenarios counts for each of them. On the timeline it appears once, on its ETA, with every scenario that depends on it. The scenario still waits for its own latest control, so a shared control due early does not move a scenario that also depends on a later one.

A scenario with no residual rating stays at its current level in the chart. On the matrix, a stage that hasn't been rated keeps the dot in its previous position; a dot only appears once its first stage is rated.

The projection reads statuses and ETAs as they are now. It doesn't change the assessment: to make the residual state the new current state once the controls are in place, use [sync to actions](sync-to-actions.md).

## Getting meaningful results

- **Rate every stage.** Give each scenario a probability and an impact for current and residual risk, and for inherent risk if you use it. A scenario rated only on current risk won't move.
- **Use a complete risk matrix.** If the matrix is still a draft without probability, impact and risk levels, the page shows a warning instead of the matrix.
- **Attach planned work as extra controls.** The projection follows the scenario's extra controls, not its existing ones. The **Projection** toggle only appears when the assessment has applied controls linked to it.
- **Give every extra control an ETA, and keep it up to date.** Without an ETA a scenario can't be placed on the timeline; with a past ETA it is held back as overdue until you set a new date or the control becomes **Active**.
- **Mark finished work as Active.** Active is the only status the projection treats as done.

If the controls can't be loaded, the **Projection** toggle is disabled and the page shows _"Extra controls could not be loaded, projection unavailable"_. The **Stages** mode still works.

## Related

- [Risk assessments](../concepts/risk-assessments.md) — inherent, current and residual risk.
- [Risk matrices](../concepts/risk-matrices.md) — the grid the scenarios move on.
- [Applied controls](../concepts/applied-controls.md) — status and ETA, the two fields the projection reads.
- [Action plans](action-plans.md) — the list of controls behind the assessment, sorted by ETA.
- [Sync to actions](sync-to-actions.md) — promote completed extra controls and make residual the new current risk.
- [Feature flags](../configuration/settings/feature-flags.md) — turn on the **Inherent Risk** stage.
