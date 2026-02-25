# Notification System

This document describes the email notification system in CISO Assistant, powered by **Huey** (async task queue) and **Django's email backend**.

## Architecture Overview

```
Event Trigger (serializer / periodic cron)
        |
        v
  Huey Task Queue  (@task / @db_periodic_task)
        |
        v
  Huey Worker Process  (run_huey -w 2 -k process)
        |
        v
  check_email_configuration()
  - notifications_enable_mailing enabled?
  - EMAIL_HOST / EMAIL_PORT / DEFAULT_FROM_EMAIL set?
  - Recipient email present?
        |
        v
  Email Template Rendering (YAML + string.Template)
        |
        v
  django.core.mail.send_mail()
  - Primary server -> Rescue server (fallback)
```

There is **no notification model** in the database. Notifications are fire-and-forget emails. Frontend toast notifications are independent and handled client-side only.

---

## Configuration

### Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `EMAIL_HOST` | Yes | SMTP server hostname |
| `EMAIL_PORT` | Yes | SMTP server port |
| `EMAIL_HOST_USER` | No | SMTP username |
| `EMAIL_HOST_PASSWORD` | No | SMTP password |
| `EMAIL_USE_TLS` | No | Enable TLS (`true`/`false`, default `false`) |
| `DEFAULT_FROM_EMAIL` | Yes | Sender address (fallback: `noreply@ciso.assistant`) |
| `EMAIL_HOST_RESCUE` | No | Fallback SMTP server |
| `EMAIL_PORT_RESCUE` | No | Fallback SMTP port |
| `EMAIL_HOST_USER_RESCUE` | No | Fallback SMTP username |
| `EMAIL_HOST_PASSWORD_RESCUE` | No | Fallback SMTP password |
| `EMAIL_USE_TLS_RESCUE` | No | Fallback TLS setting |

Source: `backend/ciso_assistant/settings.py` (lines 258-275)

### Global Setting (UI toggle)

The master switch is `notifications_enable_mailing` in the `GlobalSettings` model (`name="general"`). It must be set to `true` in **Extra > Settings** for any notification email to be sent.

Checked by `check_email_configuration()` in `backend/core/tasks.py:330`.

### Huey Configuration

```python
# backend/ciso_assistant/settings.py:529
HUEY = {
    "huey_class": "huey.SqliteHuey",
    "name": "ciso_assistant",
    "utc": True,
    "filename": HUEY_FILE_PATH,  # default: db/huey.db
    "results": True,
    "immediate": False,
}
```

Worker command: `poetry run python manage.py run_huey -w 2 -k process`

---

## Key Files

| File | Role |
|------|------|
| `backend/core/tasks.py` | All Huey tasks: periodic crons + async notification senders |
| `backend/core/email_utils.py` | Template loading, rendering, formatting helpers |
| `backend/core/serializers.py` | Where assignment notifications are triggered (in serializer `create`/`update`) |
| `backend/iam/models.py` | `User.mailing()` for password reset / welcome emails |
| `backend/iam/views.py` | `PasswordResetView` triggers password reset email |
| `backend/ciso_assistant/settings.py` | Email + Huey configuration |
| `backend/global_settings/models.py` | `GlobalSettings` stores `notifications_enable_mailing` |
| `backend/core/templates/emails/en/` | English YAML email templates |
| `backend/core/templates/emails/fr/` | French YAML email templates |
| `backend/core/templates/registration/` | HTML templates for password reset / welcome emails |

---

## Email Template System

### Location

Templates are YAML files under `backend/core/templates/emails/{locale}/`.

### Format

```yaml
subject: "CISO Assistant: You have been assigned to '${control_name}'"
body: |
  Hello,

  You have been assigned to the following Control:

  - Name: ${control_name}
  - Description: ${control_description}
  - Reference ID: ${control_ref_id}

  Log in to your CISO Assistant portal:
  ${ciso_assistant_url}

  Thank you.
```

### Variable Substitution

Uses Python's `string.Template.safe_substitute()`. Variables use `${variable_name}` syntax.

The `ciso_assistant_url` variable is always injected via `get_default_context()` in `email_utils.py`.

### Locale Fallback

1. Detect current Django language (via `get_language()`)
2. Extract base language code (`en-us` -> `en`)
3. Look for `templates/emails/{locale}/{template_name}.yaml`
4. If not found, fall back to `templates/emails/en/{template_name}.yaml`

### How to Add a New Template

1. Create `backend/core/templates/emails/en/{template_name}.yaml` with `subject` and `body` keys
2. Create `backend/core/templates/emails/fr/{template_name}.yaml` (French translation)
3. Use `${variable_name}` for dynamic content
4. `${ciso_assistant_url}` is automatically available

