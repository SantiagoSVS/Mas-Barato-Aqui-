import { Link, Navigate, useLocation } from 'react-router-dom'
import { Caja } from '../componentes/Iconos.jsx'

// Estado "sin cobertura" (RF-13): la consulta queda registrada para ampliar el catálogo
export default function SinCobertura() {
  const { state } = useLocation()
  if (!state?.texto) return <Navigate to="/" replace />

  return (
    <div className="angosto">
      <div className="tarjeta vacio" data-cy="sin-cobertura">
        <div className="vacio__icono">
          <Caja tamano={28} />
        </div>
        <h1 className="vacio__titulo">Aún no tenemos este producto</h1>
        <p className="texto-secundario" style={{ margin: 0 }}>
          “{state.texto}” no está en nuestro catálogo todavía. Quedó registrado en la lista que usamos para
          ampliar el catálogo.
        </p>
        <Link className="boton" to="/">
          Probar otra búsqueda
        </Link>
      </div>
    </div>
  )
}
