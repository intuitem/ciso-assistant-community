---
description: >-
  Keep track of assignments, approvals and deadlines through the in-app
  notification inbox and, optionally, email.
---

# Notifications

CISO Assistant tells you when something needs your attention: a control is assigned to you, an audit assignment awaits your review, a piece of evidence is about to expire. These notifications reach you through two independent channels:

- **The in-app inbox** — on by default, nothing to configure. A bell in the top bar shows how many unread notifications you have.
- **Email** — off by default. An administrator has to enable it and the instance needs an outgoing mail server.

The same events feed both channels, but neither depends on the other: the inbox works whether or not email is enabled.

## The notification inbox

### Where to find it

- **The bell** in the top bar opens the inbox. A red badge shows your unread count (shown as **99+** beyond 99). The count refreshes every minute, when you move between pages, and when you come back to the browser tab.
- **The sidebar**, under **Overview** → **Notifications**.

Third-party users don't get an inbox: the bell and the sidebar entry are hidden for them, and they keep receiving email only.

### Reading the inbox

The inbox is a table, newest first, with these columns:

- **Read** — whether you've already dealt with it. Unread rows are emphasised.
- **Category** — **Assignments**, **Approvals**, **Deadlines** or **Updates** (see below).
- **Title** — what happened, for example _You have been assigned to control 'MFA rollout'_ or _Evidence 'Pentest report' expires in 7 day(s)_. Titles are displayed in your own language, whatever language the person who triggered the event uses.
- **Created at**.

Two optional columns, **Domain** (the domain of the object the notification is about) and **Read at**, can be added from the column picker.

When other people received the same notification, a small group badge next to the title shows how many people were notified in total; hover it to read _N other people were notified_. It's a quick way to tell whether something is on you alone or shared with colleagues.

### Opening, reading and clearing

- **Click a row** to open the object it's about. The notification is marked as read at the same time. If the object has been deleted since, the notification is still marked as read.
- **Right-click a row** for **Mark as read** or **Mark as unread**.
- **Tick several rows** to get the batch bar with **Mark as read**, **Mark as unread** and **Delete**. The header checkbox selects the whole page (50 notifications), so to clear a backlog, filter on unread and mark each page as read.

Marking as read and deleting only ever affects your own inbox — other recipients of the same notification keep theirs.

### Filters

Narrow the inbox with:

- **Read** — **Yes** / **No**.
- **Category**.
- **Recipients** — **Shared with others** or **Only you**.
- **Domain** — the domain of the object the notification is about.
- **Created at** and **Read at** date ranges.

### What generates a notification

