"""La API con una base de datos falsa: rutas, filtros y 404."""

import app as api
from fastapi.testclient import TestClient


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
