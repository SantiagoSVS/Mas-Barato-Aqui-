import { defineConfig } from 'cypress'

// Pruebas E2E de la interfaz (sección 9). Necesitan el servidor de Vite corriendo
// (npm run dev). La API se simula con respuestas reales guardadas en cypress/fixtures, así las
// pruebas no dependen de los precios del día ni de que el backend esté encendido.
export default defineConfig({
  e2e: {
    baseUrl: 'http://localhost:5173',
    specPattern: 'cypress/e2e/**/*.cy.js',
    viewportWidth: 390,
    viewportHeight: 844,
    video: false,
  },
})
