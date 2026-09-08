---
description: Overview of the requirements dispatch mode
---

# Assignments / respondent mode

This feature is intended for organisations who wish to rely on a single audit where multiple users or teams will collaborate by responding to their specific sections (one or multiple requirements).

The feature flag can be enabled from Extra/Settings/Feature flags:

<figure><img src="../.gitbook/assets/image (80).png" alt=""><figcaption></figcaption></figure>

Once the feature flag is enabled, the design is as follows:

* an analyst (or higher role) starts an audit
* through the assignment management, we assign a group of requirements to one or multiple users or teams
* the assignments can be made to a user or a team, over one or multiple requirements\
  \
  ![](<../.gitbook/assets/image (1).png>)

<figure><img src="../.gitbook/assets/image (2) (1).png" alt=""><figcaption></figcaption></figure>

* the assignees need just the `respondent` role on the domain to interact with their assigned sections, and they can do that directly from the respondent view

<figure><img src="../.gitbook/assets/image (1) (1).png" alt=""><figcaption></figcaption></figure>

* when `respondent` users sign it, they get automatically redirected to the dedicated page. Users can find it later on the side nav bar

<figure><img src="../.gitbook/assets/image (3) (1).png" alt=""><figcaption></figcaption></figure>

* Users will see their assigned sections of all the audits organised by domains and they can interact with it by answering the compliance status, attaching applied controls or evidences directly.
* Keep in mind that `respondent` can create, pick or update applied controls or evidences of the domains, to encourage reusability.

<figure><img src="../.gitbook/assets/image (79).png" alt=""><figcaption></figcaption></figure>



### Workflow

The intereaction between the auditor and respondents follows these steps:\
<br>

<figure><img src="../.gitbook/assets/image (1) (2).png" alt=""><figcaption></figcaption></figure>

The default state is `draft` and you can set them and send feedbacks individually:\
&#x20;&#x20;

<figure><img src="../.gitbook/assets/image (2).png" alt=""><figcaption></figcaption></figure>

An assignment moves through the following states:

* `draft`: being prepared. Actors and requirements can be edited, and the assignment can be deleted.
* `in_progress`: launched, the respondent is working on it.
* `submitted`: the respondent has handed the work back for review.
* `changes_requested`: the reviewer asked for corrections, the respondent is expected to resubmit.
* `closed`: reviewed and accepted.

Once an assignment leaves `draft`, its scope (assigned actors and requirements) is locked, so the agreement between the auditor and the respondent stays consistent while work is ongoing. Edit and delete are therefore only available in `draft`.

To change a locked assignment, a reviewer reopens it back to `draft` from any other state, which unlocks editing and reassignment. Respondents are notified by email of a reopening only when it comes from `in_progress` or `changes_requested`, the states where they were actively working; reopening a `submitted` or `closed` assignment stays silent.

### Reviewing item by item

The assignment status says where the round as a whole stands. Underneath it, each requirement carries its own **review state**, so a reviewer can be specific about what needs work instead of bouncing the whole assignment back with a note.

Reading the respondent's answers, a reviewer has two buttons on every requirement:

* **Request changes** — flags this item. The respondent sees a red banner on it pointing them at the comments for the detail.
* the check button (**Mark as accepted**) — records that this one is settled.

An item is therefore in one of four states: unreviewed, `changes_requested`, `resubmitted`, or `accepted`. The flags then follow the assignment's own transitions:

* When the respondent hands back a `changes_requested` assignment, everything flagged becomes **Resubmitted** — it's been answered and is waiting for another look.
* When the reviewer closes a `submitted` assignment, everything resubmitted becomes **Accepted**.
* Every other transition leaves the flags alone. Reopening an assignment does not clear them: an accepted item records a verdict that was actually given, and re-flagging it is the reviewer's call, not a side effect.

Sending an assignment back opens a dialog that says how many items are currently flagged, with a link to them — or tells you that none are, and that the respondent will only get the note you write. Flagging the items first is what turns "please fix this" into something actionable.

Progress through the review is shown as a **Review progress** bar alongside completion, and the flagged count is surfaced on the [campaign](campaigns.md) dashboard so a reviewer can see across a whole round which questionnaires are waiting on rework.

For review, if the auditors don't have the permissions to update the requirements compliance result, which will be the general case to keep consistent inputs from the respondent side, they can interact with comments on each one:\
<br>

<figure><img src="../.gitbook/assets/image (3).png" alt=""><figcaption></figcaption></figure>
