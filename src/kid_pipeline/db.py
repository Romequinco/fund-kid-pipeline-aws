"""PostgreSQL con RDS Data API: sin driver ni VPC, una llamada HTTP por sentencia (D-3.1).

Las cargas son idempotentes: `ON CONFLICT` sobre el SHA-256 del documento (D-1.2).
"""

from __future__ import annotations

import json
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path

from .capture.base import Documento
from .schema import Kid

SQL_ESQUEMA = Path(__file__).resolve().parents[2] / "db" / "schema.sql"

UPSERT_DOCUMENTO = """
INSERT INTO documentos (sha256, gestora_fuente, url_pdf, url_ficha, s3_key, bytes, descargado_en)
VALUES (:sha256, :gestora_fuente, :url_pdf, :url_ficha, :s3_key, :bytes, :descargado_en)
ON CONFLICT (sha256) DO NOTHING
"""

UPSERT_KID = """
INSERT INTO kid (documento_sha256, isin, nombre_producto, nombre_clase, gestora, fecha_documento, sri,
                 periodo_mantenimiento_anios, gastos_corrientes_pct, costes_entrada_pct, costes_salida_pct, modelo)
VALUES (:documento_sha256, :isin, :nombre_producto, :nombre_clase, :gestora, :fecha_documento, :sri,
        :periodo_mantenimiento_anios, :gastos_corrientes_pct, :costes_entrada_pct, :costes_salida_pct, :modelo)
ON CONFLICT (documento_sha256) DO UPDATE SET
    isin = EXCLUDED.isin, nombre_producto = EXCLUDED.nombre_producto, nombre_clase = EXCLUDED.nombre_clase,
    gestora = EXCLUDED.gestora, fecha_documento = EXCLUDED.fecha_documento, sri = EXCLUDED.sri,
    periodo_mantenimiento_anios = EXCLUDED.periodo_mantenimiento_anios,
    gastos_corrientes_pct = EXCLUDED.gastos_corrientes_pct, costes_entrada_pct = EXCLUDED.costes_entrada_pct,
    costes_salida_pct = EXCLUDED.costes_salida_pct, modelo = EXCLUDED.modelo, extraido_en = now()
"""


def parametro(nombre: str, valor) -> dict:
    """Un valor de Python como parámetro de la Data API (con `typeHint` para fechas y decimales)."""
    if valor is None:
        return {"name": nombre, "value": {"isNull": True}}
    if isinstance(valor, bool):
        return {"name": nombre, "value": {"booleanValue": valor}}
    if isinstance(valor, int):
        return {"name": nombre, "value": {"longValue": valor}}
    if isinstance(valor, float | Decimal):
        return {"name": nombre, "value": {"stringValue": str(valor)}, "typeHint": "DECIMAL"}
    if isinstance(valor, datetime):
        return {"name": nombre, "value": {"stringValue": valor.strftime("%Y-%m-%d %H:%M:%S")}, "typeHint": "TIMESTAMP"}
    if isinstance(valor, date):
        return {"name": nombre, "value": {"stringValue": valor.isoformat()}, "typeHint": "DATE"}
    return {"name": nombre, "value": {"stringValue": str(valor)}}


class BaseDatos:
    def __init__(self, rds_data, cluster_arn: str, secret_arn: str, database: str) -> None:
        self.rds, self.destino = rds_data, {"resourceArn": cluster_arn, "secretArn": secret_arn, "database": database}

    def ejecutar(self, sql: str, **valores) -> dict:
        params = [parametro(k, v) for k, v in valores.items()]
        return self.rds.execute_statement(sql=sql, parameters=params, **self.destino)

    def consultar(self, sql: str, **valores) -> list[dict]:
        params = [parametro(k, v) for k, v in valores.items()]
        r = self.rds.execute_statement(sql=sql, parameters=params, formatRecordsAs="JSON", **self.destino)
        return json.loads(r.get("formattedRecords", "[]"))

    def crear_esquema(self) -> None:
        """La Data API ejecuta una sentencia por llamada: se quitan los comentarios y se trocea por `;`."""
        lineas = [ln for ln in SQL_ESQUEMA.read_text(encoding="utf-8").splitlines() if not ln.lstrip().startswith("--")]
        for sentencia in "\n".join(lineas).split(";"):
            if sentencia.strip():
                self.ejecutar(sentencia)

    def guardar_documento(self, doc: Documento, s3_key: str) -> None:
        e = doc.enlace
        self.ejecutar(UPSERT_DOCUMENTO, sha256=doc.sha256, gestora_fuente=e.gestora, url_pdf=e.url_pdf,
                      url_ficha=e.url_ficha, s3_key=s3_key, bytes=len(doc.contenido),
                      descargado_en=doc.descargado_en)

    def guardar_kid(self, sha256: str, kid: Kid, modelo: str) -> None:
        self.ejecutar(UPSERT_KID, documento_sha256=sha256, modelo=modelo, **kid.model_dump())
