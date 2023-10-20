#!/bin/bash
read -p "Enter admin email: " EMAIL
docker container exec -it ciso-assistant python ./manage.py changepassword $EMAIL
