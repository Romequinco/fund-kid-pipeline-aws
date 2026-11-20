"""Captura de los KID: sesión HTTP educada (D-1.1), una fuente por gestora y el informe de cada ejecución.

Cada fuente separa el parseo (funciones puras sobre el HTML, probadas con páginas guardadas en `src/fixtures/`) de la
red (`SesionEducada`). Las webs cambian: si un listado no da fichas o ninguna ficha da un KID, la fuente falla con un
error claro en vez de devolver una lista vacía en silencio (enunciado §3). Cada PDF se lee al descargarlo (`huella`)
para guardar lo que dice de sí mismo (ISIN, páginas, tipo) y rechazar lo que no es un KID (D-1.5).
"""

from __future__ import annotations

import hashlib
import io
import re
import time
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass, field, replace
from datetime import UTC, date, datetime
from urllib import robotparser
from urllib.parse import unquote, urljoin, urlparse, urlunparse

import requests
from bs4 import BeautifulSoup
from requests.utils import requote_uri

from .schema import isin_valido

USER_AGENT = "fund-kid-pipeline/0.1 (practica academica MIAX; +https://github.com/Romequinco/fund-kid-pipeline-aws)"
_ISIN = re.compile(r"\b[A-Z]{2}[A-Z0-9]{9}[0-9]\b")
PDF_MIN_BYTES, PDF_MAX_BYTES = 10_000, 20_000_000  # un KID son ~3 páginas: decenas o centenas de KB
KID_MAX_PAGINAS = 12  # KID (3 páginas) más un posible anexo; más es otro documento (folleto, informe)
MAX_FICHAS = 200  # tope de fichas por fuente: si la web cambia, seguir enlaces no se convierte en rastrear el sitio


class WebCambiada(RuntimeError):
    """La estructura de la web ya no es la esperada: hay que revisar el parseo de esa fuente."""


@dataclass(frozen=True)
class KidEnlace:
    """Dónde está un KID según la web de la gestora, antes de descargarlo."""

    gestora: str
    url_pdf: str
    url_ficha: str
    fondo: str | None = None
    clase: str | None = None  # «Clase B», del nombre del PDF, del bloque o de la URL de la ficha
    isin_web: str | None = None  # el ISIN que muestra la web, para contrastar con el del PDF y el extraído
    fecha_web: str | None = None  # fecha que da la web (Azvalor la pone en el nombre del PDF), AAAA-MM-DD


@dataclass(frozen=True)
class Documento:
    """Un PDF descargado, con su procedencia. El SHA-256 es su identidad (D-1.2)."""

    enlace: KidEnlace
    contenido: bytes = field(repr=False)
    descargado_en: datetime
    robots: str = "respetado"  # o "excepción: <motivo>" (D-1.3)
    etag: str | None = None  # cabeceras del servidor, para la siguiente petición condicional (D-1.6)
    last_modified: str | None = None
    http: int = 200  # 304: el servidor confirmó que no ha cambiado y el contenido es la copia ya guardada
    comprobado_en: datetime | None = None  # cuándo se pidió por última vez (con 304, `descargado_en` es el original)
    huella: dict = field(default_factory=dict, compare=False)  # lo que dice el PDF: páginas, ISIN, tipo

    @property
    def sha256(self) -> str:
        return hashlib.sha256(self.contenido).hexdigest()


@dataclass
class Informe:
    """Qué pasó con una fuente en una ejecución: lo que se esperaba frente a lo que llegó."""

    gestora: str
    fichas: int = 0
    enlaces: int = 0
    descargados: int = 0
    sin_cambios: int = 0  # 304: el servidor confirmó que el PDF guardado sigue vigente
    duplicados: int = 0
    sin_kid: list[str] = field(default_factory=list)  # fichas sin enlace al KID
    errores: list[str] = field(default_factory=list)

    @property
    def obtenidos(self) -> int:
        return self.descargados + self.sin_cambios

    def resumen(self) -> str:
        return (f"{self.gestora}: {self.fichas} fichas, {self.enlaces} KID enlazados, {self.descargados} descargados, "
                f"{self.sin_cambios} sin cambios (304), {self.duplicados} duplicados, {len(self.sin_kid)} fichas sin "
                f"KID, {len(self.errores)} errores")


