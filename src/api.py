"""API HTTP sobre los KID: FastAPI en Lambda con Function URL (Mangum traduce el evento de Lambda a ASGI).

Solo lectura. Es, con la aplicación, la única puerta a los datos (regla 5 del enunciado).
"""

from __future__ import annotations

from functools import cache

import boto3
from fastapi import FastAPI, HTTPException, Query
from mangum import Mangum

from kid_pipeline import Config
from kid_pipeline.db import BaseDatos

app = FastAPI(title="Fund KID API", version="0.1.0")


@cache
def db() -> BaseDatos:
    cfg = Config.desde_entorno()
    return BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn,
                     cfg.db_name)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/fondos")
def fondos(gestora: str | None = None, sri_min: int = Query(1, ge=1, le=7),
           sri_max: int = Query(7, ge=1, le=7)) -> list[dict]:
    """KID vigente de cada clase, con filtros opcionales."""
    sql = "SELECT * FROM kid_vigente WHERE sri BETWEEN :sri_min AND :sri_max"
    valores = {"sri_min": sri_min, "sri_max": sri_max}
    if gestora:
        sql += " AND gestora_fuente = :gestora"
        valores["gestora"] = gestora
    return db().consultar(sql + " ORDER BY gestora, nombre_producto, nombre_clase", **valores)


@app.get("/fondos/{isin}")
def fondo(isin: str) -> dict:
    """Todas las versiones del KID de una clase, de la más reciente a la más antigua."""
    filas = db().consultar(
        "SELECT k.*, d.url_pdf, d.descargado_en FROM kid k JOIN documentos d ON d.sha256 = k.documento_sha256 "
        "WHERE k.isin = :isin ORDER BY k.fecha_documento DESC NULLS LAST", isin=isin.upper())
    if not filas:
        raise HTTPException(404, f"No hay KID para {isin}")
    return {"isin": isin.upper(), "vigente": filas[0], "historico": filas[1:]}


@app.get("/resumen")
def resumen() -> list[dict]:
    """Por gestora: clases, SRI medio y gastos corrientes medios."""
    return db().consultar(
        "SELECT gestora_fuente, COUNT(*) AS clases, AVG(sri) AS sri_medio, "
        "AVG(gastos_corrientes_pct) AS gastos_corrientes_medios FROM kid_vigente GROUP BY gestora_fuente")


handler = Mangum(app)
