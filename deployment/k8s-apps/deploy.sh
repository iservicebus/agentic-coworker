#!/bin/bash

# Kubernetes deployment script for AIntegrator platform

set -e

echo "========================================="
echo "AIntegrator Kubernetes Deployment"
echo "========================================="
echo ""

# Check if secret.yaml exists
if [ ! -f secret.yaml ]; then
    echo "Error: secret.yaml not found!"
    echo "Please create secret.yaml from secret.yaml.template:"
    echo "  cp secret.yaml.template secret.yaml"
    echo "  # Then edit secret.yaml with your secrets"
    exit 1
fi

# Check if kubectl is available
if ! command -v kubectl &> /dev/null; then
    echo "Error: kubectl is not installed or not in PATH"
    exit 1
fi

echo "Step 1/5: Creating namespace..."
kubectl apply -f namespace.yaml

echo ""
echo "Step 2/5: Creating ConfigMap..."
kubectl apply -f configmap.yaml

echo ""
echo "Step 3/5: Creating Secrets..."
kubectl apply -f secret.yaml

echo ""
echo "Step 4/5: Deploying services..."
kubectl apply -f portal-deployment.yaml
kubectl apply -f integrator-deployment.yaml
kubectl apply -f mcp-services-deployment.yaml
kubectl apply -f support-services-deployment.yaml

echo ""
echo "Step 5/5: Waiting for pods to be ready..."
echo "This may take a few minutes..."
kubectl wait --for=condition=ready pod -l app=portal -n aintegrator --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=integrator -n aintegrator --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=mcp-services -n aintegrator --timeout=300s || true
kubectl wait --for=condition=ready pod -l app=support-services -n aintegrator --timeout=300s || true

echo ""
echo "========================================="
echo "Deployment Status:"
echo "========================================="
kubectl get all -n aintegrator

echo ""
echo "========================================="
echo "Services deployed successfully!"
echo ""
echo "Access points:"
echo "  Portal:           http://localhost:30000"
echo "  Integrator:       http://localhost:30060"
echo "  MCP Services:     http://localhost:30666"
echo "  Support Services: http://localhost:30500"
echo ""
echo "To view pod status:"
echo "  kubectl get pods -n aintegrator"
echo ""
echo "To view logs:"
echo "  kubectl logs -n aintegrator <pod-name>"
echo ""
echo "To follow logs:"
echo "  kubectl logs -n aintegrator <pod-name> -f"
echo ""
echo "To delete all resources:"
echo "  kubectl delete namespace aintegrator"
echo ""