# --- robots.txt -------------------------------------------------------------------------------------------------------

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


# --- Red --------------------------------------------------------------------------------------------------------------

_REINTENTABLES = (requests.ConnectionError, requests.Timeout, requests.exceptions.ChunkedEncodingError)


class SesionEducada:
    """requests.Session con User-Agent propio, robots.txt, pausa mínima, reintentos y validación de PDF.

    No se hace pasar por un navegador ni salta bloqueos (06_piezas_de_la_practica.md §3.1). Reintenta los fallos de
    red, los 5xx y el 429 (respetando `Retry-After`), con espera creciente y siempre con la pausa por servidor.
    """

    def __init__(self, pausa_s: float = 2.0, timeout_s: tuple[float, float] = (10.0, 30.0), reintentos: int = 2,
                 espera_max_s: float = 60.0) -> None:
        self.http = requests.Session()
        self.http.headers["User-Agent"] = USER_AGENT
        self.pausa_s, self.timeout_s, self.reintentos, self.espera_max_s = pausa_s, timeout_s, reintentos, espera_max_s
        self._robots: dict[str, tuple[robotparser.RobotFileParser, list[re.Pattern]]] = {}
        self._ultima: dict[str, float] = {}  # pausa por host

    def _pedir(self, url: str, cabeceras: dict[str, str] | None = None) -> requests.Response:
        """Una petición con la pausa por servidor y los reintentos. No lanza por un 4xx: lo decide quien llama."""
        host = urlparse(url).netloc
        for intento in range(self.reintentos + 1):
            espera = self.pausa_s - (time.monotonic() - self._ultima.get(host, 0.0))
            if espera > 0:
                time.sleep(espera)
            try:
                r = self.http.get(url, timeout=self.timeout_s, headers=cabeceras)
            except _REINTENTABLES:
                self._ultima[host] = time.monotonic()
                if intento == self.reintentos:
                    raise
                espera = self.pausa_s * 2 ** (intento + 1)
            else:
                self._ultima[host] = time.monotonic()
                if (r.status_code < 500 and r.status_code != 429) or intento == self.reintentos:
                    return r
                espera = max(self.pausa_s * 2 ** (intento + 1), _retry_after(r))
            time.sleep(min(espera, self.espera_max_s))
        raise AssertionError("inalcanzable")

    def permitido(self, url: str) -> bool:
        base = "{0.scheme}://{0.netloc}".format(urlparse(url))
        if base not in self._robots:
            rp = robotparser.RobotFileParser(urljoin(base, "/robots.txt"))
            try:
                r = self._pedir(rp.url)
                # RFC 9309: un 4xx permite todo; un 5xx obliga a suponer prohibición total. El fichero va en UTF-8.
                texto_r = r.content.decode("utf-8", "replace") if r.ok else (
                    "User-agent: *\nDisallow: /" if r.status_code >= 500 else "")
            except requests.RequestException:
                texto_r = ""
            rp.parse(texto_r.splitlines())
            self._robots[base] = (rp, prohibidos_con_comodin(texto_r))
        rp, patrones = self._robots[base]
        u = urlparse(url)
        ruta = u.path + (f"?{u.query}" if u.query else "")
        return rp.can_fetch(USER_AGENT, url) and not any(p.match(ruta) or p.match(u.path) for p in patrones)

    def get(self, url: str, respeta_robots: bool = True, cabeceras: dict[str, str] | None = None) -> requests.Response:
        if respeta_robots and not self.permitido(url):
            raise PermissionError(f"robots.txt no permite {url}")
        r = self._pedir(url, cabeceras)
        r.raise_for_status()
        return r

    def descargar(self, enlace: KidEnlace, respeta_robots: bool = True, motivo: str | None = None,
                  previo: dict | None = None, leer: Callable[[dict], bytes | None] | None = None) -> Documento:
        """Descarga el PDF. Con `previo` (su línea del último manifiesto) y `leer` (que devuelve la copia guardada),
        hace una petición condicional: si el servidor responde 304, reutiliza la copia sin volver a bajarla."""
        robots = "respetado" if respeta_robots else f"excepción: {motivo}"
        cabeceras = {}
        if previo and leer:
            if previo.get("etag"):
                cabeceras["If-None-Match"] = previo["etag"]
            if previo.get("last_modified"):
                cabeceras["If-Modified-Since"] = previo["last_modified"]
        r = self.get(enlace.url_pdf, respeta_robots, cabeceras or None)
        if r.status_code == 304 and cabeceras:  # un 304 a una petición no condicional no se puede usar
            copia = leer(previo)
            if copia is not None and hashlib.sha256(copia).hexdigest() == previo["sha256"]:
                return Documento(enlace, copia, datetime.fromisoformat(previo["descargado_en"]), robots,
                                 previo.get("etag"), previo.get("last_modified"), 304, datetime.now(UTC))
            r = self.get(enlace.url_pdf, respeta_robots)  # no hay copia fiable: descarga normal
        validar_pdf(r.content, enlace.url_pdf)
        ahora = datetime.now(UTC)
        return Documento(enlace, r.content, ahora, robots, r.headers.get("ETag"), r.headers.get("Last-Modified"),
                         200, ahora)


