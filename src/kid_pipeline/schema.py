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


def esquema_json() -> dict:
    """Esquema JSON que se pasa a Bedrock (ver extract.py y D-2.1)."""
    return Kid.model_json_schema()


def faltan_obligatorios(kid: Kid) -> list[str]:
    return [c for c in OBLIGATORIOS if getattr(kid, c) is None]
