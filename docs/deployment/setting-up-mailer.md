# Setting up mailer

Setup the following environment variables:

```sh
DEFAULT_FROM_EMAIL=purple@ciso-assistant.fr
EMAIL_HOST=localhost
EMAIL_PORT=1025
EMAIL_HOST_USER=purple
EMAIL_HOST_PASSWORD=dummy-unsafe-example
EMAIL_USE_TLS=True
```

**Note: Docker Compose Environment Variables**

When using Docker Compose, **avoid spaces around the `=` sign** in environment variable definitions. Spaces cause variables to be silently ignored.

**Correct:** `MY_VARIABLE=value`\
**Incorrect:** `MY_VARIABLE = value`

### Add automatically your local CA-certificate

An issue you may encounter when setting up your mailer is that your local CA certificates might not be included inside your Docker container. This could cause problems when sending emails.

To address this, we provide a script located at _config/init-custom-ca-certificates.sh_ and _enterprise/config/init-custom-ca-certificates.sh_.

You need to use this script with your Docker Compose setup by adding the following lines to the <mark style="color:$primary;">backend</mark> and <mark style="color:$primary;">huey</mark> services:

* **This environment variable :**&#x20;

```yaml
- CUSTOM_CA_CERT_PATH=/usr/local/share/ca-certificates/root_CA.crt
```

* **This volumes** (replace /your/ca-certificate/path/example\_CA.crt by the pass and the name of your ca-certificate) **:**

```yaml
- /your/ca-certificate/path/example_CA.crt:/usr/local/share/ca-certificates/root_CA.crt:ro
- ./config/init-custom-ca-certificates.sh:/docker-entrypoint-init.d/init-custom-ca-certificates.sh:ro
```

* **This entrypoint :**&#x20;

```yaml
entrypoint:
  - /bin/sh
  - -c
  - |
    /docker-entrypoint-init.d/init-custom-ca-certificates.sh
```

> There's already an entrypoint for huey, you can modify it like this:
>
> ```yaml
> entrypoint:  
>   - /bin/sh
>   - -c
>   - |
>     /docker-entrypoint-init.d/init-custom-ca-certificates.sh && \
>     poetry run python manage.py run_huey -w 2 --scheduler-interval 60
> ```
