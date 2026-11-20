"""Pruebas sin AWS: esquema, captura, claves de S3, salida de Bedrock, Data API y la API con una base de datos falsa."""

import hashlib
from datetime import UTC, date, datetime
from pathlib import Path

import pytest
import requests
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api
import kid_pipeline.capture as capture_mod
import pipeline
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
from kid_pipeline.extract import HERRAMIENTA, leer_respuesta, peticion
from kid_pipeline.schema import Kid, esquema_json, faltan_obligatorios, isin_valido
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
    p = peticion(b"%PDF", "modelo")
    assert p["toolConfig"]["toolChoice"] == {"tool": {"name": HERRAMIENTA}}
    assert p["toolConfig"]["tools"][0]["toolSpec"]["strict"] is True
    assert p["messages"][0]["content"][0]["document"]["format"] == "pdf"


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
