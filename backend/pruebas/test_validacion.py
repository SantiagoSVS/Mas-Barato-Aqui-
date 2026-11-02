"""Pruebas del análisis de la Fase 4: SUS (H4), pruebas con usuarios (H1, H5) y auditoría (H3).

Los datos de estas pruebas son inventados para verificar los cálculos; no son resultados.
"""

from datetime import UTC, datetime
from pathlib import Path

import pytest

from app.validacion.estadistica import biserial_de_rangos, comparar_pareadas, rango_intercuartilico
from app.validacion.precios import (
    OfertaAuditable,
    analizar_h3,
    escribir_planilla,
    leer_planilla,
    muestra_estratificada,
)
from app.validacion.sus import intervalo_media, puntaje_sus
from app.validacion.usuarios import COLUMNAS, analizar_h1, analizar_h5, emparejar, leer_registro, leer_sus

# --- SUS (H4) ---


def test_sus_valores_extremos() -> None:
    assert puntaje_sus([5, 1, 5, 1, 5, 1, 5, 1, 5, 1]) == 100  # la mejor respuesta posible
    assert puntaje_sus([1, 5, 1, 5, 1, 5, 1, 5, 1, 5]) == 0
    assert puntaje_sus([3] * 10) == 50  # neutral en todo


def test_sus_ejemplo_calculado_a_mano() -> None:
    # Impares: (4-1)+(5-1)+(4-1)+(3-1)+(4-1) = 15 · Pares: (5-2)+(5-1)+(5-2)+(5-1)+(5-2) = 17
    assert puntaje_sus([4, 2, 5, 1, 4, 2, 3, 1, 4, 2]) == (15 + 17) * 2.5


@pytest.mark.parametrize("respuestas", [[3] * 9, [3] * 11, [0, 3, 3, 3, 3, 3, 3, 3, 3, 3], [6] + [3] * 9])
def test_sus_rechaza_respuestas_invalidas(respuestas: list[int]) -> None:
    with pytest.raises(ValueError):
        puntaje_sus(respuestas)


def test_intervalo_de_la_media_contiene_la_media() -> None:
    bajo, alto = intervalo_media([60, 70, 80])
    assert bajo < 70 < alto
    assert alto - 70 == pytest.approx(70 - bajo)


# --- Estadística ---


def test_rango_intercuartilico_como_excel() -> None:
    assert rango_intercuartilico([1, 2, 3, 4, 5]) == (2, 4)


def test_biserial_de_rangos() -> None:
    assert biserial_de_rangos([-1, -2, -3]) == -1  # todas negativas
    assert biserial_de_rangos([1, 2, 3]) == 1
    # Rangos 1, 2, 3; positiva solo la de rango 1 → (1 − 5) / 6
    assert biserial_de_rangos([1, -2, -3, 0]) == pytest.approx(-4 / 6)


def test_comparacion_con_diferencias_normales_usa_t_pareada() -> None:
    app = [60, 75, 50, 90, 70, 65, 80, 55]
    manual = [200, 195, 210, 220, 220, 210, 205, 190]  # diferencias de −120 a −160
    c = comparar_pareadas(app, manual)
    assert c.prueba == "t pareada"
    assert c.significativa
    assert c.efecto < 0  # la app tarda menos


def test_comparacion_con_diferencias_no_normales_usa_wilcoxon() -> None:
    app = [10, 10, 10, 10, 10, 10, 10, 10, 10, 10]
    manual = [11, 11, 11, 11, 11, 11, 11, 11, 11, 500]  # un valor extremo rompe la normalidad
    c = comparar_pareadas(app, manual)
    assert c.prueba == "Wilcoxon"
    assert c.efecto == -1


def test_comparacion_exige_pares_suficientes_y_diferencias() -> None:
    with pytest.raises(ValueError):
        comparar_pareadas([1, 2], [3, 4])
    with pytest.raises(ValueError):
        comparar_pareadas([1, 2, 3], [1, 2, 3])
    with pytest.raises(ValueError):
        comparar_pareadas([1, 2, 3], [1, 2])


# --- Pruebas con usuarios (H1, H5) ---


