import { useEffect, useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { consultar, listarProductos, ofertasDeProducto } from '../api.js'
import { Aviso, Cargando } from '../componentes/Avisos.jsx'
import { Comillas, Lapiz, Volver } from '../componentes/Iconos.jsx'
import { PRIORIDADES, capitalizar, pesos } from '../formato.js'

// P2 · Interpretación y aclaración (RF-02)
export default function Interpretacion() {
  const { state } = useLocation()
  const navegar = useNavigate()
  const [criterios, setCriterios] = useState(state?.respuesta.criterios)
  const [editando, setEditando] = useState(null)
  const [editados, setEditados] = useState(false)
  const [elegido, setElegido] = useState(null) // producto elegido entre varios parecidos
  const [catalogo, setCatalogo] = useState([])
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)

  const respuesta = state?.respuesta
  const requiereAclaracion = respuesta?.estado === 'requiere_aclaracion' && !editados

  useEffect(() => {
    if (requiereAclaracion) listarProductos().then(setCatalogo).catch(() => setCatalogo([]))
  }, [requiereAclaracion])

  if (!respuesta) return <Navigate to="/" replace />

  // Productos parecidos para "Una pregunta para afinar": varios del catálogo coinciden, o la
  // consulta no dijo qué producto busca y se ofrece el catálogo.
  const parecidos = respuesta.comparacion
    ? [respuesta.comparacion.producto, ...respuesta.otros_productos]
    : catalogo

  function cambiar(campo, valor) {
    setCriterios({ ...criterios, [campo]: valor === '' ? null : valor })
    setEditados(true)
  }

  async function verResultados() {
    setCargando(true)
    setError(null)
    try {
      let comparacion
      if (elegido) {
        comparacion = await ofertasDeProducto(elegido, {
          prioridad: criterios.prioridad,
          presupuesto: criterios.precio_max_cop,
        })
      } else if (editados) {
        const nueva = await consultar(state.texto, { criterios })
        if (nueva.estado === 'sin_cobertura') {
          navegar('/sin-cobertura', { state: { texto: state.texto, respuesta: nueva } })
          return
        }
        if (nueva.estado === 'requiere_aclaracion') {
          setError('Indica qué producto buscas para poder comparar precios.')
          setCargando(false)
          return
        }
        comparacion = nueva.comparacion
      } else {
        comparacion = respuesta.comparacion
      }
      navegar('/resultados', { state: { texto: state.texto, criterios, comparacion } })
    } catch (e) {
      setError(e.message)
      setCargando(false)
    }
  }

  const filas = [
    { campo: 'producto', nombre: 'Producto', valor: capitalizar(criterios.producto), tipo: 'text' },
    { campo: 'marca', nombre: 'Marca', valor: criterios.marca, tipo: 'text' },
    { campo: 'modelo', nombre: 'Modelo', valor: criterios.modelo, tipo: 'text' },
    {
      campo: 'atributos',
      nombre: 'Atributos',
      valor: Object.values(criterios.atributos).map(capitalizar).join(' · ') || null,
      editable: false,
    },
    {
      campo: 'precio_max_cop',
      nombre: 'Precio máximo',
      valor: criterios.precio_max_cop ? pesos(criterios.precio_max_cop) : null,
      tipo: 'number',
    },
    { campo: 'prioridad', nombre: 'Prioridad', valor: PRIORIDADES[criterios.prioridad], tipo: 'prioridad' },
  ]

  return (
    <div className="angosto" style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
      <div className="barra-titulo">
        <button className="boton-volver" aria-label="Volver a la búsqueda" onClick={() => navegar('/')}>
          <Volver />
        </button>
        <h1 className="barra-titulo__titulo">¿Entendimos bien?</h1>
      </div>

      <div className="tarjeta consulta-original">
        <Comillas tamano={18} />
        <span data-cy="consulta-original">“{state.texto}”</span>
      </div>

      <div className="tarjeta criterios" data-cy="criterios">
        {filas.map((fila) => (
          <div className="criterio" key={fila.campo} data-cy={`criterio-${fila.campo}`}>
            <span className="criterio__nombre" id={`nombre-${fila.campo}`}>
              {fila.nombre}
            </span>
            {editando === fila.campo ? (
              <CampoEdicion fila={fila} criterios={criterios} cambiar={cambiar} terminar={() => setEditando(null)} />
            ) : (
              <span className={`criterio__valor ${fila.valor ? '' : 'criterio__valor--vacio'}`}>
                {fila.valor ?? 'Sin especificar'}
              </span>
            )}
            {fila.editable !== false && editando !== fila.campo && (
              <button
                className="boton-editar"
                aria-label={`Editar ${fila.nombre.toLowerCase()}`}
                onClick={() => setEditando(fila.campo)}
              >
                <Lapiz tamano={18} />
              </button>
            )}
          </div>
        ))}
      </div>

      {parecidos.length > 1 || requiereAclaracion ? (
        <div className="aviso aviso--advertencia" style={{ flexDirection: 'column', gap: 12 }} data-cy="aclaracion">
          <div className="aviso__textos">
            <span className="aviso__titulo">Una pregunta para afinar</span>
            <span>
              {requiereAclaracion
                ? 'No nos quedó claro qué producto buscas. ¿Es alguno de estos?'
                : 'Encontramos varios productos parecidos. ¿Cuál buscas?'}
            </span>
          </div>
          <div className="opciones">
            {parecidos.map((p) => (
              <button
                key={p.id}
                className="chip"
                aria-pressed={elegido === p.id}
                onClick={() => setElegido(elegido === p.id ? null : p.id)}
              >
                {p.nombre}
              </button>
            ))}
          </div>
        </div>
      ) : null}

      {error && <Aviso tipo="error">{error}</Aviso>}

      {cargando ? (
        <Cargando texto="Buscando los mejores precios…" />
      ) : (
        <div className="acciones">
          <button
            className="boton boton--ancho"
            onClick={verResultados}
            disabled={requiereAclaracion && !elegido}
            data-cy="ver-resultados"
          >
            Ver resultados
          </button>
          <button className="enlace-boton" onClick={() => navegar('/')}>
            Escribir otra búsqueda
          </button>
        </div>
      )}
    </div>
  )
}

function CampoEdicion({ fila, criterios, cambiar, terminar }) {
  const comun = { autoFocus: true, onBlur: terminar, 'aria-labelledby': `nombre-${fila.campo}` }
  if (fila.tipo === 'prioridad') {
    return (
      <span className="criterio__valor">
        <select {...comun} value={criterios.prioridad} onChange={(e) => cambiar('prioridad', e.target.value)}>
          {Object.entries(PRIORIDADES).map(([valor, nombre]) => (
            <option key={valor} value={valor}>
              {nombre}
            </option>
          ))}
        </select>
      </span>
    )
  }
  return (
    <span className="criterio__valor">
      <input
        {...comun}
        type={fila.tipo}
        min={fila.tipo === 'number' ? 1000 : undefined}
        step={fila.tipo === 'number' ? 1000 : undefined}
        value={criterios[fila.campo] ?? ''}
        onChange={(e) => cambiar(fila.campo, fila.tipo === 'number' ? Number(e.target.value) || '' : e.target.value)}
        onKeyDown={(e) => e.key === 'Enter' && terminar()}
      />
    </span>
  )
}
