import { useEffect, useState } from 'react'
import { consultarSalud } from './api.js'
import Encabezado from './componentes/Encabezado.jsx'

// Incremento 0: solo la base visual y la conexión con la API.
// Las pantallas P1 a P4 se construyen en el incremento 5.
export default function App() {
  const [salud, setSalud] = useState({ cargando: true })

  useEffect(() => {
    consultarSalud()
      .then((datos) => setSalud({ cargando: false, datos }))
      .catch(() => setSalud({ cargando: false, error: true }))
  }, [])

  return (
    <>
      <Encabezado />
      <main className="contenido">
        <h1>¿Qué quieres comprar?</h1>
        <p className="subtitulo">
          Escríbelo con tus palabras. Te mostramos dónde sale más barato, sumando el envío.
        </p>
        <section className="tarjeta" aria-live="polite">
          <EstadoServicio salud={salud} />
        </section>
      </main>
    </>
  )
}

function EstadoServicio({ salud }) {
  if (salud.cargando) {
    return <p className="estado">Consultando el estado del servicio…</p>
  }

  if (salud.error) {
    return (
      <>
        <p className="estado estado--error">
          <span className="estado__punto" aria-hidden="true" />
          La API no responde
        </p>
        <p className="estado__detalle">Revisa que el backend esté corriendo en el puerto 8000.</p>
      </>
    )
  }

  const { estado, base_de_datos, plataformas } = salud.datos
  const todoBien = estado === 'ok'
  return (
    <>
      <p className={`estado ${todoBien ? 'estado--ok' : 'estado--error'}`}>
        <span className="estado__punto" aria-hidden="true" />
        {todoBien ? 'Servicio funcionando' : 'Servicio degradado'}
      </p>
      <p className="estado__detalle">
        Base de datos: {base_de_datos === 'ok' ? 'conectada' : 'sin conexión'} · Tiendas
        registradas: {plataformas.length}
      </p>
    </>
  )
}
