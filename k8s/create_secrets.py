# Simple program to facilitate creation of secrets for K8s
# Transforms a list of exports in a directory ready for "kubectl create secret"
# This avoids the dreaded commit of a secret in git

import re
import sys
import os
import shutil

SECRET_KEYS = ('DJANGO_SECRET_KEY', 'POSTGRES_PASSWORD', 'DJANGO_SUPERUSER_EMAIL', 'DJANGO_SUPERUSER_PASSWORD', 'EMAIL_HOST_PASSWORD', 'EMAIL_HOST_PASSWORD_RESCUE')

if len(sys.argv) != 2:
    print("Usage: create_secrets.py var_file", file=sys.stderr)
    exit(1)

filename = sys.argv[1]
dirname = f"{filename}.secrets"
shutil.rmtree(dirname, ignore_errors=True)
os.makedirs(dirname)

mykeys = set()

with open(filename, "r") as f:
    lines = f.readlines()
    for line in lines:
        q = re.match("export (.+)=(.+)", line)
        if q:
            (name, val) = q.groups()
            if name in SECRET_KEYS:
                mykeys.add(name)
                print("creating secret ", name)
                with open(f"myvars.secrets/{name}", "w") as f2:
                    print(val, file=f2, end='')

if 'DJANGO_SECRET_KEY' in mykeys and 'POSTGRES_PASSWORD' not in mykeys:
    print("WARNING: DJANGO_SECRET_KEY defined while using sqlite. Are you sure?")
print("To load the secrets in K8s, use a command like: kubectl create secret generic myvars --from-file myvars.secrets")