def _retry_after(r: requests.Response) -> float:
    try:
        return float(r.headers.get("Retry-After", 0))
    except ValueError:  # también puede ser una fecha HTTP: se usa la espera creciente
        return 0.0


def validar_pdf(contenido: bytes, url: str) -> None:
    if b"%PDF" not in contenido[:1024]:  # la especificación admite bytes antes de la cabecera
        raise ValueError(f"No es un PDF: {url}")
    if not PDF_MIN_BYTES <= len(contenido) <= PDF_MAX_BYTES:
        raise ValueError(f"Tamaño anómalo para un KID ({len(contenido)} bytes): {url}")


# --- Ayudas de parseo -------------------------------------------------------------------------------------------------

def sopa(html: bytes | str) -> BeautifulSoup:
    return BeautifulSoup(html, "html.parser")


def texto(nodo) -> str:
    return " ".join(nodo.get_text(" ", strip=True).split()) if nodo else ""


def normal(cadena: str) -> str:
    """Minúsculas, sin tildes y con los espacios comprimidos: «Información» e «INFORMACION» comparan igual."""
    sin_tildes = unicodedata.normalize("NFKD", cadena).encode("ascii", "ignore").decode()
    return " ".join(sin_tildes.lower().split())


def compacto(cadena: str) -> str:
    """`normal` sin espacios: pypdf a veces parte palabras («DOCU MENTO»), así que se compara sin ellos."""
    return normal(cadena).replace(" ", "")


def isines(cadena: str) -> list[str]:
    """Los ISIN válidos (dígito de control incluido) de un texto, sin repetir y en orden de aparición."""
    return list(dict.fromkeys(i for i in _ISIN.findall(cadena) if isin_valido(i)))


def primer_isin(cadena: str) -> str | None:
    return next(iter(isines(cadena)), None)


def isin_tras(cadena: str, etiqueta: str) -> str | None:
    """El primer ISIN válido después de una etiqueta («Código ISIN», «ISIN»); si no, el primero de la página."""
    pos = cadena.find(etiqueta)
    return primer_isin(cadena[pos:]) if pos >= 0 else primer_isin(cadena)


# Cómo llaman las gestoras al KID (enunciado §2: muchas siguen diciendo «DFI»). Se compara con el texto `normal`.
TEXTO_KID = re.compile(r"datos fundamentales|\bk(?:i)?ids?\b|\bdfi\b|\bdfp\b|\bpriips?\b|folleto simplificado"
                       r"|key (?:investor )?information")
