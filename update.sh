#!/bin/bash

echo "Pulling latest image..."
docker pull jangwanko/newnetflix:latest

echo "Stopping old container..."
docker stop newnetflix || true
docker rm newnetflix || true

echo "Starting new container..."
docker run -d \
  --name newnetflix \
  --env-file /home/ubuntu/.env \
  -p 8000:8000 \
  jangwanko/newnetflix:latest