---

## Existing Notifications

### 1. Periodic Notifications (Scheduled Cron Tasks)

These run daily as `@db_periodic_task` Huey tasks. They query the database, group results by recipient, and send personalized emails.

| Task | Schedule | Condition | Recipients | Template |
|------|----------|-----------|------------|----------|
| `check_controls_with_expired_eta` | 06:00 | AppliedControl ETA < today, status not `active`/`deprecated` | Control owners | `expired_controls` |
| `check_compliance_assessments_due_in_month` | 06:05 | ComplianceAssessment due_date = today + 30d, status not `done`/`deprecated` | Assessment authors | `compliance_assessment_due_soon` |
| `check_compliance_assessments_due_in_week` | 06:10 | ComplianceAssessment due_date = today + 7d, status not `done`/`deprecated` | Assessment authors | `compliance_assessment_due_soon` |
| `check_compliance_assessments_due_tomorrow` | 06:15 | ComplianceAssessment due_date = today + 1d, status not `done`/`deprecated` | Assessment authors | `compliance_assessment_due_soon` |
| `check_applied_controls_expiring_in_month` | 06:17 | AppliedControl expiry_date = today + 30d, status not `deprecated` | Control owners | `applied_control_expiring_soon` |
| `check_applied_controls_expiring_in_week` | 06:20 | AppliedControl expiry_date = today + 7d, status not `deprecated` | Control owners | `applied_control_expiring_soon` |
| `check_applied_controls_expiring_tomorrow` | 06:25 | AppliedControl expiry_date = today + 1d, status not `deprecated` | Control owners | `applied_control_expiring_soon` |
| `check_evidences_expiring_in_month` | 06:27 | Evidence expiry_date = today + 30d, status not `expired` | Evidence owners | `evidence_expiring_soon` |
| `check_evidences_expiring_in_week` | 06:30 | Evidence expiry_date = today + 7d, status not `expired` | Evidence owners | `evidence_expiring_soon` |
| `check_evidences_expiring_tomorrow` | 06:35 | Evidence expiry_date = today + 1d, status not `expired` | Evidence owners | `evidence_expiring_soon` |
| `check_evidences_expired` | 06:40 | Evidence expiry_date < today | Evidence owners | `expired_evidences` |
| `check_validation_flows_deadline_in_month` | 06:37 | ValidationFlow deadline = today + 30d, status = `submitted` | Approvers | `validation_deadline` |
| `check_validation_flows_deadline_in_week` | 06:40 | ValidationFlow deadline = today + 7d, status = `submitted` | Approvers | `validation_deadline` |
| `check_validation_flows_deadline_tomorrow` | 06:45 | ValidationFlow deadline = today + 1d, status = `submitted` | Approvers | `validation_deadline` |
| `check_task_nodes_due_in_month` | 06:55 | TaskNode due_date = today + 30d, status `pending`/`in_progress`, template enabled. Skipped for recurrent tasks with interval < 30 days | Assigned actors | `task_node_due_soon` |
| `check_task_nodes_due_in_week` | 07:00 | TaskNode due_date = today + 7d, status `pending`/`in_progress`, template enabled. Skipped for recurrent tasks with interval < 7 days | Assigned actors | `task_node_due_soon` |
| `check_task_nodes_due_tomorrow` | 07:05 | TaskNode due_date = today + 1d, status `pending`/`in_progress`, template enabled | Assigned actors | `task_node_due_soon` |
| `check_task_nodes_overdue` | 07:10 | TaskNode due_date < today, status `pending`, template enabled | Assigned actors | `task_node_overdue` |

### 2. Assignment Notifications (Event-Triggered)

These are triggered from serializer `create()` / `update()` methods when users are newly assigned. They use the `@task()` decorator (async, not periodic).

| Event | Trigger Location | Task Function | Template |
|-------|-----------------|---------------|----------|
| AppliedControl owner assigned | `AppliedControlWriteSerializer.create/update` | `send_applied_control_assignment_notification` | `applied_control_assignment` |
| ComplianceAssessment author assigned | `ComplianceAssessmentWriteSerializer.create/update` | `send_compliance_assessment_assignment_notification` | `compliance_assessment_assignment` |
| TaskTemplate assigned_to set | `TaskTemplateWriteSerializer.create/update` | `send_task_template_assignment_notification` | `task_template_assignment` |
| ValidationFlow created | `ValidationFlowWriteSerializer.create` | `send_validation_flow_created_notification` | `validation_flow_created` |
| ValidationFlow status changed | `ValidationFlowWriteSerializer.update` | `send_validation_flow_updated_notification` | `validation_flow_updated` |

