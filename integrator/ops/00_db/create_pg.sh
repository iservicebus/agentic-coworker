docker run -d \
  --name postgres \
  -e POSTGRES_USER=user \
  -e POSTGRES_PASSWORD=password \
  -e POSTGRES_DB=agent-portal \
  -p 5432:5432 \
  postgres:15