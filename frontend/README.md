# Quick start (development)

1. Clone the repository
2. Create a `.env` file with environment variables or export them.

```bash
echo "PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000/api" > .env
```

OR

```bash
export PUBLIC_BACKEND_API_URL=http://127.0.0.1:8000/api
```

3. Install dependencies

```bash
npm install -g pnpm
pnpm install
```

4. Start a development server (ensure that the django app is running)

```bash
pnpm run dev
```

## Building

To create a production version of your app:

```bash
pnpm run build
```

You can preview the production build with `pnpm run preview`.

> To deploy your app, you may need to install an [adapter](https://kit.svelte.dev/docs/adapters) for your target environment.

## Testing with Safari

Safari requires https. To test it, the simplest solution is to use a local instance of caddy. To have it work properly, it is necessary to trick vite by sending it the Origin variable, as vite does not handle environment variables. The Caddyfile provided here is working properly, and can be launched by simply typing "caddy run".

In this setup, it is necessary to launch the backend with an adjusted CISO_ASSISTANT_URL=https://localhost.

## Testing SSO

1. Use `caddy run -c Caddyfile-sso`
2. Launch `ORIGIN=https://localhost PUBLIC_BACKEND_API_EXPOSED_URL=https://localhost/api node server` on frontend side
3. Launch `CISO_ASSISTANT_URL=https://localhost  python manage.py runserver` on backend side
4. Use `https://localhost` as the connection URL.
5. Configure your IdP accordingly.
