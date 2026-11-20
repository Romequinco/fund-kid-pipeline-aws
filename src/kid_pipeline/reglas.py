"""Extractor por reglas: los 10 campos del Anexo A con expresiones regulares sobre el Markdown del KID (D-2.5).

Es la línea base frente a la que se mide el modelo de Bedrock, y la segunda opinión barata sobre cada extracción.
Cubre las variantes de las tres gestoras capturadas (Bestinver, Azvalor y Cobas): etiquetas en línea («Denominación
del producto:», «Entidad», «Código ISIN»), tablas con las etiquetas partidas entre celdas («Fecha document|o:»),
fechas en número o en letra, y costes en % o con la frase «no cobramos comisión». Principio: **null antes que
adivinar**. Cada campo se busca con varias pistas; si no hay ninguna, o si se contradicen, queda a null.

Devuelve un dict plano con los campos del Anexo A (sin depender de `schema.Kid`).
"""

from __future__ import annotations

import re
from datetime import date

from kid_pipeline.schema import isin_valido

CAMPOS = ("isin", "nombre_producto", "nombre_clase", "gestora", "fecha_documento", "sri", "periodo_mantenimiento_anios",
          "gastos_corrientes_pct", "costes_entrada_pct", "costes_salida_pct")  # Anexo A
MESES = {m: i for i, m in enumerate(("enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto",
                                     "septiembre", "octubre", "noviembre", "diciembre"), 1)}
PALABRAS = {"un": 1, "uno": 1, "dos": 2, "tres": 3, "cuatro": 4, "cinco": 5, "seis": 6, "siete": 7, "ocho": 8,
            "nueve": 9, "diez": 10}
IC = re.IGNORECASE
ICM = re.IGNORECASE | re.MULTILINE

_NUM = r"(\d+(?:\s?[.,]\s?\d+)?)"  # 1,8 · 1.8 · «1, 78» (la conversión parte a veces los números)
_FECHA = (r"(?:(\d{1,2})[/.-](\d{1,2})[/.-](\d{4})"
          r"|(\d{1,2})\s+de\s+(" + "|".join(MESES) + r")\s+(?:de(?:l)?\s+)?(\d{4}))")
_ISIN = r"([A-Z]{2}[A-Z0-9]{9}\d)"
_NO_HAY = (r"no\s+(?:cobramos|hay|se\s+aplica|existe|se\s+cobra)\s+(?:ninguna\s+|una\s+|un\s+)?"
           r"comisi[oó]n(?:es)?\s+de\s+")


def limpiar(md: str, celdas: str = " | ") -> str:
    """Markdown -> texto: sin marcas (negritas, <mark>, comentarios, títulos) y con las celdas unidas por `celdas`.

    Con `celdas=""` las celdas se pegan, que es como se recompone una etiqueta partida («Fecha document|o:»).
    """
    t = re.sub(r"<!--.*?-->", " ", md, flags=re.S)
    t = re.sub(r"<br\s*/?>", " ", t, flags=IC)
    t = re.sub(r"</?(?:mark|u|b|i|sup|sub|span|strong|em)\b[^>]*>", "", t, flags=IC)
    t = re.sub(r"\*\*|~~|(?<!\w)_|_(?!\w)", "", t)
    t = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", t)
    t = re.sub(r"^[ \t]*#+[ \t]*", "", t, flags=re.M)
    t = re.sub(r"^[ \t]*\|?(?:[ \t]*:?-{3,}:?[ \t]*\|)+[ \t]*$", "", t, flags=re.M)  # separador |---|---|
    t = re.sub(r"[ \t]*\|[ \t]*", celdas, t)
    return re.sub(r"[ \t\xa0]+", " ", t)


def _numero(texto: str) -> float:
    return float(re.sub(r"\s", "", texto).replace(",", "."))


def _unico(valores: list):
    """El valor si todas las pistas coinciden; None si no hay pistas o se contradicen."""
    distintos = set(valores)
    return distintos.pop() if len(distintos) == 1 else None


def _fecha(m: re.Match) -> str | None:
    g = m.groups()
    dia, mes, anio = (g[0], g[1], g[2]) if g[0] else (g[3], MESES[g[4].lower()], g[5])
    try:
        return date(int(anio), int(mes), int(dia)).isoformat()
    except ValueError:
        return None


