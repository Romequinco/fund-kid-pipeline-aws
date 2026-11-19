"""Piezas comunes de la captura: sesión HTTP educada, enlace a un KID y documento descargado (D-1.1)."""

from __future__ import annotations

import hashlib
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


class SesionEducada:
    """requests.Session con User-Agent propio, robots.txt y pausa mínima entre peticiones."""

    def __init__(self, pausa_s: float = 2.0, timeout_s: float = 30.0) -> None:
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self.pausa_s, self.timeout_s = pausa_s, timeout_s
        self._robots: dict[str, robotparser.RobotFileParser] = {}
        self._ultima = 0.0

    def permitido(self, url: str) -> bool:
        base = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if base not in self._robots:
            rp = robotparser.RobotFileParser(urljoin(base, "/robots.txt"))
            try:
                rp.read()
            except OSError:
                rp.allow_all = True  # sin robots.txt accesible se asume permitido
            self._robots[base] = rp
        return self._robots[base].can_fetch(USER_AGENT, url)

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
