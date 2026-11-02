import { Link } from 'react-router-dom'
import { Carrito } from './Iconos.jsx'

export function Marca() {
  return (
    <span className="marca__texto">
      <span>Mas Barato</span>
      <span className="marca__aqui">Aquí!</span>
    </span>
  )
}

export default function Encabezado() {
  return (
    <header className="encabezado">
      <div className="encabezado__contenido">
        <Link className="marca" to="/" aria-label="Mas Barato Aquí!, ir al inicio">
          <span className="marca__icono">
            <Carrito tamano={24} />
          </span>
          <Marca />
        </Link>
      </div>
    </header>
  )
}
