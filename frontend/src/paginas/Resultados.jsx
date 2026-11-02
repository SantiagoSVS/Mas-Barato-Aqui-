import { useEffect, useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { consultarSalud, ofertasDeProducto } from '../api.js'
import { Aviso, AvisoCosto, Cargando } from '../componentes/Avisos.jsx'
import { Caja, Estrella, Externo, Volver } from '../componentes/Iconos.jsx'
import { PRIORIDADES, dias, envio, fechaCaptura, nombreVendedor, pesos } from '../formato.js'

// P3 · Resultados (RF-06, RF-07, RF-08, RF-11)
export default function Resultados() {
  const { state } = useLocation()
  const navegar = useNavigate()
  const [comparacion, setComparacion] = useState(state?.comparacion)
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const [sinRespuesta, setSinRespuesta] = useState([])

  // RNF-05: tiendas cuya última captura falló; se compara con las demás
  useEffect(() => {
    consultarSalud()
      .then((salud) =>
        setSinRespuesta(
          salud.plataformas.filter((p) => p.activa && p.ultima_ejecucion?.estado === 'fallida').map((p) => p.nombre),
        ),
      )
      .catch(() => setSinRespuesta([]))
  }, [])

  if (!comparacion) return <Navigate to="/" replace />

  const presupuesto = state.criterios?.precio_max_cop

  async function cambiarPrioridad(prioridad) {
    if (prioridad === comparacion.prioridad) return
    setCargando(true)
    setError(null)
    try {
      setComparacion(await ofertasDeProducto(comparacion.producto.id, { prioridad, presupuesto }))
    } catch (e) {
      setError(e.message)
    } finally {
      setCargando(false)
    }
  }

  const { recomendada, alternativas, sin_costo_completo: sinCosto, tiendas } = comparacion
  const enlaceHistorial = `/productos/${comparacion.producto.id}/historial`

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      <div className="barra-titulo">
        <button
          className="boton-volver"
          aria-label="Volver a los criterios"
          onClick={() => (state.texto ? navegar(-1) : navegar('/'))}
        >
          <Volver />
        </button>
        <div className="barra-titulo__textos">
          <h1 className="barra-titulo__titulo" data-cy="producto">
            {comparacion.producto.nombre}
          </h1>
          <span className="barra-titulo__detalle" data-cy="resumen-tiendas">
            {presupuesto ? `Hasta ${pesos(presupuesto)} · ` : ''}
            {tiendas.consultadas.length} tiendas consultadas, {tiendas.con_resultados.length} con resultados
          </span>
        </div>
      </div>

      <div className="selector" role="group" aria-label="Criterio de decisión">
        {Object.entries(PRIORIDADES).map(([valor, nombre]) => (
          <button
            key={valor}
            aria-pressed={comparacion.prioridad === valor}
            onClick={() => cambiarPrioridad(valor)}
            data-cy={`prioridad-${valor}`}
          >
            {nombre}
          </button>
        ))}
      </div>

      {sinRespuesta.map((tienda) => (
        <Aviso key={tienda} titulo={`${tienda} no respondió en la última actualización`} data-cy="tienda-sin-respuesta">
          Comparamos con las demás tiendas. Los precios de {tienda} se mostrarán cuando vuelva a estar disponible.
        </Aviso>
      ))}
      {comparacion.avisos.map((aviso) => (
        <Aviso key={aviso} data-cy="aviso">
          {aviso}
        </Aviso>
      ))}
      {error && <Aviso tipo="error">{error}</Aviso>}

      {cargando ? (
        <Cargando texto="Recalculando…" />
      ) : (
        <>
          {recomendada && (
            <Recomendada
              oferta={recomendada}
              producto={comparacion.producto.nombre}
              explicacion={comparacion.explicacion}
              prioridad={comparacion.prioridad}
              enlaceHistorial={enlaceHistorial}
            />
          )}

          {alternativas.length > 0 && (
            <section className="seccion" aria-labelledby="titulo-alternativas">
              <h2 className="seccion__titulo" id="titulo-alternativas">
                Alternativas, ordenadas por {comparacion.prioridad === 'costo_total' ? 'costo total' : 'costo ajustado'}
              </h2>
              <ListaOfertas ofertas={alternativas} desde={2} prioridad={comparacion.prioridad} />
            </section>
          )}

          {sinCosto.length > 0 && (
            <section className="seccion" aria-labelledby="titulo-sin-costo" data-cy="sin-costo">
              <h2 className="seccion__titulo" id="titulo-sin-costo">
                Con envío por confirmar
              </h2>
              <span className="alternativa__detalle">
                Estas tiendas no informan el envío antes de pagar, así que no las ordenamos con las demás.
              </span>
              {Object.entries(comparacion.notas_envio).map(([tienda, nota]) => (
                <Aviso key={tienda} tipo="info">
                  {nota}
                </Aviso>
              ))}
              <ListaOfertas ofertas={sinCosto} prioridad={comparacion.prioridad} />
            </section>
          )}

          {tiendas.sin_producto.length > 0 && (
            <span className="alternativa__detalle" data-cy="sin-producto">
              {tiendas.sin_producto.join(', ')} {tiendas.sin_producto.length === 1 ? 'no tiene' : 'no tienen'} este
              producto.
            </span>
          )}
        </>
      )}

      <AvisoCosto />
    </div>
  )
}

