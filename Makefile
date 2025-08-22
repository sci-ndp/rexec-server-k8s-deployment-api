.PHONY: build run stop clean

# Docker image name
IMAGE_NAME := rexec-k8s-deployment-api
TAG := latest

# Build and run
build:
	docker-compose build

run:
	docker-compose up --build

# Stop container
stop:
	docker-compose down

# Clean up
clean:
	docker-compose down --rmi all --volumes --remove-orphans
# 	docker system prune -f
