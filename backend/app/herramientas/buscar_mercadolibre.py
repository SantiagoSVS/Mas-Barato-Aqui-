"""Encuentra y verifica productos de Mercado Libre para anotarlos en catalogo.toml.

    python -m app.herramientas.buscar_mercadolibre --id MCO56570140 MCO47798002
    python -m app.herramientas.buscar_mercadolibre "Samsung Galaxy A55"

Forma recomendada (--id): abre el producto en mercadolibre.com.co desde el navegador; si la
dirección tiene /p/MCO12345678, ese es el identificador del catálogo. La herramienta confirma
el nombre y cuántas publicaciones activas tiene: solo sirven los que tienen publicaciones.

La búsqueda por texto usa /products/search, que encuentra pocos productos con vendedores.
"""

import argparse
import sys

from app.config import obtener_configuracion
from app.extraccion.cliente_http import ClienteHttp
from app.extraccion.conector import ErrorConector
from app.extraccion.conectores.mercadolibre import ConectorMercadoLibre, ProductoEncontrado


def imprimir(productos: list[ProductoEncontrado]) -> None:
    print(f"\n{'Identificador':<15} {'Publicaciones':>13}  Nombre")
    for producto in productos:
        print(f"{producto.id:<15} {producto.publicaciones:>13}  {producto.nombre}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("texto", nargs="?", help="búsqueda por texto, por ejemplo una marca y un modelo")
    parser.add_argument("--id", nargs="+", dest="ids", metavar="MCO…", help="verifica estos identificadores")
    parser.add_argument("--limite", type=int, default=20, help="cuántos productos revisar en la búsqueda (máximo 50)")
    parser.add_argument("--todos", action="store_true", help="mostrar también los que no tienen publicaciones")
    argumentos = parser.parse_args()
    if not argumentos.texto and not argumentos.ids:
        parser.error("indica un texto para buscar o --id con uno o más identificadores")

    configuracion = obtener_configuracion()
    if not (configuracion.mercadolibre_client_id and configuracion.mercadolibre_client_secret):
        print("Faltan MERCADOLIBRE_CLIENT_ID y MERCADOLIBRE_CLIENT_SECRET en .env", file=sys.stderr)
        return 1

    cliente = ClienteHttp(
        user_agent=configuracion.extraccion_user_agent,
        # La herramienta la usa una persona: un segundo entre peticiones basta para no saturar la API
        intervalo_minimo_s=1,
        timeout_s=configuracion.extraccion_timeout_s,
    )
    conector = ConectorMercadoLibre(
        cliente,
        client_id=configuracion.mercadolibre_client_id,
        client_secret=configuracion.mercadolibre_client_secret,
        ciudad_destino=configuracion.mercadolibre_ciudad_destino,
        ofertas_por_producto=100,
    )

    try:
        if argumentos.ids:
            imprimir([conector.verificar_producto(producto_id.strip().upper()) for producto_id in argumentos.ids])
            print("\nCopia en ids.mercadolibre de catalogo.toml solo los que tienen publicaciones.")
            return 0

        print(f"Buscando {argumentos.texto!r} en el catálogo de Mercado Libre…")
        productos = conector.buscar_en_catalogo(argumentos.texto, min(argumentos.limite, 50))
    except ErrorConector as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1

    utiles = [p for p in productos if p.publicaciones > 0 or argumentos.todos]
    if not utiles:
        print(f"Ninguno de los {len(productos)} productos encontrados tiene publicaciones activas.")
        print("Prueba con --id usando el identificador /p/MCO… de la página del producto.")
        return 0
    imprimir(utiles)
    print(f"\n{sum(1 for p in productos if p.publicaciones)} de {len(productos)} tienen publicaciones.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
