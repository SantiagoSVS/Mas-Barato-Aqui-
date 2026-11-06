"""Búsqueda sobre el catálogo real con los criterios que Claude Haiku 5.5 devolvió de verdad.

Cada caso viene de una consulta real probada el 5 de noviembre de 2026. Cinco de ellas decían
"sin cobertura" estando el producto en el catálogo. Aquí no se llama al modelo: los criterios
quedan escritos. Los precios son datos de prueba.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Configuracion, obtener_configuracion
from app.consultas.busqueda import buscar_productos
from app.consultas.servicio import resolver_consulta
from app.extraccion.catalogo import leer_catalogo
from app.interpretacion.esquema import CriteriosConsulta
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor_falso import ProveedorFalso
from app.modelos import Captura, Oferta, Plataforma, Producto

PUNTAJE_MINIMO = Configuracion(database_url="postgresql+psycopg://x@localhost/x").busqueda_puntaje_minimo


@pytest.fixture
def catalogo(sesion: Session) -> Session:
    for p in leer_catalogo(obtener_configuracion().catalogo_path):
        sesion.add(Producto(nombre_canonico=p.nombre, categoria=p.categoria, marca=p.marca, modelo=p.modelo))
    sesion.flush()
    return sesion


def criterios(producto: str, marca: str | None = None, modelo: str | None = None, **atributos: str) -> CriteriosConsulta:
    return CriteriosConsulta(
        producto=producto, marca=marca, modelo=modelo, atributos=atributos, confianza=0.95, requiere_aclaracion=False
    )


def nombres(sesion: Session, c: CriteriosConsulta) -> list[str]:
    return [e.producto.nombre_canonico for e in buscar_productos(sesion, c, PUNTAJE_MINIMO)]


@pytest.mark.parametrize(
    ("consulta", "c", "esperado"),
    [
        ("audifonos jbl tune 520 baratos", criterios("audífonos", "JBL", "Tune 520", gama="económica"), "Audífonos JBL Tune 520BT"),
        ("consola xbox series s", criterios("consola de videojuegos", "Xbox", "Series S"), "Consola Xbox Series S 512 GB"),
        ("consola ps5", criterios("consola de videojuegos", None, "PS5"), "Consola Sony PlayStation 5 Slim Digital"),
        ("tarjeta de video rtx 4060", criterios("tarjeta de video", "NVIDIA", "RTX 4060"), "Tarjeta gráfica Gigabyte GeForce RTX 4060 8 GB"),
        ("busco un nintendo switch 2", criterios("consola", "Nintendo", "Switch 2"), "Consola Nintendo Switch 2"),
        ("celular samsung galaxy a36", criterios("celular", "Samsung", "Galaxy A36"), "Celular Samsung Galaxy A36 5G 256 GB 8 GB RAM"),
        ("un iphone 16 de 128 gigas", criterios("celular", "Apple", "iPhone 16", almacenamiento="128 GB"), "Celular Apple iPhone 16 128 GB"),
        ("macbook air m4", criterios("portátil", "Apple", "MacBook Air M4"), "Portátil Apple MacBook Air M4 13 pulgadas MW0W3"),
        ("televisor de 55 pulgadas lg", criterios("televisor", "LG", tamano="55 pulgadas"), "Televisor LG 55 pulgadas 4K 55UT8050"),
        ("monitor samsung de 27 pulgadas", criterios("monitor", "samsung", tamano="27 pulgadas"), "Monitor Samsung 27 pulgadas Odyssey G3"),
        ("procesador ryzen 7 5700x", criterios("procesador", "AMD", "Ryzen 7 5700X", serie="Ryzen 7", generacion="5000"), "Procesador AMD Ryzen 7 5700X"),
        ("disco ssd de 1 tb kingston", criterios("disco ssd", "Kingston", capacidad="1 TB"), "SSD Kingston NV3 1 TB NVMe"),
        ("juego de god of war para ps5", criterios("videojuego", None, "God of War", plataforma="PS5"), "Juego God of War Ragnarök PS5"),
        ("airpods baratos", criterios("audífonos inalámbricos", "Apple", gama="económica"), "Audífonos Apple AirPods 4"),
    ],
)
def test_una_consulta_real_encuentra_su_producto_primero(
    catalogo: Session, consulta: str, c: CriteriosConsulta, esperado: str
) -> None:
    assert nombres(catalogo, c)[0] == esperado, consulta


def test_un_atributo_descriptivo_no_descarta_productos(catalogo: Session) -> None:
    encontrados = nombres(catalogo, criterios("portátil", "Lenovo", uso="estudio"))
    assert len(encontrados) == 2
    assert all("Lenovo" in n for n in encontrados)


def test_todas_las_tablets_samsung_del_catalogo_aparecen(catalogo: Session) -> None:
    assert {"Samsung Galaxy Tab A11 128 GB", "Tablet Samsung Galaxy Tab A9+ 128 GB Wi-Fi"} <= set(
        nombres(catalogo, criterios("tablet", "Samsung"))
    )


def test_la_marca_sigue_filtrando_si_el_modelo_no_coincide(catalogo: Session) -> None:
    assert nombres(catalogo, criterios("audífonos", "Bose")) == []
    assert nombres(catalogo, criterios("celular", "Motorola", "Moto G56")) == []
    encontrados = nombres(catalogo, criterios("audífonos", "Sony"))
    assert encontrados and all("Sony" in n for n in encontrados)


def test_un_producto_fuera_del_catalogo_sigue_sin_cobertura(catalogo: Session) -> None:
    assert nombres(catalogo, criterios("nevera")) == []


def capturar(sesion: Session, nombre: str, precio: int) -> None:
    plataforma = sesion.scalar(select(Plataforma).where(Plataforma.nombre == "Mercado Libre"))
    producto = sesion.scalar(select(Producto).where(Producto.nombre_canonico == nombre))
    oferta = Oferta(plataforma=plataforma, producto=producto, titulo_original=nombre, url_origen=f"https://ejemplo/{nombre}")
    sesion.add(oferta)
    sesion.add(
        Captura(
            oferta=oferta, capturado_en=datetime(2026, 11, 5, tzinfo=UTC), precio_cop=precio, envio_cop=0,
            dias_entrega=2, disponible=True,
        )
    )
    sesion.flush()


def consultar_audifonos_sony(sesion: Session, presupuesto: int | None):
    return resolver_consulta(
        sesion,
        Interprete(ProveedorFalso(), 0.5),
        "audífonos Sony",
        None,
        Configuracion(database_url="postgresql+psycopg://x@localhost/x"),
        criterios("audífonos", "Sony").model_copy(update={"precio_max_cop": presupuesto}),
    )


def test_con_presupuesto_muestra_primero_el_producto_que_cabe(catalogo: Session) -> None:
    capturar(catalogo, "Audífonos Sony WH-1000XM5", 900_000)
    capturar(catalogo, "Audífonos Sony WH-CH520", 280_000)

    respuesta = consultar_audifonos_sony(catalogo, 400_000)

    assert respuesta.comparacion.producto.nombre == "Audífonos Sony WH-CH520"
    assert [p.nombre for p in respuesta.otros_productos] == ["Audífonos Sony WH-1000XM5"]


def test_si_ninguno_cabe_o_no_hay_presupuesto_no_cambia_el_orden(catalogo: Session) -> None:
    capturar(catalogo, "Audífonos Sony WH-1000XM5", 900_000)
    capturar(catalogo, "Audífonos Sony WH-CH520", 280_000)

    assert consultar_audifonos_sony(catalogo, None).comparacion.producto.nombre == "Audífonos Sony WH-1000XM5"
    assert consultar_audifonos_sony(catalogo, 100_000).comparacion.producto.nombre == "Audífonos Sony WH-1000XM5"
