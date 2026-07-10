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

Audits produced before the semantic [`compute_result`](../configuration/authoring/framework-builder.md#questions-and-choices) aggregation may have stored results that were collapsed under the older boolean logic (any non-empty `compute_result` was treated as truthy, so a "Non-compliant" choice could still aggregate to **Compliant**). This applies to audits backed by questionnaires from either path: the [framework builder UI](../configuration/authoring/framework-builder.md) or [Excel-imported frameworks](../configuration/authoring/framework.md).

The `recompute_assessment_results` Django management command realigns stored results with the current rule.

```sh
# Preview impact, no writes
uv run python manage.py recompute_assessment_results --dry-run

# Apply to all audits, one transaction per batch (default)
uv run python manage.py recompute_assessment_results

# Scope to a single audit
uv run python manage.py recompute_assessment_results \
    --compliance-assessment <uuid>

# Tune batch size or wrap the full run in one transaction
uv run python manage.py recompute_assessment_results --batch-size 1000 --atomic

# Skip the post-run CA hooks (metrics + CEL outcomes), e.g. when chaining
# with another job that will recompute them
uv run python manage.py recompute_assessment_results --skip-post-hooks
```

Properties:

- **Scoped to compute_result-driven requirements only.** The command targets requirement assessments whose requirement carries at least one question choice with a resolvable `compute_result`. Score-only or manual-entry audits are left alone, so a manually-set result is never silently reset to `not_assessed`.
- **Idempotent.** Running twice is a no-op the second time; rows already aligned are reported as `unchanged`.
- **Per-batch commits by default.** Lock duration stays bounded on large tenants. Use `--atomic` for all-or-nothing semantics on small datasets.
- **Touches `score`, `result`, `is_scored`, `updated_at`** on the requirement assessments it rewrites. Other fields are left as-is.
- **Re-triggers CA-level hooks** after writes: `ComplianceAssessment.upsert_daily_metrics()` and CEL outcome evaluation are explicitly called once per touched audit, because `bulk_update` bypasses the `RequirementAssessment.save()` signal chain. If any hook fails, the command exits with a `CommandError` listing the failures, so you don't silently end up with up-to-date results but stale metrics or CEL outcomes. Pass `--skip-post-hooks` to opt out when you handle those hooks separately.

If you run the application via Docker Compose, prefix with `docker compose exec backend` (or the equivalent for your deployment).
