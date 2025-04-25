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

## Detailled steps

In case of issues (unsupported shell, windows, etc.) here are the steps to consider:



1. backup your db:
   1. if you're using `sqlite`, copy the file under a different name
   2. if it's `postgresql` you can use something like `pgdump`&#x20;



2. stop and clean the containers, this won't affect your data

`docker compose rm -fs`



3. restart the compose and let it handle the migration&#x20;

`docker compose up -d`

## Edge cases

**Force remove the previous docker images to get the new ones**

```bash
docker rmi ghcr.io/intuitem/ciso-assistant-community/backend:latest ghcr.io/intuitem/ciso-assistant-community/frontend:latest 2> /dev/null
```

