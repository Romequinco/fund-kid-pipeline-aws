"""Esquema del KID: los campos del Anexo A del enunciado, en un único modelo.

De aquí sale el esquema JSON que recibe Bedrock (salida estructurada) y la validación de lo que devuelve.
Todo campo es opcional porque, si no aparece en el documento, debe quedar a null: el modelo no lo inventa.
Los obligatorios del Anexo A se comprueban después, en `faltan_obligatorios`.
"""

from __future__ import annotations

import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

OBLIGATORIOS = ("isin", "nombre_producto", "gestora", "sri")
_ISIN = re.compile(r"^[A-Z]{2}[A-Z0-9]{9}[0-9]$")


def isin_valido(isin: str) -> bool:
    """Formato ISO 6166 y dígito de control (Luhn sobre las letras pasadas a números)."""
    if not _ISIN.match(isin):
        return False
    digitos = "".join(str(int(c, 36)) for c in isin[:-1])
    total = 0
    for i, d in enumerate(reversed(digitos)):
        n = int(d) * (2 if i % 2 == 0 else 1)
        total += n - 9 if n > 9 else n
    return (10 - total % 10) % 10 == int(isin[-1])


class Kid(BaseModel):
    """Campos mínimos del Anexo A. Se pueden añadir más (escenarios, divisa, objetivo...)."""

    isin: str | None = Field(None, description="Código ISIN de la clase, 12 caracteres.")
    nombre_producto: str | None = Field(None, description="Nombre del fondo tal y como aparece en el KID.")
    nombre_clase: str | None = Field(None, description="Clase o serie, p. ej. 'Clase C' o 'P Acc EUR'.")
    gestora: str | None = Field(None, description="Productor del PRIIP o sociedad gestora.")
    fecha_documento: date | None = Field(None, description="Fecha de validez del KID (AAAA-MM-DD).")
    sri: int | None = Field(None, ge=1, le=7, description="Indicador resumido de riesgo, entero de 1 a 7.")
    periodo_mantenimiento_anios: float | None = Field(None, ge=0, description="Periodo de mantenimiento, en años.")
    gastos_corrientes_pct: float | None = Field(None, ge=0, description="Gastos corrientes, en % anual.")
    costes_entrada_pct: float | None = Field(None, ge=0, description="Costes de entrada, en %.")
    costes_salida_pct: float | None = Field(None, ge=0, description="Costes de salida, en %.")

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.replace(" ", "").upper()
        if not isin_valido(v):
            raise ValueError(f"ISIN no válido: {v}")
        return v


_NO_ADMITIDAS_EN_ESTRICTO = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "minLength", "maxLength",
                             "default", "title"}


def _limpiar(nodo):
    if isinstance(nodo, dict):
        limpio = {k: _limpiar(v) for k, v in nodo.items() if k not in _NO_ADMITIDAS_EN_ESTRICTO}
        if limpio.get("type") == "object":
            limpio["additionalProperties"] = False
        return limpio
    if isinstance(nodo, list):
        return [_limpiar(v) for v in nodo]
    return nodo


def esquema_json() -> dict:
    """Esquema para las salidas estructuradas de Bedrock (D-2.1).

    El modo estricto exige `additionalProperties: false` en cada objeto y no admite `minimum`, `maximum` ni
    longitudes, así que se quitan aquí y los rangos (SRI 1-7, porcentajes >= 0) los valida Pydantic después.
    Todos los campos van en `required` aunque admitan null: el modelo tiene que pronunciarse sobre cada uno.
    """
    esquema = _limpiar(Kid.model_json_schema())
    esquema["required"] = list(esquema["properties"])
    return esquema


def faltan_obligatorios(kid: Kid) -> list[str]:
    return [c for c in OBLIGATORIOS if getattr(kid, c) is None]
