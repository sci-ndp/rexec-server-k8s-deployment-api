"""
Broker connection details for remote execution clients.
"""

from __future__ import annotations

from api.config.rexec_settings import RexecSettings, rexec_settings

from .kube import get_kubernetes_clients, get_nodeport_endpoint


def get_rexec_broker_config(
    *,
    settings: RexecSettings | None = None,
) -> dict:
    """
    Retrieve broker connection details for an externally reachable broker endpoint.
    """
    resolved_settings = settings or rexec_settings
    clients = get_kubernetes_clients(resolved_settings)

    external_host: str | None = resolved_settings.broker_external_host
    external_port: int | None = resolved_settings.broker_external_port

    if not external_host or not external_port:
        svc_name = resolved_settings.broker_external_service_name
        if svc_name:
            host, node_port = get_nodeport_endpoint(
                clients,
                svc_name,
                resolved_settings.broker_namespace,
            )
            external_host = external_host or host
            external_port = external_port or node_port

    external_url = None
    if external_host and external_port:
        external_url = f"{external_host}:{external_port}"

    return {
        "broker_external_host": external_host,
        "broker_external_port": external_port,
        "broker_external_url": external_url,
    }
