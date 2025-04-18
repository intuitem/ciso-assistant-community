---
description: Virtual Private Server - Remote internet-facing VM
---

# Deploy on a VPS

This setup aims to expose CISO Assistant on a VPS while using automated Let's Encrypt for certificates management.



1. provision your VPS and make sure it has a public reachable IP - make sure to have the [prerequisites.md](prerequisites.md "mention") mentioned on that page.
2. Setup your DNS zone to point to the IP of your VPS (A record). Give it sometime to propagate (depends on the registrar). It's better to start with this once you get the IP to give it enough time for propagation.
3. on the following I'm using ubuntu 24.04. So adjust the packages installation according to your OS
4. ssh to your server and perform the following commands:

```sh
#update ubuntu repository and OS
sudo apt update
sudo apt upgrade 

# install docker
sudo snap install docker

#install python
sudo apt install python3-pip python3.12-venv

#clone the repo
git clone https://github.com/intuitem/ciso-assistant-community.git

#go to the config generator
cd ciso-assistant-community
cd config

# setting up the python project and dependencies 
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# run the interactive config generator
python make_config.py
```

5. Follow the instructions and make sure to do the following:

* select VM/Remote
* Internet facing and ACME ready - yes
* Provide the FQDN you've set on your registrar
* Port to use: 443

It should look like something like this:

<figure><img src="../.gitbook/assets/image (34).png" alt=""><figcaption></figcaption></figure>

6. Keep track of the URL mentioned at the end of the config generator. You can review the generated yml file and adapt it if needed.

```sh
# switch to sudo. This can be avoided depending on your docker setup
sudo su 
./docker-compose.sh
```

Wait for the app to initialize and you will get a prompt to enter the first admin user and the password.



You can go back and update the docker-compose.yml according to your needs or restart the interactive guide to create a new one.



You can choose Traefik instead of Caddy using the config builder.



### 👉 Notes

* The generated file in the config directory will be named `docker-compose-custom.yml` For subsequent operations with compose, you'll need to specify it with `-f`
* If you're running docker compose without the -f, it could conflict with the default one on the repository root directory.
* If you're starting a production environment:
  * make sure to disable the debug mode,
  * have your docker-compose-custom renamed and stored out of the repo,
  * have your db folder outside of the repo.

### Clean up

<pre class="language-sh"><code class="lang-sh"><strong>cd config
</strong># stop and remove containers
docker compose -f docker-compose-custom.yml rm -fs
# delete the db and proxy config
git clean -fdx .
</code></pre>
