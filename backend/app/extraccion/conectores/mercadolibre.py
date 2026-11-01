"""Conector de Mercado Libre Colombia (API oficial, sitio MCO).

Cómo obtiene cada dato:

1. /products/search: productos del catálogo de Mercado Libre que coinciden con el término.
2. /products/{id}/items: publicaciones (vendedores) de cada producto, con precio y moneda.
3. /items/{id}/shipping_options: costo de envío y fecha estimada de entrega hasta la ciudad
   de destino configurada.

Autenticación: token de aplicación (client_credentials) con el client id y el secret de la
app de desarrollador. El token dura 6 horas y se renueva solo.

Limitaciones conocidas de la API (noviembre de 2026):
- /sites/MCO/search y /items/{id} responden 403 para tokens de aplicación, por eso se busca en
  el catálogo y no se puede actualizar una publicación suelta.
- Los productos sin publicaciones activas responden 404 en /products/{id}/items y se omiten.
"""

import time
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Any
from zoneinfo import ZoneInfo

from app.extraccion.cliente_http import ClienteHttp, ErrorHttp
from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.tipos import OfertaCapturada

URL_API = "https://api.mercadolibre.com"
SITIO = "MCO"
ZONA_COLOMBIA = ZoneInfo("America/Bogota")
# Margen para renovar el token un poco antes de que venza
MARGEN_TOKEN_S = 300


def url_publicacion(item_id: str) -> str:
    """Enlace a la publicación original: MCO4113792896 -> .../MCO-4113792896."""
    return f"https://articulo.mercadolibre.com.co/{item_id[:3]}-{item_id[3:]}"


class ConectorMercadoLibre(Conector):
    nombre_plataforma = "Mercado Libre"

    def __init__(
        self,
        cliente: ClienteHttp,
        client_id: str,
        client_secret: str,
        ciudad_destino: str,
        productos_por_termino: int,
        ofertas_por_producto: int,
        hoy: Callable[[], date] = lambda: datetime.now(ZONA_COLOMBIA).date(),
        reloj: Callable[[], float] = time.monotonic,
    ) -> None:
        self._cliente = cliente
        self._client_id = client_id
        self._client_secret = client_secret
        self._ciudad_destino = ciudad_destino
        self._productos_por_termino = productos_por_termino
        self._ofertas_por_producto = ofertas_por_producto
        self._hoy = hoy
        self._reloj = reloj
        self._token: str | None = None
        self._token_vence: float = 0

    def buscar(self, termino: str) -> list[OfertaCapturada]:
        productos = self._get(
            "/products/search",
            {"status": "active", "site_id": SITIO, "q": termino, "limit": str(self._productos_por_termino)},
        )["results"]

        ofertas: list[OfertaCapturada] = []
        for producto in productos:
            for item in self._publicaciones(producto["id"]):
                oferta = self._convertir(producto, item)
                if oferta is not None:
                    ofertas.append(oferta)
        return ofertas

    def actualizar(self, url: str) -> OfertaCapturada | None:
        raise ErrorConector(
            "La API de Mercado Libre no permite consultar una publicación suelta con token de "
            "aplicación (/items responde 403); las ofertas se actualizan al volver a buscar."
        )

    def _publicaciones(self, producto_id: str) -> list[dict[str, Any]]:
        try:
            items = self._get(f"/products/{producto_id}/items")["results"]
        except ErrorHttp as error:
            if error.status_code == 404:  # producto sin publicaciones activas
                return []
            raise
        return items[: self._ofertas_por_producto]

    def _convertir(self, producto: dict[str, Any], item: dict[str, Any]) -> OfertaCapturada | None:
        # Solo productos nuevos: un usado no es el mismo producto para comparar precios
        if item.get("condition") != "new" or item.get("currency_id") not in ("COP", "USD"):
            return None

        envio, dias = self._envio(item["item_id"])
        return OfertaCapturada(
            titulo=producto["name"],
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
