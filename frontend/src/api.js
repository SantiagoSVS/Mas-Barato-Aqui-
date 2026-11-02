// Cliente de la API. La interfaz solo habla con la API, nunca con las tiendas.
const URL_BASE = '/api'

export class ErrorApi extends Error {
  constructor(mensaje, estado) {
    super(mensaje)
    this.estado = estado
  }
}

async function pedir(ruta, opciones = {}) {
  let respuesta
  try {
    respuesta = await fetch(`${URL_BASE}${ruta}`, {
      headers: { 'Content-Type': 'application/json' },
      ...opciones,
    })
  } catch {
    throw new ErrorApi('No pudimos conectarnos. Revisa tu conexión e intenta de nuevo.', 0)
  }
  const cuerpo = await respuesta.json().catch(() => null)
  if (!respuesta.ok) {
    const detalle = typeof cuerpo?.detail === 'string' ? cuerpo.detail : null
    throw new ErrorApi(detalle ?? 'Algo salió mal. Intenta de nuevo en un momento.', respuesta.status)
  }
  return cuerpo
}

export function consultar(texto, { prioridad, criterios } = {}) {
  return pedir('/consultas', {
    method: 'POST',
    body: JSON.stringify({ texto, prioridad: prioridad ?? null, criterios: criterios ?? null }),
  })
}

export function ofertasDeProducto(id, { prioridad = 'costo_total', presupuesto } = {}) {
  const parametros = new URLSearchParams({ prioridad })
  if (presupuesto) parametros.set('presupuesto_cop', presupuesto)
  return pedir(`/productos/${id}/ofertas?${parametros}`)
}

export function historialDeProducto(id, periodo = '3M') {
  return pedir(`/productos/${id}/historial?periodo=${periodo}`)
}

export function listarProductos() {
  return pedir('/productos')
}

export function consultarSalud() {
  return pedir('/salud')
}
