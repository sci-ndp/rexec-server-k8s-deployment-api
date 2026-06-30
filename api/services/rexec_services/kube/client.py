"""
Kubernetes client construction and kubeconfig resolution for Rexec services.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from kubernetes import client, config
from kubernetes.client import ApiClient

from api.config.rexec_settings import RexecSettings

from ..exceptions import RexecConfigurationError


@dataclass
class KubernetesClients:
    """Typed container for the Kubernetes API clients we interact with."""

    api_client: ApiClient
    core_v1: client.CoreV1Api
    apps_v1: client.AppsV1Api
    networking_v1: client.NetworkingV1Api
    rbac_v1: client.RbacAuthorizationV1Api


def resolve_kubeconfig_path(settings: RexecSettings) -> str | None:
    """
    Resolve the kubeconfig path, preferring the mounted path inside the container
    and falling back to a host-local path for non-container execution.
    """
    if settings.use_in_cluster_config:
        return None

    candidates: List[str] = []

    if settings.kubeconfig_mount_path:
        candidates.append(settings.kubeconfig_mount_path)
        print(f"kubeconfig mount path: {settings.kubeconfig_mount_path}")

    if settings.kubeconfig_local_path:
        candidates.append(settings.kubeconfig_local_path)
        print(f"kubeconfig local path: {settings.kubeconfig_local_path}")

    for candidate in candidates:
        candidate_path = Path(candidate).expanduser()
        if candidate_path.exists():
            print(f"Using kubeconfig path: {candidate_path}")
            return str(candidate_path)

    raise RexecConfigurationError(
        "Kubeconfig file not found. Set 'REXEC_KUBECONFIG_MOUNT_PATH' for the "
        "in-container path or 'REXEC_KUBECONFIG_LOCAL_PATH' for the host path, "
        "or enable 'REXEC_USE_IN_CLUSTER_CONFIG=true'."
    )


def load_kubernetes_clients(
    kubeconfig_path: str | None,
    *,
    use_in_cluster_config: bool,
) -> KubernetesClients:
    """Load Kubernetes configuration and initialize client instances."""
    try:
        if use_in_cluster_config:
            config.load_incluster_config()
        else:
            if not kubeconfig_path:
                raise RexecConfigurationError(
                    "Kubeconfig path is required unless in-cluster config is enabled."
                )
            config.load_kube_config(config_file=kubeconfig_path)
    except Exception as exc:  # noqa: BLE001 - preserve original error context
        raise RexecConfigurationError(
            f"Failed to load Kubernetes config: {exc}"
        ) from exc

    api_client = client.ApiClient()
    return KubernetesClients(
        api_client=api_client,
        core_v1=client.CoreV1Api(api_client),
        apps_v1=client.AppsV1Api(api_client),
        networking_v1=client.NetworkingV1Api(api_client),
        rbac_v1=client.RbacAuthorizationV1Api(api_client),
    )


def get_kubernetes_clients(settings: RexecSettings) -> KubernetesClients:
    """Resolve the kubeconfig and build the Kubernetes API clients in one step."""
    kubeconfig_path = resolve_kubeconfig_path(settings)
    return load_kubernetes_clients(
        kubeconfig_path,
        use_in_cluster_config=settings.use_in_cluster_config,
    )
