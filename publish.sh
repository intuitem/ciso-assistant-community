#!/usr/bin/env bash

VERSION=$(<asf_rm/VERSION)
echo "publshing MIRA $VERSION to scaleway repo"
docker build -t mira:$VERSION .
docker tag mira:$VERSION rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:$VERSION
docker push rg.fr-par.scw.cloud/funcscwmiraj3whjdnx/mira:$VERSION
echo "To apply it, change the template for MIRA controller"