NO_KID = re.compile(r"escenario|rentabilidad|informe|cuentas|reglamento|folleto completo|politica|anexo")
_GENERICO = re.compile(r"^(?:(?:descargar|descarga|ver|aqui|download|pdf)\b\W*)*$")  # rótulos que no dicen qué es
_CLASE = re.compile(r"(?<![a-z])(?:clase|cl)[\s_+\-.]+([a-z]\d?)(?![a-z0-9])")
_ROTULO_CLASE = re.compile(r"^clase [a-z0-9]{1,3}$")
_FECHA = re.compile(r"(?<!\d)(\d{1,2})[.\-_](\d{1,2})[.\-_](\d{4})(?!\d)"  # DD.MM.AAAA o AAAA-MM-DD
                    r"|(?<!\d)(\d{4})[.\-_](\d{2})[.\-_](\d{2})(?!\d)")


def url_absoluta(base: str, href: str) -> str | None:
    """URL absoluta, sin fragmento y con espacios y caracteres no ASCII codificados; None si no es http(s)."""
    u = urlparse(urljoin(base, re.sub(r"[\t\r\n]", "", href).strip()))
    if u.scheme not in ("http", "https"):
        return None
    return requote_uri(urlunparse(u._replace(fragment="")))


def nombre_fichero(url: str) -> str:
    return unquote(urlparse(url).path.rsplit("/", 1)[-1])


def es_enlace_kid(a) -> bool:
    """Un enlace a PDF cuyo rótulo (texto, `title` o `aria-label`) nombra el KID; si el rótulo no dice nada
    («Descargar», un icono), decide el nombre del fichero (`dfi-...pdf`, `..._datos_fundamentales.pdf`)."""
    href = a.get("href", "")
    if ".pdf" not in href.lower():
        return False
    rotulo = normal(" ".join([texto(a), a.get("title", ""), a.get("aria-label", "")]))
    if NO_KID.search(rotulo):
        return False
    if TEXTO_KID.search(rotulo):
        return True
    if _GENERICO.match(normal(texto(a))):
        fichero = normal(re.sub(r"[_\-+.]+", " ", nombre_fichero(href)))
        return bool(TEXTO_KID.search(fichero)) and not NO_KID.search(fichero)
    return False


def anclas_kid(s, base: str, limpiar: Callable[[str], str] = lambda u: u) -> dict[str, list]:
    """URL de cada KID de la página (limpia y sin repetir) con los `<a>` que la enlazan, en orden de aparición."""
    out: dict[str, list] = {}
    for a in s.find_all("a", href=True):
        if es_enlace_kid(a) and (u := url_absoluta(base, a["href"])):
            out.setdefault(limpiar(u), []).append(a)
    return out


def bloque_de(a, url_de: dict[int, str], max_niveles: int = 10):
    """El ancestro más cercano con algún ISIN (el bloque de la clase) y su ISIN, solo si es inequívoco: un ISIN y un
    único KID en el bloque. Con dos KID y un ISIN no se sabe de cuál es: mejor null que inventar."""
    for padre in list(a.parents)[:max_niveles]:
        encontrados = isines(texto(padre))
        if encontrados:
            kids = {url_de[id(x)] for x in padre.find_all("a", href=True) if id(x) in url_de}
            return padre, (encontrados[0] if len(encontrados) == 1 and len(kids) == 1 else None)
    return None, None


def clase_en(cadena: str) -> str | None:
    """«Clase B» a partir de «clase_b», «Clase+B», «CL-B2» o «Clase B» (sin distinguir mayúsculas)."""
    m = _CLASE.search(normal(unquote(cadena)))
    return f"Clase {m.group(1).upper()}" if m else None


def clases_en(cadena: str) -> set[str]:
    return {f"Clase {c.upper()}" for c in _CLASE.findall(normal(cadena))}


