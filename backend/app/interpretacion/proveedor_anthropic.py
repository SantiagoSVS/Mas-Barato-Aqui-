"""Proveedor real: Claude, de Anthropic, por su API oficial (SDK `anthropic`).

Decisión del 1 de noviembre de 2026 (sección 4, "decisión pendiente"): Santiago delegó la
elección del proveedor. Se eligió Claude porque tiene SDK oficial de Python, sigue bien
instrucciones de formato JSON en español y deja ajustar el esfuerzo de razonamiento, lo que
controla el costo por consulta.

- Modelo: INTERPRETE_MODELO (por defecto claude-opus-5-5). Se puede cambiar por uno más barato,
  como claude-haiku-5-5, sin tocar el código; conviene comparar ambos con el script de H2.
- Esfuerzo bajo ("low"): extraer criterios es una tarea simple; menos razonamiento = menos
  tokens y respuesta más rápida (RNF-04).
- La clave va en .env (ANTHROPIC_API_KEY), nunca en el código ni en el repositorio.
- La respuesta se devuelve como texto; el Interprete la valida contra el esquema y, si no
  cumple, reintenta una vez. Nunca se ejecuta.
"""

from typing import Any

import anthropic

from app.interpretacion.proveedor import ErrorProveedor, ProveedorModelo, RespuestaModelo

# Respuesta corta (un objeto JSON); el razonamiento también cuenta dentro de este límite
MAX_TOKENS = 4000
ESFUERZO = "low"
# Si el modelo rechaza una consulta por seguridad, la API la reintenta con otro modelo.
# Haiku no tiene este mecanismo.
BETA_FALLBACKS = "server-side-fallback-2026-07-01"


def admite_fallbacks(modelo: str) -> bool:
    return not modelo.startswith("claude-haiku")


class ProveedorAnthropic(ProveedorModelo):
    nombre = "anthropic"

    def __init__(self, api_key: str, modelo: str, timeout_s: float, cliente: Any | None = None) -> None:
        self._modelo = modelo
        # El cliente se puede inyectar en las pruebas, para no llamar a la API real
        self._cliente = cliente or anthropic.Anthropic(api_key=api_key, timeout=timeout_s, max_retries=2)

    def completar(self, instrucciones: str, consulta: str) -> RespuestaModelo:
        parametros: dict[str, Any] = {
            "model": self._modelo,
            "max_tokens": MAX_TOKENS,
            "system": instrucciones,
            "messages": [{"role": "user", "content": consulta}],
            "output_config": {"effort": ESFUERZO},
        }
        if admite_fallbacks(self._modelo):
            parametros["betas"] = [BETA_FALLBACKS]
            parametros["fallbacks"] = "default"

        try:
            respuesta = self._cliente.beta.messages.create(**parametros)
        except anthropic.AuthenticationError as error:
            raise ErrorProveedor("La clave ANTHROPIC_API_KEY no es válida") from error
        except anthropic.RateLimitError as error:
            raise ErrorProveedor("Se superó el límite de uso de la API de Anthropic") from error
        except anthropic.APIStatusError as error:
            raise ErrorProveedor(f"La API de Anthropic respondió {error.status_code}") from error
        except anthropic.APIConnectionError as error:  # incluye el tiempo de espera agotado
            raise ErrorProveedor("No se pudo conectar con la API de Anthropic") from error

        # Un rechazo por seguridad no trae criterios: texto vacío, que el intérprete trata
        # como respuesta inválida y termina pidiendo aclaración
        texto = "" if respuesta.stop_reason == "refusal" else "".join(
            bloque.text for bloque in respuesta.content if bloque.type == "text"
        )
        return RespuestaModelo(
            texto=texto,
            tokens_entrada=respuesta.usage.input_tokens,
            tokens_salida=respuesta.usage.output_tokens,
        )
