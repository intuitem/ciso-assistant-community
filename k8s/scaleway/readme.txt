alias k="kubectl --kubeconfig kubeconfig-k8s-mira.yaml"
docker tag mira:0.9.1c rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest
docker push rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:latest\n
k create secret docker-registry registry-secret --docker-server=rg.fr-par.scw.cloud --docker-username <login> --docker-password <pwd>

