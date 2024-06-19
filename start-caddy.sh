#!/usr/bin/env bash
# create Caddyfile and start caddy

python -c "
import os, re, pathlib
url = os.environ.get('CISO_ASSISTANT_URL')
assert url, 'missing environment variable CISO_ASSISTANT_URL'
q=re.match(r'https://([^/]+)', url)
assert q, 'bad environment variable CISO_ASSISTANT_URL'
target=q.group(1)
a = target + ''' {
    reverse_proxy /accounts/saml/acs/ localhost:8000
    reverse_proxy /accounts/saml/acs/finish/ localhost:8000
    reverse_proxy /* localhost:3000
}'''
pathlib.Path('Caddyfile').write_text(a)
" && caddy run
