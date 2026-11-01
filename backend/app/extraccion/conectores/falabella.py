"""Conector de Falabella Colombia (extracción de la página de producto).

Falabella no tiene API pública de productos, así que se lee la página de cada producto del
catálogo (ids.falabella = ["73336565"], el número de la dirección /product/73336565/...).
La página trae sus datos como JSON en <script id="__NEXT_DATA__">, sin necesidad de ejecutar
JavaScript. Se respeta robots.txt (permite estas páginas) y el límite de frecuencia del
ClienteHttp.

Envío y días de entrega: Falabella los calcula en el navegador después de que el comprador
elige departamento, ciudad y barrio, con consultas internas no documentadas. No se replican:
quedan como desconocidos (None), y la plataforma muestra el aviso de envío gratis que la
propia página publica (por ejemplo, "desde $149.000"), aclarando que no aplica a todo.

Precio: el menor precio vigente para cualquier comprador. Se ignoran los precios tachados
(precio anterior) y el precio con tarjeta CMR, porque los descuentos por medio de pago están
fuera del alcance del proyecto.
"""

import json
import re
from typing import Any

from app.extraccion.cliente_http import ClienteHttp, ErrorHttp
from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.normalizacion import ErrorNormalizacion, parsear_precio_cop
from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo

URL_BASE = "https://www.falabella.com.co"
_NEXT_DATA = re.compile(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S)


def url_producto(producto_id: str) -> str:
    return f"{URL_BASE}/falabella-co/product/{producto_id}"


class ConectorFalabella(Conector):
    nombre_plataforma = "Falabella"
    clave_catalogo = "falabella"

    def __init__(self, cliente: ClienteHttp) -> None:
        self._cliente = cliente
        self._umbral_envio_gratis: str | None = None

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
            raise ErrorConector(f"No es una dirección de producto de Falabella: {url}")
        return self._leer_producto(coincidencia.group(1))

    def nota_envio(self) -> str | None:
        if self._umbral_envio_gratis is None:
            return None
        return (
            f"Falabella anuncia envío gratis desde {self._umbral_envio_gratis}, pero no aplica a "
            "todos los productos. El costo de envío se conoce al pagar en Falabella."
        )

    def _leer_producto(self, producto_id: str) -> OfertaCapturada | None:
        try:
            respuesta = self._cliente.get(url_producto(producto_id))
        except ErrorHttp as error:
            if error.status_code == 404:  # el producto ya no existe
                return None
            raise
        datos = self._datos_de_la_pagina(respuesta.text, producto_id)

        umbral = datos["props"]["pageProps"].get("appCtx", {}).get("siteConfig", {}).get("textDictionary", {})
        if umbral.get("ENVIO_GRATIS_LABEL_AMOUNT"):
            self._umbral_envio_gratis = umbral["ENVIO_GRATIS_LABEL_AMOUNT"]

        producto = datos["props"]["pageProps"].get("productData")
        if not producto or not producto.get("variants"):
            raise ErrorConector(f"La página del producto {producto_id} no trae datos del producto")
        variante = self._variante_principal(producto)

        return OfertaCapturada(
            titulo=producto["name"],
            url=url_producto(producto_id),
            vendedor=self._vendedor(variante),
            precio=self._precio(variante, producto_id),
            moneda="COP",
            envio=None,
            dias_entrega=None,
            disponible=bool(variante.get("isPurchaseable")) and not producto.get("isOutOfStock", False),
        )

    @staticmethod
    def _datos_de_la_pagina(html: str, producto_id: str) -> dict[str, Any]:
        coincidencia = _NEXT_DATA.search(html)
        if coincidencia is None:
            raise ErrorConector(f"La página del producto {producto_id} cambió: no tiene __NEXT_DATA__")
        try:
            return json.loads(coincidencia.group(1))
        except ValueError as error:
            raise ErrorConector(f"__NEXT_DATA__ del producto {producto_id} no es JSON válido") from error

    @staticmethod
    def _variante_principal(producto: dict[str, Any]) -> dict[str, Any]:
        principal = producto.get("primaryVariantId")
        return next((v for v in producto["variants"] if v.get("id") == principal), producto["variants"][0])

    @staticmethod
    def _vendedor(variante: dict[str, Any]) -> str | None:
        ofertas = variante.get("offerings") or []
        return ofertas[0].get("sellerName") if ofertas else None

    @staticmethod
    def _precio(variante: dict[str, Any], producto_id: str):
        vigentes = []
        for precio in variante.get("prices") or []:
            if precio.get("crossed") or "cmr" in str(precio.get("type", "")).lower():
                continue
            for valor in precio.get("price") or []:
                try:
                    vigentes.append(parsear_precio_cop(valor))
                except ErrorNormalizacion as error:
                    raise ErrorConector(f"Precio no reconocido en el producto {producto_id}: {error}") from error
        if not vigentes:
            raise ErrorConector(f"El producto {producto_id} no tiene un precio vigente")
        return min(vigentes)
