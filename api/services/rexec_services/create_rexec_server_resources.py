import os
import time
import yaml
import packaging.requirements
import packaging.specifiers
import subprocess
import re
import hashlib
from pathlib import Path
from kubernetes import client, config

def get_kubeconfig_path() -> str:
    """
    Determine the path to the kubeconfig file, prioritizing environment variables and mounted paths.
    Falls back to a default location if not found.
    """
    # Check if KUBECONFIG environment variable is set
    kubeconfig_from_env = os.environ.get("KUBECONFIG")
    print(f"KUBECONFIG environment variable: {kubeconfig_from_env}")
    if kubeconfig_from_env and os.path.exists(kubeconfig_from_env):
        # with open(kubeconfig_from_env, "r") as f: print(f.read()) # Debug print
        return kubeconfig_from_env

    # Default path inside the Docker container (mounted from env_variables)
    default_kubeconfig_path = "/code/env_variables/.kubeconfig"  # Adjust filename if necessary (e.g., "kubeconfig" or "config")

    if os.path.exists(default_kubeconfig_path):
        return default_kubeconfig_path

    # If not found, raise an exception or log a warning
    raise FileNotFoundError(
        f"Kubeconfig file not found at {default_kubeconfig_path}. "
        "Please ensure the file exists in the env_variables folder and is mounted correctly in the Docker container, "
        "or set the KUBECONFIG environment variable."
    )

# Load kubeconfig (assumes service runs with cluster access)
# Specify the custom kubeconfig path
kubeconfig_path = get_kubeconfig_path()

def load_kubeconfig(kubeconfig_path):
    try:
        config.load_kube_config(config_file=kubeconfig_path)
        # config.load_kube_config() # Load default kubeconfig
    except Exception as e:
        print(f"Attempting to load kubeconfig from: {kubeconfig_path}")
        raise Exception(f"Failed to load kubeconfig: {e}")

load_kubeconfig(kubeconfig_path)
api_client = client.ApiClient()
v1_api = client.CoreV1Api(api_client)
apps_v1_api = client.AppsV1Api(api_client)
networking_v1_api = client.NetworkingV1Api(api_client)
rbac_v1_api = client.RbacAuthorizationV1Api(api_client)

def load_yaml_file(file_path):
    """
    Load a YAML file and return a list of its contents (supports multi-document YAML).
    """
    with open(file_path, 'r') as f:
        return list(yaml.safe_load_all(f))
    
def namespace_exists(namespace):
    v1_api = client.CoreV1Api()
    try:
        v1_api.read_namespace(name=namespace)
        return True
    except client.exceptions.ApiException as e:
        if e.status == 404:
            return False
        else:
            raise e
        
def get_cluster_ip(service_name, namespace="default"):
    v1_api = client.CoreV1Api()
    try:
        service = v1_api.read_namespaced_service(name=service_name, namespace=namespace)
        return service.spec.cluster_ip
    except client.exceptions.ApiException as e:
        raise e
    
def check_deployment_label_match(label_selector, namespace="default"):
    apps_v1 = client.AppsV1Api(api_client)
    try:
        deployments = apps_v1.list_namespaced_deployment(namespace, label_selector=label_selector)
    except client.exceptions.ApiException as e:
        raise e
    if deployments.items:
        return True
    else:
        return False

def wait_for_namespace(api_instance, namespace, timeout=60):
    """
    Wait until the specified namespace is available.
    """
    print(f"Waiting for namespace '{namespace}' to be available...")
    start_time = time.time()
    while True:
        try:
            api_instance.read_namespace(name=namespace)
            print(f"Namespace '{namespace}' is ready")
            return True
        except client.ApiException as e:
            if e.status == 404:
                if time.time() - start_time > timeout:
                    raise Exception(f"Timeout waiting for namespace '{namespace}' to be created")
                time.sleep(1)
            else:
                raise e

