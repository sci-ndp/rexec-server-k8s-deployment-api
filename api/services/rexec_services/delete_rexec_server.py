"""
Teardown of a user-scoped Rexec server on Kubernetes.
"""

from __future__ import annotations

from api.config.rexec_settings import RexecSettings, rexec_settings

from .kube import delete_namespace, get_kubernetes_clients, namespace_exists


def delete_rexec_server_resources(
    user_id: str,
    *,
    settings: RexecSettings | None = None,
) -> str:
    """
    Delete the Kubernetes resources for a user's dedicated Rexec server.

    Removes the user's namespace, which cascades to the Deployment, Service,
    and any other resources created during provisioning. Idempotent: a missing
    namespace is reported as "no server found" rather than an error.
    """
    resolved_settings = settings or rexec_settings
    clients = get_kubernetes_clients(resolved_settings)

    namespace = f"{resolved_settings.namespace_prefix}{user_id}"

    if not namespace_exists(clients, namespace):
        return f"No remote execution server found for user: {user_id}"

    delete_namespace(clients, namespace)
    return f"Remote Execution server deleted for user: {user_id}"
