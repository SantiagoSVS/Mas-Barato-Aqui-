export default function Encabezado() {
  return (
    <header className="encabezado">
      <div className="encabezado__contenido">
        <a className="marca" href="/" aria-label="Mas Barato Aquí!, ir al inicio">
          <span className="marca__icono">
            <svg
              width="24"
              height="24"
              viewBox="0 0 24 24"
              fill="none"
              stroke="#FFFFFF"
              strokeWidth="2"
              strokeLinecap="round"
              strokeLinejoin="round"
              aria-hidden="true"
            >
              <path d="M3 4h2l2.4 10.2a1.5 1.5 0 0 0 1.5 1.1h7.6a1.5 1.5 0 0 0 1.4-1l1.9-6.3H6.2" />
              <circle cx="9.5" cy="19.5" r="1.4" />
              <circle cx="16.5" cy="19.5" r="1.4" />
            </svg>
          </span>
          <span className="marca__texto">
            <span>Mas Barato</span>
            <span className="marca__aqui">Aquí!</span>
          </span>
        </a>
      </div>
    </header>
  )
}
