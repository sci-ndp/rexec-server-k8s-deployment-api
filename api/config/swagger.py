from pydantic_settings import BaseSettings


class SwaggerSettings(BaseSettings):
    swagger_title: str = "R-Exec API"
    swagger_description: str = "RESTful API for Remote Execution"
    swagger_version: str = "0.0.1"

    model_config = {
        "env_file": ".env",
        "extra": "allow",
    }

settings = SwaggerSettings()