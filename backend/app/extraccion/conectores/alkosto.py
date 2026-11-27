"""Conector de Alkosto (extracción de la página de producto).

Alkosto no tiene API pública de productos, así que se lee la página de cada producto del
catálogo (ids.alkosto = ["711719574293"], el código de la dirección /p/711719574293, que es el
código de barras del producto). La página trae sus datos con el vocabulario de schema.org
(microdatos itemprop): nombre, precio, disponibilidad y envío.

robots.txt: permite las páginas de producto y prohíbe la búsqueda (*?q=, /search/), el carrito
y el checkout, por eso este conector nunca busca por texto. El ClienteHttp lo verifica en cada
petición.

Envío y días de entrega: a diferencia de Falabella y Homecenter, Alkosto publica en cada página
el envío a domicilio antes del pago (OfferShippingDetails: costo, días de alistamiento y de
tránsito). Se toma la opción de envío a domicilio, no la de recoger en tienda. El dato vale para
todo el país (no se cotiza a una ciudad), lo que se debe contrastar en la auditoría H3. Si la
página no trae la opción de envío, queda desconocido, como en las otras dos tiendas.

Reemplaza a Mercado Libre desde el 27 de noviembre de 2026: su API dejó de entregar los precios
de las publicaciones a aplicaciones de terceros.
"""

import html
import re
from decimal import Decimal, InvalidOperation

from app.extraccion.cliente_http import ClienteHttp, ErrorHttp
from app.extraccion.conector import Conector, ErrorConector
from app.extraccion.tipos import OfertaCapturada, ProductoCatalogo

URL_BASE = "https://www.alkosto.com"

_PRODUCTO = re.compile(r'itemtype="https://schema.org/Product"(.*)', re.S)
_OFERTA = re.compile(r'itemprop="offers".*?itemtype="https://schema.org/Offer"(.*?)(?:itemprop="hasMerchantReturnPolicy"|<h1)', re.S)
_NOMBRE = re.compile(r'<h1[^>]*itemprop="name"[^>]*>(.*?)</h1>', re.S)
_CODIGO = re.compile(r'itemprop="sku"[^>]*>\s*([^<\s]+)\s*<')
_PRECIO = re.compile(r'itemprop="price" content="([^"]+)"')
_MONEDA = re.compile(r'itemprop="priceCurrency" content="([^"]+)"')
_DISPONIBILIDAD = re.compile(r'itemprop="availability" href="https://schema.org/(\w+)"')
_VENDEDOR = re.compile(r'itemprop="seller".*?itemprop="name" content="([^"]+)"', re.S)
_ENVIO = re.compile(r'itemprop="shippingDetails"(.*?)(?=itemprop="shippingDetails"|$)', re.S)
_VALOR_ENVIO = re.compile(r'itemprop="shippingRate".*?itemprop="value" content="([^"]+)"', re.S)
_NOMBRE_ENVIO = re.compile(r'<meta itemprop="name" content="([^"]+)"')
_DIAS = re.compile(r'itemprop="(handlingTime|transitTime)".*?itemprop="maxValue" content="(\d+)"', re.S)


def url_producto(codigo: str) -> str:
    # Alkosto redirige /p/<código> a la dirección completa con el nombre del producto
    return f"{URL_BASE}/p/{codigo}"


class ConectorAlkosto(Conector):
    nombre_plataforma = "Alkosto"
    clave_catalogo = "alkosto"

    def __init__(self, cliente: ClienteHttp) -> None:
        self._cliente = cliente

    def buscar(self, producto: ProductoCatalogo) -> list[OfertaCapturada]:
        ofertas = []
        for codigo in producto.ids.get(self.clave_catalogo, []):
            oferta = self._leer_producto(codigo)
            if oferta is not None:
                ofertas.append(oferta)
        return ofertas

    def actualizar(self, url: str) -> OfertaCapturada | None:
        coincidencia = re.search(r"/p/(\d+)", url)
        if coincidencia is None:
            raise ErrorConector(f"No es una dirección de producto de Alkosto: {url}")
        return self._leer_producto(coincidencia.group(1))

    def _leer_producto(self, codigo: str) -> OfertaCapturada | None:
        try:
            respuesta = self._cliente.get(url_producto(codigo))
        except ErrorHttp as error:
            if error.status_code == 404:  # el producto ya no existe
                return None
            raise

        producto = _PRODUCTO.search(respuesta.text)
        oferta = _OFERTA.search(respuesta.text)
        if producto is None or oferta is None:
            raise ErrorConector(f"La página del producto {codigo} cambió: no trae los datos del producto")
        texto_producto, texto_oferta = producto.group(1), oferta.group(1)

        # Ante la duda, omitir: si la página corresponde a otro código, no se mezcla
        codigo_pagina = _CODIGO.search(texto_producto)
        if codigo_pagina is None or codigo_pagina.group(1) != codigo:
            raise ErrorConector(f"La página del producto {codigo} muestra otro producto")

        nombre = _NOMBRE.search(texto_producto)
        if nombre is None:
            raise ErrorConector(f"La página del producto {codigo} no trae el nombre")
        moneda = _MONEDA.search(texto_oferta)
        if moneda is None or moneda.group(1) != "COP":
            raise ErrorConector(f"El producto {codigo} no tiene un precio en pesos")
        envio, dias = self._envio(texto_oferta)
        disponibilidad = _DISPONIBILIDAD.search(texto_oferta)
        vendedor = _VENDEDOR.search(texto_oferta)

        return OfertaCapturada(
            titulo=html.unescape(re.sub(r"\s+", " ", nombre.group(1))).strip(),
            url=url_producto(codigo),
            vendedor=html.unescape(vendedor.group(1)) if vendedor else "Alkosto",
            precio=self._decimal(_PRECIO.search(texto_oferta), codigo, "precio"),
            moneda="COP",
            envio=envio,
            dias_entrega=dias,
            disponible=bool(disponibilidad) and disponibilidad.group(1) == "InStock",
        )

    def _envio(self, texto_oferta: str) -> tuple[Decimal | None, int | None]:
        """Costo y días del envío a domicilio (alistamiento + tránsito, el máximo publicado)."""
        for bloque in _ENVIO.findall(texto_oferta):
            nombre = _NOMBRE_ENVIO.search(bloque)
            if nombre is None or "recoge" in nombre.group(1).lower():
                continue  # recoger en tienda no es un envío
            valor = _VALOR_ENVIO.search(bloque)
            if valor is None:
                continue
            dias = {tipo: int(maximo) for tipo, maximo in _DIAS.findall(bloque)}
            total_dias = sum(dias.values()) if "transitTime" in dias else None
            return self._decimal(valor, "envío", "envío"), total_dias
        return None, None

    @staticmethod
    def _decimal(coincidencia: re.Match[str] | None, codigo: str, campo: str) -> Decimal:
        if coincidencia is None:
            raise ErrorConector(f"El producto {codigo} no trae {campo}")
        try:
            return Decimal(coincidencia.group(1))
        except InvalidOperation as error:
            raise ErrorConector(f"{campo} no reconocido en el producto {codigo}: {coincidencia.group(1)}") from error
