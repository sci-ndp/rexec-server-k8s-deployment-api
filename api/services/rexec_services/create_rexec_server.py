"""
Provisioning of a user-scoped Rexec server on Kubernetes.
"""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Iterable, Sequence

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
    builtin_requirements: Sequence[str],
    user_requirements: Sequence[str],
    broker_addr: str,
    user_id: str,
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
    containers = pod_spec.setdefault("containers", [])

    builtin_requirements_str = " ".join(builtin_requirements)
    user_requirements_str = " ".join(user_requirements)

    for container in containers:
        if container.get("name") != settings.container_name:
            continue

        # Set the container image to the specified Python version
        container["image"] = f"python:{python_version}"

        # Set environment variable for user_id; for identifying user-specific server
        env = container.setdefault("env", [])
        if not any(item.get("name") == "REXEC_USER_ID" for item in env):
            env.append({"name": "REXEC_USER_ID", "value": user_id})

        command = container.get("command")
        if command and isinstance(command, list) and command:
            command[-1] = (
                command[-1]
                .replace("${builtin_requirements}", builtin_requirements_str)
                .replace("${user_requirements}", user_requirements_str)
                .replace("${broker_addr}", broker_addr)
                .replace("${broker_port}", str(settings.broker_port))
            )

    return manifest


def create_rexec_server_resources(
    group_id: str,
    user_id: str,
    requirements: Iterable[str],
    *,
    settings: RexecSettings | None = None,
) -> str:
    """
    Create the Kubernetes resources required for a user's dedicated Rexec server.
    """
    resolved_settings = settings or rexec_settings
    clients = get_kubernetes_clients(resolved_settings)

    namespace = f"{resolved_settings.namespace_prefix}{user_id}"

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

    python_version, user_requirements = parse_requirements(requirements)

    digest_components = sorted(user_requirements)
    digest_components.insert(0, f"python=={python_version}")
    digest = hashlib.sha1(" ".join(digest_components).encode("utf-8")).hexdigest()

    if namespace_present and deployment_with_digest_exists(clients, namespace, digest):
        return "remote execution server instance with user-provided requirements exists."

    builtin_requirements = load_builtin_requirements()

    manifest_dir = Path(__file__).parent / "manifests"
    deployment_manifests = load_yaml_documents(
        manifest_dir / resolved_settings.deployment_manifest_name
    )

    broker_addr = (
        f"{resolved_settings.broker_service_name}"
        f".{resolved_settings.broker_namespace}"
        f".svc.cluster.local"
    )

    # Patch the Deployment(./manifests/rexec-server-deployment.yaml) manifests with dynamic values
    for manifest in deployment_manifests:
        if manifest.get("kind") == "Deployment":
            manifest = _prepare_deployment_manifest(
                manifest,
                namespace,
                digest,
                python_version,
                builtin_requirements,
                user_requirements,
                broker_addr,
                user_id,
                resolved_settings,
            )
        else:
            manifest.setdefault("metadata", {})["namespace"] = namespace

        apply_manifest(clients, manifest, namespace=namespace)

    return f"Remote Execution server created for user: {user_id}"