def fecha_en_nombre(url: str) -> str | None:
    """La fecha del nombre del PDF (`DFP-Iberia-09.01.2026.pdf`), AAAA-MM-DD, si es una fecha que existe."""
    for m in _FECHA.finditer(nombre_fichero(url)):
        d, mes, a = (m.group(1), m.group(2), m.group(3)) if m.group(1) else (m.group(6), m.group(5), m.group(4))
        try:
            return date(int(a), int(mes), int(d)).isoformat()
        except ValueError:
            continue
    return None


def normalizar_ficha(url: str, base: str, ruta: str, excluir: frozenset[str] | set[str] = frozenset()) -> str | None:
    """La URL de una ficha normalizada (`<ruta><slug>/`, sin query), o None si no es una ficha de fondo."""
    u = urlparse(urljoin(base, url.split("#")[0].strip()))
    m = re.match(rf"^{re.escape(ruta)}([^/]+)/?$", u.path)
    if not m or u.netloc != urlparse(base).netloc or m.group(1) in excluir:
        return None
    return urlunparse((u.scheme, u.netloc, u.path.rstrip("/") + "/", "", "", ""))


def fichas_del_listado(html: bytes | str, base: str, ruta: str, excluir: frozenset[str] | set[str] = frozenset(),
                       solo_rotulo: re.Pattern | None = None) -> list[str]:
    """URL de las fichas enlazadas cuya ruta es `<ruta><slug>/`, en orden de aparición y sin repetir."""
    vistos: dict[str, None] = {}
    for a in sopa(html).find_all("a", href=True):
        if solo_rotulo and not solo_rotulo.match(normal(texto(a) or a.get("title", ""))):
            continue
        if f := normalizar_ficha(a["href"], base, ruta, excluir):
            vistos[f] = None
    return list(vistos)


def sin_query(url: str) -> str:
    return urlunparse(urlparse(url)._replace(query="", fragment=""))


# --- Lectura del PDF --------------------------------------------------------------------------------------------------

_MARCAS_PRIIPS = ("indicadorresumidoderiesgo", "summaryriskindicator")
_TITULO_PRIIPS = ("documentodedatosfundamentales", "keyinformationdocument")
_MARCAS_UCITS = ("datosfundamentalesparaelinversor", "keyinvestorinformation", "perfilderiesgoyremuneracion",
                 "riskandrewardprofile")


def texto_pdf(contenido: bytes) -> tuple[int, str]:
    from pypdf import PdfReader

    lector = PdfReader(io.BytesIO(contenido))
    return len(lector.pages), " ".join((p.extract_text() or "") for p in lector.pages)


def tipo_documento(txt: str) -> str | None:
    """«KID PRIIPs» (desde 2023), «KIID UCITS» (el DFI antiguo) o None si el texto no es de ninguno (§2.6 teoría).

    El indicador resumido de riesgo solo existe en el KID PRIIPs; el título solo vale si no es el del KIID.
    """
    t = compacto(txt)
    ucits = any(k in t for k in _MARCAS_UCITS)
    if any(k in t for k in _MARCAS_PRIIPS) or (not ucits and any(k in t for k in _TITULO_PRIIPS)):
        return "KID PRIIPs"
    return "KIID UCITS" if ucits else None


def isin_del_pdf(txt: str, isin_web: str | None = None) -> str | None:
    """El ISIN de la clase según el PDF: el de la web si aparece; si no, el único del texto o el que sigue a «ISIN»."""
    encontrados = isines(txt)
    if isin_web and (isin_web in encontrados or isin_web.lower() in compacto(txt)):
        return isin_web
    return encontrados[0] if len(encontrados) == 1 else isin_tras(txt, "ISIN")


def huella(contenido: bytes, isin_web: str | None = None) -> tuple[dict, str]:
    """Lo que el PDF dice de sí mismo (páginas, ISIN, tipo) y su texto. Un PDF que pypdf no lee da campos a None."""
    try:
        paginas, txt = texto_pdf(contenido)
    except Exception:  # PDF mal formado: se guarda igual y `verificar` lo señala
        return {"paginas": None, "isin_pdf": None, "tipo_documento": None}, ""
    return {"paginas": paginas, "isin_pdf": isin_del_pdf(txt, isin_web), "tipo_documento": tipo_documento(txt)}, txt


