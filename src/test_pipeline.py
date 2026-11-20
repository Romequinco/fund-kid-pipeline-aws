"""Pruebas sin AWS: esquema, captura, claves de S3, salida de Bedrock, Data API y la API con una base de datos falsa."""

import copy
import hashlib
import json
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api
import kid_pipeline.capture as capture_mod
import pipeline
from kid_pipeline import reglas
from kid_pipeline.capture import (
    FUENTES,
    Azvalor,
    Bestinver,
    Cobas,
    Documento,
    Informe,
    KidEnlace,
    SesionEducada,
    WebCambiada,
    capturar,
    clase_en,
    es_enlace_kid,
    fecha_en_nombre,
    isin_del_pdf,
    prohibidos_con_comodin,
    sopa,
    tipo_documento,
    validar_pdf,
)
from kid_pipeline.db import UPSERT_KID, BaseDatos, parametro
from kid_pipeline.extract import (
    HERRAMIENTA,
    coherencia,
    extraer,
    leer_respuesta,
    peticion,
    revisar,
    verificar_evidencias,
)
from kid_pipeline.reglas import extraer_reglas, fecha_documento, periodo_mantenimiento, sri
from kid_pipeline.schema import (
    CAMPOS,
    Kid,
    comprobar_estricto,
    esquema_json,
    faltan_obligatorios,
    isin_valido,
    recuento,
)
from kid_pipeline.storage import (
    clave_manifiesto,
    clave_pdf,
    comparar,
    escribir_manifiesto_local,
    guardar_local,
    linea_manifiesto,
    metadatos,
    registro,
    vigentes,
)
from pipeline import clave_texto, coherencia_manifiesto, coincide, evaluar_extraccion, leer_predicciones

DOC = Documento(KidEnlace("cobas", "https://ejemplo.es/kid.pdf", "https://ejemplo.es/fondo", isin_web="ES0113900J37"),
                b"%PDF-1.7 prueba", datetime(2026, 11, 19, 10, 0, tzinfo=UTC))


@pytest.mark.parametrize("isin", ["ES0113900J37", "US0378331005", "IE00B03HCZ61"])
def test_isin_valido(isin):
    assert isin_valido(isin)


@pytest.mark.parametrize("isin", ["ES0113900J38", "ES011390", "es0113900j37"])
def test_isin_no_valido(isin):
    assert not isin_valido(isin)


def test_kid_normaliza_y_valida():
    assert Kid(isin="es 0113900J37").isin == "ES0113900J37"
    with pytest.raises(ValidationError):
        Kid(sri=8)
    with pytest.raises(ValidationError):
        Kid(isin="ES0113900J38")


def test_campos_ausentes_quedan_a_null():
    kid = Kid(isin="ES0113900J37", nombre_producto="Fondo", gestora="Gestora")
    assert kid.costes_salida_pct is None
    assert faltan_obligatorios(kid) == ["sri"]


def test_esquema_tiene_los_campos_del_anexo_a():
    campos = set(esquema_json()["properties"])
    assert {"isin", "nombre_producto", "nombre_clase", "gestora", "fecha_documento", "sri",
            "periodo_mantenimiento_anios", "gastos_corrientes_pct", "costes_entrada_pct",
            "costes_salida_pct"} <= campos


def test_robots_con_comodines():
    robots = "User-agent: *\nDisallow: /*.pdf$\nDisallow: /privado/\n\nUser-agent: otro\nDisallow: /*"
    patrones = prohibidos_con_comodin(robots)
    assert len(patrones) == 1
    assert patrones[0].match("/media/kid-fondo.pdf")
    assert not patrones[0].match("/fondos-de-inversion/fondo/")


def test_clave_s3_depende_solo_del_contenido():
    otro = Documento(KidEnlace("cobas", "https://otra.url/kid.pdf", "x"), DOC.contenido, datetime.now(UTC))
    assert clave_pdf(DOC) == clave_pdf(otro) == f"kid/cobas/{DOC.sha256}.pdf"
    assert metadatos(DOC)["descargado-en"].startswith("2026-11-19T10:00")
    assert clave_manifiesto(DOC.descargado_en) == "manifest/20261119T100000Z.jsonl"


def test_esquema_cumple_el_modo_estricto():
    esquema = esquema_json()
    texto = str(esquema)
    assert esquema["additionalProperties"] is False
    assert not any(k in texto for k in ("'minimum'", "'maximum'", "'default'"))
    assert set(esquema["required"]) == set(esquema["properties"])


def test_peticion_bedrock_fuerza_la_herramienta():
    p = peticion("Texto del KID", "modelo")
    assert p["toolConfig"]["toolChoice"] == {"tool": {"name": HERRAMIENTA}}
    assert p["toolConfig"]["tools"][0]["toolSpec"]["strict"] is True
    assert "Texto del KID" in p["messages"][0]["content"][0]["text"]  # el Markdown del KID, no el PDF (D-2.4)


def test_leer_respuesta_bedrock():
    respuesta = {"stopReason": "tool_use", "output": {"message": {"content": [
        {"toolUse": {"name": HERRAMIENTA, "input": {"isin": "ES0113900J37", "sri": 4, "fecha_documento": "2026-01-31"}}}
    ]}}}
    kid = leer_respuesta(respuesta)
    assert (kid.sri, kid.fecha_documento) == (4, date(2026, 1, 31))
    with pytest.raises(ValueError):
        leer_respuesta({"stopReason": "end_turn", "output": {"message": {"content": [{"text": "{}"}]}}})


def test_parametros_data_api():
    assert parametro("x", None)["value"] == {"isNull": True}
    assert parametro("x", 4)["value"] == {"longValue": 4}
    assert parametro("x", 1.25)["typeHint"] == "DECIMAL"
    assert parametro("x", date(2026, 1, 31))["typeHint"] == "DATE"
    assert parametro("x", DOC.descargado_en)["typeHint"] == "TIMESTAMP"


class RdsFalso:
    def __init__(self):
        self.llamadas = []

    def execute_statement(self, **kw):
        self.llamadas.append(kw)
        return {"formattedRecords": "[]"}


def test_carga_idempotente_y_esquema():
    rds = RdsFalso()
    db = BaseDatos(rds, "arn:cluster", "arn:secret", "kid")
    db.guardar_kid(DOC.sha256, Kid(isin="ES0113900J37", sri=3), "modelo")
    assert "ON CONFLICT (documento_sha256) DO UPDATE" in UPSERT_KID
    assert {p["name"] for p in rds.llamadas[0]["parameters"]} >= {"documento_sha256", "isin", "sri", "modelo"}
    db.crear_esquema()
    sentencias = [c["sql"] for c in rds.llamadas[1:]]
    assert len(sentencias) == 4 and not any(s.lstrip().startswith("--") for s in sentencias)


# --- API ---


class DbFalsa:
    def __init__(self, filas):
        self.filas, self.ultima = filas, None

    def consultar(self, sql, **valores):
        self.ultima = (sql, valores)
        return self.filas


def cliente(filas):
    db = DbFalsa(filas)
    api.db = lambda: db  # sustituye la conexión real
    return TestClient(api.app), db


def test_health():
    c, _ = cliente([])
    assert c.get("/health").json() == {"status": "ok"}


def test_fondos_con_filtros():
    c, db = cliente([{"isin": "ES0113900J37"}])
    assert c.get("/fondos", params={"gestora": "cobas", "sri_min": 3}).status_code == 200
    sql, valores = db.ultima
    assert "gestora_fuente = :gestora" in sql and valores == {"sri_min": 3, "sri_max": 7, "gestora": "cobas"}
    assert c.get("/fondos", params={"sri_max": 9}).status_code == 422


def test_fondo_inexistente():
    c, _ = cliente([])
    assert c.get("/fondos/ES0113900J37").status_code == 404


# --- Captura: parseo con páginas guardadas (src/fixtures/, 19/11/2026) ---

FIX = Path(__file__).with_name("fixtures")


def fix(nombre: str) -> bytes:
    return (FIX / f"{nombre}.html").read_bytes()


