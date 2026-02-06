
docker rm -f integrator-app

docker run -d -p 6060:6060 --env-file .env.docker --name integrator-app  \
    --network aintegrator-backend \
    ghcr.io/jingnanzhou/integrator:latest

docker logs -f integrator-app


