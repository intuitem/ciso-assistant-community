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

To address this, we need to apply some modifications to the compose file in the <mark style="color:$primary;">**backend**</mark> and <mark style="color:$primary;">**huey**</mark> services:

* **Add a volume to mount the certificate** (replace /your/ca-certificate/path/example\_CA.crt by the path and the name of your ca-certificate)**:**

<pre class="language-yaml"><code class="lang-yaml">backend (or huey):
  ...
  volumes:
    ...
<strong>    - /your/ca-certificate/path/example_CA.crt:/usr/local/share/ca-certificates/root_CA.crt:ro
</strong></code></pre>

* **Add a command through the entrypoint:**&#x20;

```yaml
backend:
  ...
  entrypoint:
    - /bin/sh
    - -c
    - |
      update-ca-certificates
      poetry run bash ./startup.sh
```

> There's already an entrypoint for huey, you can modify it like this:
>
> ```yaml
> huey:
>   ...  
>   entrypoint:  
>     - /bin/sh
>     - -c
>     - |
>       update-ca-certificates
>       poetry run python manage.py run_huey -w 2 --scheduler-interval 60
> ```
