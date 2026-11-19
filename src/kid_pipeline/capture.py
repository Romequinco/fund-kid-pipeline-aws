"""Captura: sesión HTTP educada (D-1.1), enlace a un KID, documento descargado y una fuente por gestora.

Las fuentes se completan en el Taller 1 inspeccionando cada web (enunciado, §3). Las webs cambian: si un selector deja
de encontrar enlaces, `enlaces()` debe fallar con un error claro, no devolver una lista vacía en silencio.
"""

from __future__ import annotations

import hashlib
import re
import time
from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass, field
from datetime import UTC, datetime
from urllib import robotparser
from urllib.parse import urljoin, urlparse

import requests

USER_AGENT = "fund-kid-pipeline/0.1 (practica academica MIAX; +https://github.com/Romequinco/fund-kid-pipeline-aws)"


@dataclass(frozen=True)
class KidEnlace:
    """Dónde está un KID según la web de la gestora, antes de descargarlo."""

    gestora: str
    url_pdf: str
    url_ficha: str
    fondo: str | None = None
    clase: str | None = None
    isin_web: str | None = None  # el ISIN que muestra la web, para contrastar con el extraído


@dataclass(frozen=True)
class Documento:
    """Un PDF descargado, con su procedencia. El SHA-256 es su identidad (D-1.2)."""

    enlace: KidEnlace
    contenido: bytes = field(repr=False)
    descargado_en: datetime

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.contenido).hexdigest()


def prohibidos_con_comodin(robots_txt: str) -> list[re.Pattern]:
    """`Disallow` con `*` o `$` del grupo `User-agent: *` (RFC 9309).

    `urllib.robotparser` no entiende comodines: con `Disallow: /*.pdf$` daría un PDF por permitido.
    """
    patrones, en_grupo = [], False
    for linea in robots_txt.splitlines():
        clave, _, valor = linea.split("#", 1)[0].partition(":")
        clave, valor = clave.strip().lower(), valor.strip()
        if clave == "user-agent":
            en_grupo = valor == "*"
        elif clave == "disallow" and en_grupo and valor and ("*" in valor or valor.endswith("$")):
            fin = valor.endswith("$")
            cuerpo = re.escape(valor.rstrip("$")).replace(r"\*", ".*")
            patrones.append(re.compile(cuerpo + ("$" if fin else "")))
    return patrones


class SesionEducada:
    """requests.Session con User-Agent propio, robots.txt y pausa mínima entre peticiones."""

    def __init__(self, pausa_s: float = 2.0, timeout_s: float = 30.0) -> None:
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self.pausa_s, self.timeout_s = pausa_s, timeout_s
        self._robots: dict[str, tuple[robotparser.RobotFileParser, list[re.Pattern]]] = {}
        self._ultima = 0.0

    def permitido(self, url: str) -> bool:
        base = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if base not in self._robots:
            rp = robotparser.RobotFileParser(urljoin(base, "/robots.txt"))
            try:
                r = self.http.get(rp.url, timeout=self.timeout_s)
                texto = r.text if r.ok else ""
            except requests.RequestException:
                texto = ""  # sin robots.txt accesible se asume permitido
            rp.parse(texto.splitlines())
            self._robots[base] = (rp, prohibidos_con_comodin(texto))
        rp, patrones = self._robots[base]
        u = urlparse(url)
        ruta = u.path + (f"?{u.query}" if u.query else "")
        return rp.can_fetch(USER_AGENT, url) and not any(p.match(ruta) or p.match(u.path) for p in patrones)

    def get(self, url: str) -> requests.Response:
        if not self.permitido(url):
            raise PermissionError(f"robots.txt no permite {url}")
        espera = self.pausa_s - (time.monotonic() - self._ultima)
        if espera > 0:
            time.sleep(espera)
        r = self.http.get(url, timeout=self.timeout_s)
        self._ultima = time.monotonic()
        r.raise_for_status()
        return r

    def descargar(self, enlace: KidEnlace) -> Documento:
        r = self.get(enlace.url_pdf)
        if not r.content.startswith(b"%PDF"):
            raise ValueError(f"No es un PDF: {enlace.url_pdf}")
        return Documento(enlace, r.content, datetime.now(UTC))


class Fuente(ABC):
    """Una gestora. Cada subclase sabe recorrer su web y devolver los enlaces a sus KID."""

    nombre: str
    inicio: str

    @abstractmethod
    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]: ...


class Bestinver(Fuente):
    """Baja: cada ficha /fondos-de-inversion/<fondo>/ enlaza «Datos fundamentales». Una clase por ficha.

    Su robots.txt prohíbe los PDF (`Disallow: /*.pdf$`): SesionEducada lo respetará (D-1.3).
    """

    nombre = "bestinver"
    inicio = "https://www.bestinver.es/fondos-de-inversion/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


class Azvalor(Fuente):
    """Media: ficha con «Folleto simplificado (DFP)». El nombre del PDF lleva la fecha: leerlo del HTML.

    El 19/11/2026 las fichas colgaban de /fondos-de-inversion/, no de /fondos/ como dice el enunciado (D-1.3).
    """

    nombre = "azvalor"
    inicio = "https://www.azvalor.com/fondos-de-inversion/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


class Cobas(Fuente):
    """Media-alta: un bloque por clase (A, B, C, D) con su ISIN y su enlace «PRIIP pdf»."""

    nombre = "cobas"
    inicio = "https://www.cobasam.com/productos/"

    def enlaces(self, sesion: SesionEducada) -> Iterator[KidEnlace]:
        raise NotImplementedError("Taller 1")


FUENTES: dict[str, type[Fuente]] = {f.nombre: f for f in (Bestinver, Azvalor, Cobas)}