def test_bestinver_listado_excluye_paginas_informativas():
    fichas = Bestinver().fichas(fix("bestinver_listado"))
    assert len(fichas) == 23
    assert all(f.startswith("https://www.bestinver.es/fondos-de-inversion/") and f.endswith("/") for f in fichas)
    assert not any(f"/{slug}/" in f for f in fichas for slug in Bestinver.NO_FONDOS)


def test_bestinver_ficha():
    url = "https://www.bestinver.es/fondos-de-inversion/bestinver-bolsa/"
    [k] = Bestinver().kids(fix("bestinver_ficha"), url)
    assert k.url_pdf == "https://www.bestinver.es/wp-content/uploads/bestinver_bolsa_fi_datos_fundamentales.pdf"
    assert (k.isin_web, k.fondo, k.url_ficha, k.clase) == ("ES0147622031", "Bestinver Bolsa", url, None)
    assert Bestinver().kids(fix("bestinver_sin_kid"), url) == []
    assert Bestinver().otras_fichas(fix("bestinver_ficha"), url) == []  # «Resumen», «Rentabilidad»: no son clases
    assert not Bestinver.respeta_robots and "profesor" in Bestinver.motivo_robots


def test_bestinver_ficha_con_clases():
    """Un fondo con clases: la ficha principal es la clase B y enlaza una ficha por cada otra clase."""
    url = "https://www.bestinver.es/fondos-de-inversion/bestinver-corto-plazo/"
    [k] = Bestinver().kids(fix("bestinver_clases"), url)
    assert k.url_pdf.endswith("/Bestinver_corto_plazo_clase_b_fi_datos_fundamentales.pd_.pdf")  # sic, sin ?h=
    assert (k.clase, k.isin_web) == ("Clase B", "ES0183091000")
    assert Bestinver().otras_fichas(fix("bestinver_clases"), url) == [
        "https://www.bestinver.es/fondos-de-inversion/bestinver-corto-plazo-clase-r/",
        "https://www.bestinver.es/fondos-de-inversion/bestinver-corto-plazo-clase-z/"]


def test_azvalor():
    fichas = Azvalor().fichas(fix("azvalor_listado"))
    assert len(fichas) == 5 and all("/fondos-de-inversion/" in f for f in fichas)
    [k] = Azvalor().kids(fix("azvalor_ficha"), "https://www.azvalor.com/fondos-de-inversion/azvalor-internacional/")
    assert k.url_pdf == "https://www.azvalor.com/wp-content/uploads/2026/01/DFP-Internacional-09.01.2026.pdf"
    assert (k.isin_web, k.fecha_web) == ("ES0112611001", "2026-01-09")


def test_cobas_solo_fondos_y_una_clase_por_bloque():
    fichas = Cobas().fichas(fix("cobas_listado"))
    assert len(fichas) == 7 and all("/productos/inversion-libre/" in f for f in fichas)  # sin planes de pensiones
    kids = Cobas().kids(fix("cobas_ficha"), "https://www.cobasam.com/productos/inversion-libre/cobas_internacional/")
    assert {k.clase: k.isin_web for k in kids} == {"Clase A": "ES0119199034", "Clase B": "ES0119199026",
                                                   "Clase C": "ES0119199000", "Clase D": "ES0119199018"}
    assert all(k.url_pdf.startswith("https://cobas-static-content.s3") and k.url_pdf.endswith(".pdf") for k in kids)
    [sicav] = Cobas().kids(fix("cobas_sicav"), "https://www.cobasam.com/productos/inversion-libre/cobas_value_sicav/")
    assert (sicav.clase, sicav.isin_web) == (None, "ES0155441035")


# --- Captura: robustez del parseo con HTML sintético ---

def ancla(html: str):
    return sopa(html).find("a")


@pytest.mark.parametrize("html,es_kid", [
    ('<a href="/a.pdf">DFI</a>', True),
    ('<a href="/a.pdf">KID</a>', True),
    ('<a href="/a.pdf">Documento de Datos Fundamentales para el Inversor</a>', True),
    ('<a href="/a.pdf">DATOS  FUNDAMENTALES</a>', True),
    ('<a href="/a.pdf">Información PRIIPs</a>', True),
    ('<a href="/a.pdf">Folleto simplificado (DFP)</a>', True),
    ('<a href="/a.pdf" title="Key Information Document"><img src="i.png"></a>', True),
    ('<a href="/kid/dfi-fondo.pdf"><i class="icono"></i></a>', True),  # sin rótulo: decide el nombre del fichero
    ('<a href="/docs/fondo_datos_fundamentales.pdf">Descargar PDF</a>', True),
    ('<a href="/a.pdf">Folleto completo</a>', False),
    ('<a href="/a.pdf">Escenarios de rentabilidad PRIIP</a>', False),
    ('<a href="/a.pdf">Informe semestral</a>', False),
    ('<a href="/que-es-el-kid/">¿Qué es el KID?</a>', False),  # no es un PDF
    ('<a href="/informe-anual.pdf">Descargar</a>', False),
])
def test_rotulos_del_kid(html, es_kid):
    assert es_enlace_kid(ancla(html)) is es_kid


def test_urls_raras_y_repetidas():
    html = ('<h1>Fondo Ñ</h1>ISIN ES0119199034'
            '<a href=" ../../docs/KID Fondo Ñ.pdf ">KID</a>'
            '<a href="/docs/KID%20Fondo%20%C3%91.pdf">Datos fundamentales</a>'  # el mismo, ya codificado
            '<a href="//cdn.g.es/dfi.pdf#page=2">DFI</a>'
            "<a href=\"javascript:abrir('kid.pdf')\">KID</a>")
    kids = Azvalor().kids(html.encode(), "https://g.es/fondos/uno/")
    assert [k.url_pdf for k in kids] == ["https://g.es/docs/KID%20Fondo%20%C3%91.pdf", "https://cdn.g.es/dfi.pdf"]
    assert all(k.isin_web is None for k in kids)  # dos KID y un ISIN: no se sabe de cuál es


def test_varios_kid_en_una_ficha():
    html = ("<h1>Fondo</h1>"
            '<div><h3>Clase A</h3>ISIN ES0119199034 <a href="/a.pdf">KID</a></div>'
            '<div><h3>Clase B</h3>ISIN ES0119199026 <a href="/b.pdf">KID</a></div>')
    kids = Azvalor().kids(html.encode(), "https://g.es/fondos/uno/")
    assert [(k.clase, k.isin_web) for k in kids] == [("Clase A", "ES0119199034"), ("Clase B", "ES0119199026")]


@pytest.mark.parametrize("cadena,clase", [
    ("bestinver_renta_clase_b_fi_datos_fundamentales.pdf", "Clase B"),
    ("/Cobas+Iberia/Clase+C/dfi-iberia.pdf", "Clase C"),
    ("ES_KIID-BESTINVER-SHARPE-HIGH-YIELD-CL-B2.pdf", "Clase B2"),
    ("/fondos-de-inversion/bestinver-renta-clase-z/", "Clase Z"),
    ("/productos/inversion-libre/cobas_concentrados_fil/", None),
    ("la clase de activo", None),
])
def test_clase_en(cadena, clase):
    assert clase_en(cadena) == clase


@pytest.mark.parametrize("nombre,fecha", [
    ("DFP-Iberia-09.01.2026.pdf", "2026-01-09"), ("5-DFP-Capital-31.12.2025-sef-v2.pdf", "2025-12-31"),
    ("kid_2026-03-31.pdf", "2026-03-31"), ("Flyer-ES-24.2.2026.pdf", "2026-02-24"),
    ("DFP-31.02.2026.pdf", None), ("dfi-renta.pdf", None),
])
def test_fecha_en_nombre(nombre, fecha):
    assert fecha_en_nombre(f"https://g.es/wp-content/uploads/2026/01/{nombre}") == fecha


def test_tipo_de_documento_e_isin_del_pdf():
    assert tipo_documento("DOCUMENTO DE DATOS FUNDA MENTALES Indicador resumido de riesgo") == "KID PRIIPs"
    assert tipo_documento("Datos fundamentales para el inversor. Perfil de riesgo y remuneración") == "KIID UCITS"
    assert tipo_documento("Folleto completo del fondo") is None
    assert isin_del_pdf("Name of Product: X CL B2 ISIN: LU3334273896") == "LU3334273896"
    assert isin_del_pdf("ISIN ES0119199034 y ES0119199026", "ES0119199026") == "ES0119199026"
    assert isin_del_pdf("Sin código") is None


