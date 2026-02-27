docker compose down

docker volume ls -q | grep '^agentic-coworker' | xargs -r docker volume rm
