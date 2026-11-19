"""Ejecución por lotes de cada fase. En local con `aws login`; en GitHub Actions con OIDC (job `lote` de deploy.yml).

    python src/pipeline.py init-db                       crea tablas y vista
    python src/pipeline.py capture [--gestora cobas]     web -> S3 + manifiesto + tabla documentos
    python src/pipeline.py extract [--todos]             S3 -> Bedrock -> tabla kid (por defecto, solo lo pendiente)
"""

from __future__ import annotations

import argparse
import logging
from datetime import UTC, datetime

import boto3

from kid_pipeline import Config
from kid_pipeline.capture import FUENTES, SesionEducada
from kid_pipeline.db import BaseDatos
from kid_pipeline.extract import extraer
from kid_pipeline.schema import faltan_obligatorios
from kid_pipeline.storage import clave_manifiesto, linea_manifiesto, subir

log = logging.getLogger("pipeline")


def capture(cfg: Config, db: BaseDatos, gestoras: list[str]) -> None:
    s3, sesion, lineas = boto3.client("s3", region_name=cfg.region), SesionEducada(), []
    for nombre in gestoras:
        for enlace in FUENTES[nombre]().enlaces(sesion):
            doc = sesion.descargar(enlace)
            clave = subir(s3, cfg.bucket, doc)
            db.guardar_documento(doc, clave)
            lineas.append(linea_manifiesto(doc))
            log.info("%s %s -> %s", nombre, enlace.url_pdf, clave)
    if lineas:
        s3.put_object(Bucket=cfg.bucket, Key=clave_manifiesto(datetime.now(UTC)),
                      Body="\n".join(lineas).encode(), ContentType="application/x-ndjson")
    log.info("%d documentos capturados", len(lineas))


def extract(cfg: Config, db: BaseDatos, todos: bool) -> None:
    s3 = boto3.client("s3", region_name=cfg.region)
    bedrock = boto3.client("bedrock-runtime", region_name=cfg.region)
    filtro = "" if todos else "WHERE NOT EXISTS (SELECT 1 FROM kid k WHERE k.documento_sha256 = d.sha256)"
    for fila in db.consultar(f"SELECT sha256, s3_key FROM documentos d {filtro} ORDER BY descargado_en"):
        pdf = s3.get_object(Bucket=cfg.bucket, Key=fila["s3_key"])["Body"].read()
        kid = extraer(bedrock, pdf, cfg.modelo_bedrock)
        if faltan := faltan_obligatorios(kid):
            log.warning("%s: faltan campos obligatorios %s", fila["s3_key"], faltan)
        db.guardar_kid(fila["sha256"], kid, cfg.modelo_bedrock)
        log.info("%s -> %s", fila["s3_key"], kid.isin)


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="fase", required=True)
    sub.add_parser("init-db")
    c = sub.add_parser("capture")
    c.add_argument("--gestora", action="append", choices=sorted(FUENTES))
    e = sub.add_parser("extract")
    e.add_argument("--todos", action="store_true", help="reprocesa también lo ya extraído")
    args = p.parse_args()

    cfg = Config.desde_entorno()
    db = BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn, cfg.db_name)
    if args.fase == "init-db":
        db.crear_esquema()
    elif args.fase == "capture":
        capture(cfg, db, args.gestora or sorted(FUENTES))
    else:
        extract(cfg, db, args.todos)


if __name__ == "__main__":
    main()
