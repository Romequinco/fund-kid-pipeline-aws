"""Ejecución por lotes de cada fase. En local con `aws login`; en GitHub Actions con OIDC (job `lote` de deploy.yml).

    python src/pipeline.py capture --local [--gestora cobas] [--dry-run]   web -> data/ (sin AWS)
    python src/pipeline.py verificar                                       comprobaciones de lo capturado en data/
    python src/pipeline.py init-db                                         crea tablas y vista
    python src/pipeline.py capture [--gestora cobas]                       web -> S3 + manifiesto + tabla documentos
    python src/pipeline.py extract [--todos]                               S3 -> Bedrock -> tabla kid
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import sys
from collections import Counter, defaultdict
from datetime import UTC, date, datetime
from pathlib import Path

import requests

from kid_pipeline import Config
from kid_pipeline.capture import (
    FUENTES,
    KID_MAX_PAGINAS,
    Informe,
    SesionEducada,
    WebCambiada,
    capturar,
    clases_en,
    compacto,
    isin_del_pdf,
    isines,
    texto_pdf,
    tipo_documento,
    validar_pdf,
)
from kid_pipeline.storage import (
    clave_manifiesto,
    comparar,
    escribir_manifiesto_local,
    guardar_local,
    isin_de,
    leer_local,
    leer_manifiestos_local,
    leer_manifiestos_s3,
    leer_s3,
    registro,
    subir,
    vigentes,
)

log = logging.getLogger("pipeline")
RAIZ_LOCAL = Path(__file__).resolve().parents[1] / "data"
MINIMOS = {"documentos": 15, "fuentes": 2}  # enunciado §4
MESES = ("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre",
         "noviembre", "diciembre")


def capture(gestoras: list[str], local: Path | None, dry_run: bool = False) -> tuple[list[Informe], dict]:
    """Captura las gestoras pedidas. Destino: `local` (carpeta) o S3 + tabla documentos (configuración del entorno).

    Compara lo capturado con el último manifiesto de cada gestora (KID nuevos, cambiados y desaparecidos) y pide
    de forma condicional cada PDF ya conocido (D-1.6).
    """
    sesion, informes, registros, vistos = SesionEducada(), [], [], set()
    if local is None and not dry_run:
        import boto3

        from kid_pipeline.db import BaseDatos
        cfg = Config.desde_entorno()
        s3 = boto3.client("s3", region_name=cfg.region)
        db = BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn,
                       cfg.db_name)
    if dry_run:
        anteriores, leer = [], None
    elif local is not None:
        anteriores, leer = vigentes(leer_manifiestos_local(local)), (lambda r: leer_local(local, r))
    else:
        anteriores, leer = vigentes(leer_manifiestos_s3(s3, cfg.bucket)), (lambda r: leer_s3(s3, cfg.bucket, r))
    anteriores = [r for r in anteriores if r["gestora"] in gestoras]
    previos = {r["url_pdf"]: r for r in anteriores}
    for nombre in gestoras:
        fuente, informe = FUENTES[nombre](), Informe(nombre)
        informes.append(informe)
        try:
            if dry_run:
                for e in fuente.enlaces(sesion, informe):
                    log.info("%s | %s | %s | %s | %s", nombre, e.isin_web, e.clase or "-", e.fecha_web or "-",
                             e.url_pdf)
                continue
            for doc in capturar(fuente, sesion, informe, vistos, previos, leer):
                if local is not None:
                    clave = guardar_local(local, doc)
                else:
                    clave = subir(s3, cfg.bucket, doc)
                    db.guardar_documento(doc, clave)
                registros.append(registro(doc))
                log.info("%s %s %s -> %s", nombre, doc.http, doc.enlace.isin_web or doc.huella.get("isin_pdf"), clave)
        except (WebCambiada, requests.RequestException, PermissionError) as e:  # p. ej., el listado no responde
            informe.errores.append(str(e))
            log.error("%s", e)
        log.info("%s", informe.resumen())
    if registros:
        momento = datetime.now(UTC)
        lineas = [json.dumps(r, ensure_ascii=False) for r in registros]
        if local is not None:
            log.info("Manifiesto: %s", escribir_manifiesto_local(local, momento, lineas))
        else:
            s3.put_object(Bucket=cfg.bucket, Key=clave_manifiesto(momento), Body="\n".join(lineas).encode(),
                          ContentType="application/x-ndjson")
    completas = {i.gestora for i in informes if not i.errores}
    return informes, comparar(anteriores, registros, completas) if not dry_run else {}


def formas_fecha(iso: str) -> re.Pattern:
    """Cómo puede escribir un KID la fecha AAAA-MM-DD, sobre el texto `compacto` (09/01/2026, 9.1.2026,
    9deenerode2026). Sin dígitos alrededor: «9 de enero» no debe encontrarse dentro de «19 de enero»."""
    d = date.fromisoformat(iso)
    mes = MESES[d.month - 1]
    formas = {f"{dia}{s}{m}{s}{d.year}" for s in "/.-" for dia in (d.day, f"{d.day:02d}")
              for m in (d.month, f"{d.month:02d}")}
    formas |= {f"{d.day}de{mes}de{d.year}", f"{d.day:02d}de{mes}de{d.year}", iso}
    return re.compile(r"(?<!\d)(?:" + "|".join(map(re.escape, sorted(formas))) + r")(?!\d)")


def _integridad(raiz: Path, historico: dict[str, dict], fallos: list[str]) -> dict[str, bytes]:
    """Fichero, SHA-256, PDF y campos de procedencia de todo lo guardado. Devuelve el contenido de cada PDF."""
    contenidos = {}
    for sha, r in historico.items():
        faltan = [k for k in ("gestora", "url_pdf", "url_ficha", "descargado_en", "s3_key", "robots") if not r.get(k)]
        if faltan:
            fallos.append(f"{sha[:12]}: faltan en el manifiesto {faltan}")
        if r.get("s3_key") != f"kid/{r.get('gestora')}/{sha}.pdf":
            fallos.append(f"{sha[:12]}: la clave {r.get('s3_key')} no es kid/<gestora>/<sha256>.pdf")
        try:
            if datetime.fromisoformat(r["descargado_en"]).tzinfo is None:
                fallos.append(f"{sha[:12]}: descargado_en sin zona horaria")
        except (KeyError, TypeError, ValueError):
            fallos.append(f"{sha[:12]}: descargado_en no es una fecha ISO")
        f = raiz / str(r.get("s3_key"))
        if not f.is_file():
            fallos.append(f"{sha[:12]}: no existe {f}")
            continue
        contenido = contenidos[sha] = f.read_bytes()
        if hashlib.sha256(contenido).hexdigest() != sha:
            fallos.append(f"{sha[:12]}: el SHA-256 no coincide con el fichero")
        try:
            validar_pdf(contenido, str(f))
        except ValueError as e:
            fallos.append(f"{sha[:12]}: {e}")
    return contenidos


def verificar(raiz: Path) -> dict:
    """Comprobaciones objetivas de lo capturado en local. Devuelve el resultado y si pasa los mínimos.

    La integridad se comprueba en todo lo guardado; el contenido, en lo vigente (el último manifiesto de cada
    gestora, que es lo que publica hoy su web): que sea un KID, que el ISIN, la clase y la fecha que da la web estén
    en el PDF, y que cada ISIN y cada clase aparezcan una sola vez.
    """
    manifiestos = leer_manifiestos_local(raiz)
    historico = {r["sha256"]: r for _, rs in manifiestos for r in rs}  # el último manifiesto manda
    actuales = vigentes(manifiestos)
    fallos, avisos = [], []
    contenidos = _integridad(raiz, historico, fallos)
    por_gestora: dict[str, Counter] = defaultdict(Counter)
    por_isin, por_clase = Counter(), Counter()
    for r in actuales:
        sha, g = r["sha256"], r["gestora"]
        c, ref = por_gestora[g], f"{sha[:12]} ({g})"
        c["documentos"] += 1
        por_clase[(g, r.get("fondo"), r.get("clase"))] += 1
        if sha not in contenidos:
            continue
        try:
            paginas, txt = texto_pdf(contenidos[sha])
        except Exception as e:  # PDF ilegible
            fallos.append(f"{ref}: no se puede leer el PDF ({e})")
            continue
        t, tipo = compacto(txt), tipo_documento(txt)
        if tipo is None:
            fallos.append(f"{ref}: el texto no parece un KID")
        elif tipo != "KID PRIIPs":
            avisos.append(f"{ref}: es un {tipo}, no un KID PRIIPs")
        if paginas > KID_MAX_PAGINAS:
            fallos.append(f"{ref}: {paginas} páginas, demasiadas para un KID")
        elif paginas > 3:  # el KID son 3 caras A4; Cobas añade un anexo de escenarios y rentabilidades pasadas
            c["con_anexo"] += 1
        isin_pdf = isin_del_pdf(txt, r.get("isin_web"))
        if len(isines(txt)) > 1:
            avisos.append(f"{ref}: el PDF tiene varios ISIN {isines(txt)}")
        if r.get("isin_pdf") and r["isin_pdf"] != isin_pdf:
            fallos.append(f"{ref}: el manifiesto dice isin_pdf {r['isin_pdf']} y el PDF da {isin_pdf}")
        if r.get("isin_web"):
            if r["isin_web"].lower() in t:
                c["isin_web_en_pdf"] += 1
            else:
                fallos.append(f"{ref}: el ISIN de la web {r['isin_web']} no está en el PDF")
        elif isin_pdf:
            c["isin_solo_pdf"] += 1
        if isin := isin_de(r) or isin_pdf:
            por_isin[isin] += 1
        else:
            fallos.append(f"{ref}: sin ISIN ni en la web ni en el PDF")
        if r.get("clase"):
            c["con_clase"] += 1
            clases_pdf = clases_en(txt[:2000])  # la sección «Producto», al principio del KID
            if r["clase"] not in clases_pdf:
                fallos.append(f"{ref}: la web dice {r['clase']} y el PDF {sorted(clases_pdf) or 'ninguna clase'}")
        if r.get("fecha_web"):
            c["con_fecha_web"] += 1
            if not formas_fecha(r["fecha_web"]).search(t):
                fallos.append(f"{ref}: la fecha del nombre del PDF ({r['fecha_web']}) no aparece en el PDF")
    fallos += [f"ISIN {i}: {n} KID vigentes" for i, n in por_isin.items() if n > 1]
    fallos += [f"{g} / {f} / {cl or 'sin clase'}: {n} KID vigentes" for (g, f, cl), n in por_clase.items() if n > 1]
    total = Counter()
    for c in por_gestora.values():
        total.update(c)
    resultado = {
        "documentos": len(actuales), "historico": len(historico), "fuentes": len(por_gestora),
        "por_gestora": {g: dict(c) for g, c in sorted(por_gestora.items())}, "con_isin": sum(por_isin.values()),
        **{k: total[k] for k in ("isin_web_en_pdf", "isin_solo_pdf", "con_clase", "con_fecha_web", "con_anexo")},
        "avisos": avisos, "fallos": fallos,
        "cumple_minimos": len(actuales) >= MINIMOS["documentos"] and len(por_gestora) >= MINIMOS["fuentes"],
    }
    resultado["ok"] = resultado["cumple_minimos"] and not fallos
    return resultado


def extract(todos: bool) -> None:
    import boto3

    from kid_pipeline.db import BaseDatos
    from kid_pipeline.extract import extraer
    from kid_pipeline.schema import faltan_obligatorios

    cfg = Config.desde_entorno()
    s3 = boto3.client("s3", region_name=cfg.region)
    bedrock = boto3.client("bedrock-runtime", region_name=cfg.region)
    db = BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn, cfg.db_name)
    filtro = "" if todos else "WHERE NOT EXISTS (SELECT 1 FROM kid k WHERE k.documento_sha256 = d.sha256)"
    for fila in db.consultar(f"SELECT sha256, s3_key FROM documentos d {filtro} ORDER BY descargado_en"):
        pdf = s3.get_object(Bucket=cfg.bucket, Key=fila["s3_key"])["Body"].read()
        kid = extraer(bedrock, pdf, cfg.modelo_bedrock)
        if faltan := faltan_obligatorios(kid):
            log.warning("%s: faltan campos obligatorios %s", fila["s3_key"], faltan)
        db.guardar_kid(fila["sha256"], kid, cfg.modelo_bedrock)
        log.info("%s -> %s", fila["s3_key"], kid.isin)


def imprimir_captura(informes: list[Informe], cambios: dict, dry_run: bool) -> None:
    for i in informes:
        print(i.resumen())
        for url in i.sin_kid:
            print("   ficha sin KID:", url)
        for err in i.errores:
            print("   error:", err)
    if dry_run:
        return
    obtenidos = sum(i.obtenidos for i in informes)
    fuentes = sum(1 for i in informes if i.obtenidos)
    print(f"Total: {obtenidos} KID de {fuentes} fuentes (mínimo del enunciado: {MINIMOS['documentos']} y "
          f"{MINIMOS['fuentes']})")
    print(f"Frente al manifiesto anterior: {len(cambios['nuevos'])} nuevos, {len(cambios['cambiados'])} cambiados, "
          f"{len(cambios['sin_cambios'])} sin cambios, {len(cambios['desaparecidos'])} desaparecidos")
    for r in cambios["nuevos"]:
        print("   NUEVO:", r["gestora"], isin_de(r), r.get("clase") or "", r["url_pdf"])
    for antes, ahora in cambios["cambiados"]:
        print("   CAMBIADO:", ahora["gestora"], isin_de(ahora), antes["sha256"][:12], "->", ahora["sha256"][:12],
              ahora["url_pdf"])
    for r in cambios["desaparecidos"]:
        print("   DESAPARECIDO:", r["gestora"], isin_de(r), r["url_pdf"])


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("pypdf").setLevel(logging.ERROR)  # avisos de PDF mal formados que pypdf sí lee
    p = argparse.ArgumentParser()
    sub = p.add_subparsers(dest="fase", required=True)
    sub.add_parser("init-db")
    c = sub.add_parser("capture")
    c.add_argument("--gestora", action="append", choices=sorted(FUENTES))
    c.add_argument("--local", nargs="?", const=RAIZ_LOCAL, type=Path, help=f"guarda en local (defecto {RAIZ_LOCAL})")
    c.add_argument("--dry-run", action="store_true", help="solo lista los enlaces, sin descargar")
    v = sub.add_parser("verificar")
    v.add_argument("--local", nargs="?", default=RAIZ_LOCAL, const=RAIZ_LOCAL, type=Path)
    e = sub.add_parser("extract")
    e.add_argument("--todos", action="store_true", help="reprocesa también lo ya extraído")
    args = p.parse_args()

    if args.fase == "init-db":
        import boto3

        from kid_pipeline.db import BaseDatos
        cfg = Config.desde_entorno()
        BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn,
                  cfg.db_name).crear_esquema()
    elif args.fase == "capture":
        informes, cambios = capture(args.gestora or sorted(FUENTES), args.local, args.dry_run)
        imprimir_captura(informes, cambios, args.dry_run)
        return 1 if any(i.obtenidos == 0 and not args.dry_run for i in informes) else 0
    elif args.fase == "verificar":
        r = verificar(args.local)
        print(json.dumps({k: v for k, v in r.items() if k not in ("fallos", "avisos")}, ensure_ascii=False, indent=2))
        for a in r["avisos"]:
            print("AVISO:", a)
        for f in r["fallos"]:
            print("FALLO:", f)
        print("OK" if r["ok"] else "NO OK")
        return 0 if r["ok"] else 1
    else:
        extract(args.todos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