**Pattern for assignment notifications in serializers:**

```python
# In create():
instance = super().create(validated_data)
if newly_assigned_data:
    self._send_assignment_notifications(instance, [a.id for a in newly_assigned_data])

# In update():
old_ids = set(instance.field.values_list("id", flat=True))
updated = super().update(instance, validated_data)
new_ids = set(updated.field.values_list("id", flat=True))
newly_assigned = new_ids - old_ids
if newly_assigned:
    self._send_assignment_notifications(updated, list(newly_assigned))

# Helper:
def _send_assignment_notifications(self, obj, actor_ids):
    actors = Actor.objects.filter(id__in=actor_ids)
    emails = []
    for actor in actors:
        emails.extend(actor.get_emails())
    if emails:
        send_xxx_assignment_notification(obj.id, emails)
```

Note: `ComplianceAssessmentWriteSerializer.update` uses `transaction.on_commit()` to defer notification until the DB transaction is committed.

### 3. Password Reset / Welcome Emails

These use a separate mechanism (`User.mailing()` in `backend/iam/models.py`) with Django HTML templates instead of YAML.

| Event | Template | Triggered By |
|-------|----------|-------------|
| Password reset | `registration/password_reset_email.html` | `PasswordResetView.post()` |
| User creation (welcome) | `registration/first_connexion_email.html` | `User.save()` / management command `welcome_mail` |
| User creation (SSO) | `registration/first_connexion_email_sso.html` | SSO user provisioning |

These emails support the **rescue (fallback) email server**. Notification emails (from `tasks.py`) currently use only the primary server.

### 4. Non-Notification Periodic Tasks

These tasks perform automated actions without sending emails:

| Task | Schedule | Action |
|------|----------|--------|
| `lock_overdue_compliance_assessments` | 02:30 | Lock overdue assessments (with campaign/entity), set status to `in_review` |
| `deactivate_expired_users` | 03:00 | Deactivate users past `expiry_date` (except superusers) |
| `mark_expired_evidences` | 03:35 | Set evidence status to `expired` |
| `check_expired_organisation_issues` | 06:50 | Set expired OrganisationIssue status to `inactive` |
| `auditlog_retention_cleanup` | 22:30 | Flush old audit log entries |
| `auditlog_prune` | Every 3h | Prune audit log |

---

## Actor Email Resolution

Notifications are sent to **Actors**, which can represent a User, Team, or Entity. The `Actor.get_emails()` method delegates to the underlying type:

- **User**: returns `[user.email]`
- **Team**: returns deduplicated list of `team_email` + leader email + deputy emails + member emails
- **Entity**: returns entity contact emails (via TPRM)

This means assigning a Team as owner of a control can notify multiple people in a single assignment.

---

## Email Templates Inventory

### English (`en/`)

| Template File | Used By |
|--------------|---------|
| `expired_controls.yaml` | `send_notification_email_expired_eta` |
| `applied_control_assignment.yaml` | `send_applied_control_assignment_notification` |
| `applied_control_expiring_soon.yaml` | `send_applied_control_expiring_soon_notification` |
| `compliance_assessment_assignment.yaml` | `send_compliance_assessment_assignment_notification` |
| `compliance_assessment_due_soon.yaml` | `send_compliance_assessment_due_soon_notification` |
| `evidence_expiring_soon.yaml` | `send_evidence_expiring_soon_notification` |
| `expired_evidences.yaml` | `send_notification_email_expired_evidence` |
| `task_template_assignment.yaml` | `send_task_template_assignment_notification` |
| `validation_flow_created.yaml` | `send_validation_flow_created_notification` |
| `validation_flow_updated.yaml` | `send_validation_flow_updated_notification` |
| `validation_deadline.yaml` | `send_validation_deadline_notification` (parametric, uses `${days}`) |
| `task_node_due_soon.yaml` | `send_task_node_due_soon_notification` |
| `task_node_overdue.yaml` | `send_task_node_overdue_notification` |

### French (`fr/`)

All English templates have a matching French translation. Both directories contain 13 templates.

---

## How to Add a New Notification

### Step-by-step: Event-triggered notification

1. **Create email templates**:
   - `backend/core/templates/emails/en/{template_name}.yaml`
   - `backend/core/templates/emails/fr/{template_name}.yaml`

