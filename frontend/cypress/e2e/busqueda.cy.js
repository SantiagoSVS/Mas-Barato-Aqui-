// P1 · Búsqueda (RF-01)
describe('P1 · Búsqueda', () => {
  beforeEach(() => {
    cy.simularApi()
    cy.visit('/')
  })

  it('muestra el título, la caja de búsqueda y las tiendas activas', () => {
    cy.contains('h1', '¿Qué quieres comprar?')
    cy.get('[data-cy=consulta]').should('have.attr', 'maxlength', '300')
    cy.get('[data-cy=tiendas]').should('contain', 'Comparamos 3 tiendas').and('contain', 'Mercado Libre')
  })

  it('el botón Buscar se habilita solo cuando hay texto y el contador avanza', () => {
    cy.get('[data-cy=buscar]').should('be.disabled')
    cy.get('[data-cy=consulta]').type('freidora')
    cy.contains('8 / 300')
    cy.get('[data-cy=buscar]').should('be.enabled')
  })

  it('un ejemplo llena la caja de búsqueda', () => {
    cy.get('[data-cy=ejemplo]').first().click()
    cy.get('[data-cy=consulta]').should('have.value', 'Audífonos Xiaomi que no pasen de 150 mil')
  })

  it('muestra el estado de carga mientras interpreta la consulta', () => {
    cy.intercept('POST', '/api/consultas', (peticion) => {
      peticion.reply({ delay: 800, fixture: 'consulta_resultados.json' })
    })
    cy.buscar('freidora de aire oster')
    cy.get('[data-cy=cargando]').should('contain', 'Entendiendo tu búsqueda…')
    cy.location('pathname').should('eq', '/criterios')
  })

  it('envía la consulta a la API tal como la escribió el usuario', () => {
    cy.buscar('freidora de aire oster que no pase de 230 mil')
    cy.wait('@consulta').its('request.body.texto').should('eq', 'freidora de aire oster que no pase de 230 mil')
  })
})
