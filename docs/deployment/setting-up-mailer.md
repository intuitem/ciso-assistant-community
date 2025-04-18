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
