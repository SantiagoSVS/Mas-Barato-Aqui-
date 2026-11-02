// Estados especiales (docs/pantallas.md): sin cobertura, aclaración, errores y responsive
describe('Estados', () => {
  beforeEach(() => {
    cy.simularApi()
    cy.visit('/')
  })

  it('producto fuera del catálogo: "Aún no tenemos este producto" (RF-13)', () => {
    cy.buscar('tenis adidas talla 42')
    cy.get('[data-cy=sin-cobertura]')
      .should('contain', 'Aún no tenemos este producto')
      .and('contain', 'tenis adidas talla 42')
    cy.contains('Probar otra búsqueda').click()
    cy.location('pathname').should('eq', '/')
  })

  it('consulta ambigua: pide elegir un producto antes de ver resultados', () => {
    cy.buscar('algo bueno y barato')
    cy.get('[data-cy=aclaracion]').should('contain', 'No nos quedó claro qué producto buscas')
    cy.get('[data-cy=ver-resultados]').should('be.disabled')
    cy.get('[data-cy=aclaracion]').contains('button', 'Freidora de aire Oster').click()
    cy.get('[data-cy=ver-resultados]').should('be.enabled').click()
    cy.wait('@ofertas')
    cy.get('[data-cy=recomendada]').should('exist')
  })

  it('al corregir un criterio, se envían los criterios editados sin volver a interpretar', () => {
    cy.buscar('freidora de aire oster')
    cy.get('[aria-label="Editar precio máximo"]').click()
    cy.get('[data-cy=criterio-precio_max_cop] input').clear().type('200000{enter}')
    cy.get('[data-cy=criterio-precio_max_cop]').should('contain', '$200.000')
    cy.get('[data-cy=ver-resultados]').click()
    cy.wait(['@consulta', '@consulta'])
      .then(([, edicion]) => {
        expect(edicion.request.body.criterios.precio_max_cop).to.eq(200000)
      })
  })

  it('demasiadas consultas: muestra el mensaje del límite por IP', () => {
    cy.intercept('POST', '/api/consultas', {
      statusCode: 429,
      body: { detail: 'Hiciste muchas consultas seguidas. Intenta de nuevo en un minuto.' },
    })
    cy.buscar('freidora')
    cy.get('[data-cy=error]').should('contain', 'Intenta de nuevo en un minuto')
  })

  it('sin conexión: muestra un error claro', () => {
    cy.intercept('POST', '/api/consultas', { forceNetworkError: true })
    cy.buscar('freidora')
    cy.get('[data-cy=error]').should('contain', 'No pudimos conectarnos')
  })

  it('una tienda que falló en la última captura se avisa en resultados (RNF-05)', () => {
    cy.fixture('salud.json').then((salud) => {
      salud.plataformas[0].ultima_ejecucion = { ...salud.plataformas[0].ultima_ejecucion, estado: 'fallida' }
      cy.intercept('GET', '/api/salud', salud)
    })
    cy.buscar('freidora de aire oster')
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('[data-cy=tienda-sin-respuesta]').should('contain', 'no respondió en la última actualización')
  })

  it('en escritorio las alternativas se muestran en tabla', () => {
    cy.viewport(1280, 900)
    cy.buscar('freidora de aire oster')
    cy.get('[data-cy=ver-resultados]').click()
    cy.get('table').should('be.visible').and('contain', 'Costo total')
    cy.get('[data-cy=alternativa]').should('not.be.visible')
  })
})