# --- Captura: red simulada ---

class Respuesta:
    def __init__(self, contenido=b"", estado=200, cabeceras=None):
        self.content, self.status_code, self.ok = contenido, estado, estado < 400
        self.text, self.headers = contenido.decode("latin-1"), cabeceras or {}

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"{self.status_code}")


class HttpFalso:
    """Una respuesta por URL (bytes, Respuesta o excepción), o una lista que se consume en orden."""

    def __init__(self, paginas):
        self.paginas, self.pedidas, self.cabeceras, self.headers = paginas, [], [], {}

    def get(self, url, timeout=None, headers=None):
        self.pedidas.append(url)
        self.cabeceras.append(headers)
        r = self.paginas.get(url)
        if isinstance(r, list):
            r = r.pop(0)
        if isinstance(r, Exception):
            raise r
        return r if isinstance(r, Respuesta) else Respuesta(r or b"", 200 if r is not None else 404)


def sesion(paginas) -> SesionEducada:
    s = SesionEducada(pausa_s=0, reintentos=1)
    s.http = HttpFalso(paginas)
    return s


PDF = b"%PDF-1.4 " + b"x" * 20_000


def test_robots_5xx_prohibe_y_4xx_permite():
    s = sesion({"https://a.es/robots.txt": Respuesta(b"", 503), "https://b.es/robots.txt": Respuesta(b"", 418)})
    assert not s.permitido("https://a.es/x.pdf")
    assert s.permitido("https://b.es/x.pdf")
    with pytest.raises(PermissionError):
        s.get("https://a.es/x.pdf")


def test_reintenta_los_5xx_y_el_429(monkeypatch):
    esperas = []
    monkeypatch.setattr(capture_mod.time, "sleep", esperas.append)
    s = sesion({"https://c.es/kid.pdf": [Respuesta(b"", 502), Respuesta(PDF)],
                "https://c.es/otro.pdf": [Respuesta(b"", 429, {"Retry-After": "7"}), Respuesta(PDF)]})
    assert s.get("https://c.es/kid.pdf", respeta_robots=False).content == PDF
    assert s.get("https://c.es/otro.pdf", respeta_robots=False).content == PDF
    assert 7.0 in esperas  # respeta el Retry-After del servidor
    s = sesion({"https://c.es/kid.pdf": [Respuesta(b"", 503), Respuesta(b"", 503)]})
    with pytest.raises(requests.HTTPError):  # agotados los reintentos, el error se ve
        s.get("https://c.es/kid.pdf", respeta_robots=False)


def test_validar_pdf():
    validar_pdf(PDF, "u")
    validar_pdf(b"\xef\xbb\xbf" + PDF, "u")  # bytes antes de %PDF: la especificación lo admite
    for malo in (b"<html>", b"%PDF corto"):
        with pytest.raises(ValueError):
            validar_pdf(malo, "u")


class FuenteFalsa(Azvalor):
    inicio = "https://f.es/fondos-de-inversion/"


def test_fuente_falla_claro_si_la_web_cambia():
    with pytest.raises(WebCambiada):
        list(FuenteFalsa().enlaces(sesion({FuenteFalsa.inicio: b"<html></html>"}), Informe("f")))
    listado = b'<a href="/fondos-de-inversion/uno/">1</a><a href="/fondos-de-inversion/dos/">2</a>'
    paginas = {FuenteFalsa.inicio: listado, "https://f.es/fondos-de-inversion/uno/": b"<h1>Uno</h1>",
               "https://f.es/fondos-de-inversion/dos/": requests.ConnectionError("caida")}
    informe = Informe("f")
    with pytest.raises(WebCambiada):
        list(FuenteFalsa().enlaces(sesion(paginas), informe))
    assert (informe.fichas, informe.sin_kid, len(informe.errores)) == (2, ["https://f.es/fondos-de-inversion/uno/"], 1)


def test_enlaces_sigue_las_fichas_de_cada_clase():
    base = "https://f.es/fondos-de-inversion/"
    menu = (f'<a href="{base}f/">Clase B</a><a href="{base}f-clase-r">Clase R</a>'
            f'<a href="{base}f-clase-z/">Clase&nbsp;Z</a><a href="{base}f/rentabilidad/">Rentabilidad</a>')
    paginas = {base: f'<a href="{base}f/">F</a>'.encode(),
               f"{base}f/": f'{menu}ISIN ES0119199034 <a href="/b.pdf">Datos fundamentales</a>'.encode(),
               f"{base}f-clase-r/": f'{menu}ISIN ES0119199026 <a href="/r.pdf">Datos fundamentales</a>'.encode(),
               f"{base}f-clase-z/": f'{menu}<a href="/b.pdf">Datos fundamentales</a>'.encode()}  # enlaza el de B
    informe = Informe("f")
    kids = list(FuenteFalsa().enlaces(sesion(paginas), informe))
    assert [(k.url_pdf, k.isin_web) for k in kids] == [("https://f.es/b.pdf", "ES0119199034"),
                                                        ("https://f.es/r.pdf", "ES0119199026")]
    assert kids[1].clase == "Clase R"  # de la URL de su ficha
    assert (informe.fichas, informe.enlaces, informe.sin_kid) == (3, 2, [f"{base}f-clase-z/"])


def test_capturar_deduplica_y_registra_errores():
    listado = b"".join(f'<a href="/fondos-de-inversion/f{i}/">f</a>'.encode() for i in range(3))
    ficha = '<h1>F</h1>ISIN ES0112611001 <a href="/{}.pdf">Folleto simplificado (DFP)</a>'
    paginas = {FuenteFalsa.inicio: listado, "https://f.es/robots.txt": b"",
               "https://f.es/a.pdf": PDF, "https://f.es/b.pdf": PDF, "https://f.es/c.pdf": b"<html>no</html>"}
    for i, n in enumerate("abc"):
        paginas[f"https://f.es/fondos-de-inversion/f{i}/"] = ficha.format(n).encode()
    informe = Informe("f")
    docs = list(capturar(FuenteFalsa(), sesion(paginas), informe, set()))
    assert len(docs) == 1 and docs[0].robots == "respetado"
    assert (informe.enlaces, informe.descargados, informe.duplicados, len(informe.errores)) == (3, 1, 1, 1)


def test_capturar_lee_el_pdf_y_rechaza_lo_que_no_es_kid():
    listado = b'<a href="/fondos-de-inversion/f0/">f</a><a href="/fondos-de-inversion/f1/">f</a>'
    ficha = '<h1>F</h1><a href="/{}.pdf">Folleto simplificado (DFP)</a>'
    paginas = {FuenteFalsa.inicio: listado, "https://f.es/robots.txt": b"",
               "https://f.es/a.pdf": pdf_con_texto(["Documento de datos fundamentales", "ISIN: ES0112611001"]),
               "https://f.es/b.pdf": pdf_con_texto(["Folleto completo del fondo"])}
    for i, n in enumerate("ab"):
        paginas[f"https://f.es/fondos-de-inversion/f{i}/"] = ficha.format(n).encode()
    informe = Informe("f")
    [doc] = list(capturar(FuenteFalsa(), sesion(paginas), informe, set()))
    assert doc.huella == {"paginas": 1, "isin_pdf": "ES0112611001", "tipo_documento": "KID PRIIPs"}
    assert registro(doc)["isin_pdf"] == "ES0112611001" and "no parece un KID" in informe.errores[0]


