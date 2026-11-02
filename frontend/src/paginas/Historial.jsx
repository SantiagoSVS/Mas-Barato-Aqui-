import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { historialDeProducto, ofertasDeProducto } from '../api.js'
import { Aviso, Cargando } from '../componentes/Avisos.jsx'
import { Bajada, Externo, Volver } from '../componentes/Iconos.jsx'
import { fechaCaptura, fechaCorta, pesos } from '../formato.js'

const PERIODOS = { '1M': '1 mes', '3M': '3 meses', '6M': '6 meses' }
// Las líneas se distinguen por color y por estilo de trazo, no solo por color (accesibilidad)
const ESTILOS = [
  { color: '#2563EB', trazo: undefined },
  { color: '#F59E0B', trazo: '7 4' },
  { color: '#0B2D6B', trazo: '2 3' },
  { color: '#4B5B7A', trazo: '10 3 2 3' },
]

// P4 · Historial del producto (RF-09, RF-10)
export default function Historial() {
  const { id } = useParams()
  const navegar = useNavigate()
  const [periodo, setPeriodo] = useState('3M')
  const [historial, setHistorial] = useState(null)
  const [urlRecomendada, setUrlRecomendada] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setError(null)
    historialDeProducto(id, periodo)
      .then(setHistorial)
      .catch((e) => setError(e.message))
  }, [id, periodo])

  useEffect(() => {
    ofertasDeProducto(id)
      .then((c) => setUrlRecomendada(c.recomendada?.url ?? null))
      .catch(() => setUrlRecomendada(null))
  }, [id])

  if (error) return <Aviso tipo="error" titulo="No pudimos cargar el historial">{error}</Aviso>
  if (!historial) return <Cargando texto="Cargando el historial…" />

  const { indicador, series, resumen } = historial
  const plazo =
    historial.datos_desde && historial.datos_desde > historial.desde
      ? `desde el ${fechaCorta(historial.datos_desde)}`
      : PERIODOS[periodo]
  const datos = unirSeries(series)

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="barra-titulo">
        <button className="boton-volver" aria-label="Volver a resultados" onClick={() => navegar(-1)}>
          <Volver />
        </button>
        <div className="barra-titulo__textos">
          <h1 className="barra-titulo__titulo">Historial de precios</h1>
          <span className="barra-titulo__detalle" data-cy="producto-historial">
            {historial.producto}
          </span>
        </div>
      </div>

      {indicador && (
        <Aviso
          tipo={indicador.cerca_del_minimo ? 'exito' : 'advertencia'}
          titulo={indicador.cerca_del_minimo ? 'Cerca de su mínimo histórico' : 'Por encima de su mínimo histórico'}
          data-cy="indicador"
        >
          {indicador.mensaje}
        </Aviso>
      )}

      <section className="tarjeta grafico" aria-label="Gráfico de precios por tienda">
        <div className="selector" role="group" aria-label="Periodo">
          {Object.keys(PERIODOS).map((p) => (
            <button key={p} aria-pressed={periodo === p} onClick={() => setPeriodo(p)} data-cy={`periodo-${p}`}>
              {p}
            </button>
          ))}
        </div>

        {datos.length === 0 ? (
          <p className="texto-secundario">Aún no hay capturas de este producto en el periodo.</p>
        ) : (
          <div className="grafico__lienzo" data-cy="grafico">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={datos} margin={{ top: 10, right: 12, bottom: 0, left: 0 }}>
                <CartesianGrid stroke="#EEF1F6" vertical={false} />
                <XAxis dataKey="fecha" tickFormatter={fechaCorta} tick={{ fontSize: 12, fill: '#4B5B7A' }} />
                <YAxis
                  width={70}
                  tickFormatter={(v) => `$${Math.round(v / 1000)}k`}
                  tick={{ fontSize: 12, fill: '#4B5B7A' }}
                  domain={['auto', 'auto']}
                />
                <Tooltip formatter={(v) => pesos(v)} labelFormatter={fechaCorta} />
                {series.map((s, i) => (
                  <Line
                    key={s.plataforma}
                    type="monotone"
                    dataKey={s.plataforma}
                    stroke={ESTILOS[i % ESTILOS.length].color}
                    strokeDasharray={ESTILOS[i % ESTILOS.length].trazo}
                    strokeWidth={2.5}
                    dot={{ r: 3 }}
                    connectNulls
                    isAnimationActive={false}
                  />
                ))}
                {indicador && (
                  <ReferenceLine
                    y={indicador.minimo_periodo_cop}
                    stroke="#15803D"
                    strokeDasharray="4 4"
                    label={{
                      value: `mín. ${indicador.plataforma} ${pesos(indicador.minimo_periodo_cop)}`,
                      position: 'insideBottomRight',
                      fill: '#15803D',
                      fontSize: 11,
                    }}
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        <div className="leyenda" aria-hidden="true">
          {series.map((s, i) => (
            <span key={s.plataforma} className="leyenda__item">
              <span
                className="leyenda__linea"
                style={{
                  borderTopColor: ESTILOS[i % ESTILOS.length].color,
                  borderTopStyle: ESTILOS[i % ESTILOS.length].trazo ? 'dashed' : 'solid',
                }}
              />
              {s.plataforma}
            </span>
          ))}
        </div>
      </section>

      <section className="tarjeta criterios resumen-historial" aria-label="Resumen por tienda" data-cy="resumen-historial">
        <div className="criterio">
          <span className="criterio__nombre">Tienda · precio actual</span>
          <span className="criterio__nombre" style={{ textAlign: 'right' }}>
            Mínimo {plazo}
          </span>
        </div>
        {resumen.map((r) => (
          <div className="criterio" key={r.plataforma}>
            <span className="criterio__valor">
              {r.plataforma} <span className="texto-secundario">{pesos(r.precio_actual_cop)}</span>
            </span>
            <span className="criterio__valor" style={{ textAlign: 'right', flex: 'none' }}>
              {pesos(r.minimo_periodo_cop)}
              {r.en_su_minimo ? ' · mínimo' : ''}
            </span>
          </div>
        ))}
      </section>

      <p className="nota" style={{ margin: 0 }}>
        {historial.nota}
        {historial.ultima_captura ? ` Última captura: ${fechaCaptura(historial.ultima_captura)}` : ''}
      </p>

      {urlRecomendada && (
        <a className="boton boton--ancho" href={urlRecomendada} target="_blank" rel="noopener noreferrer">
          <Bajada tamano={18} />
          Ir a la tienda recomendada
          <Externo tamano={16} />
          <span className="solo-lectores">(se abre en una pestaña nueva)</span>
        </a>
      )}
    </div>
  )
}

// [{plataforma, puntos:[{fecha, precio}]}] -> [{fecha, "Mercado Libre": 224175, ...}]
function unirSeries(series) {
  const porFecha = new Map()
  for (const serie of series) {
    for (const punto of serie.puntos) {
      const fila = porFecha.get(punto.fecha) ?? { fecha: punto.fecha }
      fila[serie.plataforma] = punto.precio_min_cop
      porFecha.set(punto.fecha, fila)
    }
  }
  return [...porFecha.values()].sort((a, b) => a.fecha.localeCompare(b.fecha))
}
