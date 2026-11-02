"""Pruebas del motor de costo total (sección 7). Los precios son datos de prueba."""

from datetime import UTC, datetime

import pytest

from app.costo.motor import OfertaVigente, calcular, explicar, formato_pesos, ordenar, url_de_compra

MOMENTO = datetime(2026, 11, 2, tzinfo=UTC)


def oferta(oferta_id: int, precio: int, envio: int | None, dias: int | None, plataforma: str = "T", disponible: bool = True) -> OfertaVigente:
    return OfertaVigente(
        oferta_id=oferta_id,
        plataforma=plataforma,
        titulo=f"Producto {oferta_id}",
        url=f"https://t.example/{oferta_id}",
        vendedor=None,
        precio_cop=precio,
        envio_cop=envio,
        dias_entrega=dias,
        disponible=disponible,
        capturado_en=MOMENTO,
    )


# Ejemplo de prueba de la sección 7 del documento de arquitectura
A = oferta(1, 789_000, 0, 5, "Plataforma A")
B = oferta(2, 769_000, 25_000, 2, "Plataforma B")


def test_ejemplo_del_documento_con_w_cero_gana_a() -> None:
    ranking = ordenar([A, B], w=0)

    assert [c.oferta for c in ranking.ordenadas] == [A, B]
    assert [c.costo_total for c in ranking.ordenadas] == [789_000, 794_000]


def test_ejemplo_del_documento_con_w_diez_mil_gana_b() -> None:
    ranking = ordenar([A, B], w=10_000)

    assert ranking.recomendada.oferta == B
    assert [c.costo_ajustado for c in ranking.ordenadas] == [814_000, 839_000]
    assert [c.costo_total for c in ranking.ordenadas] == [794_000, 789_000]  # CT se muestra aparte


def test_es_deterministico_sin_importar_el_orden_de_entrada() -> None:
    ofertas = [oferta(i, 100_000 + (i % 3) * 1_000, 0, 3) for i in range(1, 10)]

    assert ordenar(ofertas, 0) == ordenar(list(reversed(ofertas)), 0)


def test_empate_en_ca_gana_el_menor_ct() -> None:
    # CA igual (110.000), pero X tiene menor CT
    x = oferta(1, 90_000, 0, 2)  # CT 90.000 + 10.000·2 = 110.000
    y = oferta(2, 100_000, 0, 1)  # CT 100.000 + 10.000·1 = 110.000

    assert ordenar([y, x], w=10_000).recomendada.oferta == x


def test_empate_total_gana_la_que_llega_antes_y_luego_el_id() -> None:
    lenta = oferta(1, 100_000, 0, 5)
    rapida = oferta(2, 100_000, 0, 2)
    igual = oferta(3, 100_000, 0, 2)

    assert [c.oferta for c in ordenar([lenta, igual, rapida], w=0).ordenadas] == [rapida, igual, lenta]


def test_envio_desconocido_va_aparte_y_nunca_es_la_recomendada() -> None:
    sin_envio = oferta(1, 50_000, None, None, "Falabella")  # más barata, pero sin envío conocido
    con_envio = oferta(2, 80_000, 5_000, 3, "Mercado Libre")

    ranking = ordenar([sin_envio, con_envio], w=0)

    assert ranking.recomendada.oferta == con_envio
    assert [c.oferta for c in ranking.incompletas] == [sin_envio]
    assert ranking.incompletas[0].costo_total is None


def test_con_w_mayor_que_cero_faltan_los_dias_y_la_oferta_va_aparte() -> None:
    sin_dias = oferta(1, 50_000, 0, None)

    assert ordenar([sin_dias], w=0).recomendada is not None  # con w = 0 los días no importan
    ranking = ordenar([sin_dias], w=10_000)
    assert ranking.recomendada is None
    assert ranking.incompletas[0].costo_total == 50_000
    assert ranking.incompletas[0].costo_ajustado is None


def test_las_ofertas_no_disponibles_se_descartan() -> None:
    ranking = ordenar([oferta(1, 1_000, 0, 1, disponible=False), A], w=0)

    assert [c.oferta for c in ranking.ordenadas] == [A]


def test_aviso_de_presupuesto_usa_el_costo_total() -> None:
    # Precio dentro del presupuesto, pero con envío lo supera (como Alkomprar en el mockup P3)
    calculada = calcular(oferta(1, 789_900, 15_000, 4), w=0, presupuesto_cop=800_000)

    assert calculada.supera_presupuesto


def test_w_negativo_no_es_valido() -> None:
    with pytest.raises(ValueError):
        calcular(A, w=-1)


def test_la_neutralidad_el_nombre_de_la_tienda_no_cambia_el_orden() -> None:
    uno = ordenar([oferta(1, 100, 0, 1, "Tienda Z"), oferta(2, 200, 0, 1, "Tienda A")], 0)
    otro = ordenar([oferta(1, 100, 0, 1, "Tienda A"), oferta(2, 200, 0, 1, "Tienda Z")], 0)

    assert [c.oferta.oferta_id for c in uno.ordenadas] == [c.oferta.oferta_id for c in otro.ordenadas]


def test_explicacion_como_en_el_mockup() -> None:
    assert explicar(ordenar([A, B], w=0)) == "es $5.000 más barata que la siguiente opción al sumar el envío."


def test_explicacion_con_una_sola_opcion_y_sin_opciones() -> None:
    assert explicar(ordenar([A], 0)) == "es la única opción con precio y envío conocidos."
    assert explicar(ordenar([], 0)) is None


def test_explicacion_del_perfil_entrega_rapida() -> None:
    assert explicar(ordenar([A, B], w=10_000)) == (
        "tiene el menor costo ajustado por tiempo de entrega: $25.000 menos que la siguiente opción."
    )


def test_formato_de_pesos() -> None:
    assert formato_pesos(789_000) == "$789.000"
    assert formato_pesos(1_045_000) == "$1.045.000"
    assert formato_pesos(0) == "$0"


def test_la_url_de_compra_es_la_publicacion_original() -> None:
    assert url_de_compra(A) == "https://t.example/1"
