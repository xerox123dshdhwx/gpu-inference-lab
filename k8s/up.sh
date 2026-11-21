#!/bin/bash
# Rebuild everything inside the cluster after terraform apply. Run from the project folder.
set -e
aws eks update-kubeconfig --region eu-west-3 --name gpu-lab
kubectl apply -f k8s/gpu-nodepool.yaml
DP_VERSION=$(curl -s https://api.github.com/repos/NVIDIA/k8s-device-plugin/releases/latest | grep -oP '"tag_name": "\K[^"]+')
kubectl create -f https://raw.githubusercontent.com/NVIDIA/k8s-device-plugin/$DP_VERSION/deployments/static/nvidia-device-plugin.yml
kubectl create secret generic hf-token --from-literal=HF_TOKEN=$HF_TOKEN
kubectl create configmap bench-code --from-file=workload/replay.py \
  --from-file=eval/tool_eval.py --from-file=workload/traces.json
kubectl create configmap bench-eval --from-file=eval/eval_set.jsonl
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update
helm upgrade --install monitoring prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace \
  --set prometheus.prometheusSpec.podMonitorSelectorNilUsesHelmValues=false \
  --set prometheus.prometheusSpec.serviceMonitorSelectorNilUsesHelmValues=false
kubectl apply -f k8s/vllm-podmonitor.yaml