def test_descarga_condicional():
    url, kid = "https://f.es/a.pdf", pdf_con_texto(["Documento de datos fundamentales"])
    previo = {"url_pdf": url, "sha256": hashlib.sha256(kid).hexdigest(), "etag": '"v1"', "last_modified": "Wed, 01 "
              "Oct 2026 10:00:00 GMT", "descargado_en": "2026-10-01T10:00:00+00:00", "s3_key": "kid/f/x.pdf"}
    enlace = KidEnlace("f", url, "https://f.es/ficha/")
    s = sesion({url: Respuesta(b"", 304)})
    doc = s.descargar(enlace, False, "m", previo, lambda r: kid)
    assert (doc.http, doc.contenido, doc.descargado_en) == (304, kid, datetime(2026, 10, 1, 10, tzinfo=UTC))
    assert doc.comprobado_en > doc.descargado_en and doc.etag == '"v1"'
    assert s.http.cabeceras == [{"If-None-Match": '"v1"', "If-Modified-Since": "Wed, 01 Oct 2026 10:00:00 GMT"}]
    # sin copia guardada (o con otra), el 304 no sirve: se descarga normal y se guardan las cabeceras nuevas
    s = sesion({url: [Respuesta(b"", 304), Respuesta(kid, 200, {"ETag": '"v2"'})]})
    doc = s.descargar(enlace, False, "m", previo, lambda r: None)
    assert (doc.http, doc.etag, s.http.cabeceras[1]) == (200, '"v2"', None)
    assert registro(doc)["comprobado_en"] == registro(doc)["descargado_en"]
    with pytest.raises(ValueError):  # un 304 sin haberlo pedido no trae contenido: se rechaza, no rompe
        sesion({url: Respuesta(b"", 304)}).descargar(enlace, False, "m")


def test_un_listado_caido_no_tumba_la_captura(tmp_path, monkeypatch):
    monkeypatch.setattr(pipeline, "SesionEducada", lambda: sesion({FuenteFalsa.inicio: requests.ConnectionError("x")}))
    monkeypatch.setattr(pipeline, "FUENTES", {"f": FuenteFalsa})
    [informe], cambios = pipeline.capture(["f"], tmp_path)
    assert informe.errores and informe.obtenidos == 0 and cambios["nuevos"] == []


def test_la_excepcion_de_robots_es_solo_para_el_servidor_de_la_gestora():
    class SinRobots(FuenteFalsa):
        respeta_robots, motivo_robots = False, "prueba"
    listado = b'<a href="/fondos-de-inversion/f0/">f</a><a href="/fondos-de-inversion/f1/">f</a>'
    paginas = {SinRobots.inicio: listado, "https://f.es/robots.txt": b"User-agent: *\nDisallow: /*.pdf$",
               "https://otro.es/robots.txt": b"User-agent: *\nDisallow: /*.pdf$", "https://f.es/a.pdf": PDF,
               "https://f.es/fondos-de-inversion/f0/": b'<a href="/a.pdf">KID</a>',
               "https://f.es/fondos-de-inversion/f1/": b'<a href="https://otro.es/b.pdf">KID</a>'}
    informe = Informe("f")
    [doc] = list(capturar(SinRobots(), sesion(paginas), informe, set()))
    assert doc.robots == "excepción: prueba" and "robots.txt no permite https://otro.es/b.pdf" in informe.errores[0]


# --- Manifiestos: lo vigente y los cambios ---

def reg(gestora, sha, url, isin_web=None, isin_pdf=None):
    return {"gestora": gestora, "sha256": sha, "url_pdf": url, "isin_web": isin_web, "isin_pdf": isin_pdf}


def test_vigentes_es_el_ultimo_manifiesto_de_cada_gestora():
    a, b, c = reg("g1", "a", "u1"), reg("g2", "b", "u2"), reg("g1", "c", "u3")
    assert vigentes([("20261102T000000Z.jsonl", [c]), ("20261101T000000Z.jsonl", [a, b])]) == [c, b]


def test_comparar_detecta_nuevos_cambiados_y_desaparecidos():
    antes = [reg("g", "s1", "u1", "ES0112611001"), reg("g", "s2", "u2", "ES0112616000"), reg("g", "s3", "u3"),
             reg("g", "s4", "u4", "ES0112609005"), reg("h", "s5", "u5", "ES0112602000")]
    ahora = [reg("g", "s1", "u1", "ES0112611001"),  # igual
             reg("g", "s9", "u2-nueva-fecha", "ES0112616000"),  # mismo ISIN, otro PDF y otra URL: cambiado
             reg("g", "s3", "u3", isin_pdf="ES0112601002"),  # el registro antiguo no tenía ISIN: se empareja por URL
             reg("g", "s7", "u7", "ES0119199034")]  # nuevo
    c = comparar(antes, ahora, completas={"g"})
    assert [r["sha256"] for r in c["nuevos"]] == ["s7"]
    assert [(a["sha256"], b["sha256"]) for a, b in c["cambiados"]] == [("s2", "s9")]
    assert len(c["sin_cambios"]) == 2
    assert [r["sha256"] for r in c["desaparecidos"]] == ["s4"]  # «h» no se capturó completa: no cuenta


# --- Destino local, manifiesto y comprobaciones ---

def pdf_con_texto(lineas: list[str]) -> bytes:
    """PDF mínimo de una página con texto, para probar `verificar` sin ficheros reales."""
    contenido = "BT /F1 10 Tf 50 750 Td " + " ".join(f"({t}) Tj 0 -14 Td" for t in lineas) + " ET"
    objetos = ["<< /Type /Catalog /Pages 2 0 R >>", "<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
               "<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
               "/Resources << /Font << /F1 5 0 R >> >> >>",
               f"<< /Length {len(contenido)} >>\nstream\n{contenido}\nendstream",
               "<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"]
    salida, offsets = b"%PDF-1.4\n", []
    for i, o in enumerate(objetos, 1):
        offsets.append(len(salida))
        salida += f"{i} 0 obj\n{o}\nendobj\n".encode()
    xref = len(salida)
    salida += f"xref\n0 {len(objetos) + 1}\n0000000000 65535 f \n".encode()
    salida += b"".join(f"{o:010d} 00000 n \n".encode() for o in offsets)
    salida += f"trailer\n<< /Size {len(objetos) + 1} /Root 1 0 R >>\nstartxref\n{xref}\n%%EOF".encode()
    return salida + b"\n%" + b"0" * 12_000  # relleno: un KID real pesa más de 10 KB


def test_guardar_local_y_verificar(tmp_path):
    momento = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
    docs = [Documento(KidEnlace(g, f"https://{g}.es/{i}.pdf", f"https://{g}.es/f{i}", isin_web=isin),
                      pdf_con_texto(["Documento de datos fundamentales", f"ISIN: {isin}"]), momento)
            for i, (g, isin) in enumerate([("cobas", "ES0119199034"), ("azvalor", "ES0112611001")])]
    lineas = [linea_manifiesto(d) for d in docs if guardar_local(tmp_path, d)]
    escribir_manifiesto_local(tmp_path, momento, lineas)
    assert (tmp_path / clave_pdf(docs[0])).read_bytes() == docs[0].contenido
    assert set(registro(docs[0])) >= {"sha256", "url_pdf", "url_ficha", "descargado_en", "robots", "isin_web",
                                      "isin_pdf", "paginas", "tipo_documento", "etag", "comprobado_en"}
    r = pipeline.verificar(tmp_path)
    assert (r["documentos"], r["fuentes"], r["isin_web_en_pdf"], r["fallos"]) == (2, 2, 2, [])
    assert not r["cumple_minimos"]  # 2 < 15 documentos
    (tmp_path / clave_pdf(docs[1])).write_bytes(pdf_con_texto(["Otro documento"]))
    fallos = pipeline.verificar(tmp_path)["fallos"]
    assert any("SHA-256" in f for f in fallos) and any("no parece un KID" in f for f in fallos)


