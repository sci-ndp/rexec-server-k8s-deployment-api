"""
Low-level Kubernetes resource operations shared by the Rexec services.
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import List, Tuple

import yaml
from kubernetes import client
from kubernetes.client import exceptions as k8s_exceptions

from ..exceptions import (
    RexecConfigurationError,
    RexecDeploymentConflictError,
    RexecDeploymentError,
)
from .client import KubernetesClients


def load_yaml_documents(file_path: Path) -> List[dict]:
    """Load one or more YAML documents from a path."""
    if not file_path.exists():
        raise RexecConfigurationError(f"Manifest file not found: {file_path}")

    with file_path.open("r", encoding="utf-8") as handle:
        return [doc for doc in yaml.safe_load_all(handle) if doc]


def namespace_exists(clients: KubernetesClients, namespace: str) -> bool:
    """Check whether the requested namespace already exists."""
    try:
        clients.core_v1.read_namespace(name=namespace)
        return True
    except k8s_exceptions.ApiException as exc:
        if exc.status == 404:
            return False
        raise RexecDeploymentError(
            f"Failed to read namespace '{namespace}': {exc}"
        ) from exc


def wait_for_namespace(
    clients: KubernetesClients,
    namespace: str,
    timeout_seconds: int,
) -> None:
    """Poll until the namespace is available or the timeout expires."""
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if namespace_exists(clients, namespace):
            return
        time.sleep(1)
    raise RexecDeploymentError(
        f"Timeout waiting for namespace '{namespace}' to be created"
    )


def apply_manifest(
    clients: KubernetesClients,
    manifest: dict,
    namespace: str,
    force: bool = False,
) -> str | None:
    """
    Apply a namespace-scoped manifest, handling AlreadyExists conflicts gracefully.

    A Deployment conflict is treated differently from every other kind: since a
    same-digest respawn is already short-circuited before this is called (see
    deployment_with_digest_exists), a 409 here can only mean a Deployment with
    *different* requirements is already running. Replacing it restarts the pod
    and interrupts any job it was running, so that only happens when the caller
    explicitly opts in via `force`; otherwise this raises RexecDeploymentConflictError
    so the caller can decide, instead of the old behavior of silently reporting
    "created" while leaving the running pod untouched.

    Returns "created" or "replaced" for a Deployment (so the caller can report
    which happened); None for every other kind.
    """
    kind = manifest.get("kind")
    metadata = manifest.get("metadata", {})
    name = metadata.get("name", "<unknown>")

    try:
        if kind == "Namespace":
            clients.core_v1.create_namespace(body=manifest)
        elif kind == "Deployment":
            try:
                clients.apps_v1.create_namespaced_deployment(
                    namespace=namespace,
                    body=manifest,
                )
                return "created"
            except k8s_exceptions.ApiException as exc:
                if exc.status != 409:
                    raise
                if not force:
                    raise RexecDeploymentConflictError(
                        f"A Deployment '{name}' with different requirements is "
                        f"already running in namespace '{namespace}'. Pass "
                        f"force=True to replace it (this interrupts any job it "
                        f"is currently running)."
                    ) from exc
                existing = clients.apps_v1.read_namespaced_deployment(
                    name=name, namespace=namespace,
                )
                manifest["metadata"]["resourceVersion"] = (
                    existing.metadata.resource_version
                )
                clients.apps_v1.replace_namespaced_deployment(
                    name=name, namespace=namespace, body=manifest,
                )
                return "replaced"
        elif kind == "Service":
            clients.core_v1.create_namespaced_service(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "ConfigMap":
            clients.core_v1.create_namespaced_config_map(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "Role":
            clients.rbac_v1.create_namespaced_role(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "RoleBinding":
            clients.rbac_v1.create_namespaced_role_binding(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "Ingress":
            clients.networking_v1.create_namespaced_ingress(
                namespace=namespace,
                body=manifest,
            )
        elif kind == "NetworkPolicy":
            clients.networking_v1.create_namespaced_network_policy(
                namespace=namespace,
                body=manifest,
            )
        else:
            raise RexecDeploymentError(f"Unsupported manifest kind: {kind}")
    except k8s_exceptions.ApiException as exc:
        if exc.status == 409:  # AlreadyExists
            return
        raise RexecDeploymentError(
            f"Failed to apply {kind} '{name}': {exc}"
        ) from exc


def delete_namespace(clients: KubernetesClients, namespace: str) -> None:
    """
    Delete a namespace and, by cascade, every resource it contains.

    Idempotent: a missing namespace (404) is treated as already deleted.
    """
    try:
        clients.core_v1.delete_namespace(
            name=namespace,
            body=client.V1DeleteOptions(propagation_policy="Background"),
        )
    except k8s_exceptions.ApiException as exc:
        if exc.status == 404:  # Already gone
            return
        raise RexecDeploymentError(
            f"Failed to delete namespace '{namespace}': {exc}"
        ) from exc


def get_nodeport_endpoint(
    clients: KubernetesClients,
    service_name: str,
    namespace: str,
) -> Tuple[str | None, int | None]:
    """
    Retrieve an externally reachable host and NodePort for a service.
    """
    try:
        service = clients.core_v1.read_namespaced_service(
            name=service_name,
            namespace=namespace,
        )
    except k8s_exceptions.ApiException as exc:
        raise RexecDeploymentError(
            f"Failed to fetch service '{service_name}' in namespace '{namespace}': {exc}"
        ) from exc

    node_port: int | None = None
    host: str | None = None

    for port in service.spec.ports or []:
        if port.node_port:
            node_port = port.node_port
            break

    try:
        nodes = clients.core_v1.list_node().items
    except k8s_exceptions.ApiException as exc:
        raise RexecDeploymentError(
            f"Failed to list cluster nodes for NodePort host resolution: {exc}"
        ) from exc

    for node in nodes:
        addresses = node.status.addresses or []
        # Prefer ExternalIP/InternalIP, otherwise take the first available address
        host = next(
            (
                addr.address
                for addr in addresses
                if addr.type in ("ExternalIP", "InternalIP")
            ),
            host,
        )
        if not host and addresses:
            host = addresses[0].address
        if host:
            break

    return host, node_port


def deployment_with_digest_exists(
    clients: KubernetesClients,
    namespace: str,
    digest: str,
) -> bool:
    """Determine if a deployment already exists with the provided digest label."""
    try:
        deployments = clients.apps_v1.list_namespaced_deployment(
            namespace=namespace,
            label_selector=f"digest={digest}",
        )
    except k8s_exceptions.ApiException as exc:
        raise RexecDeploymentError(
            f"Failed to list deployments in namespace '{namespace}': {exc}"
        ) from exc

    return bool(deployments.items)