def apply_manifest(api_client, manifest, namespace=None):
    """
    Apply a Kubernetes manifest using the appropriate API.
    """
    if manifest is None:
        return
    kind = manifest.get('kind')
    api_version = manifest.get('apiVersion')
    metadata = manifest.get('metadata', {})
    name = metadata.get('name')

    print(f"Applying {kind} '{name}'...")

    if kind == 'Namespace':
        v1_api = client.CoreV1Api(api_client)
        v1_api.create_namespace(body=manifest)
    elif kind == 'Deployment':
        apps_v1 = client.AppsV1Api(api_client)
        apps_v1.create_namespaced_deployment(namespace=namespace, body=manifest)
    elif kind == 'Service':
        v1 = client.CoreV1Api(api_client)
        v1.create_namespaced_service(namespace=namespace, body=manifest)
    elif kind == 'ConfigMap':
        v1 = client.CoreV1Api(api_client)
        v1.create_namespaced_config_map(namespace=namespace, body=manifest)
    elif kind == 'Role':
        rbac_v1 = client.RbacAuthorizationV1Api(api_client)
        rbac_v1.create_namespaced_role(namespace=namespace, body=manifest)
    elif kind == 'RoleBinding':
        rbac_v1 = client.RbacAuthorizationV1Api(api_client)
        rbac_v1.create_namespaced_role_binding(namespace=namespace, body=manifest)
    elif kind == 'Ingress':
        networking_v1 = client.NetworkingV1Api(api_client)
        networking_v1.create_namespaced_ingress(namespace=namespace, body=manifest)
    elif kind == 'NetworkPolicy':
        networking_v1 = client.NetworkingV1Api(api_client)
        networking_v1.create_namespaced_network_policy(namespace=namespace, body=manifest)
    else:
        print(f"Skipping unsupported kind: {kind}")
        return

    print(f"Successfully applied {kind} '{name}'")

def get_loadbalancer_url(networking_api_instance, api_instance, namespace, ingress_name, 
                         service_name="nginx-ingress-ingress-nginx-controller", 
                         ingress_namespace="ingress-nginx", timeout=300):
    
    # Try to retrieve the domain from the Ingress with retries
    domain = None
    retries = 5
    delay = 2
    print(f"Attempting to retrieve domain from Ingress '{ingress_name}' in namespace '{namespace}'...")
    for attempt in range(retries):
        try:
            ingress = networking_api_instance.read_namespaced_ingress(name=ingress_name, namespace=namespace)
            domain = ingress.spec.rules[0].host if ingress.spec.rules else None
            if domain:
                print(f"Retrieved domain '{domain}' from Ingress '{ingress_name}'")
                break
            print(f"No host found in Ingress '{ingress_name}' on attempt {attempt + 1}/{retries}")
        except client.ApiException as e:
            print(f"Attempt {attempt + 1}/{retries} failed to retrieve Ingress '{ingress_name}': {e}")
        time.sleep(delay)
    
    if domain:
        # Use the domain from Ingress with HTTPS
        url = f"https://{domain}/{namespace}"
        print(f"Access URL is: {url}")
        return url
    
    # Fallback to LoadBalancer IP if no domain is retrieved
    print(f"Failed to retrieve domain after {retries} attempts. Waiting for LoadBalancer endpoint for service '{service_name}' in namespace '{ingress_namespace}'...")
    start_time = time.time()
    while True:
        try:
            service = api_instance.read_namespaced_service(name=service_name, namespace=ingress_namespace)
            if service.status.load_balancer.ingress:
                ingress = service.status.load_balancer.ingress[0]
                if ingress.hostname:
                    endpoint = ingress.hostname
                elif ingress.ip:
                    endpoint = ingress.ip
                else:
                    raise Exception(f"No valid IP or hostname found in LoadBalancer ingress for '{service_name}'")
                url = f"http://{endpoint}/{namespace}"
                print(f"LoadBalancer URL is ready: {url}")
                return url
            if time.time() - start_time > timeout:
                raise Exception(f"Timeout waiting for LoadBalancer endpoint for '{service_name}' in '{ingress_namespace}'")
            time.sleep(5)
        except client.ApiException as e:
            if e.status == 404:
                raise Exception(f"Service '{service_name}' not found in namespace '{ingress_namespace}'")
            else:
                raise e

