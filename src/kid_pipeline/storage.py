"""Dónde va cada PDF y qué procedencia lleva (enunciado §4: origen y fecha de descarga de cada documento).

La misma estructura sirve en S3 (bucket privado) y en local (`data/`, fuera de Git), así que subir lo capturado en
local es copiar las mismas claves:
    kid/<gestora>/<sha256>.pdf            el PDF; en S3, con su procedencia en los metadatos del objeto
    manifest/<AAAAMMDDTHHMMSSZ>.jsonl     una línea por documento capturado en esa ejecución

Cada manifiesto es una foto de lo que publicaba cada gestora capturada en esa ejecución. Comparar la última foto con
la nueva dice qué KID son nuevos, cuáles han cambiado y cuáles han desaparecido (D-1.6).
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

from botocore.exceptions import ClientError

from .capture import Documento


def clave_pdf(doc: Documento) -> str:
    return f"kid/{doc.enlace.gestora}/{doc.sha256}.pdf"


def clave_manifiesto(momento: datetime) -> str:
    return f"manifest/{momento.strftime('%Y%m%dT%H%M%SZ')}.jsonl"


def _ascii(valor: str) -> str:
    """Los metadatos de usuario de S3 solo admiten ASCII: se codifican como en una URL."""
    return quote(valor, safe=":/?&=+%#.,-_ ~()")


def metadatos(doc: Documento) -> dict[str, str]:
    e = doc.enlace
    m = {"gestora": e.gestora, "url-pdf": e.url_pdf, "url-ficha": e.url_ficha,
         "descargado-en": doc.descargado_en.isoformat(), "robots": doc.robots}
    if e.isin_web:
        m["isin-web"] = e.isin_web
    if doc.huella.get("isin_pdf"):
        m["isin-pdf"] = doc.huella["isin_pdf"]
    return {k: _ascii(v) for k, v in m.items()}


def registro(doc: Documento) -> dict:
    """Una línea del manifiesto: todo lo que se sabe del documento antes de extraerlo.

    `isin_web`, `clase` y `fecha_web` vienen de la web; `isin_pdf`, `paginas` y `tipo_documento`, del propio PDF.
    """
    e, h = doc.enlace, doc.huella
    return {"sha256": doc.sha256, "s3_key": clave_pdf(doc), "bytes": len(doc.contenido), "gestora": e.gestora,
            "fondo": e.fondo, "clase": e.clase, "isin_web": e.isin_web, "isin_pdf": h.get("isin_pdf"),
            "fecha_web": e.fecha_web, "tipo_documento": h.get("tipo_documento"), "paginas": h.get("paginas"),
            "url_pdf": e.url_pdf, "url_ficha": e.url_ficha, "descargado_en": doc.descargado_en.isoformat(),
            "comprobado_en": (doc.comprobado_en or doc.descargado_en).isoformat(), "http": doc.http,
            "etag": doc.etag, "last_modified": doc.last_modified, "robots": doc.robots}


def linea_manifiesto(doc: Documento) -> str:
    return json.dumps(registro(doc), ensure_ascii=False)


def subir(s3, bucket: str, doc: Documento) -> str:
    """Sube el PDF si no existe ya (misma clave = mismo contenido) y devuelve su clave."""
    clave = clave_pdf(doc)
    try:
        s3.head_object(Bucket=bucket, Key=clave)
    except ClientError:
        s3.put_object(Bucket=bucket, Key=clave, Body=doc.contenido, ContentType="application/pdf",
                      Metadata=metadatos(doc))
    return clave


def guardar_local(raiz: Path, doc: Documento) -> str:
    """Lo mismo que `subir`, en una carpeta local."""
    clave = clave_pdf(doc)
    destino = raiz / clave
    if not destino.exists():
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_bytes(doc.contenido)
    return clave


def escribir_manifiesto_local(raiz: Path, momento: datetime, lineas: list[str]) -> Path:
    destino = raiz / clave_manifiesto(momento)
    destino.parent.mkdir(parents=True, exist_ok=True)
    destino.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return destino


# --- Manifiestos anteriores: copia guardada y detección de cambios ----------------------------------------------------

def _lineas(contenido: str) -> list[dict]:
    return [json.loads(ln) for ln in contenido.splitlines() if ln.strip()]


def leer_manifiestos_local(raiz: Path) -> list[tuple[str, list[dict]]]:
    """(nombre, registros) de cada manifiesto, del más antiguo al más reciente (el nombre es la fecha)."""
    return [(m.name, _lineas(m.read_text(encoding="utf-8"))) for m in sorted((raiz / "manifest").glob("*.jsonl"))]


def leer_manifiestos_s3(s3, bucket: str) -> list[tuple[str, list[dict]]]:
    claves = []
    for pagina in s3.get_paginator("list_objects_v2").paginate(Bucket=bucket, Prefix="manifest/"):
        claves += [o["Key"] for o in pagina.get("Contents", []) if o["Key"].endswith(".jsonl")]
    return [(c.rsplit("/", 1)[-1], _lineas(s3.get_object(Bucket=bucket, Key=c)["Body"].read().decode("utf-8")))
            for c in sorted(claves)]


def leer_local(raiz: Path, r: dict) -> bytes | None:
    f = raiz / r["s3_key"]
    return f.read_bytes() if f.exists() else None


def leer_s3(s3, bucket: str, r: dict) -> bytes | None:
    try:
        return s3.get_object(Bucket=bucket, Key=r["s3_key"])["Body"].read()
    except ClientError:
        return None


def vigentes(manifiestos: list[tuple[str, list[dict]]]) -> list[dict]:
    """Lo último publicado por cada gestora: los registros del manifiesto más reciente en que aparece."""
    ultimo: dict[str, list[dict]] = {}
    for _, registros in sorted(manifiestos, key=lambda m: m[0]):
        for g in {r["gestora"] for r in registros}:
            ultimo[g] = [r for r in registros if r["gestora"] == g]
    return [r for g in sorted(ultimo) for r in ultimo[g]]


def isin_de(r: dict) -> str | None:
    """El ISIN del registro: el de la web y, si la web no lo da, el que trae el PDF."""
    return r.get("isin_web") or r.get("isin_pdf")


def comparar(anteriores: list[dict], actuales: list[dict], completas: set[str]) -> dict[str, list]:
    """KID nuevos, cambiados (mismo ISIN o misma URL, otro SHA-256), sin cambios y desaparecidos.

    Se empareja por (gestora, ISIN) y, si no, por (gestora, URL del PDF): Azvalor cambia la URL al publicar un KID
    nuevo, y los registros antiguos pueden no traer `isin_pdf`. Solo se dan por desaparecidos los KID de gestoras
    capturadas sin errores (`completas`): si una ficha falló, que falte su KID no dice nada.
    """
    por_isin = {(r["gestora"], isin_de(r)): r for r in anteriores if isin_de(r)}
    por_url = {(r["gestora"], r["url_pdf"]): r for r in anteriores}
    emparejados: set[int] = set()
    out: dict[str, list] = {"nuevos": [], "cambiados": [], "sin_cambios": [], "desaparecidos": []}
    for r in actuales:
        previo = por_isin.get((r["gestora"], isin_de(r))) if isin_de(r) else None
        previo = previo or por_url.get((r["gestora"], r["url_pdf"]))
        if previo is None:
            out["nuevos"].append(r)
            continue
        emparejados.add(id(previo))
        out["sin_cambios" if previo["sha256"] == r["sha256"] else "cambiados"].append((previo, r))
    out["desaparecidos"] = [r for r in anteriores if id(r) not in emparejados and r["gestora"] in completas]
    return out
