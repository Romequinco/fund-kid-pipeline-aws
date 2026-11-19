"""Pruebas sin AWS: esquema, captura, claves de S3, salida de Bedrock, Data API y la API con una base de datos falsa."""

from datetime import UTC, date, datetime

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

import api
from kid_pipeline.capture import Documento, KidEnlace, prohibidos_con_comodin
from kid_pipeline.db import UPSERT_KID, BaseDatos, parametro
from kid_pipeline.extract import HERRAMIENTA, leer_respuesta, peticion
from kid_pipeline.schema import Kid, esquema_json, faltan_obligatorios, isin_valido
from kid_pipeline.storage import clave_manifiesto, clave_pdf, metadatos

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
