// Formatos en español de Colombia (CLAUDE.md: precios como $789.000)

export function pesos(valor) {
  if (valor === null || valor === undefined) return '—'
  return '$' + Math.round(valor).toLocaleString('es-CO')
}

export function envio(valor) {
  if (valor === null || valor === undefined) return 'Por confirmar'
  return valor === 0 ? 'Gratis' : pesos(valor)
}

export function dias(valor) {
  if (valor === null || valor === undefined) return 'Por confirmar'
  return valor === 1 ? '1 día' : `${valor} días`
}

const FECHA_CAPTURA = new Intl.DateTimeFormat('es-CO', {
  day: 'numeric',
  month: 'short',
  hour: 'numeric',
  minute: '2-digit',
  timeZone: 'America/Bogota',
})

// "31 oct, 5:30 a. m." (como en los mockups)
export function fechaCaptura(iso) {
  return FECHA_CAPTURA.format(new Date(iso)).replace(' de ', ' ').replace('.,', ',')
}

const FECHA_CORTA = new Intl.DateTimeFormat('es-CO', { day: 'numeric', month: 'short', timeZone: 'UTC' })

// "1 nov" para fechas sin hora (AAAA-MM-DD)
export function fechaCorta(isoFecha) {
  return FECHA_CORTA.format(new Date(`${isoFecha}T00:00:00Z`)).replace(' de ', ' ').replace('.', '')
}

export const PRIORIDADES = {
  costo_total: 'Menor costo total',
  entrega_rapida: 'Entrega más rápida',
}

// Mercado Libre solo entrega el número del vendedor: no se muestra porque no le dice nada al usuario
export function nombreVendedor(vendedor, plataforma) {
  if (!vendedor || /^\d+$/.test(vendedor)) return null
  if (vendedor.toLowerCase() === plataforma.toLowerCase()) return null
  return vendedor
}

export function capitalizar(texto) {
  return texto ? texto.charAt(0).toUpperCase() + texto.slice(1) : texto
}