| Category | Notification | Who receives it |
| --- | --- | --- |
| **Assignments** | You're added as owner of an applied control, owner of a risk scenario, owner of a security exception, author of an audit, or assignee of a task | The person added |
| **Assignments** | An audit assignment is activated, or reopened for editing | The assignee |
| **Assignments** | A quick form response is ready for your input, or was sent back to you | The respondents |
| **Approvals** | An audit assignment is submitted for review | The reviewers (the audit's authors if none are set) |
| **Approvals** | A quick form response is submitted | The reviewers |
| **Approvals** | A validation flow is created and needs your approval | The approver |
| **Updates** | An audit assignment is reviewed (approved, reopened for review, or changes requested) | The assignee |
| **Updates** | A security exception or a validation flow changes status | Exception owners and approver; validation-flow requester or approver depending on the transition |
| **Deadlines** | An applied control, evidence or security exception is expiring; an audit, task or validation flow is due | Owners, authors, assignees or approver — see [Email notifications](#email-notifications) for the details per object |
| **Deadlines** | An applied control's ETA has passed, an evidence or security exception has expired, a task is overdue | Owners or assignees |

When an object is assigned to a **team**, every member, leader and deputy who has a user account gets their own notification.

Account messages (welcome, password reset) and third-party questionnaire invitations are email only; they never appear in the inbox.

### How deadline notifications behave

Deadline notifications are checked every morning and reflect the current state of the object, rather than piling up:

- An **expiring or due** item appears in your inbox as soon as it's within 30 days of its date, and stays there while it remains in that window. Its title keeps the number of remaining days up to date.
- If you've marked it as read, it stays read — except **30, 7 and 1 day** before the date, when it comes back as unread. Those are the same days the reminder email goes out.
- An **overdue or expired** item stays in your inbox until it's resolved, without being reopened every day once you've read it.
- As soon as the condition no longer holds — the task is done, the evidence is renewed, the date has moved — the notification disappears on the next morning's check. If the situation happens again later, you get a fresh unread notification.

Event notifications (assignments, approvals, updates) work differently: there's one notification per object and event type, and if the same event happens again — you're reassigned to the same control, say — the existing notification is marked unread again instead of being duplicated.

### Who can see what

You only ever see notifications addressed to you. Access to the inbox doesn't depend on your roles or domains: you see your notifications even about an object in a domain where you hold no role, and an administrator can't browse other users' inboxes. Notifications are created by the platform only — nobody can send one on your behalf.

### Retention

A nightly clean-up keeps the inbox manageable:

- Notifications you've **read** are removed **90 days** after they were last updated.
- Notifications about an object that has since been **deleted** are removed.
- Each inbox is capped at **1,000** notifications. Beyond that, the oldest read notifications go first.

## Email notifications

#### Prerequisites

Email notifications must be enabled by your administrator under **Extra > Settings > General > Notifications settings > Enable email notifications**. This setting is **off by default** on a fresh install, no notification emails are sent until an administrator enables it.

{% hint style="warning" %}
## Onprem instances only

Your CISO Assistant instance also needs an outgoing mail server configured (`EMAIL_HOST`, `EMAIL_PORT`, and `DEFAULT_FROM_EMAIL` at minimum). If you are not receiving emails, contact your administrator to verify these are set.
{% endhint %}

Notifications are sent to the email address associated with your account.

Administrators can also turn each email type on or off individually — see [Choosing channels per notification type](#choosing-channels-per-notification-type). All emails are on by default.

***

#### Notification types

**Assignments**

You receive an email whenever something is assigned to you.

| Object                    | Field to fill   | Your role                    |
| ------------------------- | --------------- | ---------------------------- |
| **Applied Control**       | **Owner**       | You are added as an owner    |
| **Audit** | **Authors**     | You are added as an author   |
| **Risk Scenario**         | **Owner**       | You are added as an owner    |
| **Task (template)**       | **Assigned to** | You are added as an assignee |
| **Security Exception**    | **Owner**       | You are added as an owner    |

> **Note:** Task assignment notifications fire when a **task template** is assigned. Due-date reminders (below) fire on the **task occurrences** generated from that template.

***

**Deadlines & Expiry reminders**

CISO Assistant sends reminders automatically **30 days**, **7 days**, and **1 day** before a deadline or expiry date. These emails are sent every morning.

**For reminders to fire, both fields below must be filled in.**

**Applied Control**

| Notification       | Required field                          | Who receives it |
| ------------------ | --------------------------------------- | --------------- |
| ETA expired        | **ETA** (past due, status not _Active_) | **Owner**       |
| Expiry approaching | **Expiry date**                         | **Owner**       |

**Audit**

| Notification         | Required field | Who receives it |
| -------------------- | -------------- | --------------- |
| Due date approaching | **Due date**   | **Authors**     |

**Evidence**

| Notification       | Required field  | Who receives it |
| ------------------ | --------------- | --------------- |
| Expiry approaching | **Expiry date** | **Owner**       |

**Security Exception**

| Notification       | Required field      | Who receives it |
| ------------------ | ------------------- | --------------- |
| Expiry approaching | **Expiration date** | **Owners**      |

**Validation Flow**

| Notification                                          | Required field          | Who receives it |
| ----------------------------------------------------- | ----------------------- | --------------- |
| Deadline approaching (flow in _submitted_ state only) | **Validation deadline** | **Approver**    |

**Task**

| Notification         | Required field | Who receives it |
| -------------------- | -------------- | --------------- |
| Due date approaching | **Due date**   | **Assigned to** |

> **Note for recurring tasks**: reminders are automatically skipped if the recurrence interval is shorter than the reminder horizon (e.g., a daily task will not receive a 7-day warning).

***

**Overdue alerts**

If a deadline has already passed and the item is still open, you will receive an overdue alert.

| Object                            | Required field                 | Alert sent to |
| --------------------------------- | ------------------------------ | ------------- |
| **Applied Control** — ETA expired | **ETA** + **Owner**            | Owners        |
| **Evidence** — expired            | **Expiry date** + **Owner**    | Owners        |
| **Task** — past due               | **Due date** + **Assigned to** | Assignees     |
| **Security Exception** — expired  | **Expiration date** + **Owner** | Owners        |

***

**Compliance assignment workflow**

When working on a **Requirement Assignment** inside an audit, notifications follow the review workflow automatically — no extra fields to fill.

| Event                                                         | Who is notified                                       |
| ------------------------------------------------------------- | ----------------------------------------------------- |
| Assignment activated (_Draft → In progress_)                  | Assignee                                              |
| Assignment submitted for review                               | Reviewers (falls back to authors if none are defined) |
| Assignment reviewed (approved / reopened for review / changes requested) | Assignee                                    |
| Assignment reopened for editing (sent back to _Draft_ from _In progress_ or _Changes requested_) | Assignee                          |

***

**Quick forms**

| Event                                     | Who is notified |
| ----------------------------------------- | --------------- |
| Response started (ready for input)        | Respondents     |
| Response submitted                        | Reviewers       |
| Submitted response sent back for changes  | Respondents     |

***

**Validation flows**

| Event                                 | Who is notified                                    |
| ------------------------------------- | -------------------------------------------------- |
| Validation flow created and submitted | Approver                                           |
| Validation flow status changes        | Requester or approver, depending on the transition |

***

**Security exceptions**

| Event                              | Who is notified         |
| ---------------------------------- | ----------------------- |
| Security exception status changes  | Owners                  |

***

**Account notifications**

| Event                    | Who is notified                             |
| ------------------------ | ------------------------------------------- |
| Account created          | You (welcome email with login instructions) |
| Account created via SSO  | You (welcome email)                         |
| Password reset requested | You (reset link)                            |

***

**Third-party questionnaires (TPRM)**

If your organisation uses the Third-Party Risk Management module, external contacts receive an email when a questionnaire is sent to them. This email contains a link to fill in the questionnaire.

***

#### Quick reference — what to fill in

| If you want this notification…               | Fill in these fields                                     |
| -------------------------------------------- | -------------------------------------------------------- |
| Remind owners when a control ETA expires     | **Applied Control › Owner** + **ETA**                    |
| Remind owners before a control expires       | **Applied Control › Owner** + **Expiry date**            |
| Remind authors before an assessment deadline | **Audit › Authors** + **Due date**       |
| Remind owners before evidence expires        | **Evidence › Owner** + **Expiry date**                   |
| Alert owners when evidence has expired       | **Evidence › Owner** + **Expiry date**                   |
| Remind an approver of a validation deadline  | **Validation Flow › Approver** + **Validation deadline** |
| Notify assignees of upcoming task due dates  | **Task › Assigned to** + **Due date**                    |
| Remind owners before a security exception expires | **Security Exception › Owner** + **Expiration date** |
| Alert owners when a security exception has expired | **Security Exception › Owner** + **Expiration date** |

The same fields drive the matching notifications in the in-app inbox.

## Administration

### Turning the inbox on or off

The inbox is controlled by the `notification_center` feature flag, listed as **Notifications** in the **Extra** group under **Extra > Settings > Feature flags**. It's **on by default**, in every edition.

Turning it off hides the bell, the **Notifications** sidebar entry and the **Notifications** settings tab, and stops new inbox notifications from being created. Notifications already in users' inboxes are kept. Email is not affected.

### Choosing channels per notification type

Under **Extra > Settings > Notifications**, administrators see every notification type grouped by category (**Assignments**, **Approvals**, **Deadlines**, **Updates**, **Account**), each with an **In-app** and an **Email** switch. Each category header shows how many types are on per channel, with **Enable all** and **Disable all** buttons.

- A switch is greyed out when the notification type doesn't support that channel — account emails and questionnaire invitations, for example, have no in-app version.
- The **Email** switch is the per-type on/off for emails, and only matters once **Enable email notifications** is on. On the PRO edition, **Extra > Settings > Templates** lets you change the wording of each email; whether it's sent is decided here.
- Disabling an **Account** email (welcome, password reset) blocks the sign-in flow it carries.

This tab is only shown while the inbox feature flag is on.

{% hint style="info" %}
There are no per-user preferences yet: the channel settings apply to every user on the instance.
{% endhint %}

## Frequently asked questions

**I am not receiving any emails. What should I check?** First confirm that email notifications are enabled with your administrator (the global toggle is off by default). Then ask the administrator to verify that `EMAIL_HOST`, `EMAIL_PORT`, and `DEFAULT_FROM_EMAIL` are set, and that the email type you expect is switched on under **Extra > Settings > Notifications**. Verify that your account email address is correct in your profile. Finally, check your spam folder.

**My inbox is empty but I expected a notification. Why?** Check that you're named on the object directly or through a team, and that the relevant date is filled in. Deadline notifications only appear after the next morning's check. Also ask your administrator whether the type's **In-app** switch is on.

**I filled in the fields but still got no email. Why?** Check that the field contains an exact date — reminders are sent only on specific days (30, 7, and 1 day before). If the deadline is sooner than 30 days from when you set it, the 30-day reminder will not fire.

**I am receiving too many reminders. Can I opt out?** Per-user opt-out is not yet available. An administrator can disable a specific notification type, per channel, for the whole instance under **Extra > Settings > Notifications**. In the inbox, marking a deadline notification as read keeps it quiet until the next 30-, 7- or 1-day mark.

**At what time are reminders sent?** Reminders are sent in the early morning (between 6:00 AM and 7:30 AM server time). Account, password-reset, validation-flow, and security-exception status-change event emails are sent immediately when the event occurs, not in this window.

**Will I get a reminder every day until the deadline?** No. Reminders are sent only on specific days: 30 days before, 7 days before, and 1 day before the deadline. Overdue alerts are sent daily until the item is resolved.

## Related

- [My assignments](my-assignments.md) — everything currently on your plate, in one dashboard.
- [Working with tables](working-with-tables.md) — filters, context menu and batch actions, as used by the inbox.
- [Actors and teams](../concepts/actors-and-teams.md) — how a team assignment reaches its members.
- [Feature flags](../configuration/settings/feature-flags.md) — turning modules on and off.
- [General settings](../configuration/settings/general.md) — the **Enable email notifications** switch.
- [Setting up mailer](../installation/mailer.md) — configuring outgoing email.
