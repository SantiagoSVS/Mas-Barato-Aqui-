"""Conector de Mercado Libre Colombia (API oficial, sitio MCO).

Trabaja con los identificadores de producto del catálogo de Mercado Libre que se anotan en
catalogo.toml (ids.mercadolibre = ["MCO..."]). Por cada uno:

1. /products/{id}: nombre del producto en Mercado Libre.
2. /products/{id}/items: publicaciones (vendedores) del producto, con precio y moneda.
3. /items/{id}/shipping_options: costo de envío y fecha estimada de entrega hasta la ciudad
   de destino configurada.

Autenticación: token de aplicación (client_credentials) con el client id y el secret de la
app de desarrollador. El token dura 6 horas y se renueva solo.

Por qué identificadores y no búsqueda por texto (pruebas del 1 de noviembre de 2026):
- /sites/MCO/search y /items/{id} responden 403 para tokens de aplicación.
- /products/search sí responde, pero solo 1 de cada 20 productos que devuelve tiene
  publicaciones activas, y muchos no tienen relación con lo buscado. Para encontrar los
  identificadores está la herramienta: python -m app.herramientas.buscar_mercadolibre "texto"
"""

import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.extraccion.cliente_http import ClienteHttp, ErrorHttp
from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo

URL_API = "https://api.mercadolibre.com"
SITIO = "MCO"
ZONA_COLOMBIA = ZoneInfo("America/Bogota")
# Margen para renovar el token un poco antes de que venza
MARGEN_TOKEN_S = 300


def url_publicacion(item_id: str) -> str:
    """Enlace a la publicación original: MCO4113792896 -> .../MCO-4113792896."""
    return f"https://articulo.mercadolibre.com.co/{item_id[:3]}-{item_id[3:]}"


@dataclass(frozen=True)
class ProductoEncontrado:
    """Resultado de buscar_en_catalogo, para elegir identificadores del catálogo."""

    id: str
    nombre: str
    publicaciones: int


class ConectorMercadoLibre(Conector):
    nombre_plataforma = "Mercado Libre"
    clave_catalogo = "mercadolibre"

    def __init__(
        self,
        cliente: ClienteHttp,
        client_id: str,
        client_secret: str,
        ciudad_destino: str,
        ofertas_por_producto: int,
        hoy: Callable[[], date] = lambda: datetime.now(ZONA_COLOMBIA).date(),
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cliente = cliente
        self._client_id = client_id
        self._client_secret = client_secret
        self._ciudad_destino = ciudad_destino
        self._ofertas_por_producto = ofertas_por_producto
        self._hoy = hoy
        self._reloj = reloj
        self._token: str | None = None
        self._token_vence: float = 0

    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        ofertas: list[OfertaCapturada] = []
        for producto_id in producto.ids.get(self.clave_catalogo, []):
            nombre = self._get(f"/products/{producto_id}")["name"]
            for item in self._publicaciones(producto_id):
                oferta = self._convertir(nombre, item)
                if oferta is not None:
                    ofertas.append(oferta)
        return ofertas

    def actualizar(self, url: str) -> OfertaCapturada | None:
        raise ErrorConector(
            "La API de Mercado Libre no permite consultar una publicación suelta con token de "
            "aplicación (/items responde 403); las ofertas se actualizan con cada captura."
        )

    def buscar_en_catalogo(self, texto: str, limite: int = 20) -> list[ProductoEncontrado]:
        """Busca productos del catálogo de Mercado Libre y cuenta sus publicaciones activas.

        Solo la usa la herramienta para armar catalogo.toml; el worker no la llama.
        """
        resultados = self._get(
            "/products/search", {"status": "active", "site_id": SITIO, "q": texto, "limit": str(limite)}
        )["results"]
        return [
            ProductoEncontrado(id=r["id"], nombre=r["name"], publicaciones=len(self._publicaciones(r["id"])))
            for r in resultados
        ]

    def verificar_producto(self, producto_id: str) -> ProductoEncontrado:
        """Nombre y publicaciones activas de un identificador, antes de anotarlo en el catálogo."""
        nombre = self._get(f"/products/{producto_id}")["name"]
        return ProductoEncontrado(id=producto_id, nombre=nombre, publicaciones=len(self._publicaciones(producto_id)))

    def _publicaciones(self, producto_id: str) -> list[dict[str, Any]]:
        try:
            items = self._get(f"/products/{producto_id}/items")["results"]
        except ErrorHttp as error:
            if error.status_code == 404:  # producto sin publicaciones activas
                return []
            raise
        return items[: self._ofertas_por_producto]

    def _convertir(self, nombre: str, item: dict[str, Any]) -> OfertaCapturada | None:
        # Solo productos nuevos: un usado no es el mismo producto para comparar precios
        if item.get("condition") != "new" or item.get("currency_id") not in ("COP", "USD"):
            return None

        envio, dias = self._envio(item["item_id"])
        return OfertaCapturada(
            titulo=nombre,
            url=url_publicacion(item["item_id"]),
            vendedor=str(item["seller_id"]) if item.get("seller_id") is not None else None,
            precio=Decimal(str(item["price"])),
            moneda=item["currency_id"],
            envio=envio,
            dias_entrega=dias,
            disponible=True,
        )

    def _envio(self, item_id: str) -> tuple[Decimal | None, int | None]:
        """Costo y días de entrega de la opción que Mercado Libre recomienda al comprador.

        Si no se puede consultar, ambos quedan en None (desconocidos), nunca en 0.
        """
        try:
            opciones = self._get(f"/items/{item_id}/shipping_options", {"city_to": self._ciudad_destino})["options"]
        except ErrorConector:
            return None, None
        if not opciones:
            return None, None

        opcion = next((o for o in opciones if o.get("display") == "recommended"), None)
        if opcion is None:
            opcion = min(opciones, key=lambda o: o.get("cost", float("inf")))

        costo = opcion.get("cost")
        envio = None if costo is None else Decimal(str(costo))
        return envio, self._dias_hasta(opcion.get("estimated_delivery_time") or {})

    def _dias_hasta(self, entrega: dict[str, Any]) -> int | None:
        if not entrega.get("date"):
            return None
        fecha = datetime.fromisoformat(entrega["date"]).astimezone(ZONA_COLOMBIA).date()
        return max(0, (fecha - self._hoy()).days)

    def _get(self, ruta: str, params: dict[str, str] | None = None) -> dict[str, Any]:
        respuesta = self._cliente.get(
            URL_API + ruta,
            params=params,
            encabezados={"Authorization": f"Bearer {self._obtener_token()}", "Accept": "application/json"},
            es_api_oficial=True,
        )
        try:
            return respuesta.json()
        except ValueError as error:
            raise ErrorConector(f"{ruta}: la respuesta no es JSON válido") from error

    def _obtener_token(self) -> str:
        if self._token is None or self._reloj() >= self._token_vence:
            respuesta = self._cliente.post_api(
                f"{URL_API}/oauth/token",
                {
                    "grant_type": "client_credentials",
                    "client_id": self._client_id,
                    "client_secret": self._client_secret,
                },
                encabezados={"Accept": "application/json"},
            )
            datos = respuesta.json()
            self._token = datos["access_token"]
            self._token_vence = self._reloj() + int(datos.get("expires_in", 0)) - MARGEN_TOKEN_S
        return self._token
