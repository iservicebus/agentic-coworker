#!/bin/bash
# Deployment script for docker-apps with database initialization control

set -e

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Function to print colored messages
print_green() {
    echo -e "${GREEN}$1${NC}"
}

print_yellow() {
    echo -e "${YELLOW}$1${NC}"
}

print_red() {
    echo -e "${RED}$1${NC}"
}

# Check if db-init container exists
check_db_init_exists() {
    docker ps -a --format '{{.Names}}' | grep -q "^db-init$"
}

# Show usage
usage() {
    cat << EOF
Usage: $0 [OPTIONS]

Deploy docker-apps with optional database initialization control.

OPTIONS:
    --init          Force database initialization (removes and recreates db-init)
    --skip-init     Skip database initialization (start only app services)
    --help          Show this help message

EXAMPLES:
    $0                    # Standard deploy (init runs if not already done)
    $0 --init             # Force re-initialization
    $0 --skip-init        # Skip init, only start apps

EOF
}

# Parse arguments
FORCE_INIT=false
SKIP_INIT=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --init)
            FORCE_INIT=true
            shift
            ;;
        --skip-init)
            SKIP_INIT=true
            shift
            ;;
        --help)
            usage
            exit 0
            ;;
        *)
            print_red "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Check for conflicting options
if [ "$FORCE_INIT" = true ] && [ "$SKIP_INIT" = true ]; then
    print_red "Error: Cannot use --init and --skip-init together"
    exit 1
fi

print_green "=== Docker Apps Deployment ==="
echo ""

# Check prerequisites
print_yellow "Checking prerequisites..."

# Check if platform services are running
if ! docker ps | grep -q postgres; then
    print_red "Error: Platform services (postgres) not running"
    echo "Start platform services first:"
    echo "  cd ../docker-platform && docker-compose up -d"
    exit 1
fi

# Check if agent-ops image exists
if ! docker images | grep -q "agent-ops"; then
    print_red "Error: agent-ops image not found"
    echo "Build agent-ops image first:"
    echo "  cd ../../agent_ops && ./build.sh"
    exit 1
fi

# Check if data directory exists
if [ ! -d "../../data/backup_data/default_restore" ]; then
    print_red "Error: Default restore data not found"
    echo "Expected: ../../data/backup_data/default_restore/"
    exit 1
fi

print_green "✓ Prerequisites check passed"
echo ""

# Handle deployment based on options
if [ "$SKIP_INIT" = true ]; then
    print_yellow "Skipping database initialization..."
    print_yellow "Starting app services only..."
    docker-compose up -d agent-studio integrator mcp-services support-services

elif [ "$FORCE_INIT" = true ]; then
    print_yellow "Forcing database initialization..."

    # Remove db-init container if it exists
    if check_db_init_exists; then
        print_yellow "Removing existing db-init container..."
        docker-compose rm -f db-init
    fi

    print_yellow "Starting all services (db-init will run)..."
    docker-compose up -d

    # Wait for db-init to complete
    print_yellow "Waiting for database initialization to complete..."
    max_wait=300  # 5 minutes
    elapsed=0
    while [ $elapsed -lt $max_wait ]; do
        if ! docker ps | grep -q "db-init"; then
            # Container is not running, check if it exited successfully
            if docker ps -a --filter "name=db-init" --filter "status=exited" --format "{{.Status}}" | grep -q "Exited (0)"; then
                print_green "✓ Database initialization completed successfully"
                break
            else
                print_red "✗ Database initialization failed"
                echo ""
                print_yellow "Viewing db-init logs:"
                docker-compose logs db-init
                exit 1
            fi
        fi
        echo -n "."
        sleep 5
        elapsed=$((elapsed + 5))
    done

    if [ $elapsed -ge $max_wait ]; then
        print_red "✗ Database initialization timed out"
        exit 1
    fi

else
    # Standard deployment
    if check_db_init_exists; then
        db_status=$(docker ps -a --filter "name=db-init" --format "{{.Status}}")
        if echo "$db_status" | grep -q "Exited (0)"; then
            print_green "✓ Database already initialized (db-init container exists with success status)"
            print_yellow "Starting app services..."
            print_yellow "Note: To force re-initialization, use: $0 --init"
        else
            print_yellow "Warning: db-init container exists but did not exit successfully"
            print_yellow "Removing and recreating..."
            docker-compose rm -f db-init
        fi
    else
        print_yellow "Database not yet initialized, db-init will run..."
    fi

    docker-compose up -d
fi

echo ""
print_green "=== Deployment Status ==="

# Show running services
docker-compose ps

echo ""
print_green "=== Service URLs ==="
echo "Agent Studio:     http://localhost:3000"
echo "Integrator:       http://localhost:6060"
echo "MCP Services:     http://localhost:6666"
echo "Support Services: http://localhost:5000"

echo ""
print_yellow "To view logs:"
echo "  docker-compose logs -f"
echo "  docker-compose logs -f integrator"
echo "  docker-compose logs db-init"

echo ""
print_green "Deployment complete!"