# --- Fuentes ----------------------------------------------------------------------------------------------------------

class Fuente:
    """Una gestora: dónde está su listado, de qué ruta cuelgan las fichas y cómo limpiar la URL del PDF.

    El parseo es común: en cada ficha se buscan los enlaces al KID por su rótulo (`es_enlace_kid`), y a cada uno se le
    asigna el ISIN y la clase de su bloque. Las fichas enlazadas con el rótulo «Clase X» (Bestinver tiene una página
    por clase) se visitan también. `enlaces()` junta todo con la red.
    """

    nombre: str
    inicio: str
    ruta: str  # las fichas son <ruta><slug>/
    NO_FONDOS: frozenset[str] = frozenset()
    respeta_robots: bool = True
    motivo_robots: str | None = None

    def limpiar_url(self, url: str) -> str:
        return url

    def fichas(self, html_listado: bytes | str) -> list[str]:
        return fichas_del_listado(html_listado, self.inicio, self.ruta, self.NO_FONDOS)

    def otras_fichas(self, html_ficha: bytes | str, url_ficha: str) -> list[str]:
        """Fichas hermanas enlazadas como «Clase R», «Clase Z2»: otra clase del mismo fondo, con su propio KID."""
        otras = fichas_del_listado(html_ficha, url_ficha, self.ruta, self.NO_FONDOS, _ROTULO_CLASE)
        return [u for u in otras if u != url_ficha]

    def kids(self, html_ficha: bytes | str, url_ficha: str) -> list[KidEnlace]:
        s = sopa(html_ficha)
        anclas = anclas_kid(s, url_ficha, self.limpiar_url)
        url_de = {id(a): u for u, lista in anclas.items() for a in lista}
        fondo = texto(s.find("h1")) or None
        # con un solo KID, el ISIN de la ficha es el suyo; con varios, cada uno necesita su bloque
        isin_ficha = isin_tras(texto(s), "ISIN") if len(anclas) == 1 else None
        clase_ficha = clase_en(urlparse(url_ficha).path) if len(anclas) == 1 else None
        out = []
        for url, lista in anclas.items():
            bloque, isin = bloque_de(lista[0], url_de)
            cabecera = texto(bloque.find(["h2", "h3", "h4"])) if bloque and isin else ""
            clase = (clase_en(urlparse(url).path) or clase_en(" ".join(texto(a) for a in lista))
                     or clase_en(cabecera) or clase_ficha)
            out.append(KidEnlace(self.nombre, url, url_ficha, fondo, clase, isin or isin_ficha, fecha_en_nombre(url)))
        return out

    def enlaces(self, sesion: SesionEducada, informe: Informe) -> Iterator[KidEnlace]:
        pendientes = self.fichas(sesion.get(self.inicio).content)
        informe.fichas = len(pendientes)
        if not pendientes:
            raise WebCambiada(f"{self.nombre}: el listado {self.inicio} no tiene fichas de fondos")
        vistos: set[str] = set()
        i = 0
        while i < len(pendientes):
            url = pendientes[i]
            i += 1
            try:
                html = sesion.get(url).content
            except (requests.RequestException, PermissionError) as e:
                informe.errores.append(f"{url}: {e}")
                continue
            for otra in self.otras_fichas(html, url):
                if otra not in pendientes and len(pendientes) < MAX_FICHAS:
                    pendientes.append(otra)
            informe.fichas = len(pendientes)
            kids = [k for k in self.kids(html, url) if k.url_pdf not in vistos]  # otra clase puede enlazar el mismo
            if not kids:
                informe.sin_kid.append(url)
            vistos.update(k.url_pdf for k in kids)
            informe.enlaces += len(kids)
            yield from kids
        if not informe.enlaces:
            raise WebCambiada(f"{self.nombre}: ninguna de las {len(pendientes)} fichas enlaza un KID")


