docker run --rm  -p 8000:8000 --env MIRA_URL=http://127.0.0.1:8000 --env DJANGO_DEBUG=True --env EMAIL_HOST=127.0.0.1 --env EMAIL_PORT=8025 \
	--env EMAIL_HOST_PASSWORD=bar --env EMAIL_HOST_USER=foo \ 
	--env RECAPTCHA_PUBLIC_KEY=MyRecaptchaKey123 --env RECAPTCHA_PRIVATE_KEY=MyRecaptchaPrivateKey456 \
	--env DJANGO_SUPERUSER_EMAIL=root@example.com --env DJANGO_SUPERUSER_PASSWORD=toto \
	mira-cluster-controller:0.1
