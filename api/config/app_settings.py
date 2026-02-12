from pydantic_settings import BaseSettings


class AppSettings(BaseSettings):
    """Application-level settings for the Deployment API."""

    root_path: str = ""

    model_config = {
        "env_file": ".env",
        "env_prefix": "APP_",
        "extra": "allow",
    }


app_settings = AppSettings()
