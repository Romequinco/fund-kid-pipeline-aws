"""Una fuente por gestora. Se completan en el Taller 1 inspeccionando cada web (enunciado, §3).

Las webs cambian: si un selector deja de encontrar enlaces, `enlaces()` debe fallar con un error claro,
no devolver una lista vacía en silencio.
"""

from __future__ import annotations

from collections.abc import Iterator

from .base import Fuente, KidEnlace, SesionEducada


class Bestinver(Fuente):
    """Dificultad baja: cada ficha /fondos-de-inversion/<fondo>/ enlaza «Datos fundamentales». Una clase por ficha."""

    nombre = "bestinver"
    inicio = "https://www.bestinver.es/fondos-de-inversion/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


class Azvalor(Fuente):
    """Dificultad media: ficha con «Folleto simplificado (DFP)». El nombre del PDF lleva la fecha: leerlo del HTML."""

    nombre = "azvalor"
    inicio = "https://www.azvalor.com/fondos/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


class Cobas(Fuente):
    """Dificultad media-alta: un bloque por clase (A, B, C, D) con su ISIN y su enlace «PRIIP pdf»."""

    nombre = "cobas"
    inicio = "https://www.cobasam.com/productos/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


FUENTES: dict[str, type[Fuente]] = {f.nombre: f for f in (Bestinver, Azvalor, Cobas)}
