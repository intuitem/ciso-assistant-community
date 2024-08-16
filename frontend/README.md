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
