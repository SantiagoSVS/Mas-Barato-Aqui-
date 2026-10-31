// Cliente de la API. La interfaz solo habla con la API, nunca con las tiendas.
const URL_BASE = '/api'

export async function consultarSalud() {
  const respuesta = await fetch(`${URL_BASE}/salud`)
  // 503 también trae un cuerpo útil (estado "degradado"), por eso no se descarta
  if (!respuesta.ok && respuesta.status !== 503) {
    throw new Error(`La API respondió ${respuesta.status}`)
  }
  return respuesta.json()
}
