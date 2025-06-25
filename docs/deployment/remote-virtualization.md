---
description: Experimenting CISO Assistant through remote server or hypervisor
---

# Remote/Virtualization



{% hint style="warning" %}
New: Use the config builder at the `config` folder of the repo for an interactive and reliable experience.
{% endhint %}



To get started with  the config builder, make sure you have python and docker installed. Here is an example on ubuntu:



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



{% hint style="danger" %}
<mark style="color:orange;">**You cannot use IP addresses on the configuration and you need to have a FQDN mapped to it.**</mark>
{% endhint %}



1. If you aim to expose the **VM to internet**, use this dedicated guide: [deploy-on-a-vps.md](deploy-on-a-vps.md "mention")
2. If you aim to connect **from the VM**
3. If you aim to connect **to the VM from your network**



### From the VM

This means that you _**will be using a browser from within the VM**_ so localhost settings are applicable. You can simply use the default ./docker-compose.sh at the root of the repository or trigger the config builder with the following settings:

<figure><img src="../.gitbook/assets/image (36).png" alt=""><figcaption></figcaption></figure>

run `./docker-compose.sh` and connect from within the VM using `https://localhost:8443`&#x20;

### From your network / host OS



* setup a FQDN for your VM and make sure it's known by the host you are connecting from. This will vary depending on your OS. For instance, for linux/mac, you can add a line to your `/etc/hosts` file such as:

`192.168.1.87 ca.homelab.local`

in this example, the first part is your VM's ip and the second one will be the FQDN you'll be providing to the config builder and that you will use to connect later on.

Run the config builder and provide the following settings:

<figure><img src="../.gitbook/assets/image (37).png" alt=""><figcaption></figcaption></figure>

run `./docker-compose.sh` and connect from your host this time using `https://ca.homelab.local:8443`&#x20;



_Notes:_

* If you don't want to have a specific port, use the port 443 during the settings, given it's not used by another application on your system.
* In the remote setup, if you also want to connect from within the VM, you can add your custom FQDN to the /etc/hosts of your VM but mapped to 127.0.0.1



\---

### Legacy - Kept for reference purposes&#x20;

Let's say that you want to setup or experiment with CISO Assistant on a Network or Virtualized environment (eg. Hypervisor) on a remote host, for instance, to use with multiple users:



<figure><img src="../.gitbook/assets/image (10) (1).png" alt=""><figcaption></figcaption></figure>

* Install a recent version of Docker on your remote server
* Given that we are using TLS with Caddy, we need to have DNS entries and not IPs
* The workstations need to be able to reach the remote using an FQDN (DNS entry). If not you can add an entry on your `/etc/hosts`. Keep track of the remote server DNS as you'll put it on the next step, let's say the remote is `cool-vm` for instance
* Clone the repo, but don't run anything yet. **Edit** the `docker-compose.yml` file as follows:\
  (red is for deletion and green for addition); your diff should look like:

<figure><img src="../.gitbook/assets/image (13).png" alt=""><figcaption></figcaption></figure>

* Five lines need to be edited. Save the file and move to the next step

If you're getting `SSL_ERROR_INTERNAL ERROR_ALERT` (Can be different on other browsers) blocking you from continuing, make sure that you've made the 5 changes above.

<mark style="color:purple;">The</mark> <mark style="color:purple;"></mark><mark style="color:purple;">`tls internal`</mark> <mark style="color:purple;"></mark><mark style="color:purple;">(equivalent to</mark> <mark style="color:purple;"></mark><mark style="color:purple;">`-i`</mark> <mark style="color:purple;"></mark><mark style="color:purple;">in CLI mode) parameter of Caddy can present some security issues and is not recommended for production and internet exposure. You should consider proper certificates for that.</mark>



You're all set, and you can simply run:

```
./docker-compose.sh
```

Your CISO Assistant can be reached now from  `https://cool-vm:8443`, and you can skip the SSL warning for the self-signed certificate.
