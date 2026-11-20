"""Esquema del KID: los campos del Anexo A del enunciado, con su evidencia, en un único modelo.

De aquí sale el esquema JSON que recibe Bedrock (salida estructurada) y la validación de lo que devuelve.
Todo campo es opcional porque, si no aparece en el documento, debe quedar a null: el modelo no lo inventa.
Los obligatorios del Anexo A se comprueban después, en `faltan_obligatorios`.

Cada campo va precedido de `<campo>_evidencia`: el fragmento literal del KID del que sale (D-2.4). La evidencia es una
cadena (vacía si el dato no aparece), no `string | null`, para no pasar del límite de uniones del modo estricto.
"""

from __future__ import annotations

import json
import re
from datetime import date

from pydantic import BaseModel, Field, field_validator

CAMPOS = ("isin", "nombre_producto", "nombre_clase", "gestora", "fecha_documento", "sri", "periodo_mantenimiento_anios",
          "gastos_corrientes_pct", "costes_entrada_pct", "costes_salida_pct")  # Anexo A
EVIDENCIA = "_evidencia"
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


def _evidencia(campo: str):
    return Field("", description=f"Fragmento literal del KID del que sale `{campo}`, copiado tal cual (la frase o la "
                                 "celda que contiene el dato). Cadena vacía si el dato no aparece.")


class Kid(BaseModel):
    """Campos mínimos del Anexo A, cada uno detrás de su evidencia: el modelo cita primero y extrae después."""

    isin_evidencia: str = _evidencia("isin")
    isin: str | None = Field(None, description="Código ISIN de la clase, 12 caracteres sin espacios.")
    nombre_producto_evidencia: str = _evidencia("nombre_producto")
    nombre_producto: str | None = Field(None, description="Nombre del fondo tal y como aparece en el KID.")
    nombre_clase_evidencia: str = _evidencia("nombre_clase")
    nombre_clase: str | None = Field(None, description="Clase o serie, p. ej. 'Clase C' o 'P Acc EUR'.")
    gestora_evidencia: str = _evidencia("gestora")
    gestora: str | None = Field(None, description="Productor del PRIIP o sociedad gestora.")
    fecha_documento_evidencia: str = _evidencia("fecha_documento")
    fecha_documento: date | None = Field(None, description="Fecha de elaboración o validez del KID (AAAA-MM-DD), no "
                                                           "la de los escenarios.")
    sri_evidencia: str = _evidencia("sri")
    sri: int | None = Field(None, ge=1, le=7, description="Indicador resumido de riesgo: la clase de 1 a 7 asignada "
                                                          "al producto.")
    periodo_mantenimiento_anios_evidencia: str = _evidencia("periodo_mantenimiento_anios")
    periodo_mantenimiento_anios: float | None = Field(None, ge=0, description="Periodo de mantenimiento recomendado, "
                                                                              "en años (18 meses -> 1.5).")
    gastos_corrientes_pct_evidencia: str = _evidencia("gastos_corrientes_pct")
    gastos_corrientes_pct: float | None = Field(None, ge=0, description=(
        "Comisiones de gestión y otros costes administrativos o de funcionamiento, en % anual (1,25 % -> 1.25), sin "
        "costes de operación."))
    costes_entrada_pct_evidencia: str = _evidencia("costes_entrada_pct")
    costes_entrada_pct: float | None = Field(None, ge=0, description="Costes de entrada, en % (cuadro de costes "
                                                                     "únicos); 0 si el KID dice que no se cobran.")
    costes_salida_pct_evidencia: str = _evidencia("costes_salida_pct")
    costes_salida_pct: float | None = Field(None, ge=0, description="Costes de salida, en % (cuadro de costes "
                                                                    "únicos); 0 si el KID dice que no se cobran.")

    @field_validator("isin")
    @classmethod
    def _isin(cls, v: str | None) -> str | None:
        if v is None:
            return None
        v = v.replace(" ", "").upper()
        if not isin_valido(v):
            raise ValueError(f"ISIN no válido: {v}")
        return v

    @field_validator(*[c + EVIDENCIA for c in CAMPOS], mode="before")
    @classmethod
    def _sin_evidencia(cls, v):
        return "" if v is None else v

    def valores(self) -> dict:
        """Los 10 campos del Anexo A (las columnas de la tabla `kid`)."""
        return {c: getattr(self, c) for c in CAMPOS}

    @property
    def evidencias(self) -> dict[str, str]:
        return {c: getattr(self, c + EVIDENCIA) for c in CAMPOS}


# Lo que el modo estricto rechaza [AWS salidas estructuradas]; `default` y `title` se quitan además por limpieza.
_PROHIBIDAS = {"minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum", "multipleOf", "minLength", "maxLength",
               "maxItems"}