def test_verificar_clase_fecha_isin_y_repetidos(tmp_path):
    momento = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)

    def doc(i, lineas, **kw):
        enlace = KidEnlace("g", f"https://g.es/{i}.pdf", "https://g.es/f", **{"fondo": f"Fondo {i}", **kw})
        return Documento(enlace, pdf_con_texto(lineas), momento)
    kid = "Documento de datos fundamentales"
    buenos = [doc(0, [kid, "Fondo FI Clase A ISIN: ES0119199034"], clase="Clase A", isin_web="ES0119199034"),
              doc(1, [kid, "ISIN: ES0112611001", "Fecha: 9 de enero de 2026"], fecha_web="2026-01-09"),
              doc(2, [kid, "ISIN: LU3334273896"])]  # 1 y 2, sin ISIN en la web: lo da el PDF
    malos = [doc(3, [kid, "Fondo FI Clase B ISIN: ES0119199026"], clase="Clase A", isin_web="ES0119199026"),
             doc(4, [kid, "ISIN: ES0112616000", "Fecha: 19 de enero de 2026"], fecha_web="2026-01-09"),
             doc(5, [kid, "ISIN: ES0119199034 otra vez"], fondo="Otro")]
    for d in buenos + malos:
        guardar_local(tmp_path, d)
    escribir_manifiesto_local(tmp_path, momento, [linea_manifiesto(d) for d in buenos])
    r = pipeline.verificar(tmp_path)
    assert (r["fallos"], r["con_isin"], r["isin_solo_pdf"], r["con_clase"], r["con_fecha_web"]) == ([], 3, 2, 1, 1)
    escribir_manifiesto_local(tmp_path, datetime(2026, 11, 20, tzinfo=UTC),
                              [linea_manifiesto(d) for d in buenos + malos])
    fallos = pipeline.verificar(tmp_path)["fallos"]
    assert any("la web dice Clase A y el PDF ['Clase B']" in f for f in fallos)
    assert any("(2026-01-09) no aparece" in f for f in fallos)  # «19 de enero» no vale por «9 de enero»
    assert any(f.startswith("ISIN ES0119199034: 2 KID vigentes") for f in fallos)
    assert pipeline.verificar(tmp_path)["documentos"] == 6  # solo el último manifiesto de la gestora


def test_metadatos_s3_en_ascii():
    doc = Documento(KidEnlace("cobas", "https://e.es/Política.pdf", "https://e.es/ñ"), PDF, datetime.now(UTC))
    assert all(v.isascii() for v in metadatos(doc).values())


# --- Webs reales (pytest -m red): detecta si una gestora cambia su web ---

@pytest.mark.red
@pytest.mark.parametrize("nombre,minimo", [("bestinver", 35), ("azvalor", 4), ("cobas", 15)])
def test_web_real(nombre, minimo):
    kids = list(FUENTES[nombre]().enlaces(SesionEducada(pausa_s=1), Informe(nombre)))
    assert len(kids) >= minimo
    assert all(k.url_pdf.lower().split("?")[0].endswith(".pdf") for k in kids)
    assert all(isin_valido(k.isin_web) for k in kids if k.isin_web)
    assert len({k.url_pdf for k in kids}) == len(kids)


# --- PDF -> Markdown del KID (texto.py) ---

def test_normalizar_y_aparece():
    from kid_pipeline.texto import aparece, normalizar

    assert normalizar("**Gastos** corrientes: 1, 78 %") == "gastoscorrientes:1,78%"
    assert aparece("Indicador de riesgo: 4", "| **Indicador de riesgo:** | 4 |")
    assert aparece("Período de mantenimiento", "PERIODO DE MANTENIMIENTO recomendado")
    assert not aparece("", "texto") and not aparece(None, "texto") and not aparece("5 años", "3 años")


def test_kid_markdown_solo_lee_las_paginas_del_kid(monkeypatch):
    import pymupdf

    from kid_pipeline import texto

    doc = pymupdf.open()
    for n in range(1, 6):
        doc.new_page().insert_text((72, 72), f"Pagina {n} del documento")
    pdf = doc.tobytes()
    md = texto.kid_markdown(pdf)
    assert "Pagina 3" in md and "Pagina 4" not in md  # el anexo (Cobas) no se convierte
    assert "Pagina 2" in texto.kid_markdown(pdf, paginas=2) and "Pagina 3" not in texto.kid_markdown(pdf, paginas=2)


def test_markdown_local_convierte_y_reutiliza(tmp_path):
    import pymupdf

    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), "Documento de datos fundamentales ISIN ES0112611001")
    contenido = doc.tobytes()
    momento = datetime(2026, 11, 19, 10, 0, tzinfo=UTC)
    d = Documento(KidEnlace("azvalor", "https://a.es/k.pdf", "https://a.es/f"), contenido, momento)
    guardar_local(tmp_path, d)
    escribir_manifiesto_local(tmp_path, momento, [linea_manifiesto(d)])
    assert pipeline.markdown_local(tmp_path) == {"convertidos": 1, "reutilizados": 0, "fallos": []}
    assert pipeline.markdown_local(tmp_path)["reutilizados"] == 1
    [(r, md)] = pipeline.kids_locales(tmp_path)
    assert r["sha256"] == d.sha256 and "ES0112611001" in md


# --- Evidencias por campo (D-2.4) ---
# Evidencias por campo (D-2.4): esquema estricto, extracción sobre Markdown, verificación y carga. Sin AWS.
MD = """
Denominación del producto: FONDO EJEMPLO GLOBAL, FI CLASE A

ISIN: ES0123456784 Nombre del productor del PRIIP: GESTORA DE PRUEBA SGIIC, S.A.

|**Fecha document**|**o:**<br>15 de marzo de 2026|

<!-- Start of picture text -->
4<br><!-- End of picture text -->

Hemos clasificado este producto en la clase de riesgo [4] en una escala de 7, en la que 4 significa un riesgo medio.

|**Período de ma**|**ntenimiento recomendado: 5 años**|

|**Costes de entrada**|No cobramos comisión de entrada.|0 €|
|**Costes de salida**|La comisión de salida es de 1, 50 % del importe.|150 €|
|**Comisiones de gestión y otros**<br>**costes administrativos**|1,25 % del valor de su inversión<br>al año.|125 €|
"""

ENTRADA = {  # lo que devolvería el modelo: evidencia literal y valor
    "isin_evidencia": "ISIN: ES0123456784", "isin": "ES0123456784",
    "nombre_producto_evidencia": "Denominación del producto: FONDO EJEMPLO GLOBAL, FI CLASE A",
    "nombre_producto": "Fondo Ejemplo Global, FI",
    "nombre_clase_evidencia": "FONDO EJEMPLO GLOBAL, FI CLASE A", "nombre_clase": "Clase A",
    "gestora_evidencia": "Nombre del productor del PRIIP: GESTORA DE PRUEBA SGIIC, S.A.",
    "gestora": "GESTORA DE PRUEBA SGIIC, S.A.",
    "fecha_documento_evidencia": "Fecha documento: 15 de marzo de 2026", "fecha_documento": "2026-03-15",
    "sri_evidencia": "Hemos clasificado este producto en la clase de riesgo [4] en una escala de 7", "sri": 4,
    "periodo_mantenimiento_anios_evidencia": "Período de mantenimiento recomendado: 5 años",
    "periodo_mantenimiento_anios": 5,
    "gastos_corrientes_pct_evidencia": "1,25 % del valor de su inversión al año.", "gastos_corrientes_pct": 1.25,
    "costes_entrada_pct_evidencia": "No cobramos comisión de entrada.", "costes_entrada_pct": 0,
    "costes_salida_pct_evidencia": "La comisión de salida es de 1,50 % del importe.", "costes_salida_pct": 1.5,
}


def respuesta_herramienta(entrada: dict, stop: str = "tool_use") -> dict:
    return {"stopReason": stop, "output": {"message": {"content": [
        {"text": "Registro los datos."}, {"toolUse": {"toolUseId": "t1", "name": HERRAMIENTA, "input": entrada}}]}}}


# --- Esquema y límites del modo estricto ---


def test_esquema_cumple_los_limites_del_modo_estricto():
    esquema = esquema_json()
    assert comprobar_estricto(esquema) == []
    assert recuento(esquema) == {"propiedades": 20, "opcionales": 0, "uniones": 10}
    nombres = list(esquema["properties"])
    for c in CAMPOS:  # la evidencia va justo antes de su campo y es una cadena, no una unión
        assert nombres.index(f"{c}_evidencia") == nombres.index(c) - 1
        assert esquema["properties"][f"{c}_evidencia"]["type"] == "string"
    assert {"type": "integer", "enum": [1, 2, 3, 4, 5, 6, 7]} in esquema["properties"]["sri"]["anyOf"]


def test_evidencias_nullable_pasarian_del_limite_de_uniones():
    esquema = copy.deepcopy(esquema_json())
    for c in CAMPOS:
        esquema["properties"][f"{c}_evidencia"] = {"type": ["string", "null"]}
    assert comprobar_estricto(esquema) == ["20 propiedades con unión de tipos (máximo 16)"]


