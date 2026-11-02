"""Pruebas de las reglas de evaluación de H2 y del script de evaluación."""

import json
from pathlib import Path

import pytest

from app.herramientas.evaluar_interprete import evaluar, leer_anotaciones
from app.interpretacion.esquema import CriteriosConsulta
from app.interpretacion.evaluacion import campos_distintos, intervalo_wilson

EJEMPLO = Path(__file__).parents[1] / "evaluacion" / "consultas_ejemplo.json"


def criterios(**campos) -> CriteriosConsulta:
    return CriteriosConsulta(**{"confianza": 1, "requiere_aclaracion": False, **campos})


def test_ignora_mayusculas_tildes_y_espacios() -> None:
    obtenido = criterios(producto="Portatil", marca="LENOVO", atributos={"Almacenamiento": "512gb"})
    esperado = criterios(producto="portátil", marca="Lenovo", atributos={"almacenamiento": "512 GB"})

    assert campos_distintos(obtenido, esperado) == []


def test_atributos_de_mas_o_de_menos_cuentan_como_error() -> None:
    esperado = criterios(producto="tenis", atributos={"talla": "42"})

    assert campos_distintos(criterios(producto="tenis", atributos={"talla": "42", "color": "negro"}), esperado) == ["atributos"]
    assert campos_distintos(criterios(producto="tenis"), esperado) == ["atributos"]


def test_reporta_cada_campo_distinto() -> None:
    obtenido = criterios(producto="celular", precio_max_cop=800000, prioridad="entrega_rapida")
    esperado = criterios(producto="tablet", precio_max_cop=900000)

    assert campos_distintos(obtenido, esperado) == ["producto", "precio_max_cop", "prioridad"]


def test_la_confianza_no_se_evalua() -> None:
    assert campos_distintos(criterios(producto="tv", confianza=0.1), criterios(producto="tv", confianza=0.9)) == []


def test_intervalo_de_wilson() -> None:
    bajo, alto = intervalo_wilson(40, 50)

    assert bajo == pytest.approx(0.670, abs=0.001)
    assert alto == pytest.approx(0.888, abs=0.001)
    assert intervalo_wilson(0, 0) == (0.0, 0.0)


def test_el_archivo_de_ejemplo_se_lee_y_se_evalua() -> None:
    reporte = evaluar(leer_anotaciones(EJEMPLO))

    assert reporte.total == 5
    assert reporte.correctas == reporte.total


def test_rechaza_identificadores_repetidos(tmp_path: Path) -> None:
    archivo = tmp_path / "anotadas.json"
    consulta = {"id": "A", "consulta": "celular", "esperado": {"producto": "celular", "requiere_aclaracion": False}}
    archivo.write_text(json.dumps({"consultas": [consulta, consulta]}), encoding="utf-8")

    with pytest.raises(ValueError, match="repetidos"):
        leer_anotaciones(archivo)


def test_rechaza_anotaciones_que_no_cumplen_el_esquema(tmp_path: Path) -> None:
    archivo = tmp_path / "anotadas.json"
    consulta = {"id": "A", "consulta": "celular", "esperado": {"producto": "celular", "prioridad": "urgente", "requiere_aclaracion": False}}
    archivo.write_text(json.dumps({"consultas": [consulta]}), encoding="utf-8")

    with pytest.raises(ValueError):
        leer_anotaciones(archivo)
