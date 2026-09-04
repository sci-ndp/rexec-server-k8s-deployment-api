"""
Provisioning of a user-scoped Rexec server on Kubernetes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable

from api.config.rexec_settings import RexecSettings, rexec_settings

from .kube import (
    apply_manifest,
    deployment_with_digest_exists,
    get_kubernetes_clients,
    load_yaml_documents,
    namespace_exists,
    wait_for_namespace,
)
from .requirements_parser import load_builtin_requirements, parse_requirements


def _prepare_deployment_manifest(
    manifest: dict,
    namespace: str,
    digest: str,
    python_version: str,
    broker_addr: str,
    user_id: str,
    configmap_name: str,
    settings: RexecSettings,
) -> dict:
    """
    Mutate a deployment manifest in-place with namespace, labels, image, and env vars
    """
    manifest.setdefault("metadata", {})
    manifest["metadata"]["namespace"] = namespace

    labels = manifest["metadata"].setdefault("labels", {})
    labels["digest"] = digest

    spec = manifest.setdefault("spec", {})
    template = spec.setdefault("template", {})
    template_metadata = template.setdefault("metadata", {})
    template_metadata.setdefault("labels", {})["digest"] = digest

    pod_spec = template.setdefault("spec", {})

    for volume in pod_spec.get("volumes", []):
        if volume.get("name") == "requirements":
            volume.setdefault("configMap", {})["name"] = configmap_name

    containers = pod_spec.setdefault("containers", [])

    for container in containers:
        if container.get("name") != settings.container_name:
            continue

        # Set the container image to the specified Python version
        container["image"] = f"python:{python_version}"

        # Set environment variable for user_id; for identifying user-specific server
        env = container.setdefault("env", [])
        if not any(item.get("name") == "REXEC_USER_ID" for item in env):
            env.append({"name": "REXEC_USER_ID", "value": user_id})

        container["resources"] = {
            "requests": {
                "cpu": settings.container_cpu_request,
                "memory": settings.container_memory_request,
                "ephemeral-storage": settings.container_ephemeral_storage_request,
            },
            "limits": {
                "cpu": settings.container_cpu_limit,
                "memory": settings.container_memory_limit,
                "ephemeral-storage": settings.container_ephemeral_storage_limit,
            },
        }

        command = container.get("command")
        if command and isinstance(command, list) and command:
            command[-1] = (
                command[-1]
                .replace("${broker_addr}", broker_addr)
                .replace("${broker_port}", str(settings.broker_port))
            )

    return manifest


def create_rexec_server_resources(
    group_id: str,
    user_id: str,
    requirements: Iterable[str],
    *,
    force: bool = False,
    settings: RexecSettings | None = None,
) -> str:
    """
    Create the Kubernetes resources required for a user's dedicated Rexec server.
    """
    resolved_settings = settings or rexec_settings
    clients = get_kubernetes_clients(resolved_settings)

    namespace = f"{resolved_settings.namespace_prefix}{user_id}"
    
    # Check if the namespace already exists
    # If not, create it
    namespace_present = namespace_exists(clients, namespace)
    if not namespace_present:
        namespace_manifest = {
            "apiVersion": "v1",
            "kind": "Namespace",
            "metadata": {"name": namespace},
        }
        apply_manifest(clients, namespace_manifest, namespace=namespace)
        wait_for_namespace(
            clients,
            namespace,
            resolved_settings.namespace_wait_timeout_seconds,
        )

    # Parse the user input requirements 
    # to separate the Python version from other packages and validate them
    python_version, user_requirements = parse_requirements(requirements)

    # Compute a digest of the requirements to uniquely identify this server config
    digest_components = sorted(user_requirements)
    digest_components.insert(0, f"python=={python_version}")
    digest = hashlib.sha1(" ".join(digest_components).encode("utf-8")).hexdigest()

    # Check if a deployment with the same requirements already exists
    # If it does, return a message indicating that the server already exists
    if namespace_present and deployment_with_digest_exists(clients, namespace, digest):
        return (
            f"No changes: a Rexec server with these exact requirements is "
            f"already running for user {user_id}."
        )

    builtin_requirements = load_builtin_requirements()

    # Requirements are shipped to the pod as a mounted file
    # rather than interpolated into a shell command
    configmap_name = f"rexec-server-requirements-{digest[:12]}"
    requirements_content = "\n".join([*builtin_requirements, *user_requirements]) + "\n"
    configmap_manifest = {
        "apiVersion": "v1",
        "kind": "ConfigMap",
        "metadata": {"name": configmap_name, "namespace": namespace},
        "data": {"requirements.txt": requirements_content},
    }
    # Apply the ConfigMap manifest for the requirements to the cluster
    apply_manifest(clients, configmap_manifest, namespace=namespace)

    manifest_dir = Path(__file__).parent / "manifests"
    deployment_manifests = load_yaml_documents(
        manifest_dir / resolved_settings.deployment_manifest_name
    )

    # Retrieve the broker address from environment set in rexec_settings.py
    broker_addr = (
        f"{resolved_settings.broker_service_name}"
        f".{resolved_settings.broker_namespace}"
        f".svc.cluster.local"
    )

    # Patch the Deployment(./manifests/rexec-server-deployment.yaml) manifests with dynamic values
    deployment_outcome: str | None = None
    for manifest in deployment_manifests:
        if manifest.get("kind") == "Deployment":
            manifest = _prepare_deployment_manifest(
                manifest,
                namespace,
                digest,
                python_version,
                broker_addr,
                user_id,
                configmap_name, # input requirements cm
                resolved_settings,
            )
            deployment_outcome = apply_manifest(
                clients, manifest, namespace=namespace, force=force,
            )
        else:
            manifest.setdefault("metadata", {})["namespace"] = namespace
            apply_manifest(clients, manifest, namespace=namespace)

    if deployment_outcome == "replaced":
        return (
            f"Rexec server for user {user_id} was replaced with the new "
            f"requirements; the job it was previously running was interrupted."
        )
    return f"Remote Execution server created for user: {user_id}"
