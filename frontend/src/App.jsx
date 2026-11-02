import { Route, Routes } from 'react-router-dom'
import Encabezado from './componentes/Encabezado.jsx'
import PiePagina from './componentes/PiePagina.jsx'
import Busqueda from './paginas/Busqueda.jsx'
import Historial from './paginas/Historial.jsx'
import Interpretacion from './paginas/Interpretacion.jsx'
import Resultados from './paginas/Resultados.jsx'
import SinCobertura from './paginas/SinCobertura.jsx'

// Flujo del documento (sección 8): P1 búsqueda → P2 criterios → P3 resultados → P4 historial
export default function App() {
  return (
    <div className="aplicacion">
      <Encabezado />
      <main className="contenido">
        <Routes>
          <Route path="/" element={<Busqueda />} />
          <Route path="/criterios" element={<Interpretacion />} />
          <Route path="/resultados" element={<Resultados />} />
          <Route path="/sin-cobertura" element={<SinCobertura />} />
          <Route path="/productos/:id/historial" element={<Historial />} />
          <Route path="*" element={<Busqueda />} />
        </Routes>
      </main>
      <PiePagina />
    </div>
  )
}
