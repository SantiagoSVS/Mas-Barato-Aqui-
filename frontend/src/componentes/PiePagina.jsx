import { Marca } from './Encabezado.jsx'

// Pie de los mockups de escritorio. Los enlaces legales y de redes quedan pendientes hasta que
// existan esas páginas (no se muestran enlaces que no llevan a ningún lado).
export default function PiePagina() {
  return (
    <footer className="pie">
      <div className="pie__contenido">
        <div className="pie__marca">
          <Marca />
          <strong>Compara · Encuentra · Ahorra</strong>
          <p className="pie__texto">
            No vendemos productos: te mostramos dónde sale más barato y te llevamos a la tienda original para
            que compres allí. El orden de los resultados depende solo del costo total.
          </p>
        </div>
        <div className="pie__legal">
          <span>© 2026 Mas Barato Aquí! · Medellín, Colombia</span>
          <span>
            Costos estimados: no incluyen impuestos, descuentos por medio de pago ni promociones que la tienda
            aplica al pagar.
          </span>
        </div>
      </div>
    </footer>
  )
}
