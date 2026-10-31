"""Pruebas unitarias de la normalización (RF-04)."""

from datetime import date
from decimal import Decimal

import pytest

from app.extraccion.normalizacion import (
    ErrorNormalizacion,
    normalizar_oferta,
    normalizar_titulo,
    parsear_precio_cop,
    parsear_precio_usd,
    redondear_a_peso,
)
from app.extraccion.tasa_cambio import TasaCambio
from pruebas.falsos import oferta

TASA = TasaCambio(moneda="USD", valor=Decimal("4000"), fecha=date(2026, 10, 31), fuente="prueba")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("$ 789.900", 789900),
        ("789.900", 789900),
        ("$1.299.900", 1299900),
        ("$1.299.900,50", 1299901),
        ("$ 25.000 ", 25000),
        ("950", 950),
    ],
)
def test_parsear_precio_cop(texto: str, esperado: int) -> None:
    assert parsear_precio_cop(texto) == esperado


@pytest.mark.parametrize("texto", ["", "Gratis", "1,299.90", "78.99"])
def test_parsear_precio_cop_rechaza_formatos_ambiguos(texto: str) -> None:
    with pytest.raises(ErrorNormalizacion):
        parsear_precio_cop(texto)


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [("US$ 1,234.56", Decimal("1234.56")), ("$735.00", Decimal("735.00")), ("735", Decimal("735"))],
)
def test_parsear_precio_usd(texto: str, esperado: Decimal) -> None:
    assert parsear_precio_usd(texto) == esperado


def test_parsear_precio_usd_rechaza_formato_colombiano() -> None:
    with pytest.raises(ErrorNormalizacion):
        parsear_precio_usd("1.299.900")


def test_redondeo_al_peso_mas_cercano() -> None:
    assert redondear_a_peso(Decimal("100.5")) == 101
    assert redondear_a_peso(Decimal("100.49")) == 100


@pytest.mark.parametrize(
    ("titulo", "esperado"),
    [
        ("Samsung  Galaxy A55 128gb", "Samsung Galaxy A55 128 GB"),
        ("Portátil 512GB SSD 16 gb RAM", "Portátil 512 GB SSD 16 GB RAM"),
        ("Disco 1tb", "Disco 1 TB"),
        ("Batería 5000mah", "Batería 5000 mAh"),
    ],
)
def test_normalizar_titulo_unifica_unidades(titulo: str, esperado: str) -> None:
    assert normalizar_titulo(titulo) == esperado


def test_oferta_en_pesos_conserva_valores_y_deja_envio_desconocido() -> None:
    resultado = normalizar_oferta(oferta("https://a.example/1", "789000.4"), tasa=None)

    assert resultado.precio_cop == 789000
    assert resultado.envio_cop is None
    assert resultado.precio_original is None
    assert resultado.tasa_cambio is None


def test_oferta_en_dolares_se_convierte_y_guarda_la_tasa() -> None:
    resultado = normalizar_oferta(
        oferta("https://usd.example/1", "183.75", moneda="USD", envio="15.50", dias=9), TASA
    )

    assert resultado.precio_cop == 735000
    assert resultado.envio_cop == 62000
    assert resultado.precio_original == Decimal("183.75")
    assert resultado.moneda_original == "USD"
    assert resultado.tasa_cambio == Decimal("4000")


def test_oferta_en_dolares_sin_tasa_se_rechaza() -> None:
    with pytest.raises(ErrorNormalizacion):
        normalizar_oferta(oferta("https://usd.example/1", "10", moneda="USD"), tasa=None)
