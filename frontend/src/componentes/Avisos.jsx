import { Alerta, Info } from './Iconos.jsx'

export function Aviso({ tipo = 'advertencia', titulo, children, ...props }) {
  const Icono = tipo === 'info' ? Info : Alerta
  return (
    <div className={`aviso aviso--${tipo}`} role={tipo === 'error' ? 'alert' : undefined} {...props}>
      <Icono tamano={18} />
      <div className="aviso__textos">
        {titulo && <span className="aviso__titulo">{titulo}</span>}
        {children && <span>{children}</span>}
      </div>
    </div>
  )
}

export function AvisoCosto() {
  return (
    <Aviso tipo="info" data-cy="aviso-costo">
      Costo estimado: no incluye impuestos, descuentos por medio de pago ni promociones que la tienda aplica al
      pagar.
    </Aviso>
  )
}

export function Cargando({ texto }) {
  return (
    <div className="tarjeta cargando" role="status" data-cy="cargando">
      <span className="cargando__texto">
        <span className="giro" aria-hidden="true" />
        {texto}
      </span>
      <span className="esqueleto" style={{ width: '90%' }} />
      <span className="esqueleto" style={{ width: '70%' }} />
      <span className="esqueleto" style={{ width: '80%' }} />
    </div>
  )
}
