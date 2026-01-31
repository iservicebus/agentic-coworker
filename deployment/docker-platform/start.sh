#!/bin/bash

# Start Support Platform Services

set -e

echo "========================================="
echo "AIntegrator Support Platform"
echo "========================================="
echo ""
echo "Starting infrastructure services..."
echo ""

# Start all services
docker-compose up -d

echo ""
echo "Waiting for services to start..."
sleep 10

echo ""
echo "Service Status:"
echo "========================================="
docker-compose ps

echo ""
echo "Infrastructure services are starting up!"
echo ""
echo "Services:"
echo "  Keycloak (IAM):      http://localhost:8888 (admin/admin)"
echo "  PostgreSQL:          localhost:5432 (user/password)"
echo "  Neo4j UI:            http://localhost:7474 (neo4j/password)"
echo "  Traefik Dashboard:   http://localhost:8080"
echo "  NATS Monitoring:     http://localhost:8222"
echo "  ETCD:                localhost:12379"
echo ""
echo "⚠️  Note: First startup may take 30-60 seconds for all services to be ready"
echo ""
echo "Next steps:"
echo "  1. Wait for all services to be healthy"
echo "  2. Follow the initialization steps in README.md"
echo ""
echo "To view logs:"
echo "  docker-compose logs -f"
echo ""
echo "To stop services:"
echo "  docker-compose down"
echo ""
