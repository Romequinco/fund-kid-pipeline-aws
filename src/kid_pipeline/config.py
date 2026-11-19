"""Configuración por variables de entorno: nada de secretos en el código (D-0.4).

`.env.example` documenta cada variable. En AWS las rellena Terraform; en GitHub Actions, el workflow.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Config:
    region: str
    bucket: str
    db_cluster_arn: str
    db_secret_arn: str
    db_name: str
    modelo_bedrock: str

    @classmethod
    def desde_entorno(cls) -> Config:
        return cls(
            region=os.environ.get("AWS_REGION", "eu-west-3"),
            bucket=os.environ.get("KID_BUCKET", ""),
            db_cluster_arn=os.environ.get("DB_CLUSTER_ARN", ""),
            db_secret_arn=os.environ.get("DB_SECRET_ARN", ""),
            db_name=os.environ.get("DB_NAME", "kid"),
            modelo_bedrock=os.environ.get("BEDROCK_MODEL_ID", ""),
        )
