# Frequent questions



### Didn't get the prompt for the first user

If you didn't get the prompt to create the first user, or lost the password but you still have access to the infra level, you can trigger the `createsuperuser` command to fix that.

In your compose file folder, try:

`docker compose exec backend poetry run python manage.py createsuperuser`

Alternatively, in a docker environment:

`docker ps -a | grep backend` (this will get you the id of the Backend for CISO Assistant container, keep it for the next step)

`docker exec -it <the_container_id> poetry run python manage.py createsuperuser`

and you should get a prompt now 😉

### Random issues after upgrading&#x20;

In some rare cases, the migration of database schemas can take longer than expected or fail silently. First thing to check is the backend container logs:

```
docker compose logs backend
```

Make sure you share these information if you're reporting an issue on Discord or the Support portal.

If you want to trigger the migration to make sure that all increments have been properly applied:

```
docker compose exec backend poetry run python manage.py migrate
```

### Healthcheck fails during the installation

most likely because the initialization took longer than expected. Make sure you provide the expected specs or tune the docker compose to give the app more time to finish the init phase.

### Don't want / Can't run the init script

The recommended pattern for a first local setup is to go with ./docker-compose.sh ;\
In case you can't:

Run

```
docker compose up -d
```

wait for the init to finish and then trigger the first user creation manually:

```
docker compose exec backend poetry run python manage.py createsuperuser
```

### "Payload too large" when uploading a file to the frontend

By default, the `BODY_SIZE_LIMIT` environment variable is set to 20 MB in the frontend Dockerfile:

```docker
# frontend/Dockerfile

ENV BODY_SIZE_LIMIT=20000000 
```

In order to upload larger files, this value must be increased. How to do so depends on you rmode of deployment. Here are relevant docs:

* [https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/](https://docs.docker.com/compose/how-tos/environment-variables/set-environment-variables/)
* [https://helm.sh/docs/helm/helm\_env/](https://helm.sh/docs/helm/helm_env/)
* [https://docs.docker.com/reference/cli/docker/container/run/#env](https://docs.docker.com/reference/cli/docker/container/run/#env)

{% hint style="info" %}
If you use helm, this value is overwritten by the `bodySizeLimit`  variable. Note the camel case here.
{% endhint %}



