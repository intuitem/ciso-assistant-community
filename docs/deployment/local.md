---
description: Basic setup for local deployment and experimentation
---

# Local

The recommended pattern for local deployment is to use **Docker Compose**. Check the Readme file on the CISO Assistant repo for the latest instructions.



The compose file will manage three containers and set the required variables:

* Front
* Back
* Caddy (proxy)



* Make sure to have a recent version of Docker installed
  * On a Linux distro with a server flavor, make sure to remove older versions and install the latest one using the proper Docker repos to avoid twisted setups. Check out the instructions at [https://docs.docker.com/engine/install/ubuntu/](https://docs.docker.com/engine/install/ubuntu/)
* On Windows, Docker Desktop+WSL is recommended
* On MacOS, Docker Desktop covers the requirements

### Using prebuilt images

Run:

```
./docker-compose.sh
```

It will clean up previous images and get the latest stable release.

Once the images are downloaded and migration triggered, you should see a prompt asking you to set the first superuser. Follow the instructions to set it, and you should be ready.&#x20;





In case you are running on an unsupported architecture, you can open a GitHub issue so that we add its support or use the next steps to build the images locally.

### Re-building the images locally

Alternatively, if the previous configuration didn't succeed, run:&#x20;

```
./docker-compose-build.sh
```



### SSL Warning

Given that Caddy is using a `self-signed certificate`, your browser will mention a warning that you can accept and continue.

