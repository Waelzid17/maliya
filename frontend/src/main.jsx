import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter } from 'react-router-dom'
import App from './App'
import { FournisseurMaliya } from './contexte'
import '@fontsource/schibsted-grotesk/400.css'
import '@fontsource/schibsted-grotesk/500.css'
import '@fontsource/schibsted-grotesk/600.css'
import '@fontsource/schibsted-grotesk/700.css'
import '@fontsource/schibsted-grotesk/800.css'
import '@fontsource/caveat/500.css'
import '@fontsource/caveat/600.css'
import '@fontsource/reem-kufi/600.css'
import './styles.css'

ReactDOM.createRoot(document.getElementById('racine')).render(
  <React.StrictMode>
    <BrowserRouter>
      <FournisseurMaliya>
        <App />
      </FournisseurMaliya>
    </BrowserRouter>
  </React.StrictMode>,
)
