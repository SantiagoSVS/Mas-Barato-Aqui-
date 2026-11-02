"""Pruebas del proveedor falso (reglas simples). Las respuestas pasan por el mismo esquema
que las del modelo real."""

import pytest

from app.interpretacion.interprete import leer_criterios
from app.interpretacion.proveedor_falso import ProveedorFalso


def interpretar(consulta: str):
    return leer_criterios(ProveedorFalso().completar("", consulta).texto)


def test_ejemplo_del_documento() -> None:
    criterios = interpretar("busco un celular Samsung gama media por menos de 800 mil pesos")

    assert criterios.producto == "celular"
    assert criterios.marca == "Samsung"
    assert criterios.modelo is None
    assert criterios.atributos == {"gama": "media"}
    assert criterios.precio_max_cop == 800000
    assert criterios.prioridad == "costo_total"
    assert not criterios.requiere_aclaracion


@pytest.mark.parametrize(
    ("consulta", "precio"),
    [
        ("celular por menos de 800 mil", 800_000),
        ("portátil máximo 2 millones", 2_000_000),
        ("televisor hasta $1.500.000", 1_500_000),
        ("tenis que no pase de 250k", 250_000),
        ("celular hasta 1'200.000", 1_200_000),
        ("nevera presupuesto de 1,5 millones", 1_500_000),
        ("televisor máximo millón y medio", 1_500_000),
        ("audífonos hasta medio millón", 500_000),
        ("iphone de máximo 4 palos", 4_000_000),
        ("licuadora de menos de 200 lucas", 200_000),
        ("celular samsung", None),
        ("televisor de 55 pulgadas", None),  # 55 no es un precio
    ],
)
def test_precio_maximo(consulta: str, precio: int | None) -> None:
    assert interpretar(consulta).precio_max_cop == precio


@pytest.mark.parametrize(
    "consulta",
    ["freidora que llegue rápido", "celular urgente", "audífonos para mañana", "tablet lo antes posible"],
)
def test_prioridad_entrega_rapida(consulta: str) -> None:
    assert interpretar(consulta).prioridad == "entrega_rapida"


@pytest.mark.parametrize(
    ("consulta", "producto", "marca", "modelo"),
    [
        ("iphone 15 pro", "celular", "Apple", "iPhone 15 Pro"),
        ("samsung galaxy a55", "celular", "Samsung", "Galaxy A55"),
        ("galaxy tab a11 de 128gb", "tablet", None, "Galaxy Tab A11"),
        ("redmi note 13", "celular", "Xiaomi", "Redmi Note 13"),
        ("air fryer oster", "freidora de aire", "Oster", None),
        ("zapatillas nike", "tenis", "Nike", None),
        ("Portátil LENOVO", "portátil", "Lenovo", None),
    ],
)
def test_producto_marca_y_modelo(consulta: str, producto: str, marca: str | None, modelo: str | None) -> None:
    criterios = interpretar(consulta)

    assert (criterios.producto, criterios.marca, criterios.modelo) == (producto, marca, modelo)


def test_atributos() -> None:
    criterios = interpretar("celular de 256gb con 8 gb de ram color azul gama alta")

    assert criterios.atributos == {"almacenamiento": "256 GB", "ram": "8 GB", "color": "azul", "gama": "alta"}


@pytest.mark.parametrize(
    ("consulta", "atributo", "valor"),
    [
        ("freidora de 5 litros", "capacidad", "5 L"),
        ("freidora de 6.3 litros", "capacidad", "6,3 L"),
        ("tenis talla 42", "talla", "42"),
        ("televisor de 55 pulgadas", "pantalla", "55 pulgadas"),
        ("portátil para la universidad", "uso", "universidad"),
        ("audífonos negros", "color", "negro"),
        ("tenis azules", "color", "azul"),
    ],
)
def test_atributo_individual(consulta: str, atributo: str, valor: str) -> None:
    assert interpretar(consulta).atributos[atributo] == valor


def test_sin_producto_pide_aclaracion() -> None:
    criterios = interpretar("algo bueno y barato")

    assert criterios.producto is None
    assert criterios.requiere_aclaracion


def test_no_consume_tokens() -> None:
    respuesta = ProveedorFalso().completar("", "celular")

    assert (respuesta.tokens_entrada, respuesta.tokens_salida) == (0, 0)