2. **Add a Huey task** in `backend/core/tasks.py`:
   ```python
   @task()
   def send_my_new_notification(object_id, recipient_emails):
       if not recipient_emails:
           return

       obj = MyModel.objects.get(id=object_id)

       from .email_utils import render_email_template

       context = {
           "name": obj.name,
           "description": obj.description or "No description provided",
           # ... other fields
       }

       for email in recipient_emails:
           if email and check_email_configuration(email, [obj]):
               rendered = render_email_template("my_template_name", context)
               if rendered:
                   send_notification_email(rendered["subject"], rendered["body"], email)
   ```

3. **Trigger from serializer** (in `backend/core/serializers.py`):
   ```python
   def _send_assignment_notifications(self, instance, actor_ids):
       if not actor_ids:
           return
       try:
           from core.models import Actor
           from .tasks import send_my_new_notification

           actors = Actor.objects.filter(id__in=actor_ids)
           emails = []
           for actor in actors:
               emails.extend(actor.get_emails())
           if emails:
               send_my_new_notification(instance.id, emails)
       except Exception as e:
           logger.error(f"Failed to send notification: {str(e)}")
   ```

4. Call `_send_assignment_notifications` from `create()` and/or `update()`, passing only **newly assigned** actor IDs.

### Step-by-step: Periodic notification

1. **Create email templates** (same as above).

2. **Add a periodic task** in `backend/core/tasks.py`:
   ```python
   @db_periodic_task(crontab(hour="6", minute="55"))
   def check_my_condition():
       items = MyModel.objects.filter(...)  # query condition
       .prefetch_related("owner")  # or relevant M2M

       # Group by recipient
       owner_items = defaultdict(list)
       for item in items:
           for owner in item.owner.all():
               for email in owner.get_emails():
                   owner_items[email].append(item)

       for owner_email, items in owner_items.items():
           send_my_periodic_notification(owner_email, items)
   ```

3. **Add the sender task** (same pattern as event-triggered, with `@task()` decorator).

### Important Patterns

- Always use `@task()` for the actual email sending (async)
- Always call `check_email_configuration()` before rendering/sending
- Use `defaultdict(list)` to group by recipient for batch notifications
- For `update()` in serializers, only notify **newly assigned** actors (diff old vs new IDs)
- For serializers with transactions, use `transaction.on_commit()` to defer notification
- Pass object IDs (not objects) to `@task()` functions to avoid serialization issues (except `send_validation_flow_created_notification` which passes the object directly - this works but is fragile)

---

## Known Issues and Inconsistencies

1. **`check_email_configuration` is a `@task()`**: This function is decorated as a Huey task but is called synchronously within other tasks. The `@task()` decorator means calling it returns a `Result` object, not a boolean. However, Huey's behavior in "immediate" mode or when called from within another task may vary. This could be a source of bugs.

2. **Daily re-notification for expired evidences and overdue tasks**: `check_evidences_expired` and `check_task_nodes_overdue` run daily and re-notify owners every day. There's no "already notified" tracking.

---

## Suggestions for Extensions

### High Value

1. **Risk scenario notifications**: Notify risk owners when risk scenarios change status or when risk levels exceed thresholds. Add to `RiskScenarioWriteSerializer`.

2. **Requirement assessment status change**: Notify assigned actors when a requirement assessment result changes (e.g., from `non_compliant` to `partially_compliant`). Useful for audit workflows.

3. **Incident notifications**: When a new incident is created or its severity changes, notify relevant stakeholders. The `Incident` model has owners who should be alerted.

4. **Compliance assessment status transitions**: Notify authors when an assessment moves to `in_review` or `done` status, especially when auto-locked by `lock_overdue_compliance_assessments`.

### Medium Value

5. **In-app notification center**: Add a `Notification` model to store notifications in the database, with a frontend notification bell/inbox. This would complement emails and work when email is not configured.

6. **Digest emails**: Instead of individual emails per event, offer a daily/weekly digest option that aggregates all pending notifications into a single email per user.

7. **Notification preferences per user**: Allow users to opt in/out of specific notification categories (assignments, deadlines, status changes) via their profile settings.

8. **Entity/TPRM notifications**: Notify entity contacts when an entity assessment is created or its compliance assessment is due. Relevant for third-party risk management workflows.

### Low Effort / Quick Wins

9. **Add "already notified" tracking**: For daily periodic tasks like `check_evidences_expired` and `check_task_nodes_overdue`, add a flag or timestamp to avoid re-notifying every day for the same items.

10. **Additional locales**: The template system supports any locale. Add templates for other supported languages (e.g., `de/`, `es/`, `pt/`, `ar/`) as the user base grows.
