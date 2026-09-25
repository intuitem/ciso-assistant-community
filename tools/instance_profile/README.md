# Instance profile

Reproduce the shape of a customer instance locally without its data.

## 1. Extract (customer side)

Read-only, anonymous shape of the instance: per-model counts, FK/M2M fan-out distributions, tree depths, enum spreads, text lengths, loaded library URNs and migration heads. No row values, names or IDs are exported; only public library URNs appear.

```bash
docker compose exec -T backend uv run python manage.py shell < extract_profile.py
docker compose cp backend:/tmp/instance_profile.json .
```

The script can also be pasted as-is into `python manage.py shell`. It writes `/tmp/instance_profile.json` (change `OUT` at the top to write elsewhere).

## 2. Synthesize (local side)

On a fresh database (migrated, `storelibraries` done):

```bash
python manage.py synthesize_from_profile instance_profile.json [--scale 0.5] [--seed 42] [--skip-libraries]
```

Loads the same libraries, creates rows through the real `save()` path in dependency order, follows the profiled FK/M2M distributions and trees, then prints target vs actual counts and errors per model.

Run the extractor on the result and diff both profiles to check fidelity.