_NO_ADMITIDAS_EN_ESTRICTO = _PROHIBIDAS | {"default", "title"}
MAX_OPCIONALES, MAX_UNIONES = 12, 16


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
    longitudes, así que se quitan aquí y los rangos (porcentajes >= 0) los valida Pydantic después. El SRI pasa a
    `enum` 1-7, que sí se admite: la gramática ya no deja escribir otro valor. Todos los campos van en `required`
    aunque admitan null: el modelo tiene que pronunciarse sobre cada uno (0 opcionales y 10 uniones, ver
    `comprobar_estricto`).
    """
    esquema = _limpiar(Kid.model_json_schema())
    esquema["required"] = list(esquema["properties"])
    for rama in esquema["properties"]["sri"]["anyOf"]:
        if rama.get("type") == "integer":
            rama["enum"] = list(range(1, 8))
    return esquema


def _es_union(prop: dict) -> bool:
    return "anyOf" in prop or "oneOf" in prop or isinstance(prop.get("type"), list)


def recuento(esquema: dict) -> dict[str, int]:
    """Propiedades, opcionales (fuera de `required`) y con unión de tipos, sumadas en todos los objetos del esquema."""
    total = {"propiedades": 0, "opcionales": 0, "uniones": 0}

    def visitar(nodo):
        if isinstance(nodo, list):
            for v in nodo:
                visitar(v)
        elif isinstance(nodo, dict):
            props = nodo.get("properties", {})
            total["propiedades"] += len(props)
            total["opcionales"] += len(set(props) - set(nodo.get("required", [])))
            total["uniones"] += sum(_es_union(p) for p in props.values() if isinstance(p, dict))
            for v in nodo.values():
                visitar(v)

    visitar(esquema)
    return total


def comprobar_estricto(esquema: dict) -> list[str]:
    """Incumplimientos de los límites del modo estricto de Bedrock (lista vacía si cumple).

    Cada objeto con `additionalProperties: false`; sin `minimum`/`maximum`/`multipleOf`, longitudes ni `maxItems`;
    `minItems` 0 o 1; `pattern` sin *lookaround*; sin esquemas recursivos; como mucho 12 propiedades opcionales y 16
    con unión de tipos en todo el esquema (06_piezas_de_la_practica.md §4.3).
    """
    fallos = []

    def visitar(nodo, ruta: str):
        if isinstance(nodo, list):
            for i, v in enumerate(nodo):
                visitar(v, f"{ruta}[{i}]")
            return
        if not isinstance(nodo, dict):
            return
        tipos = nodo.get("type") if isinstance(nodo.get("type"), list) else [nodo.get("type")]
        if ("object" in tipos or "properties" in nodo) and nodo.get("additionalProperties") is not False:
            fallos.append(f"{ruta}: objeto sin additionalProperties: false")
        fallos.extend(f"{ruta}: '{k}' no se admite" for k in sorted(_PROHIBIDAS & nodo.keys()))
        if nodo.get("minItems", 0) > 1:
            fallos.append(f"{ruta}: minItems {nodo['minItems']} (solo 0 o 1)")
        if re.search(r"\(\?<?[=!]", str(nodo.get("pattern", ""))):
            fallos.append(f"{ruta}: pattern con lookaround")
        if nodo.get("$ref") == "#":
            fallos.append(f"{ruta}: esquema recursivo")
        for k, v in nodo.items():
            if k in ("properties", "$defs") and isinstance(v, dict):
                for nombre, sub in v.items():
                    visitar(sub, f"{ruta}/{k}/{nombre}")
            elif k not in ("enum", "const", "required"):
                visitar(v, f"{ruta}/{k}")

    visitar(esquema, "#")
    defs = esquema.get("$defs", {})

    def refs(nodo) -> set[str]:
        return set(re.findall(r'"\$ref": "#/\$defs/([^"]+)"', json.dumps(nodo)))

    for nombre in defs:  # recursión entre definiciones (A -> B -> A)
        vistos, pendientes = set(), refs(defs[nombre])
        while pendientes:
            r = pendientes.pop()
            if r == nombre:
                fallos.append(f"#/$defs/{nombre}: esquema recursivo")
                break
            if r in defs and r not in vistos:
                vistos.add(r)
                pendientes |= refs(defs[r])
    n = recuento(esquema)
    if n["opcionales"] > MAX_OPCIONALES:
        fallos.append(f"{n['opcionales']} propiedades opcionales (máximo {MAX_OPCIONALES})")
    if n["uniones"] > MAX_UNIONES:
        fallos.append(f"{n['uniones']} propiedades con unión de tipos (máximo {MAX_UNIONES})")
    return fallos


def faltan_obligatorios(kid: Kid) -> list[str]:
    return [c for c in OBLIGATORIOS if getattr(kid, c) is None]
