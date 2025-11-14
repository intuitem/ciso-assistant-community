## how to setup the lab

- Start the compose, it will expose Postgres on two ports: the standard 5432 for direct access and 5433 that is proxied through ToxiProxy
- run the `setup_toxiproxy.sh` script that will initiate the proxy (default to 10 ms latency)
- prepare the env variables for CISO Assistant. The db settings and credentials are on the compose and use the port 5433.
- Once started you can add latency using the `add_latency.sh` script. The param is in ms. You can re-run with the new value that will override the previous one.
- You can remove it using the `remove_latency.sh` for a before and after test.
- `check_latency.sh` interacts with toxiproxy api to read the current settings.
