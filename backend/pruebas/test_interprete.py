"""Pruebas del intérprete: validación de entrada, validación de salida, reintento y reglas."""

import json

import pytest

from app.config import Configuracion
from app.interpretacion.esquema import CriteriosConsulta
from app.interpretacion.interprete import (
    INSTRUCCIONES,
    LARGO_MAXIMO_CONSULTA,
    ErrorConsulta,
    Interprete,
    leer_criterios,
    limpiar_consulta,
)
from app.interpretacion.proveedor import ErrorProveedor, ProveedorModelo, RespuestaModelo
from app.interpretacion.registro import crear_interprete

VALIDA = {
    "producto": "celular",
    "marca": "Samsung",
    "modelo": None,
    "atributos": {"gama": "media"},
    "precio_max_cop": 800000,
    "prioridad": "costo_total",
    "confianza": 0.9,
    "requiere_aclaracion": False,
}


class ProveedorGuionado(ProveedorModelo):
    """Responde, en orden, los textos que se le den; cuenta tokens fijos por llamada."""

    nombre = "guionado"

    def __init__(self, *respuestas: str) -> None:
        self.respuestas = list(respuestas)
        self.recibido: list[tuple[str, str]] = []

    def completar(self, instrucciones: str, consulta: str) -> RespuestaModelo:
        self.recibido.append((instrucciones, consulta))
        return RespuestaModelo(texto=self.respuestas.pop(0), tokens_entrada=100, tokens_salida=20)


def interprete(*respuestas: str, confianza_minima: float = 0.5) -> tuple[Interprete, ProveedorGuionado]:
    proveedor = ProveedorGuionado(*respuestas)
    return Interprete(proveedor, confianza_minima), proveedor


# --- Entrada ---

def test_limpia_espacios_y_caracteres_de_control() -> None:
    assert limpiar_consulta("  busco\tun   celular\x00\x07 ") == "busco un celular"


@pytest.mark.parametrize("texto", ["", "   ", "\x00\x01"])
def test_rechaza_consultas_vacias(texto: str) -> None:
    with pytest.raises(ErrorConsulta, match="vacía"):
        limpiar_consulta(texto)


def test_rechaza_consultas_largas_sin_llamar_al_modelo() -> None:
    i, proveedor = interprete(json.dumps(VALIDA))

    with pytest.raises(ErrorConsulta, match=str(LARGO_MAXIMO_CONSULTA)):
        i.interpretar("a" * (LARGO_MAXIMO_CONSULTA + 1))
    assert proveedor.recibido == []


def test_envia_la_consulta_limpia_con_las_instrucciones() -> None:
    i, proveedor = interprete(json.dumps(VALIDA))

    i.interpretar("  celular   samsung ")

    assert proveedor.recibido == [(INSTRUCCIONES, "celular samsung")]


# --- Salida del modelo ---

def test_acepta_json_dentro_de_un_bloque_de_codigo() -> None:
    criterios = leer_criterios(f"```json\n{json.dumps(VALIDA)}\n```")

    assert criterios.precio_max_cop == 800000


@pytest.mark.parametrize(
    "respuesta",
    [
        "esto no es JSON",
        json.dumps({**VALIDA, "campo_inventado": 1}),  # campos que no existen
        json.dumps({**VALIDA, "precio_max_cop": -5}),
        json.dumps({**VALIDA, "prioridad": "la que sea"}),
        json.dumps({**VALIDA, "confianza": 3}),
        json.dumps({k: v for k, v in VALIDA.items() if k != "requiere_aclaracion"}),
        "__import__('os').system('dir')",  # la respuesta nunca se ejecuta
    ],
)
def test_rechaza_respuestas_que_no_cumplen_el_esquema(respuesta: str) -> None:
    with pytest.raises(ValueError):
        leer_criterios(respuesta)


def test_respuesta_valida_al_primer_intento() -> None:
    i, _ = interprete(json.dumps(VALIDA))

    resultado = i.interpretar("celular samsung")

    assert resultado.respuesta_valida
    assert resultado.intentos == 1
    assert resultado.criterios == CriteriosConsulta(**VALIDA)
    assert (resultado.tokens_entrada, resultado.tokens_salida) == (100, 20)


def test_reintenta_una_vez_si_la_respuesta_no_cumple() -> None:
    i, proveedor = interprete("no es JSON", json.dumps(VALIDA))

    resultado = i.interpretar("celular samsung")

    assert resultado.respuesta_valida
    assert resultado.intentos == 2
    assert len(proveedor.recibido) == 2
    assert (resultado.tokens_entrada, resultado.tokens_salida) == (200, 40)  # se cuentan ambos intentos


def test_si_falla_dos_veces_pide_aclaracion() -> None:
    i, proveedor = interprete("no es JSON", "tampoco")

    resultado = i.interpretar("celular samsung")

    assert not resultado.respuesta_valida
    assert resultado.criterios.requiere_aclaracion
    assert resultado.criterios.producto is None
    assert len(proveedor.recibido) == 2  # no hay un tercer intento


def test_los_errores_del_proveedor_no_se_ocultan() -> None:
    class ProveedorCaido(ProveedorModelo):
        nombre = "caido"

        def completar(self, instrucciones: str, consulta: str) -> RespuestaModelo:
            raise ErrorProveedor("sin conexión")

    with pytest.raises(ErrorProveedor):
        Interprete(ProveedorCaido(), 0.5).interpretar("celular")


# --- Reglas propias ---

def test_sin_producto_siempre_pide_aclaracion_aunque_el_modelo_diga_que_no() -> None:
    i, _ = interprete(json.dumps({**VALIDA, "producto": None, "requiere_aclaracion": False}))

    assert i.interpretar("algo samsung").criterios.requiere_aclaracion


def test_confianza_baja_pide_aclaracion() -> None:
    i, _ = interprete(json.dumps({**VALIDA, "confianza": 0.3}), confianza_minima=0.5)

    assert i.interpretar("celular").criterios.requiere_aclaracion


def test_confianza_suficiente_no_pide_aclaracion() -> None:
    i, _ = interprete(json.dumps({**VALIDA, "confianza": 0.5}), confianza_minima=0.5)

    assert not i.interpretar("celular").criterios.requiere_aclaracion


# --- Configuración ---

def test_crea_el_interprete_con_el_proveedor_configurado() -> None:
    configuracion = Configuracion(database_url="postgresql+psycopg://x@localhost/x", interprete_proveedor="falso")

    resultado = crear_interprete(configuracion).interpretar("celular samsung")

    assert resultado.proveedor == "falso"


def test_proveedor_desconocido_da_un_error_claro() -> None:
    configuracion = Configuracion(database_url="postgresql+psycopg://x@localhost/x", interprete_proveedor="otro")

    with pytest.raises(ValueError, match="Disponibles: anthropic, falso"):
        crear_interprete(configuracion)
