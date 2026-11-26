"""Ejecución por lotes de cada fase. En local con `aws login`; en GitHub Actions con OIDC (job `lote` de deploy.yml).

    python src/pipeline.py capture --local [--gestora cobas] [--dry-run]   web -> data/ (sin AWS)
    python src/pipeline.py verificar                                       comprobaciones de lo capturado en data/
    python src/pipeline.py markdown                                        PDF -> Markdown del KID en data/markdown/
    python src/pipeline.py evaluar [--predicciones data/extraccion/x.jsonl] reglas o modelo frente a la referencia
    python src/pipeline.py init-db                                         crea tablas y vista
    python src/pipeline.py capture [--gestora cobas]                       web -> S3 + manifiesto + tabla documentos
    python src/pipeline.py extract --local --modelo <id> [--limite N]   data/markdown -> Bedrock -> data/extraccion/
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


def ruta_markdown(raiz: Path, r: dict) -> Path:
    """data/markdown/<gestora>/<sha256>.md: el Markdown del KID, junto al PDF del que sale."""
    return raiz / "markdown" / r["gestora"] / f"{r['sha256']}.md"


def markdown_local(raiz: Path, sobrescribir: bool = False) -> dict:
    """Convierte a Markdown (páginas del KID) cada PDF vigente de `raiz`. Lo ya convertido se reutiliza."""
    from kid_pipeline.texto import kid_markdown

    hechos = reutilizados = 0
    fallos = []
    for r in vigentes(leer_manifiestos_local(raiz)):
        destino = ruta_markdown(raiz, r)
        if destino.exists() and not sobrescribir:
            reutilizados += 1
            continue
        try:
            md = kid_markdown((raiz / r["s3_key"]).read_bytes())
        except Exception as e:  # un PDF que no se pueda convertir no para el resto
            fallos.append(f"{r['s3_key']}: {e}")
            continue
        destino.parent.mkdir(parents=True, exist_ok=True)
        destino.write_text(md, encoding="utf-8")
        hechos += 1
    return {"convertidos": hechos, "reutilizados": reutilizados, "fallos": fallos}


def kids_locales(raiz: Path) -> list[tuple[dict, str]]:
    """(registro del manifiesto, Markdown) de cada KID vigente ya convertido. Lo usan la extracción y la evaluación."""
    return [(r, ruta_markdown(raiz, r).read_text(encoding="utf-8"))
            for r in vigentes(leer_manifiestos_local(raiz)) if ruta_markdown(raiz, r).exists()]


def archivo_extraccion(raiz: Path, modelo: str) -> Path:
    """data/extraccion/<modelo>.jsonl: lo que lee `evaluar --predicciones` para comparar modelos (D-2.5)."""
    return raiz / "extraccion" / (re.sub(r"[^A-Za-z0-9._-]+", "_", modelo) + ".jsonl")


def extract_local(raiz: Path, modelo: str, mecanismo: str = "herramienta", limite: int | None = None,
                  region: str = "eu-west-3") -> dict:
    """Extrae con Bedrock los KID vigentes ya convertidos a Markdown y los añade al JSONL del modelo.

    Retoma donde lo dejó: los documentos que ya están en el JSONL no se vuelven a pedir (ni a pagar).
    """
    import time

    import boto3
    from botocore.config import Config as BotoConfig

    from kid_pipeline.extract import extraer, revisar

    # Margen para la primera compilación del esquema estricto (hasta ~90 s) y reintentos ante límites de cuota
    bedrock = boto3.client("bedrock-runtime", region_name=region,
                           config=BotoConfig(read_timeout=300, retries={"max_attempts": 6, "mode": "adaptive"}))
    destino = archivo_extraccion(raiz, modelo)
    hechos = set(leer_predicciones(destino)) if destino.exists() else set()
    pendientes = [(r, md) for r, md in kids_locales(raiz) if r["sha256"] not in hechos][:limite]
    destino.parent.mkdir(parents=True, exist_ok=True)
    ok, fallos = 0, []
    for r, md in pendientes:
        inicio = time.monotonic()
        try:
            kid = extraer(bedrock, md, modelo, mecanismo)
        except Exception as e:  # un KID que falla no para el resto; se reintenta en la próxima ejecución
            fallos.append(f"{r['sha256'][:12]} ({r['gestora']}): {type(e).__name__}: {e}")
            log.warning("%s", fallos[-1])
            continue
        revision = revisar(kid, md)
        fila = {"sha256": r["sha256"], "gestora": r["gestora"], **kid.valores(), "modelo": modelo,
                "mecanismo": mecanismo, "segundos": round(time.monotonic() - inicio, 1),
                "evidencias_ok": sum(v["aparece"] and v["coherente"] for v in revision.values()),
                "revision": revision}
        with destino.open("a", encoding="utf-8") as f:
            f.write(json.dumps(fila, ensure_ascii=False, default=str) + "\n")
        ok += 1
        log.info("%s %s -> %s (%.1f s)", r["gestora"], r["sha256"][:12], kid.isin, fila["segundos"])
    return {"modelo": modelo, "extraidos": ok, "ya_estaban": len(hechos), "fallos": fallos, "destino": str(destino)}


def extract(todos: bool) -> None:
    import boto3

    from kid_pipeline.db import BaseDatos
    from kid_pipeline.extract import extraer, revisar
    from kid_pipeline.schema import faltan_obligatorios
    from kid_pipeline.texto import kid_markdown

    cfg = Config.desde_entorno()
    s3 = boto3.client("s3", region_name=cfg.region)
    bedrock = boto3.client("bedrock-runtime", region_name=cfg.region)
    db = BaseDatos(boto3.client("rds-data", region_name=cfg.region), cfg.db_cluster_arn, cfg.db_secret_arn, cfg.db_name)
    filtro = "" if todos else "WHERE NOT EXISTS (SELECT 1 FROM kid k WHERE k.documento_sha256 = d.sha256)"
    for fila in db.consultar(f"SELECT sha256, s3_key FROM documentos d {filtro} ORDER BY descargado_en"):
        md = kid_markdown(s3.get_object(Bucket=cfg.bucket, Key=fila["s3_key"])["Body"].read())  # D-2.3
        kid = extraer(bedrock, md, cfg.modelo_bedrock)
        revision = revisar(kid, md)  # D-2.4: ¿cada evidencia está en el KID y cuadra con su valor?
        if faltan := faltan_obligatorios(kid):
            log.warning("%s: faltan campos obligatorios %s", fila["s3_key"], faltan)
        if no_cuadran := [c for c, r in revision.items() if not (r["aparece"] and r["coherente"])]:
            log.warning("%s: evidencias que no cuadran %s", fila["s3_key"], no_cuadran)
        db.guardar_kid(fila["sha256"], kid, cfg.modelo_bedrock, revision)
        log.info("%s -> %s", fila["s3_key"], kid.isin)


# --- Evaluación de la extracción frente al conjunto de referencia revisado a mano (D-2.5) ---

TOLERANCIA = 0.01  # en números: puntos porcentuales y años
_NUMERICOS = {"sri", "periodo_mantenimiento_anios", "gastos_corrientes_pct", "costes_entrada_pct", "costes_salida_pct"}
_FORMAS_LEGALES = {"fi", "fil", "sicav", "sa", "sgiic", "sgeic", "sau", "sl", "slu"}


def clave_texto(campo: str, valor) -> str:
    """Forma comparable de un texto: sin tildes, mayúsculas, puntuación ni espacios.

    En `nombre_producto` se quitan además la clase («CLASE A», «CL B2») y la forma legal («F.I.», «SICAV SA»); en
    `nombre_clase`, la palabra «Clase»; en `gestora`, la forma legal («S.G.I.I.C., S.A.» frente a «SGIIC, S.A.»).
    """
    import unicodedata

    t = "".join(c for c in unicodedata.normalize("NFKD", str(valor)) if not unicodedata.combining(c)).lower()
    palabras = re.sub(r"[^a-z0-9]+", " ", t.replace(".", "")).split()
    if campo == "nombre_producto":
        if len(palabras) >= 2 and palabras[-2] in ("clase", "cl", "class"):
            palabras = palabras[:-2]
        palabras = [p for p in palabras if p not in _FORMAS_LEGALES]
    elif campo == "nombre_clase":
        palabras = [p for p in palabras if p not in ("clase", "cl", "class", "serie")]
    elif campo == "gestora":
        palabras = [p for p in palabras if p not in _FORMAS_LEGALES]
    return "".join(palabras)


def _como_numero(valor) -> float | None:
    try:
        return float(str(valor).replace(",", ".").replace("%", "").strip())
    except ValueError:
        return None


def coincide(campo: str, obtenido, esperado) -> bool:
    """¿Es `obtenido` el mismo valor que `esperado` (no nulos)? Números con tolerancia; fechas e ISIN exactos."""
    if campo in _NUMERICOS:
        n = _como_numero(obtenido)
        return n is not None and abs(n - float(esperado)) <= (0 if campo == "sri" else TOLERANCIA)
    if campo == "fecha_documento":
        return str(obtenido)[:10] == str(esperado)[:10]
    if campo == "isin":
        return str(obtenido).replace(" ", "").upper() == str(esperado).upper()
    return clave_texto(campo, obtenido) == clave_texto(campo, esperado)


def leer_referencia(ruta: Path) -> dict[str, dict]:
    """sha256 -> {campo: {valor, alternativas, ...}} de `data/referencia.json`."""
    return {d["sha256"]: d["campos"] for d in json.loads(ruta.read_text(encoding="utf-8"))["documentos"]}


def leer_predicciones(ruta: Path) -> dict[str, dict]:
    """sha256 -> campos de un JSONL con una línea por documento: {"sha256": ..., "isin": ..., ...}."""
    filas = (json.loads(linea) for linea in ruta.read_text(encoding="utf-8").splitlines() if linea.strip())
    return {f["sha256"]: f for f in filas}


def predecir_reglas(kids: list[tuple[dict, str]]) -> dict[str, dict]:
    from kid_pipeline.reglas import extraer_reglas

    return {r["sha256"]: extraer_reglas(md) for r, md in kids}


def evaluar_extraccion(referencia: dict[str, dict], predicciones: dict[str, dict]) -> dict:
    """Compara campo a campo con la referencia: exactitud por campo y global, nulls y lista de discrepancias.

    Un null esperado y obtenido es un acierto (`null_ok`); un valor donde la referencia dice null es `inventado`, y
    un null donde hay valor, `omitido`. Un documento de la referencia sin predicción cuenta como todo omitido.
    """
    from kid_pipeline.reglas import CAMPOS

    por_campo = {c: Counter() for c in CAMPOS}
    discrepancias = []
    for sha, campos in referencia.items():
        pred = predicciones.get(sha)
        for c in CAMPOS:
            ref, obtenido, cuenta = campos[c], (pred or {}).get(c), por_campo[c]
            esperados = [v for v in [ref["valor"], *ref.get("alternativas", [])] if v is not None]
            cuenta["total"] += 1
            cuenta["esperados_null"] += not esperados
            if pred is None:  # sin predicción: fallo en todos los campos
                ok = False
                cuenta["omitidos"] += 1
            elif not esperados:
                ok = obtenido is None
                cuenta["null_ok" if ok else "inventados"] += 1
            elif obtenido is None:
                ok = False
                cuenta["omitidos"] += 1
            else:
                ok = any(coincide(c, obtenido, e) for e in esperados)
                cuenta["distintos"] += not ok
            cuenta["aciertos"] += ok
            if not ok:
                discrepancias.append({"sha256": sha, "campo": c, "esperado": ref["valor"], "obtenido": obtenido})
    resumen = {c: {"exactitud": round(n["aciertos"] / n["total"], 3) if n["total"] else None,
                   **{k: n[k] for k in ("aciertos", "total", "esperados_null", "null_ok", "inventados", "omitidos",
                                        "distintos")}}
               for c, n in por_campo.items()}
    aciertos, total = sum(n["aciertos"] for n in por_campo.values()), sum(n["total"] for n in por_campo.values())
    return {"documentos": len(referencia), "sin_prediccion": sorted(set(referencia) - set(predicciones)),
            "por_campo": resumen, "global": {"aciertos": aciertos, "total": total,
                                             "exactitud": round(aciertos / total, 3) if total else None},
            "discrepancias": discrepancias}


def coherencia_manifiesto(kids: list[tuple[dict, str]], predicciones: dict[str, dict]) -> dict:
    """En todos los KID vigentes (no solo la referencia): ISIN y clase extraídos frente a los del manifiesto
    (`isin_web` o, si la web no lo da, `isin_pdf`; `clase`), y cobertura por campo (cuántos no son null)."""
    from kid_pipeline.reglas import CAMPOS

    cuenta, cobertura, avisos = Counter(), Counter(), []
    for r, _ in kids:
        sha = r["sha256"]
        if sha not in predicciones:
            cuenta["sin_prediccion"] += 1
            continue
        p, ref = predicciones[sha], f"{sha[:12]} ({r['gestora']})"
        cuenta["documentos"] += 1
        cobertura.update(c for c in CAMPOS if p.get(c) is not None)
        if esperado := r.get("isin_web") or r.get("isin_pdf"):
            if p.get("isin") is None:
                cuenta["isin_null"] += 1
                avisos.append(f"{ref}: sin ISIN (manifiesto {esperado})")
            elif coincide("isin", p["isin"], esperado):
                cuenta["isin_ok"] += 1
            else:
                cuenta["isin_distinto"] += 1
                avisos.append(f"{ref}: ISIN {p['isin']}, el manifiesto dice {esperado}")
        if r.get("clase"):
            cuenta["con_clase"] += 1
            if p.get("nombre_clase") is not None and coincide("nombre_clase", p["nombre_clase"], r["clase"]):
                cuenta["clase_ok"] += 1
            else:
                cuenta["clase_distinta"] += 1
                avisos.append(f"{ref}: clase {p.get('nombre_clase')}, el manifiesto dice {r['clase']}")
        elif p.get("nombre_clase") is not None:
            cuenta["clase_solo_extraida"] += 1
    n = cuenta["documentos"]
    return {**{k: cuenta[k] for k in ("documentos", "sin_prediccion", "isin_ok", "isin_distinto", "isin_null",
                                      "con_clase", "clase_ok", "clase_distinta", "clase_solo_extraida")},
            "cobertura": {c: f"{cobertura[c]}/{n}" for c in CAMPOS}, "avisos": avisos}


def evaluar(raiz: Path, referencia: Path | None = None, predicciones: Path | None = None,
            guardar: Path | None = None) -> dict:
    """Evalúa las reglas (por defecto) o las predicciones de un JSONL frente a la referencia y el manifiesto."""
    kids = kids_locales(raiz)
    if predicciones is not None:
        preds, extractor = leer_predicciones(predicciones), predicciones.stem
    else:
        preds, extractor = predecir_reglas(kids), "reglas"
    if guardar is not None:
        guardar.parent.mkdir(parents=True, exist_ok=True)
        guardar.write_text("".join(json.dumps({"sha256": s, **p}, ensure_ascii=False, default=str) + "\n"
                                   for s, p in preds.items()), encoding="utf-8")
    ruta_ref = referencia or raiz / "referencia.json"
    ref = leer_referencia(ruta_ref) if ruta_ref.exists() else {}
    return {"extractor": extractor, "referencia": evaluar_extraccion(ref, preds) if ref else None,
            "manifiesto": coherencia_manifiesto(kids, preds)}


def imprimir_evaluacion(r: dict) -> None:
    print("Extractor:", r["extractor"])
    if (ref := r["referencia"]) is None:
        print("Sin referencia (data/referencia.json): solo la coherencia con el manifiesto.")
    else:
        g = ref["global"]
        print(f"Referencia: {ref['documentos']} KID, exactitud global {g['exactitud']} ({g['aciertos']}/{g['total']})")
        for c, n in ref["por_campo"].items():
            print(f"   {c:<28} {n['exactitud']:.3f}  aciertos {n['aciertos']}/{n['total']}  null_ok "
                  f"{n['null_ok']}/{n['esperados_null']}  inventados {n['inventados']}  omitidos {n['omitidos']}  "
                  f"distintos {n['distintos']}")
        for s in ref["sin_prediccion"]:
            print("   SIN PREDICCIÓN:", s[:12])
        for d in ref["discrepancias"]:
            print(f"   DISCREPANCIA {d['sha256'][:12]} {d['campo']}: esperado {d['esperado']!r}, obtenido "
                  f"{d['obtenido']!r}")
    m = r["manifiesto"]
    print(f"Manifiesto: {m['documentos']} KID con predicción ({m['sin_prediccion']} sin ella); ISIN {m['isin_ok']} "
          f"iguales, {m['isin_distinto']} distintos, {m['isin_null']} null; clase {m['clase_ok']}/{m['con_clase']} "
          f"iguales ({m['clase_solo_extraida']} extraídas sin clase en el manifiesto)")
    print("   cobertura:", ", ".join(f"{c} {v}" for c, v in m["cobertura"].items()))
    for a in m["avisos"]:
        print("   AVISO:", a)


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
    m = sub.add_parser("markdown")
    m.add_argument("--local", nargs="?", default=RAIZ_LOCAL, const=RAIZ_LOCAL, type=Path)
    m.add_argument("--sobrescribir", action="store_true", help="vuelve a convertir lo ya convertido")
    e = sub.add_parser("extract")
    e.add_argument("--todos", action="store_true", help="reprocesa también lo ya extraído")
    e.add_argument("--local", nargs="?", const=RAIZ_LOCAL, type=Path,
                   help="extrae el Markdown de data/ a data/extraccion/<modelo>.jsonl, sin S3 ni base de datos")
    e.add_argument("--modelo", help="ID del modelo o perfil de inferencia de Bedrock (defecto: BEDROCK_MODEL_ID)")
    e.add_argument("--mecanismo", choices=["herramienta", "formato"], default="herramienta", help="D-2.1")
    e.add_argument("--limite", type=int, help="como mucho N documentos (para probar)")
    ev = sub.add_parser("evaluar")
    ev.add_argument("--local", nargs="?", default=RAIZ_LOCAL, const=RAIZ_LOCAL, type=Path)
    ev.add_argument("--referencia", type=Path, help="defecto <local>/referencia.json")
    ev.add_argument("--predicciones", type=Path, help="JSONL de un modelo (una línea por sha256); sin él, las reglas")
    ev.add_argument("--guardar", type=Path, help="escribe las predicciones evaluadas en un JSONL")
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
    elif args.fase == "markdown":
        r = markdown_local(args.local, args.sobrescribir)
        print(f"{r['convertidos']} convertidos, {r['reutilizados']} reutilizados, {len(r['fallos'])} fallos")
        for f in r["fallos"]:
            print("FALLO:", f)
        return 1 if r["fallos"] else 0
    elif args.fase == "evaluar":
        imprimir_evaluacion(evaluar(args.local, args.referencia, args.predicciones, args.guardar))
    elif args.local is not None:
        cfg = Config.desde_entorno()
        modelo = args.modelo or cfg.modelo_bedrock
        if not modelo:
            p.error("falta --modelo (o la variable de entorno BEDROCK_MODEL_ID)")
        r = extract_local(args.local, modelo, args.mecanismo, args.limite, cfg.region)
        print(f"{r['modelo']}: {r['extraidos']} extraídos, {r['ya_estaban']} ya estaban, {len(r['fallos'])} fallos "
              f"-> {r['destino']}")
        for f in r["fallos"]:
            print("FALLO:", f)
        return 1 if r["fallos"] else 0
    else:
        extract(args.todos)
    return 0


if __name__ == "__main__":
    sys.exit(main())
