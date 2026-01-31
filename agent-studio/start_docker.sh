
docker stop agent-studio-app
docker rm agent-studio-app

docker run -d -p 3000:3000 --env-file ./.env.docker      --network aintegrator-backend   --name agent-studio-app ghcr.io/jingnanzhou/agent-studio:latest


docker logs -f agent-studio-app
