import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.jsx'

// Design-system tokens (copied verbatim from the Beacon design system).
import './styles/tokens/fonts.css'
import './styles/tokens/colors.css'
import './styles/tokens/typography.css'
import './styles/tokens/spacing.css'
import './styles/tokens/base.css'
// The "Ask the Network" screen's keyframes + hover/focus rules.
import './styles/ask-network.css'

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
