"""S3: dónde va cada PDF y qué metadatos lleva (enunciado §4: origen y fecha de descarga de cada documento).

Estructura del bucket (privado):
    kid/<gestora>/<sha256>.pdf      el PDF, con su procedencia en los metadatos del objeto
    manifest/<AAAAMMDDTHHMMSSZ>.jsonl   una línea por documento capturado en esa ejecución
"""

from __future__ import annotations

import json
from datetime import datetime

from botocore.exceptions import ClientError

from .capture import Documento


def clave_pdf(doc: Documento) -> str:
    return f"kid/{doc.enlace.gestora}/{doc.sha256}.pdf"


def metadatos(doc: Documento) -> dict[str, str]:
    """Metadatos de usuario de S3: solo ASCII, por eso las URL van tal cual y la fecha en ISO 8601."""
    e = doc.enlace
    m = {
        "gestora": e.gestora,
        "url-pdf": e.url_pdf,
        "url-ficha": e.url_ficha,
        "descargado-en": doc.descargado_en.isoformat(),
    }
    if e.isin_web:
        m["isin-web"] = e.isin_web
    return m


def linea_manifiesto(doc: Documento) -> str:
    e = doc.enlace
    return json.dumps(
        {"sha256": doc.sha256, "s3_key": clave_pdf(doc), "bytes": len(doc.contenido), **metadatos(doc),
         "fondo": e.fondo, "clase": e.clase},
        ensure_ascii=False,
    )


def clave_manifiesto(momento: datetime) -> str:
    return f"manifest/{momento.strftime('%Y%m%dT%H%M%SZ')}.jsonl"


def subir(s3, bucket: str, doc: Documento) -> str:
    """Sube el PDF si no existe ya (misma clave = mismo contenido) y devuelve su clave."""
    clave = clave_pdf(doc)
    try:
        s3.head_object(Bucket=bucket, Key=clave)
    except ClientError:
        s3.put_object(Bucket=bucket, Key=clave, Body=doc.contenido, ContentType="application/pdf",
                      Metadata=metadatos(doc))
    return clave