def fila(participante: str, tarea: str, condicion: str, tiempo: float, precio: str = "100000",
         envio: str = "0", completada: str = "si") -> dict[str, str]:
    return {"participante": participante, "tarea": tarea, "categoria": "hogar", "condicion": condicion,
            "orden": "app_primero", "tiempo_s": str(tiempo), "completada": completada, "tienda": "Falabella",
            "precio_cop": precio, "envio_cop": envio, "observaciones": ""}


def escribir_csv(ruta: Path, columnas: tuple[str, ...] | list[str], filas: list[dict[str, str]]) -> Path:
    lineas = [",".join(columnas)] + [",".join(f[c] for c in columnas) for f in filas]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta


def test_lee_registro_con_pesos_en_formato_colombiano(tmp_path: Path) -> None:
    ruta = escribir_csv(tmp_path / "r.csv", COLUMNAS, [fila("P01", "T1", "App", 95, "$789.000", "")])
    [r] = leer_registro(ruta)
    assert r.condicion == "app"
    assert r.precio_cop == 789000
    assert r.envio_cop is None  # envío no visible
    assert r.costo_total_cop is None


@pytest.mark.parametrize(
    ("cambio", "mensaje"),
    [({"condicion": "celular"}, "condición"), ({"tiempo_s": "0"}, "mayor que cero"),
     ({"completada": "tal vez"}, "completada"), ({"precio_cop": "barato"}, "precio_cop")],
)
def test_registro_invalido_indica_la_linea(tmp_path: Path, cambio: dict[str, str], mensaje: str) -> None:
    ruta = escribir_csv(tmp_path / "r.csv", COLUMNAS, [{**fila("P01", "T1", "app", 95), **cambio}])
    with pytest.raises(ValueError, match=mensaje):
        leer_registro(ruta)


def test_emparejar_excluye_registros_sin_pareja(tmp_path: Path) -> None:
    filas = [fila("P01", "T1", "app", 60), fila("P01", "T1", "manual", 200), fila("P02", "T1", "app", 70)]
    pares, avisos = emparejar(leer_registro(escribir_csv(tmp_path / "r.csv", COLUMNAS, filas)))
    assert len(pares) == 1
    assert avisos == ["P02 · T1: falta la condición 'manual'; se excluye"]


def test_emparejar_rechaza_duplicados(tmp_path: Path) -> None:
    filas = [fila("P01", "T1", "app", 60), fila("P01", "T1", "app", 61)]
    with pytest.raises(ValueError, match="dos registros"):
        emparejar(leer_registro(escribir_csv(tmp_path / "r.csv", COLUMNAS, filas)))


def pares_de(tmp_path: Path, filas: list[dict[str, str]]):
    pares, _ = emparejar(leer_registro(escribir_csv(tmp_path / "r.csv", COLUMNAS, filas)))
    return pares


def test_h1_usa_la_mediana_de_la_reduccion_por_par(tmp_path: Path) -> None:
    # Reducciones: 1-60/200=0,70 · 1-90/180=0,50 · 1-120/150=0,20 · 1-50/250=0,80 · 1-100/400=0,75
    tiempos = [(60, 200), (90, 180), (120, 150), (50, 250), (100, 400)]
    filas = []
    for i, (app, manual) in enumerate(tiempos, start=1):
        filas += [fila(f"P{i:02}", "T1", "app", app), fila(f"P{i:02}", "T1", "manual", manual)]
    h1 = analizar_h1(pares_de(tmp_path, filas))
    assert h1.pares == 5
    assert h1.mediana_reduccion == pytest.approx(0.70)
    assert h1.tiempos_app["mediana"] == 90


def test_h1_excluye_pares_con_tareas_sin_completar(tmp_path: Path) -> None:
    filas = []
    for i in range(1, 5):
        filas += [fila(f"P{i:02}", "T1", "app", 60 + i), fila(f"P{i:02}", "T1", "manual", 200 + 7 * i)]
    filas += [fila("P05", "T1", "app", 60), fila("P05", "T1", "manual", 900, completada="no")]
    assert analizar_h1(pares_de(tmp_path, filas)).pares == 4


