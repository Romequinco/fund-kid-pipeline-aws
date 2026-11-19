"""Extracción con Amazon Bedrock (Converse API) y salida estructurada.

El PDF entra como bloque `document` y la respuesta se fuerza con una herramienta cuyo `inputSchema` es el
esquema del KID (`toolChoice` obliga a usarla): el modelo no escribe texto libre que haya que parsear.
La alternativa (formato de respuesta con esquema JSON) está abierta en D-2.1.
"""

from __future__ import annotations

from .schema import Kid, esquema_json

HERRAMIENTA = "registrar_kid"
INSTRUCCIONES = (
    "Eres un analista que lee Documentos de Datos Fundamentales (KID) de fondos de inversión. "
    "Extrae los campos del esquema tal y como aparecen en el documento. "
    "Si un campo no aparece, déjalo a null: no lo deduzcas ni lo inventes. "
    "Los porcentajes van como número (1,25 % -> 1.25) y la fecha en formato AAAA-MM-DD."
)


def peticion(pdf: bytes, modelo: str) -> dict:
    """Argumentos de `bedrock-runtime.converse`. Separado para poder probarlo sin AWS."""
    return {
        "modelId": modelo,
        "system": [{"text": INSTRUCCIONES}],
        "messages": [{
            "role": "user",
            "content": [
                {"document": {"format": "pdf", "name": "kid", "source": {"bytes": pdf}}},
                {"text": "Extrae los datos de este KID."},
            ],
        }],
        "toolConfig": {
            "tools": [{"toolSpec": {
                "name": HERRAMIENTA,
                "description": "Registra los datos extraídos del KID.",
                "inputSchema": {"json": esquema_json()},
            }}],
            "toolChoice": {"tool": {"name": HERRAMIENTA}},
        },
        "inferenceConfig": {"temperature": 0},
    }


def leer_respuesta(respuesta: dict) -> Kid:
    for bloque in respuesta["output"]["message"]["content"]:
        if "toolUse" in bloque and bloque["toolUse"]["name"] == HERRAMIENTA:
            return Kid.model_validate(bloque["toolUse"]["input"])
    raise ValueError(f"El modelo no usó la herramienta (stopReason={respuesta.get('stopReason')})")


def extraer(bedrock, pdf: bytes, modelo: str) -> Kid:
    return leer_respuesta(bedrock.converse(**peticion(pdf, modelo)))
