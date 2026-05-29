---
description: Tips and tricks regarding specific cases
---

# Special cases



### SELINUX

If you have selinux enabled on your distro, you might want to check if it's not preventing the mount volume of the docker compose; you can try something like this:

```
chcon -Rt svirt_sandbox_file_t ./db
```

### Recompute assessment results after the semantic compute_result upgrade

Audits produced before the semantic [`compute_result`](../configuration/authoring/framework-builder.md#questions-and-choices) aggregation may have stored results that were collapsed under the older boolean logic (any non-empty `compute_result` was treated as truthy, so a "Non compliant" choice could still aggregate to **Compliant**). This applies to audits backed by questionnaires from either path: the [framework builder UI](../configuration/authoring/framework-builder.md) or [Excel-imported frameworks](../configuration/authoring/framework.md).

The `recompute_assessment_results` Django management command realigns stored results with the current rule.

```sh
# Preview impact, no writes
poetry run python manage.py recompute_assessment_results --dry-run

# Apply to all audits, one transaction per batch (default)
poetry run python manage.py recompute_assessment_results

# Scope to a single audit
poetry run python manage.py recompute_assessment_results \
    --compliance-assessment <uuid>

# Tune batch size or wrap the full run in one transaction
poetry run python manage.py recompute_assessment_results --batch-size 1000 --atomic
```

Properties:

- **Idempotent.** Running twice is a no-op the second time; rows already aligned are reported as `unchanged`.
- **Non-destructive on manual entries.** Requirements without questions (manual-entry rows, respondent-alignment-driven rows) are not touched.
- **Per-batch commits by default.** Lock duration stays bounded on large tenants. Use `--atomic` for all-or-nothing semantics on small datasets.
- **Touches `score`, `result`, `is_scored`, `updated_at`** on the requirement assessments it rewrites. Other fields are left as-is.

If you run the application via Docker Compose, prefix with `docker compose exec backend` (or the equivalent for your deployment).
