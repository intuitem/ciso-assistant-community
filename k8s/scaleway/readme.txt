# list of tricks for Scaleway

alias k="kubectl --kubeconfig $(pwd)/kubeconfig-k8s-mira.yaml"

docker tag mira:0.9.1c rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest

docker push rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest

k create secret docker-registry registry-secret --docker-server=rg.fr-par.scw.cloud --docker-username <login> --docker-password <pwd>

## ingress controller

To install nginx ingress controller, use "Easy deploy" instruction, with:
    - app name = mira
    - app namespace = kube-system
Then, launch the script "patch-nginx" to add the --enable-ssl-passthrough option to nginx.

## Transactional email

Follow Scaleway instructions to create a mail domain for outgoing mails.
