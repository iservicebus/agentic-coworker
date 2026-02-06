docker rm -f support-services-app
docker run -d --env-file ./.env.docker -p 5000:5000 --add-host=host.docker.internal:host-gateway --network aintegrator-backend --name support-services-app   ghcr.io/jingnanzhou/support-services:latest

docker logs -f support-services-app

