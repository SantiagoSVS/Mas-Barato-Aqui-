// Flujo completo del documento (sección 8): P1 → P2 → P3 → P4 → tienda
describe('Flujo de compra', () => {
  beforeEach(() => {
    cy.simularApi()
    cy.visit('/')
    cy.buscar('freidora de aire oster que no pase de 230 mil')
  })

  it('P2 muestra lo que entendió el sistema', () => {
    cy.get('[data-cy=consulta-original]').should('contain', 'freidora de aire oster que no pase de 230 mil')
    cy.get('[data-cy=criterio-producto]').should('contain', 'Freidora de aire')
    cy.get('[data-cy=criterio-marca]').should('contain', 'Oster')
    cy.get('[data-cy=criterio-precio_max_cop]').should('contain', '$230.000')
    cy.get('[data-cy=criterio-prioridad]').should('contain', 'Menor costo total')
  })

  it('P3 muestra la recomendada con su costo total, desglose, explicación y fuente', () => {
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=recomendada]').within(() => {
      cy.get('[data-cy=tienda-recomendada]').should('contain', 'Mercado Libre')
      cy.contains('$224.175')
      cy.contains('Envío').parent().should('contain', 'Gratis')
      cy.get('[data-cy=explicacion]').should('contain', 'más barata que la siguiente opción')
      cy.contains('Fuente: Mercado Libre · capturado')
    })
    cy.get('[data-cy=aviso-costo]').should('contain', 'Costo estimado')
  })

  it('P3 separa las ofertas con envío por confirmar y marca las que superan el presupuesto', () => {
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=sin-costo]').should('contain', 'Con envío por confirmar').and('contain', 'Falabella')
    cy.get('[data-cy=alternativa]').first().should('contain', 'Supera tu presupuesto con envío')
  })

  it('el enlace "Ir a la tienda" abre la publicación original en otra pestaña (RF-08)', () => {
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=ir-a-tienda]')
      .should('have.attr', 'target', '_blank')
      .and('have.attr', 'rel', 'noopener noreferrer')
      .and('have.attr', 'href')
      .and('match', /^https:\/\/articulo\.mercadolibre\.com\.co\//)
  })

  it('cambiar a "Entrega más rápida" pide el nuevo orden a la API (RF-11)', () => {
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=prioridad-entrega_rapida]').click()
    cy.wait('@ofertas').its('request.url').should('include', 'prioridad=entrega_rapida').and('include', 'presupuesto_cop=230000')
    cy.get('[data-cy=prioridad-entrega_rapida]').should('have.attr', 'aria-pressed', 'true')
    cy.get('[data-cy=aviso]').should('contain', 'aún no está calibrado')
  })

  it('P4 muestra el historial con el indicador y permite cambiar de periodo', () => {
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=ver-historial]').click()
    cy.wait('@historial')
    cy.get('[data-cy=indicador]').should('contain', 'Cerca de su mínimo histórico')
    cy.get('[data-cy=grafico] svg').should('exist')
    cy.get('[data-cy=resumen-historial]').should('contain', 'Mercado Libre').and('contain', 'Homecenter')
    cy.get('[data-cy=periodo-1M]').click()
    cy.wait('@historial1M')
    cy.get('[data-cy=periodo-1M]').should('have.attr', 'aria-pressed', 'true')
  })
})
