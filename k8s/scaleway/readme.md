# list of tricks for Scaleway

## Environment and aliases

Retrieve the kubeconfig-k8s-mira.yaml file.

``` shell
export KUBE_CONFIG=$(pwd)/kubeconfig-k8s-mira.yaml
alias k=kubectl
```

## Pushing an image

You need an API key with permission ContainerRegistryFullAccess.

``` shell
echo <api_key> | docker login rg.fr-par.scw.cloud/funcscwmiraj3whjdnx -u nologin --password-stdin 
docker tag mira:0.9.1c rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest
docker push rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest
```

## Enabling pulling image

You need an API key with permission ContainerRegistryReadOnly.

``` shell
k create secret docker-registry registry-secret --docker-server=rg.fr-par.scw.cloud --docker-username funcscwmiraj3whjdnx --docker-password <api_key>
```

Add the following line in the container definition:

```
      imagePullSecrets:
        - name: registry-secret
```

## ingress controller

To install nginx ingress controller, use "Easy deploy" instruction, with:
    - app name = mira
    - app namespace = kube-system
Then, launch the script "patch-nginx" to add the --enable-ssl-passthrough option to nginx.

## Transactional email

Follow Scaleway instructions to create a mail domain for outgoing mails.

To allow an application to send email, use permission TransactionalEmailFullAccess.

Store the API key in a secret with the following command:
```shell
k create secret generic smtp-out --from-literal EMAIL_HOST_PASSWORD=<api_key>
```

Note that EMAIL_HOST_USER shall be set to the UUID of the project.

## IAM configuration

### Applications

- mira
  - policy mira-smtp-out with permission TransactionalEmailFullAccess
  - API key without expiration
- mira-registry-push-eric
  - policy mira-registry-push with permission ContainerRegistryFullAccess
  - Used by eric for development and testing
  - API key with expiration
- mira-registry-pull
  - policy mira-registry-pull with permission ContainerRegistryReadOnly
  - API key without expiration
