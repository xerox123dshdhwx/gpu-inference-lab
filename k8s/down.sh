#!/bin/bash
kubectl delete deployment,job --all
kubectl delete nodepool --all
echo "Waiting for Karpenter to remove the GPU machines..."
while [ -n "$(kubectl get nodeclaims -o name)" ]; do sleep 10; done
cd infra && terraform destroy -auto-approve