def test_comprobar_estricto_detecta_cada_incumplimiento():
    malo = {"type": "object", "additionalProperties": False, "required": [],
            "properties": {f"p{i}": {"type": "string"} for i in range(13)} | {
                "n": {"type": "number", "minimum": 0},
                "lista": {"type": "array", "minItems": 2, "items": {"type": "string", "pattern": "^(?!x).*$"}},
                "sub": {"type": "object", "properties": {"a": {"type": "string"}}, "required": ["a"]},
                "nodo": {"$ref": "#/$defs/Nodo"}},
            "$defs": {"Nodo": {"type": "object", "additionalProperties": False, "required": ["hijo"],
                               "properties": {"hijo": {"$ref": "#/$defs/Nodo"}}}}}
    fallos = comprobar_estricto(malo)
    assert "#/properties/n: 'minimum' no se admite" in fallos
    assert "#/properties/lista: minItems 2 (solo 0 o 1)" in fallos
    assert "#/properties/lista/items: pattern con lookaround" in fallos
    assert "#/properties/sub: objeto sin additionalProperties: false" in fallos
    assert "#/$defs/Nodo: esquema recursivo" in fallos
    assert "17 propiedades opcionales (máximo 12)" in fallos


def test_kid_mantiene_los_campos_planos_y_la_validacion():
    kid = Kid.model_validate(ENTRADA)
    assert (kid.isin, kid.sri, kid.fecha_documento, kid.costes_entrada_pct) == ("ES0123456784", 4, date(2026, 3, 15), 0)
    assert list(kid.valores()) == list(CAMPOS) and kid.evidencias["isin"] == "ISIN: ES0123456784"
    assert Kid(isin="ES0123456784", sri_evidencia=None).sri_evidencia == ""  # null del modelo -> sin evidencia
    for malo in ({"sri": 8}, {"isin": "ES0123456785"}, {"gastos_corrientes_pct": -1}):
        with pytest.raises(ValidationError):
            Kid(**malo)


# --- Petición y respuesta de Bedrock (simuladas) ---


def test_peticion_lleva_el_markdown_y_la_herramienta_estricta():
    p = peticion(MD, "modelo")
    [bloque] = p["messages"][0]["content"]
    assert "document" not in bloque and "<kid>\n" + MD + "\n</kid>" in bloque["text"]
    spec = p["toolConfig"]["tools"][0]["toolSpec"]
    assert spec["strict"] is True and spec["inputSchema"]["json"] == esquema_json()
    assert p["toolConfig"]["toolChoice"] == {"tool": {"name": HERRAMIENTA}} and "outputConfig" not in p
    assert "literal" in p["system"][0]["text"] and p["inferenceConfig"]["maxTokens"] >= 1024
    with pytest.raises(TypeError):
        peticion(b"%PDF-1.7", "modelo")  # el PDF ya no se envía


def test_peticion_con_formato_json_schema():
    p = peticion(MD, "modelo", mecanismo="formato")
    formato = p["outputConfig"]["textFormat"]
    assert formato["type"] == "json_schema" and "toolConfig" not in p
    assert json.loads(formato["structure"]["jsonSchema"]["schema"]) == esquema_json()
    respuesta = {"stopReason": "end_turn", "output": {"message": {"content": [{"text": json.dumps(ENTRADA)}]}}}
    assert leer_respuesta(respuesta, mecanismo="formato").gastos_corrientes_pct == 1.25
    with pytest.raises(ValueError):
        peticion(MD, "modelo", mecanismo="otro")


def test_leer_respuesta_con_evidencias_y_errores():
    kid = leer_respuesta(respuesta_herramienta(ENTRADA))
    assert kid.sri == 4 and kid.sri_evidencia.startswith("Hemos clasificado")
    with pytest.raises(ValueError, match="maxTokens"):
        leer_respuesta(respuesta_herramienta(ENTRADA, stop="max_tokens"))


def test_extraer_con_cliente_falso():
    class BedrockFalso:
        def converse(self, **kw):
            self.kw = kw
            return respuesta_herramienta(ENTRADA)

    bedrock = BedrockFalso()
    kid = extraer(bedrock, MD, "eu.modelo")
    assert kid.isin == "ES0123456784" and bedrock.kw["modelId"] == "eu.modelo"
    assert MD in bedrock.kw["messages"][0]["content"][0]["text"]


# --- Verificación de las evidencias ---


def test_evidencias_buenas_aparecen_y_cuadran():
    kid = Kid.model_validate(ENTRADA)
    assert verificar_evidencias(kid, MD) == dict.fromkeys(CAMPOS, True)
    assert coherencia(kid) == dict.fromkeys(CAMPOS, True)


def test_evidencia_inventada_o_ausente_no_se_verifica():
    kid = Kid.model_validate(ENTRADA | {
        "gastos_corrientes_pct_evidencia": "Gastos corrientes: 1,25 %",  # no está en el texto
        "costes_salida_pct_evidencia": "",  # valor sin evidencia
        "nombre_clase_evidencia": "", "nombre_clase": None})  # null sin evidencia: no afirma nada
    v = verificar_evidencias(kid, MD)
    assert (v["gastos_corrientes_pct"], v["costes_salida_pct"], v["nombre_clase"], v["isin"]) == (False, False, True,
                                                                                                    True)


def test_valor_que_no_cuadra_con_su_evidencia():
    kid = Kid.model_validate(ENTRADA | {
        "sri": 7,  # la evidencia dice 4; el 7 de «escala de 7» no cuenta
        "gastos_corrientes_pct": 1.5, "isin": "LU9876543216", "fecha_documento": "2026-03-16",
        "costes_entrada_pct_evidencia": "No cobramos comisión de entrada.", "costes_entrada_pct": 2,
        "nombre_clase": "Clase B"})
    c = coherencia(kid)
    assert [k for k, ok in c.items() if not ok] == ["isin", "nombre_clase", "fecha_documento", "sri",
                                                    "gastos_corrientes_pct", "costes_entrada_pct"]


def test_coherencia_de_formas_habituales():
    kid = Kid(periodo_mantenimiento_anios_evidencia="Periodo de mantenimiento recomendado: 18 meses",
              periodo_mantenimiento_anios=1.5, fecha_documento_evidencia="Fecha: 01/02/2026",
              fecha_documento=date(2026, 2, 1), costes_salida_pct_evidencia="Costes de salida<br>0%",
              costes_salida_pct=0, sri_evidencia="riesgo 7 de 7", sri=7)
    c = coherencia(kid)
    assert c["periodo_mantenimiento_anios"] and c["fecha_documento"] and c["costes_salida_pct"] and c["sri"]
    assert not coherencia(Kid(fecha_documento_evidencia="Fecha: 11/02/2026", fecha_documento=date(2026, 2, 1)))[
        "fecha_documento"]


# --- Base de datos ---


class RdsFalsoJson:
    def __init__(self):
        self.llamadas = []

    def execute_statement(self, **kw):
        self.llamadas.append(kw)
        return {"formattedRecords": "[]"}


def test_guardar_kid_con_evidencias_es_idempotente():
    rds, kid = RdsFalsoJson(), Kid.model_validate(ENTRADA)
    db = BaseDatos(rds, "arn:cluster", "arn:secret", "kid")
    revision = revisar(kid, MD)
    db.guardar_kid("a" * 64, kid, "modelo", revision)
    db.guardar_kid("a" * 64, kid, "modelo", revision)  # mismo documento: misma sentencia, la fila se actualiza
    params = {p["name"]: p for p in rds.llamadas[0]["parameters"]}
    assert set(params) == {"documento_sha256", "modelo", "evidencias", "evidencias_ok", *CAMPOS}
    assert params["evidencias"]["typeHint"] == "JSON" and params["evidencias_ok"]["value"] == {"booleanValue": True}
    guardado = json.loads(params["evidencias"]["value"]["stringValue"])
    assert guardado["sri"] == {"evidencia": ENTRADA["sri_evidencia"], "aparece": True, "coherente": True}
    assert rds.llamadas[0] == rds.llamadas[1]
    assert "ON CONFLICT (documento_sha256) DO UPDATE" in UPSERT_KID and "evidencias = EXCLUDED.evidencias" in UPSERT_KID
    assert "CAST(:evidencias AS JSONB)" in UPSERT_KID


