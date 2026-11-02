"""Motor de costo total (sección 7 del documento de arquitectura).

    CT = P + E          costo total estimado
    CA = CT + w · D     costo ajustado por tiempo de entrega

P es el precio, E el envío (0 si es gratis), D los días de entrega y w el valor en pesos de
cada día de espera. w = 0 es el perfil "Menor costo total" y w > 0 el de "Entrega más rápida"
(RF-11).

Orden: por CA; si hay empate, menor CT; luego menos días; por último el id de la oferta, solo
para que el resultado sea reproducible. Ninguna regla depende de la tienda (neutralidad).

Datos incompletos ("ante la duda, omitir"): si falta el envío, CT no se puede calcular; si
w > 0 y faltan los días, tampoco CA. Esas ofertas no se mezclan con las completas: van en un
grupo aparte, ordenadas por precio, y nunca son la recomendada. Las ofertas no disponibles se
descartan.
"""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class OfertaVigente:
    """Última captura de una oferta, con lo necesario para calcular y mostrar su costo."""

    oferta_id: int
    plataforma: str
    titulo: str
    url: str
    vendedor: str | None
    precio_cop: int
    envio_cop: int | None
    dias_entrega: int | None
    disponible: bool
    capturado_en: datetime


@dataclass(frozen=True)
class OfertaCalculada:
    oferta: OfertaVigente
    costo_total: int | None  # CT; None si el envío es desconocido
    costo_ajustado: int | None  # CA; None si falta CT, o si w > 0 y faltan los días
    supera_presupuesto: bool

    @property
    def completa(self) -> bool:
        return self.costo_ajustado is not None


@dataclass(frozen=True)
class Ranking:
    w: int
    ordenadas: list[OfertaCalculada]  # con costo completo, de la mejor a la peor
    incompletas: list[OfertaCalculada]  # envío o días desconocidos, por precio

    @property
    def recomendada(self) -> OfertaCalculada | None:
        return self.ordenadas[0] if self.ordenadas else None


def calcular(oferta: OfertaVigente, w: int, presupuesto_cop: int | None = None) -> OfertaCalculada:
    if w < 0:
        raise ValueError("w no puede ser negativo")
    costo_total = None if oferta.envio_cop is None else oferta.precio_cop + oferta.envio_cop
    if costo_total is None:
        costo_ajustado = None
    elif w == 0:
        costo_ajustado = costo_total  # sin peso por día, los días no hacen falta
    elif oferta.dias_entrega is None:
        costo_ajustado = None
    else:
        costo_ajustado = costo_total + w * oferta.dias_entrega

    # Para el aviso de presupuesto se usa lo que se sabe: CT, o al menos el precio
    referencia = costo_total if costo_total is not None else oferta.precio_cop
    supera = presupuesto_cop is not None and referencia > presupuesto_cop
    return OfertaCalculada(oferta, costo_total, costo_ajustado, supera)


def ordenar(ofertas: list[OfertaVigente], w: int, presupuesto_cop: int | None = None) -> Ranking:
    calculadas = [calcular(o, w, presupuesto_cop) for o in ofertas if o.disponible]
    dias = lambda c: c.oferta.dias_entrega if c.oferta.dias_entrega is not None else float("inf")  # noqa: E731
    completas = sorted(
        (c for c in calculadas if c.completa),
        key=lambda c: (c.costo_ajustado, c.costo_total, dias(c), c.oferta.oferta_id),
    )
    incompletas = sorted(
        (c for c in calculadas if not c.completa),
        key=lambda c: (c.oferta.precio_cop, c.oferta.oferta_id),
    )
    return Ranking(w=w, ordenadas=completas, incompletas=incompletas)


def explicar(ranking: Ranking) -> str | None:
    """Frase "Por qué es la recomendada" de la pantalla P3."""
    recomendada = ranking.recomendada
    if recomendada is None:
        return None
    if len(ranking.ordenadas) == 1:
        return "es la única opción con precio y envío conocidos."
    siguiente = ranking.ordenadas[1]
    if ranking.w == 0:
        diferencia = siguiente.costo_total - recomendada.costo_total
        if diferencia == 0:
            return "tiene el mismo costo total que la siguiente opción y llega antes o igual."
        return f"es {formato_pesos(diferencia)} más barata que la siguiente opción al sumar el envío."
    diferencia = siguiente.costo_ajustado - recomendada.costo_ajustado
    if diferencia == 0:
        return "tiene el mismo costo ajustado que la siguiente opción y menor costo total."
    return (
        f"tiene el menor costo ajustado por tiempo de entrega: {formato_pesos(diferencia)} menos "
        "que la siguiente opción."
    )


def formato_pesos(valor: int) -> str:
    """$789.000, con punto como separador de miles (español de Colombia)."""
    return "$" + f"{valor:,}".replace(",", ".")


def url_de_compra(oferta: OfertaVigente) -> str:
    """Enlace para "Ir a la tienda" (RF-08).

    Toda redirección pasa por aquí: si más adelante se agrega afiliación, se cambia solo esta
    función y el orden de las ofertas no se ve afectado (neutralidad).
    """
    return oferta.url
