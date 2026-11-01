"""Dobles de prueba: reemplazan tiendas, internet y la TRM para que las pruebas sean
rápidas, repetibles y no dependan de la red. Los precios son datos de prueba, no reales."""

from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal

from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.tasa_cambio import ErrorTasaCambio, ProveedorTasaCambio, TasaCambio
from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo


class ConectorFalso(Conector):
    """Devuelve ofertas fijas por nombre de producto. Un producto en `fallas` simula una
    tienda caída."""

    nombre_plataforma = "Tienda falsa"
    clave_catalogo = "falsa"

    def __init__(
        self,
        ofertas_por_producto: dict[str, list[OfertaCapturada]],
        fallas: set[str] | None = None,
    ) -> None:
        self.ofertas_por_producto = ofertas_por_producto
        self.fallas = fallas or set()

    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        if producto.nombre in self.fallas:
            raise ErrorConector(f"la tienda no respondió a {producto.nombre!r}")
        return self.ofertas_por_producto.get(producto.nombre, [])

    def actualizar(self, url: str) -> OfertaCapturada | None:
        return None


class ConectorRoto(Conector):
    """Falla con un error inesperado (no ErrorConector), como un bug en un conector."""

    nombre_plataforma = "Tienda rota"
    clave_catalogo = "rota"

    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        raise RuntimeError("error inesperado del conector")

    def actualizar(self, url: str) -> OfertaCapturada | None:
        return None


class ProveedorTasaFalso(ProveedorTasaCambio):
    def __init__(self, valor: Decimal | None) -> None:
        self.valor = valor
        self.consultas = 0

    def obtener(self, moneda: str, fecha: date) -> TasaCambio:
        self.consultas += 1
        if self.valor is None:
            raise ErrorTasaCambio("TRM no disponible")
        return TasaCambio(moneda=moneda, valor=self.valor, fecha=fecha, fuente="prueba")


@dataclass
class RespuestaFalsa:
    status_code: int
    text: str = ""
    datos: object = None

    def json(self) -> object:
        if self.datos is None:
            raise ValueError("no es JSON")
        return self.datos


@dataclass
class SesionHttpFalsa:
    """Sustituye a requests.Session: responde según la URL y guarda cada petición."""

    respuestas: dict[str, RespuestaFalsa]
    peticiones: list[dict] = field(default_factory=list)

    def get(self, url, params=None, headers=None, timeout=None, allow_redirects=True):
        self.peticiones.append({"url": url, "params": params, "headers": headers, "timeout": timeout})
        if url not in self.respuestas:
            return RespuestaFalsa(status_code=404)
        respuesta = self.respuestas[url]
        if isinstance(respuesta, Exception):
            raise respuesta
        return respuesta

    def post(self, url, data=None, headers=None, timeout=None):
        self.peticiones.append({"url": url, "data": data, "headers": headers, "timeout": timeout, "metodo": "POST"})
        return self.respuestas.get(url, RespuestaFalsa(status_code=404))


def producto(nombre: str, categoria: str = "tecnologia", **ids: list[str]) -> ProductoCatalogo:
    return ProductoCatalogo(nombre=nombre, categoria=categoria, ids=ids)


def oferta(
    url: str,
    precio: str,
    moneda: str = "COP",
    envio: str | None = None,
    dias: int | None = None,
    titulo: str = "Producto de prueba",
) -> OfertaCapturada:
    return OfertaCapturada(
        titulo=titulo,
        url=url,
        precio=Decimal(precio),
        moneda=moneda,
        envio=None if envio is None else Decimal(envio),
        dias_entrega=dias,
    )
