#!/usr/bin/env bash
# simple script to have an overview of a cluster
# KUBECONFIG shall be properly set

echo "********* Environment ***************"
echo $(basename "$KUBECONFIG")
echo
echo "********* List of client pods and images **************"
kubectl get pods -n default -o jsonpath='{range .items[*]}{@.metadata.name}{" "}{@.spec.containers[*].image}{"\n"}{end}'| column -t
echo
echo "********* List of client pods with status **************"
kubectl get pods -n default 