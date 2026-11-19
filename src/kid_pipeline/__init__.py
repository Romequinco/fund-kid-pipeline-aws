"""Pipeline de KID de fondos: captura, S3, extracción con Bedrock y carga en PostgreSQL.

`Config` reúne la configuración, que entra por variables de entorno: nada de secretos en el código (D-0.4).
`.env.example` documenta cada variable; en AWS las rellena Terraform y en GitHub Actions, el workflow.
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
        e = os.environ.get
        return cls(region=e("AWS_REGION", "eu-west-3"), bucket=e("KID_BUCKET", ""),
                   db_cluster_arn=e("DB_CLUSTER_ARN", ""), db_secret_arn=e("DB_SECRET_ARN", ""),
                   db_name=e("DB_NAME", "kid"), modelo_bedrock=e("BEDROCK_MODEL_ID", ""))