def test_h5_cuenta_empates_a_favor_y_excluye_costos_incompletos(tmp_path: Path) -> None:
    filas = [
        fila("P01", "T1", "app", 60, "100000", "0"), fila("P01", "T1", "manual", 200, "100000", "5000"),  # menor
        fila("P02", "T1", "app", 60, "100000", "0"), fila("P02", "T1", "manual", 200, "100000", "0"),  # igual
        fila("P03", "T1", "app", 60, "120000", "0"), fila("P03", "T1", "manual", 200, "100000", "0"),  # mayor
        fila("P04", "T1", "app", 60, "100000", "0"), fila("P04", "T1", "manual", 200, "90000", ""),  # sin envío
    ]
    h5 = analizar_h5(pares_de(tmp_path, filas))
    assert h5.pares == 3
    assert h5.pares_sin_costo == 1
    assert h5.app_menor_o_igual == 2
    assert not h5.cumple  # 66,7 % < 80 %


def test_lee_respuestas_sus(tmp_path: Path) -> None:
    columnas = ["participante"] + [f"p{i}" for i in range(1, 11)]
    filas = [{"participante": "P01", **{f"p{i}": "3" for i in range(1, 11)}}]
    assert leer_sus(escribir_csv(tmp_path / "s.csv", columnas, filas)) == {"P01": [3] * 10}


# --- Auditoría de precios (H3) ---


def ofertas(plataforma: str, categoria: str, cuantas: int, desde: int) -> list[OfertaAuditable]:
    return [
        OfertaAuditable(desde + i, plataforma, categoria, "Producto", f"https://tienda/{desde + i}",
                        datetime(2026, 11, 2, 12, tzinfo=UTC), 100000, None)
        for i in range(cuantas)
    ]


def test_muestra_estratificada_es_proporcional_reproducible_y_cubre_todos_los_estratos() -> None:
    todas = ofertas("ML", "tecnologia", 60, 0) + ofertas("Falabella", "hogar", 30, 100) + ofertas("Homecenter", "hogar", 2, 200)
    muestra = muestra_estratificada(todas, 20, semilla=1)

    assert len(muestra) == 20
    conteo = {p: sum(1 for o in muestra if o.plataforma == p) for p in ("ML", "Falabella", "Homecenter")}
    assert conteo["Homecenter"] >= 1  # todo estrato queda representado
    assert conteo["ML"] > conteo["Falabella"] > 0
    assert muestra == muestra_estratificada(todas, 20, semilla=1)
    assert len({o.captura_id for o in muestra}) == 20  # sin repetidas


def test_muestra_con_menos_ofertas_que_el_tamano_las_toma_todas() -> None:
    todas = ofertas("ML", "hogar", 5, 0)
    assert muestra_estratificada(todas, 100, semilla=1) == todas


def test_planilla_de_auditoria_y_resultado(tmp_path: Path) -> None:
    muestra = ofertas("ML", "hogar", 4, 0)
    ruta = tmp_path / "auditoria.csv"
    escribir_planilla(ruta, muestra)

    # La persona que audita llena las columnas de verificación
    lineas = ruta.read_text(encoding="utf-8-sig").splitlines()
    verificado = [
        "2026-11-02T13:00,si,$100.000,,",  # precio igual; envío desconocido en los dos
        "2026-11-02T13:00,si,100000,0,",  # precio igual; la página muestra envío gratis
        "2026-11-02T13:00,si,95000,,precio rebajado",
        "2026-11-02T13:00,no,,,publicación pausada",
    ]
    lineas = [lineas[0]] + [linea.removesuffix(",,,,,") + "," + v for linea, v in zip(lineas[1:], verificado, strict=True)]
    ruta.write_text("\n".join(lineas) + "\n", encoding="utf-8")

    r = analizar_h3(leer_planilla(ruta))
    assert r.verificadas == 3
    assert r.no_disponibles == 1
    assert (r.precio.aciertos, r.envio.aciertos, r.precio_y_envio.aciertos) == (2, 2, 1)
    assert not r.cumple


def test_planilla_sin_verificar_avisa(tmp_path: Path) -> None:
    ruta = tmp_path / "auditoria.csv"
    escribir_planilla(ruta, ofertas("ML", "hogar", 1, 0))
    with pytest.raises(ValueError, match="falta verificar"):
        leer_planilla(ruta)