def test_guardar_kid_sin_revision_y_columnas():
    rds = RdsFalsoJson()
    BaseDatos(rds, "c", "s", "kid").guardar_kid("b" * 64, Kid(isin="ES0123456784", isin_evidencia="ISIN"), "m")
    params = {p["name"]: p["value"] for p in rds.llamadas[0]["parameters"]}
    assert params["evidencias_ok"] == {"isNull": True}
    assert json.loads(params["evidencias"]["stringValue"])["isin"] == {"evidencia": "ISIN"}
    assert parametro("x", {"a": "ñ"})["value"] == {"stringValue": '{"a": "ñ"}'}
    sql = (Path(__file__).parent / "kid_pipeline" / "schema.sql").read_text(encoding="utf-8")
    assert "evidencias                   JSONB" in sql and "evidencias_ok                BOOLEAN" in sql


# --- Extractor por reglas y evaluación (D-2.5) ---
# Tests del extractor por reglas y del evaluador (D-2.5), con fragmentos inventados: ningún KID real en el repo.
TIPO_BESTINVER = """Denominación del producto: FONDO INVENTADO RENTA CLASE R ISIN: ES0111111110 Nombre del \
productor del PRIIP: GESTORA FICTICIA SGIIC, S.A. Sitio web del productor del PRIIP: www.ejemplo.es

GESTORA FICTICIA, S.A., S.G.I.I.C. está autorizada en España. Fecha de elaboración del documento de datos \
fundamentales: 30/06/2026

<!-- Start of picture text -->
1<br><!-- End of picture text -->

**Este indicador de riesgo presupone que usted mantendrá el producto durante 3 años.**

Hemos clasificado este producto en la clase de riesgo 2 en una escala de 7, en la que 2 significa un riesgo bajo.

|**Período de ma**|**ntenimiento recomendado: 3 años**|||
|---|---|---|---|
|**Costes totales**|230 €|1.477 €|

|**Costes únicos de entrada o salid**|**En caso de sali**<br>**a**|**da después de 1 año**|
|---|---|---|
|**Costes de entrada**|1,5% desde el 1/01/2026 hasta el 31/12/2027, ambos inclusive.|150 €|
|**Costes de salida**|No cobramos una comisión de salida por este producto.|0 €|
|**Costes corrientes detraídos cada**|**año**||
|**Comisiones de gestión y otros**<br>**costes administrativos o de**<br>**funcionamiento**|0,9 % del valor de su \
inversión al año.|90 €|
|**Costes de operación**|0,1 % del valor de su inversión al año.|10 €|

El periodo de mantenimiento recomendado es de 3 años. Se deben tener en cuenta los posibles costes de salida.
"""

TIPO_AZVALOR = """# Documento de 5<sup>a</sup> Datos Fundamentales del Producto

## Inventado Global FI

Fecha de documento 9 de enero de 2026

#### Producto

Inventado Global FI

Entidad  Inventada Asset Management, SGIIC, S.A. Código ISIN  ES0222222228 Dirección web  www.ejemplo.com \
Fecha de registro del fondo  23 de octubre de 2015

|Riesgo más bajo||Riesgo más alto|
|---|---|---|
|1*<br>3<br>2|5<br>4|6<br>7|

Hemos clasificado este producto en la clase de riesgo [5] en una escala de 7, en la que 5 significa «medio alto».

|Periodo de mantenimiento recom<br>Inversión: €10.000|endado: 5 años||
|---|---|---|

|Costes únicos de entrada o salida<br>En caso de salida después de 1 año|
|---|
|Costes de entrada<br>0%|
|No hay comisión de entrada para este producto<br>0EUR|
|Costes de salida<br>0%|
|La comisión de salida es de 0,00%. En caso de participaciones con<br>antigüedad menor a 1 año se aplicara un 3,00%.|

#### Costes corrientes detraídos cada año Comisiones de gestión y otros costes administrativos o de funcionamiento

|1,89% del valor de su inversión por año<br>190EUR|
|---|
|Costes de operación|
|0,14% del valor de su inversión por año<br>15EUR|

Fecha de documento 9 de enero de 2026

#### Período de mantenimiento recomendado: 5 años (debido a la política de inversión)
"""

TIPO_COBAS = """# **<mark>Inventado Value, FI CLASE B</mark>**

|**Información gen**|**eral**|||
|---|---|---|---|
|**Producto:**|Inventado Value, FI CLASE B|**ISIN:**|ES0333333336|
|**Entidad:**|Inventada Gestión, S.G.I.I.C., S.A.|**Grupo:**|Grupo Ficticio|
|**Fecha document**|**o:**<br>31 de diciembre de 2025|**Para más infor**|**mación, llame al:**<br>900 00 00 00|

El indicador de riesgos presupone que usted mantendrá el producto durante 5 años. **1 2 3 4 5 6 7**

Hemos clasificado este producto en la clase de riesgo [4] en una escala de 7, en la que 4 significa «un riesgo medio».

|**Periodo de**|**mantenimiento recomendado:**|**5 años**|**En caso**|
|---|---|---|---|

|**Costes únicos a la entrada o sal**|**ida**|**Incidencia anual**|
|---|---|---|
|**Costes de entrada**|No hay comisión de entrada para este producto.<br>La comisión de salida es de 4,00% para \
participaciones con antigüedad menor a 1 año|0 €|
|**Costes de salida**|excepto traspasos en el fondo.|400 €|
|**Costes recurrentes cargados ca**|**da año**||
|**Comisiones de gestión y otros**|Esto es una estimación basada en los costes reales.<br>1,38% del valor de su \
inversión por año.|138 €|
|**Costes de operación**|0,13% del valor de su inversión por año.|13 €|

# **<mark>Período de mantenimiento recomendado: 5 años</mark>**
"""

TIPO_LUXEMBURGO = """**BESTINVENTO HIGH YIELD CL B2**

Name of Product: BESTINVENTO HIGH YIELD CL B2

ISIN: LU0444444441 Nombre del producto del PRIIP: GESTORA FICTICIA SGIIC, S.A. Sitio web del producto del PRIIP: x.lu

Fecha de elaboración del documento de datos fundamentales: 27/02/2026

**Este indicador de riesgo da por sentado que usted mantendrá el producto durante 5 años.**

Hemos clasificado este producto en la categoría de riesgo **2** en una escala de **7** , lo que corresponde a una \
clase de riesgo baja.

## **PERÍODO DE MANTENIMIENTO RECOMENDADO: 4 AÑOS**

El periodo de mantenimiento recomendado es de 4 años.

|**Costes de entrada**|No cobramos comisiones de entrada<br>0 €|
|**Costes de salida**|No cobramos un comisión de salida por este producto<br>0 €|
|**Comisiones de gestión y**<br>**otros costes**|0,2 % del valor de su inversión al año.<br>19 €|
"""


def test_reglas_formato_bestinver():
    assert extraer_reglas(TIPO_BESTINVER) == {
        "isin": "ES0111111110", "nombre_producto": "FONDO INVENTADO RENTA", "nombre_clase": "Clase R",
        "gestora": "GESTORA FICTICIA SGIIC, S.A.", "fecha_documento": "2026-06-30", "sri": 2,
        "periodo_mantenimiento_anios": 3.0, "gastos_corrientes_pct": 0.9, "costes_entrada_pct": 1.5,
        "costes_salida_pct": 0.0}


def test_reglas_formato_azvalor():
    """Fecha en letra (y no la de registro del fondo), SRI entre corchetes, sin clase, salida 0 pese al 3 % del
    texto (el cuadro dice 0%) y periodo sacado del apartado propio (la tabla lo parte)."""
    assert extraer_reglas(TIPO_AZVALOR) == {
        "isin": "ES0222222228", "nombre_producto": "Inventado Global FI", "nombre_clase": None,
        "gestora": "Inventada Asset Management, SGIIC, S.A.", "fecha_documento": "2026-01-09", "sri": 5,
        "periodo_mantenimiento_anios": 5.0, "gastos_corrientes_pct": 1.89, "costes_entrada_pct": 0.0,
        "costes_salida_pct": 0.0}