def isin(texto: str) -> str | None:
    """El ISIN junto a su etiqueta; si no hay etiqueta, el único ISIN válido del documento."""
    etiquetados = [c for c in re.findall(r"\bISIN\b[\s:|]{0,20}" + _ISIN, texto) if isin_valido(c)]
    if etiquetados:
        return _unico(etiquetados)
    return _unico([c for c in re.findall(r"\b" + _ISIN + r"\b", texto) if isin_valido(c)])


_NOMBRE = (
    r"^.*?Denominaci[oó]n del producto:\s*(.+?)(?=\s+ISIN\b|\s*$)",                       # Bestinver
    r"^.*?(?:Name of (?:the )?Product|Nombre del producto):\s*(.+?)(?=\s+ISIN\b|\s*$)",  # Bestinver Sharpe
    r"^\s*\|?\s*Producto:\s*\|?\s*([^|\n]+?)\s*(?:\||$)",                                   # Cobas (tabla)
    r"^Producto[ \t]+(\S[^\n|]*?)\s*$",                                                  # Azvalor, en línea
    r"^Producto[ \t]*\n(?:[ \t]*\n)*[ \t]*(\S[^\n|]*?)\s*$",                             # Azvalor, título y nombre
)
_CLASE = re.compile(r"^(.*?)[\s,]*\b(?:clase|cl\.?)\s+([A-Z]\d?)\s*$", IC)


def nombre_y_clase(texto: str) -> tuple[str | None, str | None]:
    """Nombre del producto tal y como aparece y, si lo acompaña, la clase («... CLASE A», «... CL B2»)."""
    for patron in _NOMBRE:
        if m := re.search(patron, texto, ICM):
            nombre = m.group(1).strip(" ,:")
            if not nombre:
                continue
            if c := _CLASE.match(nombre):
                return c.group(1).strip(" ,"), f"Clase {c.group(2).upper()}"
            return nombre, None
    return None, None


_GESTORA = (
    r"Nombre del product(?:or|o)? del PRIIP:\s*(.+?)(?=\s+Sitio web|\s*$)",  # Bestinver (y la errata «producto»)
    r"^\s*\|?\s*Entidad:\s*\|?\s*([^|\n]+?)\s*(?:\||$)",                      # Cobas (tabla)
    r"^Entidad\s+(.+?)(?=\s+C[oó]digo ISIN|\s+ISIN|\s*$)",                 # Azvalor
    r"(?:Productor|Sociedad gestora|Entidad gestora):\s*(.+?)(?=\s*[|\n]|\.\s|$)",
)


def gestora(texto: str) -> str | None:
    for patron in _GESTORA:
        if (m := re.search(patron, texto, ICM)) and (g := m.group(1).strip(" ,:")):
            return g
    return None


def fecha_documento(pegado: str) -> str | None:
    """«Fecha de elaboración del documento de datos fundamentales: 31/12/2025», «Fecha (de) documento 9 de enero de
    2026». No vale cualquier fecha: la de registro del fondo o las de los escenarios no son la del KID."""
    patron = (r"fecha\s+(?:de\s+)?(?:elaboraci[oó]n\s+(?:del\s+)?|validez\s+(?:del\s+)?)?documento"
              r"(?:\s+de\s+datos\s+fundamentales)?\s*:?\s*" + _FECHA)
    return _unico([f for m in re.finditer(patron, pegado, IC) if (f := _fecha(m))])


def sri(texto: str) -> int | None:
    """La frase obligatoria «clase/categoría de riesgo N en una escala de 7» (el gráfico no se lee)."""
    pistas = re.findall(r"(?:clase|categor[ií]a)\s+de\s+riesgo\s*\[?\s*([1-7])\s*\]?\s*(?:,\s*)?en\s+una\s+escala\s+"
                        r"de\s*7", texto, IC)
    pistas += re.findall(r"\b(?:SRI|indicador resumido de riesgo)\s*(?:\(SRI\))?\s*(?::|=|es(?:\s+de)?)?\s*([1-7])"
                         r"(?:\s*(?:/|de|sobre)\s*7)?\b(?!\s*[.,]\d)", texto, IC)
    return _unico([int(p) for p in pistas])


