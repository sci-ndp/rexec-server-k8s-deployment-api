# SciDx Remote Execution Server Deployment API
RESTful API for automated deployment and management of Remote Execution server environments on Kubernetes clusters in [SciDx software stack](https://scidx.sci.utah.edu/) with the support to [DataSpaces](https://dataspaces.sci.utah.edu/) Data Staging framework. It provides a unified interface to provision, configure, and manage remote execution infrastructure across distributed computing environments.

## Requirements
* Docker and Docker Compose
* Kubernetes cluster access
* Kubernetes configuration file (`.kubeconfig`)
* Python __>=3.9__ (for development)

## Usage
### Quick Start
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

### API Endpoints
Once running, access:
- **Swagger UI**: http://localhost:8001/docs
- **Health Check**: http://localhost:8001/health

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

## Configuration
- **Port**: 8001 (host) → 8000 (container)
- **Kubeconfig**: Mount your config to `env_variables/.kubeconfig`
- **Environment**: Set via docker-compose environment variables

## K8s Deployment
The API automatically provisions remote execution server resources including:
- Deployment configurations
- Service definitions
- Resource management
- Network policies

## License
This project is licensed under the [Apache License 2.0](LICENSE).
