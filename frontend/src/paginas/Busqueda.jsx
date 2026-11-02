import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { consultar, consultarSalud } from '../api.js'
import { Aviso, Cargando } from '../componentes/Avisos.jsx'
import { Lupa } from '../componentes/Iconos.jsx'

const LARGO_MAXIMO = 300
// Ejemplos de productos que hoy están en el catálogo
const EJEMPLOS = [
  'Audífonos Xiaomi que no pasen de 150 mil',
  'Freidora de aire Oster, que llegue rápido',
  'Reloj inteligente Redmi Watch 6 Active',
]

// P1 · Búsqueda (RF-01)
export default function Busqueda() {
  const navegar = useNavigate()
  const [texto, setTexto] = useState('')
  const [cargando, setCargando] = useState(false)
  const [error, setError] = useState(null)
  const [tiendas, setTiendas] = useState([])

  useEffect(() => {
    consultarSalud()
      .then((salud) => setTiendas(salud.plataformas.filter((p) => p.activa).map((p) => p.nombre)))
      .catch(() => setTiendas([]))
  }, [])

  async function buscar(evento) {
    evento.preventDefault()
    if (!texto.trim()) return
    setCargando(true)
    setError(null)
    try {
      const respuesta = await consultar(texto.trim())
      const destino = respuesta.estado === 'sin_cobertura' ? '/sin-cobertura' : '/criterios'
      navegar(destino, { state: { texto: texto.trim(), respuesta } })
    } catch (e) {
      setError(e.message)
      setCargando(false)
    }
  }

  return (
    <div className="busqueda">
      <div className="busqueda__principal">
        <div>
          <h1>¿Qué quieres comprar?</h1>
          <p className="subtitulo">Escríbelo con tus palabras. Te mostramos dónde sale más barato, sumando el envío.</p>
        </div>

        {cargando ? (
          <Cargando texto="Entendiendo tu búsqueda…" />
        ) : (
          <form className="tarjeta caja-busqueda" onSubmit={buscar}>
            <label htmlFor="consulta">Tu búsqueda</label>
            <textarea
              id="consulta"
              rows={3}
              maxLength={LARGO_MAXIMO}
              value={texto}
              placeholder="Ej.: busco un celular gama media por menos de 800 mil"
              onChange={(e) => setTexto(e.target.value)}
              data-cy="consulta"
            />
            <div className="caja-busqueda__pie">
              <span className="contador" aria-live="polite">
                {texto.length} / {LARGO_MAXIMO}
              </span>
              <button className="boton" type="submit" disabled={!texto.trim()} data-cy="buscar">
                <Lupa tamano={18} />
                Buscar
              </button>
            </div>
          </form>
        )}

        {error && (
          <Aviso tipo="error" titulo="No pudimos hacer la búsqueda" data-cy="error">
            {error}
          </Aviso>
        )}

        <div className="ejemplos">
          <span className="ejemplos__titulo">Ejemplos de búsqueda</span>
          {EJEMPLOS.map((ejemplo) => (
            <button key={ejemplo} type="button" className="ejemplo" onClick={() => setTexto(ejemplo)} data-cy="ejemplo">
              “{ejemplo}”
            </button>
          ))}
        </div>
      </div>

      <div className="busqueda__lateral">
        <section className="asi-funciona" aria-labelledby="como-funciona">
          <span className="asi-funciona__titulo" id="como-funciona">
            Así funciona
          </span>
          <ol className="pasos">
            <li className="paso">
              <span className="paso__numero">1</span>Describe lo que buscas
            </li>
            <li className="paso">
              <span className="paso__numero">2</span>Confirma lo que entendimos
            </li>
            <li className="paso">
              <span className="paso__numero">3</span>Compra donde más te conviene
            </li>
          </ol>
        </section>

        {tiendas.length > 0 && (
          <section className="tiendas" data-cy="tiendas">
            <strong>Comparamos {tiendas.length} tiendas</strong>
            <span className="tiendas__nombres">{tiendas.join(' · ')}</span>
            <span>Precios actualizados de forma periódica. No necesitas cuenta.</span>
          </section>
        )}
      </div>
    </div>
  )
}
