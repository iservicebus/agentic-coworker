
docker stop  mcp-services-app
docker rm  mcp-services-app

docker run -d  -p 6666:6666 --env-file .env.docker  --network aintegrator-backend   --name mcp-services-app ghcr.io/jingnanzhou/mcp-services:latest

docker logs -f mcp-services-app

