"""Conector de Homecenter Colombia (extracción de la página de producto).

Homecenter no tiene API pública de productos, así que se lee la página de cada producto del
catálogo (ids.homecenter = ["3111000"], el número de la dirección /product/3111000/...).
La página trae sus datos como JSON en <script id="__NEXT_DATA__"> (productProps.result).

robots.txt: permite las páginas de producto y prohíbe la búsqueda (*/search?), por eso este
conector nunca busca por texto. El ClienteHttp lo verifica en cada petición.

Envío y días de entrega: Homecenter los calcula cuando el comprador elige la dirección de
entrega. Quedan como desconocidos (None) y la plataforma muestra un aviso.

Precio: el menor precio vigente (normalmente INTERNET frente a NORMAL). Se ignora el precio
con tarjeta CMR, porque los descuentos por medio de pago están fuera del alcance del proyecto.
"""

import json
import re
from typing import Any

from app.extraccion.cliente_http import ClienteHttp, ErrorHttp
from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.normalizacion import ErrorNormalizacion, parsear_precio_cop
from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo

URL_BASE = "https://www.homecenter.com.co"
NOTA_ENVIO = (
    "Homecenter calcula el envío cuando eliges la dirección de entrega; algunos productos lo "
    "anuncian gratis. El costo de envío se conoce al pagar en Homecenter."
)
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def url_producto(producto_id: str) -> str:
    return f"{URL_BASE}/homecenter-co/product/{producto_id}"


class ConectorHomecenter(Conector):
    nombre_plataforma = "Homecenter"
    clave_catalogo = "homecenter"

    def __init__(self, cliente: ClienteHttp) -> None:
        self._cliente = cliente

    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        ofertas = []
        for producto_id in producto.ids.get(self.clave_catalogo, []):
            oferta = self._leer_producto(producto_id)
            if oferta is not None:
                ofertas.append(oferta)
        return ofertas

    def actualizar(self, url: str) -> OfertaCapturada | None:
        coincidencia = re.search(r"/product/(\d+)", url)
        if coincidencia is None:
            raise ErrorConector(f"No es una dirección de producto de Homecenter: {url}")
        return self._leer_producto(coincidencia.group(1))

    def nota_envio(self) -> str | None:
        return NOTA_ENVIO

    def _leer_producto(self, producto_id: str) -> OfertaCapturada | None:
        try:
            respuesta = self._cliente.get(url_producto(producto_id))
        except ErrorHttp as error:
            if error.status_code == 404:  # el producto ya no existe
                return None
            raise

        coincidencia = _NEXT_DATA.search(respuesta.text)
        if coincidencia is None:
            raise ErrorConector(f"La página del producto {producto_id} cambió: no tiene __NEXT_DATA__")
        try:
            datos = json.loads(coincidencia.group(1))
        except ValueError as error:
            raise ErrorConector(f"__NEXT_DATA__ del producto {producto_id} no es JSON válido") from error

        producto = (datos["props"]["pageProps"].get("productProps") or {}).get("result")
        if not producto or not producto.get("variants"):
            raise ErrorConector(f"La página del producto {producto_id} no trae datos del producto")
        principal = producto.get("primaryVariantId")
        variante = next((v for v in producto["variants"] if v.get("id") == principal), producto["variants"][0])

        return OfertaCapturada(
            titulo=producto["name"],
            url=url_producto(producto_id),
            vendedor=self._vendedor(variante),
            precio=self._precio(variante, producto_id),
            moneda="COP",
            envio=None,
            dias_entrega=None,
            disponible=any(
                a.get("hasStock") and a.get("shippingType") == "homeDelivery" for a in variante.get("availability") or []
            ),
        )

    @staticmethod
    def _vendedor(variante: dict[str, Any]) -> str:
        # Las publicaciones de terceros traen el vendedor en offers; si no hay, vende Homecenter
        ofertas = variante.get("offers") or []
        return (ofertas[0].get("sellerName") if ofertas else None) or "Homecenter"

    @staticmethod
    def _precio(variante: dict[str, Any], producto_id: str):
        vigentes = []
        for precio in variante.get("price") or []:
            if "cmr" in str(precio.get("type", "")).lower():
                continue
            try:
                vigentes.append(parsear_precio_cop(str(precio.get("price", ""))))
            except ErrorNormalizacion as error:
                raise ErrorConector(f"Precio no reconocido en el producto {producto_id}: {error}") from error
        if not vigentes:
            raise ErrorConector(f"El producto {producto_id} no tiene un precio vigente")
        return min(vigentes)
