"""Pruebas del proveedor de Anthropic con un cliente simulado: no llaman a la API real ni
gastan tokens."""

import json
from types import SimpleNamespace

import anthropic
import httpx2
import pytest

from app.config import Configuracion
from app.interpretacion.interprete import Interprete
from app.interpretacion.proveedor import ErrorProveedor
from app.interpretacion.proveedor_anthropic import BETA_FALLBACKS, ProveedorAnthropic
from app.interpretacion.registro import crear_interprete

CRITERIOS = {
    "producto": "celular",
    "marca": "Samsung",
    "modelo": None,
    "atributos": {"gama": "media"},
    "precio_max_cop": 800000,
    "prioridad": "costo_total",
    "confianza": 0.95,
    "requiere_aclaracion": False,
}
PETICION = httpx2.Request("POST", "https://api.anthropic.com/v1/messages")


def respuesta(texto: str, stop_reason: str = "end_turn") -> SimpleNamespace:
    return SimpleNamespace(
        stop_reason=stop_reason,
        content=[SimpleNamespace(type="thinking", thinking=""), SimpleNamespace(type="text", text=texto)],
        usage=SimpleNamespace(input_tokens=850, output_tokens=60),
    )


class ClienteSimulado:
    """Imita client.beta.messages.create y guarda los parámetros de cada llamada."""

    def __init__(self, resultado) -> None:
        self.resultado = resultado
        self.llamadas: list[dict] = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **parametros):
        self.llamadas.append(parametros)
        if isinstance(self.resultado, Exception):
            raise self.resultado
        return self.resultado


def proveedor(resultado, modelo: str = "claude-opus-5-5") -> tuple[ProveedorAnthropic, ClienteSimulado]:
    cliente = ClienteSimulado(resultado)
    return ProveedorAnthropic(api_key="clave-de-prueba", modelo=modelo, timeout_s=5, cliente=cliente), cliente


def test_envia_instrucciones_consulta_modelo_y_esfuerzo_bajo() -> None:
    p, cliente = proveedor(respuesta(json.dumps(CRITERIOS)))

    p.completar("INSTRUCCIONES", "celular samsung")

    [llamada] = cliente.llamadas
    assert llamada["model"] == "claude-opus-5-5"
    assert llamada["system"] == "INSTRUCCIONES"
    assert llamada["messages"] == [{"role": "user", "content": "celular samsung"}]
    assert llamada["output_config"] == {"effort": "low"}
    assert llamada["fallbacks"] == "default"
    assert llamada["betas"] == [BETA_FALLBACKS]


def test_haiku_no_usa_fallbacks() -> None:
    p, cliente = proveedor(respuesta("{}"), modelo="claude-haiku-5-5")

    p.completar("I", "celular")

    assert "fallbacks" not in cliente.llamadas[0]
    assert "betas" not in cliente.llamadas[0]


def test_devuelve_el_texto_y_los_tokens() -> None:
    p, _ = proveedor(respuesta(json.dumps(CRITERIOS)))

    resultado = p.completar("I", "celular samsung")

    assert json.loads(resultado.texto) == CRITERIOS
    assert (resultado.tokens_entrada, resultado.tokens_salida) == (850, 60)


def test_un_rechazo_por_seguridad_termina_en_aclaracion() -> None:
    p, cliente = proveedor(respuesta("", stop_reason="refusal"))

    resultado = Interprete(p, 0.5).interpretar("celular")

    assert not resultado.respuesta_valida
    assert resultado.criterios.requiere_aclaracion
    assert len(cliente.llamadas) == 2  # el intento y un reintento


def test_integrado_con_el_interprete() -> None:
    p, _ = proveedor(respuesta(json.dumps(CRITERIOS)))

    resultado = Interprete(p, 0.5).interpretar("busco un celular Samsung gama media por menos de 800 mil")

    assert resultado.proveedor == "anthropic"
    assert resultado.criterios.precio_max_cop == 800000
    assert resultado.tokens_entrada == 850


@pytest.mark.parametrize(
    ("error", "mensaje"),
    [
        (anthropic.AuthenticationError("x", response=httpx2.Response(401, request=PETICION), body=None), "no es válida"),
        (anthropic.RateLimitError("x", response=httpx2.Response(429, request=PETICION), body=None), "límite de uso"),
        (anthropic.InternalServerError("x", response=httpx2.Response(500, request=PETICION), body=None), "respondió 500"),
        (anthropic.APIConnectionError(request=PETICION), "No se pudo conectar"),
        (anthropic.APITimeoutError(request=PETICION), "No se pudo conectar"),
    ],
)
def test_los_errores_de_la_api_se_convierten_en_error_de_proveedor(error: Exception, mensaje: str) -> None:
    p, _ = proveedor(error)

    with pytest.raises(ErrorProveedor, match=mensaje):
        p.completar("I", "celular")


def test_sin_clave_da_un_error_claro() -> None:
    configuracion = Configuracion(
        database_url="postgresql+psycopg://x@localhost/x", interprete_proveedor="anthropic", anthropic_api_key=None
    )

    with pytest.raises(ValueError, match="ANTHROPIC_API_KEY"):
        crear_interprete(configuracion)


def test_la_clave_no_aparece_en_la_configuracion_impresa() -> None:
    configuracion = Configuracion(database_url="postgresql+psycopg://x@localhost/x", anthropic_api_key="sk-secreta")

    assert "sk-secreta" not in repr(configuracion)
