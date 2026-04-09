#!/bin/bash

# This script provides a few useful commands for monitoring the Kubernetes cluster.

NAMESPACE="weibo-sentiment"

echo "--- Cluster Info ---"
kubectl cluster-info

echo "
--- Nodes ---"
kubectl get nodes -o wide

echo "
--- Pods in namespace '$NAMESPACE' ---"
kubectl get pods -n $NAMESPACE -o wide

echo "
--- Services in namespace '$NAMESPACE' ---"
kubectl get services -n $NAMESPACE

echo "
--- Deployments in namespace '$NAMESPACE' ---"
kubectl get deployments -n $NAMESPACE

echo "
--- Ingresses in namespace '$NAMESPACE' ---"
kubectl get ingress -n $NAMESPACE

# To view logs for a specific pod, use:
# kubectl logs <pod-name> -n $NAMESPACE

# To get a shell into a running container, use:
# kubectl exec -it <pod-name> -n $NAMESPACE -- /bin/sh