def create_rexec_server_resources(group_id: str, user_id: str, requirements: list[str]) -> str:
    """
    Create all Kubernetes resources for a user's rexec server instance in a unique namespace.
    """
    # Refresh k8s token everytime call this function
    load_kubeconfig(kubeconfig_path)
    # Check if namespace(group) exists
    # If not, generate unique namespace
    print(f'group id: {group_id} passed to create_rexec_server_resources')
    namespace = f"rexec-server-{group_id}"

    ns_exist = namespace_exists(namespace)
    if not ns_exist:
        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": namespace}
        }
        print("DEBUG01")
        try:
            apply_manifest(api_client, namespace_manifest)
            print("DEBUG02")
        except client.ApiException as e:
            print("DEBUG03")
            raise e
    print("DEBUG00")
    # Extract Python version
    user_requirements = []
    for line in requirements:
        req = packaging.requirements.Requirement(line)
        if req.name == "python":
            python_version = packaging.specifiers.Specifier(req.specifier.__str__()).version
        else:
            user_requirements.append(line)
    user_requirements_str = ' '.join(user_requirements)

    # Calculate SHA-1 digest of the user-provided requirements
    digest_list = user_requirements.copy()
    digest_list.sort()
    digest_list.insert(0, f"python=={python_version}")
    digest_list_str = ' '.join(digest_list)
    digest_list_bstr = digest_list_str.encode('utf-8')
    digest = hashlib.sha1(digest_list_bstr).hexdigest()

    print("DEBUG0")
    if ns_exist:
        digest_exist = check_deployment_label_match(f"digest={digest}", namespace)
        if digest_exist:
            print("remote execution server instance with user-provided requirements exists.")
            return "remote execution server instance with user-provided requirements exists."

    # Read RExec server builtin requirements
    rexec_server_repo_dir = Path(__file__).parent / "SciDx_rexec_server"
    builtin_requirements = []
    with open(rexec_server_repo_dir.joinpath("requirements.txt"), 'r') as fd:
        for line in fd:
            req_str = line.strip()
            if not req_str or req_str == '' or req_str.startswith('#'):
                continue
            else:
                try:
                    req = packaging.requirements.Requirement(req_str)
                except packaging.requirements.InvalidRequirement:
                    print(f"{req_str} does not conform to the specification of dependency specifiers!")
                    raise
                else:
                    builtin_requirements.append(req_str)
    builtin_requirements_str = ' '.join(builtin_requirements)

    # Define base directory for manifests
    manifest_dir = Path(__file__).parent / "k8s"
    manifests = load_yaml_file(manifest_dir.joinpath("rexec-server-deployment.yaml"))

    broker_addr = get_cluster_ip("rexec-broker-internal-ip", "rexec-broker") # check ns

    # Wait for namespace to be ready
    if not ns_exist:
        wait_for_namespace(v1_api, namespace)
        print(f'namespace : {namespace} created in create_rexec_server_resources')

    # Apply each manifest with namespace substitution
    for manifest in manifests:
        if manifest:
            for container in manifest["spec"]["template"]["spec"]["containers"]:
                if container["name"] == "rexec-server":
                    manifest["metadata"]["labels"]["digest"] = digest
                    container["image"] = f"python:{python_version}"
                    cmd_str = (container["command"][-1]
                                .replace("${builtin_requirements}", builtin_requirements_str)
                                .replace("${user_requirements}", user_requirements_str)
                                .replace("${broker_addr}", broker_addr)
                                .replace("${broker_port}", "5560"))
                    container["command"][-1] = cmd_str
            
            manifest["metadata"]["namespace"] = namespace
            apply_manifest(api_client, manifest, namespace)

    return "remote execution server instance created for user."