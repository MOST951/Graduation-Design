#!/bin/bash

# Exit on error
set -e

# Build and push the backend image
docker build -t your-repo/weibo-backend:latest -f deployment/docker/Dockerfile.backend .
docker push your-repo/weibo-backend:latest

# Build and push the frontend image
docker build -t your-repo/weibo-frontend:latest -f deployment/docker/Dockerfile.frontend .
docker push your-repo/weibo-frontend:latest
