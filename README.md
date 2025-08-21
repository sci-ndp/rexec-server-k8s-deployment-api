# rexec deployment api

RESTful API for setting up Remote Execution environment on Kubernetes clusters.

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Kubernetes configuration file (`.kubeconfig`)

### Setup

1. **Clone and navigate to the project**
   ```bash
   git clone https://github.com/bozhang-hpc/rexec-server-k8s-deployment-api.git
   cd rexec-server-k8s-deployment-api
   ```

2. **Add your Kubernetes config**
   ```bash
   cp ~/.kube/config env_variables/.kubeconfig
   ```

3. **Start the API**
   ```bash
   make run
   ```

   The API will be available at: http://localhost:8001

### Alternative Commands

```bash
# Build only
make build

# Run with docker-compose directly
docker-compose up --build

# Stop the API
make stop

# Clean up containers and images
make clean
```

## API Documentation

Once running, visit:
- **Swagger UI**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

## Configuration

- **Port**: 8001 (host) → 8000 (container)
- **Kubeconfig**: Mount your config to `env_variables/.kubeconfig`
- **Environment**: Set via docker-compose environment variables

## Development

The API is built with:
- FastAPI
- Uvicorn
- Kubernetes Python client

## Troubleshooting

1. **Port already in use**: Change port mapping in `docker-compose.yml`
2. **Kubeconfig not found**: Ensure `.kubeconfig` exists in `env_variables/`
3. **Permission issues**: Check file ownership and Docker permissions