function Recomendada({ oferta, producto, explicacion, prioridad, enlaceHistorial }) {
  return (
    <section className="recomendada" aria-label="Opción recomendada" data-cy="recomendada">
      <div className="recomendada__franja">
        <Estrella tamano={16} />
        Recomendada · {PRIORIDADES[prioridad].toLowerCase()}
      </div>
      <div className="recomendada__cuerpo">
        <div style={{ display: 'grid', gap: 12 }}>
          <div className="producto">
            <div className="producto__imagen">
              <Caja tamano={28} />
            </div>
            <div className="producto__textos">
              <span className="producto__titulo">{oferta.titulo || producto}</span>
              <span className="producto__tienda" data-cy="tienda-recomendada">
                {oferta.plataforma}
                {nombreVendedor(oferta.vendedor, oferta.plataforma) ? ` · vende ${nombreVendedor(oferta.vendedor, oferta.plataforma)}` : ''}
              </span>
            </div>
          </div>
          <div className="costo-total solo-movil">
            <span className="costo-total__etiqueta">Costo total estimado</span>
            <span className="costo-total__valor">{pesos(oferta.costo_total_cop)}</span>
          </div>
          <div className="desglose">
            <Dato nombre="Precio" valor={pesos(oferta.precio_cop)} />
            <Dato nombre="Envío" valor={envio(oferta.envio_cop)} />
            <Dato nombre="Entrega" valor={dias(oferta.dias_entrega)} />
          </div>
          {prioridad === 'entrega_rapida' && oferta.costo_ajustado_cop !== oferta.costo_total_cop && (
            <span className="fuente">Costo ajustado por tiempo de entrega: {pesos(oferta.costo_ajustado_cop)}</span>
          )}
          {explicacion && (
            <p className="explicacion" data-cy="explicacion">
              <b>Por qué es la recomendada:</b> {explicacion}
            </p>
          )}
          {oferta.supera_presupuesto && (
            <span className="etiqueta-presupuesto">Supera tu presupuesto con envío</span>
          )}
          <span className="fuente">
            Fuente: {oferta.plataforma} · capturado {fechaCaptura(oferta.capturado_en)}
          </span>
        </div>
        <div className="recomendada__acciones">
          <div className="costo-total solo-escritorio">
            <span className="costo-total__etiqueta">Costo total estimado</span>
            <span className="costo-total__valor" data-cy="costo-total">
              {pesos(oferta.costo_total_cop)}
            </span>
          </div>
          <div className="botones-par">
            <Link className="boton boton--secundario" to={enlaceHistorial} data-cy="ver-historial">
              Ver historial
            </Link>
            <a className="boton" href={oferta.url} target="_blank" rel="noopener noreferrer" data-cy="ir-a-tienda">
              Ir a la tienda
              <Externo tamano={16} />
              <span className="solo-lectores">(se abre en una pestaña nueva)</span>
            </a>
          </div>
        </div>
      </div>
    </section>
  )
}

function Dato({ nombre, valor }) {
  return (
    <div className="desglose__dato">
      <span className="desglose__nombre">{nombre}</span>
      <span className="desglose__valor">{valor}</span>
    </div>
  )
}

function ListaOfertas({ ofertas, desde, prioridad }) {
  const costo = (o) => (prioridad === 'entrega_rapida' ? o.costo_ajustado_cop : o.costo_total_cop)
  return (
    <>
      {/* Móvil: lista de tarjetas */}
      <div className="lista-ofertas solo-movil">
        {ofertas.map((o, i) => (
          <a
            key={o.url}
            className="alternativa"
            href={o.url}
            target="_blank"
            rel="noopener noreferrer"
            data-cy="alternativa"
          >
            {desde && <span className="alternativa__posicion">{desde + i}</span>}
            <span className="alternativa__textos">
              <span className="alternativa__tienda">{o.plataforma}</span>
              <span className="alternativa__detalle">
                {pesos(o.precio_cop)} + {o.envio_cop === 0 ? 'envío gratis' : o.envio_cop === null ? 'envío por confirmar' : `${pesos(o.envio_cop)} envío`}
                {o.dias_entrega !== null ? ` · ${dias(o.dias_entrega)}` : ''} · {fechaCaptura(o.capturado_en)}
              </span>
              {o.supera_presupuesto && <span className="etiqueta-presupuesto">Supera tu presupuesto con envío</span>}
            </span>
            <span className="alternativa__costo">{o.costo_total_cop !== null ? pesos(costo(o)) : pesos(o.precio_cop)}</span>
          </a>
        ))}
      </div>

      {/* Escritorio: tabla con desplazamiento horizontal si no cabe */}
      <div className="tabla-contenedor solo-escritorio">
        <table className="tabla">
          <thead>
            <tr>
              {desde && <th scope="col">#</th>}
              <th scope="col">Tienda</th>
              <th scope="col" className="numero">Precio</th>
              <th scope="col" className="numero">Envío</th>
              <th scope="col">Entrega</th>
              <th scope="col" className="numero">Costo total</th>
              <th scope="col">Capturado</th>
              <th scope="col">
                <span className="solo-lectores">Acción</span>
              </th>
            </tr>
          </thead>
          <tbody>
            {ofertas.map((o, i) => (
              <tr key={o.url}>
                {desde && <td>{desde + i}</td>}
                <td>
                  <strong>{o.plataforma}</strong>
                </td>
                <td className="numero">{pesos(o.precio_cop)}</td>
                <td className="numero">{envio(o.envio_cop)}</td>
                <td>{dias(o.dias_entrega)}</td>
                <td className="numero">
                  <strong>{pesos(o.costo_total_cop)}</strong>
                  {o.supera_presupuesto && (
                    <div className="etiqueta-presupuesto">supera tu presupuesto con envío</div>
                  )}
                </td>
                <td>{fechaCaptura(o.capturado_en)}</td>
                <td>
                  <a href={o.url} target="_blank" rel="noopener noreferrer">
                    Ir a la tienda<span className="solo-lectores"> {o.plataforma} (se abre en una pestaña nueva)</span>
                  </a>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  )
}
