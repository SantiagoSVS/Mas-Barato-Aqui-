// Comandos compartidos por las pruebas E2E

// Simula la API con respuestas reales guardadas (capturadas el 2 de noviembre de 2026)
Cypress.Commands.add('simularApi', () => {
  cy.intercept('GET', '/api/salud', { fixture: 'salud.json' }).as('salud')
  cy.intercept('GET', '/api/productos', { fixture: 'productos.json' }).as('productos')
  cy.intercept('POST', '/api/consultas', (peticion) => {
    const texto = peticion.body.texto.toLowerCase()
    if (texto.includes('tenis')) peticion.reply({ fixture: 'consulta_sin_cobertura.json' })
    else if (texto.includes('algo bueno')) peticion.reply({ fixture: 'consulta_aclaracion.json' })
    else peticion.reply({ fixture: 'consulta_resultados.json' })
  }).as('consulta')
  cy.fixture('consulta_resultados.json').then((resultados) => {
    cy.intercept('GET', '/api/productos/*/ofertas*', (peticion) => {
      if (peticion.url.includes('entrega_rapida')) peticion.reply({ fixture: 'ofertas_entrega_rapida.json' })
      else peticion.reply(resultados.comparacion)
    }).as('ofertas')
  })
  cy.intercept('GET', '/api/productos/*/historial?periodo=3M', { fixture: 'historial.json' }).as('historial')
  cy.intercept('GET', '/api/productos/*/historial?periodo=1M', { fixture: 'historial_1m.json' }).as('historial1M')
})

// Escribe una consulta en P1 y la envía
Cypress.Commands.add('buscar', (texto) => {
  cy.get('[data-cy=consulta]').clear().type(texto)
  cy.get('[data-cy=buscar]').click()
})
