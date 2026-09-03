"""Configuration for Rexec server provisioning."""

from pydantic_settings import BaseSettings


class RexecSettings(BaseSettings):
    """Settings that control the Rexec deployment integration."""

    kubeconfig_local_path: str | None = None
    # Canonical in-container kubeconfig path; keep in sync with the docker-compose
    # bind-mount target. Set REXEC_KUBECONFIG_MOUNT_PATH only to override it.
    kubeconfig_mount_path: str | None = "/home/appuser/.kube/config"
    use_in_cluster_config: bool = False
    namespace_prefix: str = "rexec-server-"
    namespace_wait_timeout_seconds: int = 60
    broker_service_name: str = "rexec-broker-internal-ip"
    broker_namespace: str = "rexec-broker"
    broker_port: int = 5560
    broker_external_service_name: str | None = "rexec-broker-external-ip"
    broker_external_host: str | None = None
    broker_external_port: int | None = None
    container_name: str = "rexec-server"
    deployment_manifest_name: str = "rexec-server-deployment.yaml"

    # Resource ceilings applied to every rexec-server pod. No per-user override --
    # a client-supplied size is never trusted directly.
    container_cpu_request: str = "250m"
    container_cpu_limit: str = "2"
    container_memory_request: str = "512Mi"
    container_memory_limit: str = "4Gi"
    container_ephemeral_storage_request: str = "512Mi"
    container_ephemeral_storage_limit: str = "2Gi"

    model_config = {
        "env_file": ".env",
        "env_prefix": "REXEC_",
        "extra": "allow"
    }


rexec_settings = RexecSettings()
