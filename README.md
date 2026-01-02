# SciDx Remote Execution Deployment API
FastAPI service for provisioning user-scoped SciDx Rexec servers on a Kubernetes cluster. The API creates namespaces, deploys the Rexec server pod with user-specified requirements, and returns broker connection details for remote execution clients.

## Prerequisites
* Python __>=3.10__
* Docker and Docker Compose (for local development)
* Access to a Kubernetes cluster via kubeconfig with permissions to create namespaces, deployments, services, and network policies



## Installation
### Configure environment
```
cp example.env .env
```
Edit `.env` to set your kubeconfig paths and broker service details.
```
vi .env
```
For details and examples, [click to see the `.env settings` section below](#env-settings)



### Run locally with Docker Compose
```
docker compose up --build -d
```
The compose file binds your kubeconfig into the container, reloads on code changes.


### Access the API Swagger UI
`http://localhost:8000/docs`


<br>

## .env settings

Goal: fill `/.env`. <br>
Prepare these first:
   1. `REXEC_KUBECONFIG_LOCAL_PATH`, path to your target kubeconfig file on the host machine;
   2. `REXEC_KUBECONFIG_MOUNT_PATH`, path inside the container where the kubeconfig is mounted (e.g., /home/appuser/.kube/config); Leave it as is if using Docker Compose, otherwise ensure Dockerfile and container run command mount the same path.

If `ENABLE_GROUP_BASED_ACCESS` is set to `True`, also prepare:
>**IMPORTANT**: 
> if you enable group-based access control, ensure your AUTH_API_URL is set up as the same as the `NDP Endpoint API`; also the group name should match those defined in `NDP Endpoint API`.
   1. `AUTH_API_URL`: authentication endpoint for bearer token validation.
   2. `GROUP_NAMES`: comma-separated list of allowed groups for write operations.

Left defaults can be used for the rest:
- `REXEC_NAMESPACE_PREFIX`: prefix applied to per-user namespaces (default `rexec-server-`).
- `REXEC_BROKER_SERVICE_NAME` / `REXEC_BROKER_NAMESPACE` / `REXEC_BROKER_PORT`: service discovery for the broker inside the cluster; `REXEC_BROKER_EXTERNAL_SERVICE_NAME` enables NodePort lookup.


Example:
```bash
# ==============================================
# Rexec Provisioning Configuration
# ==============================================

# Path to the kubeconfig on the host
# Example: REXEC_KUBECONFIG_LOCAL_PATH=~/.kube/config
REXEC_KUBECONFIG_LOCAL_PATH=

# Path to the kubeconfig inside the container (should match the bind mount)
REXEC_KUBECONFIG_MOUNT_PATH=/home/appuser/.kube/config

# Prefix applied to namespaces created for Rexec users
REXEC_NAMESPACE_PREFIX=rexec-server-

# Service discovery values for the Rexec broker running in the cluster
REXEC_BROKER_SERVICE_NAME=rexec-broker-internal-ip
REXEC_BROKER_NAMESPACE=rexec-broker
REXEC_BROKER_PORT=5560



# ==============================================
# Authentication Configuration
# ==============================================

# URL for the authentication API to retrieve user information
# This endpoint is used to validate tokens and fetch user details
AUTH_API_URL=https://idp.nationaldataplatform.org/temp/information



# ==============================================
# ACCESS CONTROL (Optional)
# ==============================================
# Group-based access control restricts write operations (POST, PUT, DELETE)
# to users belonging to specific groups. GET endpoints remain public.
#
# How it works:
# 1. User authenticates with Bearer token
# 2. API validates token against AUTH_API_URL and retrieves user's groups
# 3. If ENABLE_GROUP_BASED_ACCESS=True, checks if user belongs to any group in GROUP_NAMES
# 4. Access granted only if user's groups overlap with GROUP_NAMES
#
# Group matching is case-insensitive (e.g., "Admins" matches "admins")

# Enable group-based access control (True/False)
ENABLE_GROUP_BASED_ACCESS=False

# Comma-separated list of allowed groups for write operations
# Example: GROUP_NAMES=admins,developers,data-managers
# If empty and ENABLE_GROUP_BASED_ACCESS=True, all write operations will be denied
GROUP_NAMES=
```

[Back to `Configure environment`](#configure-environment)



## License
This project is licensed under the [Apache License 2.0](LICENSE).
