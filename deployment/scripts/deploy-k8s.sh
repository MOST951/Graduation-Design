#!/bin/bash

# Exit on error
set -e

# Apply the Kubernetes configurations
kubectl apply -f deployment/k8s/configmap.yml
kubectl apply -f deployment/k8s/backend-deployment.yml
kubectl apply -f deployment/k8s/backend-service.yml
kubectl apply -f deployment/k8s/frontend-deployment.yml
kubectl apply -f deployment/k8s/frontend-service.yml
kubectl apply -f deployment/k8s/ingress.yml