def periodo_mantenimiento(texto: str) -> float | None:
    """«Período de mantenimiento recomendado: 5 años» o «... es de 4 años». Solo si el KID no lo dice así se usa la
    frase del indicador de riesgo («mantendrá el producto durante 1 año»), que no siempre coincide (Sharpe Z2: 5
    años en el indicador y 4 de periodo recomendado)."""
    cantidad = r"(\d+(?:[.,]\d+)?|" + "|".join(PALABRAS) + r")\s*(años?|meses|mes)\b"
    patrones = (r"per[ií]odo\s+de\s+mantenimiento\s+recomendado(?:\s+es)?(?:\s+de|\s*:)\s*" + cantidad,
                r"mantendr[aá]\s+(?:usted\s+)?el\s+producto\s+durante\s+" + cantidad)
    for patron in patrones:
        pistas = []
        for n, unidad in re.findall(patron, texto, IC):
            n = PALABRAS[n.lower()] if n.lower() in PALABRAS else _numero(n)
            pistas.append(round(n / 12, 2) if unidad.lower().startswith("mes") else float(n))
        if pistas:
            return _unico(pistas)
    return None


def gastos_corrientes(texto: str) -> float | None:
    """El % de «Comisiones de gestión y otros costes administrativos o de funcionamiento», no los costes de
    operación ni los importes en euros."""
    for m in re.finditer(r"Comisiones\s+de\s+gesti[oó]n\s+y\s+otros", texto, IC):
        tramo = re.split(r"Costes\s+de\s+operaci[oó]n", texto[m.end():m.end() + 1200], maxsplit=1, flags=IC)[0]
        if p := re.search(_NUM + r"\s*%\s*del\s+valor\s+de\s+su\s+inversi[oó]n", tramo, IC):
            return _numero(p.group(1))
    return None


def _tramo_costes_unicos(texto: str) -> str:
    """De «Costes únicos» (o la primera fila «Costes de entrada») hasta los costes corrientes."""
    inicio = re.search(r"Costes\s+[uú]nicos|Costes\s+de\s+entrada", texto, IC)
    if not inicio:
        return ""
    tramo = texto[inicio.start():inicio.start() + 2500]
    return re.split(r"Costes\s+(?:corrientes|recurrentes)|Comisiones\s+de\s+gesti[oó]n", tramo, maxsplit=1,
                    flags=IC)[0]


def coste_unico(texto: str, tipo: str) -> float | None:
    """Costes de entrada (`tipo="entrada"`) o de salida, en %: el % de su fila, «la comisión de salida es de 4,00%»
    o 0 si el KID dice que no se cobra. Si las pistas se contradicen, null."""
    sinonimo = {"entrada": r"(?:entrada|suscripci[oó]n)", "salida": r"(?:salida|reembolso)"}[tipo]
    tramo = _tramo_costes_unicos(texto)
    pistas = [_numero(n) for n in re.findall(r"Costes\s+de\s+" + tipo + r"\s*\|?\s*" + _NUM + r"\s*%", tramo, IC)]
    pistas += [_numero(n) for n in re.findall(r"comisi[oó]n\s+de\s+" + sinonimo + r"\s+es\s+(?:de\s+)?(?:un\s+)?"
                                              + _NUM + r"\s*%", tramo, IC)]
    pistas += [0.0 for _ in re.findall(_NO_HAY + sinonimo, tramo, IC)]
    return _unico(pistas)


def extraer_reglas(markdown: str) -> dict:
    """Los 10 campos del Anexo A a partir del Markdown del KID; null lo que no se encuentra con seguridad."""
    texto, pegado = limpiar(markdown), limpiar(markdown, celdas="")
    nombre, clase = nombre_y_clase(texto)
    return {
        "isin": isin(texto),
        "nombre_producto": nombre,
        "nombre_clase": clase,
        "gestora": gestora(texto),
        "fecha_documento": fecha_documento(pegado),
        "sri": sri(texto),
        "periodo_mantenimiento_anios": periodo_mantenimiento(pegado),
        "gastos_corrientes_pct": gastos_corrientes(texto),
        "costes_entrada_pct": coste_unico(texto, "entrada"),
        "costes_salida_pct": coste_unico(texto, "salida"),
    }
