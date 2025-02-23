## Using the config builder

- Install Python
- Create a virtual env
- Install dependencies (`requirements.txt`)
- Run `python3 make_config.py`
- Review the generated file and adapt it if needed
- Run `docker-compose.sh` and follow the instructions. First initialization could take up to 2 mn.

Note: if you are looking for a striped variant with no proxy, checkout the file in `docker-compose-no-proxy.yml` on which you'll be able to access the app on `https://localhost:3000`. In this case, and since SvelteKit (node server) will be directly exposed, make sure to always have the `ORIGIN` variable at the frontend matching the `CISO_ASSISTANT_URL` at the backend to avoid getting blocked by the CSRF protection.

The no-proxy setup is not recommended and not part of the supported variant and only serves as a reference for other implementation.
