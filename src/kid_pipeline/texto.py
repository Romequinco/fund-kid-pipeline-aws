"""Del PDF al texto que lee el modelo: Markdown de las páginas del KID (D-2.3).

`pymupdf4llm` conserva títulos, listas y tablas (las de costes y escenarios salen como tablas Markdown), que es como
mejor las entiende un modelo de lenguaje. Solo se convierten las páginas del KID: el Reglamento PRIIPs lo limita a
3 caras A4, y Cobas publica en el mismo PDF un anexo de escenarios y rentabilidades pasadas que no debe leerse.

Los 68 KID capturados tienen capa de texto, así que no hace falta OCR.
"""

from __future__ import annotations

import re
import unicodedata

KID_PAGINAS = 3


def kid_markdown(pdf: bytes, paginas: int = KID_PAGINAS) -> str:
    """Markdown de las primeras `paginas` del PDF (todas si tiene menos)."""
    import pymupdf
    import pymupdf4llm

    with pymupdf.open(stream=pdf, filetype="pdf") as doc:
        return pymupdf4llm.to_markdown(doc, pages=list(range(min(paginas, doc.page_count))), show_progress=False,
                                       use_ocr=False)


def normalizar(texto: str) -> str:
    """Para comparar un fragmento con el documento: sin marca Markdown, tildes, mayúsculas ni espacios.

    Se quitan todos los espacios porque la conversión parte a veces palabras y números (`1, 78 %`).
    """
    texto = unicodedata.normalize("NFKD", texto)
    texto = "".join(c for c in texto if not unicodedata.combining(c))
    texto = re.sub(r"[*_~`#|>]", "", texto)
    return re.sub(r"\s+", "", texto).lower()


def aparece(fragmento: str | None, documento: str) -> bool:
    """¿Está el fragmento, tal cual (salvo formato), en el documento?"""
    return bool(fragmento) and normalizar(fragmento) in normalizar(documento)