class Bestinver(Fuente):
    """Dificultad baja: cada ficha /fondos-de-inversion/<fondo>/ enlaza «Datos Fundamentales». Una clase por ficha:
    los fondos con varias clases tienen una ficha por clase (`...-clase-r/`), enlazada desde la ficha principal.

    Su robots.txt pide no descargar PDF (`Disallow: /*.pdf$`); el profesor autorizó hacerlo en el Taller 1 (D-1.3).
    El parámetro `?h=` del enlace cambia en cada carga: se quita para que la URL guardada sea estable.
    """

    nombre = "bestinver"
    inicio = "https://www.bestinver.es/fondos-de-inversion/"
    ruta = "/fondos-de-inversion/"
    respeta_robots = False
    motivo_robots = "autorizado por el profesor en el Taller 1 (D-1.3)"
    NO_FONDOS = frozenset({"como-contratar-un-fondo-de-inversion", "como-funcionan-y-que-ventajas-tienen", "otros",
                           "por-que-un-fondo-de-inversion", "sicav-luxemburguesas"})

    def limpiar_url(self, url):
        return sin_query(url)


class Azvalor(Fuente):
    """Dificultad media: ficha con «Folleto simplificado (DFP)». El nombre del PDF lleva la fecha: se lee del HTML.

    El 19/11/2026 las fichas colgaban de /fondos-de-inversion/, no de /fondos/ como dice el enunciado (D-1.3).
    """

    nombre = "azvalor"
    inicio = "https://www.azvalor.com/fondos-de-inversion/"
    ruta = "/fondos-de-inversion/"


class Cobas(Fuente):
    """Dificultad media-alta: un bloque `article.ficha` por clase (A, B, C, D), con su ISIN y su «PRIIP pdf».

    Solo fondos y SICAV (/productos/inversion-libre/): los planes de pensiones no publican un KID PRIIPs.
    """

    nombre = "cobas"
    inicio = "https://www.cobasam.com/productos/"
    ruta = "/productos/inversion-libre/"


FUENTES: dict[str, type[Fuente]] = {f.nombre: f for f in (Bestinver, Azvalor, Cobas)}


def capturar(fuente: Fuente, sesion: SesionEducada, informe: Informe, vistos: set[str],
             previos: dict[str, dict] | None = None,
             leer: Callable[[dict], bytes | None] | None = None) -> Iterator[Documento]:
    """Descarga los KID de una fuente. Los errores de un documento se registran y no paran el resto.

    `previos` (url_pdf -> línea del último manifiesto) y `leer` activan las peticiones condicionales (D-1.6).
    Un PDF legible que no es un KID (sin las marcas del KID o con demasiadas páginas) se rechaza (D-1.5).
    """
    previos = previos or {}
    host = urlparse(fuente.inicio).netloc
    for enlace in fuente.enlaces(sesion, informe):
        # la excepción de robots (D-1.3) vale para los PDF del propio servidor de la gestora, no para otros
        respeta = fuente.respeta_robots or urlparse(enlace.url_pdf).netloc != host
        try:
            doc = sesion.descargar(enlace, respeta, fuente.motivo_robots, previos.get(enlace.url_pdf), leer)
            h, txt = huella(doc.contenido, enlace.isin_web)
            if txt.strip() and (h["tipo_documento"] is None or h["paginas"] > KID_MAX_PAGINAS):
                raise ValueError(f"el PDF no parece un KID ({h['paginas']} páginas, tipo {h['tipo_documento']})")
        except (requests.RequestException, ValueError, PermissionError) as e:
            informe.errores.append(f"{enlace.url_pdf}: {e}")
            continue
        doc = replace(doc, huella=h)
        if doc.sha256 in vistos:
            informe.duplicados += 1
            continue
        vistos.add(doc.sha256)
        if doc.http == 304:
            informe.sin_cambios += 1
        else:
            informe.descargados += 1
        yield doc
