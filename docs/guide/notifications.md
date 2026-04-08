---
description: >-
  CISO Assistant can send you email notifications to keep you informed about
  deadlines, assignments, and status changes.
icon: bell
---

# Notifications

### Prerequisites

Email notifications must be enabled by your administrator under **Extra > Settings > Enable email notifications**. Your CISO Assistant instance also needs an outgoing mail server configured. If you are not receiving emails, contact your administrator.

Notifications are sent to the email address associated with your account.

***

### Notification types

#### Assignments

You receive an email whenever something is assigned to you.

| Object                    | Field to fill   | Your role                    |
| ------------------------- | --------------- | ---------------------------- |
| **Applied Control**       | **Owner**       | You are added as an owner    |
| **Compliance Assessment** | **Authors**     | You are added as an author   |
| **Risk Scenario**         | **Owner**       | You are added as an owner    |
| **Task**                  | **Assigned to** | You are added as an assignee |

***

#### Deadlines & Expiry reminders

CISO Assistant sends reminders automatically **30 days**, **7 days**, and **1 day** before a deadline or expiry date. These emails are sent every morning.

**For reminders to fire, both fields below must be filled in.**

**Applied Control**

| Notification       | Required field                          | Who receives it |
| ------------------ | --------------------------------------- | --------------- |
| ETA expired        | **ETA** (past due, status not _Active_) | **Owner**       |
| Expiry approaching | **Expiry date**                         | **Owner**       |

**Compliance Assessment**

| Notification         | Required field | Who receives it |
| -------------------- | -------------- | --------------- |
| Due date approaching | **Due date**   | **Authors**     |

**Evidence**

| Notification       | Required field  | Who receives it |
| ------------------ | --------------- | --------------- |
| Expiry approaching | **Expiry date** | **Owner**       |

**Validation Flow**

| Notification                              | Required field          | Who receives it |
| ----------------------------------------- | ----------------------- | --------------- |
| Deadline approaching (flow still pending) | **Validation deadline** | **Approver**    |

**Task**

| Notification         | Required field | Who receives it |
| -------------------- | -------------- | --------------- |
| Due date approaching | **Due date**   | **Assigned to** |

> **Note for recurring tasks**: reminders are automatically skipped if the recurrence interval is shorter than the reminder horizon (e.g., a daily task will not receive a 7-day warning).

***

#### Overdue alerts

If a deadline has already passed and the item is still open, you will receive an overdue alert.

| Object                            | Required field                 | Alert sent to |
| --------------------------------- | ------------------------------ | ------------- |
| **Applied Control** — ETA expired | **ETA** + **Owner**            | Owners        |
| **Evidence** — expired            | **Expiry date** + **Owner**    | Owners        |
| **Task** — past due               | **Due date** + **Assigned to** | Assignees     |

***

#### Compliance assignment workflow

When working on a **Requirement Assignment** inside a compliance assessment, notifications follow the review workflow automatically — no extra fields to fill.

| Event                                                         | Who is notified                                       |
| ------------------------------------------------------------- | ----------------------------------------------------- |
| Assignment activated (_Draft → In progress_)                  | Assignee                                              |
| Assignment submitted for review                               | Reviewers (falls back to authors if none are defined) |
| Assignment reviewed (approved / reopened / changes requested) | Assignee                                              |

***

#### Validation flows

| Event                                 | Who is notified                                    |
| ------------------------------------- | -------------------------------------------------- |
| Validation flow created and submitted | Approver                                           |
| Validation flow status changes        | Requester or approver, depending on the transition |

***

#### Account notifications

| Event                    | Who is notified                             |
| ------------------------ | ------------------------------------------- |
| Account created          | You (welcome email with login instructions) |
| Account created via SSO  | You (welcome email)                         |
| Password reset requested | You (reset link)                            |

***

#### Third-party questionnaires (TPRM)

If your organisation uses the Third-Party Risk Management module, external contacts receive an email when a questionnaire is sent to them. This email contains a link to fill in the questionnaire.

***

### Quick reference — what to fill in

| If you want this notification…               | Fill in these fields                                     |
| -------------------------------------------- | -------------------------------------------------------- |
| Remind owners when a control ETA expires     | **Applied Control › Owner** + **ETA**                    |
| Remind owners before a control expires       | **Applied Control › Owner** + **Expiry date**            |
| Remind authors before an assessment deadline | **Compliance Assessment › Authors** + **Due date**       |
| Remind owners before evidence expires        | **Evidence › Owner** + **Expiry date**                   |
| Remind an approver of a validation deadline  | **Validation Flow › Approver** + **Validation deadline** |
| Notify assignees of upcoming task due dates  | **Task › Assigned to** + **Due date**                    |

***

### Frequently asked questions

**I am not receiving any emails. What should I check?** First confirm that email notifications are enabled with your administrator. Then verify that your account email address is correct in your profile. Finally, check your spam folder.

**I filled in the fields but still got no email. Why?** Check that the field contains an exact date — reminders are sent only on specific days (30, 7, and 1 day before). If the deadline is sooner than 30 days from when you set it, the 30-day reminder will not fire.

**I am receiving too many reminders. Can I opt out?** Per-user opt-out is not yet available.

**At what time are reminders sent?** Reminders are sent in the early morning (between 6 AM and 7 AM server time).

**Will I get a reminder every day until the deadline?** No. Reminders are sent only on specific days: 30 days before, 7 days before, and 1 day before the deadline. Overdue alerts are sent daily until the item is resolved.
