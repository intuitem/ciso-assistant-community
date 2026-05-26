---
description: Deployment documentation for rootless containers
---

# Docker rootless configuration

> Since V3.16, CISO Assistant now runs as non-root user 1001:1001 by default across all compose templates.

{% hint style="warning" %}
If you already have a local instance of CISO Assistant, please refer to the migration guide&#x20;
{% endhint %}

## Fresh install&#x20;

If you are new from Ciso-Assistant, you will automatically be deployed with a rootless Docker configuration by running pre-built images or local image build

### Using pre-built images

```
./docker-compose.sh
```

### Using image local build

```
./docker-compose-build.sh
```

## Migration guide

You already have a self-hosted Ciso Assistant (Community version or On-Premise Pro version) and you want to know all the options you have:

<details>

<summary>I want a rootless Docker and I am currently running CISO Assistant with pre-built images</summary>

#### You are using <mark style="color:$primary;">docker-compose.yml</mark> to deploy Ciso Assistant

```
git pull
docker compose down
sudo chown -R 1001:1001 ./db
```

Then update your docker-compose.yml on the version you want (ex: v3.16) or keep latest tag and then ignore the manual update in your file.

```
docker compose up -d
```

Your new containers should be root-less!

#### You are using a <mark style="color:$primary;">custom .yml</mark> to deploy Ciso Assistant

If you have any doubt about updating your custom .yml, do not hesitate to contact us on our Discord or Support portal.&#x20;



</details>

<details>

<summary>I want a rootless Docker and I am currently running CISO Assistant with local images</summary>

```
git pull
docker compose down
sudo chown -R 1001:1001 ./db
docker compose -f docker-compose-build.yml up -d
```

</details>

## Keep root Docker&#x20;

In the case you do not want to have rootless Docker&#x20;

<details>

<summary>Keep the root Docker as it was before </summary>

```
docker compose down
```

Then manually update your docker-compose.yml on the images version you want (ex: v3.16). <mark style="color:$primary;">Ignore this step if you use latest image</mark>

```
image: ghcr.io/intuitem/ciso-assistant-community/frontend:v3.15.2
# replace with (for example)
image: ghcr.io/intuitem/ciso-assistant-community/frontend:v3.16
```

```
docker compose up -d
```

That is it! Since you did not update the github repository, the docker-compose.yml keeps the initial form without root less Docker configuration

{% hint style="warning" %}
In the case you did update the github repository by doing a _git pull_ command, we suggest you to take an older version of the file (like the v3.15.5 docker-compose.yml version)
{% endhint %}

</details>

## Simple rootless check

If you want to verify if you run a rootless Docker container, do:

```
docker exec -it backend id
```

It should say :

```
uid=1001 gid=1001 groups=1001
```
