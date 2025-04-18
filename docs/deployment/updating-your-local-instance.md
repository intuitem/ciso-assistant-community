---
description: >-
  How to update your local instance. All docker images are available on ghcr
  with the specific versions matching the repo tags. The latest tag points to
  the most recent release for both back and front.
---

# Updating your local instance

## Hands-free

The easiest way to update your on-prem/local instance (pro or community)

**Run the script&#x20;**_**update-ciso-assistant**_**:**

```bash
./update-ciso-assistant.sh
```

## Manually

If you need to do it manually for any reasons on a local instance

**Backup your db file outside of the repo folder, always a good practice**

```bash
cp db/ciso-assistant.sqlite3 ../ciso-assistant-backup.sqlite3
```

**Stop the containers and delete the containers instances**

```bash
docker compose down
```

**Clean up the previous docker images**

```bash
docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> /dev/null
```

**Trigger compose up to refresh the images**

```bash
docker compose up -d #remove -d if you want the logs directly in your shell
```