def test_reglas_formato_cobas():
    """Tabla con «Fecha document|o:» partida, la frase de la comisión de salida en la fila de entrada y el % de
    gestión detrás del texto."""
    assert extraer_reglas(TIPO_COBAS) == {
        "isin": "ES0333333336", "nombre_producto": "Inventado Value, FI", "nombre_clase": "Clase B",
        "gestora": "Inventada Gestión, S.G.I.I.C., S.A.", "fecha_documento": "2025-12-31", "sri": 4,
        "periodo_mantenimiento_anios": 5.0, "gastos_corrientes_pct": 1.38, "costes_entrada_pct": 0.0,
        "costes_salida_pct": 4.0}


def test_reglas_formato_luxemburgues():
    """«CL B2», la errata «producto del PRIIP», SRI en negrita y el periodo recomendado (4) por delante del que
    presupone el indicador (5)."""
    e = extraer_reglas(TIPO_LUXEMBURGO)
    assert (e["isin"], e["nombre_producto"], e["nombre_clase"], e["gestora"]) == (
        "LU0444444441", "BESTINVENTO HIGH YIELD", "Clase B2", "GESTORA FICTICIA SGIIC, S.A.")
    assert (e["fecha_documento"], e["sri"], e["periodo_mantenimiento_anios"]) == ("2026-02-27", 2, 4.0)
    assert (e["gastos_corrientes_pct"], e["costes_entrada_pct"], e["costes_salida_pct"]) == (0.2, 0.0, 0.0)


def test_reglas_null_antes_que_adivinar():
    """Sin datos, todo null; ISIN con dígito de control falso, null; pistas contradictorias, null."""
    assert extraer_reglas("Documento sin datos del producto.") == dict.fromkeys(CAMPOS)
    assert extraer_reglas("ISIN: ES0111111111")["isin"] is None
    assert sri("en la clase de riesgo 3 en una escala de 7 ... en la clase de riesgo 5 en una escala de 7") is None
    assert periodo_mantenimiento("Periodo de mantenimiento recomendado: 3 años. El periodo de mantenimiento "
                                 "recomendado es de 5 años") is None
    assert reglas.coste_unico("Costes únicos | Costes de entrada | 2% | No hay comisión de entrada", "entrada") is None
    assert reglas.coste_unico("Costes únicos | Costes de entrada | 0 € | 200 €", "entrada") is None  # solo euros: null


@pytest.mark.parametrize("texto, esperado", [
    ("Fecha de elaboración del documento de datos fundamentales: 31/12/2025", "2025-12-31"),
    ("Fecha documento: 1 de febrero de 2026", "2026-02-01"),
    ("Fecha de documento 9 de enero de 2026 ... Fecha de documento 9 de enero de 2026", "2026-01-09"),
    ("Fecha de registro del fondo 23 de octubre de 2015", None),
    ("Fecha documento: 31/02/2026", None),
])
def test_fecha_documento(texto, esperado):
    assert fecha_documento(texto) == esperado


@pytest.mark.parametrize("texto, esperado", [
    ("Período de mantenimiento recomendado: 18 meses", 1.5),
    ("El periodo de mantenimiento recomendado es de cinco años", 5.0),
    ("Este indicador presupone que usted mantendrá el producto durante 1 año.", 1.0),
])
def test_periodo_mantenimiento(texto, esperado):
    assert periodo_mantenimiento(texto) == esperado


def test_sri_otras_formas():
    assert sri("Indicador resumido de riesgo (SRI): 6 de 7") == 6
    assert sri("SRI 3") == 3


def test_limpiar_recompone_etiquetas_partidas():
    assert "Fecha documento: 31 de" in reglas.limpiar("|**Fecha document**|**o:**<br>31 de|", celdas="")
    assert "Producto: | Fondo X |" in reglas.limpiar("|**Producto:**|Fondo X|**ISIN:**|")


# --- Evaluador ---

def test_comparacion_normalizada():
    assert coincide("gestora", "Inventada Gestión SGIIC, S.A.", "INVENTADA GESTION, S.G.I.I.C., S.A.")
    assert coincide("nombre_producto", "Fondo Inventado, F.I. Clase A", "FONDO INVENTADO FI")
    assert coincide("nombre_clase", "B2", "Clase B2")
    assert not coincide("nombre_clase", "Clase B", "Clase B2")
    assert coincide("gastos_corrientes_pct", "1,805", 1.8) and not coincide("gastos_corrientes_pct", 1.84, 1.8)
    assert not coincide("sri", 3.5, 4) and coincide("sri", "4", 4)
    assert coincide("fecha_documento", "2026-01-09T00:00:00", "2026-01-09")
    assert coincide("isin", "es 0111111110", "ES0111111110")
    assert clave_texto("nombre_producto", "Cobas Seleccíon, FI CLASE B") == "cobasseleccion"


def _campos(**valores):
    return {c: {"valor": valores.get(c)} for c in CAMPOS}


def test_evaluar_extraccion():
    referencia = {
        "a" * 64: _campos(isin="ES0111111110", sri=4, gastos_corrientes_pct=1.8, costes_salida_pct=0.0),
        "b" * 64: _campos(isin="ES0222222228", sri=2) | {"gestora": {"valor": "Gestora A", "alternativas": ["B"]}},
        "c" * 64: _campos(sri=1),
    }
    predicciones = {
        "a" * 64: {"isin": "ES0111111110", "sri": 5, "gastos_corrientes_pct": 1.805, "nombre_clase": "Clase A"},
        "b" * 64: {"isin": "ES0222222228", "sri": 2, "gestora": "b"},
    }
    r = evaluar_extraccion(referencia, predicciones)
    assert r["sin_prediccion"] == ["c" * 64]
    assert r["por_campo"]["isin"] == {"exactitud": 0.667, "aciertos": 2, "total": 3, "esperados_null": 1,
                                      "null_ok": 0, "inventados": 0, "omitidos": 1, "distintos": 0}
    assert r["por_campo"]["sri"]["distintos"] == 1 and r["por_campo"]["sri"]["aciertos"] == 1
    assert r["por_campo"]["nombre_clase"]["inventados"] == 1 and r["por_campo"]["nombre_clase"]["null_ok"] == 1
    assert r["por_campo"]["gestora"]["aciertos"] == 2  # null esperado en «a» y una alternativa en «b»
    assert r["por_campo"]["costes_salida_pct"]["omitidos"] == 2  # 0 esperado, null obtenido; y «c» sin predicción
    assert r["global"]["total"] == 30
    assert {"sha256": "a" * 64, "campo": "sri", "esperado": 4, "obtenido": 5} in r["discrepancias"]


def test_coherencia_manifiesto_y_predicciones_jsonl(tmp_path):
    kids = [({"sha256": "a" * 64, "gestora": "g1", "isin_web": "ES0111111110", "clase": "Clase A"}, ""),
            ({"sha256": "b" * 64, "gestora": "g1", "isin_web": None, "isin_pdf": "ES0222222228", "clase": None}, ""),
            ({"sha256": "c" * 64, "gestora": "g2", "isin_web": "ES0333333336", "clase": "Clase B"}, "")]
    ruta = tmp_path / "modelo.jsonl"
    ruta.write_text("\n".join(json.dumps(p) for p in [
        {"sha256": "a" * 64, "isin": "ES0111111110", "nombre_clase": "A", "sri": 4},
        {"sha256": "b" * 64, "isin": "ES0555555558", "nombre_clase": "Clase C"},
    ]) + "\n\n", encoding="utf-8")
    r = coherencia_manifiesto(kids, leer_predicciones(ruta))
    assert (r["documentos"], r["sin_prediccion"], r["isin_ok"], r["isin_distinto"]) == (2, 1, 1, 1)
    assert (r["con_clase"], r["clase_ok"], r["clase_solo_extraida"]) == (1, 1, 1)
    assert r["cobertura"]["sri"] == "1/2" and r["cobertura"]["isin"] == "2/2"
    assert any("ES0555555558" in a for a in r["avisos"])


def test_api_devuelve_las_evidencias_como_objeto():
    c, _ = cliente([{"isin": "ES0113900J37", "evidencias": '{"sri": {"evidencia": "riesgo 4", "aparece": true}}'}])
    assert c.get("/fondos").json()[0]["evidencias"]["sri"]["aparece"] is True
