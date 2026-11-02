// Íconos de línea de los mockups. Son decorativos: los botones llevan su texto o aria-label.
function Icono({ children, tamano = 20, color = 'currentColor', grosor = 2 }) {
  return (
    <svg
      width={tamano}
      height={tamano}
      viewBox="0 0 24 24"
      fill="none"
      stroke={color}
      strokeWidth={grosor}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      {children}
    </svg>
  )
}

export const Carrito = (p) => (
  <Icono {...p}>
    <path d="M3 4h2l2.4 10.2a1.5 1.5 0 0 0 1.5 1.1h7.6a1.5 1.5 0 0 0 1.4-1l1.9-6.3H6.2" />
    <circle cx="9.5" cy="19.5" r="1.4" />
    <circle cx="16.5" cy="19.5" r="1.4" />
  </Icono>
)
export const Lupa = (p) => (
  <Icono {...p}>
    <circle cx="11" cy="11" r="7" />
    <path d="M20 20l-3.5-3.5" />
  </Icono>
)
export const Volver = (p) => (
  <Icono {...p}>
    <path d="M15 18l-6-6 6-6" />
  </Icono>
)
export const Lapiz = (p) => (
  <Icono {...p}>
    <path d="M4 20h4L19 9l-4-4L4 16v4z" />
  </Icono>
)
export const Externo = (p) => (
  <Icono {...p}>
    <path d="M14 4h6v6M20 4l-9 9M18 14v5a1 1 0 0 1-1 1H5a1 1 0 0 1-1-1V7a1 1 0 0 1 1-1h5" />
  </Icono>
)
export const Estrella = (p) => (
  <Icono {...p}>
    <path d="M12 3l2.7 5.6 6.1.9-4.4 4.3 1 6.1L12 17l-5.4 2.9 1-6.1L3.2 9.5l6.1-.9L12 3z" />
  </Icono>
)
export const Info = (p) => (
  <Icono {...p}>
    <circle cx="12" cy="12" r="9" />
    <path d="M12 11v5M12 8h.01" />
  </Icono>
)
export const Alerta = (p) => (
  <Icono {...p}>
    <path d="M12 3l9.5 16.5H2.5L12 3z" />
    <path d="M12 10v4M12 17h.01" />
  </Icono>
)
export const Bajada = (p) => (
  <Icono {...p}>
    <path d="M3 7l6 6 4-4 8 8M21 11v6h-6" />
  </Icono>
)
export const Caja = (p) => (
  <Icono {...p}>
    <path d="M3 7l9-4 9 4-9 4-9-4z" />
    <path d="M3 7v10l9 4 9-4V7M12 11v10" />
  </Icono>
)
export const Comillas = (p) => (
  <Icono {...p}>
    <path d="M7 7h4v4c0 3-2 5-4 6M15 7h4v4c0 3-2 5-4 6" />
  </Icono>
)
